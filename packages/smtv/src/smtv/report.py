"""«Report a problem» (stage 17): one archive, `smtv-report-<time>.zip`, that tells us what happened, and a new GitHub
issue with the title and a short summary filled in. The person drags the archive into the issue themselves: nothing is
ever sent by SMTV.

What goes in: versions of SMTV, its core and plugins; the system, processor, graphics card and ffmpeg; `smtv doctor`;
the settings without secrets; the failed request's event journal and the end of its log; the end of SMTV's own logs;
the crash files (`smtv_core.crash`).

Privacy, applied to every file of the archive (`Scrubber`):
- every saved secret (model keys, the phone key, the window's session token, key-like environment variables) is cut out
  by its exact value, and anything that merely looks like a key or a token by its shape (`keycheck.redact` and more);
- the home folder in paths becomes `~`;
- links to streams and names of files and requests are hidden unless the person ticks «include links and file names».
The person sees every file before it is saved (`Report.preview`), and what is saved is exactly what was shown.
"""
from __future__ import annotations

import io
import json
import os
import platform
import re
import secrets as secrets_mod
import shutil
import subprocess
import sys
import time
import urllib.parse
import webbrowser
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from smtv_core import checks as core
from smtv_core import crash, events, paths, proc
from smtv_core.llm import keycheck
from smtv_core.settings import PROVIDERS, Settings, get_secret, secret_names
from smtv_core.tool import Tool

from . import __version__

# The public repository: issues, the README's «Report a problem». The one place to change when it moves.
REPO = "yuriti/clipit"
REPO_URL = f"https://github.com/{REPO}"
ISSUE_TEMPLATE = "bug.yml"
# GitHub answers 414 for longer addresses (about 8 KB); the summary is cut to stay under this.
MAX_URL = 8000
LOG_LINES = 400            # the end of every log
JOURNAL_LINES = 3000       # the end of a request's event journal (a long stream writes tens of thousands of progress lines)
CRASHES = 10               # the newest crash files
TEXT_LIMIT = 2_000_000     # any one file of the archive

JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")
SECRET_NAME = re.compile(r"(key|token|secret|password|passwd|cookie|auth)", re.I)
URL = re.compile(r"https?://[^\s\"'<>)\]}]+")
# Hosts that say nothing about the person: model providers, our own pages, this computer.
PUBLIC_HOSTS = {"api.openai.com", "api.anthropic.com", "generativelanguage.googleapis.com", "openrouter.ai", "api.groq.com",
                "github.com", "pypi.org", "files.pythonhosted.org", "127.0.0.1", "localhost", "developers.openai.com"}
LINK_FILE = re.compile(r"\.(mp4|mkv|mov|webm|flv|ts|m4a|mp3|wav|aac|avi|m3u8)$", re.I)


# --- what is secret ------------------------------------------------------------------------------------------

def secret_values(extra: tuple[str, ...] = (), problems: list[str] | None = None) -> list[str]:
    """Every secret this SMTV knows, by value: saved keys (keychain or file), the window's session token, the phone key,
    and environment variables named like keys. Values shorter than 8 characters are not secrets worth cutting text for.
    A key that could not be read (a locked keychain) is named in `problems`: the report says so."""
    found: set[str] = {e for e in extra if e}
    try:
        names = secret_names()
    except Exception as e:  # noqa: BLE001 — unreadable settings: the names every SMTV used before stage 19, and the shapes
        names = [f"{p}_api_key" for p in PROVIDERS if p != "codex"] + ["phone_key"]
        if problems is not None:
            problems.append(f"the list of keys could not be read ({type(e).__name__}); keys are cut out by their shape too")
    from smtv_core import account
    from . import container
    for name in sorted({*names, account.SECRET_NAME}):
        try:
            value = get_secret(name)
        except Exception as e:  # noqa: BLE001 — a locked keychain: the shapes still catch what looks like a key
            value = None
            if problems is not None:
                problems.append(f"{name} could not be read ({type(e).__name__}); keys are cut out by their shape only")
        if value:
            found.add(value)
            found.update(_inner_values(value))     # the account session is JSON: its tokens are cut one by one
    try:   # the Docker access key (stage 21): a file in the data volume
        found.add(container.key_file().read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        pass
    try:   # a file an older SMTV left in plain text, before it is encrypted
        saved = json.loads(paths.secrets_file().read_text(encoding="utf-8"))
        if isinstance(saved, dict) and "keys" not in saved:
            found.update(v for v in saved.values() if isinstance(v, str))
    except (OSError, ValueError, AttributeError):
        pass
    try:
        session = json.loads((paths.home() / "run" / "session.json").read_text(encoding="utf-8"))
        if isinstance(session.get("token"), str):
            found.add(session["token"])
    except (OSError, ValueError, AttributeError):
        pass
    try:     # the key in the window's address (decision 7): never in a report, even if a log carried it
        found.add((paths.home() / "run" / "launch.key").read_text(encoding="utf-8").strip())
    except OSError:
        pass
    for name, value in os.environ.items():
        if SECRET_NAME.search(name) and value.strip():
            found.add(value.strip())
    return sorted((v for v in found if len(v) >= 8), key=len, reverse=True)


def _inner_values(value: str) -> list[str]:
    """String values inside a secret that is itself JSON (`{"access_token": …, "refresh_token": …}`)."""
    try:
        data = json.loads(value)
    except ValueError:
        return []
    out = []
    stack = [data]
    while stack:
        v = stack.pop()
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, dict):
            stack.extend(v.values())
        elif isinstance(v, list):
            stack.extend(v)
    return out


def _short_path(path: str) -> str:
    """The 8.3 short form of a Windows folder (`SOMEON~1` for `Someone Two`): logs of old programs print it."""
    if sys.platform != "win32":
        return ""
    try:
        import ctypes
        buf = ctypes.create_unicode_buffer(1024)
        n = ctypes.windll.kernel32.GetShortPathNameW(str(path), buf, 1024)
        return buf.value if 0 < n < 1024 else ""
    except Exception:  # noqa: BLE001 — no short names on this drive
        return ""


def _home_variants() -> list[str]:
    out = set()
    for home in {str(Path.home()), os.environ.get("HOME", ""), os.environ.get("USERPROFILE", "")}:
        if len(home) < 4:
            continue
        for h in (home, os.path.realpath(home), _short_path(home)):
            if len(h) < 4:
                continue
            for form in (h, h.replace("\\", "/"), h.replace("/", "\\")):
                out |= {form, json.dumps(form)[1:-1]}
    return sorted((v for v in out if len(v) >= 4), key=len, reverse=True)


@dataclass
class Scrubber:
    """Cuts secrets, the home folder and — unless kept — links and names out of a text."""
    secrets: list[str]
    names: dict[str, str] = field(default_factory=dict)     # name → what it becomes
    hide_links: bool = True
    homes: list[str] = field(default_factory=_home_variants)

    def __call__(self, text: str) -> str:
        for s in self.secrets:
            if s in text:
                text = text.replace(s, "[key]")
            esc = json.dumps(s)[1:-1]
            if esc != s and esc in text:
                text = text.replace(esc, "[key]")
        text = keycheck.redact_all(text)
        if self.hide_links:
            text = URL.sub(_link, text)
            for name in sorted(self.names, key=len, reverse=True):
                if name in text:
                    text = re.sub(r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])", self.names[name], text)
        for home in self.homes:      # Windows paths come in any case: C:\Users\Someone and c:\users\someone
            text = re.sub(re.escape(home), "~", text, flags=re.IGNORECASE)
        return text


    def deep(self, value):
        """The same for every string inside a JSON value (keys too): a JSON text itself is never cut, so it stays JSON."""
        if isinstance(value, str):
            return self(value)
        if isinstance(value, dict):
            return {self(str(k)): self.deep(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self.deep(v) for v in value]
        return value

    def file(self, name: str, text: str) -> str:
        """A file of the archive: JSON and JSON lines value by value, anything else as text."""
        if name.endswith(".json"):
            try:
                return json.dumps(self.deep(json.loads(text)), ensure_ascii=False, indent=2) + "\n"
            except ValueError:
                return self(text)
        if name.endswith(".jsonl"):
            out = []
            for line in text.splitlines():
                try:
                    out.append(json.dumps(self.deep(json.loads(line)), ensure_ascii=False))
                except ValueError:
                    out.append(self(line))
            return "\n".join(out) + "\n"
        return self(text)


def _link(m: re.Match) -> str:
    url = m.group(0)
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    if host in PUBLIC_HOSTS:
        return url
    return "[link]"


# --- what is private ---------------------------------------------------------------------------------------

def _job_roots(tools: list[Tool]) -> list[tuple[str, Path]]:
    out = []
    for t in tools:
        if t.page and t.page.jobs:
            try:
                out.append((t.name, Path(t.page.jobs())))
            except Exception:  # noqa: BLE001 — a tool that cannot say where its jobs are has none to report
                continue
    return out


def job_folders(tools: list[Tool]) -> list[tuple[str, Path]]:
    out = []
    for name, root in _job_roots(tools):
        try:
            out += [(name, p) for p in root.iterdir() if p.is_dir() and JOB_ID.match(p.name)]
        except OSError:
            continue
    return out


def private_names(tools: list[Tool]) -> dict[str, str]:
    """Names that tell which stream or file this was: request folders (`request-1`, …), and from each request its link,
    file, title and channel; files the person uploaded."""
    names: dict[str, str] = {}
    jobs = sorted(job_folders(tools), key=lambda x: x[1].name)
    for n, (_, folder) in enumerate(jobs, 1):
        names.setdefault(folder.name, f"request-{n}")
    for _, folder in jobs:
        for file in ("source.json", "page-run.json"):
            try:
                data = json.loads((folder / file).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            values = list(data.values()) if isinstance(data, dict) else []
            values += [a for a in (data.get("args") or []) if isinstance(a, str)] if isinstance(data, dict) else []
            for value in values:
                if not isinstance(value, str) or len(value) < 3 or value.startswith("--") or value in ("run", "auto", "link", "file", "vodcut"):
                    continue
                if value in names:
                    continue
                if "://" in value:
                    names[value] = "[link]"
                    tail = value.rstrip("/").rsplit("/", 1)[-1]
                    if len(tail) >= 3:
                        names.setdefault(tail, names.get(tail, "[name]"))
                elif "/" in value or "\\" in value:
                    names[value] = "[file]"
                    p = Path(value)
                    for part in (p.name, p.stem):
                        if len(part) >= 3 and part not in names:
                            names[part] = "[file]"
                elif file == "source.json" and not re.fullmatch(r"[\d.]+|[a-z]{2}", value) and value not in (
                        "twitchvod", "youtube", "twitch", "kick"):
                    names[value] = "[name]"
    uploads = paths.data_dir() / "uploads"
    try:
        for p in uploads.iterdir():
            for part in (p.name, p.stem):
                if len(part) >= 3:
                    names.setdefault(part, "[file]")
    except OSError:
        pass
    return names


# --- the computer --------------------------------------------------------------------------------------------

def _run(argv: list[str], timeout: float = 10) -> str:
    try:     # through proc: no black console window under pythonw, and a hung program is stopped with its children
        done = proc.run(argv, timeout, what=os.path.basename(argv[0]))
        return (done.stdout or "").strip() if done.returncode == 0 else ""
    except (OSError, proc.TimedOut):
        return ""


def _cpu() -> str:
    if sys.platform == "darwin":
        name = _run(["sysctl", "-n", "machdep.cpu.brand_string"])
    elif sys.platform.startswith("linux"):
        try:
            name = next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                         if line.startswith("model name")), "")
        except OSError:
            name = ""
    else:
        name = platform.processor()
    return f"{name or platform.machine()}, {os.cpu_count() or '?'} threads"


def _memory_gb() -> str:
    try:
        if sys.platform == "darwin":
            return f"{int(_run(['sysctl', '-n', 'hw.memsize']) or 0) / 2**30:.0f} GB"
        if sys.platform.startswith("linux"):
            kb = next(int(line.split()[1]) for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemTotal"))
            return f"{kb / 2**20:.0f} GB"
        if sys.platform == "win32":
            import ctypes

            class Status(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), ("ullTotalPhys", ctypes.c_ulonglong),
                            ("ullAvailPhys", ctypes.c_ulonglong), ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong), ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
            s = Status()
            s.dwLength = ctypes.sizeof(Status)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))  # type: ignore[attr-defined]
            return f"{s.ullTotalPhys / 2**30:.0f} GB"
    except Exception:  # noqa: BLE001 — memory size is a nicety
        pass
    return "?"


def _gpu() -> str:
    if shutil.which("nvidia-smi"):
        out = _run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"])
        if out:
            return out.splitlines()[0]
    if sys.platform == "darwin":
        out = _run(["system_profiler", "SPDisplaysDataType"], timeout=15)
        chips = [line.split(":", 1)[1].strip() for line in out.splitlines() if "Chipset Model" in line]
        return ", ".join(chips) or "none found"
    if sys.platform == "win32":
        out = _run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                    "(Get-CimInstance Win32_VideoController).Name -join ', '"], timeout=20)
        return out or "none found"
    if shutil.which("lspci"):
        out = _run(["lspci"])
        cards = [line.split(": ", 1)[-1] for line in out.splitlines() if "VGA" in line or "3D controller" in line]
        return ", ".join(cards) or "none found"
    return "none found"


def _system() -> str:
    if sys.platform == "darwin":
        return f"macOS {platform.mac_ver()[0]} ({platform.machine()})"
    if sys.platform == "win32":
        return f"Windows {platform.release()} {platform.version()} ({platform.machine()})"
    try:
        pretty = next((line.split("=", 1)[1].strip('"') for line in Path("/etc/os-release").read_text().splitlines()
                       if line.startswith("PRETTY_NAME=")), "")
    except OSError:
        pretty = ""
    return f"{pretty or 'Linux'} {platform.release()} ({platform.machine()})"


def in_docker() -> bool:
    return Path("/.dockerenv").exists() or os.environ.get("SMTV_IN_DOCKER") == "1" or os.environ.get("SMTV_DOCKER") == "1"


def computer() -> dict:
    found = shutil.which("ffmpeg")
    ffmpeg = _run(["ffmpeg", "-hide_banner", "-version"]).splitlines()[:1] if found else []
    if found and not ffmpeg:
        ffmpeg = [f"found at {found}, but ffmpeg -version failed"]
    return {"system": _system(), "processor": _cpu(), "memory": _memory_gb(), "graphics": _gpu(),
            "ffmpeg": ffmpeg[0].split(" Copyright")[0] if ffmpeg else "not found", "python": f"{platform.python_version()} ({sys.executable})",
            "docker": in_docker()}


# --- the report ----------------------------------------------------------------------------------------------

@dataclass
class Part:
    name: str           # its path inside the archive
    about: str          # one line: what it is
    text: str


@dataclass
class Report:
    id: str
    created: float
    names: bool
    job: dict | None                 # {"tool", "id", "status", "error"} of the request it is about, or None
    summary: dict
    parts: list[Part]
    saved: Path | None = None
    newest_crash: str | None = None   # the newest crash file in it: «seen» goes up to this one, not to a newer one

    @property
    def file_name(self) -> str:
        return "smtv-report-" + time.strftime("%Y%m%d-%H%M%S", time.localtime(self.created)) + ".zip"

    def preview(self) -> dict:
        """What the window shows before saving: every file in full (they are small), and what the issue will say."""
        return {"id": self.id, "names": self.names, "job": self.job, "file": self.file_name, "summary": self.summary,
                "title": issue_title(self), "issue_body": summary_text(self),
                "files": [{"name": p.name, "about": p.about, "size": len(p.text.encode("utf-8")), "text": p.text} for p in self.parts]}

    def zip_bytes(self) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for p in self.parts:
                info = zipfile.ZipInfo(p.name, date_time=time.localtime(self.created)[:6])
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, p.text.encode("utf-8"))
        return buf.getvalue()

    def save(self, folder: Path | None = None) -> Path:
        folder = folder or default_folder()
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / self.file_name
        n = 2
        while target.exists():
            target = folder / self.file_name.replace(".zip", f"-{n}.zip")
            n += 1
        tmp = target.with_suffix(".part")
        tmp.write_bytes(self.zip_bytes())
        os.replace(tmp, target)
        self.saved = target
        return target


def default_folder() -> Path:
    """Downloads, where a browser's «attach» looks first; SMTV's own folder where there is none (a server, Docker)."""
    downloads = Path.home() / "Downloads"
    if downloads.is_dir() and not in_docker():
        return downloads
    return paths.home() / "reports"


def _tail(path: Path, lines: int) -> str | None:
    try:
        size = path.stat().st_size
        with path.open("rb") as f:
            f.seek(max(0, size - 4_000_000))
            data = f.read().decode("utf-8", "replace")
    except OSError:
        return None
    rows = data.splitlines()
    cut = len(rows) > lines
    rows = rows[-lines:]
    return ("[… earlier lines left out]\n" if cut else "") + "\n".join(rows) + "\n"


def _settings_text() -> str:
    try:
        raw = json.loads(paths.settings_file().read_text(encoding="utf-8"))
    except FileNotFoundError:
        return json.dumps({"note": "no settings saved yet"}) + "\n"
    except (OSError, ValueError) as e:
        return json.dumps({"note": f"the settings file could not be read: {type(e).__name__}: {e}"}) + "\n"

    def clean(x):
        if isinstance(x, dict):
            return {k: ("[removed]" if SECRET_NAME.search(str(k)) and isinstance(v, str) and v else clean(v)) for k, v in x.items()}
        if isinstance(x, list):
            return [clean(v) for v in x]
        return x

    data = clean(raw)
    keys = {}
    try:
        providers = Settings.load().providers
    except Exception:  # noqa: BLE001 — the file was read above; a shape Settings refuses is shown as it is
        providers = []
    for p in providers:
        name = p.key_name()
        try:
            saved = bool(name and get_secret(name))
        except Exception as e:  # noqa: BLE001
            saved = f"unreadable ({type(e).__name__})"
        keys[p.id] = {"needed": bool(name), "saved": saved}
    data["keys"] = keys
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _doctor_text(tools, broken) -> str:
    from .tools import doctor_rows
    try:
        rows = doctor_rows(tools, broken)
    except Exception as e:  # noqa: BLE001 — the report goes on without it
        return f"smtv doctor failed: {type(e).__name__}: {e}\n"
    mark = {core.OK: "ok  ", core.WARN: "warn", core.FAIL: "FAIL"}
    width = max((len(r.name) for r in rows), default=4)
    out = []
    for r in rows:
        out.append(f"  {mark.get(r.status, r.status)}  {r.name:<{width}}  {r.detail}")
        if r.status != core.OK and r.fix:
            out.append(f"        {'':<{width}}  fix: {r.fix}")
    return "\n".join(out) + "\n"


def find_job(tools: list[Tool], spec: str | None) -> tuple[str, Path] | None:
    """`<tool>/<id>`, a request's id, or a request folder. None: the newest request that failed (or nothing)."""
    from .jobs import FAILED, status
    folders = job_folders(tools)
    if spec:
        spec = spec.strip()
        if "/" in spec and not Path(spec).exists():
            tool, _, job = spec.partition("/")
            match = [(t, f) for t, f in folders if t == tool and f.name == job]
        else:
            p = Path(spec).expanduser()
            match = [(t, f) for t, f in folders if f.name == spec or (p.exists() and f.resolve() == p.resolve())]
        if not match:
            raise LookupError(f"no request {spec}")
        return match[0]

    def touched(f: Path) -> float:
        try:
            return (f / events.FILE_NAME).stat().st_mtime
        except OSError:
            return 0.0

    for tool, folder in sorted(folders, key=lambda x: touched(x[1]), reverse=True):
        try:
            if status(folder, None) == FAILED:
                return tool, folder
        except Exception:  # noqa: BLE001 — an unreadable journal is not the one to report
            continue
    return None


def _last_error(folder: Path) -> tuple[str, str] | None:
    """(step, message) of the request's last error."""
    try:
        evs = events.read(folder)
    except Exception:  # noqa: BLE001
        return None
    for e in reversed(evs):
        if e.get("type") == "error" and e.get("data", {}).get("stage") != "subscriber":
            return str(e["data"].get("stage") or ""), str(e["data"].get("message") or "")
    return None


def collect(tools: list[Tool], broken: list, *, job: tuple[str, Path] | None = None, names: bool = False,
            now: float | None = None, extra_secrets: tuple[str, ...] = ()) -> Report:
    """Builds the report in memory. `job` is the request it is about (None: none). Nothing is written.
    `extra_secrets`: secrets only the caller knows (the running window's session token)."""
    from .jobs import status as job_status
    now = now or time.time()
    problems: list[str] = []
    scrub = Scrubber(secret_values(extra_secrets, problems), {} if names else private_names(tools), hide_links=not names)
    parts: list[Part] = []

    def add(name: str, about: str, text: str | None) -> None:
        if text is None:
            return
        if len(text) > TEXT_LIMIT:
            text = "[… beginning left out]\n" + text[-TEXT_LIMIT:]
        parts.append(Part(scrub(name), about, scrub.file(name, text)))

    versions = {"smtv": __version__, **crash.versions()}
    versions.update({t.name: t.version for t in tools})
    for b in broken:
        versions[b.name] = f"broken: {b.error}"
    info = computer()
    job_info = None
    if job:
        tool, folder = job
        err = _last_error(folder)
        job_info = {"tool": tool, "id": folder.name, "status": job_status(folder, None),
                    "step": err[0] if err else None, "error": err[1] if err else None}
    all_crashes = crash.files()
    newest = all_crashes[:CRASHES]
    seen = crash.seen_mark()
    unseen = [p for p in all_crashes if p.name > seen]
    if unseen and unseen[-1] not in newest:
        newest.append(unseen[-1])              # the first crash since the last report: often the cause of the rest
    if job:
        newest += [p for p in all_crashes if p not in newest and (crash.read(p) or {}).get("job") == job[1].name]
    unreadable = [p.name for p in newest if crash.read(p) is None]
    last_crash = next((c for c in (crash.read(p) for p in newest) if c), None)
    summary = {"versions": versions, "computer": info, "job": job_info,
               "crash": {k: last_crash.get(k) for k in ("time", "where", "stage", "type", "message")} if last_crash else None,
               "crash_files": len(all_crashes), "created": time.strftime("%Y-%m-%d %H:%M:%S %z", time.localtime(now))}
    if unreadable:
        problems.append(f"crash files that are not JSON: {', '.join(unreadable)}")
    if problems:
        summary["report_problems"] = problems
    add("summary.json", "versions, this computer, what failed", json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    add("doctor.txt", "smtv doctor: what is installed and what is missing", _doctor_text(tools, broken))
    add("settings.json", "settings, without keys", _settings_text())
    if job:
        tool, folder = job
        base = f"request/{tool}-{folder.name}"
        journal = _tail(folder / events.FILE_NAME, JOURNAL_LINES)
        add(f"{base}/events.jsonl", "the request's event journal (steps, model calls, errors)", journal or "(no journal)\n")
        add(f"{base}/run.log", f"the end of the request's log (last {LOG_LINES} lines)", _tail(folder / "run.log", LOG_LINES))
    logs = paths.home() / "logs"
    try:
        for log in sorted(logs.glob("*.log")):
            add(f"logs/{log.name}", f"the end of SMTV's log {log.name} (last {LOG_LINES} lines)", _tail(log, LOG_LINES))
    except OSError:
        pass
    for p in newest:
        try:
            add(f"crashes/{p.name}", "an unexpected error: where, the step, the stack", p.read_text(encoding="utf-8"))
        except OSError:
            continue
    report = Report(secrets_mod.token_urlsafe(9), now, names, None, {}, parts, newest_crash=all_crashes[0].name if all_crashes else None)
    report.job = scrub.deep(job_info) if job_info else None
    report.summary = scrub.deep(summary)
    return report


# --- the issue -----------------------------------------------------------------------------------------------

def issue_title(r: Report) -> str:
    j, c = r.job, r.summary.get("crash")
    if j and j.get("error"):
        what = f"{j['tool']}: {j.get('step') or 'error'} — {j['error']}"
    elif c:
        what = f"{c.get('where')}: {c.get('type')}: {c.get('message') or ''}"
    else:
        what = "a problem"
    what = " ".join(what.split())
    return (what[:110] + "…") if len(what) > 111 else what


def summary_text(r: Report, error_chars: int = 600) -> str:
    v, pc, j, c = r.summary.get("versions", {}), r.summary.get("computer", {}), r.job, r.summary.get("crash")
    lines = ["Versions: " + ", ".join(f"{k} {val}" for k, val in v.items()),
             f"System: {pc.get('system')}" + (" (Docker)" if pc.get("docker") else ""),
             f"Processor: {pc.get('processor')}, memory {pc.get('memory')}",
             f"Graphics: {pc.get('graphics')}",
             f"ffmpeg: {pc.get('ffmpeg')}"]
    if j:
        lines.append(f"Request: {j['tool']}, status {j.get('status')}" + (f", step {j['step']}" if j.get("step") else ""))
        if j.get("error"):
            lines.append("Error: " + j["error"][:error_chars])
    if c:
        lines.append(f"Crash: {c.get('where')}, {c.get('stage') or '-'}: {c.get('type')}: {(c.get('message') or '')[:error_chars]}")
    lines.append(f"Report file: {r.saved.name if r.saved else r.file_name} — attach it below.")
    return "\n".join(lines)


def issue_url(r: Report) -> str:
    """A new issue in the public repository with the bug form, its title and summary filled in, never longer than
    MAX_URL: the error text is cut first, then the summary itself."""
    def build(body: str) -> str:
        query = urllib.parse.urlencode({"template": ISSUE_TEMPLATE, "title": issue_title(r), "summary": body},
                                       quote_via=urllib.parse.quote)
        return f"{REPO_URL}/issues/new?{query}"
    for chars in (600, 300, 120, 0):
        url = build(summary_text(r, chars))
        if len(url) <= MAX_URL:
            return url
    body = summary_text(r, 0)
    while body and len(build(body)) > MAX_URL:
        body = body[: int(len(body) * 0.8)]
    return build(body)


# --- showing it --------------------------------------------------------------------------------------------

def can_open() -> bool:
    """A desktop to show a folder and a browser on (not Docker, not a server without a screen)."""
    if in_docker():
        return False
    if sys.platform.startswith("linux"):
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    return True


def explorer_select(path: Path) -> str:
    """The command line that opens Explorer with the file selected.

    A string, not a list: a list quotes `/select,C:\\…someone two…` whole, and Explorer then opens «Documents» instead.
    """
    return f'explorer /select,"{path}"'


def reveal(path: Path) -> bool:
    """The archive, selected in Finder or Explorer (the folder on Linux)."""
    try:
        if sys.platform == "darwin":
            return subprocess.run(["open", "-R", str(path)], capture_output=True, timeout=15).returncode == 0
        if sys.platform == "win32":
            subprocess.Popen(explorer_select(path))   # explorer's exit code says nothing
            return True
        return subprocess.run(["xdg-open", str(path.parent)], capture_output=True, timeout=15).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def open_issue(url: str) -> bool:
    try:
        return bool(webbrowser.open(url))
    except Exception:  # noqa: BLE001 — no browser: the address is printed and shown anyway
        return False
