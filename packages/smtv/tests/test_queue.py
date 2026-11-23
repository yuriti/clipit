"""SMTV's queue (stage 16): a request for a busy tool waits with its place, starts by itself when the running one ends,
pauses or fails, outlives a restart, leaves the queue on cancel; a job command from a terminal joins it."""
import json
import sys
import threading

import pytest

from smtv import jobs as jobs_module
from smtv import phone, serve
from smtv_core.events import Journal, contract, read
from test_serve import CHILD, Client, isolated, make_tool, wait_for  # noqa: F401 — isolated is an autouse fixture


def start_server(root, launcher=None):
    tool = make_tool(root)
    runner = jobs_module.Runner(launcher or (lambda name, args: [sys.executable, "-c", CHILD, *args]))
    app = serve.App([tool], [], runner)
    srv = serve.make_server(app, port=0)
    threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    return srv, Client(srv.server_address[1], app.token), app


def stop_server(srv, app):
    app.stopping.set()
    app.runner.stop_all()
    srv.shutdown()
    srv.server_close()


@pytest.fixture
def server(tmp_path):
    root = tmp_path / "jobs"
    root.mkdir()
    srv, c, app = start_server(root)
    yield srv, c, root, app
    stop_server(srv, app)


def kinds(folder):
    return [e["type"] for e in read(folder)]


def all_fit_the_contract(folder):
    return all(contract.validate(e) == [] and contract.undeclared(e) == [] for e in read(folder))


def test_a_second_request_waits_with_its_place_and_starts_when_the_first_ends(server):
    _, c, root, app = server
    assert c.request("POST", "/api/tools/demo/jobs", {"source": "a", "seconds": 1.0, "mode": "done"})[1]["status"] == "running"
    wait_for(lambda: (root / "a" / "events.jsonl").exists())
    status, b = c.request("POST", "/api/tools/demo/jobs", {"source": "b", "seconds": 30})
    assert status == 201 and b["status"] == "queued"
    assert b["queue"] == {"position": 1, "waiting": 1, "after": {"id": "a", "title": "a stream"}}
    _, cc = c.request("POST", "/api/tools/demo/jobs", {"source": "c", "seconds": 30})
    assert cc["queue"] == {"position": 2, "waiting": 2, "after": {"id": "b", "title": "a stream"}}
    listed = {j["id"]: j for j in c.request("GET", "/api/jobs")[1]}
    assert listed["b"]["queue"]["position"] == 1 and listed["c"]["queue"]["position"] == 2 and "queue" not in listed["a"]
    q = read(root / "b")[-1]
    assert q["type"] == "queued" and q["data"] == {"by": "page", "position": 1, "after": "a"} and all_fit_the_contract(root / "b")
    wait_for(lambda: app.runner.running("demo", "b"))                       # a ended: b started by itself
    assert c.request("GET", "/api/jobs/demo/a")[1]["status"] == "done"
    _, cc = c.request("GET", "/api/jobs/demo/c")
    assert cc["status"] == "queued" and cc["queue"] == {"position": 1, "waiting": 1, "after": {"id": "b", "title": "a stream"}}
    assert app.activity()["running"] == 1 and app._look()["activity"]["queued"] == 1


def test_the_next_one_starts_after_a_failure_or_a_stop_too(server):
    _, c, root, app = server
    c.request("POST", "/api/tools/demo/jobs", {"source": "bad", "seconds": 0.3, "code": 3})
    c.request("POST", "/api/tools/demo/jobs", {"source": "next", "seconds": 30})
    wait_for(lambda: app.runner.running("demo", "next"))
    assert c.request("GET", "/api/jobs/demo/bad")[1]["status"] == "failed"
    c.request("POST", "/api/tools/demo/jobs", {"source": "after", "seconds": 30})
    c.request("POST", "/api/jobs/demo/next/cancel")                         # «Stop now» on the running one
    wait_for(lambda: app.runner.running("demo", "after"))


def test_cancel_takes_a_request_out_of_the_queue_and_it_never_starts(server):
    _, c, root, app = server
    c.request("POST", "/api/tools/demo/jobs", {"source": "a", "seconds": 0.8, "mode": "done"})
    c.request("POST", "/api/tools/demo/jobs", {"source": "b", "seconds": 30})
    c.request("POST", "/api/tools/demo/jobs", {"source": "c", "seconds": 30})
    assert c.request("POST", "/api/jobs/demo/b/cancel", {}, headers={"X-SMTV-Token": None})[0] == 403
    status, b = c.request("POST", "/api/jobs/demo/b/cancel")
    assert status == 200 and b["status"] == "cancelled" and "queue" not in b
    last = read(root / "b")[-1]
    assert last["type"] == "cancelled" and last["data"] == {"by": "user", "stage": "queue"} and all_fit_the_contract(root / "b")
    assert c.request("GET", "/api/jobs/demo/c")[1]["queue"]["position"] == 1          # c moved up
    wait_for(lambda: app.runner.running("demo", "c"))                                 # a ended: c, not b
    assert not app.runner.running("demo", "b") and kinds(root / "b")[-1] == "cancelled"
    assert c.request("POST", "/api/jobs/demo/b/cancel")[0] == 409                      # nothing left to cancel


def test_a_waiting_request_can_be_deleted_and_never_starts(server):
    _, c, root, app = server
    c.request("POST", "/api/tools/demo/jobs", {"source": "a", "seconds": 0.8, "mode": "done"})
    c.request("POST", "/api/tools/demo/jobs", {"source": "gone", "seconds": 30})
    assert c.request("POST", "/api/jobs/demo/gone/delete", {"confirm": "delete"})[1] == {"deleted": True}
    wait_for(lambda: not app.runner.running("demo", "a"))
    assert not (root / "gone").exists() and app.runner.busy("demo") is None


def test_asking_twice_keeps_the_place_and_continue_while_busy_queues(server):
    _, c, root, app = server
    c.request("POST", "/api/tools/demo/jobs", {"source": "a", "seconds": 30})
    c.request("POST", "/api/tools/demo/jobs", {"source": "b", "seconds": 30})
    assert c.request("POST", "/api/tools/demo/jobs", {"source": "b", "seconds": 30})[1]["queue"]["position"] == 1
    assert kinds(root / "b").count("queued") == 1
    assert c.request("POST", "/api/tools/demo/jobs", {"source": "a"})[1]["error"] == "running"
    Journal(root / "old", tool="demo", subscribers=[]).emit("cancelled", by="user")
    (root / "old" / serve.PAGE_RUN).write_text(json.dumps({"tool": "demo", "args": ["30", "0", "events"]}), encoding="utf-8")
    status, old = c.request("POST", "/api/jobs/demo/old/restart")                    # «Continue» while another runs
    assert status == 201 and old["status"] == "queued" and old["queue"]["position"] == 2


def test_the_queue_outlives_a_restart_of_smtv(tmp_path):
    root = tmp_path / "jobs"
    root.mkdir()
    srv, c, app = start_server(root)
    c.request("POST", "/api/tools/demo/jobs", {"source": "a", "seconds": 30})
    c.request("POST", "/api/tools/demo/jobs", {"source": "b", "seconds": 30})
    c.request("POST", "/api/tools/demo/jobs", {"source": "c", "seconds": 30})
    stop_server(srv, app)                                     # quit: a stops and waits first; b and c stay queued
    assert kinds(root / "a")[-1] == "queued" and read(root / "a")[-1]["data"] == {"by": "restart", "first": True}
    assert "cancelled" not in kinds(root / "a")
    assert kinds(root / "b")[-1] == "queued" and kinds(root / "c")[-1] == "queued"
    srv, c, app = start_server(root)
    try:
        assert c.request("GET", "/api/jobs/demo/a")[1]["queue"]["position"] == 1      # B30: the interrupted one first
        assert c.request("GET", "/api/jobs/demo/c")[1]["queue"]["position"] == 3
        app.queue_next()                                      # what `smtv app` and `smtv serve` do once they listen
        assert app.runner.running("demo", "a") and c.request("GET", "/api/jobs/demo/b")[1]["queue"]["position"] == 1
    finally:
        stop_server(srv, app)


def test_quitting_starts_nothing_from_the_queue(server):
    _, c, root, app = server
    c.request("POST", "/api/tools/demo/jobs", {"source": "a", "seconds": 30})
    c.request("POST", "/api/tools/demo/jobs", {"source": "b", "seconds": 30})
    app.runner.stop_all()                                     # quit, update or removal
    assert app.runner.busy("demo") is None and kinds(root / "b")[-1] == "queued"


def test_a_queued_job_that_cannot_start_says_so_and_the_next_one_goes(server):
    _, c, root, app = server
    c.request("POST", "/api/tools/demo/jobs", {"source": "a", "seconds": 0.8, "mode": "done"})
    c.request("POST", "/api/tools/demo/jobs", {"source": "broken", "seconds": 30})
    c.request("POST", "/api/tools/demo/jobs", {"source": "fine", "seconds": 30})
    (root / "broken" / serve.PAGE_RUN).write_text("{not json", encoding="utf-8")
    wait_for(lambda: app.runner.running("demo", "fine"))
    last = read(root / "broken")[-1]
    assert last["type"] == "error" and last["data"]["stage"] == "queue" and "could not start" in last["data"]["message"]
    assert c.request("GET", "/api/jobs/demo/broken")[1]["status"] == "failed" and all_fit_the_contract(root / "broken")


def test_a_queued_job_that_ends_without_a_word_is_not_started_again_and_again(tmp_path):
    root = tmp_path / "jobs"
    root.mkdir()
    srv, c, app = start_server(root, launcher=lambda name, args: [sys.executable, "-c", "import time; time.sleep(float(__import__('sys').argv[1]))", *args])
    try:
        c.request("POST", "/api/tools/demo/jobs", {"source": "a", "seconds": 0.5})
        c.request("POST", "/api/tools/demo/jobs", {"source": "mute", "seconds": 0})
        wait_for(lambda: kinds(root / "mute")[-1] == "error")
        assert kinds(root / "mute") == ["queued", "error"] and app.runner.busy("demo") is None
    finally:
        stop_server(srv, app)


def test_jobs_smtv_starts_know_they_run_under_its_lock(tmp_path):
    root = tmp_path / "jobs"
    root.mkdir()
    code = "import os, pathlib; pathlib.Path('env.txt').write_text(os.environ.get('SMTV_UNDER_SMTV', ''), encoding='utf-8')"
    srv, c, app = start_server(root, launcher=lambda name, args: [sys.executable, "-c", code])
    try:
        c.request("POST", "/api/tools/demo/jobs", {"source": "e"})
        wait_for(lambda: (root / "e" / "env.txt").exists() and (root / "e" / "env.txt").read_text(encoding="utf-8"))
        assert (root / "e" / "env.txt").read_text(encoding="utf-8") == str(__import__("os").getpid())
    finally:
        stop_server(srv, app)


# --- a job command from a terminal, handed over ------------------------------------------------------------------

def test_a_terminal_job_joins_the_queue_only_with_the_token_and_never_from_the_phone(server):
    _, c, root, app = server
    body = {"tool": "demo", "job": "cli", "args": ["30", "0", "events"]}
    assert c.request("POST", "/api/queue", body, headers={"X-SMTV-Token": None})[0] == 403
    assert phone.denied("POST", "/api/queue")
    for bad in ({**body, "job": "../x"}, {**body, "args": "30"}, {**body, "args": []}, {**body, "tool": "nope"}):
        assert c.request("POST", "/api/queue", bad)[0] in (400, 404)
    status, job = c.request("POST", "/api/queue", body)
    assert status == 201 and job["status"] == "running"
    status, second = c.request("POST", "/api/queue", {**body, "job": "cli2"})
    assert second["status"] == "queued" and read(root / "cli2")[-1]["data"]["by"] == "terminal"
    saved = json.loads((root / "cli2" / serve.PAGE_RUN).read_text(encoding="utf-8"))
    assert saved == {"tool": "demo", "args": ["30", "0", "events"], "by": "terminal"}


def test_a_job_page_stream_says_its_place_in_the_queue(server):
    from test_serve import read_sse
    _, c, root, app = server
    c.request("POST", "/api/tools/demo/jobs", {"source": "a", "seconds": 30})
    c.request("POST", "/api/tools/demo/jobs", {"source": "b", "seconds": 30})
    conn, res = c.stream("/api/jobs/demo/b/events")
    try:
        msgs = read_sse(res, lambda m: any(e == "status" for _, e, _ in m))
        st = next(d for _, e, d in msgs if e == "status")
        assert st["status"] == "queued" and st["queue"]["after"]["id"] == "a"
    finally:
        conn.close()


# --- what the silent-failure review found (stage 16) ---------------------------------------------------------------

def test_a_waiting_update_holds_the_queue_and_calling_it_off_lets_it_go_on(server):
    _, c, root, app = server
    c.request("POST", "/api/tools/demo/jobs", {"source": "a", "seconds": 0.5, "mode": "done"})
    c.request("POST", "/api/tools/demo/jobs", {"source": "b", "seconds": 30})
    app.updates.pending = {"action": "update", "tool": None}         # «update when the jobs end»
    wait_for(lambda: not app.runner.running("demo", "a"))
    time_left = __import__("time").monotonic() + 0.5
    while __import__("time").monotonic() < time_left:
        assert not app.runner.running("demo", "b")                   # the update is not pushed back by the queue
    app.updates.cancel()                                             # called off: the next look goes on with the queue
    app._look()
    wait_for(lambda: app.runner.running("demo", "b"))


def test_a_start_the_system_refuses_fails_one_job_not_the_whole_queue(server):
    _, c, root, app = server
    c.request("POST", "/api/tools/demo/jobs", {"source": "a", "seconds": 30})
    c.request("POST", "/api/tools/demo/jobs", {"source": "b", "seconds": 30})
    c.request("POST", "/api/tools/demo/jobs", {"source": "c", "seconds": 30})
    app.runner.launcher = lambda name, args: ["/no/such/python"]
    c.request("POST", "/api/jobs/demo/a/cancel")
    wait_for(lambda: kinds(root / "b")[-1] == "error")
    assert kinds(root / "c")[-1] == "queued" and "could not start" in read(root / "b")[-1]["data"]["message"]
    app._look()                                                      # within the pause: not tried again at once
    assert kinds(root / "c")[-1] == "queued"


def _left_job(*marks):
    """A process like a job an SMTV that crashed left running: its command line names smtv."""
    import subprocess
    import time as _t
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", *marks], start_new_session=True)
    return p, _t.time()


def test_a_job_started_by_an_smtv_that_crashed_is_not_started_twice(server, capsys):
    _, c, root, app = server
    p, started = _left_job("-m", "smtv", "demo")
    try:
        Journal(root / "orphan", tool="demo", subscribers=[]).emit("queued", by="page", position=1)
        (root / "orphan" / serve.PAGE_RUN).write_text(json.dumps({"tool": "demo", "args": ["30", "0", "events"], "by": "page",
                                                                   "started": started + 1, "pid": p.pid}), encoding="utf-8")
        for _ in range(5):                                       # A5: told once, the window is not poked again and again
            app.queue_next("demo")
        assert app.runner.busy("demo") is None and kinds(root / "orphan") == ["queued"]
        assert capsys.readouterr().out.count("still runs as process") == 1
        # A3: «Continue» and «Delete» refuse while it runs; «Stop» stops it
        assert c.request("POST", "/api/jobs/demo/orphan/restart")[1]["error"] == "still_running"
        assert c.request("POST", "/api/jobs/demo/orphan/delete", {"confirm": "delete"})[1]["error"] == "still_running"
        assert c.request("POST", "/api/jobs/demo/orphan/cancel")[0] == 200
        p.wait(10)
        assert kinds(root / "orphan")[-1] == "cancelled"
    finally:
        p.kill()


@pytest.mark.skipif(sys.platform == "win32", reason="Windows knows a job by its start time: this other program started at the same moment")
def test_a_living_process_that_is_not_a_job_does_not_hold_the_request(server):
    _, c, root, app = server
    p, started = _left_job()                                    # the same number now belongs to another program
    try:
        Journal(root / "x", tool="demo", subscribers=[]).emit("queued", by="page", position=1)
        (root / "x" / serve.PAGE_RUN).write_text(json.dumps({"tool": "demo", "args": ["30", "0", "events"], "by": "page",
                                                              "started": started, "pid": p.pid}), encoding="utf-8")
        app.queue_next("demo")
        assert app.runner.running("demo", "x")
    finally:
        p.kill()


def test_the_queue_does_not_spin_while_a_start_waits(server):
    """A5: a queue that cannot start now does not poke the window's look over and over (100 % of a core before)."""
    _, c, root, app = server
    pokes = []
    app.hub.poke = lambda: pokes.append(1)
    Journal(root / "w", tool="demo", subscribers=[]).emit("queued", by="page", position=1)
    (root / "w" / serve.PAGE_RUN).write_text(json.dumps({"tool": "demo", "args": ["30", "0", "events"], "by": "page"}), encoding="utf-8")
    app._queue_pause_until = __import__("time").monotonic() + 60     # after a refused start
    for _ in range(50):
        app._look()
    assert pokes == [] and app._queue_timer is not None and app._queue_timer.is_alive()   # B5: tried again by itself
    app._queue_timer.cancel()


def test_the_queue_goes_on_without_a_window_after_a_pause(server, monkeypatch):
    """B5: after the pause the queue starts by itself, with no window listening (Docker, a minimised window)."""
    _, c, root, app = server
    monkeypatch.setattr(serve, "QUEUE_RETRY_S", 0.2)
    Journal(root / "w", tool="demo", subscribers=[]).emit("queued", by="page", position=1)
    (root / "w" / serve.PAGE_RUN).write_text(json.dumps({"tool": "demo", "args": ["30", "0", "events"], "by": "page"}), encoding="utf-8")
    app._queue_pause_until = __import__("time").monotonic() + 0.1
    app.queue_next("demo")
    wait_for(lambda: app.runner.running("demo", "w"))


def test_nothing_starts_from_the_queue_while_a_fix_or_a_speech_download_runs(server):
    """A18: «Fix» replacing ffmpeg, or a speech model coming into its folder: the queue waits for them."""
    _, c, root, app = server
    Journal(root / "w", tool="demo", subscribers=[]).emit("queued", by="page", position=1)
    (root / "w" / serve.PAGE_RUN).write_text(json.dumps({"tool": "demo", "args": ["30", "0", "events"], "by": "page"}), encoding="utf-8")
    app.fixes.running = lambda: object()
    app.queue_next("demo")
    assert app.runner.busy("demo") is None
    app.fixes.running = lambda: None
    app.downloads.items["speech:gigaam"] = {"status": "running"}
    app.queue_next("demo")
    assert app.runner.busy("demo") is None
    app.downloads.items["speech:gigaam"] = {"status": "done"}
    app.queue_next("demo")
    assert app.runner.running("demo", "w")


def test_any_line_of_the_job_after_queued_means_it_started(tmp_path):
    j = Journal(tmp_path / "x", tool="demo", subscribers=[])
    j.emit("queued", by="page", position=1)
    assert jobs_module.state(tmp_path / "x", None)[0] == "queued"
    j.emit("progress", stage="audio", done=1, total=2)
    assert jobs_module.state(tmp_path / "x", None) == ("unfinished", None)


def test_the_retry_timer_keeps_trying_while_the_start_stays_refused(server, monkeypatch):
    """B5: a second refusal inside the timer's own try schedules a third — the queue never stalls without a window."""
    _, c, root, app = server
    monkeypatch.setattr(serve, "QUEUE_RETRY_S", 0.1)
    Journal(root / "w", tool="demo", subscribers=[]).emit("queued", by="page", position=1)
    (root / "w" / serve.PAGE_RUN).write_text(json.dumps({"tool": "demo", "args": ["30", "0", "events"], "by": "page"}), encoding="utf-8")
    tries = []
    real = app._queue_next

    def refused_twice(tool):
        tries.append(1)
        if len(tries) <= 2:
            app._queue_pause_until = __import__("time").monotonic() + 0.05
        return real(tool)

    monkeypatch.setattr(app, "_queue_next", refused_twice)
    app._queue_pause_until = __import__("time").monotonic() + 0.05
    app.queue_next("demo")
    wait_for(lambda: app.runner.running("demo", "w"))
    assert len(tries) >= 3
