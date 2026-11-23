"""Stage 24: «Fix» — recipes run from the window with a console, the start of a request refused while a check fails,
SMTV's cache and folder. External programs are stand-ins (a small Python script), nothing is installed."""
import os
import sys
import threading
import time
from pathlib import Path

import pytest

from smtv import fixes, phone, serve
from smtv_core import checks
from smtv_core.checks import FAIL, OK, WARN, Check, Recipe

from test_serve import Client, make_tool, read_sse  # noqa: F401 — the page's server, as the window talks to it


@pytest.fixture(autouse=True)
def no_real_ffmpeg_lookup(monkeypatch):
    """After a fix SMTV looks for ffmpeg again and changes PATH: counted here, never done for real in tests."""
    looked = []
    monkeypatch.setattr(checks, "use_ffmpeg", lambda: looked.append(1))
    return looked


def py(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def wait_end(f: fixes.Fixes, fid: str, timeout: float = 10) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = f.get(fid).state()
        if state["status"] != fixes.RUNNING:
            return state
        time.sleep(0.05)
    raise AssertionError("the fix did not end")


def check(argv, status=FAIL, admin=False, cid="thing") -> Check:
    return Check("Thing", status, "missing", id=cid, recipe=Recipe("thing", argv, admin=admin))


# --- the runner -------------------------------------------------------------------------------------------------

def test_a_recipe_runs_and_its_lines_come_in_order():
    done = []
    f = fixes.Fixes(on_done=lambda: done.append(1))
    s = f.start(check(py("import sys\nprint('one')\nprint('two\\rtwo-b', flush=True)\nprint('three', file=sys.stderr)")))
    end = wait_end(f, s["id"])
    texts = [l["text"] for l in end["lines"]]
    assert end["status"] == fixes.DONE and end["code"] == 0 and done == [1, 1]
    assert texts[0].startswith("$ ") and texts[1:] == ["one", "two", "two-b", "three"]      # \r progress is split, stderr too
    assert [l["text"] for l in f.get(s["id"]).state(after=3)["lines"]] == ["two-b", "three"]


def test_a_failed_recipe_says_so_and_can_be_run_again():
    f = fixes.Fixes()
    first = wait_end(f, f.start(check(py("print('no network'); raise SystemExit(3)")))["id"])
    assert first["status"] == fixes.FAILED and first["code"] == 3 and first["lines"][-1]["text"] == "ended with code 3"
    again = wait_end(f, f.start(check(py("print('ok')")))["id"])          # «Fix» once more after a failure
    assert again["status"] == fixes.DONE and again["id"] != first["id"]


def test_after_a_fix_ffmpeg_is_looked_up_before_the_window_learns_it_ended(no_real_ffmpeg_lookup):
    seen = []
    f = fixes.Fixes(on_done=lambda: seen.append((len(no_real_ffmpeg_lookup), f.running() is not None)))
    end = wait_end(f, f.start(check(py("print(1)")))["id"])
    assert end["status"] == fixes.DONE and no_real_ffmpeg_lookup == [1]
    assert seen == [(1, True), (1, False)]          # the check dropped before the end shows, and once more after it


def test_a_recipe_that_hangs_is_stopped_after_the_time_limit():
    f = fixes.Fixes()
    f.time_limit_s = 0.5
    end = wait_end(f, f.start(check(py("import time; time.sleep(30)")))["id"])
    assert end["status"] == fixes.FAILED and any("longer than" in l["text"] for l in end["lines"])


def test_stop_right_after_start_is_not_lost():
    f = fixes.Fixes()
    s = f.start(check(py("import time; time.sleep(30)")))
    f.stop(s["id"])
    assert wait_end(f, s["id"])["status"] == fixes.STOPPED


def test_one_fix_at_a_time_and_none_while_a_request_runs():
    busy = [False]
    f = fixes.Fixes(busy=lambda: busy[0])
    s = f.start(check(py("import time; time.sleep(5)")))
    with pytest.raises(fixes.FixError) as e:
        f.start(check(py("print(1)")))
    assert e.value.status == 409 and e.value.code == "fixing"
    f.stop(s["id"])
    assert wait_end(f, s["id"])["status"] == fixes.STOPPED
    busy[0] = True
    with pytest.raises(fixes.FixError) as e:
        f.start(check(py("print(1)")))
    assert e.value.code == "busy"


def test_stop_ends_the_program_and_what_it_started():
    f = fixes.Fixes()
    code = ("import subprocess, sys, time\n"
            "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
            "print('started', flush=True); time.sleep(30)")
    s = f.start(check(py(code)))
    deadline = time.monotonic() + 5
    while "started" not in [l["text"] for l in f.get(s["id"]).state()["lines"]] and time.monotonic() < deadline:
        time.sleep(0.05)
    t0 = time.monotonic()
    f.stop(s["id"])
    end = wait_end(f, s["id"])
    assert end["status"] == fixes.STOPPED and time.monotonic() - t0 < 5


def test_nothing_to_fix_and_a_program_that_does_not_start():
    f = fixes.Fixes()
    with pytest.raises(fixes.FixError) as e:
        f.start(check(py("print(1)"), status=OK))
    assert e.value.code == "nothing_to_fix"
    with pytest.raises(fixes.FixError):
        f.start(Check("x", FAIL, "no recipe"))
    s = f.start(check(["/no/such/program-smtv"]))
    end = f.get(s["id"]).state()
    assert end["status"] == fixes.FAILED and "did not start" in end["lines"][-1]["text"]


def test_administrator_rights_open_a_terminal_never_run_here():
    ran, opened = [], []
    f = fixes.Fixes(popen=lambda *a, **k: ran.append(a), terminal=lambda r: (opened.append(r.id) or True, "Terminal opened"))
    s = f.start(check(["sudo", "apt-get", "install", "-y", "ffmpeg"], admin=True))
    assert ran == [] and opened == ["thing"] and s["status"] == fixes.OPENED
    f2 = fixes.Fixes(terminal=lambda r: (False, "no terminal found: run the command yourself"))
    s = f2.start(check(["sudo", "x"], admin=True))
    assert s["status"] == fixes.FAILED and "no terminal" in s["lines"][-1]["text"]


@pytest.mark.skipif(os.name != "posix", reason="the script for macOS and Linux")
def test_the_terminal_script_shows_and_runs_exactly_the_recipe(tmp_path):
    r = Recipe("homebrew", ["/bin/bash", "-c", checks.HOMEBREW_INSTALL], shown=checks.HOMEBREW_INSTALL, admin=True)
    path = fixes._script(r, tmp_path)
    text = path.read_text(encoding="utf-8")
    assert os.access(path, os.X_OK) and text.startswith("#!/bin/bash")
    import shlex
    assert shlex.join(r.argv) in text and "read -r -p" in text


def test_the_program_writes_unbuffered_so_lines_come_as_they_are_printed():
    f = fixes.Fixes()
    end = wait_end(f, f.start(check(py("import os; print(os.environ.get('PYTHONUNBUFFERED'))")))["id"])
    assert end["lines"][-1]["text"] == "1"


# --- cache and folder --------------------------------------------------------------------------------------------

def test_the_cache_is_pieces_and_work_files_only(tmp_path):
    job = tmp_path / "job"
    for rel, size in (("pieces/clip01.mp4", 1000), ("recap/work/a.ts", 500), ("recap/pieces/p.mp4", 200), ("source_audio.m4a.part", 50),
                      ("clips/clip01.mp4", 7000), ("transcript.json", 300), ("recap/video.mp4", 9000)):
        (job / rel).parent.mkdir(parents=True, exist_ok=True)
        (job / rel).write_bytes(b"x" * size)
    assert fixes.cache_size([job]) == 1750
    freed, left = fixes.clear_cache([job])
    assert freed == 1750 and left == [] and fixes.cache_size([job]) == 0
    assert (job / "clips/clip01.mp4").exists() and (job / "transcript.json").exists() and (job / "recap/video.mp4").exists()


def test_clearing_asks_again_before_each_request_and_keeps_a_busy_one(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    for job in (a, b):
        (job / "pieces").mkdir(parents=True)
        (job / "pieces" / "x.mp4").write_bytes(b"x" * 100)
    freed, _ = fixes.clear_cache([a, b], busy=lambda folder: folder == b)
    assert freed == 100 and not (a / "pieces").exists() and (b / "pieces" / "x.mp4").exists()


def test_a_size_that_cannot_be_read_is_nothing(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "rglob", lambda self, pattern: (_ for _ in ()).throw(PermissionError("denied")))
    assert fixes.size_of(tmp_path) == 0


def test_a_phone_cannot_fix_or_clear():
    for path in ("/api/fixes", "/api/fixes/abc/stop", "/api/cache/clear", "/api/folder/open"):
        assert phone.denied("POST", path), path
    assert not phone.denied("GET", "/api/doctor")


# --- through the page's server ------------------------------------------------------------------------------------

@pytest.fixture
def page(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)
    root = tmp_path / "jobs"
    root.mkdir()
    rows = {"smtv": [Check("ffmpeg", FAIL, "not found", "brew install ffmpeg-full", id="ffmpeg",
                           recipe=Recipe("ffmpeg", py("print('installing'); print('done')"))),
                     Check("Graphics card", OK, "none", id="gpu")],
            "demo": [Check("demo: links", WARN, "not signed in", id="demo-links", actions=(checks.SIGN_IN,))]}
    calls = []

    def groups(tools, broken, settings=None, verify=None):
        calls.append(verify)
        return [(g, list(r)) for g, r in rows.items()]

    monkeypatch.setattr(serve, "doctor_groups", groups)
    from smtv import jobs as jobs_module
    from test_serve import CHILD
    runner = jobs_module.Runner(lambda name, args: [sys.executable, "-c", CHILD, *args])
    app = serve.App([make_tool(root)], [], runner)
    srv = serve.make_server(app, port=0)
    threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    yield Client(srv.server_address[1], app.token), app, rows, calls
    app.stopping.set()
    runner.stop_all()
    srv.shutdown()
    srv.server_close()


def test_the_doctor_says_what_blocks_which_tool_and_shows_recipes(page):
    c, app, rows, _ = page
    status, d = c.request("GET", "/api/doctor")
    assert status == 200 and d["ready"] is False and d["blocks"] == {"demo": ["ffmpeg"]}
    ff = next(r for r in d["rows"] if r["id"] == "ffmpeg")
    assert ff["recipe"]["kind"] == "command" and "installing" in ff["recipe"]["command"] and ff["group"] == "smtv"
    links = next(r for r in d["rows"] if r["id"] == "demo-links")
    assert links["actions"] == ["sign_in"] and links["recipe"] is None


def test_the_doctor_is_kept_a_little_and_any_change_drops_it(page):
    c, app, rows, calls = page
    c.request("GET", "/api/doctor")
    c.request("GET", "/api/doctor")
    assert len(calls) == 1
    c.request("GET", "/api/doctor?fresh=1")
    assert len(calls) == 2
    c.request("POST", "/api/tools/demo/options", {"name": "loud", "value": False})
    c.request("GET", "/api/doctor")
    assert len(calls) == 3


@pytest.mark.doctor
def test_a_request_does_not_start_while_a_check_it_needs_fails(page):
    c, app, rows, _ = page
    status, body = c.request("POST", "/api/tools/demo/jobs", {"source": "a", "seconds": 0.2})
    assert status == 409 and body["error"] == "not_ready" and "ffmpeg" in body["message"]
    rows["smtv"][0] = Check("ffmpeg", OK, "7.1", id="ffmpeg")     # fixed: warnings alone do not block
    app.doctor_stale()
    status, body = c.request("POST", "/api/tools/demo/jobs", {"source": "a", "seconds": 0.2})
    assert status == 201, body


@pytest.mark.doctor
def test_a_check_of_another_tool_does_not_block_this_one(page):
    c, app, rows, _ = page
    rows["smtv"][0] = Check("ffmpeg", OK, "7.1", id="ffmpeg")
    rows["other"] = [Check("other: x", FAIL, "broken", id="other-x")]
    app.doctor_stale()
    status, body = c.request("POST", "/api/tools/demo/jobs", {"source": "b", "seconds": 0.2})
    assert status == 201, body


def test_fix_from_the_window_streams_its_console_then_checks_again(page):
    c, app, rows, calls = page
    c.request("GET", "/api/doctor")
    status, s = c.request("POST", "/api/fixes", {"check": "ffmpeg"})
    assert status == 201 and s["check"] == "ffmpeg" and s["recipe"]["id"] == "ffmpeg"
    conn, res = c.stream(f"/api/fixes/{s['id']}/events")
    msgs = read_sse(res, lambda m: any(e == "status" and d["status"] != "running" for _, e, d in m))
    conn.close()
    lines = [d["text"] for _, e, d in msgs if e == "line"]
    assert lines[1:] == ["installing", "done"] and lines[0].startswith("$ ")
    assert [d["status"] for _, e, d in msgs if e == "status"][-1] == "done"
    assert app._doctor_cache is None                               # the check runs again after the fix
    status, again = c.request("GET", f"/api/fixes/{s['id']}?after=2")
    assert [l["text"] for l in again["lines"]] == ["done"]


def test_fix_names_a_check_never_a_command(page):
    c, *_ = page
    assert c.request("POST", "/api/fixes", {"check": "nope"})[0] == 404
    assert c.request("POST", "/api/fixes", {"command": "rm -rf /"})[0] == 400
    assert c.request("POST", "/api/fixes", {"check": "gpu"})[1]["error"] == "nothing_to_fix"
    assert c.request("POST", "/api/fixes", {"check": "demo-links"})[1]["error"] == "nothing_to_fix"   # an action, not a recipe
    assert c.request("GET", "/api/fixes/unknown")[0] == 404
    assert c.request("POST", "/api/fixes", {"check": "ffmpeg"}, headers={"X-SMTV-Token": "wrong"})[0] == 403


def test_stop_from_the_window(page):
    c, app, rows, _ = page
    rows["smtv"][0].recipe = Recipe("ffmpeg", py("import time; print('wait', flush=True); time.sleep(30)"))
    _, s = c.request("POST", "/api/fixes", {"check": "ffmpeg"})
    status, stopped = c.request("POST", f"/api/fixes/{s['id']}/stop")
    assert status == 200
    deadline = time.monotonic() + 5
    while app.fixes.get(s["id"]).status == "running" and time.monotonic() < deadline:
        time.sleep(0.05)
    assert app.fixes.get(s["id"]).status == "stopped"


def test_the_live_check_remembers_a_refused_key_until_providers_change(page, monkeypatch):
    c, app, rows, calls = page
    from smtv_core.llm import keycheck
    from smtv_core.settings import Provider
    p = Provider(id="oa", kind="openai", preset="openai", base_url="https://api.openai.com/v1")
    monkeypatch.setattr(keycheck, "check", lambda m, timeout=15: keycheck.KeyCheck(keycheck.BAD_KEY, "HTTP 401"))
    c.request("GET", "/api/doctor?live=1")
    assert calls[-1](p) == (False, "HTTP 401")
    c.request("GET", "/api/doctor?fresh=1")                      # not live: the refused key stays refused
    assert calls[-1](p) == (False, "HTTP 401")
    c.request("POST", "/api/settings/providers/oa/check", {})    # any change of the providers forgets it
    c.request("GET", "/api/doctor?fresh=1")
    assert calls[-1](p) == (None, "")
    monkeypatch.setattr(keycheck, "check", lambda m, timeout=15: keycheck.KeyCheck(keycheck.UNREACHABLE, "no network"))
    c.request("GET", "/api/doctor?live=1")
    assert calls[-1](p) == (None, "")                            # no network is not a bad key


def test_the_cache_through_the_page(page, tmp_path):
    c, app, *_ = page
    job = tmp_path / "jobs" / "old"
    (job / "pieces").mkdir(parents=True)
    (job / "pieces" / "clip01.mp4").write_bytes(b"x" * 4000)
    from smtv_core.events import Journal
    with Journal(job, tool="demo", subscribers=[]) as j:
        j.emit("done", stage="analysis", file="clips.json")
    status, d = c.request("GET", "/api/cache")
    assert status == 200 and d["bytes"] == 4000
    status, d = c.request("POST", "/api/cache/clear")
    assert status == 200 and d["freed"] == 4000 and d["bytes"] == 0 and not (job / "pieces").exists()


@pytest.mark.doctor
def test_run_again_is_refused_while_a_check_fails(page, tmp_path):
    c, app, rows, _ = page
    rows["smtv"][0] = Check("ffmpeg", OK, "7.1", id="ffmpeg")
    app.doctor_stale()
    status, job = c.request("POST", "/api/tools/demo/jobs", {"source": "first", "seconds": 0.1})
    assert status == 201, job
    deadline = time.monotonic() + 5
    while app.runner.running("demo", "first") and time.monotonic() < deadline:
        time.sleep(0.05)
    rows["smtv"][0] = Check("ffmpeg", FAIL, "not found", id="ffmpeg", recipe=Recipe("ffmpeg", py("print(1)")))
    app.doctor_stale()
    from smtv_core.tool import JobStart
    app.tools["demo"].page.again = lambda folder, args: JobStart(folder.parent / "second", args)
    status, body = c.request("POST", "/api/jobs/demo/first/again")
    assert status == 409 and body["error"] == "not_ready"


@pytest.mark.doctor
def test_checks_that_crash_do_not_block_requests(page, monkeypatch):
    c, app, *_ = page
    monkeypatch.setattr(serve, "doctor_groups", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("broken")))
    app.doctor_stale()
    status, body = c.request("POST", "/api/tools/demo/jobs", {"source": "c", "seconds": 0.1})
    assert status == 201, body


@pytest.mark.doctor
def test_no_request_starts_while_a_fix_runs(page):
    c, app, rows, _ = page
    rows["smtv"][0] = Check("ffmpeg", WARN, "old", id="ffmpeg", recipe=Recipe("ffmpeg", py("import time; time.sleep(30)")))
    app.doctor_stale()
    _, s = c.request("POST", "/api/fixes", {"check": "ffmpeg"})          # a warning can be fixed too
    assert s["status"] == "running"
    status, body = c.request("POST", "/api/tools/demo/jobs", {"source": "d", "seconds": 0.1})
    assert status == 409 and body["error"] == "fixing"
    c.request("POST", f"/api/fixes/{s['id']}/stop")


def test_fix_is_refused_while_a_request_runs_through_the_page(page):
    c, app, *_ = page
    assert c.request("POST", "/api/tools/demo/jobs", {"source": "long", "seconds": 3})[0] == 201
    status, body = c.request("POST", "/api/fixes", {"check": "ffmpeg"})
    assert status == 409 and body["error"] == "busy"


def test_the_cache_of_a_running_request_is_kept(page, tmp_path):
    c, app, *_ = page
    assert c.request("POST", "/api/tools/demo/jobs", {"source": "busy", "seconds": 3})[0] == 201
    (tmp_path / "jobs" / "busy" / "pieces").mkdir(parents=True, exist_ok=True)
    (tmp_path / "jobs" / "busy" / "pieces" / "x.mp4").write_bytes(b"x" * 100)
    deadline = time.monotonic() + 5
    while not (tmp_path / "jobs" / "busy" / "events.jsonl").exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    status, d = c.request("POST", "/api/cache/clear")
    assert status == 200 and d["freed"] == 0 and (tmp_path / "jobs" / "busy" / "pieces" / "x.mp4").exists()
