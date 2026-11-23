"""One SMTV per data folder (stage 16).

`<SMTV home>/run/instance.lock` is held with the system's own file lock — `flock` on macOS and Linux, `msvcrt.locking`
on Windows — for as long as the process that took it lives. The system lets go of it when that process ends, even when it
crashes or is killed, so a lock file left behind never blocks the next start. The file itself is never removed (removing
a locked file would let a second process lock a new file of the same name). Who holds it is written beside it, in
`run/instance.json`: the process id, the kind (`server` or `job`), the port of a server, the job of a terminal command.

Who takes it:
- a server (`smtv app`, `smtv serve`). A second server on the same data folder, on any port, does not start: it brings
  the first one forward and quits;
- a job command typed in a terminal (`smtv vodcut run …`) while no SMTV runs: it works by itself under the lock. While
  SMTV runs, the command hands its job over to SMTV instead (`handoff.py`), into SMTV's queue.

The jobs SMTV starts itself run under SMTV's lock: their environment carries `jobs.UNDER_SMTV`.
Another data folder (`SMTV_HOME`, a Docker container) is another SMTV with a lock of its own: that is allowed.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from smtv_core import paths

SERVER, JOB = "server", "job"


def lock_file(home: Path | None = None) -> Path:
    return (home or paths.home()) / "run" / "instance.lock"


def info_file(home: Path | None = None) -> Path:
    return (home or paths.home()) / "run" / "instance.json"


def _try_lock(f) -> bool:
    """The system lock on an open file, without waiting. False: another process (or another open file) holds it."""
    if sys.platform == "win32":
        import msvcrt
        try:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)   # one byte at the start; the file may be empty
            return True
        except OSError:
            return False
    import fcntl
    try:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False


def _unlock(f) -> None:
    if sys.platform == "win32":
        import msvcrt
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


class Lock:
    """The data folder's lock, held by this process from `take` until `release` or the process's end."""

    def __init__(self, home: Path | None = None):
        self.home = home or paths.home()
        self.path = lock_file(self.home)
        self._f = None
        self.info: dict = {}

    @property
    def held(self) -> bool:
        return self._f is not None

    def take(self, kind: str, **info) -> bool:
        """True: this process holds the lock now and has said who it is. False: someone else holds it."""
        if self._f is not None:
            return True
        self.path.parent.mkdir(parents=True, exist_ok=True)
        f = open(self.path, "a+b")  # noqa: SIM115 — stays open as long as the lock is held; never inherited by children
        if not _try_lock(f):
            f.close()
            return False
        self._f = f
        self.info = {"pid": os.getpid(), "kind": kind, "started": round(time.time(), 3), **info}
        try:
            _write_private(info_file(self.home), self.info)
        except OSError as e:     # the lock is what keeps a second SMTV out; without the note it only cannot say who
            print(f"instance: {info_file(self.home)} not written: {e}", file=sys.stderr)
        return True

    def update(self, **info) -> None:
        """More about the holder once known (the port a server got)."""
        if self._f is None:
            return
        self.info.update(info)
        try:
            _write_private(info_file(self.home), self.info)
        except OSError as e:
            print(f"instance: {info_file(self.home)} not written: {e}", file=sys.stderr)

    def release(self) -> None:
        if self._f is None:
            return
        try:
            if read_info(self.home).get("pid") == os.getpid():
                info_file(self.home).unlink()
        except OSError:
            pass
        try:
            _unlock(self._f)
        except OSError:
            pass                  # closing the file lets go of it anyway
        self._f.close()
        self._f = None


def read_info(home: Path | None = None) -> dict:
    try:
        data = json.loads(info_file(home).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def holder(home: Path | None = None, wait: float = 2.0) -> dict | None:
    """Who holds the lock of this data folder: its note ({} when it has not written one yet), or None when nobody does.
    A holder that has just taken the lock writes its note a moment later: wait up to `wait` seconds for it. The look takes
    the lock for an instant, so a `take` at that very instant fails: callers that get None try `take` again (`claim`)."""
    path = lock_file(home)
    if not path.exists():
        return None
    with open(path, "a+b") as f:              # a look only: it writes no note of its own
        if _try_lock(f):
            try:
                _unlock(f)
            except OSError:
                pass
            return None
    deadline = time.monotonic() + wait
    while True:
        info = read_info(home)
        if info.get("kind") in (SERVER, JOB) and alive(info.get("pid")):
            return info
        if time.monotonic() >= deadline:
            return info
        time.sleep(0.1)


def alive(pid) -> bool:
    """Whether a process with this id runs now."""
    if not isinstance(pid, int) or pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        kernel = ctypes.windll.kernel32  # type: ignore[attr-defined]
        handle = kernel.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(code))) and code.value == 259   # STILL_ACTIVE
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _write_private(path: Path, data: dict) -> None:
    """Readable only by this user (the note sits next to the session token), whole or not at all."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, path)
