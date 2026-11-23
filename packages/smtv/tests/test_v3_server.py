"""В3, the server: upload names (A4), uploads that never collide or fill the disk (B12, B13), the native file dialog
(decision 16), a delete that cannot finish (B14), the token on every request (B15, A20), «Continue» and «Run again»
(B17), Docker names on «Phone» (decision 12)."""
import http.client
import json
import sys
import threading
from collections import namedtuple
from pathlib import Path

import pytest


from smtv import serve
from smtv_core import paths
from smtv_core.events import Journal
from smtv_core.tool import JobStart
from test_serve import CHILD, Client, isolated, make_tool, server, wait_for  # noqa: F401 — fixtures


def put(port, name, data, token, extra=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request("PUT", "/api/uploads", body=data, headers={"Host": f"127.0.0.1:{port}", "X-SMTV-Token": token,
                                                             "X-File-Name": name, **(extra or {})})
    res = conn.getresponse()
    out = res.status, json.loads(res.read() or b"{}")
    conn.close()
    return out


# --- A4: an uploaded file's name is a name the list can show ---------------------------------------------------------

@pytest.mark.parametrize("given,want", [
    ("стрим_23_11.mp4", "strim_23_11.mp4"),
    ("Мой стрим.mp4", "Moy-strim.mp4"),
    ("_x.mkv", "x.mkv"),
    ("___.mp4", None),                      # nothing readable left: a dated name
    ("my stream.MOV", "my-stream.mov"),
    ("клип", "klip"),
])
def test_an_uploaded_name_passes_the_job_check_and_keeps_its_extension(server, given, want):  # noqa: F811
    _, _, _, app = server
    target = app.upload_target(given)
    assert serve.JOB_ID.match(target.stem) and serve.JOB_ID.match(target.name)
    if want:
        assert target.name == want
    else:
        assert target.name.startswith("video-") and target.suffix == ".mp4"
    assert target.exists()                  # taken at once: a second upload gets another name


def test_a_request_folder_the_list_cannot_show_is_refused(server):  # noqa: F811
    _, _, root, app = server
    with pytest.raises(serve.ApiError) as e:
        app._launch("demo", root / "_23_11", ["1", "0", "done"])
    assert e.value.status == 400 and e.value.code == "bad_name"
    assert not (root / "_23_11").exists()


# --- B12, B13: uploads ------------------------------------------------------------------------------------------

def test_two_uploads_with_one_name_keep_their_own_contents(server):  # noqa: F811
    srv, c, _, app = server
    results = []
    bodies = [b"A" * 300_000, b"B" * 300_000]
    threads = [threading.Thread(target=lambda b=b: results.append(put(c.port, "same.mp4", b, c.token))) for b in bodies]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(r[0] for r in results) == [201, 201]
    files = {Path(r[1]["path"]).name: Path(r[1]["path"]).read_bytes() for r in results}
    assert sorted(files) == ["same-2.mp4", "same.mp4"] and sorted(v[:1] for v in files.values()) == [b"A", b"B"]
    assert not [f for f in (paths.data_dir() / "uploads").iterdir() if f.name.endswith(".part")]


def test_an_upload_bigger_than_the_free_space_is_refused_at_once(server, monkeypatch):  # noqa: F811
    srv, c, _, app = server
    monkeypatch.setattr(serve.shutil, "disk_usage", lambda p: namedtuple("U", "total used free")(10**12, 0, 10_000))
    status, data = put(c.port, "big.mp4", b"x" * 100, c.token)
    assert status == 507 and data["error"] == "no_space" and "места" in data["message"]
    assert [f.name for f in (paths.data_dir() / "uploads").iterdir()] == []        # no name, no .part left


def test_deleting_a_request_deletes_its_uploaded_copy(server):  # noqa: F811
    _, c, root, app = server
    status, up = put(c.port, "stream.mp4", b"video", c.token)
    folder = root / "fromupload"
    Journal(folder, tool="demo", subscribers=[]).emit("done", stage="analysis", file="clips.json")
    (folder / serve.PAGE_RUN).write_text(json.dumps({"tool": "demo", "args": ["run", up["path"], "--out", str(folder)]}), encoding="utf-8")
    assert c.request("POST", "/api/jobs/demo/fromupload/delete", {"confirm": "delete"})[1] == {"deleted": True}
    assert not Path(up["path"]).exists() and not folder.exists()


def test_a_copy_no_request_uses_counts_in_the_cache_and_goes_with_it(server):  # noqa: F811
    import os
    _, c, root, app = server
    _, up = put(c.port, "left.mp4", b"x" * 1000, c.token)
    os.utime(up["path"], (1, 1))                                     # uploaded long ago, never started
    _, fresh = put(c.port, "fresh.mp4", b"y" * 10, c.token)          # a moment ago: about to start, never touched
    assert c.request("GET", "/api/cache")[1]["bytes"] >= 1000
    status, cleared = c.request("POST", "/api/cache/clear", {})
    assert status == 200 and cleared["freed"] >= 1000
    assert not Path(up["path"]).exists() and Path(fresh["path"]).exists()


# --- decision 16: the window's own file dialog --------------------------------------------------------------------

def test_the_window_picks_a_file_by_its_path_without_a_copy(server, tmp_path):  # noqa: F811
    _, c, _, app = server
    assert c.request("POST", "/api/pick-file", {})[1]["error"] == "no_native"     # a browser: upload as before
    video = tmp_path / "Мой стрим.mp4"
    video.write_bytes(b"v")
    app.pick_file = lambda: str(video)
    status, data = c.request("POST", "/api/pick-file", {})
    assert status == 200 and data["path"] == str(video)
    assert not (paths.data_dir() / "uploads").exists() or not list((paths.data_dir() / "uploads").iterdir())
    app.pick_file = lambda: None                                                   # cancelled
    assert c.request("POST", "/api/pick-file", {})[1] == {"path": None}


# --- B14: a delete Windows cannot do while a clip is open ---------------------------------------------------------

def test_a_request_whose_file_is_open_stays_whole_with_a_clear_word(server, monkeypatch):  # noqa: F811
    _, c, root, app = server
    folder = root / "open"
    Journal(folder, tool="demo", subscribers=[]).emit("done", stage="analysis", file="clips.json")
    real = Path.rename
    monkeypatch.setattr(Path, "rename", lambda self, to: (_ for _ in ()).throw(PermissionError(13, "in use")) if self.name == "open" else real(self, to))
    status, data = c.request("POST", "/api/jobs/demo/open/delete", {"confirm": "delete"})
    assert status == 409 and data["error"] == "in_use" and "Закройте" in data["message"]
    assert (folder / "events.jsonl").exists()


def test_leftovers_of_a_delete_are_swept_at_the_next_start(tmp_path):
    root = tmp_path / "jobs"
    (root / ".deleting-old-abc123").mkdir(parents=True)
    (root / ".deleting-old-abc123" / "clip.mp4").write_bytes(b"x")
    serve.App([make_tool(root)], [])
    assert not (root / ".deleting-old-abc123").exists()


# --- B15, A20: the token on every request ------------------------------------------------------------------------

def test_reading_needs_the_page_token_or_its_cookie(server):  # noqa: F811
    _, c, _, app = server
    port = c.port
    bare = {"Cookie": None}
    assert c.request("GET", "/api/settings", headers=bare)[1]["error"] == "stale_page"       # any program on this computer
    assert c.request("GET", "/api/settings", headers={**bare, "X-SMTV-Token": app.token})[0] == 200
    assert c.request("GET", "/api/settings")[0] == 200                                           # the page's cookie
    assert c.request("GET", "/api/settings", headers={"Cookie": f"smtv_{port}=old-token"})[1]["error"] == "stale_page"
    assert c.request("GET", "/api/hello", headers=bare)[0] == 200                                # the probe stays open
    assert c.request("GET", "/static/app.js", headers=bare)[0] == 200


def test_another_site_cannot_start_a_live_check(server):  # noqa: F811
    _, c, _, app = server
    status, data = c.request("GET", "/api/doctor?live=1", headers={"Sec-Fetch-Site": "cross-site"})
    assert status == 403 and data["error"] == "cross_origin"


def test_the_page_brings_its_cookie_for_its_own_port(server):  # noqa: F811
    _, c, _, app = server
    res, _ = c.request("GET", f"/?launch={app.launch}", headers={"Cookie": None}, raw=True)
    cookie = res.getheader("Set-Cookie")
    assert cookie.startswith(f"smtv_{c.port}={app.token};") and "HttpOnly" in cookie and "SameSite=Strict" in cookie


@pytest.mark.parametrize("path", ["/", "/index.html", "/?window=mac", "/?launch=", "/?launch=wrong-key-of-the-same-length-000000000",
                                  "/?launch=%D0%BA%D0%BB%D1%8E%D1%87"])
def test_another_program_does_not_get_the_page_with_the_token(server, path):  # noqa: F811
    """Decision 7: another user of this computer, or a program that reaches 127.0.0.1 but cannot read this person's files,
    gets neither the page with the session token nor its cookie."""
    _, c, _, app = server
    res, page = c.request("GET", path, headers={"Cookie": None, "Accept-Language": "ru-RU,ru;q=0.9"}, raw=True)
    assert res.status == 403 and res.getheader("Set-Cookie") is None
    assert app.token.encode() not in page and app.launch.encode() not in page
    assert "Откройте SMTV значком".encode() in page
    res, page = c.request("GET", path, headers={"Cookie": f"smtv_{c.port}=an-old-token"}, raw=True)
    assert res.status == 403 and app.token.encode() not in page


def test_the_window_and_a_page_with_its_cookie_get_the_page(server):  # noqa: F811
    _, c, _, app = server
    res, page = c.request("GET", f"/?launch={app.launch}&window=mac", headers={"Cookie": None}, raw=True)
    assert res.status == 200 and app.token.encode() in page and b'class="shell shell-mac"' in page
    res, page = c.request("GET", "/?window=mac", raw=True)                # a reload: the cookie from the first load
    assert res.status == 200 and app.token.encode() in page


def test_the_launch_key_is_private_lasts_across_starts_and_stays_out_of_logs_and_reports(server, tmp_path):  # noqa: F811
    _, c, root, app = server
    path = serve.paths.home() / "run" / "launch.key"
    assert path.read_text(encoding="utf-8") == app.launch and len(app.launch) >= 32
    if sys.platform != "win32":
        assert path.stat().st_mode & 0o077 == 0
    assert serve.App([make_tool(root)], []).launch == app.launch           # a page left open loads after a restart
    assert serve.launch_url(8642) == f"http://127.0.0.1:8642/?launch={app.launch}" and "launch" not in serve.page_url(8642)
    from smtv import report
    assert app.launch in report.secret_values()                           # cut out of a problem report


def test_a_page_from_an_earlier_start_is_told_to_reload(server):  # noqa: F811
    _, c, root, app = server
    old = Client(c.port, "token-of-the-smtv-before")
    status, data = old.request("POST", "/api/tools/demo/jobs", {"source": "x"})
    assert status == 403 and data["error"] == "stale_page"
    assert app._look()["boot"] == app.boot
    assert serve.App([make_tool(root)], []).boot != app.boot


def test_a_new_server_address_drops_the_saved_key(server, tmp_path):  # noqa: F811
    _, c, _, app = server
    from smtv_core.settings import get_secret
    status, data = c.request("POST", "/api/settings/providers", {"kind": "openai", "preset": "custom", "base_url": "http://127.0.0.1:1/v1", "key": "sk-secret"})
    pid = [p for p in data["providers"] if p["kind"] == "openai"][0]["id"]
    from smtv_core.settings import Settings
    p = [p for p in Settings.load().providers if p.id == pid][0]
    assert get_secret(p.key_name()) == "sk-secret"
    c.request("POST", f"/api/settings/providers/{pid}", {"name": "renamed"})
    assert get_secret(p.key_name()) == "sk-secret"                       # the same address: the key stays
    c.request("POST", f"/api/settings/providers/{pid}", {"base_url": "http://other.example/v1"})
    assert not get_secret(p.key_name())                                  # another server: asked for again


# --- B17: «Continue» and «Run again» -----------------------------------------------------------------------------

def test_continue_without_saved_arguments_is_a_clear_409(server):  # noqa: F811
    _, c, root, app = server
    Journal(root / "noargs", tool="demo", subscribers=[]).emit("cancelled", by="user")
    (root / "noargs" / serve.PAGE_RUN).write_text(json.dumps({"tool": "demo"}), encoding="utf-8")
    status, data = c.request("POST", "/api/jobs/demo/noargs/restart")
    assert status == 409 and data["error"] == "not_from_page"


def test_continue_waits_for_a_ready_computer_too(server, monkeypatch):  # noqa: F811
    _, c, root, app = server
    Journal(root / "x", tool="demo", subscribers=[]).emit("cancelled", by="user")
    (root / "x" / serve.PAGE_RUN).write_text(json.dumps({"tool": "demo", "args": ["1", "0", "done"]}), encoding="utf-8")
    monkeypatch.setattr(app, "not_ready", lambda name: (_ for _ in ()).throw(serve.ApiError(409, "not_ready", "ffmpeg")))
    assert c.request("POST", "/api/jobs/demo/x/restart")[1]["error"] == "not_ready"


def test_run_again_twice_at_once_makes_one_request_and_no_500(server):  # noqa: F811
    _, c, root, app = server
    page = app.tools["demo"].page

    def again(folder, args):
        new = root / f"{folder.name}-2"
        new.mkdir()                          # FileExistsError the second time, as vodcut's `again` does
        return JobStart(new, args)
    page.again = again
    Journal(root / "a", tool="demo", subscribers=[]).emit("done", stage="analysis", file="clips.json")
    (root / "a" / serve.PAGE_RUN).write_text(json.dumps({"tool": "demo", "args": ["30", "0", "events"]}), encoding="utf-8")
    out = []
    threads = [threading.Thread(target=lambda: out.append(c.request("POST", "/api/jobs/demo/a/again")[0])) for _ in range(2)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sorted(out) == [201, 409]


# --- decision 12: Docker names over plain HTTP --------------------------------------------------------------------

def test_phone_page_warns_about_docker_names(server):  # noqa: F811
    _, c, _, app = server
    assert c.request("GET", "/api/phone")[1]["docker_hosts"] == []
    from smtv.container import Docker
    app.docker = Docker(port=8642, public_port=8642, key="k" * 32, extra=["nas.local:8642"])
    assert app.phone_state()["docker_hosts"] == ["nas.local:8642"]


@pytest.mark.parametrize("broken", ["", "short"])
def test_a_broken_launch_key_is_made_again(tmp_path, monkeypatch, broken):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    path = tmp_path / "home" / "run" / "launch.key"
    path.parent.mkdir(parents=True)
    path.write_text(broken, encoding="utf-8")
    old = __import__("time").time() - 60
    __import__("os").utime(path, (old, old))                       # left by a start that crashed a minute ago
    key = serve.launch_key()
    assert len(key) >= 32 and path.read_text(encoding="utf-8") == key and serve.launch_key() == key
    if sys.platform != "win32":
        assert path.stat().st_mode & 0o077 == 0
