import io
import json
import os
import stat
import subprocess
import sys
import urllib.error
from pathlib import Path

import pytest

from smtv_core import checks, paths
from smtv_core.llm import providers
from smtv_core.settings import ModelSettings, Settings, get_secret, set_secret


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    for key in list(os.environ):
        if key.startswith("SMTV_") and key != "SMTV_HOME":
            monkeypatch.delenv(key)
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)
    return tmp_path / "home"


def test_home_follows_smtv_home(isolated_home):
    assert paths.home() == isolated_home
    assert paths.settings_file().parent == isolated_home


def test_settings_round_trip_and_unknown_fields_are_ignored(isolated_home):
    from smtv_core.settings import Provider
    s = Settings(providers=[Provider(id="openai", kind="openai", name="OpenAI", default_model="some-model")])
    s.tools["vodcut"] = {"recap": True}
    s.save()
    raw = json.loads(paths.settings_file().read_text(encoding="utf-8"))
    assert "model" not in raw
    raw["providers"][0]["from_the_future"] = 1
    raw["providers"].append({"id": "BAD ID", "kind": "openai"})          # refused, not a crash
    raw["providers"].append({"id": "x", "kind": "something-new"})
    paths.settings_file().write_text(json.dumps(raw), encoding="utf-8")
    loaded = Settings.load()
    assert [(p.id, p.kind, p.default_model) for p in loaded.providers] == [("openai", "openai", "some-model")]
    assert loaded.tools == {"vodcut": {"recap": True}}


def test_secret_file_is_private_and_env_wins(isolated_home, monkeypatch):
    assert set_secret("openai_api_key", "sk-file") == "file"
    mode = stat.S_IMODE(os.stat(paths.secrets_file()).st_mode)
    assert sys.platform == "win32" or mode == 0o600      # Windows has no POSIX permission bits
    assert get_secret("openai_api_key") == "sk-file"
    monkeypatch.setenv("SMTV_OPENAI_API_KEY", "sk-env")
    assert get_secret("openai_api_key") == "sk-env"
    assert "sk-file" not in paths.settings_file().read_text(encoding="utf-8") if paths.settings_file().exists() else True


def test_transport_schema_and_parse_json():
    schema = {"type": "object", "allOf": [{}], "properties": {"r": {"$ref": "#/$defs/rect"}}, "$defs": {"rect": {"type": "object", "multipleOf": 5}}}
    sent = providers.transport_schema(schema)
    assert "allOf" not in sent and "$defs" not in sent and sent["properties"]["r"] == {"type": "object"}
    assert providers.parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert providers.parse_json('text {"a": [1]} more') == {"a": [1]}
    with pytest.raises(providers.ProviderError):
        providers.parse_json("nothing")


def _http_error(code, body):
    return urllib.error.HTTPError("https://x", code, "err", {}, io.BytesIO(body.encode()))


def test_quota_is_not_retried_and_overload_is(monkeypatch):
    calls = []

    def fake(*_a, **_k):
        calls.append(1)
        raise _http_error(429, '{"error":{"code":"insufficient_quota"}}')

    monkeypatch.setattr(providers.urllib.request, "urlopen", fake)
    monkeypatch.setattr(providers.time, "sleep", lambda s: None)
    with pytest.raises(providers.QuotaExceeded):
        providers._post("https://x", {}, {}, 5)
    assert len(calls) == 1

    calls.clear()

    def busy(*_a, **_k):
        calls.append(1)
        raise _http_error(503, "busy")

    monkeypatch.setattr(providers.urllib.request, "urlopen", busy)
    with pytest.raises(providers.Overloaded):
        providers._post("https://x", {}, {}, 5)
    assert len(calls) == 3


def test_call_without_setup_explains_what_to_do():
    with pytest.raises(providers.ProviderError, match="no provider is set up"):
        providers.call(ModelSettings(), "hi", {})
    with pytest.raises(providers.ProviderError, match="no model id"):
        providers.call(ModelSettings(provider="openai"), "hi", {})
    with pytest.raises(providers.ProviderError, match="no key"):
        providers.call(ModelSettings(provider="openai", model="m"), "hi", {})


def test_ffmpeg_missing_and_libass_detection(monkeypatch, tmp_path):
    monkeypatch.setattr(checks, "_ffmpeg_dirs", lambda: ([], []))
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    rows = checks.check_ffmpeg()
    assert rows[0].status == checks.FAIL and rows[0].fix

    for name in ("ffmpeg", "ffprobe"):
        (tmp_path / checks._exe(name)).write_text("", encoding="utf-8")
    monkeypatch.setattr(checks.shutil, "which", lambda name: str(tmp_path / name))
    without = " ... scale             V->V       Scale the input video size\n"
    with_ass = without + " ... ass               V->V       Render ASS subtitles onto input video using the libass library.\n"
    outputs = {"-version": "ffmpeg version 7.1", "-filters": without}
    monkeypatch.setattr(checks, "_run", lambda argv, timeout=15: outputs[argv[-1]])
    assert [r.status for r in checks.check_ffmpeg()] == [checks.OK, checks.FAIL]
    outputs["-filters"] = with_ass
    assert [r.status for r in checks.check_ffmpeg()] == [checks.OK, checks.OK]


def test_model_check(monkeypatch):
    from smtv_core.settings import Provider
    assert checks.check_model(Settings()).status == checks.FAIL
    s = Settings(model=ModelSettings(provider="openai", model="m"))
    assert "no key" in checks.check_model(s).detail
    set_secret("openai_api_key", "sk-xxxxxxxxxx")
    row = checks.check_model(s)
    assert row.status == checks.OK and "sk-x" not in row.detail
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    assert checks.check_model(Settings(model=ModelSettings(provider="codex"))).status == checks.FAIL
    # several providers: ready while one of them is; the others are named with the reason
    s.providers.append(Provider(id="claude-code", kind="claude_code", name="Claude Code CLI"))
    row = checks.check_model(s)
    assert row.status == checks.OK and "Claude Code CLI: Claude Code not found" in row.detail
    s.providers[0].enabled = False
    assert checks.check_model(s).status == checks.FAIL


def test_redact_removes_the_key_and_anything_that_looks_like_one():
    from smtv_core.llm.keycheck import redact
    text = "Incorrect API key provided: sk-proj-abc123****wxyz; also AIzaSyA1234567890abcdef and Bearer sk-x and mysecretvalue"
    out = redact(text, "mysecretvalue")
    assert "abc123" not in out and "AIzaSy" not in out and "mysecretvalue" not in out and out.count("[key]") >= 3


def test_key_check_without_a_key_does_not_call_the_provider(monkeypatch):
    from smtv_core.llm import keycheck
    from smtv_core.settings import ModelSettings
    monkeypatch.setattr("smtv_core.llm.keycheck.get_secret", lambda name: None)
    monkeypatch.setattr(keycheck, "_get", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert keycheck.check(ModelSettings(provider="anthropic", model="m")).status == keycheck.NO_KEY


def test_cost_needs_prices_and_tokens():
    from smtv_core.settings import ModelSettings
    assert ModelSettings().cost(100, 100) is None
    assert ModelSettings(price_in=1).cost(None, None) is None
    assert ModelSettings(price_in=1, price_out=4).cost(1000, 1000) == 0.005


def test_a_cancelled_job_fits_the_contract(tmp_path):
    from smtv_core.events import CANCELLED, Journal, contract
    with Journal(tmp_path, tool="t", subscribers=[]) as j:
        event = j.emit(CANCELLED, by="user", stage="speech")
    assert contract.validate(event) == [] and contract.undeclared(event) == [] and event["v"] == contract.version()


def test_codex_reports_its_tokens_from_the_json_events():
    from smtv_core.llm.providers import codex_usage
    out = '{"type":"turn.started"}\nnot json\n{"type":"turn.completed","usage":{"input_tokens":15114,"cached_input_tokens":12160,"output_tokens":9}}\n'
    assert codex_usage(out) == (15114, 9)
    assert codex_usage('{"type":"item.completed"}') == (None, None) and codex_usage("") == (None, None)


# --- stage 19: the Claude Code CLI, and the key in error texts --------------------------------------------------

FAKE_CLAUDE = """#!{python}
import json, sys, os
args = sys.argv[1:]
prompt = sys.stdin.read()
with open(os.environ["FAKE_CLAUDE_LOG"], "w") as f:
    json.dump({{"args": args, "prompt": prompt, "cwd": os.getcwd()}}, f)
if args[:3] == ["auth", "status", "--json"]:
    print(json.dumps({{"loggedIn": os.environ.get("FAKE_CLAUDE_IN") == "1", "email": "person@example.com"}}))
    sys.exit(0)
if os.environ.get("FAKE_CLAUDE_LIMIT") == "1":
    print(json.dumps({{"type": "result", "is_error": True, "result": "Claude usage limit reached"}}))
    sys.exit(1)
print(json.dumps({{"type": "result", "is_error": False, "result": "", "structured_output": {{"ok": True}},
                  "usage": {{"input_tokens": 10, "cache_read_input_tokens": 90, "output_tokens": 5}}}}))
"""


@pytest.fixture
def fake_claude(tmp_path, monkeypatch):
    if sys.platform == "win32":
        pytest.skip("the fake `claude` is a script with #!: Windows runs only .exe/.cmd from PATH")
    binary = tmp_path / "claude"
    binary.write_text(FAKE_CLAUDE.format(python=sys.executable), encoding="utf-8")
    binary.chmod(0o755)
    log = tmp_path / "claude.json"
    monkeypatch.setenv("FAKE_CLAUDE_LOG", str(log))
    return binary, log


def test_claude_code_is_called_with_the_model_the_schema_and_no_tools(fake_claude):
    binary, log = fake_claude
    m = ModelSettings(provider="claude_code", model="claude-sonnet-5-5", claude_bin=str(binary))
    answer = providers.call(m, "rate this", {"type": "object", "properties": {"ok": {"type": "boolean"}}})
    assert answer.data == {"ok": True} and (answer.tokens_in, answer.tokens_out) == (100, 5)
    seen = json.loads(log.read_text(encoding="utf-8"))
    args = seen["args"]
    assert seen["prompt"] == "rate this"                                   # the prompt goes on stdin, not in the arguments
    assert args[0] == "-p" and args[args.index("--model") + 1] == "claude-sonnet-5-5"
    assert args[args.index("--tools") + 1] == "" and "--no-session-persistence" in args and "--strict-mcp-config" in args
    assert json.loads(args[args.index("--json-schema") + 1])["properties"]["ok"] == {"type": "boolean"}
    assert "--bare" not in args                                            # --bare would skip the person's own sign-in
    with pytest.raises(providers.ProviderError, match="text only"):
        providers.call(m, "look", {"type": "object"}, images=[Path("frame.jpg")])


def test_claude_code_out_of_its_limit_stops_the_run(fake_claude, monkeypatch):
    binary, _ = fake_claude
    monkeypatch.setenv("FAKE_CLAUDE_LIMIT", "1")
    with pytest.raises(providers.QuotaExceeded):
        providers.call(ModelSettings(provider="claude_code", claude_bin=str(binary)), "x", {"type": "object"})


def test_claude_code_check_says_only_signed_in_or_not(fake_claude, monkeypatch):
    from smtv_core.llm import keycheck
    binary, _ = fake_claude
    m = ModelSettings(provider="claude_code", claude_bin=str(binary))
    monkeypatch.setenv("FAKE_CLAUDE_IN", "1")
    r = keycheck.check(m)
    assert r.status == keycheck.OK and "example.com" not in json.dumps(r.as_dict())     # the account's email stays out
    monkeypatch.setenv("FAKE_CLAUDE_IN", "0")
    assert keycheck.check(m).status == keycheck.NOT_SIGNED_IN
    assert keycheck.check(ModelSettings(provider="claude_code", claude_bin="/nowhere/claude")).status == keycheck.NOT_INSTALLED


class EchoKey(__import__("http.server").server.BaseHTTPRequestHandler):
    """A provider that repeats the key it was sent in its error, as some do."""
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        body = json.dumps({"error": {"message": "Incorrect API key provided: " + self.headers.get("Authorization", "")}}).encode()
        self.send_response(401)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def test_a_providers_error_never_carries_the_key_into_the_journal(tmp_path):
    import http.server
    import threading
    from smtv_core.events import Journal
    srv = http.server.HTTPServer(("127.0.0.1", 0), EchoKey)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    key = "my-own-server-key-without-any-shape-123"
    set_secret("provider.mine", key)
    m = ModelSettings(provider="openai", model="m", base_url=f"http://127.0.0.1:{srv.server_address[1]}/v1", key_ref="provider.mine")
    try:
        with pytest.raises(providers.ProviderError) as e:
            providers.call(m, "hi", {"type": "object"})
    finally:
        srv.shutdown()
        srv.server_close()
    assert key not in str(e.value) and "[key]" in str(e.value)
    with Journal(tmp_path, tool="t", subscribers=[]) as j:
        j.emit("model_call", purpose="scan", model="openai/m", error=f"model: {e.value}"[:300])
    assert key not in (tmp_path / "events.jsonl").read_text(encoding="utf-8")


def test_a_key_for_a_provider_of_the_list_or_the_old_environment_variable():
    m = ModelSettings(provider="anthropic", model="m", key_ref="provider.claude-2")
    with pytest.raises(providers.ProviderError, match="claude-2|no key"):
        providers._key(ModelSettings(provider="anthropic", model="m", key_ref="provider.claude-2", provider_id="claude-2"))
    os.environ["SMTV_ANTHROPIC_API_KEY"] = "sk-ant-from-the-environment"
    try:
        assert providers._key(m) == "sk-ant-from-the-environment"
        set_secret("provider.claude-2", "sk-ant-saved-for-this-one")
        assert providers._key(m) == "sk-ant-saved-for-this-one"           # its own key wins
    finally:
        del os.environ["SMTV_ANTHROPIC_API_KEY"]


def test_an_openrouter_key_is_checked_by_its_own_page_not_by_the_open_list(monkeypatch):
    from smtv_core.llm import keycheck
    asked = []

    def get(url, headers, timeout):
        asked.append(url)
        if url.endswith("/key"):
            raise urllib.error.HTTPError(url, 401, "User not found.", {}, io.BytesIO(b'{"error":{"message":"User not found."}}'))
        return {"data": [{"id": "openai/gpt-6.2-sol"}]}

    monkeypatch.setattr(keycheck, "_get", get)
    m = ModelSettings(provider="openai", base_url="https://openrouter.ai/api/v1")
    assert keycheck.check(m, "sk-or-v1-wrong-000000000000").status == keycheck.BAD_KEY
    assert asked == ["https://openrouter.ai/api/v1/key"]


def test_an_openai_key_from_the_environment_never_goes_to_another_server(monkeypatch):
    from smtv_core.llm import keycheck
    monkeypatch.setenv("SMTV_OPENAI_API_KEY", "sk-env-openai-000000000000")
    sent = []
    monkeypatch.setattr(keycheck, "_get", lambda url, headers, timeout: sent.append(headers) or {"data": []})
    for url in ("https://openrouter.ai/api/v1", "http://10.0.0.5/v1"):
        m = ModelSettings(provider="openai", model="x", base_url=url, key_ref="provider.other")
        assert providers._key(m, optional=True) == ""
        with pytest.raises(providers.ProviderError, match="no key"):
            providers._key(m)
        keycheck.check(m)
    assert all("sk-env" not in json.dumps(h) for h in sent)
    official = ModelSettings(provider="openai", model="x", key_ref="provider.openai-2")
    assert providers._key(official) == "sk-env-openai-000000000000"          # OpenAI's own server: as before


def test_the_providers_own_list_gives_images_prices_and_ids(monkeypatch):
    from smtv_core.llm import keycheck
    replies = {
        "openrouter": {"data": [{"id": "x/text-only", "architecture": {"input_modalities": ["text"]},
                                 "pricing": {"prompt": "0.000002", "completion": "0.00001"}},
                                {"id": "x/sees", "architecture": {"input_modalities": ["text", "image"]}, "pricing": {"prompt": "bad"}}]},
        "gemini": {"models": [{"name": "models/gemini-x", "displayName": "Gemini X"}]},
        "anthropic": {"data": [{"id": "claude-x", "display_name": "Claude X"}]},
    }
    monkeypatch.setattr(keycheck, "_get", lambda url, headers, timeout: replies["openrouter"] if "openrouter" in url
                        else replies["gemini"] if "googleapis" in url else replies["anthropic"])
    r = keycheck.check(ModelSettings(provider="openai", base_url="https://openrouter.ai/api/v1"), "sk-or-key-000000000")
    assert r.models == ["x/sees", "x/text-only"]
    assert r.info == {"x/text-only": {"images": False, "price": {"in": 2.0, "out": 10.0}}, "x/sees": {"images": True}}
    g = keycheck.check(ModelSettings(provider="gemini"), "AIza-key-0000000000")
    assert g.models == ["gemini-x"] and g.info == {"gemini-x": {"label": "Gemini X"}}
    a = keycheck.check(ModelSettings(provider="anthropic"), "sk-ant-key-000000000")
    assert a.models == ["claude-x"] and a.info == {"claude-x": {"label": "Claude X"}}


def test_codex_runs_without_its_tools_and_its_long_instructions(tmp_path, monkeypatch):
    """B12: Codex CLI sends 15 thousand tokens of its own with every call; SMTV needs none of its tools."""
    from smtv_core.llm import providers
    seen = {}

    def run(argv, timeout, what, input=None):
        seen["argv"] = argv
        work = Path(argv[argv.index("-C") + 1])
        seen["instructions"] = (work / "instructions.md").read_text(encoding="utf-8") if (work / "instructions.md").exists() else None
        Path(argv[argv.index("-o") + 1]).write_text('{"ok": true}', encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, '{"type":"turn.completed","usage":{"input_tokens":6191,"output_tokens":15}}\n', "")
    monkeypatch.setattr(providers.shutil, "which", lambda name: "/bin/codex")
    monkeypatch.setattr(providers.proc, "run", run)
    answer = providers.call_codex(ModelSettings(provider="codex"), "Return {\"ok\": true}.", {"type": "object"}, [])
    argv = seen["argv"]
    assert answer.data == {"ok": True} and answer.tokens_in == 6191
    assert "features.shell_tool=false" in argv and 'web_search="disabled"' in argv and "--disable" not in argv
    assert any(a.startswith("model_instructions_file=") for a in argv) and "Do not use tools" in seen["instructions"]
    monkeypatch.setattr(providers, "CODEX_LEAN", False)
    providers.call_codex(ModelSettings(provider="codex"), "x", {"type": "object"}, [])
    assert not any("features." in a or "model_instructions_file" in a for a in seen["argv"])


def test_a_codex_that_refuses_the_lean_settings_is_asked_once_more_without_them(tmp_path, monkeypatch):
    from smtv_core.llm import providers
    runs = []

    def run(argv, timeout, what, input=None):
        runs.append(argv)
        if any("model_instructions_file" in a for a in argv):
            return subprocess.CompletedProcess(argv, 2, "", "Error: unknown config key model_instructions_file")
        Path(argv[argv.index("-o") + 1]).write_text('{"ok": true}', encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, "", "")
    monkeypatch.setattr(providers.shutil, "which", lambda name: "/bin/codex")
    monkeypatch.setattr(providers.proc, "run", run)
    assert providers.call_codex(ModelSettings(provider="codex"), "x", {"type": "object"}, []).data == {"ok": True}
    assert len(runs) == 2 and not any("features." in a for a in runs[1])
    runs.clear()
    monkeypatch.setattr(providers.proc, "run", lambda argv, *a, **k: (runs.append(argv), subprocess.CompletedProcess(argv, 1, "", "network down"))[1])
    with pytest.raises(providers.ProviderError, match="network down"):
        providers.call_codex(ModelSettings(provider="codex"), "x", {"type": "object"}, [])
    assert len(runs) == 1                        # any other failure is not repeated
    monkeypatch.setattr(Path, "write_text", lambda self, *a, **k: (_ for _ in ()).throw(OSError("disk full")) if self.name == "instructions.md" else 0)
    assert providers.codex_lean_args(tmp_path) == []
