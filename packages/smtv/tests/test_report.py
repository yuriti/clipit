"""«Report a problem» (stage 17): crash files, the report archive and its privacy, the GitHub issue address, `smtv report`
without a window, and the window's API."""
import io
import json
import os
import sys
import threading
import time
import urllib.parse
import zipfile
from pathlib import Path

import pytest

from smtv import cli, report, serve
from smtv import jobs as jobs_module
from smtv_core import crash
from smtv_core.events import Journal
from smtv_core.settings import Settings, set_secret
from smtv_core.tool import JobStart, Page, Tool

KEY = "sk-proj-REPORTTESTKEY0123456789abcdef"          # looks like a key
PLAIN = "plain-secret-without-any-shape-42"             # does not: only its exact value gives it away
SECOND = "work-key-without-a-known-shape-77"
PHONE = "phonekeyAAAABBBBCCCCDDDD1234"
ENV_TOKEN = "envtokenvalue-zzzz-9876"
LINK = "https://www.twitch.tv/videos/2933609914"
TITLE = "Very Private Stream Title"
CHANNEL = "secret_streamer_name"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    home = tmp_path / "userhome"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("SMTV_HOME", str(home / "smtvhome"))
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)
    monkeypatch.setattr(crash, "_recent", {})
    monkeypatch.setattr(report, "_gpu", lambda: "Test GPU")
    monkeypatch.setattr(report, "can_open", lambda: False)
    monkeypatch.setattr(report.webbrowser, "open", lambda *a, **k: pytest.fail("the browser must not open"))
    for name in list(os.environ):
        if report.SECRET_NAME.search(name) and name not in ("SMTV_HOME",):
            monkeypatch.delenv(name, raising=False)
    return home


def make_tool(root: Path) -> Tool:
    page = Page(title="Demo", folder=root / "web", jobs=lambda: root, start=lambda f: JobStart(root / "x", []),
                describe=lambda folder: {})
    (root / "web").mkdir(parents=True, exist_ok=True)
    return Tool(name="demo", summary="demo", version="1.0", add_commands=lambda p: None, checks=lambda s: [], page=page)


def failed_job(root: Path, name: str = "2933609914", message: str = "boom") -> Path:
    folder = root / name
    folder.mkdir(parents=True)
    (folder / "source.json").write_text(json.dumps({"kind": "link", "url": LINK, "title": TITLE, "channel": CHANNEL,
                                                    "id": "v" + name, "platform": "twitchvod"}), encoding="utf-8")
    (folder / "page-run.json").write_text(json.dumps({"tool": "demo", "args": ["run", LINK, "--out", str(folder)]}), encoding="utf-8")
    with Journal(folder, tool="demo", subscribers=[]) as j:
        j.emit("stage", name="audio", step=1, steps=5)
        j.emit("error", stage="analysis", message=message)
    return folder


def everything(r: report.Report) -> str:
    """Every file name and every byte of the saved archive."""
    data = r.zip_bytes()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return "\n".join(n + "\n" + z.read(n).decode("utf-8") for n in z.namelist())


def secrets_everywhere(home: Path, root: Path, monkeypatch) -> Path:
    from smtv_core.settings import ModelSettings, Provider
    s = Settings(model=ModelSettings(provider="openai", model="gpt-x"))        # one provider moved from before stage 19
    s.providers.append(Provider(id="claude-2", kind="anthropic", name="Claude — work"))   # and one added later
    s.tools["demo"] = {"token": PLAIN, "nested": {"api_key": KEY}}
    s.save()
    set_secret("openai_api_key", KEY)
    set_secret("provider.claude-2", SECOND)
    set_secret("gemini_api_key", PLAIN)
    set_secret("phone_key", PHONE)
    monkeypatch.setenv("SOME_SERVICE_TOKEN", ENV_TOKEN)
    folder = failed_job(root, message=f"401 from the provider: bad key {KEY}; also {PLAIN}")
    (folder / "run.log").write_text(f"Authorization: Bearer {KEY}\nusing {PLAIN}\nphone http://192.168.1.5:8642/?k={PHONE}\n{ENV_TOKEN}\n", encoding="utf-8")
    logs = Path(os.environ["SMTV_HOME"]) / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / "app.log").write_text(f"model call failed: {KEY}\n{PLAIN}\n{json.dumps({'key': PLAIN})}\nsecond {SECOND}\n", encoding="utf-8")
    crashes = crash.folder()
    crashes.mkdir(parents=True, exist_ok=True)
    (crashes / "20261121-100000-000.json").write_text(json.dumps({"where": "job", "message": f"bad {KEY} {PLAIN}", "stack": PHONE,
                                                                  "job": folder.name}), encoding="utf-8")
    return folder


# --- privacy -------------------------------------------------------------------------------------------------

def test_no_secret_anywhere_in_the_archive(isolated, tmp_path, monkeypatch):
    root = tmp_path / "jobs"
    folder = secrets_everywhere(isolated, root, monkeypatch)
    tool = make_tool(root)
    for names in (False, True):
        r = report.collect([tool], [], job=("demo", folder), names=names)
        text = everything(r)
        for secret in (KEY, PLAIN, PHONE, ENV_TOKEN, SECOND):
            assert secret not in text, (secret, names)
        assert "[key]" in text
        assert "request/" in text and "run.log" in text and "events.jsonl" in text and "crashes/" in text
        assert "logs/app.log" in text and "settings.json" in text and "doctor.txt" in text and "summary.json" in text
        preview, url = json.dumps(r.preview(), ensure_ascii=False), urllib.parse.unquote(report.issue_url(r))
        for secret in (KEY, PLAIN, PHONE, ENV_TOKEN, SECOND):
            assert secret not in preview and secret not in url


def test_settings_keep_their_shape_without_secrets(isolated, tmp_path, monkeypatch):
    root = tmp_path / "jobs"
    secrets_everywhere(isolated, root, monkeypatch)
    r = report.collect([make_tool(root)], [])
    settings = json.loads(next(p.text for p in r.parts if p.name == "settings.json"))
    assert [p["id"] for p in settings["providers"]] == ["openai", "claude-2"]
    assert settings["tools"]["demo"]["token"] == "[removed]" and settings["tools"]["demo"]["nested"]["api_key"] == "[removed]"
    assert settings["keys"] == {"openai": {"needed": True, "saved": True}, "claude-2": {"needed": True, "saved": True}}


def test_links_and_names_only_with_the_checkbox(isolated, tmp_path):
    root = tmp_path / "jobs"
    folder = failed_job(root, message=f"could not open {LINK} ({TITLE})")
    uploads = Path(os.environ["SMTV_HOME"]) / "data" / "uploads"
    uploads.mkdir(parents=True)
    (uploads / "my holiday video.mp4").write_bytes(b"")
    logs = Path(os.environ["SMTV_HOME"]) / "logs"
    logs.mkdir(parents=True)
    (logs / "app.log").write_text(f"uploaded my holiday video.mp4\nchannel {CHANNEL}\nhttps://api.openai.com/v1/models ok\n", encoding="utf-8")
    tool = make_tool(root)
    hidden = everything(report.collect([tool], [], job=("demo", folder)))
    for private in (LINK, "twitch.tv", TITLE, CHANNEL, "2933609914", "my holiday video"):
        assert private not in hidden, private
    assert "request-1" in hidden and "[link]" in hidden
    assert "https://api.openai.com/v1/models" in hidden          # a provider's address says nothing about the person
    shown = everything(report.collect([tool], [], job=("demo", folder), names=True))
    for private in (LINK, TITLE, "2933609914", "my holiday video"):
        assert private in shown, private


def test_home_folder_shows_as_tilde(isolated, tmp_path):
    root = tmp_path / "jobs"
    folder = failed_job(root, message=f"cannot read {isolated}/Movies/x.mkv")
    logs = Path(os.environ["SMTV_HOME"]) / "logs"
    logs.mkdir(parents=True)
    windowsish = str(isolated).replace("/", "\\")
    (logs / "app.log").write_text(f"home {isolated}/Library/smtv\n{json.dumps({'p': windowsish + chr(92) + 'a'})}\n", encoding="utf-8")
    for names in (False, True):
        text = everything(report.collect([make_tool(root)], [], job=("demo", folder), names=names))
        assert str(isolated) not in text and windowsish not in text and json.dumps(windowsish)[1:-1] not in text
        assert "~/Library/smtv" in text


def test_scrubber_catches_key_shapes():
    s = report.Scrubber([], hide_links=False, homes=[])
    for raw in ("ghp_" + "a" * 30, "github_pat_" + "b" * 30, "hf_" + "c" * 20, "xoxb-1234567890-abc",
                "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abcdefghijk", "AIza" + "d" * 30):  # gitleaks:allow (made-up token)
        assert raw not in s(f"x {raw} y"), raw
    assert "secretvalue" not in s("http://x.test/a?token=secretvalue&b=1")
    assert "secretvalue" not in s('{"client_api_key": "secretvalue"}')
    assert "secretvalue" not in s("X-Api-Key: secretvalue")


# --- what is in it ---------------------------------------------------------------------------------------------

def test_the_newest_failed_request_is_the_default(isolated, tmp_path):
    root = tmp_path / "jobs"
    failed_job(root, "old")
    time.sleep(0.02)
    newest = failed_job(root, "new")
    ok = root / "fine"
    ok.mkdir()
    with Journal(ok, tool="demo", subscribers=[]) as j:
        j.emit("done", stage="analysis", file="clips.json")
    os.utime(newest / "events.jsonl", (time.time() + 5, time.time() + 5))
    assert report.find_job([make_tool(root)], None) == ("demo", newest)
    assert report.find_job([make_tool(root)], "demo/old")[1].name == "old"
    with pytest.raises(LookupError):
        report.find_job([make_tool(root)], "demo/nope")


def test_journal_and_logs_are_tails(isolated, tmp_path):
    root = tmp_path / "jobs"
    folder = failed_job(root)
    (folder / "run.log").write_text("".join(f"line {i}\n" for i in range(5000)), encoding="utf-8")
    r = report.collect([make_tool(root)], [], job=("demo", folder))
    log = next(p.text for p in r.parts if p.name.endswith("run.log"))
    assert "line 4999" in log and "line 10\n" not in log and log.count("\n") <= report.LOG_LINES + 2
    summary = json.loads(next(p.text for p in r.parts if p.name == "summary.json"))
    assert summary["job"]["error"] == "boom" and summary["job"]["step"] == "analysis"
    assert summary["computer"]["graphics"] == "Test GPU" and "smtv" in summary["versions"]


# --- crash files ----------------------------------------------------------------------------------------------

def test_record_writes_a_crash_file(isolated):
    try:
        raise ValueError(f"broken with {KEY}")
    except ValueError as e:
        path = crash.record(e, where="job", stage="render", tool="vodcut", job="j1")
        assert crash.record(e, where="job") == path           # the same error, seen again on its way out: one file
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["where"] == "job" and data["stage"] == "render" and data["type"] == "ValueError" and data["job"] == "j1"
    assert "test_record_writes_a_crash_file" in data["stack"] and KEY not in path.read_text(encoding="utf-8")
    assert "smtv-core" in data["versions"]
    assert crash.state()["unseen"] and crash.state()["count"] == 1
    crash.mark_seen()
    assert not crash.state()["unseen"]


def test_the_same_crash_again_soon_is_one_file(isolated):
    for _ in range(5):
        crash.record(None, where="server", stage="x", message="again and again")
    assert len(crash.files()) == 1


def test_old_crash_files_go(isolated, monkeypatch):
    monkeypatch.setattr(crash, "KEEP", 3)
    for w in ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel"][:6]:
        crash.record(None, where="server", message=f"error {w}")
    assert len(crash.files()) == 3


def test_a_crash_file_that_cannot_be_written_does_not_raise(isolated, monkeypatch, capsys):
    blocker = Path(os.environ["SMTV_HOME"])
    blocker.parent.mkdir(parents=True, exist_ok=True)
    blocker.write_text("a file where the folder should be", encoding="utf-8")
    assert crash.record(None, where="server", message="nowhere to go") is None
    assert "could not write a crash file" in capsys.readouterr().err


def test_unhandled_errors_of_threads_leave_a_crash_file(isolated, monkeypatch):
    monkeypatch.setattr(crash, "_hooks_for", None)
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)
    monkeypatch.setattr(threading, "excepthook", lambda args: None)
    crash.install_hooks("server")

    def bad():
        raise RuntimeError("thread fell over")
    t = threading.Thread(target=bad, name="worker")
    t.start()
    t.join()
    files = crash.files()
    assert files and json.loads(files[0].read_text(encoding="utf-8"))["stage"] == "thread worker"


def test_a_failing_command_leaves_a_crash_file(isolated, monkeypatch):
    monkeypatch.setattr(crash, "_hooks_for", "cli")          # the hooks of this test process stay as they are

    def broken(args, tools, broken_):
        raise KeyError("no such thing")
    monkeypatch.setattr(cli, "cmd_doctor", broken)
    with pytest.raises(KeyError):
        cli.main(["doctor"])
    data = json.loads(crash.files()[0].read_text(encoding="utf-8"))
    assert data["where"] == "cli" and data["stage"] == "doctor" and data["type"] == "KeyError"


def test_the_crash_file_is_in_the_report(isolated, tmp_path):
    root = tmp_path / "jobs"
    folder = failed_job(root)
    crash.record(None, where="job", job=folder.name, message="it broke")
    r = report.collect([make_tool(root)], [], job=("demo", folder))
    assert any(p.name.startswith("crashes/") and "it broke" in p.text for p in r.parts)
    assert r.summary["crash"]["message"] == "it broke"


# --- the issue -------------------------------------------------------------------------------------------------

def test_issue_url_fits_github(isolated, tmp_path):
    root = tmp_path / "jobs"
    folder = failed_job(root, message="Ж" * 20000 + " end")
    r = report.collect([make_tool(root)], [], job=("demo", folder))
    url = report.issue_url(r)
    assert len(url) <= report.MAX_URL
    q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
    assert url.startswith(f"https://github.com/{report.REPO}/issues/new?")
    assert q["template"] == ["bug.yml"] and q["title"][0].startswith("demo: analysis")
    assert "System:" in q["summary"][0] and r.file_name in q["summary"][0]


def test_issue_url_cuts_the_summary_when_even_that_is_too_long(isolated, tmp_path, monkeypatch):
    monkeypatch.setattr(report, "MAX_URL", 400)
    r = report.collect([make_tool(tmp_path / "jobs")], [])
    assert len(report.issue_url(r)) <= 400


def test_repository_address_lives_in_one_place():
    readme = (Path(__file__).resolve().parents[3] / "README.md").read_text(encoding="utf-8")
    form = Path(__file__).resolve().parents[3] / ".github" / "ISSUE_TEMPLATE" / report.ISSUE_TEMPLATE
    assert f"https://github.com/{report.REPO}/issues/new?template={report.ISSUE_TEMPLATE}" in readme
    assert "id: summary" in form.read_text(encoding="utf-8")               # the field issue_url fills in


# --- smtv report without a window -------------------------------------------------------------------------------

def test_smtv_report_without_a_window(isolated, tmp_path, monkeypatch, capsys):
    root = tmp_path / "jobs"
    failed_job(root)
    monkeypatch.setattr(cli, "discover", lambda: ([make_tool(root)], []))
    monkeypatch.setattr(report, "reveal", lambda p: pytest.fail("nothing to show in a terminal without a desktop"))
    out = tmp_path / "out"
    assert cli.main(["report", "--out", str(out)]) == 0           # not a terminal: no question
    printed = capsys.readouterr().out
    archives = list(out.glob("smtv-report-*.zip"))
    assert len(archives) == 1 and "New issue: https://github.com/" in printed and "Nothing was sent" in printed
    with zipfile.ZipFile(archives[0]) as z:
        assert "doctor.txt" in z.namelist() and any(n.endswith("events.jsonl") for n in z.namelist())
    assert "request/demo-request-1/events.jsonl" in printed


def test_smtv_report_in_docker_saves_into_smtv_home(isolated, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("SMTV_IN_DOCKER", "1")
    monkeypatch.setattr(report, "can_open", lambda: not report.in_docker())
    (isolated / "Downloads").mkdir()
    monkeypatch.setattr(cli, "discover", lambda: ([], []))
    assert cli.main(["report", "--yes"]) == 0
    assert list((Path(os.environ["SMTV_HOME"]) / "reports").glob("smtv-report-*.zip"))
    assert "docker cp" in capsys.readouterr().out


def test_smtv_report_asks_at_a_terminal(isolated, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "discover", lambda: ([], []))
    monkeypatch.setattr(cli, "at_terminal", lambda: True)
    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    assert cli.main(["report", "--out", str(tmp_path / "out")]) == 1
    assert not (tmp_path / "out").exists() and "Nothing saved" in capsys.readouterr().out


# --- the window's API ----------------------------------------------------------------------------------------

@pytest.fixture
def server(tmp_path):
    root = tmp_path / "jobs"
    root.mkdir()
    app = serve.App([make_tool(root)], [], jobs_module.Runner(lambda name, args: [sys.executable, "-c", "pass"]))
    srv = serve.make_server(app, port=0)
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    yield srv, app, root
    app.stopping.set()
    srv.shutdown()
    srv.server_close()


def call(srv, app, method, path, body=None):
    import http.client
    conn = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=20)
    headers = {"Host": f"127.0.0.1:{srv.server_address[1]}", "Cookie": f"smtv_{srv.server_address[1]}={app.token}"}
    data = None
    if method != "GET":
        headers |= {"X-SMTV-Token": app.token, "Content-Type": "application/json"}
        data = json.dumps(body or {}).encode()
    conn.request(method, path, body=data, headers=headers)
    res = conn.getresponse()
    payload = res.read()
    conn.close()
    return res.status, json.loads(payload) if payload else None


def test_the_saved_archive_is_what_the_window_showed(server, tmp_path, monkeypatch):
    srv, app, root = server
    failed_job(root, "abc")
    monkeypatch.setattr(report, "default_folder", lambda: tmp_path / "saved")
    status, preview = call(srv, app, "GET", "/api/report?tool=demo&job=abc")
    assert status == 200 and preview["job"]["id"] == "request-1" and not preview["names"]
    (root / "abc" / "run.log").write_text("written after the preview\n", encoding="utf-8")
    status, saved = call(srv, app, "POST", "/api/report", {"id": preview["id"]})
    assert status == 200 and not saved["browser"] and saved["url"].startswith("https://github.com/")
    with zipfile.ZipFile(saved["path"]) as z:
        assert sorted(z.namelist()) == sorted(f["name"] for f in preview["files"])
        for f in preview["files"]:
            assert z.read(f["name"]).decode() == f["text"]
    status, gone = call(srv, app, "POST", "/api/report", {"id": "nope"})
    assert status == 404


def test_names_checkbox_through_the_api(server):
    srv, app, root = server
    failed_job(root, "abc")
    _, shown = call(srv, app, "GET", "/api/report?tool=demo&job=abc&names=1")
    assert shown["names"] and shown["job"]["id"] == "abc"


def test_a_server_error_leaves_a_crash_file(server, monkeypatch):
    srv, app, _ = server
    monkeypatch.setattr(app, "doctor", lambda **kw: (_ for _ in ()).throw(ZeroDivisionError(f"oops {KEY}")))
    status, body = call(srv, app, "GET", "/api/doctor")
    assert status == 500 and KEY not in json.dumps(body)
    data = json.loads(crash.files()[0].read_text(encoding="utf-8"))
    assert data["where"] == "server" and data["stage"] == "GET /api/doctor" and data["type"] == "ZeroDivisionError"
    assert KEY not in json.dumps(data)


def test_window_errors_become_crash_files_a_few_at_most(server):
    srv, app, _ = server
    for w in ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel"]:
        status, body = call(srv, app, "POST", "/api/crash", {"where": "window app.js:10", "message": f"TypeError {w}", "stack": "at x"})
        assert status == 200
    files = crash.files()
    assert len(files) == 5 and json.loads(files[0].read_text(encoding="utf-8"))["where"] == "window"
    status, state = call(srv, app, "POST", "/api/crashes/seen")
    assert status == 200 and state["unseen"] is False


def test_the_window_stream_carries_crashes(server):
    _, app, _ = server
    crash.record(None, where="job", message="first")
    look = app._look()
    assert look["crash"]["unseen"] and look["crash"]["count"] == 1


# --- found by the silent-failure review ----------------------------------------------------------------------

def test_a_token_at_the_end_of_an_error_does_not_break_the_report(isolated, tmp_path):
    root = tmp_path / "jobs"
    folder = failed_job(root, message="401: Authorization: Bearer abcdef123456")
    crash.record(None, where="job", job=folder.name, message='rejected "Authorization: Basic xyz" Bearer zzzzzzzzz')
    r = report.collect([make_tool(root)], [], job=("demo", folder))
    for p in r.parts:                                    # every JSON file stays JSON
        if p.name.endswith(".json"):
            json.loads(p.text)
        if p.name.endswith(".jsonl"):
            [json.loads(line) for line in p.text.splitlines()]
    text = everything(r)
    assert "abcdef123456" not in text and "zzzzzzzzz" not in text
    assert "abcdef123456" not in report.issue_url(r)


def test_names_in_cyrillic_and_after_a_line_break_are_hidden_everywhere(isolated, tmp_path):
    root = tmp_path / "jobs"
    uploads = Path(os.environ["SMTV_HOME"]) / "data" / "uploads"
    uploads.mkdir(parents=True)
    (uploads / "Стрим про котиков.mp4").write_bytes(b"")
    folder = failed_job(root, message="ffmpeg:\nСтрим про котиков.mp4: Invalid data")
    crash.record(None, where="job", job=folder.name, message="\nСтрим про котиков.mp4: Invalid data")
    r = report.collect([make_tool(root)], [], job=("demo", folder))
    assert "котиков" not in everything(r)
    assert "котиков" not in json.dumps(r.preview(), ensure_ascii=False)
    assert "котиков" not in urllib.parse.unquote(report.issue_url(r))


def test_a_locked_keychain_is_said_in_the_report(isolated, tmp_path, monkeypatch):
    def locked(name):
        raise RuntimeError("keychain is locked")
    monkeypatch.setattr(report, "get_secret", locked)
    r = report.collect([make_tool(tmp_path / "jobs")], [])
    assert any("could not be read" in x for x in r.summary["report_problems"])


def test_the_window_token_is_cut_out(isolated, tmp_path):
    logs = Path(os.environ["SMTV_HOME"]) / "logs"
    logs.mkdir(parents=True)
    (logs / "app.log").write_text("token LiveWindowToken_abcdefgh123\n", encoding="utf-8")
    r = report.collect([make_tool(tmp_path / "jobs")], [], extra_secrets=("LiveWindowToken_abcdefgh123",))
    assert "LiveWindowToken_abcdefgh123" not in everything(r)


def test_seen_goes_only_up_to_the_crash_in_the_report(isolated, tmp_path):
    crash.record(None, where="job", message="first one")
    r = report.collect([make_tool(tmp_path / "jobs")], [])
    time.sleep(0.01)
    crash.record(None, where="job", message="came later")
    crash.mark_seen(r.newest_crash)
    assert crash.state()["unseen"]                        # the later one is still offered


def test_the_first_unseen_crash_stays_in_the_report(isolated, tmp_path, monkeypatch):
    monkeypatch.setattr(report, "CRASHES", 2)
    for w in ["root cause", "bravo", "charlie", "delta"]:
        crash.record(None, where="job", message=w)
        time.sleep(0.002)
    r = report.collect([make_tool(tmp_path / "jobs")], [])
    assert any("root cause" in p.text for p in r.parts if p.name.startswith("crashes/"))


def test_a_failed_write_does_not_silence_the_next_try(isolated, capsys):
    home = Path(os.environ["SMTV_HOME"])
    home.parent.mkdir(parents=True, exist_ok=True)
    home.write_text("not a folder", encoding="utf-8")
    assert crash.record(None, where="server", message="disk trouble") is None
    home.unlink()
    assert crash.record(None, where="server", message="disk trouble") is not None


@pytest.mark.skipif(sys.platform == "win32", reason="chmod does not make a folder read-only on Windows")
def test_save_falls_back_to_smtv_home(server, tmp_path, monkeypatch):
    srv, app, root = server
    failed_job(root, "abc")
    readonly = tmp_path / "ro"
    readonly.mkdir()
    readonly.chmod(0o500)
    monkeypatch.setattr(report, "default_folder", lambda: readonly / "sub")
    _, preview = call(srv, app, "GET", "/api/report?tool=demo&job=abc")
    status, saved = call(srv, app, "POST", "/api/report", {"id": preview["id"]})
    readonly.chmod(0o700)
    assert status == 200 and Path(saved["path"]).parent == Path(os.environ["SMTV_HOME"]) / "reports"
