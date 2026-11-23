"""`smtv serve`: the local page. Installed tools, their sections, jobs shown live from their event journals, settings.

Built on the standard library's HTTP server, not a web framework: the page has one person on one computer, a handful of
connections, JSON and a stream of events (SSE is a long response, nothing more). A framework would add a dozen packages
to every install for features this page does not use.

Safety:
- listens on 127.0.0.1; on a private address of the home network too only while «Phone access» is on (stage 9,
  `phone.py`): there every request needs the phone key (from the QR code, then a cookie), and the model key and changes
  to the program are refused;
- answers only requests whose Host is 127.0.0.1 or localhost on its own port (a foreign site cannot reach it through DNS rebinding);
- changes (POST, PUT) need the session token in the header X-SMTV-Token and, if the browser sends Origin or Sec-Fetch-Site,
  our own origin. The token is random, made when the server starts, and written only into the page itself (index.html),
  which another site cannot read; a plain GET link changes nothing. No CORS headers are ever sent;
- a key goes from the form to the keychain (or the private file) and is never sent back, logged or put in an error text;
- job files are served only from inside the job folder.

In Docker (stage 21, `container.py`) it listens on every address inside the container and every request needs the access
key (printed in the log as a link, then a cookie) on top of the rules above; the Host it answers is the published one.

The port is fixed (8642): a taken port is an error, not another port. The page runs in SMTV's own window (`window.py`),
which asks for `?window=mac|win|linux` so the header leaves room for that window's buttons from the first frame.
"""
from __future__ import annotations

import errno
import hmac
import html as html_mod
import http.client
import http.cookies
import json
import mimetypes
import os
import posixpath
import re
import secrets
import shutil
import signal
import socket
import sys
import threading
import time
import traceback
import urllib.parse
import webbrowser
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from smtv_core import agents as agents_mod
from smtv_core import checks as checks_mod
from smtv_core import crash, events, pause, paths, presets, prompts
from smtv_core.events import CANCELLED, ERROR, QUEUED, Journal
from smtv_core.llm import keycheck
from smtv_core import account as account_mod
from smtv_core.settings import (ANTHROPIC, CLAUDE_CODE, CLI_KINDS, CODEX, GEMINI, KINDS, OPENAI, PRESETS, STREAMMOMENT, Provider, Settings,
                                broken_notice, default_name, delete_secret, get_secret, secrets_backend, set_secret)
from smtv_core.settings import lock as settings_lock
from smtv_core.tool import Page, Tool

from . import __version__
from . import about as about_mod
from . import container
from . import fixes as fixes_mod
from . import i18n
from . import models_api
from . import phone as phone_access
from . import report as report_mod
from .activity import IDLE_MINUTES, Tracker
from .hub import Hub, jobs_by_key
from .jobs import QUEUED_STATUS, Busy, Runner, Tail, leftover, smtv_command, state as job_state, status, stop_leftover
from .tools import CATALOG, Broken, doctor_groups, plugins
from .updates import UpdateError, Updates
from .usage import Usage

HOST = "127.0.0.1"
DEFAULT_PORT = 8642
WEB = Path(__file__).parent / "web"
JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")
SERVED = {".mp4", ".jpg", ".jpeg", ".png", ".json", ".ass", ".log", ".txt", ".srt", ".vtt", ".webm"}
POLL_S, HEARTBEAT_S = 0.25, 15.0
QUEUE_RETRY_S = 30.0
UPLOAD_SPARE = 512 * 1024 * 1024   # an upload leaves this much free: the request needs room for its audio and clips
# A page from an earlier start of SMTV (its token is gone): the page reloads itself on this code (A20)
STALE_PAGE = "stale_page"
STALE_TEXT = "SMTV перезапустился: обновите страницу."          # after a start the system refused, or while a job left from before still runs
PAGE_TTL_S = 90.0
CLEAR_SITE_DATA = '"cache", "storage"'   # on removal: anything an older SMTV left in a browser for this site
SHELLS = {"mac", "win", "linux"}
PAGE_ID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
PAGE_RUN = "page-run.json"   # what the page started in this job folder, so it can be started again after a stop
HELLO_APP = "smtv"
ANY_ADDRESS = "0.0.0.0"   # only in Docker: the published port reaches the server inside the container this way
DOCKER_OPEN = {"/healthz", "/manifest.webmanifest", "/favicon.ico", "/static/icon.svg"}   # no key: nothing secret in them
MANIFEST = {"name": "SMTV", "short_name": "SMTV", "id": "/", "start_url": "/", "scope": "/", "display": "standalone",
            "background_color": "#181818", "theme_color": "#181818",
            "icons": [{"src": "/static/icons/icon-256.png", "sizes": "256x256", "type": "image/png"},
                      {"src": "/static/icons/icon-mac-512.png", "sizes": "512x512", "type": "image/png"}]}
CSP = ("default-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; style-src 'self' 'unsafe-inline'; "
       "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str = ""):
        super().__init__(message or code)
        self.status, self.code, self.message = status, code, message or code


class PortBusy(OSError):
    """The page's port is taken: by SMTV itself (`smtv` is True) or by another program."""

    def __init__(self, port: int, smtv: bool):
        super().__init__(f"port {port} is taken" + (" by SMTV" if smtv else ""))
        self.port, self.smtv = port, smtv


def page_url(port: int = DEFAULT_PORT) -> str:
    """The page's address as it may be shown and logged: without the launch key, it opens nothing by itself."""
    return f"http://{HOST}:{port}/"


def launch_url(port: int = DEFAULT_PORT) -> str:
    """The address the window and the browser open: the page with the launch key (decision 7). Never printed to a log."""
    return f"{page_url(port)}?launch={launch_key()}"


def launch_key() -> str:
    """The key in the address the window and the browser open SMTV with (decision 7 of the В2 review): without it, or
    the session's cookie, nobody gets the page that carries the session token — not another user of this computer, not a
    program that reaches 127.0.0.1 but cannot read this person's files. Kept in run/launch.key, readable only by its
    owner, and the same across starts: a page left open from an earlier start still loads after SMTV restarts (A20)."""
    path = paths.home() / "run" / "launch.key"
    for _ in range(40):
        try:
            key = path.read_text(encoding="utf-8").strip()
            if len(key) >= 32:
                return key
            if time.time() - path.stat().st_mtime > 5:      # empty or cut short long ago (a crash, a full disk): made again
                print(f"launch key: {path} was broken; a new one is made")
                path.unlink(missing_ok=True)
                continue
        except FileNotFoundError:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name(f".launch.{secrets.token_hex(4)}.tmp")
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(secrets.token_urlsafe(32))
            try:
                os.link(tmp, path)         # whole or not at all; a start that made one a moment earlier wins
            except FileExistsError:
                pass
            except OSError:                # a file system without hard links
                if not path.exists():
                    os.replace(tmp, path)
            finally:
                tmp.unlink(missing_ok=True)
            continue
        time.sleep(0.05)                   # just made by another start
    raise OSError(f"{path}: no launch key could be read or made")


def probe(port: int = DEFAULT_PORT, timeout: float = 1.5) -> dict | None:
    """What answers on the page's port: SMTV's hello, or None (nothing, or another program)."""
    try:
        conn = http.client.HTTPConnection(HOST, port, timeout=timeout)
        conn.request("GET", "/api/hello", headers={"Host": f"{HOST}:{port}"})
        resp = conn.getresponse()
        data = json.loads(resp.read(10_000) or b"{}") if resp.status == 200 else {}
        conn.close()
    except (OSError, ValueError, http.client.HTTPException):
        return None
    return data if isinstance(data, dict) and data.get("app") == HELLO_APP else None


PROMPTS_REPO = "https://github.com/streammomenttv/prompts"
LIVE_MODELS_TTL_S = 600
MODEL_ID = re.compile(r"^[A-Za-z0-9._:/@+-]*$")
TABLE_COLUMNS = ("codex", "claude_code", "openai", "openrouter", "anthropic", "gemini")
TABLE_LABELS = {"codex": "Codex CLI", "claude_code": "Claude Code CLI", "openai": "OpenAI", "openrouter": "OpenRouter",
                "anthropic": "Claude API", "gemini": "Gemini"}


class App:
    """Everything the page needs, apart from HTTP."""

    def __init__(self, tools: list[Tool], broken: list[Broken], runner: Runner | None = None):
        self.tools = {t.name: t for t in tools}
        self.broken = broken
        self.runner = runner or Runner(smtv_command)
        self.stopping = threading.Event()
        self.token = secrets.token_urlsafe(32)   # proof that a change comes from the page this server served
        self.launch = launch_key()                # the key in the address of the window's page (decision 7)
        self.tracker = Tracker(self.runner)
        self.usage = Usage()
        self.agent_usage: dict[str, Usage] = {}  # each tool's journals apart: one card counts only its own tools' calls
        self._live_models: dict[tuple, tuple[float, dict]] = {}   # the provider's own list of models, for a few minutes
        self._settings_lock = settings_lock()     # one load-change-save at a time: threads here, and other SMTV processes
        self._login: account_mod.Login | account_mod.DeviceLogin | None = None   # the StreamMoment sign-in in progress (stage 22)
        # downloads of models (stage 20): Ollama's and the speech models, in the background, one per model
        self.downloads = models_api.Downloads(on_change=lambda: self.hub.poke())
        self.quit = None                          # stops this server (set by `smtv serve` and `smtv app`)
        self.show_window = None                   # brings SMTV's window forward (set by `smtv app`)
        self.pick_file = None                     # the window's own «open file» dialog → a path or None (set by the window)
        self.lang: str | None = None              # the page's language (notifications speak it)
        self.port = DEFAULT_PORT                  # set by make_server
        self.docker: container.Docker | None = None   # SMTV in Docker (stage 21): the access key and the published hosts
        # Open pages. A page asks /api/activity every few seconds with its own id; it counts as open for PAGE_TTL_S
        # after that (hidden tabs are woken about once a minute). No connection is held for this: a browser allows six
        # per site across all tabs, and the page's job streams already hold some.
        self.streams = 0                          # job event streams being read now
        self.pages: dict[str, float] = {}
        self.clock = time.monotonic
        self._viewers_lock = threading.Lock()
        self._job_cache: dict[tuple[str, str], tuple[tuple, dict]] = {}
        # Updates and plugins from the window (stage 8), and the window's one stream of events
        self.updates = Updates(tools=lambda: list(self.tools), running=lambda: sum(1 for r in list(self.runner.runs.values()) if not r.finished.is_set()),
                               stop_jobs=self.runner.stop_all, port=lambda: self.port)
        self.updates.quit = lambda: self.quit() if self.quit else None
        self.hub = Hub(self._look, self.stopping)
        self.updates.on_change = self.hub.poke
        # Phone access over home Wi-Fi (stage 9): remembered between starts; `phone.restore()` after the server is made
        self.phone = phone_access.Phone(lambda address: make_phone_server(self, address), port=lambda: self.port, saved=phone_access.Saved())
        # The queue (stage 16): a request for a tool that is busy waits, and starts by itself when the running one ends,
        # pauses or fails. Its order lives in the jobs' own journals (a `queued` event), so it outlives a restart.
        self.queue_lock = threading.RLock()
        self.runner.on_finished = lambda run: self.queue_next(run.tool)
        self.instance = None                      # the data folder's lock (`instance.py`), held as long as this server
        self.removing = False                     # SMTV is being removed: nothing more starts
        self._queue_pause_until = 0.0             # after a failed start: the next try waits a little
        self._queue_timer: threading.Timer | None = None   # that next try, also when no window looks (B5)
        self._said_leftover: dict[tuple[str, str], int] = {}   # «still runs from before» is printed once per process
        # «Report a problem» (stage 17): reports shown in the window, kept until saved, so the archive holds exactly
        # what the person saw; the window's own errors (JavaScript) become crash files too, a few per minute at most
        self.reports: dict[str, report_mod.Report] = {}
        self._reports_lock = threading.Lock()
        self._window_crashes: list[float] = []
        # The check of this computer and «Fix» (stage 24): the last result for a little while (a check runs programs and
        # may ask our server), keys a provider refused at the last «Check again», and the fixes' consoles
        self._doctor_cache: tuple[float, dict, dict] | None = None
        self._doctor_lock = threading.Lock()
        self._keys_refused: dict[str, str] = {}
        self.fixes = fixes_mod.Fixes(on_done=self._fixed, busy=self._jobs_running)
        self.boot = secrets.token_hex(6)          # this start of the server: a page that sees another one reloads (A20)
        for tool in self.tools.values():          # what a delete left behind (a clip was open in a player): gone now
            if tool.page:
                try:
                    sweep_deleting(tool.page.jobs())
                except Exception:  # noqa: BLE001 — a tool whose folder cannot be read is listed without this
                    pass

    def _look(self) -> dict:
        """Everything the window shows, for the hub: a waiting update starts here once no job runs."""
        if self.updates.pending:
            try:
                self.updates.go()
            except UpdateError:
                pass
        jobs = self.jobs()
        self._queue_watch(jobs)
        return {"boot": self.boot, "jobs": jobs_by_key(jobs), "activity": {**self.tracker.snapshot(), "queued": sum(1 for j in jobs if j["status"] == QUEUED_STATUS)},
                "usage": self.tokens(), "update": self.updates.state(), "crash": crash.state()}

    def viewer(self, delta: int) -> None:
        with self._viewers_lock:
            self.streams += delta

    def page_seen(self, page: str) -> None:
        if not PAGE_ID.match(page):
            return
        with self._viewers_lock:
            now = self.clock()
            self.pages[page] = now
            for old in [k for k, t in self.pages.items() if now - t > PAGE_TTL_S]:
                del self.pages[old]

    @property
    def viewers(self) -> int:
        with self._viewers_lock:
            now = self.clock()
            return self.streams + sum(1 for t in self.pages.values() if now - t <= PAGE_TTL_S)

    def activity(self) -> dict:
        return {**self.tracker.snapshot(), "viewers": self.viewers}

    # --- the program ----------------------------------------------------------------------------------------

    def window_show(self) -> dict:
        """A second start of SMTV: bring the running one's window forward."""
        if not self.show_window:
            raise ApiError(409, "no_window", "this SMTV has no window: it was started with smtv serve")
        self.show_window()
        return {"shown": True}

    def _not_in_docker(self, what: str, instead: str) -> None:
        if self.docker:
            raise ApiError(409, "in_docker", f"{what} is not done from the page in Docker: {instead}")

    def quit_now(self) -> dict:
        """«Quit SMTV» from the page: running jobs stop, then the server."""
        self._not_in_docker("stopping SMTV", "docker compose stop")
        if not self.quit:
            raise ApiError(409, "cannot_quit", "this SMTV was started in a terminal: stop it there with Ctrl+C")
        print("quit: from the page")
        threading.Timer(0.5, self.quit).start()
        return {"quitting": True}

    @staticmethod
    def uninstall_plan() -> dict:
        from . import uninstall
        return uninstall.plan().as_dict()

    def uninstall(self, body: dict) -> dict:
        """Removes SMTV (the icon, the program; the data only with data: true), then this server quits."""
        self._not_in_docker("removing SMTV", "docker compose down (add -v to delete the data volume too)")
        if body.get("confirm") != "remove" or not isinstance(body.get("data", False), bool):
            raise ApiError(400, "not_confirmed", 'send {"confirm": "remove", "data": true|false}')
        from . import uninstall
        self.removing = True                      # the queue starts nothing more
        self.runner.stop_all()                    # jobs write into the data folder
        result = uninstall.run(body.get("data", False)).as_dict()
        if self.quit:
            print("quit: SMTV was removed from the page")
            threading.Timer(1.0, self.quit).start()
        return result

    # --- «Report a problem» (stage 17) ----------------------------------------------------------------------

    def report_preview(self, query: dict) -> dict:
        """Builds a report and shows it: every file in full, the issue's title and summary. Nothing is written."""
        tool, job = (query.get("tool") or [""])[0], (query.get("job") or [""])[0]
        names = (query.get("names") or ["0"])[0] == "1"
        target = None
        if tool and job:
            target = (tool, self.folder(tool, job))
        else:
            target = report_mod.find_job(list(self.tools.values()), None)   # the newest failed request, if any
        r = report_mod.collect(list(self.tools.values()), self.broken, job=target, names=names, extra_secrets=(self.token,))
        with self._reports_lock:
            self.reports[r.id] = r
            for old in list(self.reports)[:-6]:
                self.reports.pop(old, None)
        return {**r.preview(), "can_open": report_mod.can_open()}

    def report_save(self, body: dict) -> dict:
        """Saves the report the window showed, shows it in Finder or Explorer and opens a new issue in the browser."""
        r = self.reports.get(str(body.get("id") or ""))
        if not r:
            raise ApiError(404, "no_report", "this report is gone: open «Report a problem» again")
        if not r.saved:
            try:
                r.save()
            except OSError as first:            # Downloads is read-only or on a drive that is gone: SMTV's own folder
                try:
                    r.save(paths.home() / "reports")
                except OSError as e:
                    raise ApiError(500, "report_not_saved", f"the report could not be saved: {first}; {e}") from e
        path = r.saved
        url = report_mod.issue_url(r)
        opened = bool(body.get("open", True)) and report_mod.can_open()
        shown = opened and report_mod.reveal(path)
        browser = opened and report_mod.open_issue(url)
        crash.mark_seen(r.newest_crash)
        out = {"path": str(path), "folder": str(path.parent), "url": url, "shown": shown, "browser": browser}
        if self.docker:      # the archive is inside the container: the browser downloads it
            out["download"] = f"/api/report/{r.id}/archive"
        return out

    def report_file(self, rid: str) -> Path:
        r = self.reports.get(rid)
        if not r or not r.saved or not Path(r.saved).is_file():
            raise ApiError(404, "no_report", "save the report first")
        return Path(r.saved)

    def report_reveal(self, body: dict) -> dict:
        r = self.reports.get(str(body.get("id") or ""))
        if not r or not r.saved:
            raise ApiError(404, "no_report", "save the report first")
        return {"shown": report_mod.reveal(r.saved)}

    def window_crash(self, body: dict) -> dict:
        """An error in the window's own code (JavaScript): a crash file like any other."""
        now = time.monotonic()
        self._window_crashes = [t for t in self._window_crashes if now - t < 60]
        if len(self._window_crashes) >= 5:
            print("window error: more than 5 in a minute, not saved")
            return {"saved": False}
        text = lambda k, n: str(body.get(k) or "")[:n]  # noqa: E731
        path = crash.record(None, where="window", stage=text("where", 200) or None, message=text("message", 2000),
                            stack=text("stack", 8000))
        if path:
            self._window_crashes.append(now)   # a repeat that was not written takes no place from a new error
        return {"saved": bool(path)}

    def crashes_seen(self) -> dict:
        crash.mark_seen()
        return crash.state()

    # --- tools and settings -------------------------------------------------------------------------------

    @staticmethod
    def _page_info(page: Page) -> dict:
        """What the window needs to place a tool: its kind of request, its rail item, its icon (stage 7). Texts are keys of
        the tool's words; the window gets them in every language ({language: text}) and picks its own."""
        words = page.folder / "i18n"
        request = {**asdict(page.request), "title": i18n.texts(page.request.title, words),
                   "about": i18n.texts(page.request.about, words)} if page.request else None
        nav = {**asdict(page.nav), "title": i18n.texts(page.nav.title, words)} \
            if page.nav and re.match(r"^[a-z0-9-]{1,40}$", page.nav.id) else None
        return {"title": page.title, "options": bool(page.options), "estimate": bool(page.estimate), "icon": page.icon, "pause": page.pause, "again": bool(page.again),
                "about": i18n.texts(page.about, words), "request": request, "nav": nav}

    def _agent_words(self, agent) -> dict:
        """An agent's words in every language: from the language files of the tool that declares it (the window's for the
        core's shared agents), keys `agent.<id>.<field>`. A field no file has is empty."""
        tool = next((t for t in self.tools.values() if not agent.shared and any(a is agent for a in t.agents)), None)
        folder = tool.page.folder / "i18n" if tool and tool.page else None

        def say(field: str) -> dict:
            found = i18n.texts(f"agent.{agent.id}.{field}", folder)
            return {} if found == {i18n.SOURCE: f"agent.{agent.id}.{field}"} else found
        title = say("title") or {i18n.SOURCE: agent.id}
        return {"title": title, "short": say("short"), "does": say("does"), "stage": say("stage"),
                "needs": {**asdict(agent.needs), "text": say("needs"), "why": say("why")}}

    def state(self) -> dict:
        tools = [{"name": t.name, "version": t.version, "summary": t.summary, "page": self._page_info(t.page) if t.page else None,
                  "agents": len(t.agents)}
                 for t in self.tools.values()]
        catalog = [{"name": n, "summary": s, "installed": n in self.tools, "add": f"smtv add {n}"} for n, s in CATALOG.items()]
        return {"version": __version__, "events_version": events.VERSION, "tools": tools,
                "broken": [asdict(b) for b in self.broken], "catalog": catalog, "plugins": plugins(list(self.tools.values()), self.broken),
                "data": str(paths.data_dir()), "idle_minutes": IDLE_MINUTES,
                "soon": list(about_mod.soon()), "support": about_mod.SUPPORT_URL}

    DOCTOR_TTL_S = 30.0

    def _verify_key(self, live: bool):
        """For the model check: with `live`, a free request to each keyed provider (keycheck); otherwise what the last
        live check found refused stays refused until the providers change."""
        def verify(p: Provider) -> tuple[bool | None, str]:
            if not live:
                return (False, self._keys_refused[p.id]) if p.id in self._keys_refused else (None, "")
            found = keycheck.check(p.connection(""), timeout=8)
            if found.status in (keycheck.BAD_KEY, keycheck.NO_KEY):
                self._keys_refused[p.id] = found.detail[:200]
                return False, found.detail[:200]
            self._keys_refused.pop(p.id, None)
            return (True if found.status == keycheck.OK else None), ""
        return verify

    def _doctor_groups(self, live: bool = False) -> list[tuple[str, list]]:
        if self.lang:
            checks_mod.LANGUAGE_HINT = self.lang
        return doctor_groups(list(self.tools.values()), self.broken, verify=self._verify_key(live))

    def doctor(self, fresh: bool = False, live: bool = False) -> dict:
        """Every check, grouped, with what blocks each tool: a failed check of SMTV's own blocks every tool, a tool's own
        failed check blocks that tool (stage 24). Kept for a little while; any change from the window drops it."""
        with self._doctor_lock:
            cached = self._doctor_cache
            if cached and not fresh and not live and self.clock() - cached[0] < self.DOCTOR_TTL_S:
                return cached[1]
            groups = self._doctor_groups(live)
            rows = [{**r.public(), "group": g} for g, rs in groups for r in rs]
            blocks = {name: [r["id"] for r in rows if r["status"] == "fail" and r["group"] in ("smtv", name)] for name in self.tools}
            result = {"rows": rows, "ready": not any(r["status"] == "fail" for r in rows), "blocks": blocks,
                      "fixing": (run.state()["id"] if (run := self.fixes.running()) else None)}
            self._doctor_cache = (self.clock(), result, {})
            return result

    def doctor_stale(self, providers_changed: bool = False) -> None:
        self._doctor_cache = None
        if providers_changed:
            self._keys_refused.clear()

    def not_ready(self, name: str) -> None:
        """A new request of this tool cannot start while a check it needs fails: refused with the same reason the window
        shows above «What shall we process?»."""
        try:
            d = self.doctor()
        except Exception as e:  # noqa: BLE001 — a check that crashes must not stop every request: logged, not blocking
            print(f"doctor: {type(e).__name__}: {e}")
            return
        running = self.fixes.running()
        if running:
            raise ApiError(409, "fixing", "a fix is running (Settings → System): start the request when it ends")
        failing = [r for r in d["rows"] if r["id"] in (d["blocks"].get(name) or [])]
        if failing:
            names = "; ".join(f"{r['name']}: {r['detail']}" for r in failing)
            raise ApiError(409, "not_ready", f"fix this first (Settings → System): {names}")

    def _fixed(self) -> None:
        self.doctor_stale()
        self.hub.poke()

    def fix_start(self, body: dict) -> dict:
        """«Fix» on a check: its recipe, found by the check's id among checks built again now (never a command from the
        request)."""
        wanted = body.get("check")
        if not isinstance(wanted, str) or not wanted:
            raise ApiError(400, "bad_check", "check: the id of a check")
        found = next((r for _, rows in self._doctor_groups() for r in rows if (r.id or r.name) == wanted), None)
        if found is None:
            raise ApiError(404, "no_check", f"no check {wanted}")
        try:
            return self.fixes.start(found)
        except fixes_mod.FixError as e:
            raise ApiError(e.status, e.code, e.message) from None

    def fix_state(self, fid: str, after: int = 0) -> dict:
        try:
            return self.fixes.get(fid).state(after)
        except fixes_mod.FixError as e:
            raise ApiError(e.status, e.code, e.message) from None

    def fix_stop(self, fid: str) -> dict:
        try:
            return self.fixes.stop(fid)
        except fixes_mod.FixError as e:
            raise ApiError(e.status, e.code, e.message) from None

    def _busy_folder(self, tool: str, folder: Path) -> bool:
        if self.runner.running(tool, folder.name):
            return True
        try:
            self._job_cache.pop((tool, folder.name), None)
            return self._job_base(tool, folder.name)["status"] == QUEUED_STATUS
        except (ApiError, OSError):
            return True                       # not known: kept

    def _idle_job_folders(self) -> list[Path]:
        """Requests that neither run nor wait: their cache can go."""
        return [folder for tool, folder in self._job_folders() if not self._busy_folder(tool, folder)]

    def _loose_uploads(self) -> list[Path]:
        """Uploaded copies of videos no request uses any more (its request was deleted, or never started): B13."""
        folder = paths.data_dir() / "uploads"
        try:
            files = [f for f in folder.iterdir() if f.is_file()]
        except OSError:
            return []
        used = set()
        for _, job in self._job_folders():
            used.update(str(a) for a in (self._saved_run(job).get("args") or []))
        cutoff = time.time() - 3600                # one uploaded a moment ago is about to start: never removed under it
        out = []
        for f in files:
            try:
                if str(f) not in used and str(f.resolve()) not in used and f.stat().st_mtime < cutoff:
                    out.append(f)
            except OSError:
                pass
        return out

    def cache(self) -> dict:
        loose = sum(fixes_mod.size_of(f) for f in self._loose_uploads())
        return {"bytes": fixes_mod.cache_size(self._idle_job_folders()) + loose, "folder": str(paths.home())}

    def cache_clear(self) -> dict:
        tools = {folder: tool for tool, folder in self._job_folders()}
        with self.queue_lock:                 # nothing starts from the queue while the files go
            freed, left = fixes_mod.clear_cache(self._idle_job_folders(), busy=lambda f: self._busy_folder(tools.get(f, ""), f))
            for f in self._loose_uploads():
                size = fixes_mod.size_of(f)
                try:
                    f.unlink()
                    freed += size
                except OSError as e:
                    left.append(f"{f.name}: {e.strerror or e}")
        self.doctor_stale()
        return {"freed": freed, "left": left[:20], **self.cache()}

    def open_home(self) -> dict:
        self._not_in_docker("Opening SMTV's folder", "the data is in the volume /data")
        if not fixes_mod.open_folder(paths.home()):
            raise ApiError(500, "not_opened", f"the folder did not open: {paths.home()}")
        return {"ok": True}

    def tokens(self) -> dict:
        """Tokens spent by every job on this computer, from the `model_call` events of their journals."""
        return self.usage.total([folder / events.FILE_NAME for _, folder in self._job_folders()])

    # --- «Settings → Providers» (stage 19) ------------------------------------------------------------------

    @staticmethod
    def _choices() -> list[dict]:
        """What «Add a provider» offers: the OpenAI-compatible kind as OpenAI, OpenRouter and an address of your own, its
        local servers (Ollama, LM Studio, vLLM, llama.cpp) and cloud services (DeepSeek, Groq, …: stage 20), then Claude
        API, Gemini and the two CLIs; StreamMoment (stage 22, our key: an account instead of a key) first."""
        out = [{"choice": STREAMMOMENT, "kind": STREAMMOMENT, "preset": "", "base_url": "", "cli": False, "needs_key": False, "local": False,
                "group": "main", "account": True, "name": default_name(STREAMMOMENT)}]
        for pr in presets.PRESETS_LIST:
            group = "local" if pr.local else "cloud" if pr.id in presets.CLOUD else "main"
            out.append({"choice": pr.id, "kind": OPENAI, "preset": pr.id, "base_url": pr.base_url, "cli": False,
                        "needs_key": not pr.local and pr.id != "custom", "local": pr.local, "group": group, "api": pr.api,
                        "json_mode": pr.json_mode, "name": default_name(OPENAI, pr.id), "label": pr.label, "key_url": pr.key_url,
                        "key_hint": pr.key_hint, "note": pr.note})
        for kind in (ANTHROPIC, GEMINI, CODEX, CLAUDE_CODE):
            if kind in CLI_KINDS and container.active():
                continue          # not in Docker (stage 21): signing in to a subscription inside a container is awkward
            out.append({"choice": kind, "kind": kind, "preset": "", "base_url": "", "cli": kind in CLI_KINDS, "needs_key": kind not in CLI_KINDS,
                        "local": False, "group": "cli" if kind in CLI_KINDS else "main",
                        "name": default_name(kind), **keycheck.HELP[kind],
                        "rules": [{"title": t, "url": u} for t, u in keycheck.RULES.get(kind, [])], "steps": keycheck.STEPS.get(kind, [])})
        order = {"main": 0, "local": 1, "cloud": 2, "cli": 3}
        return sorted(out, key=lambda c: order[c["group"]])       # sorted() keeps the order within a group

    def _users(self) -> dict[str, list]:
        return {t.name: list(t.agents) for t in self.tools.values() if t.agents}

    def _provider_public(self, p: Provider, settings: Settings) -> dict:
        name = p.key_name()
        try:
            saved = bool(name and get_secret(name))
            unreadable = False
        except Exception:  # noqa: BLE001 — a damaged key file or a locked keychain: shown as «no key», with the reason
            saved, unreadable = False, True
        using = sum(1 for tool, agents in self._users().items() for a in agents
                    if agents_mod.resolve(settings, tool, a).provider is p)
        return {"id": p.id, "kind": p.kind, "name": p.name or default_name(p.kind, p.preset), "preset": p.preset,
                "base_url": p.base_url if p.kind == OPENAI else "", "json_mode": p.json_mode, "reasoning_effort": p.reasoning_effort,
                "default_model": p.default_model, "enabled": p.enabled, "cli": p.kind in CLI_KINDS, "table": p.table_key(),
                "images": agents_mod.sees_images(p.kind), "agents": using, "local": p.local(), "api": p.api(),
                "key": {"needed": p.needs_key(), "saved": saved,
                        "unreadable": unreadable, "where": secrets_backend()}}

    def settings(self) -> dict:
        s = Settings.load()
        return {"providers": [self._provider_public(p, s) for p in s.providers if p.kind in KINDS],
                "choices": self._choices(), "where": secrets_backend(), "broken": broken_notice()}

    @staticmethod
    def _apply(p: Provider, body: dict) -> None:
        """Fields of a provider from the window, checked. The key is not here: it goes straight to the keychain."""
        if "name" in body:
            name = str(body.get("name") or "").strip()[:60]
            p.name = name or default_name(p.kind, p.preset)
        if p.kind == OPENAI and body.get("base_url") is not None:
            url = str(body["base_url"]).strip()
            if not re.match(r"^https?://[^\s]+$", url):
                raise ApiError(400, "bad_base_url", "the server address starts with http:// or https://")
            p.base_url = url
        if "default_model" in body:
            model = body.get("default_model")
            if not isinstance(model, str) or len(model) > 200 or not MODEL_ID.match(model):
                raise ApiError(400, "bad_model", "model: the id exactly as the provider names it")
            p.default_model = model
        if body.get("json_mode") in ("schema", "object", "none"):
            p.json_mode = body["json_mode"]
        if body.get("reasoning_effort") in ("minimal", "low", "medium", "high"):
            p.reasoning_effort = body["reasoning_effort"]
        if "enabled" in body:
            if not isinstance(body["enabled"], bool):
                raise ApiError(400, "bad_enabled", "enabled: true or false")
            p.enabled = body["enabled"]

    def _save_key(self, p: Provider, body: dict) -> None:
        key = str(body.get("key") or "").strip()
        if not key:
            return
        if not p.key_name():
            raise ApiError(400, "no_key_needed", "this provider signs in on its own and needs no key")
        set_secret(p.key_name(), key)
        self._forget_live(p.id)

    def _forget_live(self, pid: str) -> None:
        for k in [k for k in list(self._live_models) if k[0] == pid]:
            self._live_models.pop(k, None)

    def provider_add(self, body: dict) -> dict:
        with self._settings_lock:
            return self._provider_add_locked(body)

    def _provider_add_locked(self, body: dict) -> dict:
        settings = Settings.load()
        kind, preset = body.get("kind"), str(body.get("preset") or "")
        if kind not in KINDS:
            raise ApiError(400, "bad_provider", f"kind: one of {', '.join(KINDS)}")
        if kind in CLI_KINDS and container.active():
            raise ApiError(400, "cli_not_in_docker", "the Codex and Claude Code CLIs are not available in Docker: use an API key")
        if kind == STREAMMOMENT and any(o.kind == STREAMMOMENT for o in settings.providers):
            raise ApiError(409, "already_added", "StreamMoment is already on the list: one account per computer")
        if kind == OPENAI and preset not in PRESETS:
            raise ApiError(400, "bad_preset", f"preset: one of {', '.join(PRESETS)}")
        p = Provider(id=settings.new_id(kind if kind != OPENAI or preset in ("openai", "") else preset), kind=kind,
                     preset=preset if kind == OPENAI else "")
        if kind == OPENAI:
            pr = presets.get(preset)
            p.base_url, p.json_mode, p.default_model = pr.base_url, pr.json_mode, pr.default_model
            if preset == "custom" and not body.get("base_url"):
                raise ApiError(400, "bad_base_url", "the server address starts with http:// or https://")
        self._apply(p, {"name": "", **body})
        settings.providers.append(p)
        self._save_key(p, body)        # the key first: a provider is never saved pointing at a key that failed to save
        settings.save()
        could = sum(1 for tool, agents in self._users().items() for a in agents
                    if agents_mod.recommendation(a.id, p.table_key()) is not None and agents_mod.suits(a, p))
        return {**self.settings(), "added": p.id, "can_recommend": could}

    def _provider(self, settings: Settings, pid: str) -> Provider:
        p = settings.provider(pid)
        if p is None or p.kind not in KINDS:
            raise ApiError(404, "no_provider", f"no provider {pid}")
        return p

    def provider_update(self, pid: str, body: dict) -> dict:
        with self._settings_lock:
            return self._provider_update_locked(pid, body)

    def _provider_update_locked(self, pid: str, body: dict) -> dict:
        settings = Settings.load()
        p = self._provider(settings, pid)
        old_url = p.base_url
        self._apply(p, body)
        if p.base_url != old_url and not str(body.get("key") or "").strip():
            # B15: a key saved for one server never goes to another one; the window asks for it again
            name = p.key_name()
            if name and not any(o is not p and o.key_name() == name for o in settings.providers):
                try:
                    delete_secret(name)
                except Exception as e:  # noqa: BLE001 — a locked keychain: nothing changes, the person is told
                    raise ApiError(500, "key_not_deleted", f"the address was not changed: the old key could not be removed "
                                                           f"({type(e).__name__}); unlock the keychain and try again") from None
        self._save_key(p, body)
        self._forget_live(p.id)
        settings.save()
        return self.settings()

    def provider_delete(self, pid: str) -> dict:
        with self._settings_lock:
            return self._provider_delete_locked(pid)

    def _provider_delete_locked(self, pid: str) -> dict:
        settings = Settings.load()
        p = self._provider(settings, pid)
        settings.providers.remove(p)
        agents_mod.forget_provider(settings, p.id)
        # its key goes first (unless another provider still reads the same name): a key that cannot be deleted leaves
        # the provider in place with a clear error, never a removed provider whose key stays for the next one of its id
        name = p.key_name()
        if name and not any(o.key_name() == name for o in settings.providers):
            try:
                delete_secret(name)
            except Exception as e:  # noqa: BLE001 — a locked keychain, an unreadable key file
                raise ApiError(500, "key_not_deleted", f"the key of {p.name or p.id} could not be deleted ({type(e).__name__}); "
                                                       "the provider is kept: unlock the keychain and try again") from None
        settings.save()
        self._forget_live(p.id)
        return self.settings()

    def provider_check(self, pid: str | None, body: dict) -> dict:
        """«Check»: a free request (the list of models) or the CLI's sign-in status. Before adding, `body` holds the kind."""
        if pid:
            p = self._provider(Settings.load(), pid)
        else:
            kind, preset = body.get("kind"), str(body.get("preset") or "")
            if kind not in KINDS or (kind == OPENAI and preset not in PRESETS):
                raise ApiError(400, "bad_provider", "choose a provider")
            p = Provider(id="new", kind=kind, preset=preset, base_url=PRESETS.get(preset, "") if kind == OPENAI else "")
            self._apply(p, {k: v for k, v in body.items() if k in ("base_url",)})
        if p.kind == STREAMMOMENT:
            return self.account_check()
        m = p.connection("")
        key = str(body.get("key") or "").strip() or None
        # a provider not added yet has no saved key: only the one typed in counts, not another saved one or the environment
        result = keycheck.check(m, key, saved=bool(pid)).as_dict()
        result["models"] = len(result.get("models") or [])
        return result

    def _live_list(self, p: Provider) -> dict:
        """The provider's own list of models: a free request with the saved key (never sent anywhere else), kept for a
        few minutes. The CLIs have none: their known list comes from the table; StreamMoment's model is our server's."""
        if p.kind in CLI_KINDS or p.kind == STREAMMOMENT:
            return {"ok": True, "detail": "", "models": [], "info": {}}
        key = (p.id, p.base_url, p.kind)
        cached = self._live_models.get(key)
        if cached and time.monotonic() - cached[0] < LIVE_MODELS_TTL_S:
            return cached[1]
        found = keycheck.check(p.connection(""))
        result = {**found.as_dict(), "info": found.info}
        if found.status == keycheck.OK:        # a failure is not kept: the next look asks again
            self._live_models[key] = (time.monotonic(), result)
        return result

    def provider_models(self, pid: str, query: dict) -> dict:
        """The models of a provider for the dropdown: the table's known ones, then the provider's own list; each with
        «recommended / tested / reads images», its price and, for an agent, its warnings. A provider that does not
        answer gives the known ones and a reason, and the window offers to type a name."""
        settings = Settings.load()
        p = self._provider(settings, pid)
        agent = None
        spec = (query.get("agent") or [""])[0]
        if spec:
            tool, _, agent_id = spec.partition("/")
            _t, agent = self._agent(tool, agent_id)
        live = self._live_list(p)
        known = list(agents_mod.known_models(p.table_key()))
        ids = known + sorted(set(live.get("models") or []) - set(known))
        if p.default_model and p.default_model not in ids:
            ids.append(p.default_model)
        probe = agent or agents_mod.Agent(id="_", prompt="", schema="", needs=agents_mod.Needs(level="light"))
        rows = []
        for i in ids:
            if not i and p.kind not in CLI_KINDS + (STREAMMOMENT,):
                continue
            m = agents_mod.marks(probe, p, i, (live.get("info") or {}).get(i))
            if not agent:
                m["recommended"], m["warnings"] = False, []
            rows.append({"id": i, **m})
        if agent:       # suitable first: recommended, then tested, then the rest; a model with warnings last
            rows.sort(key=lambda r: (not r["recommended"], not r["tested"], bool(r["warnings"])))
        return {"provider": p.id, "kind": p.kind, "models": rows,
                "live": {"ok": bool(live.get("ok")), "status": live.get("status", ""), "detail": live.get("detail", "")}}

    def provider_recommend(self, pid: str) -> dict:
        """«Give the agents this provider's recommended models»."""
        with self._settings_lock:
            return self._provider_recommend_locked(pid)

    def _provider_recommend_locked(self, pid: str) -> dict:
        settings = Settings.load()
        p = self._provider(settings, pid)
        try:
            done = agents_mod.assign_recommended(settings, p.id, self._users())
        except ValueError as e:
            raise ApiError(400, "provider_off", str(e)) from None
        settings.save()
        return {"assigned": [{"tool": t, "agent": a, "model": m} for t, a, m in done], **self.settings_agents()}

    # --- the StreamMoment account (stage 22) ------------------------------------------------------------------------
    # The window never polls our server in the background: the balance is asked when the section is open, after a
    # purchase for a few minutes, and by the person's button.

    @staticmethod
    def _account_error(e: Exception) -> ApiError:
        if isinstance(e, account_mod.NotSignedIn):
            return ApiError(401, "not_signed_in", str(e))
        if isinstance(e, account_mod.AccountError):
            text = str(e) + (f" {e.hint}" if e.hint else "")
            return ApiError(502 if e.code in ("unreachable", "not_ours", "server_unavailable") else 400, e.code, text)
        return ApiError(500, "account_failed", f"{type(e).__name__}")

    def account_check(self) -> dict:
        """«Check access to StreamMoment»: our server answers (not a VPN's page), with a timeout."""
        found = account_mod.check()
        who = account_mod.signed_in()
        return {"ok": bool(found["ok"] and who), "status": keycheck.OK if found["ok"] and who else keycheck.NOT_SIGNED_IN if found["ok"] else keycheck.UNREACHABLE,
                "detail": found["detail"], "reachable": found["ok"], "hint": found.get("hint", ""), "signed_in": who is not None,
                "account": True, "models": 0}

    def account(self, live: bool) -> dict:
        """The account on this computer; with `live`, its balance and packages from our server."""
        login = self._login
        if login and login.state == "done" and not getattr(login, "provider_added", False):
            login.provider_added = True
            self._ensure_streammoment()
        who = account_mod.signed_in()
        out = {"signed_in": who is not None, "account": who, "server": account_mod.server(),
               "login": {"state": login.state, "error": login.error, "url": login.url,
                         "user_code": getattr(login, "user_code", "")} if login else None}
        if who and live:
            try:
                out.update(account_mod.info())
            except account_mod.NotSignedIn:
                out.update(signed_in=False, account=None)
            except account_mod.AccountError as e:
                out["error"] = {"code": e.code, "detail": str(e), "hint": e.hint}
            except Exception as e:  # noqa: BLE001 — a locked keychain while refreshing: shown with its reason, never a bare 500
                out["error"] = {"code": "account_failed", "detail": f"the account could not be read ({type(e).__name__}): unlock the keychain and try again", "hint": ""}
        return out

    def _ensure_streammoment(self) -> None:
        """Signed in from the profile menu: StreamMoment joins the providers (last, so a provider the person already has
        keeps its agents) — signing in is enough, nothing else to add by hand. Removed later, it stays removed."""
        with self._settings_lock:
            settings = Settings.load()
            if any(p.kind == STREAMMOMENT for p in settings.providers):
                return
            settings.providers.append(Provider(id=settings.new_id(STREAMMOMENT), kind=STREAMMOMENT, name=default_name(STREAMMOMENT)))
            settings.save()

    def account_login(self, body: dict) -> dict:
        """Sign in: through the browser (default), or by a code typed on our page («device»)."""
        if self._login and self._login.state == "waiting":
            self._login.cancel()
        try:
            if body.get("mode") == "device":
                login = account_mod.DeviceLogin()
                login.start()
            else:
                login = account_mod.Login(opener=webbrowser.open)
                login.start()
        except Exception as e:  # noqa: BLE001 — our server cannot be reached: the window says why and suggests the VPN
            raise self._account_error(e) from None
        self._login = login
        return self.account(False)

    def account_logout(self) -> dict:
        if self._login:
            self._login.cancel()
        try:
            done = account_mod.sign_out()
        except Exception as e:  # noqa: BLE001 — a locked keychain: the tokens could not be deleted
            raise self._account_error(e) from None
        return {**self.account(False), "server_signed_out": done.get("server", False), "hint": done.get("hint", "")}

    def account_buy(self, body: dict) -> dict:
        """A package's payment page on our site, opened in the browser; the window then asks the balance for a while."""
        package = str(body.get("package") or "")
        if not re.match(r"^[a-z0-9_-]{1,40}$", package):
            raise ApiError(400, "bad_package", "package: one of the account's packages")
        try:
            url = account_mod.purchase(package)
        except Exception as e:  # noqa: BLE001
            raise self._account_error(e) from None
        try:
            webbrowser.open(url)
        except Exception:  # noqa: BLE001 — no browser: the window shows the link
            pass
        return {"url": url}

    # --- local servers, Ollama's models, «Settings → Speech» (stage 20) -------------------------------------------

    def _refused(self, call, *args):
        try:
            return call(*args)
        except models_api.Refused as e:
            raise ApiError(e.status, e.code, e.message) from None

    def providers_discover(self) -> dict:
        """«Find on this computer»: Ollama, LM Studio, vLLM, llama.cpp at their usual addresses."""
        return models_api.discover(Settings.load())

    def _ollama(self, pid: str) -> Provider:
        p = self._provider(Settings.load(), pid)
        if p.api() != "ollama":
            raise ApiError(400, "not_ollama", "this provider is not Ollama")
        return p

    def ollama_state(self, pid: str) -> dict:
        return models_api.ollama_state(self._ollama(pid), self.downloads)

    def ollama_action(self, pid: str, action: str, body: dict) -> dict:
        p = self._ollama(pid)
        model = str(body.get("model") or "")
        if action == "pull":
            self._refused(models_api.ollama_pull, p, model, self.downloads, lambda: self._forget_live(p.id))
        elif action == "delete":
            self._refused(models_api.ollama_delete, p, model, self.downloads)
            self._forget_live(p.id)
        elif action == "cancel":
            self.downloads.cancel(f"ollama:{p.id}:{model}")
        else:
            raise ApiError(404, "not_found", "no such action")
        return self.ollama_state(pid)

    def _jobs_running(self) -> bool:
        return any(not r.finished.is_set() for r in list(self.runner.runs.values()))

    def speech(self) -> dict:
        return models_api.speech_state(Settings.load(), self.downloads, self._jobs_running)

    def speech_action(self, model_id: str, action: str) -> dict:
        if action == "download":
            self._refused(models_api.speech_download, model_id, self.downloads, self._jobs_running())
        elif action == "delete":
            self._refused(models_api.speech_remove, model_id, self.downloads, self._jobs_running())
        elif action == "cancel":
            self.downloads.cancel(f"speech:{model_id}")
        else:
            raise ApiError(404, "not_found", "no such action")
        return self.speech()

    def speech_choose(self, body: dict) -> dict:
        with self._settings_lock:
            settings = Settings.load()
            self._refused(models_api.speech_choose, settings, body)
            settings.save()
        return self.speech()

    # --- «Settings → Agents» (stage 19) and the plugin's read-only tab (stage 10) --------------------------------

    def _agent(self, name: str, agent_id: str):
        tool = self.tools.get(name)
        agent = next((a for a in (tool.agents if tool else []) if a.id == agent_id), None)
        if not agent:
            raise ApiError(404, "no_agent", f"no agent {agent_id} in {name}")
        return tool, agent

    def _agent_stats(self, users: list[str], agent) -> dict:
        """One line from the model_call events of the journals of the tools that use this agent."""
        rows = []
        for user in users:
            journals = [f / events.FILE_NAME for n, f in self._job_folders() if n == user]
            rows.append(self.agent_usage.setdefault(user, Usage()).by_purpose(journals))
        out = {"calls": 0, "seconds": 0.0, "timed": 0, "errors": 0, "cost_usd": 0.0, "cost_known": False}
        for by in rows:
            for purpose in agent.calls():
                row = by.get(purpose)
                if row:
                    for k in ("calls", "seconds", "timed", "errors", "cost_usd"):
                        out[k] += row[k]
                    out["cost_known"] = out["cost_known"] or row["cost_known"]
        return {"calls": out["calls"], "avg_s": round(out["seconds"] / out["timed"], 1) if out["timed"] else None,
                "errors": out["errors"], "cost_usd": round(out["cost_usd"], 4) if out["cost_known"] else None}

    def _recommendations(self, agent, settings: Settings) -> list[dict]:
        """What the table recommends and what was tested, for every provider column; the columns of connected providers first."""
        connected = {p.table_key() for p in settings.enabled()}
        recs = []
        for col in TABLE_COLUMNS:
            rec = agents_mod.recommendation(agent.id, col)
            if rec:
                m = agents_mod.marks(agent, col, rec["model"])
                recs.append({"provider": col, "label": TABLE_LABELS.get(col, col), "model": rec["model"], "model_label": m["label"],
                             "tested": m["tested"], "warnings": m["warnings"], "connected": col in connected})
        recs.sort(key=lambda r: not r["connected"])
        return recs

    def _agent_card(self, name: str, agent, settings: Settings) -> dict:
        users = [t.name for t in self.tools.values() if any(a.id == agent.id for a in t.agents)]
        try:
            schema_text = json.dumps(prompts.schema(agent.schema), ensure_ascii=False, indent=2)
            prompt_text = prompts.text(agent.prompt)
        except OSError:
            schema_text = prompt_text = None
        return {**agent.as_dict(), **self._agent_words(agent), "users": users, "prompt_text": prompt_text, "schema_text": schema_text,
                "current": agents_mod.resolve(settings, name, agent).as_dict(agent),
                "recommendations": self._recommendations(agent, settings), "stats": self._agent_stats(users, agent)}

    def agents(self, name: str) -> dict:
        """The plugin's «Agents» tab: read only; the provider and the model are changed in «Settings → Agents»."""
        tool = self.tools.get(name)
        if not tool:
            raise ApiError(404, "no_tool", f"no tool {name}")
        settings = Settings.load()
        table = agents_mod.table()
        return {"prompts": {"version": prompts.version(), "date": (table.get("prompts") or {}).get("date"),
                            "table_date": table.get("updated"), "repo": PROMPTS_REPO},
                "providers": len(settings.enabled()),
                "agents": [self._agent_card(name, a, settings) for a in tool.agents]}

    def settings_agents(self) -> dict:
        """«Settings → Agents»: every agent of every plugin, grouped by plugin; the core's shared agents once."""
        settings = Settings.load()
        groups, shared = [], {}
        for tool in self.tools.values():
            own = []
            for a in tool.agents:
                if a.shared:
                    shared.setdefault(a.id, (a, []))[1].append(tool.name)
                    continue
                own.append(self._settings_row(tool.name, [tool.name], a, settings))
            if own:
                groups.append({"id": tool.name, "core": False, "title": tool.page.title if tool.page else tool.name, "agents": own})
        if shared:
            groups.append({"id": "core", "core": True, "title": "", "agents": [self._settings_row(users[0], users, a, settings)
                                                                                 for a, users in shared.values()]})
        return {"providers": [{"id": p.id, "name": p.name or default_name(p.kind, p.preset), "kind": p.kind, "enabled": p.enabled,
                               "images": agents_mod.sees_images(p.kind), "cli": p.kind in CLI_KINDS} for p in settings.providers if p.kind in KINDS],
                "groups": groups}

    def _settings_row(self, tool: str, users: list[str], agent, settings: Settings) -> dict:
        current = agents_mod.resolve(settings, tool, agent)
        # a shared agent shown once: if its tools went different ways (chosen before stage 19), the window says so
        differs = any(agents_mod.resolve(settings, u, agent).model.model != current.model.model
                      or agents_mod.resolve(settings, u, agent).provider is not current.provider for u in users[1:])
        return {"tool": tool, "users": users, "id": agent.id, **self._agent_words(agent), "shared": agent.shared, "current": current.as_dict(agent), "differs": differs,
                "providers": [p.id for p in settings.enabled() if agents_mod.suits(agent, p)]}

    def settings_agent_set(self, name: str, agent_id: str, body: dict) -> dict:
        """Give an agent a provider and a model, or (reset) back to the recommended ones. A shared agent of the core is
        set for every plugin that uses it: it is one row in the settings."""
        with self._settings_lock:
            return self._settings_agent_set_locked(name, agent_id, body)

    def _settings_agent_set_locked(self, name: str, agent_id: str, body: dict) -> dict:
        _tool, agent = self._agent(name, agent_id)
        settings = Settings.load()
        users = [t.name for t in self.tools.values() if any(a.id == agent.id for a in t.agents)] if agent.shared else [name]
        if body.get("reset") is True:
            for u in users:
                agents_mod.reset_model(settings, u, agent.id)
        else:
            pid, model = body.get("provider"), body.get("model")
            if not isinstance(pid, str) or not isinstance(model, str) or len(model) > 200 or not MODEL_ID.match(model):
                raise ApiError(400, "bad_model", "model: the id exactly as the provider names it")
            p = settings.provider(pid)
            if p is not None and not model and p.kind not in CLI_KINDS + (STREAMMOMENT,):
                raise ApiError(400, "bad_model", "model: the id exactly as the provider names it")
            default = agents_mod.resolve(Settings(providers=settings.providers), name, agent)
            try:
                for u in users:
                    if p is not None and default.provider is p and default.model.model == model:
                        agents_mod.reset_model(settings, u, agent.id)      # the default anyway: follows the table from now on
                    else:
                        agents_mod.set_model(settings, u, agent, pid, model)
            except ValueError as e:
                raise ApiError(400, "bad_provider", str(e)) from None
        settings.save()
        return self.settings_agents()

    def _page_tool(self, name: str) -> Tool:
        tool = self.tools.get(name)
        if not tool or not tool.page:
            raise ApiError(404, "no_tool", f"no tool {name} with a page")
        return tool

    def options(self, name: str) -> list[dict]:
        page = self._page_tool(name).page
        return page.options(Settings.load()) if page.options else []

    def set_option(self, name: str, body: dict) -> list[dict]:
        page = self._page_tool(name).page
        if not page.set_option or not isinstance(body.get("value"), bool):
            raise ApiError(400, "bad_option", "value: true or false")
        try:
            with Settings.edit() as settings:
                page.set_option(settings, str(body.get("name")), body["value"])
        except KeyError:
            raise ApiError(400, "bad_option", f"no switch {body.get('name')}") from None
        return page.options(settings)

    def estimate(self, name: str, body: dict) -> dict:
        page = self._page_tool(name).page
        if not page.estimate:
            raise ApiError(404, "no_estimate")
        try:
            return page.estimate(body)
        except ValueError as e:
            raise ApiError(400, "bad_fields", str(e)) from None

    # --- jobs ---------------------------------------------------------------------------------------------

    def folder(self, name: str, job: str) -> Path:
        page = self._page_tool(name).page
        if not JOB_ID.match(job) or ".." in job:
            raise ApiError(404, "no_job")
        folder = page.jobs() / job
        if not folder.is_dir():
            raise ApiError(404, "no_job", f"no job {job}")
        return folder

    def start(self, name: str, body: dict) -> dict:
        page = self._page_tool(name).page
        self.not_ready(name)
        try:
            spec = page.start(body)
        except ValueError as e:
            raise ApiError(400, "bad_fields", str(e)) from None
        return self._launch(name, spec.folder, spec.args)

    def _launch(self, name: str, folder: Path, args: list[str], by: str = "page") -> dict:
        """Runs the job now, or puts it in the queue when another job of this tool runs or waits."""
        if not JOB_ID.match(folder.name):           # a folder the list cannot show could be neither seen nor stopped
            raise ApiError(400, "bad_name", f"SMTV cannot name the request folder «{folder.name}»: rename the file and try again")
        with self.queue_lock:
            if self.runner.running(name, folder.name):
                raise ApiError(409, "running", "the request is still running")
            self._no_leftover(folder)
            if folder.name in self._queue(name):
                return self.job(name, folder.name)          # asked twice: it keeps its place
            if self.runner.busy(name) or self._queue(name) or self._held():
                self._enqueue(name, folder, args, by)
            else:
                try:
                    self._run(name, folder, args, by)
                except Busy:                                # cannot happen under the queue's lock; queued all the same
                    self._enqueue(name, folder, args, by)
                except OSError as e:
                    raise ApiError(500, "not_started", f"the job could not start: {e}") from None
        self.queue_next(name)                               # a queue that waited without a runner goes on now
        return self.job(name, folder.name)

    def _held(self) -> bool:
        """Nothing new starts from the queue: SMTV quits, is being removed, a change of SMTV waits for the jobs to end,
        «Fix» installs a program (a job would take the ffmpeg being replaced), or a speech model is being downloaded
        (a job would download the same model into the same folder)."""
        return (self.stopping.is_set() or self.removing or bool(self.updates.pending) or bool(self.updates.leaving)
                or self.fixes.running() is not None or self._speech_downloading())

    def _speech_downloading(self) -> bool:
        with self.downloads.lock:
            return any(k.startswith("speech:") and (v or {}).get("status") == "running" for k, v in self.downloads.items.items())

    @staticmethod
    def _saved_run(folder: Path) -> dict:
        try:
            saved = json.loads((folder / PAGE_RUN).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return saved if isinstance(saved, dict) else {}

    def _leftover(self, folder: Path) -> int | None:
        """A process of this request left by an SMTV that crashed or was killed, and still running."""
        return leftover(self._saved_run(folder), self.runner.runs)

    def _no_leftover(self, folder: Path) -> None:
        if self._leftover(folder):
            raise ApiError(409, "still_running", "Эта заявка ещё работает с прошлого запуска SMTV. Нажмите «Остановить» "
                           "и подождите несколько секунд.")

    def _run(self, name: str, folder: Path, args: list[str], by: str) -> None:
        pause.clear(folder)                       # a pause asked for before is done with: this run goes on
        folder.mkdir(parents=True, exist_ok=True)
        _write_json(folder / PAGE_RUN, {"tool": name, "args": args, "by": by})     # before the start: a failure leaves no process
        run = self.runner.start(name, folder, args)
        try:                                      # the process id: after a crash of SMTV, a new SMTV does not start it twice
            _write_json(folder / PAGE_RUN, {"tool": name, "args": args, "by": by, "started": run.started, "pid": run.process.pid})
        except OSError as e:
            print(f"queue: {name}/{folder.name}: {PAGE_RUN} not updated: {e}")

    def _enqueue(self, name: str, folder: Path, args: list[str], by: str) -> None:
        queue = self._queue(name)
        running = self.runner.busy(name)
        ahead = queue[-1] if queue else (running.job if running else None)
        folder.mkdir(parents=True, exist_ok=True)
        _write_json(folder / PAGE_RUN, {"tool": name, "args": args, "by": by})
        with Journal(folder, tool=name, subscribers=[]) as j:
            j.emit(QUEUED, by=by, position=len(queue) + 1, **({"after": ahead} if ahead else {}))
        self._job_cache.pop((name, folder.name), None)
        print(f"queued: {name}/{folder.name} (place {len(queue) + 1}, by {by})")

    def _queue(self, name: str) -> list[str]:
        """The jobs of this tool waiting in the queue, the next one first."""
        waiting = []
        for tool, folder in self._job_folders():
            if tool != name:
                continue
            try:
                base = self._job_base(tool, folder.name)
            except (ApiError, OSError):
                continue
            if base["status"] == QUEUED_STATUS:
                waiting.append((base.get("queued_at") or 0, folder.name))
        return [job for _, job in sorted(waiting)]

    def queue_next(self, name: str | None = None) -> None:
        """Starts the next waiting job of a tool (of every tool: on SMTV's start) when none of its jobs runs. A queued job
        that cannot start gets an error event and leaves the queue; a start the system refuses stops this pass (the
        next look tries again a little later), so one cause does not fail every waiting job at once."""
        changed = False
        for tool in [name] if name else list(self.tools):
            try:
                changed = bool(self._queue_next(tool)) or changed
            except Exception as e:  # noqa: BLE001 — never lost: the window's next look tries again
                print(f"queue: {tool}: {type(e).__name__}: {e}")
        if changed:          # only then: a poke makes the window look again, and the look calls this again
            self.hub.poke()

    def _queue_later(self) -> None:
        """Try the queue again in a little while, with or without an open window (Docker, a minimised window)."""
        with self.queue_lock:
            timer = self._queue_timer
            # the timer's own callback asks again from inside the timer thread: that one must not count as «waiting»
            if timer is not None and timer.is_alive() and timer is not threading.current_thread():
                return
            self._queue_timer = threading.Timer(QUEUE_RETRY_S, lambda: None if self.stopping.is_set() else self.queue_next())
            self._queue_timer.daemon = True
            self._queue_timer.start()

    def _queue_next(self, tool: str) -> bool:
        """True when the queue changed: a job started or left it."""
        with self.queue_lock:
            if self._held() or self.runner.busy(tool) or tool not in self.tools:
                return False
            if time.monotonic() < self._queue_pause_until:
                self._queue_later()
                return False
            changed = False
            for job in self._queue(tool):
                folder = self.tools[tool].page.jobs() / job
                try:
                    saved = json.loads((folder / PAGE_RUN).read_text(encoding="utf-8"))
                    args = saved["args"]
                    if not isinstance(args, list):
                        raise ValueError("no arguments saved")
                except (OSError, ValueError, KeyError, TypeError) as e:
                    self._queue_failed(tool, job, folder, f"the job could not start from the queue: its arguments are lost ({type(e).__name__}: {e})")
                    changed = True
                    continue
                pid = leftover(saved, self.runner.runs)
                if pid:
                    # started by an SMTV that crashed or was killed: it still runs, not again (told once per process)
                    if self._said_leftover.get((tool, job)) != pid:
                        self._said_leftover[(tool, job)] = pid
                        print(f"queue: {tool}/{job}: still runs as process {pid} from before; not started again")
                    self._queue_later()
                    continue
                try:
                    self._run(tool, folder, [str(a) for a in args], str(saved.get("by") or "page"))
                except Busy:
                    return changed
                except Exception as e:  # noqa: BLE001 — the system refused the start: told, and tried again later
                    self._queue_pause_until = time.monotonic() + QUEUE_RETRY_S
                    self._queue_failed(tool, job, folder, f"the job could not start: {type(e).__name__}: {e}")
                    self._queue_later()
                    return True
                print(f"from the queue: {tool}/{job}")
                return True
            return changed

    def _queue_failed(self, tool: str, job: str, folder: Path, message: str) -> None:
        message = message[:500]
        print(f"queue: {tool}/{job}: {message}")
        try:
            with Journal(folder, tool=tool, subscribers=[]) as j:
                j.emit(ERROR, stage="queue", message=message)
        except OSError as e:
            print(f"queue: {tool}/{job}: the journal cannot be written either: {e}")
        self._job_cache.pop((tool, job), None)

    def _queue_watch(self, jobs: list[dict]) -> None:
        """The window's look (every second while it listens): a queue left without a running job — a start that was
        missed or refused, an update that was called off — goes on."""
        idle = {j["tool"] for j in jobs if j["status"] == QUEUED_STATUS} - {t for t in self.tools if self.runner.busy(t)}
        for tool in idle:
            self.queue_next(tool)

    def hand_over(self, body: dict) -> dict:
        """A job command typed in a terminal while this SMTV runs (`smtv vodcut run …`): it runs here, through the queue,
        and shows in the window like any request. Its folder is a job folder of the tool, nothing else."""
        name, job, args = body.get("tool"), body.get("job"), body.get("args")
        if not isinstance(name, str) or not isinstance(job, str):
            raise ApiError(400, "bad_job", "tool and job: strings")
        page = self._page_tool(name).page
        if not JOB_ID.match(job) or ".." in job:
            raise ApiError(400, "bad_job", "job: a job folder name")
        if not isinstance(args, list) or not args or len(args) > 40 or not all(isinstance(a, str) and len(a) <= 4096 for a in args):
            raise ApiError(400, "bad_args", "args: the command's arguments, a list of strings")
        return self._launch(name, page.jobs() / job, args, by="terminal")

    def restart(self, name: str, job: str) -> dict:
        folder = self.folder(name, job)
        saved = self._saved_run(folder)
        args = saved.get("args")
        if not isinstance(args, list) or not args:
            raise ApiError(409, "not_from_page", "this job was started from the command line: start it there again")
        self.not_ready(name)                          # «Continue» needs a ready computer as much as «Start»
        return self._launch(name, folder, [str(a) for a in args], by=str(saved.get("by") or "page"))

    def again(self, name: str, job: str) -> dict:
        """«Run again»: a new request with the same source and choices; the old one stays as it is."""
        folder = self.folder(name, job)
        page = self.tools[name].page
        if not page.again:
            raise ApiError(409, "no_again", "this tool cannot start a new request from an old one")
        if self.runner.running(name, job):
            raise ApiError(409, "running", "the request is still running")
        args = self._saved_run(folder).get("args")
        if not isinstance(args, list) or not args:
            raise ApiError(409, "not_from_page", "this job was started from the command line: start it there again")
        self.not_ready(name)
        with self.queue_lock:                         # a double click makes one new request, never a 500
            try:
                spec = page.again(folder, [str(a) for a in args])
            except FileExistsError:
                raise ApiError(409, "again_twice", "Новая заявка уже создаётся") from None
            return self._launch(name, spec.folder, spec.args)

    def pause(self, name: str, job: str) -> dict:
        """Asks the job to stop at its next safe point (between two steps or two clips), so nothing done is lost.
        Only for a tool whose jobs look for it (`Page.pause`); stopping at once is `cancel`."""
        folder = self.folder(name, job)
        if not self.tools[name].page.pause:
            raise ApiError(409, "no_pause", "this tool's jobs can only be stopped at once")
        if not self.runner.running(name, job):
            raise ApiError(409, "not_running", "the job is not running")
        pause.ask(folder)
        return self.job(name, job)

    def cancel(self, name: str, job: str) -> dict:
        """Stops the running job at once; a waiting one leaves the queue (a `cancelled` event, stage queue)."""
        folder = self.folder(name, job)
        if self.runner.cancel(name, job):
            return self.job(name, job)
        pid = self._leftover(folder)
        if pid:                                       # left running by an SMTV that crashed: stopped with what it runs
            stop_leftover(pid)
            with Journal(folder, tool=name, subscribers=[]) as j:
                j.emit(CANCELLED, by="user")
            self._job_cache.pop((name, job), None)
            return self.job(name, job)
        with self.queue_lock:
            if self.runner.running(name, job):              # the queue started it a moment ago
                self.runner.cancel(name, job)
            elif self._job_base(name, job)["status"] == QUEUED_STATUS:
                with Journal(folder, tool=name, subscribers=[]) as j:
                    j.emit(CANCELLED, by="user", stage="queue")
                self._job_cache.pop((name, job), None)
                print(f"out of the queue: {name}/{job}")
            else:
                raise ApiError(409, "not_running", "the job is not running")
        return self.job(name, job)

    def delete(self, name: str, job: str, body: dict) -> dict:
        """Removes a request for good: its whole job folder (clips, frames, journal). Only when asked in so many words
        (`{"confirm": "delete"}`, after the page's own question) and never while its process runs."""
        if body.get("confirm") != "delete":
            raise ApiError(400, "not_confirmed", 'send {"confirm": "delete"}')
        folder = self.folder(name, job)
        with self.queue_lock:                         # a waiting request is not started while it is being deleted
            if self.runner.running(name, job):
                raise ApiError(409, "running", "the request is still running: cancel it first")
            self._no_leftover(folder)
            root = self.tools[name].page.jobs().resolve()
            target = folder.resolve()
            if target.parent != root:                 # a job folder sits right inside the tool's jobs folder, nowhere else
                raise ApiError(404, "no_job")
            upload = self._upload_of(folder)
            _remove_job_folder(target)
            self._job_cache.pop((name, job), None)
            if upload is not None:                    # the copy of the video the page uploaded for it (B13)
                try:
                    upload.unlink(missing_ok=True)
                except OSError as e:
                    print(f"deleted: {name}/{job}: its uploaded copy {upload.name} stays: {e}")
        print(f"deleted: {name}/{job}")
        return {"deleted": True}

    def _upload_of(self, folder: Path) -> Path | None:
        """The uploaded copy this request was made from, when no other request uses it."""
        args = self._saved_run(folder).get("args") or []
        root = (paths.data_dir() / "uploads").resolve()
        for a in args:
            if not isinstance(a, str) or not a:
                continue
            try:
                p = Path(a).resolve()
            except (OSError, ValueError):
                continue
            if p.parent == root and p.is_file():
                for _, other in self._job_folders():
                    if other.resolve() != folder.resolve() and a in (self._saved_run(other).get("args") or []):
                        return None
                return p
        return None

    def job(self, name: str, job: str) -> dict:
        base = self._job_base(name, job)
        if base["status"] != QUEUED_STATUS:
            return base
        mine = []
        for tool, folder in self._job_folders():
            if tool == name:
                try:
                    mine.append(self._job_base(tool, folder.name))
                except (ApiError, OSError):
                    continue
        return next((j for j in self._with_queue(mine) if j["id"] == job), base)

    def _with_queue(self, jobs: list[dict]) -> list[dict]:
        """Each waiting job with its place: {"position", "waiting", "after": {"id", "title"}} — the job it waits for."""
        out, queues = [], {}
        for j in jobs:
            if j["status"] == QUEUED_STATUS:
                queues.setdefault(j["tool"], []).append(j)
        places = {}
        for tool, waiting in queues.items():
            waiting.sort(key=lambda j: (j.get("queued_at") or 0, j["id"]))
            running = self.runner.busy(tool)
            ahead = None
            if running:
                try:
                    r = self._job_base(tool, running.job)
                    ahead = {"id": r["id"], "title": r.get("title") or r["id"]}
                except (ApiError, OSError):
                    ahead = {"id": running.job, "title": running.job}
            for i, j in enumerate(waiting):
                places[(tool, j["id"])] = {"position": i + 1, "waiting": len(waiting), "after": ahead}
                ahead = {"id": j["id"], "title": j.get("title") or j["id"]}
        for j in jobs:
            place = places.get((j["tool"], j["id"]))
            out.append({**j, "queue": place} if place else j)
        return out

    def _job_base(self, name: str, job: str) -> dict:
        folder = self.folder(name, job)
        page = self.tools[name].page
        run = self.runner.running(name, job)
        journal = folder / events.FILE_NAME
        # The window's stream looks at every job each second: a job whose journal, process and pause did not change is
        # not read again.
        try:
            st = journal.stat()
            key = (st.st_mtime_ns, st.st_size, id(run) if run else None, run.started if run else None,
                   bool(run) and pause.requested(folder), (folder / PAGE_RUN).exists())
        except OSError:
            key = None
        cached = self._job_cache.get((name, job))
        if key is not None and cached and cached[0] == key:
            return cached[1]
        out = self._job_fresh(name, job, folder, page, run, journal)
        if key is not None:
            self._job_cache[(name, job)] = (key, out)
        return out

    def _job_fresh(self, name, job, folder, page, run, journal) -> dict:
        info = {}
        if page.describe:
            try:
                info = page.describe(folder)
            except Exception as e:  # noqa: BLE001 — a summary is decoration; the job is listed anyway, the cause in the log
                info = {}
                print(f"jobs: {name}/{job}: its summary could not be read: {type(e).__name__}: {e}")
        now, queued_at = job_state(folder, run)
        return {"tool": name, "id": job, "status": now, "queued_at": queued_at, "last": events.last_number(journal),
                "updated": journal.stat().st_mtime if journal.exists() else folder.stat().st_mtime,
                "started": run.started if run else None, "restart": (folder / PAGE_RUN).exists(),
                "pausing": bool(run) and pause.requested(folder), **info}

    def _job_folders(self) -> list[tuple[str, Path]]:
        """Every job folder of every tool with a page. A tool whose folder cannot be read is skipped, never the rest."""
        out = []
        for name, tool in self.tools.items():
            if not tool.page:
                continue
            try:
                root = tool.page.jobs()
                folders = [f for f in root.iterdir()] if root.is_dir() else []
            except Exception as e:  # noqa: BLE001 — one tool's trouble must not empty the list of the others
                sys.stderr.write(f"smtv serve: jobs of {name}: {type(e).__name__}: {e}\n")
                continue
            out += [(name, f) for f in folders if f.is_dir() and JOB_ID.match(f.name) and (f / events.FILE_NAME).exists()]
        return out

    def jobs(self) -> list[dict]:
        """The one list of requests on Home: every tool's jobs, the newest first."""
        out = []
        for name, folder in self._job_folders():
            try:
                out.append(self._job_base(name, folder.name))
            except (ApiError, OSError):
                continue          # removed between the listing and the look
        return sorted(self._with_queue(out), key=lambda j: -j["updated"])

    def file(self, name: str, job: str, rel: str) -> Path:
        folder = self.folder(name, job).resolve()
        target = (folder / rel).resolve()
        if folder not in target.parents or target.suffix.lower() not in SERVED or not target.is_file():
            raise ApiError(404, "no_file")
        return target

    def upload_target(self, filename: str) -> Path:
        """A new file in the uploads folder, taken at once (two uploads with one name never share a file, B12).

        Its name passes the job-name check (A4): «стрим_23_11.mp4» → `strim_23_11.mp4`, «Мой стрим.mp4» →
        `Moy-strim.mp4`; the extension stays, so the request is named after the video, not «mp4»."""
        raw = Path(str(filename).replace("\\", "/")).name
        stem, dot, ext = raw.rpartition(".")
        if not dot or not stem:
            stem, ext = raw, ""
        ext = re.sub(r"[^A-Za-z0-9]", "", ext)[:10].lower()
        suffix = f".{ext}" if ext else ""
        stem = paths.safe_name(stem, fallback=f"video-{time.strftime('%Y%m%d-%H%M%S')}", limit=80)
        folder = paths.data_dir() / "uploads"
        folder.mkdir(parents=True, exist_ok=True)
        i = 1
        while True:
            target = folder / (f"{stem}{suffix}" if i == 1 else f"{stem}-{i}{suffix}")
            try:
                with target.open("xb"):
                    return target
            except FileExistsError:
                i += 1


    # --- updates and plugins (stage 8) -------------------------------------------------------------------

    def update_settings(self, body: dict) -> dict:
        if not isinstance(body.get("check"), bool):
            raise ApiError(400, "bad_setting", "check: true or false")
        with Settings.edit() as settings:
            settings.tools.setdefault("smtv", {})["update_check"] = body["check"]
        self.hub.poke()
        return self.updates.state()

    def pick_video(self, native: bool) -> dict:
        """«Choose a file» in SMTV's own window (decision 16): the system's dialog, and the request reads the video where
        it lies — no copy of a 10 GB recording. The browser and a phone have no such dialog: 409, they upload a copy."""
        picker = self.pick_file if native else None
        if picker is None:
            raise ApiError(409, "no_native", "no file dialog here: upload the file")
        path = picker()
        if not path:
            return {"path": None}
        p = Path(path)
        if not p.is_file():
            raise ApiError(400, "no_file", f"Файл не найден: {p.name}")
        return {"path": str(p), "size": p.stat().st_size, "name": p.name}

    def phone_state(self) -> dict:
        """«Phone», with the names the Docker page also answers on the home network (decision 12: the key goes over
        plain HTTP to them, the page says so)."""
        return {**self.phone.state(), "docker_hosts": sorted(self.docker.extra) if self.docker and self.docker.extra else []}

    def phone_set(self, body: dict) -> dict:
        if not isinstance(body.get("on"), bool):
            raise ApiError(400, "bad_phone", "on: true or false")
        address = body.get("address")
        if address is not None and not isinstance(address, str):
            raise ApiError(400, "bad_address", "address: a string")
        try:
            out = self.phone.enable(address) if body["on"] else self.phone.disable()
        except phone_access.PhoneError as e:
            raise ApiError(409, e.code, e.message) from None
        return {**out, "docker_hosts": self.phone_state()["docker_hosts"]}

    def update_do(self, action: str, tool: str | None, body: dict) -> dict:
        now = body.get("now", False)
        if not isinstance(now, bool):
            raise ApiError(400, "bad_now", "now: true or false")
        try:
            return self.updates.ask(action, tool, now=now)
        except UpdateError as e:
            raise ApiError(409, e.code, e.message) from None


def _int(value) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _remove_job_folder(target: Path, tries: int = 5, wait_s: float = 0.4) -> None:
    """Removes a request's folder, or leaves it whole and says why. On Windows a clip open in a player cannot be deleted:
    the folder is first renamed aside (`.deleting-…`: the list no longer shows it) and removed with a few tries; what is
    left there is swept on the next start (`sweep_deleting`)."""
    aside = target.with_name(f".deleting-{target.name}-{secrets.token_hex(3)}")
    try:
        target.rename(aside)
    except OSError as e:
        raise ApiError(409, "in_use", "Заявку нельзя удалить: её файл открыт в другой программе. Закройте видео и "
                       f"попробуйте ещё раз. ({e.strerror or e})") from None
    for i in range(tries):
        try:
            shutil.rmtree(aside)
            return
        except FileNotFoundError:
            return
        except OSError as e:
            if i == tries - 1:
                print(f"deleted: {target.name}: some files stay until the next start of SMTV: {e}")
                return
            time.sleep(wait_s)


def sweep_deleting(root: Path) -> None:
    """What a delete could not finish (a file was open): removed now, quietly."""
    try:
        for f in root.iterdir():
            if f.name.startswith(".deleting-") and f.is_dir():
                shutil.rmtree(f, ignore_errors=True)
    except OSError:
        pass


def _write_json(path: Path, data: dict) -> None:
    """Whole or not at all: a half-written file would lose a queued job's arguments."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


# --- HTTP ---------------------------------------------------------------------------------------------------

def _redact_body(body: dict | None) -> str | None:
    return str(body.get("key")).strip() or None if isinstance(body, dict) and body.get("key") else None


class Handler(BaseHTTPRequestHandler):
    server_version = "smtv"
    sys_version = ""
    protocol_version = "HTTP/1.1"
    app: App
    port: int
    lan: str | None = None       # the home-network address this handler serves (phone access), None on 127.0.0.1

    # quiet log: method, path without the query, status; never headers or bodies
    def log_message(self, fmt, *args):  # noqa: D401
        return

    def log_request(self, code="-", size="-"):
        path = urllib.parse.urlsplit(self.path).path
        if not path.startswith(("/static/", "/fonts/", "/tools/")) and not str(code).startswith("2"):
            sys.stderr.write(f"smtv serve: {self.command} {path} {code}\n")

    # --- checks -------------------------------------------------------------------------------------------

    def _hosts(self) -> set[str]:
        if self.app.docker:
            return self.app.docker.hosts
        return {f"{self.lan}:{self.port}"} if self.lan else {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}

    def _allowed_host(self) -> bool:
        return (self.headers.get("Host") or "").strip().lower() in self._hosts()

    def _cross_site(self) -> bool:
        """The browser says another site sent this (a page elsewhere, an <img> pointing here)."""
        origin = self.headers.get("Origin")
        if origin and origin.lower() not in {f"http://{h}" for h in self._hosts()}:
            return True
        return (self.headers.get("Sec-Fetch-Site") or "same-origin") not in ("same-origin", "none")

    def _same_origin(self) -> bool:
        return not self._cross_site() and self._header_token()

    def _header_token(self) -> bool:
        return hmac.compare_digest(self.headers.get("X-SMTV-Token") or "", self.app.token)

    def _session_cookie(self) -> str:
        return f"smtv_{self.port}"         # cookies do not tell ports apart: two SMTVs on one computer keep their own

    def _token_ok(self) -> bool:
        """The page this server served asks: its token in the header, or the session cookie the page got with it
        (an EventSource or a <video> cannot send headers)."""
        if self._header_token():
            return True
        cookie = self._cookie(self._session_cookie())
        return cookie is not None and hmac.compare_digest(cookie, self.app.token)

    # --- answers ------------------------------------------------------------------------------------------

    def _headers(self, status: int, ctype: str, length: int | None, extra: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        if length is not None:
            self.send_header("Content-Length", str(length))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", CSP)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()

    def _json(self, data, status: int = 200, extra: dict | None = None) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self._headers(status, "application/json; charset=utf-8", len(body), {"Cache-Control": "no-store", **(extra or {})})
        self.wfile.write(body)

    def _error(self, status: int, code: str, message: str = "") -> None:
        self._json({"error": code, "message": message or code}, status)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length > 1_000_000:
            raise ApiError(413, "too_big")
        if length and not (self.headers.get("Content-Type") or "").startswith("application/json"):
            raise ApiError(415, "json_only", "send JSON")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw or b"{}")
        except ValueError:
            raise ApiError(400, "bad_json") from None
        if not isinstance(body, dict):
            raise ApiError(400, "bad_json")
        return body

    def _static(self, root: Path, rel: str, cache: bool = False) -> None:
        root = root.resolve()
        target = (root / rel).resolve()
        if root not in target.parents or not target.is_file():
            raise ApiError(404, "not_found")
        self._send_file(target, cache=cache)

    def _index(self, query: dict) -> None:
        """The page, with this server's session token in it: only the page itself can send changes. In SMTV's window
        (`?window=mac|win|linux`) the page is marked for it from the first frame, so its header never shifts. On this
        computer the page is given only with the launch key in its address (the window, `smtv serve`, a second start of
        SMTV) or to a page that already has this start's cookie; Docker and a phone have their own keys."""
        if not self.app.docker and not self.lan:
            given = (query.get("launch") or [""])[0].encode("utf-8", "replace")
            cookie = (self._cookie(self._session_cookie()) or "").encode("utf-8", "replace")
            if not (hmac.compare_digest(given, self.app.launch.encode()) or hmac.compare_digest(cookie, self.app.token.encode())):
                return self._refused(refused_page("launch", self._browser_lang()))
        shell = (query.get("window") or [""])[0]
        mark = f' class="shell shell-{shell}"' if shell in SHELLS else ""
        html = (WEB / "index.html").read_text(encoding="utf-8").replace("{{SMTV_TOKEN}}", self.app.token)
        html = html.replace("{{SMTV_LANGUAGES}}", ",".join(i18n.languages()))   # the page loads web/i18n/<language>.json
        html = html.replace('<html lang="en">', f'<html lang="en"{mark}>', 1)
        if self.app.docker:    # Chrome and Edge offer «Install SMTV»: its own window, icon, notifications, badge
            html = html.replace("</title>", '</title>\n<link rel="manifest" href="/manifest.webmanifest">', 1)
        html = html.encode("utf-8")
        extra = {"Cache-Control": "no-store"}
        if not self.app.docker and not self.lan:   # Docker and a phone have their own keys as cookies
            extra["Set-Cookie"] = f"{self._session_cookie()}={self.app.token}; Path=/; HttpOnly; SameSite=Strict"
        self._headers(200, "text/html; charset=utf-8", len(html), extra)
        if self.command != "HEAD":
            self.wfile.write(html)

    def _send_file(self, path: Path, download: bool = False, cache: bool = False) -> None:
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
            ctype += "; charset=utf-8"
        if path.suffix == ".js":
            ctype = "text/javascript; charset=utf-8"
        size = path.stat().st_size
        start, end, status = 0, size - 1, 200
        rng = self.headers.get("Range")
        m = re.match(r"^bytes=(\d*)-(\d*)$", rng or "")
        if m and size:
            a, b = m.groups()
            if a:
                start, end = int(a), min(int(b) if b else size - 1, size - 1)
            elif b:
                start, end = max(0, size - int(b)), size - 1
            if start > end or start >= size:
                self._headers(416, "text/plain", 0, {"Content-Range": f"bytes */{size}"})
                return
            status = 206
        extra = {"Accept-Ranges": "bytes", "Cache-Control": "max-age=3600" if cache else "no-cache"}
        if status == 206:
            extra["Content-Range"] = f"bytes {start}-{end}/{size}"
        if download:
            extra["Content-Disposition"] = f"attachment; filename=\"{path.name}\""
        self._headers(status, ctype, end - start + 1, extra)
        if self.command == "HEAD":
            return
        with path.open("rb") as f:
            f.seek(start)
            left = end - start + 1
            while left > 0:
                chunk = f.read(min(1 << 20, left))
                if not chunk:
                    break
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                left -= len(chunk)

    # --- dispatch -----------------------------------------------------------------------------------------

    def do_HEAD(self):
        self._dispatch("GET")

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")

    def _phone_gate(self, method: str, path: str, query: dict) -> bool:
        """On the home-network address: the key from the QR code becomes a cookie (and leaves the address bar); without
        the key nothing answers; the model key and changes to the program are refused. True: answered here."""
        phone = self.app.phone
        key = (query.get("k") or [None])[0]
        if method == "GET" and path == "/" and key is not None:
            if not phone.admits(self.lan, key):
                self._phone_refused()
                return True
            self._headers(303, "text/plain; charset=utf-8", 0, {"Location": "/", "Cache-Control": "no-store",
                          "Set-Cookie": f"{phone_access.COOKIE}={key}; Path=/; HttpOnly; SameSite=Strict; Max-Age=31536000"})
            return True
        cookie = self._cookie(phone_access.COOKIE)
        if not phone.admits(self.lan, cookie):
            if method == "GET" and path in ("/", "/index.html"):
                self._phone_refused()
                return True
            raise ApiError(403, "no_phone_key", "scan the QR code in SMTV on the computer again")
        if phone_access.denied(method, path):
            raise ApiError(403, "not_from_phone", "Это можно сделать только на компьютере: откройте SMTV там.")
        return False

    def _cookie(self, name: str) -> str | None:
        jar = http.cookies.SimpleCookie()
        try:
            jar.load(self.headers.get("Cookie") or "")
        except http.cookies.CookieError:
            pass
        return jar[name].value if name in jar else None

    def _docker_gate(self, method: str, path: str, query: dict) -> bool:
        """In Docker every request needs the access key: the link from the log (`/?token=`) swaps it for a cookie. A
        phone opened from the QR code («Phone», on the home-network address) gets its own key and the phone's limits.
        True: answered here."""
        d = self.app.docker
        self.lan = None
        clean = posixpath.normpath(path) if path.startswith("/") else path
        if method == "GET" and clean == path and (path in DOCKER_OPEN or re.fullmatch(r"/static/icons/[A-Za-z0-9_-]+\.png", path)):
            return False
        token = (query.get("token") or [None])[0]
        if method == "GET" and path == "/" and token is not None:
            if not d.admits(token):
                self._refused(refused_page("docker", self._browser_lang()))
                return True
            self._headers(303, "text/plain; charset=utf-8", 0, {"Location": "/", "Cache-Control": "no-store", "Set-Cookie": d.cookie()})
            return True
        if d.admits(self._cookie(container.COOKIE)):
            return False
        host = (self.headers.get("Host") or "").strip().lower()
        if self.app.phone.on and host == d.phone_host():
            self.lan = d.lan
            return self._phone_gate(method, path, query)
        if method == "GET" and path in ("/", "/index.html"):
            self._refused(refused_page("docker", self._browser_lang()))
            return True
        raise ApiError(403, "no_access_key", "open the link with the key from the log: docker compose logs smtv")

    def _browser_lang(self) -> str:
        return i18n.from_accept_language(self.headers.get("Accept-Language"))

    def _refused(self, page: str) -> None:
        html = page.encode("utf-8")
        self.close_connection = True
        self._headers(403, "text/html; charset=utf-8", len(html), {"Cache-Control": "no-store"})
        if self.command != "HEAD":
            self.wfile.write(html)

    def _phone_refused(self) -> None:
        html = refused_page("phone", self._browser_lang()).encode("utf-8")
        self.close_connection = True
        self._headers(403, "text/html; charset=utf-8", len(html), {"Cache-Control": "no-store"})
        if self.command != "HEAD":
            self.wfile.write(html)

    def _dispatch(self, method: str) -> None:
        body = None
        try:
            if not self._allowed_host():
                raise ApiError(403, "bad_host", "open the page at http://127.0.0.1")
            url = urllib.parse.urlsplit(self.path)
            path, query = urllib.parse.unquote(url.path), urllib.parse.parse_qs(url.query)
            if method != "GET" or (path.startswith("/api/") and path != "/api/hello"):
                if self._cross_site():
                    raise ApiError(403, "cross_origin", "changes come only from the page itself")
                if method != "GET" and not self._header_token():
                    raise ApiError(403, STALE_PAGE, STALE_TEXT)
            if self.app.docker:
                if self._docker_gate(method, path, query):
                    return
            elif self.lan:
                if self._phone_gate(method, path, query):
                    return
            elif method == "GET" and path.startswith("/api/") and path != "/api/hello" and not self._token_ok():
                # B15: any program on this computer could read settings, start a live check of the keys, make a report
                raise ApiError(403, STALE_PAGE, STALE_TEXT)
            if method == "PUT" and path == "/api/uploads":
                return self._upload()
            if method == "POST":
                body = self._body()
            self._route(method, path, query, body)
        except ApiError as e:
            if method != "GET" and body is None:   # the body was not read: the connection cannot carry another request
                self.close_connection = True
            self._error(e.status, e.code, keycheck.redact(e.message, _redact_body(body)))
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True
        except Exception as e:  # noqa: BLE001 — an unexpected error is answered, never shown with a key in it
            message = keycheck.redact(f"{type(e).__name__}: {e}", _redact_body(body))
            where = urllib.parse.urlsplit(self.path).path
            sys.stderr.write(f"smtv serve: {method} {where}: {message}\n")
            stack = keycheck.redact("".join(traceback.format_exception(type(e), e, e.__traceback__)), _redact_body(body))
            crash.record(e, where="server", stage=f"{method} {re.sub(r'/api/jobs/[^/]+/[^/]+', '/api/jobs/<tool>/<job>', where)}",
                         message=keycheck.redact(str(e), _redact_body(body)), stack=stack)
            try:
                self._error(500, "internal", message)
            except OSError:
                pass

    def _route(self, method: str, path: str, query: dict, body: dict | None) -> None:
        try:
            self._route_inner(method, path, query, body)
        finally:
            if method != "GET":
                # a change: the check of this computer looks again, the window's stream looks at once
                self.app.doctor_stale(providers_changed=path.startswith(("/api/settings/providers", "/api/account")))
                self.app.hub.poke()

    def _route_inner(self, method: str, path: str, query: dict, body: dict | None) -> None:
        app = self.app
        parts = [p for p in path.split("/") if p]
        if method == "GET":
            if path in ("/", "/index.html"):
                return self._index(query)
            if path == "/favicon.ico":
                return self._static(WEB, "icon.svg", cache=True)
            if self.app.docker and path == "/healthz":
                return self._json({"ok": True})
            if self.app.docker and path == "/manifest.webmanifest":
                body = json.dumps(MANIFEST).encode("utf-8")
                self._headers(200, "application/manifest+json", len(body), {"Cache-Control": "no-cache"})
                return self.wfile.write(body) if self.command != "HEAD" else None
            if path == "/api/hello":
                return self._json({"app": HELLO_APP, "version": __version__, "tools": sorted(app.tools)})
            if parts[:1] == ["static"]:
                return self._static(WEB, "/".join(parts[1:]))
            if parts[:1] == ["fonts"]:
                from smtv_core.render.fonts import FONTS_DIR
                return self._static(Path(FONTS_DIR), "/".join(parts[1:]), cache=True)
            if parts[:1] == ["tools"] and len(parts) >= 3:
                return self._static(app._page_tool(parts[1]).page.folder, "/".join(parts[2:]))
            if path == "/api/state":
                return self._json({**app.state(), "phone": bool(self.lan), "docker": bool(app.docker)})
            if path == "/api/phone":
                return self._json(app.phone_state())
            if path == "/api/doctor":
                return self._json(app.doctor(fresh=query.get("fresh") == ["1"], live=query.get("live") == ["1"]))
            if path == "/api/cache":
                return self._json(app.cache())
            if parts[:2] == ["api", "fixes"] and len(parts) == 3:
                return self._json(app.fix_state(parts[2], _int((query.get("after") or ["0"])[0])))
            if parts[:2] == ["api", "fixes"] and len(parts) == 4 and parts[3] == "events":
                return self._fix_events(parts[2], query)
            if path == "/api/about":
                return self._json(about_mod.info(list(app.tools.values())))
            if path == "/api/settings":
                return self._json(app.settings())
            if path == "/api/account":
                return self._json(app.account(query.get("live") == ["1"]))
            if path == "/api/settings/agents":
                return self._json(app.settings_agents())
            if parts[:3] == ["api", "settings", "providers"] and len(parts) == 5 and parts[4] == "models":
                return self._json(app.provider_models(parts[3], query))
            if parts[:3] == ["api", "settings", "providers"] and len(parts) == 5 and parts[4] == "ollama":
                return self._json(app.ollama_state(parts[3]))
            if path == "/api/settings/speech":
                return self._json(app.speech())
            if path == "/api/jobs":
                return self._json(app.jobs())
            if path == "/api/usage":
                return self._json(app.tokens())
            if path == "/api/activity":
                if query.get("page"):
                    app.page_seen(query["page"][0])
                if (query.get("lang") or [""])[0] in i18n.languages() and app.lang != query["lang"][0]:
                    app.lang = query["lang"][0]
                    print(f"page language: {app.lang}")
                return self._json(app.activity())
            if path == "/api/uninstall":
                return self._json(app.uninstall_plan())
            if path == "/api/window/events":
                return self._window_events(query)
            if path == "/api/updates":
                return self._json(app.updates.state())
            if path == "/api/report":
                return self._json(app.report_preview(query))
            if parts[:2] == ["api", "report"] and len(parts) == 4 and parts[3] == "archive":
                return self._send_file(app.report_file(parts[2]), download=True)
            if parts[:2] == ["api", "tools"] and len(parts) == 4 and parts[3] == "options":
                return self._json(app.options(parts[2]))
            if parts[:2] == ["api", "tools"] and len(parts) == 4 and parts[3] == "agents":
                return self._json(app.agents(parts[2]))
            if parts[:2] == ["api", "jobs"] and len(parts) == 4:
                return self._json(app.job(parts[2], parts[3]))
            if parts[:2] == ["api", "jobs"] and len(parts) == 5 and parts[4] == "events":
                return self._events(parts[2], parts[3], query)
            if parts[:2] == ["api", "jobs"] and len(parts) >= 6 and parts[4] == "files":
                target = app.file(parts[2], parts[3], "/".join(parts[5:]))
                return self._send_file(target, download=query.get("download") == ["1"])
        if method == "POST":
            if path == "/api/settings/providers":
                return self._json(app.provider_add(body), 201)
            if path == "/api/account/login":
                return self._json(app.account_login(body))
            if path == "/api/account/logout":
                return self._json(app.account_logout())
            if path == "/api/account/buy":
                return self._json(app.account_buy(body))
            if path == "/api/account/check":
                return self._json(app.account_check())
            if path == "/api/settings/providers/check":
                return self._json(app.provider_check(None, body))
            if path == "/api/settings/providers/discover":
                return self._json(app.providers_discover())
            if parts[:3] == ["api", "settings", "providers"] and len(parts) == 6 and parts[4] == "ollama":
                return self._json(app.ollama_action(parts[3], parts[5], body))
            if path == "/api/settings/speech/languages":
                return self._json(app.speech_choose(body))
            if parts[:4] == ["api", "settings", "speech", "models"] and len(parts) == 6:
                return self._json(app.speech_action(parts[4], parts[5]))
            if parts[:3] == ["api", "settings", "providers"] and len(parts) == 4:
                return self._json(app.provider_update(parts[3], body))
            if parts[:3] == ["api", "settings", "providers"] and len(parts) == 5:
                action = {"delete": app.provider_delete, "recommend": app.provider_recommend}.get(parts[4])
                if parts[4] == "check":
                    return self._json(app.provider_check(parts[3], body))
                if action:
                    return self._json(action(parts[3]))
            if parts[:3] == ["api", "settings", "agents"] and len(parts) == 5:
                return self._json(app.settings_agent_set(parts[3], parts[4], body))
            if path == "/api/fixes":
                return self._json(app.fix_start(body), 201)
            if parts[:2] == ["api", "fixes"] and len(parts) == 4 and parts[3] == "stop":
                return self._json(app.fix_stop(parts[2]))
            if path == "/api/cache/clear":
                return self._json(app.cache_clear())
            if path == "/api/folder/open":
                return self._json(app.open_home())
            if path == "/api/window/show":
                return self._json(app.window_show())
            if path == "/api/pick-file":
                return self._json(app.pick_video(native=not self.lan and not app.docker))
            if path == "/api/quit":
                return self._json(app.quit_now())
            if path == "/api/queue":
                return self._json(app.hand_over(body), 201)
            if path == "/api/phone":
                return self._json(app.phone_set(body))
            if path == "/api/report":
                return self._json(app.report_save(body))
            if path == "/api/report/reveal":
                return self._json(app.report_reveal(body))
            if path == "/api/crash":
                return self._json(app.window_crash(body))
            if path == "/api/crashes/seen":
                return self._json(app.crashes_seen())
            if path == "/api/updates/check":
                return self._json(app.updates.check())
            if path == "/api/updates/settings":
                return self._json(app.update_settings(body))
            if path == "/api/updates/update":
                return self._json(app.update_do("update", None, body))
            if path == "/api/updates/cancel":
                return self._json(app.updates.cancel())
            if path == "/api/updates/seen":
                return self._json(app.updates.seen())
            if parts[:2] == ["api", "plugins"] and len(parts) == 4 and parts[3] in ("install", "remove"):
                return self._json(app.update_do(parts[3], parts[2], body))
            if path == "/api/uninstall":
                # The browser forgets this site: the service worker and its saved "SMTV is not running" page, local
                # settings. Otherwise that saved page keeps waiting for an SMTV that is gone.
                return self._json(app.uninstall(body), extra={"Clear-Site-Data": CLEAR_SITE_DATA})
            if parts[:2] == ["api", "tools"] and len(parts) == 4:
                if parts[3] == "options":
                    return self._json(app.set_option(parts[2], body))
                if parts[3] == "estimate":
                    return self._json(app.estimate(parts[2], body))
                if parts[3] == "jobs":
                    return self._json(app.start(parts[2], body), 201)
            if parts[:2] == ["api", "jobs"] and len(parts) == 5:
                if parts[4] == "cancel":
                    return self._json(app.cancel(parts[2], parts[3]))
                if parts[4] == "pause":
                    return self._json(app.pause(parts[2], parts[3]))
                if parts[4] == "again":
                    return self._json(app.again(parts[2], parts[3]), 201)
                if parts[4] == "restart":
                    return self._json(app.restart(parts[2], parts[3]), 201)
                if parts[4] == "delete":
                    return self._json(app.delete(parts[2], parts[3], body))
        raise ApiError(404, "not_found")

    def _upload(self) -> None:
        length = int(self.headers.get("Content-Length") or -1)
        name = urllib.parse.unquote(self.headers.get("X-File-Name") or "")
        if length < 0 or not name:
            raise ApiError(400, "bad_upload", "Content-Length and X-File-Name are needed")
        folder = paths.data_dir() / "uploads"
        folder.mkdir(parents=True, exist_ok=True)
        free = shutil.disk_usage(folder).free
        if length + UPLOAD_SPARE > free:          # B13: said at once, before a 10 GB copy fails half-way
            self.close_connection = True
            raise ApiError(507, "no_space", f"Не хватает места на диске: видео {length / 1e9:.1f} ГБ, свободно "
                                            f"{free / 1e9:.1f} ГБ. Освободите место или выберите файл поменьше.")
        target = self.app.upload_target(name)
        part = target.with_name(f".{target.name}.{secrets.token_hex(4)}.part")   # its own, never another upload's (B12)
        left, done = length, False
        try:
            with part.open("xb") as f:
                while left > 0:
                    chunk = self.rfile.read(min(1 << 20, left))
                    if not chunk:
                        raise ApiError(400, "upload_cut", "the upload was cut off")
                    f.write(chunk)
                    left -= len(chunk)
            part.replace(target)
            done = True
        except OSError as e:
            if e.errno == errno.ENOSPC:
                raise ApiError(507, "no_space", "Место на диске закончилось во время загрузки. Освободите место и "
                                                "попробуйте ещё раз.") from None
            raise
        finally:
            part.unlink(missing_ok=True)
            if not done:
                target.unlink(missing_ok=True)    # the name taken for it goes too
        self._json({"path": str(target), "size": length}, 201)

    def _window_events(self, query: dict) -> None:
        """The window's one stream (stage 8, `hub.py`): requests, what runs now, tokens, updates. An open stream also
        counts as an open page."""
        app = self.app
        if (query.get("lang") or [""])[0] in i18n.languages() and app.lang != query["lang"][0]:
            app.lang = query["lang"][0]
            print(f"page language: {app.lang}")
        self.close_connection = True
        self._headers(200, "text/event-stream; charset=utf-8", None,
                      {"Cache-Control": "no-store", "Connection": "close", "X-Accel-Buffering": "no"})
        app.viewer(+1)
        try:
            app.hub.stream(self.wfile.write, self.wfile.flush)
        except (BrokenPipeError, ConnectionResetError, OSError):
            return
        finally:
            app.viewer(-1)

    def _fix_events(self, fid: str, query: dict) -> None:
        """A fix's console as Server-Sent Events: its lines as they come (`id:` the line's number, so a reconnecting
        browser misses none), and its state when it changes; the stream ends with the fix."""
        app = self.app
        app.fix_state(fid)                        # 404 before the stream starts
        after = _int(self.headers.get("Last-Event-ID") or (query.get("after") or ["0"])[0])
        self.close_connection = True
        self._headers(200, "text/event-stream; charset=utf-8", None,
                      {"Cache-Control": "no-store", "Connection": "close", "X-Accel-Buffering": "no"})
        write, sent, beat = self.wfile.write, None, time.monotonic()
        write(b"retry: 1500\n\n")
        app.viewer(+1)
        try:
            while not app.stopping.is_set():
                state = app.fix_state(fid, after)
                for line in state.pop("lines"):
                    write(f"id: {line['n']}\nevent: line\ndata: {json.dumps(line, ensure_ascii=False)}\n\n".encode("utf-8"))
                    after = line["n"]
                if state["status"] != sent:
                    sent = state["status"]
                    write(f"event: status\ndata: {json.dumps(state, ensure_ascii=False)}\n\n".encode("utf-8"))
                if time.monotonic() - beat > HEARTBEAT_S:
                    write(b": ping\n\n")
                    beat = time.monotonic()
                self.wfile.flush()
                if state["status"] != fixes_mod.RUNNING and after >= state["last"]:
                    return
                app.stopping.wait(POLL_S)
        except (BrokenPipeError, ConnectionResetError, OSError):
            return
        finally:
            app.viewer(-1)

    def _events(self, name: str, job: str, query: dict) -> None:
        """The job's journal as Server-Sent Events: `id:` is the event number, so a reconnecting browser asks for the rest
        with Last-Event-ID and misses nothing. A `status` event (no id) says whether the job's process runs."""
        app = self.app
        folder = app.folder(name, job)
        try:
            after = int(self.headers.get("Last-Event-ID") or (query.get("after") or ["0"])[0])
        except ValueError:
            after = 0
        self.close_connection = True
        self._headers(200, "text/event-stream; charset=utf-8", None,
                      {"Cache-Control": "no-store", "Connection": "close", "X-Accel-Buffering": "no"})
        tail = Tail(folder / events.FILE_NAME, max(0, after))
        sent_status, beat = None, time.monotonic()
        write = self.wfile.write
        write(b"retry: 1500\n\n")
        app.viewer(+1)
        try:
            while not app.stopping.is_set():
                fresh = tail.read()
                for e in fresh:
                    write(f"id: {e['n']}\nevent: job\ndata: {json.dumps(e, ensure_ascii=False)}\n\n".encode("utf-8"))
                run = app.runner.running(name, job)
                place = None
                if not run:
                    try:
                        place = app.job(name, job).get("queue")
                    except (ApiError, OSError):
                        place = None
                key = (bool(run), tail.after, json.dumps(place, sort_keys=True))
                if key != sent_status:
                    sent_status = key
                    payload = {"status": status(folder, run), "running": bool(run), "last": tail.after,
                               "started": run.started if run else None, "queue": place}
                    write(f"event: status\ndata: {json.dumps(payload)}\n\n".encode("utf-8"))
                if time.monotonic() - beat > HEARTBEAT_S:
                    write(b": ping\n\n")
                    beat = time.monotonic()
                self.wfile.flush()
                app.stopping.wait(POLL_S)
        except (BrokenPipeError, ConnectionResetError, OSError):
            return
        finally:
            app.viewer(-1)


class Server(ThreadingHTTPServer):
    daemon_threads = True
    # On Windows SO_REUSEADDR lets a second server take a port that is in use: there a taken port must stay an error.
    allow_reuse_address = sys.platform != "win32"

    max_live: int | None = None             # phone access: at most this many connections at once (B28); None: no cap

    def __init__(self, *args, **kwargs):
        self.live: set = set()               # connections being answered now (phone access cuts them when switched off)
        self._live_lock = threading.Lock()
        self.refused = 0                     # connections closed at once because `max_live` were open
        super().__init__(*args, **kwargs)

    def process_request(self, request, client_address):
        """Counted before its thread starts, so a burst of connections cannot slip past the cap."""
        with self._live_lock:
            full = self.max_live is not None and len(self.live) >= self.max_live
            if full:
                self.refused += 1
            else:
                self.live.add(request)
        if full:
            if self.refused in (1, 10, 100) or self.refused % 1000 == 0:
                print(f"phone access: {self.max_live} connections are open; closing new ones ({self.refused} so far)")
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            with self._live_lock:
                self.live.discard(request)
            raise

    def process_request_thread(self, request, client_address):
        with self._live_lock:
            self.live.add(request)
        try:
            super().process_request_thread(request, client_address)
        finally:
            with self._live_lock:
                self.live.discard(request)

    def cut_all(self) -> None:
        with self._live_lock:
            conns = list(self.live)
        for conn in conns:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def handle_error(self, request, client_address):
        error = sys.exc_info()[1]
        if isinstance(error, (ConnectionResetError, BrokenPipeError, TimeoutError)):
            return   # the browser closed a tab or a video stopped loading: nothing to report
        if isinstance(error, Exception):
            crash.record(error, where="server", stage="connection")
        super().handle_error(request, client_address)


def make_server(app: App, port: int = DEFAULT_PORT, host: str = HOST) -> Server:
    """A server on 127.0.0.1 only, on exactly this port (0: any free one, for tests). A taken port raises PortBusy:
    another port would be another site for the browser, without the installed app and its saved pages."""
    try:
        server = Server((host, port), Handler)
    except OSError as e:
        if port == 0:
            raise
        raise PortBusy(port, probe(port) is not None) from e
    handler = type("BoundHandler", (Handler,), {"app": app, "port": server.server_address[1]})
    app.port = server.server_address[1]
    server.RequestHandlerClass = handler
    return server


PHONE_TIMEOUT_S = 30.0
PHONE_MAX_CONNECTIONS = 64


def make_phone_server(app: App, address: str, bind: tuple[str, int] | None = None) -> Server:
    """The second server of phone access: the same page on a private address of the home network, same port.
    `bind` is for tests only: where to listen while the page still answers as `address`."""
    if not phone_access.private(address):
        raise OSError(f"{address} is not a private address")
    server = Server(bind or (address, app.port), Handler)
    # B28: anyone on the home network reaches this server, even without the key. A connection that sends nothing (or
    # stops reading) for PHONE_TIMEOUT_S is closed — the streams write a heartbeat every HEARTBEAT_S, so a live one never
    # waits that long — and no more than PHONE_MAX_CONNECTIONS are answered at once.
    server.RequestHandlerClass = type("PhoneHandler", (Handler,), {"app": app, "port": app.port, "lan": address,
                                                                   "timeout": PHONE_TIMEOUT_S})
    server.max_live = PHONE_MAX_CONNECTIONS
    return server


def refused_page(kind: str, lang: str) -> str:
    """What a phone without the QR code's key (kind «phone»), a browser without Docker's key link («docker») or a
    program on this computer without the launch key («launch») gets, in the browser's language."""
    def t(key: str) -> str:
        return html_mod.escape(i18n.text(key, lang, link="\0")).replace("\0", "<code>http://127.0.0.1:…/?token=…</code>")
    if kind in ("phone", "launch"):
        body = f'<h1 style="font-size:20px">{t(f"refused_{kind}_title")}</h1><p>{t(f"refused_{kind}_body")}</p>'
    else:
        body = (f'<h1 style="font-size:20px">{t("refused_docker_title")}</h1><p>{t("refused_docker_body")}</p>'
                '<pre style="background:#222;padding:10px 12px;border-radius:8px">docker compose logs smtv | grep token=</pre>'
                f'<p>{t("refused_docker_open")}</p>')
    return (f'<!doctype html><html lang="{lang}"><meta charset="utf-8"><meta name="viewport" content="width=device-width, '
            'initial-scale=1"><title>SMTV</title><body style="font:16px/1.5 system-ui,sans-serif;margin:0;padding:32px 20px;'
            f'background:#181818;color:#eee">{body}</body></html>')


def serve(tools: list[Tool], broken: list[Broken], port: int = DEFAULT_PORT, open_browser: bool = True) -> int:
    from . import desktop, instance
    lock = instance.Lock()
    code = desktop.claim(port, lock, opener=webbrowser.open if open_browser else (lambda url: None))
    if code is not None:
        return code
    try:
        return _serve(tools, broken, port, open_browser, lock)
    finally:
        lock.release()


def docker_setup(app: App, port: int) -> None:
    """SMTV in Docker (stage 21): the access key, the published hosts, and «Phone» on the host's home-network address
    without a second server (the page already listens on every address in the container)."""
    app.docker = container.Docker.from_env(port)
    d = app.docker
    app.phone = phone_access.Phone(lambda address: container.NoServer(), port=lambda: d.public_port,
                                   find=lambda: [d.lan] if d.lan else [], saved=phone_access.Saved())


def _stop_on_term(signum, frame):
    raise KeyboardInterrupt


def _serve(tools, broken, port, open_browser, lock) -> int:
    app = App(tools, broken)
    app.instance = lock
    if container.active():
        try:
            docker_setup(app, port)
        except (ValueError, OSError) as e:
            print(f"SMTV in Docker cannot start: {e}")
            return 2
        open_browser = False
        # `docker stop` sends SIGTERM: stop the jobs as Ctrl+C would (they go on from the same step next time)
        signal.signal(signal.SIGTERM, _stop_on_term)
    try:
        server = make_server(app, port, host=ANY_ADDRESS) if app.docker else make_server(app, port)
        lock.update(port=app.port)
    except PortBusy as e:
        print(busy_message(e) if not e.smtv else f"Port {port} is taken by another SMTV with another data folder: "
              f"close it, or run smtv serve --port {port + 1}.")
        return 2
    url = launch_url(server.server_address[1])
    from .desktop import write_session, remove_session
    write_session(server.server_address[1], app.token)    # a terminal job hands itself over with this token
    app.phone.restore()
    app.quit = lambda: threading.Thread(target=server.shutdown, daemon=True).start()
    threading.Thread(target=app.updates.daily, args=(app.stopping,), name="smtv-updates", daemon=True).start()
    if app.docker:
        links = "\n".join(f"  {link}" for link in app.docker.links())
        if app.docker.extra:
            print(f"Warning: SMTV_HOSTS ({', '.join(sorted(app.docker.extra))}) opens the page over plain HTTP: the access key "
                  "travels unencrypted on that network. Use these names only at home, never on public Wi-Fi.")
        print(f"SMTV in Docker {__version__}. Open the page with its key (the browser remembers it):\n{links}\n"
              f"Chrome or Edge then offer «Install SMTV» in the address bar: its own window and icon. "
              f"To cut off every browser: delete {container.key_file()} and restart the container.")
    else:
        # the address with its key only to a person's terminal, never to a log a problem report may carry
        shown = url if sys.stdout.isatty() else page_url(server.server_address[1])
        print(f"smtv page: {shown}\nStop with Ctrl+C. Jobs started from the page stop with it.")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        app.queue_next()                   # requests that waited when SMTV last quit go on
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        print("\nStopping…")
    finally:
        app.stopping.set()
        app.phone.close()
        app.runner.stop_all()
        server.server_close()
        remove_session(app.token)
    return 0


def busy_message(e: PortBusy) -> str:
    if e.smtv:
        return f"SMTV is already running: {page_url(e.port)}"
    return (f"Port {e.port} on 127.0.0.1 is taken by another program, and SMTV needs it. Close that program and start SMTV "
            f"again, or run `smtv serve --port {e.port + 1}` (the installed app and its saved pages stay on port {DEFAULT_PORT}).")
