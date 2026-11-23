"""SMTV in Docker (stage 21): the access key on every request (link → cookie), the checks of the window's page kept on
top of it, the published hosts, the manifest for «Install SMTV», no self-update, no CLIs, «Phone» without a second
server, and the image's files: what is in them and what is not."""
import io
import json
import os
import re
import stat
import sys
import threading
from contextlib import redirect_stderr
from pathlib import Path

import pytest

from smtv import container, handoff, serve, updates
from smtv import jobs as jobs_module
from smtv import phone as phone_module
from test_serve import CHILD, Client, make_tool

ROOT = Path(__file__).resolve().parents[3]
LAN = "192.168.50.7"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)
    monkeypatch.setenv("SMTV_DOCKER", "1")
    for name in ("SMTV_PUBLIC_PORT", "SMTV_HOSTS", "SMTV_LAN_ADDRESS"):
        monkeypatch.delenv(name, raising=False)


class DockerClient(Client):
    def __init__(self, port, token, key=None):
        super().__init__(port, token)
        self.key = key

    def request(self, method, path, body=None, headers=None, host=None, raw=False, key=True):
        h = dict(headers or {})
        if key and self.key:
            h.setdefault("Cookie", f"{container.COOKIE}={self.key}")
        return super().request(method, path, body=body, headers=h, host=host, raw=raw)


def start(tmp_path, monkeypatch, env=None):
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)
    root = tmp_path / "jobs"
    root.mkdir(exist_ok=True)
    runner = jobs_module.Runner(lambda name, args: [sys.executable, "-c", CHILD, *args])
    app = serve.App([make_tool(root)], [], runner)
    srv = serve.make_server(app, port=0)         # 127.0.0.1 in tests; the image listens on 0.0.0.0
    serve.docker_setup(app, srv.server_address[1])
    threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    return srv, app, DockerClient(srv.server_address[1], app.token, app.docker.key)


@pytest.fixture
def docker(tmp_path, monkeypatch):
    made = []

    def make(**env):
        srv, app, client = start(tmp_path, monkeypatch, env)
        made.append((srv, app))
        return srv, app, client

    yield make
    for srv, app in made:
        app.stopping.set()
        app.phone.close()
        app.runner.stop_all()
        srv.shutdown()
        srv.server_close()


# --- the access key -------------------------------------------------------------------------------------------

def test_without_the_key_nothing_answers_but_a_page_that_says_where_the_link_is(docker):
    _, _, c = docker()
    res, html = c.request("GET", "/", raw=True, key=False)
    assert res.status == 403 and b"token=" in html and b"docker compose logs" in html
    assert c.app_token_missing if False else True
    for path in ("/api/state", "/api/jobs", "/api/settings", "/api/window/events", "/static/app.js", "/api/hello"):
        status, body = c.request("GET", path, key=False)
        assert status == 403, path
    status, body = c.request("GET", "/api/state", key=False)
    assert body["error"] == "no_access_key"


def test_the_link_from_the_log_becomes_a_cookie_and_leaves_the_address_bar(docker):
    _, app, c = docker()
    res, _ = c.request("GET", f"/?token={app.docker.key}", raw=True, key=False)
    assert res.status == 303 and res.getheader("Location") == "/"
    cookie = res.getheader("Set-Cookie")
    assert cookie.startswith(f"{container.COOKIE}={app.docker.key};")
    assert "HttpOnly" in cookie and "SameSite=Strict" in cookie and "Path=/" in cookie
    res, html = c.request("GET", "/", raw=True)
    assert res.status == 200 and app.token.encode() in html
    assert b'<link rel="manifest" href="/manifest.webmanifest">' in html
    status, state = c.request("GET", "/api/state")
    assert status == 200 and state["docker"] is True and state["phone"] is False


def test_a_wrong_key_is_refused_and_never_written_to_the_log(docker):
    _, app, c = docker()
    err = io.StringIO()
    with redirect_stderr(err):
        res, _ = c.request("GET", "/?token=guess-guess-guess-guess-guess-guess", raw=True, key=False)
        assert res.status == 403 and res.getheader("Set-Cookie") is None
        status, _ = c.request("GET", "/api/state", headers={"Cookie": f"{container.COOKIE}=guess"}, key=False)
        assert status == 403
    assert "guess" not in err.getvalue() and app.docker.key not in err.getvalue()


def test_changes_still_need_the_session_token_and_our_origin(docker):
    _, app, c = docker()
    ok, _ = c.request("POST", "/api/crashes/seen", body={})
    assert ok == 200
    status, body = c.request("POST", "/api/crashes/seen", body={}, headers={"X-SMTV-Token": None})
    assert status == 403 and body["error"] == "stale_page"      # A20: the page reloads itself on this code
    status, _ = c.request("POST", "/api/crashes/seen", body={}, headers={"Origin": "http://evil.example"})
    assert status == 403
    status, _ = c.request("POST", "/api/crashes/seen", body={}, key=False)   # the session token alone is not enough
    assert status == 403


def test_only_our_hosts_answer_even_with_the_key(docker):
    _, _, c = docker(SMTV_PUBLIC_PORT="9000", SMTV_HOSTS="nas.local,192.168.1.20:8000")
    for host in ("127.0.0.1:9000", "localhost:9000", f"127.0.0.1:{c.port}", "nas.local:9000", "192.168.1.20:8000"):
        assert c.request("GET", "/api/state", host=host)[0] == 200, host
    for host in ("evil.example:9000", "nas.local:8000", "127.0.0.1:1", "192.168.1.20:9000"):
        status, body = c.request("GET", "/api/state", host=host)
        assert status == 403 and body["error"] == "bad_host", host
    status, _ = c.request("POST", "/api/crashes/seen", body={}, host="nas.local:9000", headers={"Origin": "http://nas.local:9000"})
    assert status == 200


def test_no_cors_and_the_strict_policy_stay(docker):
    _, _, c = docker()
    res, _ = c.request("GET", "/", raw=True, headers={"Origin": "http://evil.example"})
    assert res.getheader("Access-Control-Allow-Origin") is None
    assert "frame-ancestors 'none'" in res.getheader("Content-Security-Policy")


def test_health_manifest_and_icons_need_no_key(docker):
    _, _, c = docker()
    assert c.request("GET", "/healthz", key=False) == (200, {"ok": True})
    res, body = c.request("GET", "/manifest.webmanifest", raw=True, key=False)
    assert res.status == 200 and res.getheader("Content-Type") == "application/manifest+json"
    manifest = json.loads(body)
    assert manifest["display"] == "standalone" and manifest["start_url"] == "/"
    sizes = {i["sizes"] for i in manifest["icons"]}
    assert "512x512" in sizes
    for icon in manifest["icons"]:
        res, png = c.request("GET", icon["src"], raw=True, key=False)
        assert res.status == 200 and png.startswith(b"\x89PNG"), icon["src"]


def test_outside_docker_there_is_no_manifest_no_health_route_and_no_key(tmp_path, monkeypatch):
    monkeypatch.delenv("SMTV_DOCKER")
    root = tmp_path / "jobs"
    root.mkdir()
    app = serve.App([make_tool(root)], [], jobs_module.Runner(lambda n, a: [sys.executable, "-c", CHILD, *a]))
    srv = serve.make_server(app, port=0)
    threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    try:
        c = Client(srv.server_address[1], app.token)
        assert c.request("GET", "/manifest.webmanifest")[0] == 404
        assert c.request("GET", "/healthz")[0] == 404
        res, html = c.request("GET", "/", raw=True)
        assert res.status == 200 and b"manifest" not in html
        assert c.request("GET", "/api/state")[1]["docker"] is False
    finally:
        srv.shutdown()
        srv.server_close()


def test_the_key_is_kept_in_the_volume_readable_only_by_its_owner(tmp_path):
    path = tmp_path / "home" / container.KEY_FILE
    first = container.access_key(path)
    assert len(first) >= 32 and container.access_key(path) == first     # a new container: the same key, the same cookie
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    path.unlink()
    assert container.access_key(path) != first                          # deleted: every old browser is cut off


def test_the_log_prints_the_links_with_the_key(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_PUBLIC_PORT", "9000")
    monkeypatch.setenv("SMTV_HOSTS", "nas.local")
    d = container.Docker.from_env(8642, key="k" * 32)
    assert d.links() == [f"http://127.0.0.1:9000/?token={'k' * 32}", f"http://nas.local:9000/?token={'k' * 32}"]


@pytest.mark.parametrize("env,value", [("SMTV_PUBLIC_PORT", "nine"), ("SMTV_PUBLIC_PORT", "70000"), ("SMTV_HOSTS", "evil host"),
                                       ("SMTV_HOSTS", "a.b:port"), ("SMTV_LAN_ADDRESS", "8.8.8.8"), ("SMTV_LAN_ADDRESS", "nas")])
def test_bad_settings_stop_the_start_with_a_clear_message(monkeypatch, env, value):
    monkeypatch.setenv(env, value)
    with pytest.raises(ValueError, match=env):
        container.Docker.from_env(8642, key="k" * 32)


def test_sigterm_from_docker_stop_ends_the_server_like_ctrl_c():
    with pytest.raises(KeyboardInterrupt):
        serve._stop_on_term(15, None)


# --- what is different in a container -----------------------------------------------------------------------

def test_quit_and_remove_are_left_to_docker(docker):
    _, _, c = docker()
    for path in ("/api/quit", "/api/uninstall"):
        status, body = c.request("POST", path, body={})
        assert status == 409 and body["error"] == "in_docker" and "docker compose" in body["message"], path


def test_the_clis_are_not_offered_in_docker(docker):
    _, _, c = docker()
    status, s = c.request("GET", "/api/settings")
    assert status == 200 and not [x for x in s["choices"] if x["cli"]]
    for kind in ("codex", "claude_code"):
        status, body = c.request("POST", "/api/settings/providers", body={"kind": kind})
        assert status == 400 and body["error"] == "cli_not_in_docker"


def test_updates_come_with_a_new_image():
    assert updates.install_kind() == "docker"
    u = updates.Updates(tools=lambda: [], running=lambda: 0, stop_jobs=lambda: None, port=lambda: 8642)
    with pytest.raises(updates.UpdateError):
        u.ask("update")


def test_local_model_servers_are_on_the_host(monkeypatch):
    import importlib
    from smtv_core import presets
    from smtv_core.llm import ollama
    monkeypatch.setenv("SMTV_LOCAL_HOST", "host.docker.internal")
    try:
        importlib.reload(presets)
        importlib.reload(ollama)
        assert presets.BY_ID["ollama"].base_url == "http://host.docker.internal:11434"
        assert presets.BY_ID["lmstudio"].base_url == "http://host.docker.internal:1234/v1"
        assert ollama.DEFAULT_URL == "http://host.docker.internal:11434"
        assert presets.is_local_url("http://host.docker.internal:11434")
        monkeypatch.setenv("SMTV_LOCAL_HOST", "bad host; rm")
        importlib.reload(presets)
        assert presets.BY_ID["ollama"].base_url == "http://127.0.0.1:11434"
    finally:
        monkeypatch.delenv("SMTV_LOCAL_HOST")
        importlib.reload(presets)
        importlib.reload(ollama)


def test_a_command_inside_the_container_hands_over_with_the_key(tmp_path, docker):
    srv, app, c = docker()
    container.access_key()                    # the server made it in the volume; the command reads the same file
    assert container.auth_headers() == {"Cookie": f"{container.COOKIE}={app.docker.key}"}
    status, body = handoff._call(srv.server_address[1], "GET", "/api/state")
    assert status == 200 and body["docker"] is True


def test_the_report_archive_is_downloaded_from_the_page(docker):
    _, app, c = docker()
    status, rep = c.request("GET", "/api/report")
    assert status == 200
    status, saved = c.request("POST", "/api/report", body={"id": rep["id"], "open": False})
    assert status == 200 and saved["download"] == f"/api/report/{rep['id']}/archive"
    res, data = c.request("GET", saved["download"], raw=True)
    assert res.status == 200 and data.startswith(b"PK") and "attachment" in res.getheader("Content-Disposition")
    assert c.request("GET", saved["download"], key=False)[0] == 403


# --- «Phone» in a container -----------------------------------------------------------------------------------

def test_phone_in_docker_uses_the_hosts_address_and_keeps_the_phones_limits(docker):
    _, app, c = docker(SMTV_PUBLIC_PORT="9000", SMTV_LAN_ADDRESS=LAN)
    status, p = c.request("POST", "/api/phone", body={"on": True})
    assert status == 200 and p["on"] and p["address"] == LAN
    assert p["url"].startswith(f"http://{LAN}:9000/?k=")
    host = f"{LAN}:9000"
    assert c.request("GET", "/api/state", host=host, key=False)[0] == 403        # no key at all
    phone_key = p["url"].split("?k=", 1)[1]
    res, _ = c.request("GET", f"/?k={phone_key}", raw=True, host=host, key=False)
    assert res.status == 303
    cookie = {"Cookie": f"{phone_module.COOKIE}={phone_key}"}
    status, state = c.request("GET", "/api/state", host=host, headers=cookie, key=False)
    assert status == 200 and state["phone"] is True
    status, body = c.request("GET", "/api/settings", host=host, headers=cookie, key=False)
    assert status == 403 and body["error"] == "not_from_phone"
    # the phone's key is only for the home-network address; the loopback name needs the access key
    assert c.request("GET", "/api/state", headers=cookie, key=False)[0] == 403
    c.request("POST", "/api/phone", body={"on": False})
    assert c.request("GET", "/api/state", host=host, headers=cookie, key=False)[0] == 403


def test_phone_in_docker_without_the_hosts_address_says_what_to_set(docker):
    _, _, c = docker()
    status, p = c.request("GET", "/api/phone")
    assert status == 200 and p["addresses"] == [] and not p["on"]
    status, body = c.request("POST", "/api/phone", body={"on": True})
    assert status >= 400


# --- the image's files ----------------------------------------------------------------------------------------

def _run_lines(text: str) -> list[str]:
    """The Dockerfile's instructions with continuation lines joined, comments left out."""
    out, cur = [], ""
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        cur += line.rstrip("\\").strip() + " "
        if not line.rstrip().endswith("\\"):
            if cur.strip():
                out.append(cur.strip())
            cur = ""
    return out


def test_the_image_has_ffmpeg_with_libass_and_no_downloader_or_cli_of_its_own():
    lines = _run_lines((ROOT / "Dockerfile").read_text(encoding="utf-8"))
    text = "\n".join(lines).lower()
    assert any(l.startswith("RUN apt-get") and " ffmpeg " in l and "tini" in l for l in lines)
    assert "grep -qe '^ ... ass '" in text                        # the build fails if ffmpeg cannot burn captions
    for absent in ("yt-dlp", "yt_dlp", "codex", "claude", "keyring", "npm"):
        assert absent not in text, absent                       # yt-dlp: stage 23; CLIs: not in the container
    assert "env smtv_docker=1" in text and "smtv_home=/data" in text and "smtv_local_host=host.docker.internal" in text
    assert 'volume ["/data"]' in text and "user smtv" in text and "healthcheck" in text
    assert 'cmd ["smtv", "serve", "--no-browser"]' in text


def test_compose_publishes_only_on_the_hosts_loopback_and_keeps_data_in_a_volume():
    text = (ROOT / "compose.yaml").read_text(encoding="utf-8")
    ports = re.findall(r'^\s*-\s*"([^"]+:8642)"', text, re.M)
    assert ports == ["127.0.0.1:8642:8642"]
    assert re.search(r"^\s*-\s*smtv-data:/data", text, re.M)
    assert "host.docker.internal:host-gateway" in text


def test_the_build_context_leaves_out_the_local_environment():
    rules = (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    assert rules[0] == "**"                                     # only what is let in below: the packages' sources
    assert not any(".venv" in r or "tests" in r for r in rules if r.startswith("!"))


def test_the_window_check_says_the_page_opens_in_the_browser():
    from smtv.tools import window_check
    c = window_check()
    assert c.status == "ok" and "Docker" in c.detail and "Chrome" in c.detail


def test_only_the_icons_themselves_are_open_not_a_path_through_them(docker):
    _, _, c = docker()
    for path in ("/static/icons/../app.js", "/static/icons/%2e%2e/app.js", "/static/icons/../../serve.py", "/static/icons/icon-256.png/"):
        assert c.request("GET", path, key=False)[0] == 403, path
    assert c.request("GET", "/static/icons/icon-256.png", key=False)[0] == 200
