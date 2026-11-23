"""One read-change-write at a time, between threads of a process and between SMTV processes (the window, a job,
`smtv model` in a terminal): settings.json and the keys file (B20). Reentrant in a thread; the file lock is taken at the
outermost level only. fcntl.flock on a Mac and Linux, msvcrt.locking on Windows: both are released by the system when
the process dies, so a crashed SMTV never leaves a lock behind.
"""
from __future__ import annotations

import errno
import os
import sys
import threading
import time
from pathlib import Path
from typing import Callable


class ProcessLock:
    """`with lock:` — this thread, then this computer. `where()` is the lock file, asked on every outermost entry (the
    SMTV folder may change between tests)."""

    def __init__(self, where: Callable[[], Path], what: str, timeout: float = 30.0, strict: bool = False):
        # strict: a lock not had in `timeout` raises LockTimeout instead of going on without it (the keys file: a lost
        # key is worse than «try again»)
        self.where, self.what, self.timeout, self.strict = where, what, timeout, strict
        self._thread = threading.RLock()
        self._depth = 0
        self._file = None

    def __enter__(self):
        self._thread.acquire()
        self._depth += 1
        if self._depth == 1:
            try:
                self._file = file_lock(self.where(), self.what, self.timeout, self.strict)
            except BaseException:
                self._depth -= 1
                self._thread.release()
                raise
        return self

    def __exit__(self, *exc):
        self._depth -= 1
        try:
            if self._depth == 0 and self._file is not None:
                f, self._file = self._file, None
                file_unlock(f)
        finally:
            self._thread.release()
        return False


class LockTimeout(OSError):
    """Another SMTV process held the lock for the whole timeout."""


# «held by another process»: the only failure worth waiting for. Anything else (a network folder without locks, no
# rights) will not pass by waiting: said at once, and the work goes on without the lock.
BUSY = {errno.EAGAIN, errno.EWOULDBLOCK, errno.EACCES, getattr(errno, "EDEADLOCK", errno.EDEADLK)}


def file_lock(path: Path, what: str = "the file", timeout: float = 30.0, strict: bool = False):
    """The open lock file, locked. A process that hangs holding it for `timeout`: said in the log, and this one goes on
    rather than freeze the window — or, `strict`, raises LockTimeout."""
    path.parent.mkdir(parents=True, exist_ok=True)
    f = open(path, "a+b")
    deadline = time.monotonic() + timeout
    while True:
        try:
            if os.name == "nt":
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined]
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return f
        except OSError as e:
            if e.errno not in BUSY:
                print(f"smtv: {what} cannot be locked here ({type(e).__name__}: {e}); going on without the lock", file=sys.stderr)
                return f
            if time.monotonic() > deadline:
                if strict:
                    f.close()
                    raise LockTimeout(f"{what} is held by another SMTV process") from e
                print(f"smtv: {what} is locked by another SMTV process for too long; going on", file=sys.stderr)
                return f
            time.sleep(0.05)


def file_unlock(f) -> None:
    try:
        if os.name == "nt":
            import msvcrt
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except OSError:
        pass
    finally:
        f.close()
