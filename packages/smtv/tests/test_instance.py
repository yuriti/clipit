"""One SMTV per data folder (stage 16): the lock `run/instance.lock`, a second server on any port, a lock left by a crash,
a job command from a terminal while SMTV runs and while it does not, another data folder."""
import argparse
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from smtv import desktop, handoff, instance, serve
from smtv import jobs as jobs_module
from smtv.cli import _job_command
from smtv_core.events import read
from smtv_core.tool import JobStart
from test_serve import CHILD, Client, make_tool

# A process that takes the lock of SMTV_HOME as `kind`, says so on stdout, optionally starts a long child, and sleeps.
HOLDER = """
import os, subprocess, sys, time
from smtv import instance
lock = instance.Lock()
ok = lock.take(sys.argv[1], port=int(sys.argv[2]))
if ok and sys.argv[3] == "child":
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    print("child", child.pid, flush=True)
print("took" if ok else "busy", flush=True)
time.sleep(60)
"""


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    monkeypatch.setenv("SMTV_HOME", str(h))
    monkeypatch.delenv(jobs_module.UNDER_SMTV, raising=False)
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)
    return h


def holder_process(kind="server", port=8642, child=False, env=None):
    p = subprocess.Popen([sys.executable, "-c", HOLDER, kind, str(port), "child" if child else "-"], stdout=subprocess.PIPE,
                         text=True, env={**os.environ, **(env or {})})
    lines = [p.stdout.readline().strip()]
    if child:
        lines.append(p.stdout.readline().strip())
    return p, lines


def test_one_holder_at_a_time_and_it_says_who_it_is(home):
    first, second = instance.Lock(), instance.Lock()
    assert instance.holder() is None
    assert first.take("server", port=8650)
    assert not second.take("server", port=8651)                     # even in the same process: another open file
    info = instance.holder()
    assert info["kind"] == "server" and info["port"] == 8650 and info["pid"] == os.getpid()
    assert sys.platform == "win32" or (os.stat(instance.info_file()).st_mode & 0o777) == 0o600   # no POSIX bits on Windows
    first.release()
    assert instance.holder() is None and not instance.info_file().exists() and instance.lock_file().exists()
    assert second.take("server", port=8651)
    second.release()


def test_two_starts_at_once_only_one_wins(home):
    procs = [subprocess.Popen([sys.executable, "-c", HOLDER, "server", str(8700 + i), "-"], stdout=subprocess.PIPE, text=True)
             for i in range(4)]
    try:
        answers = [p.stdout.readline().strip() for p in procs]
        assert sorted(answers) == ["busy", "busy", "busy", "took"]
    finally:
        for p in procs:
            p.kill()
            p.wait()


@pytest.mark.skipif(sys.platform == "win32", reason="SIGKILL; and a venv's python.exe on Windows starts the real one as a child, so pids differ")
def test_a_lock_left_by_a_crash_is_free_at_once_even_with_its_jobs_still_running(home):
    p, lines = holder_process(child=True)
    child_pid = int(lines[0].split()[1])
    try:
        assert lines[1] == "took" and instance.holder()["pid"] == p.pid
        p.send_signal(signal.SIGKILL)                               # a crash: nobody releases anything
        p.wait()
        assert instance.holder() is None                            # the system let go; the child holds nothing
        lock = instance.Lock()
        assert lock.take("server", port=8642)
        lock.release()
    finally:
        os.kill(child_pid, signal.SIGKILL)


def test_another_data_folder_is_another_smtv(home, tmp_path):
    p, lines = holder_process(env={"SMTV_HOME": str(tmp_path / "docker-home")})
    try:
        assert lines == ["took"]
        lock = instance.Lock()
        assert lock.take("server", port=8642)                       # this folder is free
        lock.release()
    finally:
        p.kill()
        p.wait()


def test_a_second_server_on_another_port_brings_the_first_forward_and_quits(home):
    p, _ = holder_process(port=8642)
    shown, opened = [], []
    try:
        lock = instance.Lock()
        code = desktop.claim(8766, lock, show=lambda port: shown.append(port) or True, opener=opened.append)
        assert code == 0 and shown == [8642] and not opened and not lock.held
        code = desktop.claim(8766, lock, show=lambda port: False, opener=opened.append)   # no window there: its page
        assert code == 0 and opened == [serve.launch_url(8642)]
    finally:
        p.kill()
        p.wait()


def test_smtv_does_not_open_while_a_terminal_job_holds_the_folder(home):
    p, _ = holder_process(kind="job")
    said = []
    try:
        assert desktop.claim(8642, instance.Lock(), say=said.append, lang="ru") == 2
        assert "в терминале идёт задание" in said[0]
    finally:
        p.kill()
        p.wait()


def test_smtv_serve_on_another_port_does_not_start_a_second_server(home, capsys):
    lock = instance.Lock()
    assert lock.take("server", port=8642)
    try:
        assert serve.serve([], [], port=0, open_browser=False) == 0
        assert "already running on this data folder" in capsys.readouterr().out
    finally:
        lock.release()


def test_run_app_with_the_lock_taken_starts_no_window(home):
    lock = instance.Lock()
    assert lock.take("server", port=8642)
    made = []
    try:
        code = desktop.run_app([], [], port=0, log=False, window_factory=lambda *a: made.append(a), opener=lambda url: None)
        assert code == 0 and made == []
    finally:
        lock.release()


# --- job commands typed in a terminal -----------------------------------------------------------------------

def demo_tool(root: Path):
    tool = make_tool(root)
    tool.page.command_job = lambda args: JobStart(root / args.job, ["0.3", "0", "done"], echo=lambda e: print("event", e["type"]))
    return tool


def test_without_smtv_the_command_runs_itself_under_the_lock(home, tmp_path):
    tool = demo_tool(tmp_path / "jobs")
    seen = {}

    def func(args, tools, broken):
        seen["holder"] = instance.holder()
        return 0
    args = argparse.Namespace(job="x", func=func)
    assert handoff.run_command(tool, tool.page.command_job(args), args, [tool], []) == 0
    assert seen["holder"]["kind"] == "job" and seen["holder"]["job"] == "x" and instance.holder() is None


def test_a_second_terminal_job_waits_for_the_first(home, tmp_path, capsys):
    tool = demo_tool(tmp_path / "jobs")
    first = instance.Lock()
    assert first.take("job", job="first")
    ran = []
    args = argparse.Namespace(job="x", func=lambda a, t, b: ran.append(time.monotonic()) or 0)
    threading.Timer(0.5, first.release).start()
    t0 = time.monotonic()
    assert handoff.run_command(tool, tool.page.command_job(args), args, [tool], [], wait=0.1) == 0
    assert ran and ran[0] - t0 >= 0.4 and "Waiting: another job runs" in capsys.readouterr().out


def test_with_smtv_open_the_terminal_job_goes_to_its_queue_and_is_followed(home, tmp_path, capsys):
    root = tmp_path / "jobs"
    root.mkdir()
    tool = demo_tool(root)
    runner = jobs_module.Runner(lambda name, args: [sys.executable, "-c", CHILD, *args])
    app = serve.App([tool], [], runner)
    srv = serve.make_server(app, port=0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    lock = instance.Lock()
    assert lock.take("server", port=port)
    desktop.write_session(port, app.token)
    c = Client(port, app.token)
    try:
        c.request("POST", "/api/tools/demo/jobs", {"source": "busy", "seconds": 0.6, "mode": "done"})   # the window's job
        ran = []
        args = argparse.Namespace(job="from-terminal", func=lambda *a: ran.append(1) or 0)
        code = handoff.run_command(tool, tool.page.command_job(args), args, [tool], [])
        out = capsys.readouterr().out
        assert code == 0 and ran == []                                      # it did not run here
        assert "SMTV is running: the job went to it" in out and "place 1 of 1" in out and "«a stream»" in out
        assert "event stage" in out and "event done" in out                 # its events, printed here as they came
        events = read(root / "from-terminal")
        assert [e["type"] for e in events] == ["queued", "stage", "done"] and events[0]["data"]["by"] == "terminal"
        assert c.request("GET", "/api/jobs/demo/from-terminal")[1]["status"] == "done"
    finally:
        app.stopping.set()
        runner.stop_all()
        srv.shutdown()
        srv.server_close()
        lock.release()


def test_a_terminal_job_outside_the_data_folder_is_not_handed_over(home, tmp_path, capsys):
    tool = demo_tool(tmp_path / "jobs")
    spec = JobStart(tmp_path / "elsewhere" / "x", ["1"])
    assert handoff.hand_over(tool, spec, {"kind": "server", "port": 8642, "pid": 1}) == 2
    assert "only in its own data folder" in capsys.readouterr().out


def test_jobs_smtv_started_run_as_they_are_and_non_jobs_too(home, tmp_path, monkeypatch):
    tool = demo_tool(tmp_path / "jobs")
    args = argparse.Namespace(command="demo", job="x")
    assert _job_command(args, [tool])[1].folder == tmp_path / "jobs" / "x"
    monkeypatch.setenv(jobs_module.UNDER_SMTV, str(os.getpid()))
    assert _job_command(args, [tool]) is None                    # SMTV's own child: under SMTV's lock already
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    monkeypatch.setenv(jobs_module.UNDER_SMTV, str(dead.pid))
    assert _job_command(args, [tool]) is not None                # a value left in a shell by a gone SMTV is not enough
    monkeypatch.delenv(jobs_module.UNDER_SMTV)
    assert _job_command(argparse.Namespace(command="list"), [tool]) is None
    tool.page.command_job = lambda a: None                       # `smtv demo set …`: not a job
    assert _job_command(args, [tool]) is None


def test_a_look_at_the_lock_at_the_moment_of_a_start_does_not_turn_smtv_away(home, monkeypatch):
    lock, tries = instance.Lock(), []
    real = lock.take
    monkeypatch.setattr(lock, "take", lambda *a, **k: (tries.append(1), len(tries) > 1 and real(*a, **k))[1])   # the first take loses to a look
    assert desktop.claim(8642, lock) is None and len(tries) == 2
    lock.release()


def test_following_a_request_deleted_in_smtv_says_so(home, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(handoff, "_call", lambda *a, **k: (404, {"error": "no_job"}))
    assert handoff.follow(1, "demo", {"status": "running", "last": 0}, tmp_path, every=0) == 1
    assert "deleted in SMTV" in capsys.readouterr().out
