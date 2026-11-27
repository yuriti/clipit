"""Jobs started from the page: each runs as `smtv <tool> <args>` in its own process, and the page reads its event journal.

A separate process because a job can be stopped only that way: speech recognition, ffmpeg and model calls cannot be
interrupted from a thread. One job is written by one process at a time: the page writes to a job's journal only after
its process has ended (the `cancelled` event, or an `error` when the process died without saying why).
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from smtv_core import events
from smtv_core.events import CANCELLED, ERROR, QUEUED, Journal

RUNNING, DONE, FAILED, CANCELLED_STATUS, UNFINISHED, NEW = "running", "done", "failed", "cancelled", "unfinished", "new"
QUEUED_STATUS = "queued"
LOG_NAME = "run.log"
# In the environment of every job SMTV starts: the job runs under SMTV's own lock of the data folder (`instance.py`), so
# its command neither hands itself over to SMTV again nor waits for the lock.
UNDER_SMTV = "SMTV_UNDER_SMTV"

Launcher = Callable[[str, list[str]], list[str]]


def smtv_command(tool: str, args: list[str]) -> list[str]:
    return [sys.executable, "-m", "smtv", tool, *args]


@dataclass
class Run:
    tool: str
    folder: Path
    process: subprocess.Popen
    first: int                      # the journal's last number before this run started
    started: float = field(default_factory=time.time)
    cancelled: bool = False
    interrupted: bool = False       # stopped because SMTV quits or updates, not by the person: it waits first in the queue
    finished: threading.Event = field(default_factory=threading.Event)

    @property
    def job(self) -> str:
        return self.folder.name


class Busy(Exception):
    pass


class Runner:
    """The jobs this page started and that still run. At most one running job per tool: they all want the whole processor.
    The others wait in SMTV's queue (`serve.App`): `on_finished` is told when a run ends, so the next one can start."""

    def __init__(self, launcher: Launcher = smtv_command):
        self.launcher = launcher
        self.runs: dict[tuple[str, str], Run] = {}
        self.lock = threading.Lock()
        self.on_finished: Callable[[Run], None] | None = None

    def running(self, tool: str, job: str) -> Run | None:
        run = self.runs.get((tool, job))
        return run if run and not run.finished.is_set() else None

    def busy(self, tool: str) -> Run | None:
        return next((r for (t, _), r in list(self.runs.items()) if t == tool and not r.finished.is_set()), None)

    def start(self, tool: str, folder: Path, args: list[str]) -> Run:
        with self.lock:
            other = self.busy(tool)
            if other:
                raise Busy(other.job)
            folder.mkdir(parents=True, exist_ok=True)
            first = events.last_number(folder / events.FILE_NAME)
            log = (folder / LOG_NAME).open("ab")
            env = {**os.environ, "PYTHONUNBUFFERED": "1", "PYTHONIOENCODING": "utf-8", UNDER_SMTV: str(os.getpid())}
            kwargs: dict = {"stdout": log, "stderr": subprocess.STDOUT, "stdin": subprocess.DEVNULL, "env": env, "cwd": str(folder)}
            if sys.platform == "win32":
                # no console window: the page may run under pythonw, and the job's output goes to its log anyway
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
            else:
                # its own process group: cancel reaches the job; the job turns SIGTERM into SystemExit (`as_job`), so
                # the ffmpeg or yt-dlp it runs (each in a group of its own, `proc.run`) is stopped by it first
                kwargs["start_new_session"] = True
            try:
                process = subprocess.Popen(self.launcher(tool, args), **kwargs)
            finally:
                log.close()
            run = Run(tool, folder, process, first)
            self.runs[(tool, folder.name)] = run
        threading.Thread(target=self._watch, args=(run,), name=f"smtv-job-{folder.name}", daemon=True).start()
        return run

    def cancel(self, tool: str, job: str, grace: float = 5.0, interrupted: bool = False) -> bool:
        run = self.running(tool, job)
        if not run:
            return False
        if run.process.poll() is not None and run.process.returncode == 0:
            run.finished.wait(5)            # it has just ended by itself: what it said stays (never «cancelled» over «done»)
            return True
        run.cancelled = True
        run.interrupted = interrupted
        _stop(run.process, grace)
        run.finished.wait(grace + 5)
        return True

    def _watch(self, run: Run) -> None:
        try:
            code = run.process.wait()
            _kill_group(run.process)        # whatever the job left behind in its group goes with it
            after = [e for e in events.read(run.folder, run.first)]
            said = any(e["type"] in ("done", "error", "cancelled") and e["data"].get("stage") != "subscriber" for e in after)
            if run.cancelled and any(e["type"] == "done" for e in after):
                pass                        # it finished before the stop reached it: «done» stays, never «cancelled»
            elif run.interrupted:
                # SMTV quits or updates: the request goes back to the queue, first, and goes on by itself next time
                with Journal(run.folder, tool=run.tool, subscribers=[]) as j:
                    j.emit(QUEUED, by="restart", first=True)
            elif run.cancelled:
                stage = next((e["data"].get("name") for e in reversed(after) if e["type"] == "stage"), None)
                with Journal(run.folder, tool=run.tool, subscribers=[]) as j:
                    j.emit(CANCELLED, by="user", **({"stage": stage} if stage else {}))
            elif code != 0 and not said:
                with Journal(run.folder, tool=run.tool, subscribers=[]) as j:
                    j.emit(ERROR, stage="process", exit_code=code, message=f"the job stopped with exit code {code}; details in {LOG_NAME}")
            elif not after and state(run.folder, None)[0] == QUEUED_STATUS:
                # it came from the queue and ended without a word: left as it is, the queue would start it again and again
                with Journal(run.folder, tool=run.tool, subscribers=[]) as j:
                    j.emit(ERROR, stage="process", exit_code=code, message=f"the job ended without writing anything; details in {LOG_NAME}")
        except Exception as e:  # noqa: BLE001 — a full disk or a broken journal: written down, the run ends anyway
            print(f"job {run.tool}/{run.job}: after the end: {type(e).__name__}: {e}")
            from smtv_core import crash
            try:
                crash.record(e, where="server", stage="job watch", tool=run.tool, job=run.job)
            except Exception:  # noqa: BLE001
                pass
        finally:
            run.finished.set()
            if self.on_finished:
                try:
                    self.on_finished(run)
                except Exception as e:  # noqa: BLE001 — the queue's trouble is its own; the run has ended either way
                    print(f"queue: after {run.tool}/{run.job}: {type(e).__name__}: {e}")
                    from smtv_core import crash
                    crash.record(e, where="server", stage="queue", tool=run.tool, job=run.job)

    def stop_all(self) -> None:
        """SMTV quits or updates: every running job stops and waits first in the queue for the next start."""
        for (tool, job) in list(self.runs):
            self.cancel(tool, job, grace=2.0, interrupted=True)


def _kill_group(process: subprocess.Popen) -> None:
    if sys.platform == "win32":
        return                              # taskkill /T went over the tree when it was stopped; nothing is left by a normal end
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def _stop(process: subprocess.Popen, grace: float) -> None:
    """Asks the job's whole process group to stop, then kills it if it does not."""
    if process.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, timeout=30,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        else:
            os.killpg(process.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError, subprocess.TimeoutExpired):
        pass
    try:
        process.wait(grace)
    except subprocess.TimeoutExpired:
        if sys.platform != "win32":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        process.kill()
        process.wait(5)


def status(folder: Path, run: Run | None) -> str:
    """What the journal says happened to the job, unless its process still runs."""
    return state(folder, run)[0]


def state(folder: Path, run: Run | None) -> tuple[str, float | None]:
    """The job's status and, while it waits in the queue, when it was put there (the queue's order)."""
    if run is not None:
        return RUNNING, None
    now, queued = NEW, None
    for e in events.read(folder):
        kind = e["type"]
        if kind == "queued":
            # a request SMTV stopped when it quit waits before every other one (its place is the start of time)
            now, queued = QUEUED_STATUS, 0.0 if e["data"].get("first") else float(e.get("t") or 0)
            continue
        if now == QUEUED_STATUS:          # anything after `queued` (even a progress line): the job has started
            now, queued = UNFINISHED, None
        if kind in ("stage", "done", "cancelled") or (kind == "error" and e["data"].get("stage") != "subscriber"):
            queued = None
        if kind == "stage":
            now = UNFINISHED
        elif kind == "done":
            now = DONE
        elif kind == "error" and e["data"].get("stage") != "subscriber":
            now = FAILED
        elif kind == "cancelled":
            now = CANCELLED_STATUS
    return now, queued


class Tail:
    """New complete events of a journal file, read from where the last read stopped (a page following a job)."""

    def __init__(self, path: Path, after: int = 0):
        self.path, self.after, self.offset = path, after, 0

    def read(self) -> list[dict]:
        try:
            size = self.path.stat().st_size
        except FileNotFoundError:
            return []
        if size < self.offset:   # the journal was replaced: start over, the numbers still say what was seen
            self.offset = 0
        if size == self.offset:
            return []
        with self.path.open("rb") as f:
            f.seek(self.offset)
            chunk = f.read(size - self.offset)
        end = chunk.rfind(b"\n")
        if end < 0:
            return []
        self.offset += end + 1
        out = []
        for line in chunk[:end].split(b"\n"):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict) and isinstance(event.get("n"), int) and event["n"] > self.after:
                out.append(event)
                self.after = event["n"]
        return out


def as_job() -> None:
    """At the start of a job process SMTV started (`UNDER_SMTV` in its environment): «Остановить» stops what it runs
    too (SIGTERM becomes SystemExit, `proc.run` stops its program), and the job ends when the SMTV that started it
    is gone — it must not go on writing into the folder while a new SMTV starts it again."""
    from smtv_core import proc

    owner = os.environ.get(UNDER_SMTV, "")
    if not owner.isdigit():
        return
    proc.exit_on_terminate()
    threading.Thread(target=_watch_owner, args=(int(owner),), name="smtv-owner", daemon=True).start()


def _watch_owner(pid: int, every: float = 5.0, alive=None, end=None) -> None:
    from .instance import alive as _alive
    alive = alive or _alive
    while alive(pid):
        time.sleep(every)
    print(f"Clip It! (process {pid}) is gone: this job stops; the new Clip It! goes on with it")
    (end or _end_self)()


def _end_self() -> None:
    if sys.platform == "win32":
        try:                                # this job and every program under it (ffmpeg, yt-dlp): none keeps writing
            from smtv_core import proc
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(os.getpid())], capture_output=True, timeout=30,
                           **proc.hidden())
        except (OSError, subprocess.SubprocessError):
            pass
        os._exit(3)
    os.kill(os.getpid(), signal.SIGTERM)


def leftover(saved: dict, runs: dict | None = None) -> int | None:
    """The process of a job started by an SMTV that is gone (crashed, killed) and still running: its id, or None.

    The id from the job's page-run note must belong to a living SMTV job started then — not to a program that got the
    same number later: on Mac and Linux its command line is `… -m smtv <tool>`, on Windows it started when the note says.
    """
    pid = saved.get("pid") if isinstance(saved, dict) else None
    if not isinstance(pid, int) or pid <= 0 or pid == os.getpid():
        return None
    if runs and any(r.process.pid == pid for r in list(runs.values())):
        return None                         # ours: the runner knows it
    from .instance import alive
    if not alive(pid):
        return None
    return pid if _is_job(pid, float(saved.get("started") or 0), str(saved.get("tool") or "")) else None


def _is_job(pid: int, started: float, tool: str) -> bool:
    try:
        if sys.platform == "win32":
            at = _win_started(pid)
            return at is not None and abs(at - started) < 30
        done = subprocess.run(["ps", "-o", "command=", "-p", str(pid)], capture_output=True, text=True, timeout=10)
        return done.returncode == 0 and f"-m smtv {tool}" in done.stdout     # `smtv_command`
    except (OSError, subprocess.SubprocessError, ValueError):
        return True     # cannot tell: a living process is taken for the job, never a second job in the same folder


def _win_started(pid: int) -> float | None:
    import ctypes
    kernel = ctypes.windll.kernel32  # type: ignore[attr-defined]
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        times = [ctypes.c_ulonglong() for _ in range(4)]
        if not kernel.GetProcessTimes(handle, *[ctypes.byref(t) for t in times]):
            return None
        return times[0].value / 1e7 - 11644473600          # FILETIME (100 ns since 1601) → Unix seconds
    finally:
        kernel.CloseHandle(handle)


def stop_leftover(pid: int, grace: float = 5.0) -> None:
    """Stops a job left by a gone SMTV, with its group (its ffmpeg and yt-dlp)."""
    from .instance import alive
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=30,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        else:
            os.killpg(pid, signal.SIGTERM)
    except (OSError, subprocess.SubprocessError):
        pass
    end = time.monotonic() + grace
    while alive(pid) and time.monotonic() < end:
        time.sleep(0.1)
    if alive(pid) and sys.platform != "win32":
        try:
            os.killpg(pid, signal.SIGKILL)
        except OSError:
            pass
