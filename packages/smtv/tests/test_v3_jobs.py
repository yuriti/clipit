"""В3: a stopped job takes what it runs with it (A3), its end is never lost (B7), «Stop» after the end keeps «done» (B18),
quitting puts the running job first in the queue (B30)."""
import os
import sys
import time

import pytest

from smtv import jobs
from smtv_core.events import Journal, contract, read

posix_only = pytest.mark.skipif(sys.platform == "win32", reason="process groups and SIGTERM are POSIX")


def wait_for(fn, timeout=10.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if fn():
            return True
        time.sleep(0.05)
    raise AssertionError("timed out")


def gone(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    try:          # a zombie of ours is as good as gone
        return os.waitpid(pid, os.WNOHANG)[0] == pid
    except ChildProcessError:
        return False


JOB = """
import sys, time
from pathlib import Path
from smtv.jobs import as_job
from smtv_core import proc
as_job()
pidfile = sys.argv[1]
proc.run([sys.executable, "-c", "import os, sys, time; open(sys.argv[1], 'w').write(str(os.getpid())); time.sleep(60)", pidfile], 120)
"""


@posix_only
def test_stopping_a_job_stops_the_program_it_runs_too(tmp_path):
    pidfile = tmp_path / "child.pid"
    runner = jobs.Runner(lambda tool, args: [sys.executable, "-c", JOB, str(pidfile)])
    runner.start("demo", tmp_path / "job", [])
    wait_for(lambda: pidfile.exists() and pidfile.read_text(encoding="utf-8"))
    child = int(pidfile.read_text(encoding="utf-8"))
    assert runner.cancel("demo", "job")
    wait_for(lambda: gone(child))          # before: ffmpeg in its own session outlived the job and kept writing


def test_a_job_ends_when_the_smtv_that_started_it_is_gone():
    ended = []
    alive = iter([True, True, False])
    jobs._watch_owner(123, every=0, alive=lambda pid: next(alive), end=lambda: ended.append(1))
    assert ended == [1]


def test_as_job_does_nothing_outside_smtv(monkeypatch):
    monkeypatch.delenv(jobs.UNDER_SMTV, raising=False)
    import signal
    before = signal.getsignal(signal.SIGTERM)
    jobs.as_job()
    assert signal.getsignal(signal.SIGTERM) is before


def test_stop_right_after_the_end_keeps_done(tmp_path):
    script = ("from pathlib import Path; from smtv_core.events import Journal\n"
              "with Journal(Path.cwd(), tool='demo', subscribers=[]) as j: j.emit('done', stage='analysis', file='clips.json')")
    runner = jobs.Runner(lambda tool, args: [sys.executable, "-c", script])
    run = runner.start("demo", tmp_path / "job", [])
    run.process.wait(20)
    runner.cancel("demo", "job")           # the click came while the job was saying «done»
    run.finished.wait(10)
    assert [e["type"] for e in read(tmp_path / "job")][-1] == "done"
    assert jobs.status(tmp_path / "job", None) == jobs.DONE


def test_a_broken_journal_after_the_end_is_written_down_not_lost(tmp_path, monkeypatch):
    recorded = []
    import smtv_core.crash as crash
    monkeypatch.setattr(crash, "record", lambda e, **kw: recorded.append((type(e).__name__, kw.get("stage"))))
    monkeypatch.setattr(jobs.Journal, "emit", lambda self, *a, **k: (_ for _ in ()).throw(OSError(28, "No space left on device")))
    runner = jobs.Runner(lambda tool, args: [sys.executable, "-c", "import sys; sys.exit(3)"])
    finished = []
    runner.on_finished = finished.append
    run = runner.start("demo", tmp_path / "job", [])
    assert run.finished.wait(20)
    assert recorded == [("OSError", "job watch")] and finished == [run]      # the queue still goes on


def test_quitting_puts_the_running_job_first_in_the_queue(tmp_path):
    runner = jobs.Runner(lambda tool, args: [sys.executable, "-c", "import time; time.sleep(30)"])
    Journal(tmp_path / "waiting", tool="demo", subscribers=[]).emit("queued", by="page", position=1)
    runner.start("demo", tmp_path / "job", [])
    runner.stop_all()                      # quit or «Update now»
    last = read(tmp_path / "job")[-1]
    assert last["type"] == "queued" and last["data"] == {"by": "restart", "first": True}
    assert contract.validate(last) == [] and contract.undeclared(last) == []
    assert jobs.state(tmp_path / "job", None) == (jobs.QUEUED_STATUS, 0.0)
    assert jobs.state(tmp_path / "waiting", None)[1] > 0                  # it waits after the interrupted one



def test_a_job_process_started_by_smtv_turns_on_as_job(monkeypatch, tmp_path):
    """A3: the real entry point (`smtv <tool> …` under SMTV) installs the stop handler — not only a test script."""
    from smtv import cli
    called = []
    monkeypatch.setenv("SMTV_HOME", str(tmp_path))
    monkeypatch.setenv(jobs.UNDER_SMTV, "12345")
    monkeypatch.setattr(jobs, "as_job", lambda: called.append(1))
    monkeypatch.setattr(cli, "first_run_shortcut", lambda command: None)
    cli.main(["list"])
    assert called == [1]
    monkeypatch.delenv(jobs.UNDER_SMTV)
    cli.main(["list"])
    assert called == [1], "a command typed in a terminal is not a job"


@posix_only
def test_a_job_started_through_the_real_command_stops_its_program_on_cancel(tmp_path, monkeypatch):
    """A3 end to end through `cli.main`: the job runs a program in its own session (as proc.run does for ffmpeg);
    «Остановить» must stop that program too, not only the job."""
    pidfile = tmp_path / "child.pid"
    script = tmp_path / "job.py"
    script.write_text(
        "import sys\n"
        "from smtv import cli\n"
        "from smtv_core import proc\n"
        "pidfile = sys.argv[1]\n"
        "def run(*a, **k):\n"
        "    proc.run([sys.executable, '-c', 'import os,sys,time; open(sys.argv[1],\"w\").write(str(os.getpid())); "
        "time.sleep(60)', pidfile], 120)\n"
        "    return 0\n"
        "cli.first_run_shortcut = lambda c: None\n"
        "build = cli.build_parser\n"
        "def patched(tools):\n"
        "    parser = build(tools)\n"
        "    for a in parser._subparsers._group_actions:\n"
        "        a.choices['list'].set_defaults(func=run)\n"
        "    return parser\n"
        "cli.build_parser = patched\n"
        "cli.main(['list'])\n", encoding="utf-8")
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    runner = jobs.Runner(lambda tool, args: [sys.executable, str(script), str(pidfile)])
    runner.start("demo", tmp_path / "job", [])
    wait_for(lambda: pidfile.exists() and pidfile.read_text(encoding="utf-8"))
    child = int(pidfile.read_text(encoding="utf-8"))
    assert runner.cancel("demo", "job")
    wait_for(lambda: gone(child))


def test_a_process_that_cannot_be_looked_at_is_taken_for_the_job(monkeypatch):
    """A3: when `ps` fails, a living process is kept as the job — never a second job started into the same folder."""
    def broken(*a, **k):
        raise OSError("ps is missing")

    monkeypatch.setattr(jobs.subprocess, "run", broken)
    monkeypatch.setattr(jobs.sys, "platform", "linux")
    assert jobs._is_job(99999, 0.0, "vodcut") is True
