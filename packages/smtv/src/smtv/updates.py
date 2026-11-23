"""Updates and plugins from the window (stage 8): no terminal for the person.

- A check once a day (and by a button) reads the signed manifest of the update channel (`channel.py`, stage 27): the
  latest version, its list of changes and the files of each kind of install. It can be turned off (Settings → System).
  An update of a uv or pip install installs the wheels named there, downloaded and checked against the manifest's
  SHA-256 sums first; the desktop apps (dmg, exe) get their installer the same way; Docker gets the command.
- An update, an install or a removal of a tool is done by a separate process, the updater (`updater.py`): this server
  writes a plan, starts the updater and quits (on Windows the files of a running program are locked). The updater waits
  for this process to end, runs the installer, starts SMTV again and waits until it answers with the expected version
  and tools; if it does not, it puts back the versions written down before and starts SMTV again.
- While jobs run, an update waits for them to end (or for «update now», which pauses them; they go on with «Continue»).

Safety: only the packages named here (`smtv`, `smtv-core`) and the tools of the built-in CATALOG are ever installed or
removed, by names written in this code; a name from the network or from the page is only looked up in that list. The
index for the dependencies and the rollback is PyPI over https; SMTV_INDEX (a person's own setting, never read from the
network) points to another index for tests and mirrors: https, or http on this computer only. Versions read from the
manifest are used only if they are plain release numbers and the manifest is signed. Commands are argument lists, never
a shell line.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Callable, Sequence

from smtv_core import paths
from smtv_core.settings import Settings

from . import channel
from .channel import VERSION, is_pre, newer  # noqa: F401 — the version numbers live with the channel
from .channel import parse_version as parse
from .tools import CATALOG

PYPI = "https://pypi.org"
CORE = ("smtv", "smtv-core")
DAY_S = 24 * 3600
FIRST_CHECK_S = 20.0           # after a start, so the window opens first
KIND_MARKER = "smtv-install-kind"
APP_KINDS = ("dmg", "exe", "zip")   # the desktop apps: SMTV with its own Python inside, plugins and all
SETTING = "update_check"       # Settings.tools["smtv"]["update_check"]: false turns the daily check off
LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]"}


# --- the index ----------------------------------------------------------------------------------------------------

def index_base() -> str:
    """PyPI, or SMTV_INDEX when this person set it: https, or http on this computer only."""
    raw = os.environ.get("SMTV_INDEX", "").strip().rstrip("/")
    if not raw:
        return PYPI
    u = urllib.parse.urlsplit(raw)
    if u.scheme == "https" and u.hostname or (u.scheme == "http" and (u.hostname or "") in {"127.0.0.1", "localhost", "::1"}):
        return raw
    raise ValueError("SMTV_INDEX: an https address, or http://127.0.0.1:<port>")


def changelog(text: str) -> list[dict]:
    """Entries of the `## Changelog` section of a package description: [{"version", "notes": [...]}], newest first as
    written. Only plain text is kept (the window shows it as text, never as HTML)."""
    out: list[dict] = []
    inside, cur = False, None
    cur_notes: list[str] = []
    for line in (text or "").splitlines():
        s = line.strip()
        if s.startswith("## "):
            inside = s[3:].strip().lower() in ("changelog", "changes", "what's new", "what’s new")
            cur = None
            continue
        if not inside:
            continue
        if s.startswith("### "):
            version = s[4:].strip().split()[0].lstrip("v") if s[4:].strip() else ""
            cur = None
            if parse(version):
                cur_notes = []
                cur = {"version": version, "notes": cur_notes}
                out.append(cur)
        elif cur and s[:2] in ("- ", "* "):
            cur_notes.append(s[2:].strip()[:400])
        elif cur and s and cur_notes:
            cur_notes[-1] = (cur_notes[-1] + " " + s)[:400]
    return out[:50]


# --- what is installed and how -------------------------------------------------------------------------------------

def allowed_packages() -> tuple[str, ...]:
    return (*CORE, *CATALOG)


def version_of(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def installed_tools(tool_names) -> list[str]:
    """The installed tools that SMTV itself may install and remove: only CATALOG names."""
    return sorted(n for n in tool_names if n in CATALOG)


def install_kind() -> str:
    """How this SMTV was installed: "uv" (uv tool install), "pip" (an environment with pip), "dev" (editable, from
    source: updated from the source, never from the window), "docker" (stage 21: a new version is a new image), "dmg" or
    "exe" (the desktop apps: a new version is a new installer), "zip" (the Windows app without installation: a new
    version is a new archive from the release page) or "none" (no way to update it from here)."""
    if os.environ.get("SMTV_DOCKER", "").strip() == "1":
        return "docker"
    try:      # the desktop apps (install/app/build.py) write their kind (dmg, exe, zip) beside their Python
        marked = (Path(sys.prefix) / KIND_MARKER).read_text(encoding="utf-8").strip()
        if marked in APP_KINDS:
            return marked
        print(f"updates: {KIND_MARKER} says {marked[:40]!r}, not one of {APP_KINDS}: ignored", file=sys.stderr)
    except OSError:
        pass
    try:
        direct = metadata.distribution("smtv").read_text("direct_url.json")
        if direct and json.loads(direct).get("dir_info", {}).get("editable"):
            return "dev"
    except (metadata.PackageNotFoundError, ValueError):
        return "dev"
    if os.path.exists(os.path.join(sys.prefix, "uv-receipt.toml")):
        return "uv" if find_uv() else "none"
    try:
        import importlib.util
        if importlib.util.find_spec("pip") is not None:
            return "pip"
    except (ImportError, ValueError):
        pass
    return "none"


def find_uv() -> str | None:
    """uv on PATH, or where its installer puts it (an SMTV started from an icon may have a short PATH)."""
    found = shutil.which("uv")
    if found:
        return found
    home = Path.home()
    names = ("uv.exe",) if sys.platform == "win32" else ("uv",)
    for folder in (home / ".local" / "bin", home / ".cargo" / "bin", Path("/opt/homebrew/bin"), Path("/usr/local/bin")):
        for n in names:
            if (folder / n).is_file():
                return str(folder / n)
    return None


def base_python() -> str:
    """The Python this environment was made from, outside it: the updater runs there, because the installer replaces
    the environment (on Windows its files cannot even be replaced while they run)."""
    cfg = Path(sys.prefix) / "pyvenv.cfg"
    try:
        home = next((line.split("=", 1)[1].strip() for line in cfg.read_text(encoding="utf-8").splitlines()
                     if line.split("=", 1)[0].strip() == "home"), "")
    except OSError:
        home = ""
    names = ("pythonw.exe", "python.exe") if sys.platform == "win32" else (f"python{sys.version_info[0]}.{sys.version_info[1]}", "python3", "python")
    if home:
        for n in names:
            if (Path(home) / n).is_file():
                return str(Path(home) / n)
    return getattr(sys, "_base_executable", None) or sys.executable


def relaunch_command() -> list[str]:
    """How the updater starts SMTV again: through SMTV.app on a Mac when this process runs from it (so SMTV keeps its
    name and icon), else this environment's Python with the same command and options this process got."""
    exe = Path(sys.executable)
    if sys.platform == "darwin":
        for parent in exe.parents:
            if parent.suffix == ".app" and parent.name == "SMTV.app":
                return ["open", str(parent)]
    python = Path(sys.prefix) / ("Scripts" if sys.platform == "win32" else "bin") / ("pythonw.exe" if sys.platform == "win32" else "python")
    if not python.exists():
        python = exe
    return [str(python), "-m", "smtv", *same_options(sys.argv[1:])]


def same_options(argv: list[str]) -> list[str]:
    """The command (app or serve) and the options SMTV was started with that matter for a start again."""
    command = next((a for a in argv if not a.startswith("-")), "app")
    out = [command if command in ("app", "serve") else "app"]
    for i, a in enumerate(argv):
        if a in ("--browser", "--no-browser"):
            out.append(a)
        elif a == "--port" and i + 1 < len(argv) and argv[i + 1].isdigit():
            out += ["--port", argv[i + 1]]
        elif a.startswith("--port=") and a[7:].isdigit():
            out += ["--port", a[7:]]
    return out


# --- the installer's commands ---------------------------------------------------------------------------------------

def _pins(versions: dict[str, str]) -> list[tuple[str, str]]:
    out = []
    for name in allowed_packages():
        v = versions.get(name)
        if v is None:
            continue
        if not parse(v):
            raise ValueError(f"not a plain version for {name}: {v!r}")
        out.append((name, v))
    return out


def _index_args(kind: str, base: str) -> list[str]:
    if kind == "uv":
        return ["--default-index", f"{PYPI}/simple"] if base == PYPI else ["--index", f"{base}/simple"]
    return ["--index-url", f"{PYPI}/simple"] if base == PYPI else ["--index-url", f"{base}/simple", "--extra-index-url", f"{PYPI}/simple"]


# --- what uv was asked to install besides SMTV -------------------------------------------------------------------------

NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,100}$")
EXTRA = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,60}$")
SPECIFIER = re.compile(r"^[<>=!~][<>=!~ 0-9A-Za-z.*,+-]{0,100}$")


def _receipt_requirements(text: str) -> list[dict]:
    """`[tool] requirements = [{ name = …, extras = […], specifier = … }, …]` of uv-receipt.toml."""
    try:
        import tomllib  # Python 3.11+
        data = tomllib.loads(text)
        reqs = (data.get("tool") or {}).get("requirements") or []
        return [r for r in reqs if isinstance(r, dict)]
    except ImportError:
        pass
    except ValueError:
        return []
    m = re.search(r"(?m)^\s*requirements\s*=\s*\[", text)
    if not m:
        return []
    depth, i = 1, m.end()
    while i < len(text) and depth:
        depth += {"[": 1, "]": -1}.get(text[i], 0)
        i += 1
    out = []
    for table in re.findall(r"\{([^{}]*)\}", text[m.end():i]):
        r: dict = {}
        for key, value in re.findall(r'(\w+)\s*=\s*("(?:[^"\\]|\\.)*"|\[[^\]]*\]|true|false)', table):
            if value.startswith("["):
                r[key] = re.findall(r'"((?:[^"\\]|\\.)*)"', value)
            elif value in ("true", "false"):
                r[key] = value == "true"
            else:
                r[key] = value[1:-1]
        out.append(r)
    return out


def carried(prefix: str | None = None) -> tuple[list[str], dict[str, list[str]]]:
    """What a `uv tool install --reinstall` must be told again, or it is dropped: the packages added with `--with`
    (yt-dlp for «download on this computer», pywebview[qt] for the window on Linux, a third-party plugin) and the extras
    of SMTV's own packages (`smtv-core[keyring]`). Returns (the --with specs of others, {own package: extras})."""
    try:
        text = (Path(prefix or sys.prefix) / "uv-receipt.toml").read_text(encoding="utf-8")
    except FileNotFoundError:
        return [], {}
    except OSError as e:     # said in the log: an update after this may drop what was added with --with
        print(f"smtv update: uv-receipt.toml could not be read ({e}); packages added with --with are not carried over")
        return [], {}
    own = set(allowed_packages())
    others, extras_of = [], {}
    for r in _receipt_requirements(text):
        name = str(r.get("name") or "")
        if not NAME.match(name):
            print(f"smtv update: a package in uv-receipt.toml is not understood and is not carried over: {name[:60]!r}")
            continue
        extras = [e for e in (r.get("extras") or []) if isinstance(e, str) and EXTRA.match(e)]
        canon = name.lower().replace("_", "-")
        if canon in own:
            if canon != "smtv" and extras:
                extras_of[canon] = sorted(set(extras))
            continue
        spec = name + (f"[{','.join(extras)}]" if extras else "")
        if r.get("url"):
            spec += f" @ {r['url']}"
        elif r.get("directory") or r.get("path"):
            spec += f" @ {Path(str(r.get('directory') or r.get('path'))).resolve().as_uri()}"
        elif isinstance(r.get("specifier"), str) and SPECIFIER.match(r["specifier"].strip() or "="):
            spec += r["specifier"].strip()
        others.append(spec)
    return others, extras_of


def install_steps(kind: str, tools: list[str], versions: dict[str, str], base: str, drop: Sequence[str] = (),
                  uv: str | None = None, python: str | None = None, carry: Sequence[str] = (),
                  extras_of: dict[str, list[str]] | None = None, files: dict[str, str] | None = None) -> list[list[str]]:
    """The commands that leave exactly smtv with these tools at these versions, and whatever else was added (`carry`).
    `files` ({package: path of its checked wheel}) installs those packages from the files instead of the index."""
    tools = [t for t in sorted(set(tools)) if t in CATALOG]
    pins = dict(_pins(versions))
    if "smtv" not in pins:
        raise ValueError("the version of smtv is needed")
    extras_of, files = extras_of or {}, files or {}

    def spec(n: str, v: str, ex: list[str] | None = None) -> str:
        ex = ex if ex is not None else extras_of.get(n)
        named = f"{n}{'[' + ','.join(ex) + ']' if ex else ''}"
        return f"{named} @ {Path(files[n]).resolve().as_uri()}" if n in files else f"{named}=={v}"

    others = [(n, v) for n, v in pins.items() if n != "smtv" and (n in CORE or n in tools)]
    if kind == "uv":
        cmd = [uv or find_uv() or "uv", "tool", "install", "--reinstall", spec("smtv", pins["smtv"], tools)]
        for n, v in others:
            cmd += ["--with", spec(n, v)]
        for c in carry:
            cmd += ["--with", c]
        return [cmd + _index_args(kind, base)]
    if kind == "pip":
        py = python or sys.executable
        steps = [[py, "-m", "pip", "install", "--upgrade", "--disable-pip-version-check",
                  spec("smtv", pins["smtv"], tools), *[spec(n, v) for n, v in others], *_index_args(kind, base)]]
        gone = sorted(n for n in set(drop) if n in CATALOG and n not in tools)
        if gone:
            steps.append([py, "-m", "pip", "uninstall", "-y", "--disable-pip-version-check", *gone])
        return steps
    raise ValueError(f"this SMTV cannot be updated from its window ({kind})")


@dataclass
class Plan:
    """What the updater does. Written as JSON next to the updater; nothing in it comes from the page or the network
    except version numbers that passed `parse`."""
    action: str                        # update | install | remove
    steps: list[list[str]]
    rollback: list[list[str]]
    relaunch: list[str]
    expect: dict                       # {"version": smtv version, "tools": [names]} after the change
    previous: dict                     # the same before it
    wait_pid: int
    port: int
    home: str
    status: str
    log: str
    timeout_s: float = 180.0
    rollback_offline: list[list[str]] | None = None   # uv: the rollback from uv's cache first (no network needed)

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def make_plan(action: str, kind: str, tools_now: list[str], current: dict[str, str], target: dict[str, str],
              tools_after: list[str], port: int, base: str | None = None, uv: str | None = None, python: str | None = None,
              relaunch: list[str] | None = None, files: dict[str, str] | None = None) -> Plan:
    base = base or index_base()
    if action not in ("update", "install", "remove"):
        raise ValueError(action)
    tools_now, tools_after = installed_tools(tools_now), installed_tools(tools_after)
    added = [t for t in tools_after if t not in tools_now]
    removed = [t for t in tools_now if t not in tools_after]
    carry, extras_of = carried() if kind == "uv" else ([], {})
    steps = install_steps(kind, tools_after, target, base, drop=removed, uv=uv, python=python, carry=carry, extras_of=extras_of,
                          files=files)
    rollback = install_steps(kind, tools_now, current, base, drop=added, uv=uv, python=python, carry=carry, extras_of=extras_of)
    offline = [step + ["--offline"] for step in rollback] if kind == "uv" else None
    run = paths.home() / "run"
    known = list(CATALOG)    # the updater compares only these: a third-party plugin in /api/hello is not a mismatch
    return Plan(action, steps, rollback, relaunch or relaunch_command(),
                {"version": target["smtv"], "tools": tools_after, "known": known},
                {"version": current["smtv"], "tools": tools_now, "known": known},
                os.getpid(), port, str(paths.home()), str(run / "update-status.json"), str(paths.home() / "logs" / "update.log"),
                rollback_offline=offline)


# --- the state the window shows -------------------------------------------------------------------------------------

def checks_on(settings: Settings | None = None) -> bool:
    return (settings or Settings.load()).tools.get("smtv", {}).get(SETTING, True) is not False


def cache_file() -> Path:
    return paths.home() / "run" / "updates.json"


def status_file() -> Path:
    return paths.home() / "run" / "update-status.json"


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def updater_alive() -> bool:
    """An updater from before is still at work (its status says so and its process lives)."""
    s = _read_json(status_file())
    return s.get("state") in ("waiting", "installing", "starting", "rolling_back") and pid_alive(int(s.get("pid") or 0))


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, pid)  # type: ignore[attr-defined]
        if not h:
            return False
        code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(code))  # type: ignore[attr-defined]
        ctypes.windll.kernel32.CloseHandle(h)  # type: ignore[attr-defined]
        return code.value == 259
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


class Updates:
    """The check, the waiting update, and the start of the updater. `tools` gives the installed tools' names;
    `running` the number of running jobs; `quit` stops this server (the updater starts it again)."""

    def __init__(self, tools: Callable[[], list[str]], running: Callable[[], int], stop_jobs: Callable[[], None],
                 port: Callable[[], int], manifest=None, download=None, open_file=None, spawn=None, clock=time.time,
                 kind: str | None = None):
        self.tools, self.running, self.stop_jobs, self.port = tools, running, stop_jobs, port
        # manifest(floor) -> the verified manifest (channel.load); download(files, folder) -> {name: path}, checked
        self.manifest = manifest or (lambda floor: channel.load(allowed_packages(), floor))
        self.download = download or download_files
        self.open_file = open_file or open_installer
        self.spawn, self.clock = spawn or start_updater, clock
        self.kind = kind or install_kind()
        self.quit: Callable[[], None] | None = None
        self.on_change: Callable[[], None] = lambda: None
        self.lock = threading.Lock()
        self.checking = False
        self.pending: dict | None = None        # {"action", "tool"} waiting for jobs to end
        self.leaving = False                    # the updater is started: this SMTV is quitting
        self.error: str | None = None
        self.cache = _read_json(cache_file())

    # versions
    def current(self) -> dict[str, str]:
        out = {n: version_of(n) for n in CORE}
        for t in installed_tools(self.tools()):
            out[t] = version_of(t)
        return {k: v for k, v in out.items() if v}

    def check(self) -> dict:
        """Ask the index now (the button, or once a day)."""
        with self.lock:
            if self.checking:
                return self.state()
            self.checking = True
        self.on_change()
        try:
            error = None
            try:
                m = self.manifest(self.cache.get(channel.VERSION_KEY))
                packages = {name: {"current": cur, "latest": m["packages"].get(name),
                                   "changes": [e for e in m["changes"] if newer(e["version"], cur)][:20]}
                            for name, cur in self.current().items()}
                self.cache = {"checked": self.clock(), "packages": packages, "manifest": m,
                              channel.VERSION_KEY: m["version"], "error": None}
                self.error = None          # a good check also clears an old error of a failed start
            except (channel.ChannelError, ValueError) as e:
                # no network, no release yet, a bad signature, an old manifest: shown; what was known stays, and the
                # check is tried again within the hour, not in a day
                error = f"{getattr(e, 'code', 'error')}: {e}"[:400]
                print(f"updates: the check failed: {error}")
                self.cache = {**self.cache, "error": error}
            try:
                _write_json(cache_file(), self.cache)
            except OSError as e:
                print(f"updates: could not keep the check: {e}")
        finally:
            with self.lock:
                self.checking = False
            self.on_change()
        return self.state()

    def available(self) -> dict | None:
        """{"version": the smtv version to go to, "versions": {name: version}} when anything is newer, else None."""
        pk = self.cache.get("packages") or {}
        cur = self.current()
        latest = (pk.get("smtv") or {}).get("latest")
        if not pk or not latest or not cur.get("smtv") or not newer(latest, cur["smtv"]):
            return None
        # smtv, smtv-core and the tools come out together under one number: all of them go to it, or none does. A package
        # whose answer is missing or older (the index has not caught up, the check timed out) waits for the next check:
        # a half-new set cannot be installed.
        if any((pk.get(name) or {}).get("latest") != latest for name in cur):
            return None
        target = {name: latest for name in cur}
        return {"version": latest, "versions": target}

    def state(self) -> dict:
        last = _read_json(status_file())
        if last.get("state") not in ("done", "rolled_back", "failed"):
            if not last.get("state"):
                last_out = None
            elif updater_alive():
                last_out = {"state": last.get("state")}
            else:   # the updater was stopped half way (the computer went off): say so, never stay silent
                last_out = {"state": "failed", "action": last.get("action"), "from": last.get("from"), "to": last.get("to"),
                            "finished": last.get("started"), "tools": None, "log": str(paths.home() / "logs" / "update.log"),
                            "seen": last.get("seen", False)}
        else:
            last_out = {k: last.get(k) for k in ("state", "action", "from", "to", "finished", "tools", "log", "seen")}
        pk = self.cache.get("packages") or {}
        cur = self.current()
        return {
            "kind": self.kind, "check": checks_on(), "checked": self.cache.get("checked"), "checking": self.checking,
            "error": self.error or self.cache.get("error"),     # a failed update first: it is the newer news
            "packages": {n: {"current": v, "latest": (pk.get(n) or {}).get("latest"), "changes": (pk.get(n) or {}).get("changes") or []}
                         for n, v in cur.items()},
            "catalog": {n: {"latest": ((self.cache.get("manifest") or {}).get("packages") or {}).get(n)} for n in CATALOG},
            "available": self.available(), "pending": self.pending, "running": self.running(),
            "leaving": self.leaving, "last": last_out,
        }

    def due(self) -> bool:
        return checks_on() and self.clock() - float(self.cache.get("checked") or 0) >= DAY_S

    def daily(self, stopping: threading.Event, first: float = FIRST_CHECK_S, tick: float = 2.0, every: float = 3600.0) -> None:
        """SMTV's own updates thread, independent of any window: a waiting update starts as soon as no job runs (the
        window may be closed while the jobs go on in the background), and the daily check runs a while after the
        start, then whenever a day has passed since the last one (looked at once an hour)."""
        started, looked = time.monotonic(), None
        while not stopping.wait(tick):
            try:
                if self.pending:
                    try:
                        self.go()
                    except UpdateError:
                        pass
                now = time.monotonic()
                if now - started < first or (looked is not None and now - looked < every):
                    continue
                looked = now
                if self.due() and self.kind in channel.KINDS:
                    self.check()
            except Exception as e:  # noqa: BLE001 — a failed check or a broken count of jobs is shown, never ends the thread
                self.error = f"{type(e).__name__}: {e}"[:400]
                print(f"updates: {self.error}", file=sys.stderr)

    # the change itself
    def ask(self, action: str, tool: str | None = None, now: bool = False) -> dict:
        """update | install <tool> | remove <tool>; waits while jobs run, unless now (jobs are paused first)."""
        if action in ("install", "remove") and tool not in CATALOG:   # a name from the page is only looked up
            raise UpdateError("not_in_catalog", "SMTV installs only the plugins of its own list")
        if self.kind not in ("uv", "pip") and not (action == "update" and channel.METHOD.get(self.kind) == "installer"):
            raise UpdateError("cannot_update", "this SMTV was installed from source or without uv or pip: update it there")
        if updater_alive() or self.leaving:
            raise UpdateError("updating", "an update is already running")
        installed = installed_tools(self.tools())
        if action == "update":
            if not self.available():
                raise UpdateError("up_to_date", "nothing newer to install")
            tool = None
        elif action in ("install", "remove"):
            tool = next(n for n in CATALOG if n == tool)
            if action == "install" and tool in installed:
                raise UpdateError("installed", "this plugin is installed already")
            if action == "remove" and tool not in installed:
                raise UpdateError("not_installed", "this plugin is not installed")
        else:
            raise UpdateError("bad_action", "update, install or remove")
        with self.lock:
            self.pending = {"action": action, "tool": tool}
        if now and self.running():
            self.stop_jobs()
        self.on_change()
        return self.go()

    def cancel(self) -> dict:
        with self.lock:
            self.pending = None
        self.on_change()
        return self.state()

    def go(self) -> dict:
        """Start the waiting change if no job runs (called after `ask` and by the window's thread every second)."""
        with self.lock:
            p = self.pending
            if not p or self.leaving or self.running():
                return self.state()
            self.pending, self.leaving = None, True
        try:
            if channel.METHOD.get(self.kind) == "installer":   # the desktop apps: their own installer does the rest
                self.open_file(self.fetch_files(channel.files_for(self.cache.get("manifest") or {}, self.kind))[0])
            else:
                self.spawn(self.plan(p["action"], p["tool"]))
        except Exception as e:  # noqa: BLE001 — shown in the window and the log; this SMTV stays as it is
            self.leaving = False
            self.error = f"{getattr(e, 'code', type(e).__name__)}: {e}"[:400]    # bad_file, disk, …: the window's plain words
            print(f"updates: {p['action']} did not start: {self.error}")
            self.on_change()
            raise UpdateError("not_started", self.error) from None
        self.error = None
        self.on_change()
        if self.quit:
            print(f"quit: {p['action']} by the updater")
            threading.Timer(1.0, self.quit).start()   # the window gets the news first
        return self.state()

    def plan(self, action: str, tool: str | None) -> Plan:
        now = installed_tools(self.tools())
        cur = self.current()
        target = dict(cur)
        after = list(now)
        files = None
        if action == "update":
            target = (self.available() or {}).get("versions") or cur
            if target != cur:    # the new wheels, checked against the signed manifest before anything is installed
                wanted = [n for n in target if n in allowed_packages()]
                files = dict(zip(wanted, self.fetch_files(channel.files_for(self.cache.get("manifest") or {}, self.kind, wanted))))
        elif action == "install" and tool:
            after = now + [tool]
            target[tool] = cur["smtv"]        # tools are released together with smtv, under the same number
        elif action == "remove" and tool:
            after = [t for t in now if t != tool]
            target.pop(tool, None)
        return make_plan(action, self.kind, now, cur, target, after, self.port(), files=files)

    def fetch_files(self, files: list[dict]) -> list[str]:
        """The manifest's files for this update, downloaded and checked, in the same order; a file that does not match
        stops the update (ChannelError("bad_file")) and nothing is installed."""
        version = (self.cache.get("manifest") or {}).get("version") or "unknown"
        return [str(p) for p in self.download(files, update_files_folder(version))]

    def seen(self) -> dict:
        s = _read_json(status_file())
        if s:
            s["seen"] = True
            try:
                _write_json(status_file(), s)
            except OSError:
                pass
        self.on_change()
        return self.state()


def update_files_folder(version: str) -> Path:
    """Where the files of one update are kept until it is done: run/update-files/<version>; older ones are removed."""
    root = paths.home() / "run" / "update-files"
    if root.is_dir():
        for old in root.iterdir():
            if old.name != version:
                shutil.rmtree(old, ignore_errors=True)
    return root / version


def download_files(files: list[dict], folder: Path) -> list[Path]:
    return [channel.download(f, folder) for f in files]


def open_installer(path: str) -> None:
    """Opens a desktop app's installer (dmg, exe) with the system: the person finishes the install there."""
    if sys.platform == "darwin":
        subprocess.run(["open", path], check=True, timeout=60)
    elif sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]  # noqa: S606 — a file we downloaded and checked
    else:
        raise OSError("an installer opens only on macOS and Windows")


class UpdateError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def trim_log(path: Path, limit: int = 2_000_000, keep: int = 500_000) -> None:
    """update.log grows by every update: past `limit` bytes only the last `keep` stay."""
    try:
        if path.stat().st_size <= limit:
            return
        with open(path, "rb") as f:
            f.seek(-keep, os.SEEK_END)
            tail = f.read()
        tail = tail[tail.find(b"\n") + 1:] if b"\n" in tail else tail
        path.write_bytes(tail)
    except OSError:
        pass


def start_updater(plan: Plan, confirm_s: float = 15.0) -> int:
    """Copies the updater next to the plan and starts it with the Python outside this environment, detached: it lives
    on after this server quits."""
    run = Path(plan.home) / "run"
    run.mkdir(parents=True, exist_ok=True)
    script = run / "updater.py"
    shutil.copyfile(Path(__file__).with_name("updater.py"), script)
    plan_file = run / "update-plan.json"
    _write_json(plan_file, plan.as_dict())
    Path(plan.log).parent.mkdir(parents=True, exist_ok=True)
    trim_log(Path(plan.log))
    log = open(plan.log, "ab")  # noqa: SIM115
    kwargs: dict = {"stdin": subprocess.DEVNULL, "stdout": log, "stderr": subprocess.STDOUT, "cwd": str(run), "close_fds": True}
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000   # DETACHED_PROCESS | NEW_PROCESS_GROUP | NO_WINDOW
    else:
        kwargs["start_new_session"] = True
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "__PYVENV"))}
    started = time.time()
    try:
        # -X utf8: the log is written in UTF-8 whatever the Windows code page (a path outside it would crash a print)
        p = subprocess.Popen([base_python(), "-I", "-X", "utf8", str(script), str(plan_file)], env=env, **kwargs)
    finally:
        log.close()
    # This SMTV quits only once the updater has said it is there (its status with its own pid): otherwise the window
    # would close with nothing to bring it back.
    deadline = time.monotonic() + confirm_s
    while time.monotonic() < deadline:
        s = _read_json(Path(plan.status))
        # not by pid: a macOS framework Python may run the script in a child of the process started here
        if s.get("state") and int(s.get("pid") or 0) > 0 and float(s.get("started") or 0) >= started - 1:
            return p.pid
        if p.poll() is not None:
            break
        time.sleep(0.1)
    raise OSError(f"the updater did not start (see {plan.log})")
