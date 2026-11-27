"""The page's server: safety (only 127.0.0.1, our own page, keys never shown), live events with Last-Event-ID, jobs started
and cancelled in their own process, settings, files."""
import http.client
import http.server
import io
import json
import types
import sys
import threading
import time
from contextlib import redirect_stderr
from pathlib import Path

import pytest

from smtv import jobs as jobs_module
from smtv import serve
from smtv_core.checks import OK, Check
from smtv_core.events import Journal, contract
from smtv_core import agents
from smtv_core.agents import Agent, Needs
from smtv_core.tool import JobStart, Page, Tool

SECRET = "sk-test-0123456789abcdefSECRET"  # gitleaks:allow (made-up key)
DEMO_AGENT = Agent(id="finder", prompt="vod/pass1-prompt.txt", schema="pass1", purposes=("scan", "scan_repair"),
                   needs=Needs(level="strong"))

# A job process: writes a stage, then sleeps `seconds` and exits with `code`; with "quiet" it exits without an event.
CHILD = """
import sys, time
from pathlib import Path
from smtv_core.events import Journal
seconds, code, mode = float(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
if mode != "quiet":
    with Journal(Path.cwd(), tool="demo", subscribers=[]) as j:
        j.emit("stage", name="audio", step=1, steps=5)
        if mode == "done":
            j.emit("done", stage="analysis", file="clips.json")
time.sleep(seconds)
sys.exit(code)
"""


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)


def make_tool(root: Path, options=None) -> Tool:
    switches = options if options is not None else {"loud": True}

    def start(fields):
        if not fields.get("source"):
            raise ValueError("paste a link or choose a file")
        return JobStart(root / fields["source"], [str(fields.get("seconds", 30)), str(fields.get("code", 0)), fields.get("mode", "events")])

    def set_option(settings, name, value):
        if name not in switches:
            raise KeyError(name)
        switches[name] = value

    page = Page(title="Demo", folder=root / "web", jobs=lambda: root, start=start, estimate=lambda f: {"seconds": 60, "steps": []},
                describe=lambda folder: {"title": "a stream"}, options=lambda s: [{"name": k, "value": v, "about": k} for k, v in switches.items()],
                set_option=set_option)
    (root / "web").mkdir(parents=True, exist_ok=True)
    (root / "web" / "section.js").write_text("export function mount() {}", encoding="utf-8")
    (root / "web" / "i18n").mkdir(exist_ok=True)       # the tool's words: its agents' and its places' (V9)
    (root / "web" / "i18n" / "en.json").write_text(json.dumps({"agent.finder.title": "Finder", "agent.finder.why": "reads a lot",
                                                               "request.title": "Recording"}), encoding="utf-8")
    (root / "web" / "i18n" / "ru.json").write_text(json.dumps({"agent.finder.title": "Поиск", "request.title": "Запись"}), encoding="utf-8")
    return Tool(name="demo", summary="demo", version="1.0", add_commands=lambda p: None, checks=lambda s, v=None: [Check("demo: thing", OK, "fine")], page=page,
                agents=[DEMO_AGENT, *agents.core("layout")])


class Client:
    def __init__(self, port, token):
        self.port, self.token = port, token

    def request(self, method, path, body=None, headers=None, host=None, raw=False):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        # like the page: the session cookie it got with the page on every request, the token on every change
        h = {"Host": host or f"127.0.0.1:{self.port}", "Cookie": f"smtv_{self.port}={self.token}"}
        if method != "GET":
            h["X-SMTV-Token"] = self.token
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        h.update(headers or {})
        conn.request(method, path, body=data, headers={k: v for k, v in h.items() if v is not None})
        res = conn.getresponse()
        payload = res.read()
        conn.close()
        if raw:
            return res, payload
        return res.status, (json.loads(payload) if payload and res.getheader("Content-Type", "").startswith("application/json") else payload)

    def stream(self, path, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", path, headers={"Host": f"127.0.0.1:{self.port}", "Cookie": f"smtv_{self.port}={self.token}", **(headers or {})})
        res = conn.getresponse()
        return conn, res


def read_sse(res, until, timeout=8.0):
    """SSE messages as (id, event, data) until `until(messages)` is true."""
    messages, current, deadline = [], {}, time.monotonic() + timeout
    while time.monotonic() < deadline:
        line = res.fp.readline().decode("utf-8")
        if line == "":
            break
        line = line.rstrip("\n")
        if not line:
            if "data" in current:
                messages.append((current.get("id"), current.get("event", "message"), json.loads(current["data"])))
                if until(messages):
                    return messages
            current = {}
        elif not line.startswith(":") and ":" in line:
            k, v = line.split(":", 1)
            current[k] = v.lstrip(" ")
    raise AssertionError(f"stream ended early: {messages}")


@pytest.fixture
def server(tmp_path):
    root = tmp_path / "jobs"
    root.mkdir()
    tool = make_tool(root)
    runner = jobs_module.Runner(lambda name, args: [sys.executable, "-c", CHILD, *args])
    app = serve.App([tool], [], runner)
    srv = serve.make_server(app, port=0)
    thread = threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
    thread.start()
    yield srv, Client(srv.server_address[1], app.token), root, app
    app.stopping.set()
    runner.stop_all()
    srv.shutdown()
    srv.server_close()


# --- safety -----------------------------------------------------------------------------------------------

def test_listens_only_on_loopback(server):
    srv, *_ = server
    assert srv.server_address[0] == "127.0.0.1"
    assert serve.HOST == "127.0.0.1"


def test_a_foreign_host_is_refused(server):
    _, c, *_ = server
    assert c.request("GET", "/api/state", host=f"evil.example:{c.port}")[0] == 403      # DNS rebinding
    assert c.request("GET", "/api/state", host=f"localhost:{c.port}")[0] == 200
    assert c.request("GET", "/api/state")[0] == 200


def test_changes_come_only_from_the_page(server):
    _, c, *_ = server
    assert c.request("POST", "/api/tools/demo/options", {"name": "loud", "value": False}, headers={"X-SMTV-Token": None})[0] == 403   # no token
    assert c.request("POST", "/api/tools/demo/options", {"name": "loud", "value": False}, headers={"X-SMTV-Token": "guess"})[0] == 403  # wrong token
    for path, body in (("/api/tools/demo/jobs", {"source": "x"}), ("/api/settings/providers", {"kind": "openai", "preset": "openai", "key": SECRET}),
                       ("/api/jobs/demo/x/cancel", {})):
        assert c.request("POST", path, body, headers={"X-SMTV-Token": None})[0] == 403
    assert c.request("POST", "/api/tools/demo/options", {"name": "loud", "value": False}, headers={"Origin": "https://evil.example"})[0] == 403
    assert c.request("POST", "/api/tools/demo/options", {"name": "loud", "value": False}, headers={"Sec-Fetch-Site": "cross-site"})[0] == 403
    status, body = c.request("POST", "/api/tools/demo/options", {"name": "loud", "value": False}, headers={"Origin": f"http://127.0.0.1:{c.port}"})
    assert status == 200 and body == [{"name": "loud", "value": False, "about": "loud"}]


def test_pages_carry_a_strict_content_policy_and_no_cors(server):
    _, c, *_ = server
    res, page = c.request("GET", "/", raw=True)
    assert res.status == 200 and "default-src 'self'" in res.getheader("Content-Security-Policy")
    assert res.getheader("X-Content-Type-Options") == "nosniff"
    assert c.token.encode() in page and b"{{SMTV_TOKEN}}" not in page            # the session token lives only in the page
    for path in ("/api/state", "/api/settings", "/api/jobs"):
        res, body = c.request("GET", path, headers={"Origin": "https://evil.example"}, raw=True)
        assert res.getheader("Access-Control-Allow-Origin") is None and c.token.encode() not in body
    res, _ = c.request("OPTIONS", "/api/settings/providers", raw=True)                # no preflight answer: a foreign page cannot send changes
    assert res.getheader("Access-Control-Allow-Origin") is None and res.status >= 400


def test_each_server_start_makes_a_new_token():
    a, b = serve.App([], []), serve.App([], [])
    assert a.token != b.token and len(a.token) >= 32


def test_job_files_only_from_inside_the_job(server):
    _, c, root, _ = server
    job = root / "j1"
    (job / "clips").mkdir(parents=True)
    Journal(job, tool="demo", subscribers=[]).emit("stage", name="audio")
    (job / "clips" / "clip01.mp4").write_bytes(b"0123456789")
    (root / "secret.mp4").write_bytes(b"nope")
    assert c.request("GET", "/api/jobs/demo/j1/files/clips/clip01.mp4")[1] == b"0123456789"
    assert c.request("GET", "/api/jobs/demo/j1/files/../secret.mp4")[0] == 404
    assert c.request("GET", "/api/jobs/demo/j1/files/%2e%2e/secret.mp4")[0] == 404
    assert c.request("GET", "/api/jobs/demo/..%2Fj1/events")[0] == 404
    res, part = c.request("GET", "/api/jobs/demo/j1/files/clips/clip01.mp4", headers={"Range": "bytes=2-5"}, raw=True)
    assert res.status == 206 and part == b"2345" and res.getheader("Content-Range") == "bytes 2-5/10"   # the video player seeks
    res, _ = c.request("GET", "/api/jobs/demo/j1/files/clips/clip01.mp4?download=1", raw=True)
    assert "attachment" in res.getheader("Content-Disposition")


# --- the key ---------------------------------------------------------------------------------------------

class FakeProvider(http.server.BaseHTTPRequestHandler):
    """An OpenAI-compatible server: lists models for the right key, and on a wrong one answers like OpenAI does, with the key in the text."""
    def do_GET(self):
        auth = self.headers.get("Authorization", "")
        if auth == f"Bearer {SECRET}":
            body, code = {"data": [{"id": "model-a"}, {"id": "model-b"}]}, 200
        else:
            body, code = {"error": {"message": f"Incorrect API key provided: {auth.removeprefix('Bearer ')}"}}, 401
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


@pytest.fixture
def provider():
    srv = http.server.HTTPServer(("127.0.0.1", 0), FakeProvider)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/v1"
    srv.shutdown()
    srv.server_close()


def add(c, **body):
    status, data = c.request("POST", "/api/settings/providers", body)
    assert status == 201, data
    return data["added"], data


def test_the_key_is_saved_but_never_sent_back_or_logged(server, provider, tmp_path):
    _, c, *_ = server
    log = io.StringIO()
    wrong = "sk-test-WRONGKEY987654321"
    with redirect_stderr(log):
        pid, added = add(c, kind="openai", preset="custom", name="My server", base_url=provider, key=SECRET)
        _, shown = c.request("GET", "/api/settings")
        _, good = c.request("POST", f"/api/settings/providers/{pid}/check", {})
        _, bad = c.request("POST", "/api/settings/providers/check", {"kind": "openai", "preset": "custom", "base_url": provider, "key": wrong})
        _, before = c.request("POST", "/api/settings/providers/check", {"kind": "openai", "preset": "custom", "base_url": provider, "key": SECRET})
        _, models = c.request("GET", f"/api/settings/providers/{pid}/models")
        c.request("POST", f"/api/settings/providers/{pid}", {"key": SECRET, "base_url": "ftp://nope"})    # an error with the key in it
        c.request("POST", "/api/settings/providers", {"kind": "nonsense", "key": SECRET})
    for answer in (added, shown, good, bad, before, models):
        assert SECRET not in json.dumps(answer) and "WRONGKEY" not in json.dumps(answer)
    assert SECRET not in log.getvalue() and "WRONGKEY" not in log.getvalue()
    p = shown["providers"][0]
    assert p["key"]["saved"] is True and p["name"] == "My server" and "key" not in {k for k in p if k != "key"}
    assert set(p["key"]) == {"needed", "saved", "unreadable", "where"}
    assert good["ok"] and good["models"] == 2                       # the saved key was used; only the count comes back
    assert bad["status"] == "bad_key" and "[key]" in bad["detail"]
    assert before["ok"]                                             # a key typed in before adding is checked as typed
    assert [m["id"] for m in models["models"]] == ["model-a", "model-b"]
    from smtv_core.settings import Settings, get_secret
    assert get_secret(Settings.load().provider(pid).key_name()) == SECRET
    assert SECRET not in (tmp_path / "home" / "settings.json").read_text(encoding="utf-8")
    _, job = c.request("POST", "/api/tools/demo/jobs", {"source": "keyjob", "seconds": 0, "mode": "done"})   # nor in a job's events
    conn, res = c.stream("/api/jobs/demo/keyjob/events")
    streamed = read_sse(res, lambda m: any(x[1] == "job" and x[2]["type"] == "done" for x in m))
    conn.close()
    assert SECRET not in json.dumps(streamed) and SECRET not in (tmp_path / "jobs" / "keyjob" / "events.jsonl").read_text(encoding="utf-8")
    for path in ("/api/state", "/api/doctor", "/api/jobs", "/api/settings", "/api/settings/agents", "/api/tools/demo/agents"):
        assert SECRET not in json.dumps(c.request("GET", path)[1])


def test_streammoment_is_one_account_without_a_key_and_its_api_needs_the_token(server, monkeypatch):
    """Stage 22: StreamMoment is offered first, added once, has no key; signing in and buying go through the token-guarded
    API; the account (no network without ?live=1) says who is signed in and never any token."""
    _, c, *_ = server
    choices = c.request("GET", "/api/settings")[1]["choices"]
    assert choices[0]["choice"] == "streammoment" and choices[0]["account"] and not choices[0]["needs_key"]
    status, body = c.request("POST", "/api/settings/providers", {"kind": "streammoment"})
    assert status == 201
    p = next(x for x in body["providers"] if x["kind"] == "streammoment")
    assert p["key"]["needed"] is False
    assert c.request("POST", "/api/settings/providers", {"kind": "streammoment"})[0] == 409
    assert c.request("GET", "/api/account")[1]["signed_in"] is False
    from smtv_core import account
    account._save({"access_token": "a-secret", "refresh_token": "r-secret", "expires_in": 3600, "account": {"name": "Аня", "provider": "google"}})
    state = c.request("GET", "/api/account")[1]
    assert state["signed_in"] and state["account"]["name"] == "Аня" and "secret" not in json.dumps(state)
    monkeypatch.setenv("SMTV_ACCOUNT_URL", "http://127.0.0.1:9")       # nobody there: the window says so and suggests the VPN
    checked = c.request("POST", "/api/account/check", {})[1]
    assert checked["account"] and not checked["reachable"] and "VPN" in checked["hint"]
    assert c.request("POST", "/api/account/buy", {"package": "../x"})[0] == 400
    out = c.request("POST", "/api/account/logout", {})[1]
    assert out["signed_in"] is False and out["server_signed_out"] is False
    for path in ("/api/account/login", "/api/account/logout", "/api/account/buy", "/api/account/check"):
        assert c.request("POST", path, {}, headers={"X-SMTV-Token": None})[0] == 403


def test_a_wrong_provider_or_field_is_refused(server):
    _, c, *_ = server
    assert c.request("POST", "/api/settings/providers", {"kind": "nonsense"})[0] == 400
    assert c.request("POST", "/api/settings/providers", {"kind": "openai", "preset": "elsewhere"})[0] == 400
    assert c.request("POST", "/api/settings/providers", {"kind": "openai", "preset": "custom"})[0] == 400        # no address
    assert c.request("POST", "/api/settings/providers", {"kind": "openai", "preset": "custom", "base_url": "ftp://x"})[0] == 400
    pid, _ = add(c, kind="gemini")
    assert c.request("POST", f"/api/settings/providers/{pid}", {"enabled": "yes"})[0] == 400
    assert c.request("POST", f"/api/settings/providers/{pid}", {"default_model": "a b"})[0] == 400
    assert c.request("POST", "/api/settings/providers/nope", {"name": "x"})[0] == 404
    assert c.request("POST", "/api/settings/providers/nope/delete", {})[0] == 404


def test_the_clis_need_no_key_and_are_not_offered_by_default(server):
    _, c, *_ = server
    _, s = c.request("GET", "/api/settings")
    assert s["providers"] == []                                  # nothing is chosen for the person, no CLI either
    choices = {x["choice"]: x for x in s["choices"]}
    assert list(choices) == ["streammoment", "openai", "openrouter", "custom", "anthropic", "gemini",
                             "ollama", "lmstudio", "vllm", "llamacpp",
                             "deepseek", "groq", "mistral", "xai", "together", "fireworks", "qwen", "kimi", "glm", "cerebras",
                             "codex", "claude_code"]
    for cli in ("codex", "claude_code"):
        assert choices[cli]["cli"] and not choices[cli]["needs_key"] and choices[cli]["steps"]
        assert all(r["url"].startswith("https://") for r in choices[cli]["rules"]) and len(choices[cli]["rules"]) >= 2
    assert "code.claude.com/docs/en/legal-and-compliance" in json.dumps(choices["claude_code"]["rules"])
    assert "openai.com/policies/terms-of-use" in json.dumps(choices["codex"]["rules"])
    status, body = c.request("POST", "/api/settings/providers", {"kind": "codex", "key": SECRET})
    assert status == 400 and body["error"] == "no_key_needed" and SECRET not in json.dumps(body)
    from smtv_core.settings import Settings
    assert Settings.load().providers == []                         # a refused add leaves nothing behind


def test_several_providers_of_one_kind_and_removing_one(server):
    _, c, *_ = server
    from smtv_core.settings import Settings, get_secret
    one, _ = add(c, kind="openai", preset="openai", name="OpenAI — personal", key="sk-personal-000000000000")
    two, data = add(c, kind="openai", preset="openai", name="OpenAI — work", key="sk-work-000000000000000")
    assert (one, two) == ("openai", "openai-2") and data["can_recommend"] == 1           # layout; finder is not in the table
    names = [p["name"] for p in data["providers"]]
    assert names == ["OpenAI — personal", "OpenAI — work"]
    s = Settings.load()
    assert get_secret(s.provider(one).key_name()) == "sk-personal-000000000000"
    assert get_secret(s.provider(two).key_name()) == "sk-work-000000000000000"
    status, agents_ = c.request("POST", "/api/settings/agents/demo/layout", {"provider": two, "model": "gpt-6.2-astra"})
    assert status == 200
    c.request("POST", f"/api/settings/providers/{two}/delete", {})
    s = Settings.load()
    assert [p.id for p in s.providers] == [one] and get_secret("provider.openai-2") is None
    assert "agents" not in s.tools.get("demo", {})                  # its agents follow the recommendations of the rest
    _, agents_ = c.request("GET", "/api/settings/agents")
    layout = [a for g in agents_["groups"] for a in g["agents"] if a["id"] == "layout"][0]
    assert (layout["current"]["provider"], layout["current"]["model"], layout["current"]["source"]) == (one, "gpt-6.1-terra", "recommended")


# --- tools, switches, doctor ----------------------------------------------------------------------------

def test_state_lists_tools_and_their_sections(server):
    _, c, *_ = server
    _, state = c.request("GET", "/api/state")
    assert [t["name"] for t in state["tools"]] == ["demo"] and state["tools"][0]["page"]["title"] == "Demo"
    assert {t["name"] for t in state["catalog"]} >= {"vodcut"}
    assert c.request("GET", "/tools/demo/section.js")[0] == 200
    assert c.request("GET", "/tools/demo/../../etc/passwd")[0] == 404


def test_switches_change_and_bad_ones_are_refused(server):
    _, c, *_ = server
    assert c.request("POST", "/api/tools/demo/options", {"name": "loud", "value": False})[1][0]["value"] is False
    assert c.request("GET", "/api/tools/demo/options")[1][0]["value"] is False
    assert c.request("POST", "/api/tools/demo/options", {"name": "nope", "value": True})[0] == 400
    assert c.request("POST", "/api/tools/demo/options", {"name": "loud", "value": "yes"})[0] == 400


def test_doctor_gives_rows_with_fixes(server, monkeypatch):
    _, c, *_ = server
    monkeypatch.setattr("smtv_core.checks.core_checks", lambda s, v=None: [Check("ffmpeg", "fail", "not found", "brew install ffmpeg-full")])
    _, d = c.request("GET", "/api/doctor")
    assert d["ready"] is False
    row = lambda name: next({k: r[k] for k in ("name", "status", "detail", "fix", "group")} for r in d["rows"] if r["name"] == name)
    assert row("ffmpeg") == {"name": "ffmpeg", "status": "fail", "detail": "not found", "fix": "brew install ffmpeg-full", "group": "smtv"}
    assert row("demo: thing") == {"name": "demo: thing", "status": "ok", "detail": "fine", "fix": "", "group": "demo"}   # the tool's own, under its name   # the tool's own checks, under its name


def test_estimate_and_bad_fields(server):
    _, c, *_ = server
    assert c.request("POST", "/api/tools/demo/estimate", {"source": "x"})[1]["seconds"] == 60
    status, body = c.request("POST", "/api/tools/demo/jobs", {})
    assert status == 400 and body["message"] == "paste a link or choose a file"


# --- live events ------------------------------------------------------------------------------------------

def test_events_resume_after_last_event_id_without_loss_or_repeat(server):
    _, c, root, _ = server
    job = root / "live"
    j = Journal(job, tool="demo", subscribers=[])
    j.emit("stage", name="speech")
    for i in range(4):
        j.emit("progress", stage="speech", percent=i * 10)
    conn, res = c.stream("/api/jobs/demo/live/events", headers={"Last-Event-ID": "3"})
    assert res.status == 200 and res.getheader("Content-Type").startswith("text/event-stream")
    got = read_sse(res, lambda m: sum(1 for x in m if x[1] == "job") >= 2)
    jobs = [m for m in got if m[1] == "job"]
    assert [m[0] for m in jobs] == ["4", "5"] and [m[2]["n"] for m in jobs] == [4, 5]       # id: is the event number
    j.emit("progress", stage="speech", percent=60)                                            # a new event arrives live
    more = read_sse(res, lambda m: any(x[1] == "job" for x in m))
    assert [m[2]["n"] for m in more if m[1] == "job"] == [6]
    conn.close()
    conn, res = c.stream("/api/jobs/demo/live/events?after=5")                                 # the same through the query
    got = read_sse(res, lambda m: any(x[1] == "job" for x in m) and any(x[1] == "status" for x in m))
    assert [m[2]["n"] for m in got if m[1] == "job"] == [6]
    status = [m[2] for m in got if m[1] == "status"]
    assert status and status[0]["running"] is False and status[0]["status"] == "unfinished"
    conn.close()


def test_a_torn_last_line_is_not_sent_until_it_is_complete(tmp_path):
    path = tmp_path / "events.jsonl"
    path.write_text('{"n": 1, "type": "stage"}\n{"n": 2, "ty', encoding="utf-8")
    tail = jobs_module.Tail(path)
    assert [e["n"] for e in tail.read()] == [1]
    with path.open("a", encoding="utf-8") as f:
        f.write('pe": "stage"}\n')
    assert [e["n"] for e in tail.read()] == [2] and tail.read() == []


# --- jobs ---------------------------------------------------------------------------------------------------

def wait_for(fn, timeout=10.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = fn()
        if value:
            return value
        time.sleep(0.05)
    raise AssertionError("timed out")


def test_start_runs_the_job_in_its_own_process_and_cancel_stops_it(server):
    _, c, root, app = server
    status, job = c.request("POST", "/api/tools/demo/jobs", {"source": "j1", "seconds": 60})
    assert status == 201 and job["status"] == "running" and job["restart"] is True
    wait_for(lambda: (root / "j1" / "events.jsonl").exists())
    status, second = c.request("POST", "/api/tools/demo/jobs", {"source": "j2"})       # one running job per tool:
    assert status == 201 and second["status"] == "queued"                                  # the second one waits
    c.request("POST", "/api/jobs/demo/j2/cancel")                                          # (out of the queue: this test is about j1)
    process = app.runner.running("demo", "j1").process
    status, after = c.request("POST", "/api/jobs/demo/j1/cancel")
    assert status == 200 and after["status"] == "cancelled" and process.poll() is not None
    from smtv_core.events import read
    events = read(root / "j1")
    assert events[-1]["type"] == "cancelled" and events[-1]["data"] == {"by": "user", "stage": "audio"}
    assert all(contract.validate(e) == [] and contract.undeclared(e) == [] for e in events)
    assert c.request("POST", "/api/jobs/demo/j1/cancel")[0] == 409                         # nothing left to cancel
    assert (root / "j1" / "run.log").exists()


def test_a_job_that_dies_silently_gets_an_error_event(server):
    _, c, root, app = server
    c.request("POST", "/api/tools/demo/jobs", {"source": "j3", "seconds": 0, "code": 3, "mode": "quiet"})
    wait_for(lambda: app.runner.runs[("demo", "j3")].finished.is_set())
    _, job = c.request("GET", "/api/jobs/demo/j3")
    assert job["status"] == "failed"
    from smtv_core.events import read
    last = read(root / "j3")[-1]
    assert last["type"] == "error" and last["data"]["stage"] == "process" and last["data"]["exit_code"] == 3
    assert contract.validate(last) == [] and contract.undeclared(last) == []


def test_a_finished_job_is_listed_and_can_run_again(server):
    _, c, root, app = server
    c.request("POST", "/api/tools/demo/jobs", {"source": "j4", "seconds": 0, "mode": "done"})
    wait_for(lambda: app.runner.runs[("demo", "j4")].finished.is_set())
    _, listed = c.request("GET", "/api/jobs")
    assert [(j["id"], j["status"], j["title"]) for j in listed] == [("j4", "done", "a stream")]
    status, again = c.request("POST", "/api/jobs/demo/j4/restart")
    assert status == 201 and again["status"] == "running"
    wait_for(lambda: app.runner.runs[("demo", "j4")].finished.is_set())
    from smtv_core.events import read
    assert [e["n"] for e in read(root / "j4")] == [1, 2, 3, 4]                               # numbers continue across runs


def test_a_job_started_elsewhere_cannot_be_restarted_from_the_page(server):
    _, c, root, _ = server
    Journal(root / "cli", tool="demo", subscribers=[]).emit("stage", name="audio")
    assert c.request("POST", "/api/jobs/demo/cli/restart")[0] == 409
    assert c.request("GET", "/api/jobs/demo/nope")[0] == 404


def test_upload_lands_in_the_data_folder(server, tmp_path):
    _, c, *_ = server
    conn = http.client.HTTPConnection("127.0.0.1", c.port, timeout=10)
    conn.request("PUT", "/api/uploads", body=b"video-bytes", headers={"Host": f"127.0.0.1:{c.port}", "X-SMTV-Token": c.token, "X-File-Name": "my%20stream.mp4"})
    res = conn.getresponse()
    body = json.loads(res.read())
    assert res.status == 201 and Path(body["path"]).read_bytes() == b"video-bytes" and Path(body["path"]).name == "my-stream.mp4"
    conn = http.client.HTTPConnection("127.0.0.1", c.port, timeout=10)
    conn.request("PUT", "/api/uploads", body=b"x", headers={"Host": f"127.0.0.1:{c.port}", "X-File-Name": "a.mp4"})      # not from the page
    assert conn.getresponse().status == 403


# --- launch without a terminal: fixed port, installable page, "not running" page -----------------------------------

def test_hello_says_it_is_smtv_and_obeys_the_host_check(server):
    _, c, _, app = server
    status, body = c.request("GET", "/api/hello")
    assert status == 200 and body["app"] == "smtv" and c.token not in json.dumps(body)
    assert c.request("GET", "/api/hello", host=f"evil.example:{c.port}")[0] == 403
    assert serve.probe(c.port) == body


def test_a_taken_port_is_an_error_not_another_port(server):
    import socket
    srv, *_ = server
    with pytest.raises(serve.PortBusy) as e:                         # SMTV itself is there
        serve.make_server(serve.App([], []), srv.server_address[1])
    assert e.value.smtv and "already running" in serve.busy_message(e.value)
    other = socket.socket()
    other.bind(("127.0.0.1", 0))
    other.listen()
    port = other.getsockname()[1]
    try:
        with pytest.raises(serve.PortBusy) as e:
            serve.make_server(serve.App([], []), port)
        assert not e.value.smtv
        assert f"Port {port}" in serve.busy_message(e.value) and "another program" in serve.busy_message(e.value)
    finally:
        other.close()


def test_serve_on_a_port_taken_by_another_program_exits_with_a_clear_message(capsys, monkeypatch):
    monkeypatch.setattr(serve, "make_server", lambda app, port: (_ for _ in ()).throw(serve.PortBusy(port, False)))
    assert serve.serve([], [], port=8642, open_browser=False) == 2
    assert "taken by another program" in capsys.readouterr().out


def test_the_page_knows_it_is_in_smtvs_window_from_the_first_frame(server):
    _, c, *_ = server
    _, page = c.request("GET", "/?window=mac", raw=True)
    assert b'<html lang="en" class="shell shell-mac">' in page
    _, page = c.request("GET", "/?window=evil%22%3E%3Cscript%3E", raw=True)      # only known windows, nothing else
    assert b'<html lang="en">' in page and b"<script>" not in page.split(b"</head>")[0].split(b"<html")[1][:200]
    for gone in ("/sw.js", "/manifest.webmanifest", "/offline"):                 # no installable-page parts any more
        assert c.request("GET", gone, raw=True)[0].status == 404


def test_a_second_start_can_only_bring_the_window_forward_with_the_token(server):
    _, c, _, app = server
    shown = []
    assert c.request("POST", "/api/window/show", {}, headers={"X-SMTV-Token": None})[0] == 403
    assert c.request("POST", "/api/window/show", {})[0] == 409            # started with smtv serve: no window
    app.show_window = lambda: shown.append(1)
    assert c.request("POST", "/api/window/show", {}) == (200, {"shown": True}) and shown == [1]


# --- stage 7: the window's places for tools, the list of requests, tokens -------------------------------------

def test_state_says_where_each_tool_plugs_into_the_window(tmp_path):
    from smtv_core.tool import NavItem, RequestKind
    tool = make_tool(tmp_path / "jobs")
    tool.page.request = RequestKind(title="request.title", icon="<path/>")      # a key of the tool's words
    tool.page.nav = NavItem(id="live-streams", title="Live streams")
    tool.page.about, tool.page.icon = "What it does", "<circle/>"                # no such key: shown as it is
    state = serve.App([tool], []).state()
    page = state["tools"][0]["page"]
    assert page["request"] == {"title": {"en": "Recording", "ru": "Запись"}, "about": {}, "icon": "<path/>"}
    assert page["nav"] == {"id": "live-streams", "title": {"en": "Live streams"}, "icon": ""}
    assert page["about"] == {"en": "What it does"} and page["icon"] == "<circle/>"
    tool.page.nav = NavItem(id="../evil", title="x")                 # an item id goes into the address: only a-z, 0-9, -
    assert serve.App([tool], []).state()["tools"][0]["page"]["nav"] is None


def test_a_tool_without_places_leaves_no_trace(tmp_path):
    state = serve.App([make_tool(tmp_path / "jobs")], []).state()
    page = state["tools"][0]["page"]
    assert page["request"] is None and page["nav"] is None
    assert serve.App([], []).state()["tools"] == []


def test_plugins_list_installed_broken_available_and_soon(tmp_path):
    from smtv.tools import Broken
    state = serve.App([make_tool(tmp_path / "jobs")], [Broken("vodcut", "ImportError: no module named x")]).state()
    by = {p["name"]: p for p in state["plugins"]}
    assert by["demo"]["status"] == "installed" and by["demo"]["version"] == "1.0"
    assert by["vodcut"]["status"] == "broken" and "ImportError" in by["vodcut"]["error"]   # shown as broken, not as «can be added»
    assert by["livecut"]["status"] == "soon"
    assert [p["name"] for p in state["plugins"]].count("vodcut") == 1
    state = serve.App([], []).state()
    assert {p["name"]: p["status"] for p in state["plugins"]} == {
        "vodcut": "available", "livecut": "soon", "mcp": "soon", "autopublish": "soon", "tiktok-hashtags": "soon", "tiktok-music": "soon"}


def test_the_announced_plugins_are_exactly_the_soon_list():
    """Stage 13: MCP, auto-publishing and the two TikTok helpers are announced next to LiveCut; none of them can be added."""
    from smtv.tools import CATALOG, SOON
    assert list(SOON) == ["livecut", "mcp", "autopublish", "tiktok-hashtags", "tiktok-music"]
    assert not set(SOON) & set(CATALOG)
    assert all(summary.strip() for summary in SOON.values())
    cards = [p for p in serve.App([], []).state()["plugins"] if p["status"] == "soon"]
    assert [p["name"] for p in cards] == list(SOON)
    assert all("add" not in p and "version" not in p for p in cards)    # nothing on a «soon» card installs anything


def test_a_tool_whose_jobs_cannot_be_read_does_not_hide_the_others(tmp_path):
    good = make_tool(tmp_path / "jobs")
    (tmp_path / "jobs" / "a1").mkdir(parents=True)
    with Journal(tmp_path / "jobs" / "a1", tool="demo", subscribers=[]) as j:
        j.emit("stage", name="audio", step=1, steps=5)
    bad = make_tool(tmp_path / "other")
    bad.name = "bad"
    bad.page.jobs = lambda: (_ for _ in ()).throw(PermissionError("no access"))
    app = serve.App([good, bad], [])
    with redirect_stderr(io.StringIO()):
        assert [j["id"] for j in app.jobs()] == ["a1"]
        assert app.tokens()["calls"] == 0


def test_requests_of_every_tool_in_one_list_newest_first(tmp_path):
    one, two = make_tool(tmp_path / "one"), make_tool(tmp_path / "two")
    two.name = "other"
    for root, job, t in ((tmp_path / "one", "old", 100), (tmp_path / "two", "new", 200)):
        (root / job).mkdir(parents=True)
        (root / job / "events.jsonl").write_text(json.dumps({"n": 1, "t": t, "type": "stage", "v": "1.1", "job": job, "tool": "x", "data": {"name": "audio"}}) + "\n", encoding="utf-8")
        import os
        os.utime(root / job / "events.jsonl", (t, t))
    jobs = serve.App([one, two], []).jobs()
    assert [(j["tool"], j["id"]) for j in jobs] == [("other", "new"), ("demo", "old")]


def test_tokens_are_the_sum_of_model_calls_in_every_journal(server, tmp_path):
    _, c, root, _ = server
    for job, calls in (("j1", [(100, 20, 0.01), (None, None, None)]), ("j2", [(5, 5, None)])):
        (root / job).mkdir(parents=True)
        with Journal(root / job, tool="demo", subscribers=[]) as j:
            j.emit("stage", name="scan", step=3, steps=6)
            for tin, tout, cost in calls:
                data = {"purpose": "scan", "seconds": 1.0, "model": "m"}
                if tin is not None:
                    data.update(tokens_in=tin, tokens_out=tout)
                if cost is not None:
                    data["cost_usd"] = cost
                j.emit("model_call", **data)
    status, u = c.request("GET", "/api/usage")
    assert status == 200
    assert (u["calls"], u["tokens_in"], u["tokens_out"], u["tokens"], u["unreported"]) == (3, 105, 25, 130, 1)
    assert u["cost_known"] is True and abs(u["cost_usd"] - 0.01) < 1e-9
    with Journal(root / "j2", tool="demo", subscribers=[]) as j:          # a journal that grew is read again
        j.emit("model_call", purpose="rating", seconds=1.0, model="m", tokens_in=1, tokens_out=1)
    assert c.request("GET", "/api/usage")[1]["tokens"] == 132


def test_usage_is_a_plain_get_that_changes_nothing(server):
    _, c, *_ = server
    assert c.request("GET", "/api/usage", host="evil.example:80")[0] == 403      # the host check holds here too
    assert c.request("POST", "/api/usage", {})[0] == 404


def test_a_damaged_journal_does_not_break_the_tokens_of_the_others(server):
    _, c, root, _ = server
    for job, data in (("good", {"purpose": "scan", "seconds": 1.0, "model": "m", "tokens_in": 10, "tokens_out": 5}),
                      ("bad1", "oops"), ("bad2", {"purpose": "scan", "tokens_in": True, "tokens_out": -7, "cost_usd": -1})):
        (root / job).mkdir(parents=True)
        (root / job / "events.jsonl").write_text(json.dumps({"n": 1, "t": 1, "type": "model_call", "v": "1.1", "job": job, "tool": "demo", "data": data}) + "\n", encoding="utf-8")
    status, u = c.request("GET", "/api/usage")
    assert status == 200
    assert (u["calls"], u["tokens"], u["unreported"], u["cost_known"]) == (2, 15, 1, False)


def test_usage_reads_only_the_new_lines_of_a_journal_and_forgets_removed_ones(tmp_path, monkeypatch):
    """B27: a running job adds a line a second; the window asks for the tokens every second. Only the new lines are
    read — never the whole journal again — and a journal replaced by a shorter one is counted from its start."""
    from smtv import usage
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"

    def line(n, tokens=1, kind="model_call"):
        return json.dumps({"n": n, "t": n, "type": kind, "v": "1.1", "job": "x", "tool": "demo",
                           "data": {"purpose": "scan", "tokens_in": tokens, "tokens_out": tokens}}) + "\n"
    a.write_text("".join(line(n) for n in range(1, 501)), encoding="utf-8")
    b.write_text(line(1), encoding="utf-8")
    monkeypatch.setattr(usage, "journal_usage", lambda p: (_ for _ in ()).throw(AssertionError(f"{p.name} read whole")))
    u = usage.Usage()
    assert u.total([a, b])["tokens"] == 1002
    reads = []
    real_read = usage.Tail.read
    monkeypatch.setattr(usage.Tail, "read", lambda self: (lambda got: (reads.append((self.path.name, len(got))), got)[1])(real_read(self)))
    with a.open("a", encoding="utf-8") as f:
        f.write(line(501, 10) + line(502, kind="stage") + '{"n": 503, "type": "model_call", "da')   # the last one half-written
    total = u.total([a, b])
    assert total["tokens"] == 1022 and total["calls"] == 502
    assert reads == [("a.jsonl", 2), ("b.jsonl", 0)]                           # two new events, nothing else
    assert u.by_purpose([a, b])["scan"]["calls"] == 502
    with a.open("a", encoding="utf-8") as f:
        f.write('ta": {"tokens_in": 3, "tokens_out": 0}}\n')                 # the half line completed
    assert u.total([a, b])["tokens"] == 1025
    a.write_text(line(1, 7), encoding="utf-8")                                   # replaced by a shorter journal
    assert u.total([a, b])["tokens"] == 16
    b.unlink()
    assert u.total([a, b])["tokens"] == 14 and set(u._cache) == {a}


def test_doctor_a_crashing_or_broken_tool_gets_one_failed_row_under_its_name(tmp_path, monkeypatch):
    from smtv.tools import Broken
    monkeypatch.setattr("smtv_core.checks.core_checks", lambda s, v=None: [Check("python", "ok", "fine")])
    tool = make_tool(tmp_path / "jobs")
    tool.checks = lambda s: (_ for _ in ()).throw(RuntimeError("boom"))
    d = serve.App([tool], [Broken("vodcut", "ImportError: x")]).doctor()
    groups = [r["group"] for r in d["rows"]]
    assert groups[0] == "smtv" and "Clip It! window" in [r["name"] for r in d["rows"] if r["group"] == "smtv"]
    demo = [r for r in d["rows"] if r["group"] == "demo"]
    assert len(demo) == 1 and demo[0]["status"] == "fail" and "boom" in demo[0]["detail"]
    broken = [r for r in d["rows"] if r["group"] == "vodcut"]
    assert broken[0]["fix"] == "smtv add vodcut" and d["ready"] is False
    tool.checks = lambda s: []                                                 # no checks: no empty group
    assert "demo" not in {r["group"] for r in serve.App([tool], []).doctor()["rows"]}


def test_a_job_removed_between_listing_and_look_is_skipped(tmp_path, monkeypatch):
    tool = make_tool(tmp_path / "jobs")
    for job in ("keep", "gone"):
        (tmp_path / "jobs" / job).mkdir(parents=True)
        (tmp_path / "jobs" / job / "events.jsonl").write_text("", encoding="utf-8")
    app = serve.App([tool], [])
    real = app._job_base
    monkeypatch.setattr(app, "_job_base", lambda name, job: (_ for _ in ()).throw(serve.ApiError(404, "no_job")) if job == "gone" else real(name, job))
    assert [j["id"] for j in app.jobs()] == ["keep"]


def test_plugins_a_tool_without_a_page_and_an_installed_soon_tool(tmp_path):
    tool = make_tool(tmp_path / "jobs")
    tool.name, tool.page = "livecut", None
    by = {p["name"]: p for p in serve.App([tool], []).state()["plugins"]}
    assert by["livecut"]["status"] == "installed" and by["livecut"]["title"] == "livecut" and by["livecut"]["icon"] == ""


def test_a_request_is_deleted_only_when_confirmed_with_the_token_and_not_while_it_runs(server):
    _, c, root, app = server
    (root / "old").mkdir(parents=True)
    with Journal(root / "old", tool="demo", subscribers=[]) as j:
        j.emit("stage", name="audio", step=1, steps=5)
    (root / "old" / "clips").mkdir()
    (root / "old" / "clips" / "clip01.mp4").write_bytes(b"x")
    assert c.request("POST", "/api/jobs/demo/old/delete", {"confirm": "delete"}, headers={"X-SMTV-Token": None})[0] == 403
    assert c.request("POST", "/api/jobs/demo/old/delete", {"confirm": "delete"}, headers={"Origin": "http://evil.example"})[0] == 403
    assert c.request("POST", "/api/jobs/demo/old/delete", {})[0] == 400                   # the page asks first
    assert c.request("GET", "/api/jobs/demo/old/delete")[0] == 404                        # a link never deletes
    assert (root / "old").is_dir()
    assert c.request("POST", "/api/jobs/demo/old/delete", {"confirm": "delete"}) == (200, {"deleted": True})
    assert not (root / "old").exists()
    assert c.request("POST", "/api/jobs/demo/old/delete", {"confirm": "delete"})[0] == 404
    assert c.request("POST", "/api/jobs/demo/..%2F..%2Fetc/delete", {"confirm": "delete"})[0] == 404
    status, job = c.request("POST", "/api/tools/demo/jobs", {"source": "live", "seconds": 30})
    assert status == 201
    try:
        assert c.request("POST", "/api/jobs/demo/live/delete", {"confirm": "delete"})[0] == 409   # running: cancel first
        assert (root / "live").is_dir()
    finally:
        c.request("POST", "/api/jobs/demo/live/cancel", {})


def test_pause_is_asked_with_the_token_only_while_running_and_a_new_run_clears_it(server):
    from smtv_core import pause
    _, c, root, app = server
    app.tools["demo"].page.pause = True
    status, job = c.request("POST", "/api/tools/demo/jobs", {"source": "slow", "seconds": 30})
    assert status == 201
    try:
        assert c.request("POST", "/api/jobs/demo/slow/pause", {}, headers={"X-SMTV-Token": None})[0] == 403
        status, body = c.request("POST", "/api/jobs/demo/slow/pause", {})
        assert status == 200 and body["pausing"] is True and pause.requested(root / "slow")
    finally:
        c.request("POST", "/api/jobs/demo/slow/cancel", {})
    assert c.request("POST", "/api/jobs/demo/slow/pause", {})[0] == 409            # not running
    pause.ask(root / "slow")
    c.request("POST", "/api/jobs/demo/slow/restart", {})
    try:
        assert not pause.requested(root / "slow")                                 # «Continue» starts without the old request
    finally:
        c.request("POST", "/api/jobs/demo/slow/cancel", {})
    app.tools["demo"].page.pause = False
    c.request("POST", "/api/tools/demo/jobs", {"source": "plain", "seconds": 30})
    try:
        assert c.request("POST", "/api/jobs/demo/plain/pause", {})[1]["error"] == "no_pause"   # a tool that cannot pause
    finally:
        c.request("POST", "/api/jobs/demo/plain/cancel", {})


def test_run_again_starts_a_new_request_and_leaves_the_old_one(server):
    from smtv_core.tool import JobStart
    _, c, root, app = server
    assert c.request("POST", "/api/tools/demo/jobs", {"source": "first", "seconds": 0.2, "mode": "done"})[0] == 201
    for _ in range(50):
        if not app.runner.running("demo", "first"):
            break
        time.sleep(0.1)
    assert c.request("POST", "/api/jobs/demo/first/again", {})[1]["error"] == "no_again"            # a tool without it
    app.tools["demo"].page.again = lambda folder, args: JobStart(root / "first-2", args)
    assert c.request("POST", "/api/jobs/demo/first/again", {}, headers={"X-SMTV-Token": None})[0] == 403
    status, job = c.request("POST", "/api/jobs/demo/first/again", {})
    try:
        assert status == 201 and job["id"] == "first-2" and (root / "first").is_dir()
    finally:
        c.request("POST", "/api/jobs/demo/first-2/cancel", {})


# --- stage 8: the window's one stream, updates and plugins ---------------------------------------------------------

def test_the_window_stream_starts_with_the_whole_picture_then_sends_changes(server):
    srv, client, root, app = server
    conn, res = client.stream("/api/window/events?lang=ru")
    assert res.status == 200 and res.getheader("Content-Type").startswith("text/event-stream")
    first = read_sse(res, lambda m: any(e == "snapshot" for _, e, _ in m))
    snap = next(d for _, e, d in first if e == "snapshot")
    assert snap["jobs"] == [] and snap["activity"]["running"] == 0 and "update" in snap and "usage" in snap
    assert app.lang == "ru" and app.viewers >= 1           # an open window counts as an open page
    status, job = client.request("POST", "/api/tools/demo/jobs", {"source": "s8", "seconds": 0.3, "mode": "done"})
    assert status == 201
    got = read_sse(res, lambda m: any(e == "job" and d["id"] == "s8" and d["status"] == "done" for _, e, d in m), timeout=15)
    assert any(e == "activity" for _, e, _ in got)            # it ran: the header saw it
    import shutil
    shutil.rmtree(root / "s8")
    read_sse(res, lambda m: any(e == "job_gone" and d == {"tool": "demo", "id": "s8"} for _, e, d in m), timeout=10)
    conn.close()


def test_the_window_stream_obeys_the_host_check(server):
    _, client, _, _ = server
    status, _ = client.request("GET", "/api/window/events", host="evil.example:80")
    assert status == 403


def test_hello_names_the_installed_tools(server):
    _, client, _, _ = server
    status, data = client.request("GET", "/api/hello")
    assert data == {"app": "smtv", "version": serve.__version__, "tools": ["demo"]}


def test_update_actions_need_the_token_and_refuse_names_outside_the_catalog(server, monkeypatch):
    _, client, _, app = server
    spawned = []
    app.updates.spawn = spawned.append
    app.updates.kind = "uv"
    for path in ("/api/plugins/vodcut/install", "/api/plugins/vodcut/remove", "/api/updates/update", "/api/updates/check",
                 "/api/updates/settings", "/api/updates/cancel"):
        status, data = client.request("POST", path, {}, headers={"X-SMTV-Token": None})
        assert status == 403, path
    from smtv.tools import SOON
    for name in ("evil", "smtv", "..%2Fvodcut", *SOON):
        status, data = client.request("POST", f"/api/plugins/{name}/install", {})
        assert status in (404, 409) and data.get("error") in ("not_in_catalog", "not_found"), (name, data)
    status, data = client.request("POST", "/api/plugins/vodcut/install", {"now": "yes"})
    assert status == 400
    assert spawned == []
    # a GET changes nothing
    status, data = client.request("GET", "/api/plugins/vodcut/install")
    assert status == 404 and spawned == []


def test_the_update_check_setting_is_kept(server):
    _, client, _, _ = server
    status, data = client.request("POST", "/api/updates/settings", {"check": False})
    assert status == 200 and data["check"] is False
    status, data = client.request("GET", "/api/updates")
    assert data["check"] is False and data["kind"] == "dev"
    assert client.request("POST", "/api/updates/settings", {"check": "no"})[0] == 400


def test_a_dev_install_is_never_changed_from_the_window(server):
    _, client, _, app = server
    status, data = client.request("POST", "/api/plugins/vodcut/install", {})
    assert status == 409 and data["error"] == "cannot_update"


# --- agents on a plugin's page (stage 10) ------------------------------------------------------------------------

def test_a_plugin_page_lists_its_agents_with_prompt_schema_models_and_stats(server):
    srv, c, root, app = server
    add(c, kind="anthropic", key=SECRET)
    (root / "j1").mkdir()
    with Journal(root / "j1", tool="demo", subscribers=[]) as j:
        j.emit("model_call", purpose="scan", seconds=2.0, model="m", cost_usd=0.5)
        j.emit("model_call", purpose="scan_repair", seconds=4.0, model="m")
        j.emit("model_call", purpose="layout", error="busy: 529", model="m")
        j.emit("model_call", purpose="rating", seconds=9.0, model="m")
    status, data = c.request("GET", "/api/tools/demo/agents")
    assert status == 200 and SECRET not in json.dumps(data)
    assert data["prompts"]["version"] == "1.1.0" and data["prompts"]["date"] and data["providers"] == 1
    finder, layout = data["agents"]
    assert finder["id"] == "finder" and not finder["shared"] and finder["prompt"] == "vod/pass1-prompt.txt"
    assert finder["prompt_text"].strip() and finder["needs"]["level"] == "strong" and finder["purposes"] == ["scan", "scan_repair"]
    assert json.loads(finder["schema_text"])["type"] == "object"
    assert finder["current"]["source"] == "none"            # no recommendation for an unknown agent, no default model
    # words come from the language files (V9): the tool's for its own agent, the window's for the core's shared one
    assert finder["title"] == {"en": "Finder", "ru": "Поиск"} and finder["needs"]["why"] == {"en": "reads a lot"}
    assert finder["short"] == {} and finder["needs"]["text"] == {}          # a field no file has: empty, never the key
    assert layout["title"]["ru"] == "Раскладка" and layout["needs"]["why"]["en"].startswith("Medium with images")
    assert finder["stats"] == {"calls": 2, "avg_s": 3.0, "errors": 0, "cost_usd": 0.5}
    assert layout["shared"] and layout["users"] == ["demo"]
    cur = layout["current"]
    assert (cur["provider"], cur["provider_name"], cur["model"], cur["source"], cur["recommended"], cur["tested"]) == (
        "anthropic", "Claude API", "claude-sonnet-5-5", "recommended", True, [])
    assert cur["price"] == {"kind": "table", "in": 2.0, "out": 10.0} and cur["images"] is True
    assert layout["stats"] == {"calls": 1, "avg_s": None, "errors": 1, "cost_usd": None}
    recs = {r["provider"]: r for r in layout["recommendations"]}
    assert recs["codex"]["model"] == "" and recs["codex"]["label"] == "Codex CLI" and recs["codex"]["tested"]
    assert layout["recommendations"][0]["provider"] == "anthropic" and layout["recommendations"][0]["connected"]
    assert "claude_code" not in recs                          # it cannot pass frames: no recommendation for layout there
    # the plugin's tab is read only: there is no way to change a model from it any more
    assert c.request("POST", "/api/tools/demo/agents/layout/model", {"model": "x"})[0] == 404
    assert c.request("GET", "/api/tools/demo/agents/layout/models")[0] == 404


def test_a_shared_agent_shows_on_the_page_of_every_plugin_that_uses_it(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    one = make_tool(a)
    two = Tool(name="other", summary="other", version="1.0", add_commands=lambda p: None, agents=agents.core("layout", "banner"))
    app = serve.App([one, two], [])
    cards = {name: {x["id"]: x for x in app.agents(name)["agents"]} for name in ("demo", "other")}
    assert cards["demo"]["layout"]["users"] == cards["other"]["layout"]["users"] == ["demo", "other"]
    assert cards["demo"]["layout"]["prompt_text"] == cards["other"]["layout"]["prompt_text"]
    assert "finder" not in cards["other"] and cards["other"]["banner"]["users"] == ["other"]
    assert {t["name"]: t["agents"] for t in app.state()["tools"]} == {"demo": 2, "other": 2}


def test_settings_agents_groups_by_plugin_and_shows_the_cores_agents_once(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    one = make_tool(a)
    two = Tool(name="other", summary="other", version="1.0", add_commands=lambda p: None, agents=agents.core("layout", "banner"))
    app = serve.App([one, two], [])
    data = app.settings_agents()
    groups = {g["id"]: g for g in data["groups"]}
    assert list(groups) == ["demo", "core"] and groups["demo"]["title"] == "Demo"
    assert [x["id"] for x in groups["demo"]["agents"]] == ["finder"]
    core = {x["id"]: x for x in groups["core"]["agents"]}
    assert set(core) == {"layout", "banner"} and core["layout"]["users"] == ["demo", "other"] and core["banner"]["users"] == ["other"]


def test_an_agents_provider_and_model_change_only_with_the_token_and_go_back_to_the_recommended(server):
    _, c, _, app = server
    pid, _ = add(c, kind="anthropic", key=SECRET)
    status, data = c.request("POST", "/api/settings/agents/demo/layout", {"provider": pid, "model": "claude-haiku-5-5"}, headers={"X-SMTV-Token": "nope"})
    assert status == 403
    status, data = c.request("POST", "/api/settings/agents/demo/layout", {"provider": pid, "model": "claude-haiku-5-5"})
    assert status == 200
    layout = [x for g in data["groups"] for x in g["agents"] if x["id"] == "layout"][0]
    assert layout["current"]["model"] == "claude-haiku-5-5" and layout["current"]["source"] == "own"
    assert layout["current"]["warnings"] == ["weaker"]           # a warning, and the choice stays
    from smtv_core.settings import Settings
    assert Settings.load().tools["demo"]["agents"]["layout"] == {"provider": pid, "model": "claude-haiku-5-5"}
    for bad in ({"provider": pid, "model": "a b"}, {"provider": pid, "model": 5}, {"provider": pid, "model": ""},
                {"provider": pid, "model": "x" * 201}, {"provider": "nope", "model": "x"}):
        assert c.request("POST", "/api/settings/agents/demo/layout", bad)[0] == 400, bad
    assert c.request("POST", "/api/settings/agents/demo/nope", {"provider": pid, "model": "x"})[0] == 404
    status, data = c.request("POST", "/api/settings/agents/demo/layout", {"reset": True})
    assert [x for g in data["groups"] for x in g["agents"] if x["id"] == "layout"][0]["current"]["source"] == "recommended"
    # choosing the default is the same as going back to it: it follows the table from then on
    c.request("POST", "/api/settings/agents/demo/layout", {"provider": pid, "model": "claude-sonnet-5-5"})
    assert "agents" not in Settings.load().tools.get("demo", {})


def test_an_agent_that_reads_frames_is_offered_only_providers_that_pass_them(server):
    _, c, *_ = server
    cc, _ = add(c, kind="claude_code")
    cx, _ = add(c, kind="codex")
    _, data = c.request("GET", "/api/settings/agents")
    rows = {x["id"]: x for g in data["groups"] for x in g["agents"]}
    assert rows["finder"]["providers"] == [cc, cx] and rows["layout"]["providers"] == [cx]
    assert rows["layout"]["current"]["provider"] == cx
    status, body = c.request("POST", "/api/settings/agents/demo/layout", {"provider": cc, "model": "claude-sonnet-5-5"})
    assert status == 400 and "frames" in body["message"]
    assert {p["id"]: p["images"] for p in data["providers"]} == {cc: False, cx: True}


def test_assigning_the_recommended_models_of_a_new_provider(server):
    _, c, *_ = server
    first, _ = add(c, kind="gemini", key=SECRET)
    second, data = add(c, kind="codex")
    assert data["can_recommend"] == 1                                   # layout; the demo's own finder has no row in the table
    status, data = c.request("POST", f"/api/settings/providers/{second}/recommend", {})
    assert status == 200 and data["assigned"] == [{"tool": "demo", "agent": "layout", "model": ""}]
    rows = {x["id"]: x for g in data["groups"] for x in g["agents"]}
    assert rows["layout"]["current"]["provider"] == second and rows["layout"]["current"]["source"] == "own"
    # switched off: its agents go back to the recommended models of the remaining provider
    c.request("POST", f"/api/settings/providers/{second}", {"enabled": False})
    _, data = c.request("GET", "/api/settings/agents")
    rows = {x["id"]: x for g in data["groups"] for x in g["agents"]}
    assert (rows["layout"]["current"]["provider"], rows["layout"]["current"]["model"]) == (first, "gemini-3.7-flash")
    assert c.request("POST", f"/api/settings/providers/{second}/recommend", {})[0] == 400


def test_the_list_of_models_marks_recommended_tested_images_and_price(server, monkeypatch):
    _, c, _, app = server
    cx, _ = add(c, kind="codex")
    status, data = c.request("GET", f"/api/settings/providers/{cx}/models?agent=demo/layout")
    assert status == 200 and data["provider"] == cx and data["live"]["ok"]
    rows = {r["id"]: r for r in data["models"]}
    assert data["models"][0]["id"] == "" and rows[""]["recommended"] and rows[""]["tested"]
    assert rows["gpt-6-luna"]["warnings"] == ["weaker"] and not rows["gpt-6-luna"]["tested"]
    assert rows["gpt-6.2-astra"]["price"] == {"kind": "subscription"} and rows["gpt-6.2-astra"]["images"] is True
    # an API provider adds its own live list (a free request with the saved key), asked once for a while
    calls = []
    info = {"anthropic/new-1": {"images": False, "price": {"in": 0.25, "out": 1.0}}}
    monkeypatch.setattr(serve.keycheck, "check", lambda m, key=None: calls.append(m.provider_id) or serve.keycheck.KeyCheck(
        "ok", "the key works", ["anthropic/new-1"], info))
    orr, _ = add(c, kind="openai", preset="openrouter", key=SECRET)
    for _ in range(2):
        status, data = c.request("GET", f"/api/settings/providers/{orr}/models?agent=demo/layout")
    assert calls == [orr] and SECRET not in json.dumps(data)
    rows = {r["id"]: r for r in data["models"]}
    assert data["models"][0]["id"] == "anthropic/claude-sonnet-5.5" and data["models"][0]["recommended"]
    assert rows["anthropic/claude-sonnet-5.5"]["price"] == {"kind": "table", "in": 2.0, "out": 10.0}
    new = rows["anthropic/new-1"]
    assert new["known"] is False and new["images"] is False and new["warnings"] == ["no_images"]
    assert new["price"] == {"kind": "table", "in": 0.25, "out": 1.0}
    assert data["models"][-1]["id"] == "anthropic/new-1"              # a model with a warning goes last


def test_a_provider_that_does_not_answer_gives_the_known_models_and_a_reason(server, monkeypatch):
    _, c, *_ = server
    calls = []
    monkeypatch.setattr(serve.keycheck, "check", lambda m, key=None: calls.append(1) or serve.keycheck.KeyCheck(
        "unreachable", "could not reach https://api.anthropic.com/v1/models: timed out"))
    pid, _ = add(c, kind="anthropic", key=SECRET)
    status, data = c.request("GET", f"/api/settings/providers/{pid}/models?agent=demo/layout")
    assert status == 200 and not data["live"]["ok"] and data["live"]["status"] == "unreachable" and "timed out" in data["live"]["detail"]
    assert [r["id"] for r in data["models"]][:1] == ["claude-sonnet-5-5"] and len(data["models"]) == 3
    c.request("GET", f"/api/settings/providers/{pid}/models")
    assert len(calls) == 2                                          # a failure is not kept: asked again next time
    # a model typed in by hand is accepted
    assert c.request("POST", "/api/settings/agents/demo/layout", {"provider": pid, "model": "claude-typed-by-hand"})[0] == 200
    custom, _ = add(c, kind="openai", preset="custom", base_url="http://127.0.0.1:9/v1")
    status, data = c.request("GET", f"/api/settings/providers/{custom}/models")
    assert status == 200 and data["models"] == [] and not data["live"]["ok"]


def test_a_key_that_cannot_be_deleted_keeps_its_provider(server, monkeypatch):
    _, c, *_ = server
    pid, _ = add(c, kind="gemini", key=SECRET)
    def locked(name):
        raise RuntimeError("keychain is locked")
    monkeypatch.setattr(serve, "delete_secret", locked)
    status, body = c.request("POST", f"/api/settings/providers/{pid}/delete", {})
    assert status == 500 and body["error"] == "key_not_deleted" and SECRET not in json.dumps(body)
    from smtv_core.settings import Settings
    assert [p.id for p in Settings.load().providers] == [pid]


def test_checking_a_provider_before_adding_it_uses_only_the_key_typed_in(server, monkeypatch):
    _, c, *_ = server
    monkeypatch.setenv("SMTV_ANTHROPIC_API_KEY", "sk-ant-from-the-environment-000")
    status, body = c.request("POST", "/api/settings/providers/check", {"kind": "anthropic"})
    assert status == 200 and body["status"] == "no_key"


def test_two_providers_added_at_once_are_both_kept(server):
    _, c, *_ = server
    import threading
    gate = threading.Barrier(4)
    results = []

    def go(kind, key):
        gate.wait()
        results.append(c.request("POST", "/api/settings/providers", {"kind": kind, "key": key})[0])

    threads = [threading.Thread(target=go, args=(k, f"key-of-{k}-{i}-00000000")) for i, k in enumerate(("anthropic", "gemini", "anthropic", "gemini"))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    from smtv_core.settings import Settings, get_secret
    s = Settings.load()
    assert results == [201] * 4 and len(s.providers) == 4 and len({p.id for p in s.providers}) == 4
    assert sorted(get_secret(p.key_name()) for p in s.providers) == sorted(f"key-of-{k}-{i}-00000000" for i, k in enumerate(("anthropic", "gemini", "anthropic", "gemini")))


def test_a_shared_agent_is_set_and_reset_for_every_plugin_that_uses_it(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir(), b.mkdir()
    two = Tool(name="other", summary="other", version="1.0", add_commands=lambda p: None, agents=agents.core("layout"))
    app = serve.App([make_tool(a), two], [])
    from smtv_core.settings import Provider, Settings
    Settings(providers=[Provider(id="codex", kind="codex", name="Codex CLI")]).save()
    data = app.settings_agent_set("demo", "layout", {"provider": "codex", "model": "gpt-6.2-astra"})
    s = Settings.load()
    assert s.tools["demo"]["agents"]["layout"] == s.tools["other"]["agents"]["layout"] == {"provider": "codex", "model": "gpt-6.2-astra"}
    row = [x for g in data["groups"] for x in g["agents"] if x["id"] == "layout"][0]
    assert row["users"] == ["demo", "other"] and not row["differs"]
    s.tools["other"]["agents"]["layout"]["model"] = "gpt-6-luna"           # set apart before stage 19
    s.save()
    assert [x for g in app.settings_agents()["groups"] for x in g["agents"] if x["id"] == "layout"][0]["differs"]
    app.settings_agent_set("demo", "layout", {"reset": True})
    s = Settings.load()
    assert "agents" not in s.tools.get("demo", {}) and "agents" not in s.tools.get("other", {})


# --- stage 20: presets, «Find on this computer», Ollama's models, «Settings → Speech» -----------------------------

def test_a_cloud_preset_comes_with_its_address_json_mode_and_needs_a_key(server):
    _, c, *_ = server
    pid, data = add(c, kind="openai", preset="deepseek", key=SECRET)
    p = next(x for x in data["providers"] if x["id"] == pid)
    assert p["name"] == "DeepSeek" and p["json_mode"] == "object" and p["default_model"] == "deepseek-chat"
    assert p["key"]["needed"] and p["key"]["saved"] and not p["local"]
    from smtv_core.settings import Settings
    assert Settings.load().provider(pid).base_url == "https://api.deepseek.com/v1"
    assert SECRET not in json.dumps(data)
    choices = {x["choice"]: x for x in data["choices"]}
    assert choices["ollama"]["group"] == "local" and not choices["ollama"]["needs_key"]
    assert choices["groq"]["group"] == "cloud" and choices["groq"]["needs_key"]


def test_find_on_this_computer_and_add_what_is_found(server, monkeypatch):
    _, c, *_ = server
    from smtv_core import presets
    monkeypatch.setattr(presets, "discover", lambda timeout=1.5: [
        {"preset": "ollama", "base_url": "http://127.0.0.1:11434", "found": True, "models": ["qwen3:8b"], "detail": ""},
        {"preset": "lmstudio", "base_url": "http://127.0.0.1:1234/v1", "found": False, "models": [], "detail": "refused"}])
    _, d = c.request("POST", "/api/settings/providers/discover", {})
    assert [(x["preset"], x["found"], x["added"], x["count"]) for x in d["servers"]] == [("ollama", True, None, 1), ("lmstudio", False, None, 0)]
    pid, data = add(c, kind="openai", preset="ollama", base_url="http://127.0.0.1:11434")
    p = next(x for x in data["providers"] if x["id"] == pid)
    assert p["local"] and p["api"] == "ollama" and not p["key"]["needed"] and p["table"] == "ollama"
    assert data["can_recommend"] == 1                       # the table recommends qwen3-vl for the demo's layout agent
    _, d = c.request("POST", "/api/settings/providers/discover", {})
    assert d["servers"][0]["added"] == pid


class FakeOllama(http.server.BaseHTTPRequestHandler):
    pulled: list = []

    def log_message(self, *a):
        pass

    def _send(self, code, data, ndjson=False):
        out = b"".join(json.dumps(x).encode() + b"\n" for x in data) if ndjson else json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def do_GET(self):
        if self.path == "/api/tags":
            return self._send(200, {"models": [{"name": m, "size": 5_000_000_000, "details": {"parameter_size": "8B"}} for m in ["qwen3:8b", *self.pulled]]})
        self._send(404, {})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/api/show":
            return self._send(200, {"capabilities": ["completion", "vision"] if "vl" in body["model"] else ["completion"]})
        if self.path == "/api/pull":
            if body["model"] == "bad:1b":
                return self._send(200, [{"error": "file does not exist"}], ndjson=True)
            self.pulled.append(body["model"])
            return self._send(200, [{"status": "pulling", "total": 10, "completed": 10}, {"status": "success"}], ndjson=True)
        self._send(404, {})

    def do_DELETE(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if body["model"] in self.pulled:
            self.pulled.remove(body["model"])
        self._send(200, {})


def poll_until(c, path, done, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        _, d = c.request("GET", path)
        if done(d):
            return d
        time.sleep(0.05)
    raise AssertionError(d)


def test_ollamas_models_are_listed_downloaded_and_removed(server):
    _, c, *_ = server
    FakeOllama.pulled = []
    srv = http.server.HTTPServer(("127.0.0.1", 0), FakeOllama)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        pid, _ = add(c, kind="openai", preset="ollama", base_url=f"http://127.0.0.1:{srv.server_address[1]}")
        url = f"/api/settings/providers/{pid}/ollama"
        _, d = c.request("GET", url)
        assert d["running"] and [m["id"] for m in d["installed"]] == ["qwen3:8b"] and d["installed"][0]["images"] is False
        rec = {m["id"]: m for m in d["recommended"]}
        assert rec["qwen3:8b"]["installed"] and not rec["qwen3-vl:8b"]["installed"] and rec["qwen3-vl:8b"]["images"]
        assert rec["qwen3:14b"]["size_gb"] > 5 and "scan" in rec["qwen3:14b"]["for"]
        status, _ = c.request("POST", f"{url}/pull", {"model": "qwen3-vl:8b"})
        assert status == 200
        d = poll_until(c, url, lambda d: d["pulls"].get("qwen3-vl:8b", {}).get("status") == "done")
        assert {m["id"] for m in d["installed"]} == {"qwen3:8b", "qwen3-vl:8b"}
        _, models = c.request("GET", f"/api/settings/providers/{pid}/models?agent=demo/layout")
        first = models["models"][0]
        assert first["id"] == "qwen3-vl:8b" and first["recommended"] and first["images"] and not first["tested"]
        c.request("POST", f"{url}/pull", {"model": "bad:1b"})
        d = poll_until(c, url, lambda d: d["pulls"].get("bad:1b", {}).get("status") == "error")
        assert "file does not exist" in d["pulls"]["bad:1b"]["detail"]
        status, d = c.request("POST", f"{url}/pull", {"model": "rm -rf /"})
        assert status == 400 and d["error"] == "bad_model"
        _, d = c.request("POST", f"{url}/delete", {"model": "qwen3-vl:8b"})
        assert [m["id"] for m in d["installed"]] == ["qwen3:8b"]
    finally:
        srv.shutdown()
        srv.server_close()
    _, d = c.request("GET", url)
    assert not d["running"] and "not running" in d["detail"]
    other, _ = add(c, kind="openai", preset="deepseek", key=SECRET)
    status, d = c.request("GET", f"/api/settings/providers/{other}/ollama")
    assert status == 400 and d["error"] == "not_ollama"


def test_speech_settings_list_models_and_set_a_model_per_language(server, tmp_path):
    _, c, *_ = server
    _, d = c.request("GET", "/api/settings/speech")
    models = {m["id"]: m for m in d["models"]}
    assert list(models) == ["gigaam", "parakeet", "whisper", "groq", "openai"]
    assert models["gigaam"]["where"] == "local" and models["gigaam"]["speed_x"] == 54 and models["gigaam"]["license"] == "MIT"
    assert models["groq"]["where"] == "cloud" and models["groq"]["key"] is False and models["groq"]["price_hour"] == 0.04
    assert not models["whisper"]["installed"] and models["whisper"]["size_mb"] > 1000
    langs = {x["code"]: x for x in d["languages"]}
    assert (langs["ru"]["model"], langs["de"]["model"], langs["ja"]["model"], langs["*"]["model"]) == ("gigaam", "parakeet", "whisper", "whisper")
    assert langs["ru"]["choices"] == ["gigaam", "parakeet", "whisper", "groq", "openai"] and "gigaam" not in langs["en"]["choices"]
    _, d = c.request("POST", "/api/settings/speech/languages", {"language": "en", "model": "groq"})
    assert {x["code"]: x for x in d["languages"]}["en"] == {**langs["en"], "model": "groq", "source": "own"}
    status, d = c.request("POST", "/api/settings/speech/languages", {"language": "en", "model": "gigaam"})
    assert status == 400 and d["error"] == "bad_choice"
    _, d = c.request("POST", "/api/settings/speech/languages", {"language": "en", "model": None})
    assert {x["code"]: x for x in d["languages"]}["en"]["model"] == "parakeet"
    status, d = c.request("POST", "/api/settings/speech/models/groq/download", {})
    assert status == 404
    (tmp_path / "home" / "models" / "whisper").mkdir(parents=True)
    (tmp_path / "home" / "models" / "whisper" / "model.bin").write_bytes(b"x" * 10)
    (tmp_path / "home" / "models" / "whisper" / "config.json").write_text("{}", encoding="utf-8")
    _, d = c.request("GET", "/api/settings/speech")
    assert {m["id"]: m for m in d["models"]}["whisper"]["installed"]
    _, d = c.request("POST", "/api/settings/speech/models/whisper/delete", {})
    assert not {m["id"]: m for m in d["models"]}["whisper"]["installed"] and not (tmp_path / "home" / "models" / "whisper").exists()


def test_a_speech_model_downloads_in_the_background_once(server, monkeypatch):
    _, c, _, app = server
    from smtv_core.asr import catalog, whisper
    gate = threading.Event()
    calls = []

    def download(models_dir=None, progress=None, every_s=2.0):
        calls.append(1)
        progress(100, 1550)
        gate.wait(5)
        raise OSError("no room on the disk")
    monkeypatch.setattr(whisper, "download", download)
    monkeypatch.setattr(catalog, "package_ready", lambda m: True)
    status, d = c.request("POST", "/api/settings/speech/models/whisper/download", {})
    assert status == 200
    status, again = c.request("POST", "/api/settings/speech/models/whisper/download", {})
    assert status == 409 and again["error"] == "downloading"            # a second press does not start a second download
    d = poll_until(c, "/api/settings/speech", lambda d: {m["id"]: m for m in d["models"]}["whisper"]["download"]["done"] == 100)
    gate.set()
    d = poll_until(c, "/api/settings/speech", lambda d: {m["id"]: m for m in d["models"]}["whisper"]["download"]["status"] == "error")
    assert "no room" in {m["id"]: m for m in d["models"]}["whisper"]["download"]["detail"] and calls == [1]


def test_speech_shows_a_saved_cloud_key_but_never_the_key(server):
    _, c, *_ = server
    pid, _ = add(c, kind="openai", preset="groq", key=SECRET)
    _, d = c.request("GET", "/api/settings/speech")
    groq = {m["id"]: m for m in d["models"]}["groq"]
    assert groq["key"] is True and groq["provider"] == pid and SECRET not in json.dumps(d)


def test_signing_in_from_the_profile_menu_adds_streammoment_once_and_last(server):
    """Owner, 21.11: «Sign in» lives in the profile menu; a finished sign-in puts StreamMoment on the providers list
    (after the person's own ones, so their agents keep their models), and only once."""
    _, c, _, app = server
    add(c, kind="gemini")
    app._login = types.SimpleNamespace(state="done", error="", url="", user_code="")
    c.request("GET", "/api/account")
    c.request("GET", "/api/account")
    kinds = [p["kind"] for p in c.request("GET", "/api/settings")[1]["providers"]]
    assert kinds == ["gemini", "streammoment"]
    sm = next(p for p in c.request("GET", "/api/settings")[1]["providers"] if p["kind"] == "streammoment")
    c.request("POST", f"/api/settings/providers/{sm['id']}/delete", {})
    c.request("GET", "/api/account")
    assert [p["kind"] for p in c.request("GET", "/api/settings")[1]["providers"]] == ["gemini"], "removed later, it stays removed"


def test_a_prompt_links_to_the_copy_inside_this_release_of_smtv():
    """The prompts are published only inside SMTV: a release links its own tag, a development build links main."""
    assert serve.prompts_source("0.1.0") == "https://github.com/yuriti/clipit/blob/v0.1.0/packages/smtv-core/src/smtv_core/prompts"
    assert serve.prompts_source("0.2.0.dev0").startswith("https://github.com/yuriti/clipit/blob/main/")
