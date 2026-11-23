"""A StreamMoment account on this computer: sign-in, its tokens, the balance and buying a package (stage 22).

With the «StreamMoment» provider, calls to a model go through our server with our key: the person brings no key of
their own. Only the window's tokens are kept here — never a provider's key, which stays on our server.

Sign-in like `gh`, Codex and Claude Code (RFC 8252 loopback + PKCE): SMTV listens on 127.0.0.1 for one answer, opens our
page in the browser, the person signs in there (Google, Twitch, Telegram), our server sends the browser back to
127.0.0.1 with a one-time code, and SMTV trades it and its secret verifier for tokens. Where no browser can come back
(Docker, another computer), a device code (RFC 8628): SMTV shows a short code, the person types it on our page.

Tokens: a short access token (an hour) and a refresh token (60 days, a new one on every refresh), kept as one secret in
the keychain (or the encrypted file, `settings.set_secret`). The page and a job are two processes: a refresh happens under
a file lock, and the other one reads the new tokens instead of refreshing again (an old refresh token shown later ends the
session on the server: that is how a stolen copy is caught).

Reaching streammoment.tv: every failure to reach it says so and suggests the usual cause — a VPN.
"""
from __future__ import annotations

import base64
import hashlib
import http.server
import json
import os
import secrets
import socket
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

from . import paths
from .settings import delete_secret, get_secret, set_secret

SERVER = "https://streammoment.tv"
SECRET_NAME = "streammoment.session"
TIMEOUT_S = 15.0
CHECK_TIMEOUT_S = 6.0
LOGIN_WAIT_S = 600.0
REFRESH_EARLY_S = 120.0
# The site answered, but has no sign-in for SMTV yet (404): the network is fine, so no VPN hint (owner, 21.11).
NOT_OPEN = "StreamMoment answers, but sign-in for SMTV is not open on the site yet: try again later"
VPN_HINT = {
    "en": "The StreamMoment site cannot be reached. A VPN may be on: turn it off or add streammoment.tv to the VPN's exceptions.",
    "ru": "Сайт StreamMoment недоступен. Возможно, включён VPN — выключите его или добавьте streammoment.tv в исключения VPN.",
}


class AccountError(Exception):
    """Something the person can act on; `code` is the server's or ours, `hint` a step to take."""

    def __init__(self, code: str, message: str = "", hint: str = "", status: int | None = None):
        super().__init__(message or code)
        self.code, self.hint, self.status = code, hint, status


class NotSignedIn(AccountError):
    def __init__(self, message: str = "not signed in to StreamMoment: sign in in «Settings → Providers»"):
        super().__init__("not_signed_in", message)


class Unreachable(AccountError):
    def __init__(self, detail: str):
        super().__init__("unreachable", f"streammoment.tv cannot be reached: {detail}", VPN_HINT["en"])


def _allowed(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme == "https" or (parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost"))


def set_server(url: str | None) -> str:
    """`smtv account server <url>`: our server for this computer (a local test stand); None goes back to streammoment.tv.
    Kept in the settings (`tools.smtv.account_server`), so SMTV.app started from the Dock follows it too."""
    from .settings import Settings
    url = (url or "").strip().rstrip("/")
    if url and not _allowed(url):
        raise AccountError("bad_server", "the address must be https://…, or http:// on this computer")
    before = server()
    with Settings.edit() as s:
        own = s.tools.setdefault("smtv", {})
        if url and url != SERVER:
            own["account_server"] = url
        else:
            own.pop("account_server", None)
    if server() != before:            # tokens of another server mean nothing here
        delete_secret(SECRET_NAME)
    return server()


def server() -> str:
    """Our site. SMTV_ACCOUNT_URL (the person's own environment) or `smtv account server` (the settings) point to a local
    test stand: https, or http on this computer only."""
    url = os.environ.get("SMTV_ACCOUNT_URL", "").strip().rstrip("/")
    if not url:
        try:
            from .settings import Settings
            url = str((Settings.load().tools.get("smtv") or {}).get("account_server") or "").strip().rstrip("/")
        except Exception:  # noqa: BLE001 — unreadable settings: our own site
            url = ""
    if not url:
        return SERVER
    if _allowed(url):
        return url
    raise AccountError("bad_server", "the StreamMoment address must be https://…, or http:// on this computer")


# --- HTTP ---------------------------------------------------------------------------------------------------

def _request(method: str, path: str, body: dict | None = None, headers: dict | None = None, timeout: float = TIMEOUT_S) -> tuple[int, dict]:
    """(status, JSON answer). Never raises for an HTTP status; raises Unreachable when nothing answered."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(server() + path, data=data, method=method,
                                     headers={"Accept": "application/json", "User-Agent": "smtv", **({"Content-Type": "application/json"} if data else {}), **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw, status = response.read(), response.status
    except urllib.error.HTTPError as e:
        raw, status = e.read(), e.code
    except (urllib.error.URLError, TimeoutError, OSError, ssl.SSLError) as e:
        raise Unreachable(str(getattr(e, "reason", e))[:200]) from e
    try:
        answer = json.loads(raw.decode("utf-8")) if raw else {}
    except ValueError:
        answer = None
    if not isinstance(answer, dict):
        if status >= 500:         # our own front page while the server restarts: wait, not a VPN
            raise AccountError("server_unavailable", f"StreamMoment is not answering right now (HTTP {status}): try again in a minute", status=status)
        if 400 <= status < 500:   # our site answered, it just has no such address yet (sign-in not open there): not a VPN
            raise AccountError("not_open", NOT_OPEN, status=status)
        # a page instead of our answer: a VPN's or a network's own page
        raise AccountError("not_ours", f"streammoment.tv answered with something else (HTTP {status})", VPN_HINT["en"], status)
    return status, answer


def check() -> dict:
    """«Can StreamMoment be reached?»: our own server answered (not a captive portal or a VPN's page), with a timeout.
    {ok, detail, hint, sign_in, payments}. Asked by a button, before a sign-in and after a failure; never in the background."""
    started = time.monotonic()
    try:
        status, answer = _request("GET", "/api/smtv/hello", timeout=CHECK_TIMEOUT_S)
    except AccountError as e:
        return {"ok": False, "detail": str(e), "hint": e.hint, "sign_in": [], "payments": False}
    ms = round((time.monotonic() - started) * 1000)
    if 400 <= status < 500:      # the site answers, only without sign-in for SMTV: no VPN hint, the network is fine
        return {"ok": False, "detail": NOT_OPEN, "hint": "", "sign_in": [], "payments": False, "ms": ms}
    if status != 200 or answer.get("service") != "streammoment":
        return {"ok": False, "detail": f"streammoment.tv answered HTTP {status}, not as our server", "hint": VPN_HINT["en"], "sign_in": [], "payments": False}
    if not answer.get("enabled"):
        return {"ok": False, "detail": "sign-in to StreamMoment is not open yet", "hint": "", "sign_in": [], "payments": False, "ms": ms}
    return {"ok": True, "detail": f"answers in {ms} ms", "hint": "", "sign_in": list(answer.get("sign_in") or []),
            "payments": bool(answer.get("payments")), "ms": ms}


def _fail(status: int, answer: dict, what: str) -> AccountError:
    if status == 404 and answer.get("error") in (None, "Not Found"):   # Fastify's own 404 says «Not Found»; ours are codes     # our server, but without this address: sign-in is not open there yet
        return AccountError("not_open", NOT_OPEN, status=status)
    code = str(answer.get("error") or f"http_{status}")
    return AccountError(code, f"{what}: {code}", status=status)


# --- tokens -------------------------------------------------------------------------------------------------

def _load() -> dict | None:
    raw = get_secret(SECRET_NAME)
    if not raw:
        return None
    try:
        session = json.loads(raw)
    except ValueError:
        return None
    return session if isinstance(session, dict) and session.get("refresh_token") else None


def _save(tokens: dict) -> dict:
    session = {"access_token": tokens["access_token"], "refresh_token": tokens["refresh_token"],
               "expires_at": time.time() + float(tokens.get("expires_in") or 3600), "account": tokens.get("account") or {}}
    set_secret(SECRET_NAME, json.dumps(session))
    return session


def _lock_path() -> Path:
    return paths.home() / "run" / "account.lock"


@contextmanager
def _lock(timeout: float = 30.0):
    """One refresh at a time on this computer (the page and a job are separate processes)."""
    path = _lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a+b") as f:
        deadline = time.monotonic() + timeout
        while True:
            try:
                if sys.platform == "win32":
                    import msvcrt
                    f.seek(0)
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise AccountError("busy", "another SMTV process holds the account lock")
                time.sleep(0.1)
        try:
            yield
        finally:
            if sys.platform == "win32":
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def signed_in() -> dict | None:
    """{name, provider, id} of the account on this computer, or None. Reads only the keychain, no network."""
    try:
        session = _load()
    except Exception:  # noqa: BLE001 — a locked keychain: «not signed in» with no crash; the call says why
        return None
    return dict(session.get("account") or {}) if session else None


def _refresh(session: dict) -> dict:
    status, answer = _request("POST", "/api/smtv/token", {"grant_type": "refresh_token", "refresh_token": session["refresh_token"]})
    if status == 200:
        return _save(answer)
    if status == 409:            # another process of this computer refreshed a moment ago: its tokens are saved
        time.sleep(0.3)
        fresh = _load()
        if fresh and fresh["refresh_token"] != session["refresh_token"]:
            return fresh
    if status in (400, 401):
        delete_secret(SECRET_NAME)
        raise NotSignedIn("the StreamMoment sign-in on this computer has ended: sign in again in «Settings → Providers»")
    raise _fail(status, answer, "refresh")


def access_token(force: bool = False) -> str:
    """A valid access token; refreshed under the lock when it ends within two minutes (or `force`)."""
    session = _load()
    if not session:
        raise NotSignedIn()
    if not force and session.get("expires_at", 0) - time.time() > REFRESH_EARLY_S:
        return session["access_token"]
    with _lock():
        fresh = _load()
        if not fresh:
            raise NotSignedIn()
        if fresh["access_token"] != session["access_token"] and fresh.get("expires_at", 0) - time.time() > REFRESH_EARLY_S:
            return fresh["access_token"]          # another process refreshed while this one waited
        return _refresh(fresh)["access_token"]


def authorized(method: str, path: str, body: dict | None = None, headers: dict | None = None, timeout: float = TIMEOUT_S) -> tuple[int, dict]:
    """A request with the account's token; one refresh and one more try on 401."""
    status, answer = _request(method, path, body, {**(headers or {}), "Authorization": f"Bearer {access_token()}"}, timeout)
    if status == 401:
        status, answer = _request(method, path, body, {**(headers or {}), "Authorization": f"Bearer {access_token(force=True)}"}, timeout)
        if status == 401:
            raise NotSignedIn("StreamMoment no longer accepts this computer's sign-in: sign in again")
    return status, answer


# --- sign-in ------------------------------------------------------------------------------------------------

def _label() -> str:
    return f"SMTV on {socket.gethostname()[:60]}"


def _pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
    return verifier, challenge


DONE_PAGE = ("<!doctype html><meta charset=utf-8><title>SMTV</title><body style='font:16px system-ui;padding:48px;text-align:center'>"
             "<h1>{title}</h1><p>{text}</p></body>")


class Login:
    """One sign-in through the browser, waiting in a thread: `start()` returns the page to open; `state` follows it
    (waiting → done | failed), `error` says why. One at a time per process."""

    def __init__(self, opener: Callable[[str], object] | None = None, wait_s: float = LOGIN_WAIT_S):
        self.opener, self.wait_s = opener, wait_s
        self.state, self.error, self.url, self.account = "idle", "", "", None
        self._server: http.server.HTTPServer | None = None

    def start(self) -> str:
        verifier, challenge = _pkce()
        state = secrets.token_urlsafe(24)
        got: dict = {}
        done = threading.Event()

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):        # nothing of the request goes to the console
                pass

            def do_GET(self):  # noqa: N802
                parsed = urllib.parse.urlparse(self.path)
                query = dict(urllib.parse.parse_qsl(parsed.query))
                ours = parsed.path == "/callback" and query.get("state") == state and query.get("code")
                title, text = ("Готово", "Вернитесь в окно SMTV — вход завершается там. Эту вкладку можно закрыть.") if ours else \
                    ("Не тот адрес", "Этот адрес ждёт только ответа StreamMoment. Нажмите «Войти» в окне SMTV ещё раз.")
                body = DONE_PAGE.format(title=title, text=text).encode("utf-8")
                self.send_response(200 if ours else 400)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                if ours and not done.is_set():
                    got["code"] = query["code"]
                    done.set()

        srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        self._server = srv
        redirect = f"http://127.0.0.1:{srv.server_address[1]}/callback"
        try:
            status, answer = _request("POST", "/api/smtv/connect", {"state": state, "code_challenge": challenge, "redirect_uri": redirect})
        except AccountError:
            srv.server_close()
            raise
        if status != 200 or not isinstance(answer.get("url"), str) or not answer["url"].startswith(server() + "/"):
            srv.server_close()
            raise _fail(status, answer, "sign-in")
        self.url, self.state, self.error = answer["url"], "waiting", ""

        def serve():
            srv.timeout = 1.0
            deadline = time.monotonic() + self.wait_s
            try:
                while not done.is_set() and time.monotonic() < deadline and self.state == "waiting":
                    srv.handle_request()
            finally:
                srv.server_close()
            if self.state != "waiting":
                return
            if not done.is_set():
                self.state, self.error = "failed", "timeout"
                return
            try:
                status, tokens = _request("POST", "/api/smtv/token", {"grant_type": "authorization_code", "code": got["code"],
                                                                      "code_verifier": verifier, "redirect_uri": redirect, "label": _label()})
                if status != 200:
                    raise _fail(status, tokens, "sign-in")
                self.account = _save(tokens)["account"]
                self.state = "done"
            except AccountError as e:
                self.state, self.error = "failed", e.code
            except Exception as e:  # noqa: BLE001 — the keychain refused the tokens: the window must stop waiting and say so
                self.state, self.error = "failed", f"keychain: {type(e).__name__}"

        threading.Thread(target=serve, name="smtv-login", daemon=True).start()
        if self.opener:
            try:
                self.opener(self.url)
            except Exception:  # noqa: BLE001 — no browser here: the window shows the link and the device code
                pass
        return self.url

    def cancel(self) -> None:
        if self.state == "waiting":
            self.state, self.error = "failed", "cancelled"


class DeviceLogin:
    """Sign-in by a code typed on our page; polls in a thread at the server's pace."""

    def __init__(self):
        self.state, self.error, self.user_code, self.url, self.account = "idle", "", "", "", None

    def start(self) -> dict:
        status, answer = _request("POST", "/api/smtv/device")
        if status != 200 or not answer.get("device_code"):
            raise _fail(status, answer, "sign-in by code")
        code = str(answer["user_code"])
        self.user_code, self.url, self.state = f"{code[:4]}-{code[4:]}", str(answer.get("verification_uri_complete") or answer.get("verification_uri")), "waiting"
        device, interval, expires = answer["device_code"], max(2, int(answer.get("interval") or 5)), time.monotonic() + float(answer.get("expires_in") or 600)

        def poll():
            pause = interval
            while self.state == "waiting" and time.monotonic() < expires:
                time.sleep(pause)
                try:
                    status, tokens = _request("POST", "/api/smtv/token", {"grant_type": "device_code", "device_code": device, "label": _label()})
                except AccountError:
                    continue                  # the network came back and forth: keep waiting until the code ends
                if status == 200:
                    try:
                        self.account = _save(tokens)["account"]
                    except Exception as e:  # noqa: BLE001 — the keychain refused the tokens: say so, do not wait forever
                        self.state, self.error = "failed", f"keychain: {type(e).__name__}"
                        return
                    self.state = "done"
                    return
                error = tokens.get("error")
                if error == "slow_down":
                    pause += 5
                elif error != "authorization_pending":
                    self.state, self.error = "failed", str(error or f"http_{status}")
                    return
            if self.state == "waiting":
                self.state, self.error = "failed", "timeout"

        threading.Thread(target=poll, name="smtv-device-login", daemon=True).start()
        return {"user_code": self.user_code, "url": self.url}

    def cancel(self) -> None:
        if self.state == "waiting":
            self.state, self.error = "failed", "cancelled"


def sign_out() -> dict:
    """«Sign out on this computer»: the server ends this session; the tokens are deleted here even when it cannot be reached."""
    session = None
    try:
        session = _load()
    finally:
        delete_secret(SECRET_NAME)
    if not session:
        return {"signed_out": True, "server": False}
    try:
        status, answer = _request("POST", "/api/smtv/sign-out", {"refresh_token": session["refresh_token"]})
        return {"signed_out": True, "server": status == 200 and bool(answer.get("signed_out"))}
    except AccountError as e:
        return {"signed_out": True, "server": False, "detail": str(e), "hint": e.hint}


# --- balance and purchases ----------------------------------------------------------------------------------

def info() -> dict:
    """The account, its balance and the packages (also asks our server to look at payments still open)."""
    status, answer = authorized("GET", "/api/smtv/account")
    if status != 200:
        raise _fail(status, answer, "balance")
    return answer


def purchase(package: str) -> str:
    """The payment page of a package on our site (YooKassa); opened in the browser by the caller."""
    status, answer = authorized("POST", "/api/smtv/purchase", {"package": package})
    if status != 200 or not isinstance(answer.get("url"), str):
        raise _fail(status, answer, "purchase")
    url = answer["url"]
    if urllib.parse.urlparse(url).scheme != "https":
        raise AccountError("bad_payment_url", "the payment page is not https")
    return url
