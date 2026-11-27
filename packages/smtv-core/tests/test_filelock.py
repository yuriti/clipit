"""B20: one read-change-write at a time between SMTV processes (smtv_core.filelock)."""
import subprocess
import sys
import time

import pytest

from smtv_core import filelock

PROBE = ("import fcntl, sys\nf = open(sys.argv[1], 'a+b')\n"
         "try:\n    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB); print('got')\nexcept OSError:\n    print('busy')\n")
HOLD = ("import sys, time\nfrom smtv_core import filelock\nf = filelock.file_lock(__import__('pathlib').Path(sys.argv[1]))\n"
        "print('held', flush=True)\ntime.sleep(float(sys.argv[2]))\n")

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="the probe uses fcntl")


def probe(path) -> str:
    return subprocess.run([sys.executable, "-c", PROBE, str(path)], capture_output=True, text=True, timeout=30).stdout.strip()


def test_the_lock_is_reentrant_and_keeps_other_processes_out(tmp_path):
    path = tmp_path / "run" / "x.lock"
    lock = filelock.ProcessLock(lambda: path, "x", timeout=5)
    with lock:
        started = time.monotonic()
        with lock:                                   # the same thread again: no wait on its own lock
            assert time.monotonic() - started < 0.5
            assert probe(path) == "busy"
        assert probe(path) == "busy"                 # still held until the outermost exit
    assert probe(path) == "got"


def test_a_lock_held_too_long_is_said_and_passed_or_refused_when_strict(tmp_path, capsys):
    path = tmp_path / "x.lock"
    holder = subprocess.Popen([sys.executable, "-c", HOLD, str(path), "10"], stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "held"
        started = time.monotonic()
        with filelock.ProcessLock(lambda: path, "settings", timeout=0.3):
            assert 0.25 < time.monotonic() - started < 5
        assert "settings is locked by another Clip It! process for too long" in capsys.readouterr().err
        with pytest.raises(filelock.LockTimeout):
            with filelock.ProcessLock(lambda: path, "keys", timeout=0.3, strict=True):
                pass
    finally:
        holder.kill()
        holder.wait()


def test_a_failed_entry_leaves_the_lock_usable(tmp_path):
    calls = []

    def where():
        calls.append(1)
        if len(calls) == 1:
            raise OSError("no folder yet")
        return tmp_path / "x.lock"
    lock = filelock.ProcessLock(where, "x", timeout=1)
    with pytest.raises(OSError):
        with lock:
            pass
    with lock:
        assert lock._depth == 1
    assert lock._depth == 0 and lock._file is None
