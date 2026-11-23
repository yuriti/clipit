"""«Fix» from the window (stage 24): runs a check's recipe and keeps its output for the window's console.

Only recipes built into SMTV run here (`smtv_core.checks.Recipe`): the window names a check, never a command, and the
server builds the checks again to find that check's recipe. A recipe runs as a program with its arguments, without a
shell; its output is kept line by line for the window's console (`/api/fixes/<id>/events`), and «Stop» stops it with
everything it started. One fix at a time, and none while a request runs (a request may be using that ffmpeg or that
model right now). A recipe that needs administrator rights is never run here: SMTV writes it into a small script in its
own folder and opens a terminal with it, where the person sees it and runs it.

Also here: what the window can do for a check that has no recipe — open SMTV's folder, and clear SMTV's cache (the
pieces of video and the work files of requests that are not running; they are fetched or made again when needed).
"""
from __future__ import annotations

import importlib
import os
import secrets
import shlex
import shutil
import stat
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from smtv_core import checks, paths, proc
from smtv_core.checks import WINGET_CONSENT, Check, Recipe  # noqa: F401 — WINGET_CONSENT: the text, here as before

RUNNING, DONE, FAILED, STOPPED, OPENED = "running", "done", "failed", "stopped", "opened"
MAX_LINES = 4000          # the console keeps the last lines of a long output
KEEP_RUNS = 20
TIME_LIMIT_S = 45 * 60    # a recipe that hangs (waits for input, a stalled download) is stopped after this


class FixError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


@dataclass
class FixRun:
    id: str
    check: str
    recipe: Recipe
    status: str = RUNNING
    code: int | None = None
    started: float = field(default_factory=time.time)
    ended: float | None = None
    lines: list[tuple[int, str]] = field(default_factory=list)
    count: int = 0                       # lines ever written; the window asks for the ones after its last
    stop_asked: bool = False
    process: subprocess.Popen | None = None

    def add(self, text: str) -> None:
        self.count += 1
        self.lines.append((self.count, text))
        if len(self.lines) > MAX_LINES:
            del self.lines[: len(self.lines) - MAX_LINES]

    def state(self, after: int = 0) -> dict:
        return {"id": self.id, "check": self.check, "status": self.status, "code": self.code, "started": self.started,
                "ended": self.ended, "recipe": {**self.recipe.public(), "consent": consent(self.recipe)}, "last": self.count,
                "lines": [{"n": n, "text": t} for n, t in self.lines if n > after]}


def _child_env() -> dict:
    env = dict(os.environ)
    env.update({"PYTHONUNBUFFERED": "1", "HOMEBREW_NO_ENV_HINTS": "1", "NONINTERACTIVE": "1"})
    return env


def _new_session() -> dict:
    """Its own group («Stop» ends everything it started) and, on Windows, no black console window."""
    return proc.group()


def consent(recipe: Recipe) -> str | None:
    """What the person agrees to by pressing «Исправить»: the recipe knows it, so the window shows it before the press."""
    return recipe.consent()


def _oem() -> str:
    """The console code page of this Windows (cp866 on a Russian one): winget writes in it when its output is piped."""
    try:
        import ctypes
        return f"cp{ctypes.windll.kernel32.GetOEMCP()}"
    except Exception:  # noqa: BLE001 — not Windows
        return "utf-8"


def decode(raw: bytes) -> str:
    """A line of a recipe's output: UTF-8 when it is, otherwise the console code page (winget, Windows tools)."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode(_oem() if sys.platform == "win32" else "latin-1", errors="replace")


# --- a terminal for what needs administrator rights ---------------------------------------------------------------

def _script(recipe: Recipe, folder: Path) -> Path:
    """The recipe as a small script in SMTV's folder: it shows the command, runs it, and waits for Enter."""
    folder.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        path = folder / f"{recipe.id}.cmd"
        note = consent(recipe)
        path.write_text("@echo off\r\nchcp 65001 >nul\r\n" + (f"echo {note}\r\n" if note else "") +
                        "echo SMTV: " + recipe.line().replace("%", "%%") + "\r\n" +
                        subprocess.list2cmdline(recipe.argv) + "\r\npause\r\n", encoding="utf-8")
    else:
        path = folder / (f"{recipe.id}.command" if sys.platform == "darwin" else f"{recipe.id}.sh")
        path.write_text("#!/bin/bash\nprintf '%s\\n\\n' " + shlex.quote("SMTV: " + recipe.line()) + "\n" + shlex.join(recipe.argv) +
                        "\nprintf '\\n'\nread -r -p 'Press Enter to close this window. ' _\n", encoding="utf-8")
        path.chmod(stat.S_IRWXU)
    return path


def open_terminal(recipe: Recipe, folder: Path | None = None) -> tuple[bool, str]:
    """Opens a terminal running the recipe's script. (opened, what to tell the person)."""
    if checks.in_docker():
        return False, "in Docker there is no terminal to open: run the command on the host"
    try:
        script = _script(recipe, folder or paths.home() / "fix")
        if sys.platform == "darwin":
            done = subprocess.run(["open", "-a", "Terminal", str(script)], capture_output=True, timeout=30)
            return (done.returncode == 0, "Terminal opened" if done.returncode == 0 else "Terminal did not open")
        if sys.platform == "win32":
            subprocess.Popen(["cmd", "/c", "start", "", "cmd", "/k", str(script)], **proc.hidden())   # only the new window shows
            return True, "a command window opened"
        for term, flag in (("x-terminal-emulator", ["-e"]), ("gnome-terminal", ["--"]), ("konsole", ["-e"]), ("xterm", ["-e"])):
            if shutil.which(term):
                subprocess.Popen([term, *flag, "bash", str(script)])
                return True, f"{term} opened"
    except (OSError, subprocess.SubprocessError) as e:
        return False, f"the terminal did not open: {type(e).__name__}: {e}"
    return False, "no terminal found: run the command yourself"


# --- the runner ---------------------------------------------------------------------------------------------------

class Fixes:
    def __init__(self, on_done: Callable[[], None] = lambda: None, busy: Callable[[], bool] = lambda: False,
                 popen: Callable[..., subprocess.Popen] = subprocess.Popen, terminal: Callable[[Recipe], tuple[bool, str]] = open_terminal):
        self.on_done, self.busy, self.popen, self.terminal = on_done, busy, popen, terminal
        self.runs: dict[str, FixRun] = {}
        self.lock = threading.RLock()
        self.time_limit_s = TIME_LIMIT_S

    def running(self) -> FixRun | None:
        with self.lock:
            return next((r for r in self.runs.values() if r.status == RUNNING), None)

    def get(self, fid: str) -> FixRun:
        with self.lock:
            run = self.runs.get(fid)
        if run is None:
            raise FixError(404, "no_fix", "no such fix")
        return run

    def start(self, check: Check) -> dict:
        recipe = check.recipe
        if check.status == checks.OK or recipe is None:
            raise FixError(409, "nothing_to_fix", "this check has nothing to fix now")
        with self.lock:
            if any(r.status == RUNNING for r in self.runs.values()):
                raise FixError(409, "fixing", "another fix is running: wait for it to end")
            if self.busy():
                raise FixError(409, "busy", "a request is running: fix this when it ends")
            run = FixRun(secrets.token_hex(6), check.id or check.name, recipe)
            self.runs[run.id] = run
            for old in [k for k, r in self.runs.items() if r.status != RUNNING][:-KEEP_RUNS]:
                self.runs.pop(old, None)
        if recipe.admin:
            opened, said = self.terminal(recipe)
            run.add(said)
            self._end(run, OPENED if opened else FAILED, None)
            return run.state()
        note = consent(recipe)
        if note:
            run.add(note)
        run.add("$ " + recipe.line())
        try:
            with self.lock:              # «Stop» waits for the process to exist: a click right after «Run» is never lost
                # bytes, decoded line by line: winget writes in the console code page, not UTF-8
                run.process = self.popen(recipe.argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                         env=_child_env(), **_new_session())
        except OSError as e:
            run.add(f"did not start: {type(e).__name__}: {e}")
            self._end(run, FAILED, None)
            return run.state()
        threading.Thread(target=self._read, args=(run,), name=f"fix {recipe.id}", daemon=True).start()
        threading.Thread(target=self._limit, args=(run,), name=f"fix {recipe.id} limit", daemon=True).start()
        return run.state()

    def _limit(self, run: FixRun) -> None:
        deadline = time.monotonic() + self.time_limit_s
        while run.status == RUNNING and time.monotonic() < deadline:
            time.sleep(min(1.0, max(0.01, deadline - time.monotonic())))
        if run.status == RUNNING:
            with self.lock:
                run.add(f"stopped: it ran longer than {round(self.time_limit_s / 60)} min")
            self._kill(run)

    def _read(self, run: FixRun) -> None:
        p = run.process
        try:
            for raw in iter(p.stdout.readline, b""):
                text = decode(raw) if isinstance(raw, bytes) else raw
                if not text:
                    break
                for part in text.replace("\r", "\n").split("\n"):    # progress bars rewrite one line with \r
                    if part.strip():
                        with self.lock:
                            run.add(part.rstrip()[:2000])
            code = p.wait()
        except Exception as e:  # noqa: BLE001 — the run ends as failed, with the reason in its own console
            with self.lock:
                run.add(f"{type(e).__name__}: {e}")
            self._kill(run)                  # nothing watches it any more: it must not go on unseen
            try:
                code = p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                code = None
        self._end(run, STOPPED if run.stop_asked else DONE if code == 0 else FAILED, code)

    def _end(self, run: FixRun, status: str, code: int | None) -> None:
        """What the fix changed is taken in first (a new package, a new ffmpeg on PATH, the check dropped), and only then
        the window sees it ended: its «check again» never meets the old result."""
        importlib.invalidate_caches()        # a package installed just now (yt-dlp) is found without a restart
        try:
            checks.use_ffmpeg()              # a new ffmpeg first on PATH for the jobs started from now on
        except Exception as e:  # noqa: BLE001 — the check after the fix says what is wrong
            print(f"fix {run.recipe.id}: ffmpeg lookup: {type(e).__name__}: {e}")
        self._done_hook(run)
        with self.lock:
            if status == FAILED and code is not None:
                run.add(f"ended with code {code}")
            run.status, run.code, run.ended = status, code, time.time()
        self._done_hook(run)                 # again: a check made while it ran still said «fixing»
        print(f"fix {run.recipe.id}: {status}" + (f" (code {code})" if code is not None else ""))

    def _done_hook(self, run: FixRun) -> None:
        try:
            self.on_done()
        except Exception as e:  # noqa: BLE001 — the window still learns that the fix ended
            print(f"fix {run.recipe.id}: after the fix: {type(e).__name__}: {e}")

    def _kill(self, run: FixRun) -> None:
        """Stops the recipe and what it started, only while it has not ended (its process id is not reused yet)."""
        with self.lock:
            p = run.process
            if p is not None and p.poll() is None:
                proc._kill(p)

    def stop(self, fid: str) -> dict:
        run = self.get(fid)
        with self.lock:
            if run.status == RUNNING and run.process is not None:
                run.stop_asked = True
                self._kill(run)
        return run.state()


# --- SMTV's folder and cache --------------------------------------------------------------------------------------

CACHE_DIRS = ("pieces", "recap/pieces", "recap/work")


def cache_paths(job_folders: list[Path]) -> list[Path]:
    """What can go: pieces of video and work files of these requests (made again when needed), and unfinished downloads."""
    out = []
    for folder in job_folders:
        out += [folder / d for d in CACHE_DIRS if (folder / d).is_dir()]
        try:
            out += [p for p in folder.rglob("*.part") if p.is_file()]
        except OSError:
            pass
    return out


def size_of(path: Path) -> int:
    """Bytes under a path; what cannot be read counts as nothing, never an error."""
    try:
        if path.is_file():
            return path.stat().st_size
        total = 0
        for p in path.rglob("*"):
            try:
                if p.is_file():
                    total += p.stat().st_size
            except OSError:
                pass
        return total
    except OSError:
        return 0


def cache_size(job_folders: list[Path]) -> int:
    return sum(size_of(p) for p in cache_paths(job_folders))


def clear_cache(job_folders: list[Path], busy: Callable[[Path], bool] = lambda folder: False) -> tuple[int, list[str]]:
    """(bytes freed, what could not be removed). `busy(folder)` is asked again right before each request's files go: a
    request that started meanwhile keeps them."""
    freed, left = 0, []
    for p in [q for f in job_folders if not busy(f) for q in cache_paths([f])]:
        size = size_of(p)
        try:
            shutil.rmtree(p) if p.is_dir() else p.unlink()
            freed += size
        except OSError as e:
            left.append(f"{p.name}: {e.strerror or e}")
    return freed, left


def open_folder(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        if sys.platform == "darwin":
            return subprocess.run(["open", str(path)], capture_output=True, timeout=15).returncode == 0
        if sys.platform == "win32":
            os.startfile(str(path))  # noqa: S606 — SMTV's own folder
            return True
        return subprocess.run(["xdg-open", str(path)], capture_output=True, timeout=15).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False
