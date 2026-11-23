"""Where StreamMoment tools keep settings and data on this computer.

SMTV_HOME overrides everything (tests, portable installs, a second drive).
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path


def home() -> Path:
    override = os.environ.get("SMTV_HOME", "").strip()
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return base / "smtv"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "smtv"
    base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return base / "smtv"


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
    if sys.platform == "win32" and not os.environ.get("SMTV_HOME", "").strip():
        local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(local) / "smtv" / "secrets.key"
    return home() / "secrets.key"


def data_dir() -> Path:
    """Downloads, transcripts and finished clips. Large: keep it on a drive with room."""
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
