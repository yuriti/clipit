"""The StreamMoment account (stage 22): reaching our server (and the VPN hint), sign-in by loopback + PKCE and by a
device code, tokens in the keychain and their refresh across processes, sign-out, and a call with our key — one
idempotency key for every retry, the balance running out, only SMTV's own agents."""
import base64
import hashlib
import json
import os
import socket
import threading
import time
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from smtv_core import account, agents, prompts
from smtv_core.llm import providers
from smtv_core.llm.providers import Overloaded, ProviderError, QuotaExceeded
from smtv_core.settings import STREAMMOMENT, ModelSettings, Provider, Settings, get_secret

# The anchors of apps/backend/src/runtime/smtv/model-call.ts (StreamMoment repository), prompts 1.1.0: the server
# accepts a prompt only when it holds its agent's anchor. If a prompt changes, both lists change in the same release.
ANCHORS = {
    "scan": "Task: read consecutive windows of an automatic transcript of a stream recording",
    "rating": "Below are clip candidates found in the speech transcript",
    "fit": "Task: assess whether each 70-second source can yield a self-contained conversati",
    "recap": "You are the editor of a YouTube channel that publishes stream recaps",
    "layout": "You are selecting a composition for one short video.",
    "banner": "Determine STATIC blur regions for ONE entire streamer video from five sampled fr",
    "critic": "Role: release editor of a vertical clips channel.",
}


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    for key in list(os.environ):
        if key.startswith("SMTV_") and key != "SMTV_HOME":
            monkeypatch.delenv(key)
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)
    monkeypatch.setattr(account, "CHECK_TIMEOUT_S", 2.0)
    monkeypatch.setattr(providers.time, "sleep", lambda s: None)


class Fake:
    """Our server, as much of it as the window uses."""

    def __init__(self):
        self.connects, self.calls, self.refreshes = {}, [], 0
        self.pending = 2
        self.call_answers: list[tuple[int, dict]] = []
        self.refresh_answer: tuple[int, dict] | None = None
        self.hello = (200, {"service": "streammoment", "smtv_api": 1, "enabled": True, "sign_in": ["google"], "payments": True})
        self.raw: tuple[int, bytes] | None = None
        fake = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, status, body):
                data = body if isinstance(body, bytes) else json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):  # noqa: N802
                if fake.raw:
                    return self._send(*fake.raw)
                if self.path == "/api/smtv/hello":
                    return self._send(*fake.hello)
                if self.path == "/api/smtv/account":
                    if self.headers.get("Authorization") != "Bearer access-2" and self.headers.get("Authorization") != "Bearer access-1":
                        return self._send(401, {"error": "unauthorized"})
                    return self._send(200, {"account": {"name": "Аня"}, "balance": {"tokens": 4000000, "free": 4000000, "reserved": 0, "hours": 10.0, "tokens_per_hour": 400000}, "packages": []})
                self._send(404, {"error": "nope"})

            def do_POST(self):  # noqa: N802
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                if self.path == "/api/smtv/connect":
                    fake.connects["c1"] = body
                    return self._send(200, {"connect": "c1", "url": f"{fake.url}/ru/connect?c=c1"})
                if self.path == "/api/smtv/device":
                    return self._send(200, {"device_code": "dev", "user_code": "ABCDEFGH", "verification_uri": f"{fake.url}/ru/connect",
                                            "verification_uri_complete": f"{fake.url}/ru/connect?code=ABCDEFGH", "expires_in": 30, "interval": 2})
                if self.path == "/api/smtv/token":
                    return self._token(body)
                if self.path == "/api/smtv/sign-out":
                    return self._send(200, {"signed_out": body.get("refresh_token") == "refresh-1"})
                if self.path == "/api/smtv/model/call":
                    fake.calls.append({"key": self.headers.get("Idempotency-Key"), "auth": self.headers.get("Authorization"), **body})
                    return self._send(*(fake.call_answers.pop(0) if fake.call_answers else
                                        (200, {"data": {"windows": []}, "tokens_in": 10, "tokens_out": 2, "charged": 12})))
                self._send(404, {"error": "nope"})

            def _token(self, body):
                tokens = {"access_token": "access-1", "refresh_token": "refresh-1", "expires_in": 3600, "account": {"id": "a1", "name": "Аня", "provider": "google"}}
                if body["grant_type"] == "authorization_code":
                    c = fake.connects.get("c1") or {}
                    challenge = base64.urlsafe_b64encode(hashlib.sha256(body["code_verifier"].encode()).digest()).decode().rstrip("=")
                    if body["code"] != "code-1" or challenge != c.get("code_challenge") or body["redirect_uri"] != c.get("redirect_uri"):
                        return self._send(400, {"error": "invalid_grant"})
                    return self._send(200, tokens)
                if body["grant_type"] == "device_code":
                    if fake.pending > 0:
                        fake.pending -= 1
                        return self._send(400, {"error": "authorization_pending"})
                    return self._send(200, tokens)
                if body["grant_type"] == "refresh_token":
                    fake.refreshes += 1
                    if fake.refresh_answer:
                        return self._send(*fake.refresh_answer)
                    return self._send(200, {**tokens, "access_token": "access-2", "refresh_token": "refresh-2"})

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


@pytest.fixture
def fake(monkeypatch):
    f = Fake()
    monkeypatch.setenv("SMTV_ACCOUNT_URL", f.url)
    yield f
    f.close()


def save_tokens(expires_in=3600):
    account._save({"access_token": "access-1", "refresh_token": "refresh-1", "expires_in": expires_in, "account": {"name": "Аня", "provider": "google"}})


def wait(pred, s=10.0):
    end = time.monotonic() + s
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(0.05)
    return False


# --- reaching our server ---------------------------------------------------------------------------------------

def test_only_our_own_answer_counts_and_a_failure_suggests_the_vpn(fake, monkeypatch):
    assert account.check()["ok"] is True
    fake.raw = (200, b"<html>Your VPN says hello</html>")            # a VPN's or a captive portal's page
    r = account.check()
    assert not r["ok"] and "VPN" in r["hint"]
    fake.raw = (502, b"<html>Bad gateway</html>")                       # our own front page while the server restarts
    r = account.check()
    assert not r["ok"] and "try again" in r["detail"]
    fake.raw = None
    fake.hello = (200, {"service": "something-else"})
    assert account.check()["ok"] is False
    with socket.socket() as s:                                          # nobody listens there
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    monkeypatch.setenv("SMTV_ACCOUNT_URL", f"http://127.0.0.1:{port}")
    r = account.check()
    assert not r["ok"] and "VPN" in r["hint"] and "streammoment.tv" in r["hint"]


def test_the_server_address_can_only_be_ours_or_this_computer(monkeypatch):
    assert account.server() == "https://streammoment.tv"
    monkeypatch.setenv("SMTV_ACCOUNT_URL", "http://evil.example")
    with pytest.raises(account.AccountError):
        account.server()


# --- sign-in -------------------------------------------------------------------------------------------------

def test_loopback_sign_in_with_pkce_saves_the_tokens_in_the_keychain(fake):
    opened = []
    login = account.Login(opener=opened.append)
    url = login.start()
    assert url == f"{fake.url}/ru/connect?c=c1" and opened == [url]
    sent = fake.connects["c1"]
    redirect = urllib.parse.urlparse(sent["redirect_uri"])
    assert redirect.hostname == "127.0.0.1" and redirect.path == "/callback"
    # A request with another state is not the answer: the page says so and SMTV keeps waiting.
    with pytest.raises(urllib.error.HTTPError):
        urllib.request.urlopen(f"{sent['redirect_uri']}?code=code-1&state=forged", timeout=5)
    assert login.state == "waiting"
    with urllib.request.urlopen(f"{sent['redirect_uri']}?code=code-1&state={sent['state']}", timeout=5) as r:
        assert "Clip It!" in r.read().decode()
    assert wait(lambda: login.state == "done"), login.error
    assert account.signed_in() == {"id": "a1", "name": "Аня", "provider": "google"}
    stored = json.loads(get_secret(account.SECRET_NAME))
    assert stored["refresh_token"] == "refresh-1"


def test_a_sign_in_nobody_finishes_ends_without_tokens(fake):
    login = account.Login(wait_s=1.5)
    login.start()
    assert wait(lambda: login.state == "failed") and login.error == "timeout"
    assert account.signed_in() is None


def test_device_code_waits_for_the_person_then_signs_in(fake, monkeypatch):
    monkeypatch.setattr(account.time, "sleep", lambda s: None)
    login = account.DeviceLogin()
    shown = login.start()
    assert shown == {"user_code": "ABCD-EFGH", "url": f"{fake.url}/ru/connect?code=ABCDEFGH"}
    assert wait(lambda: login.state == "done"), login.error
    assert account.signed_in()["name"] == "Аня"


# --- tokens --------------------------------------------------------------------------------------------------

def test_an_ending_token_is_refreshed_and_a_dead_session_signs_out(fake):
    save_tokens(expires_in=30)
    assert account.access_token() == "access-2"
    assert json.loads(get_secret(account.SECRET_NAME))["refresh_token"] == "refresh-2"
    assert account.access_token() == "access-2" and fake.refreshes == 1      # fresh now: no second refresh
    save_tokens(expires_in=30)
    fake.refresh_answer = (400, {"error": "invalid_grant"})
    with pytest.raises(account.NotSignedIn):
        account.access_token()
    assert account.signed_in() is None


def test_another_process_refreshed_first_its_tokens_are_read(fake):
    save_tokens(expires_in=30)
    fake.refresh_answer = (409, {"error": "refresh_raced"})
    original = account._load

    def other_process_saved():
        account._save({"access_token": "access-9", "refresh_token": "refresh-9", "expires_in": 3600, "account": {}})
        return original()

    session = original()
    account.time.sleep = lambda s: other_process_saved()
    try:
        assert account._refresh(session)["access_token"] == "access-9"
    finally:
        account.time.sleep = time.sleep


def test_sign_out_deletes_the_tokens_here_even_when_the_server_is_away(fake, monkeypatch):
    save_tokens()
    assert account.sign_out() == {"signed_out": True, "server": True}
    assert account.signed_in() is None
    save_tokens()
    monkeypatch.setenv("SMTV_ACCOUNT_URL", "http://127.0.0.1:9")
    out = account.sign_out()
    assert out["signed_out"] and not out["server"] and "VPN" in out["hint"]
    assert account.signed_in() is None


# --- calls with our key ---------------------------------------------------------------------------------------

def sm(agent="scan"):
    return ModelSettings(provider=STREAMMOMENT, model="", agent=agent, timeout_s=10)


def test_a_call_sends_the_agent_and_keeps_one_idempotency_key_across_retries(fake):
    save_tokens()
    fake.call_answers = [(503, {"error": "busy", "retryable": True}), (409, {"error": "in_flight"})]
    answer = providers.call(sm(), ANCHORS["scan"] + " …", {"type": "object", "properties": {}})
    assert answer.data == {"windows": []} and answer.tokens_in == 10
    assert len(fake.calls) == 3 and len({c["key"] for c in fake.calls}) == 1
    assert fake.calls[0]["agent"] == "scan" and fake.calls[0]["prompts_version"] == prompts.version()
    assert fake.calls[0]["auth"] == "Bearer access-1"
    providers.call(sm(), ANCHORS["scan"], {"type": "object"})
    assert fake.calls[-1]["key"] != fake.calls[0]["key"], "a new call has a new key"


def test_an_empty_balance_stops_the_run_and_other_refusals_say_why(fake):
    save_tokens()
    fake.call_answers = [(402, {"error": "insufficient_balance"})]
    with pytest.raises(QuotaExceeded):
        providers.call(sm(), ANCHORS["scan"], {"type": "object"})
    fake.call_answers = [(422, {"error": "prompt_not_this_agent"})]
    with pytest.raises(ProviderError, match="prompt_not_this_agent"):
        providers.call(sm(), ANCHORS["scan"], {"type": "object"})
    fake.call_answers = [(503, {"error": "busy"})] * 4
    with pytest.raises(Overloaded):
        providers.call(sm(), ANCHORS["scan"], {"type": "object"})
    with pytest.raises(ProviderError, match="agent"):
        providers.call(sm(agent=""), "free chat", {"type": "object"})


def test_without_a_sign_in_a_call_asks_to_sign_in(fake):
    with pytest.raises(ProviderError, match="sign in"):
        providers.call(sm(), ANCHORS["scan"], {"type": "object"})


# --- the provider and the agents --------------------------------------------------------------------------------

def test_every_agent_gets_streammoment_with_its_own_id_and_no_key():
    s = Settings(providers=[Provider(id="streammoment", kind=STREAMMOMENT, name="StreamMoment")])
    for agent in agents.CORE.values():
        choice = agents.resolve(s, "vodcut", agent)
        assert choice.provider.kind == STREAMMOMENT and choice.model.agent == agent.id and choice.model.model == ""
        assert choice.model.key_name() is None
        assert agents.marks(agent, choice.provider, "")["price"] == {"kind": "balance"}
    assert agents.default_connection(s).provider == "", "a call no agent declares is never sent to our key"


def test_every_prompt_holds_the_anchor_our_server_checks():
    vodcut = pytest.importorskip("vodcut.agents")
    fit = pytest.importorskip("vodcut.fit")
    every = {a.id: a for a in [*vodcut.AGENTS, *agents.CORE.values()]}
    assert set(every) == set(ANCHORS)
    for agent_id, a in every.items():
        text = fit.policy() if agent_id == "fit" else prompts.fill(prompts.text(a.prompt), channel="c", context="a stream", title="t", date="d", duration="1 h")
        assert ANCHORS[agent_id] in text[:20_000], agent_id


def test_a_call_still_in_flight_is_waited_for_with_the_same_key_not_paid_twice(fake):
    """The server may wait up to 630 s for the model: «in flight» is waited out with the same key (its answer is already
    paid), and only after that long the run is told to try later."""
    save_tokens()
    fake.call_answers = [(409, {"error": "in_flight"})] * 5
    assert providers.call(sm(), ANCHORS["scan"], {"type": "object"}).data == {"windows": []}
    assert len({c["key"] for c in fake.calls}) == 1 and len(fake.calls) == 6
    fake.calls.clear()
    fake.call_answers = [(409, {"error": "in_flight"})] * 40
    with pytest.raises(Overloaded):
        providers.call(sm(), ANCHORS["scan"], {"type": "object"})
    assert len({c["key"] for c in fake.calls}) == 1
    assert len(fake.calls) * providers.STREAMMOMENT_IN_FLIGHT_WAIT_S > 630


def test_a_site_without_sign_in_is_not_a_vpn_problem(fake):
    """Owner, 21.11: a 404 means our site answered without SMTV sign-in (not opened there yet) — the VPN hint is only for
    a server that does not answer, or a page that is not ours."""
    fake.hello = (404, {"message": "Route GET:/api/smtv/hello not found", "error": "Not Found", "statusCode": 404})
    r = account.check()
    assert not r["ok"] and r["hint"] == "" and "not open" in r["detail"]
    fake.raw = (404, b"<html>404 Not Found</html>")
    r = account.check()
    assert not r["ok"] and r["hint"] == "" and "not open" in r["detail"]
    err = account._fail(404, {"error": "Not Found", "statusCode": 404}, "sign-in")     # «Войти» on such a site
    assert err.code == "not_open" and err.hint == ""
    assert account._fail(404, {"error": "connect_expired"}, "sign-in").code == "connect_expired", "our own codes stay as they are"


def test_a_local_stand_is_set_in_the_settings_and_the_tokens_of_another_server_go(monkeypatch):
    save_tokens()
    assert account.set_server("http://localhost:3121") == "http://localhost:3121"
    assert account.server() == "http://localhost:3121" and account.signed_in() is None
    with pytest.raises(account.AccountError):
        account.set_server("http://evil.example")
    assert account.set_server(None) == "https://streammoment.tv"
