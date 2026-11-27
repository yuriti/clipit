"""Where StreamMoment tools keep settings and data on this computer.

SMTV_HOME overrides everything (tests, portable installs, a second drive). The Windows ZIP is portable: whatever it
writes stays in its own folder (`portable_top`): `data` beside ClipIt.exe, the requests and their clips in `Clips`.
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path


APP_FOLDER = "app"   # the Windows desktop app: its own files, below SMTV.exe and what Windows loads before Python


def app_folder(prefix: str | None = None) -> Path:
    """Where the desktop app keeps its own files (ffmpeg, its kind of install, its icon): `app` inside the Windows app's
    folder, whose top holds only SMTV.exe, the files Windows needs to start it and a how-to text (install/app/build.py);
    elsewhere the Python's own prefix."""
    top = Path(prefix or sys.prefix)
    inner = top / APP_FOLDER
    return inner if (inner / "Lib" / "site-packages").is_dir() else top


KIND_MARKER = "smtv-install-kind"    # updates.KIND_MARKER: in the app's own folder, how this copy was installed
PORTABLE_DATA = "data"                # beside ClipIt.exe: settings, keys, models, caches, logs, temporary files
PORTABLE_CLIPS = "Clips"              # beside ClipIt.exe: the requests, each with its clips


def portable_top(prefix: str | None = None, platform: str | None = None) -> Path | None:
    """The Windows ZIP's own folder (ClipIt.exe, app), where everything it writes stays; None for every other install
    (uv, pip, the Mac app: a .app cannot be written into, Linux)."""
    if (platform or sys.platform) != "win32":
        return None
    top = Path(prefix or sys.prefix)
    try:
        kind = (top / APP_FOLDER / KIND_MARKER).read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return top if kind == "zip" else None


def portable_env(data: Path) -> dict[str, str]:
    """What the Windows ZIP sets for itself and every process it starts, so nothing lands outside its data folder:
    temporary files, the model hub's cache, pip's cache, the window's browser profile. `data` is the folder SMTV keeps
    its data in: top\\data, or a person's own SMTV_HOME."""
    tmp = data / "tmp"
    return {"SMTV_HOME": str(data), "TEMP": str(tmp), "TMP": str(tmp), "TMPDIR": str(tmp),
            "HF_HOME": str(data / "cache" / "huggingface"), "PIP_CACHE_DIR": str(data / "cache" / "pip"),
            "WEBVIEW2_USER_DATA_FOLDER": str(data / "webview")}


PORTABLE_SITE = "site-packages"     # in the data folder: what the Windows ZIP installs later (yt-dlp); updates keep it


def apply_portable(prefix: str | None = None, platform: str | None = None) -> Path | None:
    """Sets portable_env for this process (sitecustomize calls it before anything else is imported) and puts the data
    folder's own site-packages on the path. All of it follows SMTV_HOME when a person set one. The system's own
    temporary folder is kept in SMTV_OUTER_TEMP for the one thing that must run outside: removing the folder itself."""
    top = portable_top(prefix, platform)
    if top is None:
        return None
    if "SMTV_OUTER_TEMP" not in os.environ and os.environ.get("TEMP"):
        os.environ["SMTV_OUTER_TEMP"] = os.environ["TEMP"]
    own = os.environ.get("SMTV_HOME", "").strip()
    data = Path(own).expanduser() if own else top / PORTABLE_DATA
    os.environ.update(portable_env(data))
    try:
        Path(os.environ["TEMP"]).mkdir(parents=True, exist_ok=True)
    except OSError:
        pass                               # a folder that cannot be written: the window says so (portable_problem)
    import site
    import tempfile
    tempfile.tempdir = None                # asked again, from the new TEMP
    if (data / PORTABLE_SITE).is_dir():
        site.addsitedir(str(data / PORTABLE_SITE))
    return top


def portable_problem(top: Path) -> str | None:
    """Why the Windows ZIP cannot keep its data in its folder (one put in Program Files, a read-only drive), or None."""
    probe = top / PORTABLE_DATA / ".write-test"
    try:
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        (top / PORTABLE_CLIPS).mkdir(exist_ok=True)
    except OSError as e:
        return f"{type(e).__name__}: {e}"
    return None


def standard_home(platform: str | None = None) -> Path:
    """Where an installed SMTV keeps its data (also where the Windows ZIP looks for 0.1.0's settings)."""
    platform = platform or sys.platform
    if platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return base / "smtv"
    if platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "smtv"
    base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "smtv"


def home() -> Path:
    override = os.environ.get("SMTV_HOME", "").strip()
    if override:
        return Path(override).expanduser()
    top = portable_top()
    if top is not None:
        return top / PORTABLE_DATA
    return standard_home()


def settings_file() -> Path:
    return home() / "settings.json"


def secrets_file() -> Path:
    """Keys, encrypted, when there is no system keychain (`vault.py`)."""
    return home() / "secrets.json"


def secrets_key_file() -> Path:
    """The key that encrypts `secrets_file`: a separate file, readable only by its owner.

    On Windows it lives in %LOCALAPPDATA%\\smtv, not beside the keys in %APPDATA% (Roaming): in a domain Roaming is
    copied to the server, and the key must stay on this computer. With SMTV_HOME (a portable install) it stays in that
    folder, so the folder can be moved with its keys.
    """
    if sys.platform == "win32" and not os.environ.get("SMTV_HOME", "").strip() and portable_top() is None:
        local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(local) / "smtv" / "secrets.key"
    return home() / "secrets.key"


def data_dir() -> Path:
    """Downloads, transcripts and finished clips. Large: keep it on a drive with room. The Windows ZIP keeps its requests
    in Clips beside ClipIt.exe: each request's folder holds its clips (with what it needs to continue or run again)."""
    top = portable_top()
    if top is not None and home() == top / PORTABLE_DATA:
        return top / PORTABLE_CLIPS
    return home() / "data"


def models_dir() -> Path:
    """Speech recognition models, downloaded once."""
    return home() / "models"


_CYRILLIC = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюяіїєґў",
                     "a b v g d e e zh z i y k l m n o p r s t u f kh ts ch sh shch - y - e yu ya i yi ye g u".split()))


def safe_name(text: str, fallback: str = "video", limit: int = 60) -> str:
    """A folder or file name that works everywhere and passes the server's job-name check.

    Latin letters, digits, `.`, `_`, `-`; Russian (and Ukrainian, Belarusian) letters are spelled in Latin so
    «Стрим вчера» stays readable as `Strim-vchera`; it starts with a letter or a digit; empty becomes `fallback`.
    """
    out = []
    for ch in str(text or ""):
        low = ch.lower()
        if low in _CYRILLIC:
            t = _CYRILLIC[low].replace("-", "")
            out.append(t.capitalize() if ch != low and t else t)
        else:
            out.append(ch)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", "".join(out))
    slug = re.sub(r"^[^A-Za-z0-9]+", "", slug)[:limit].rstrip("-._")
    return slug or fallback


def short_hash(text: str, n: int = 8) -> str:
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()[:n]
