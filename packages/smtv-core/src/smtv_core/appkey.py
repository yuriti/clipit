"""The app key: what our server checks instead of a sign-in when a link is downloaded.

Never in the repository. Where it comes from, first found wins:
  1. the environment variable SMTV_APP_KEY (a local run);
  2. `.env` in the current folder, the line SMTV_APP_KEY=… (a local run);
  3. `smtv_core/_appkey.py`, a generated, git-ignored module that a build writes from the GitHub Actions secret
     SMTV_APP_KEY (`python scripts/write_appkey.py`).
No key: links are off, with a clear message; files of one's own still work.
"""
from __future__ import annotations

import os
from pathlib import Path

ENV = "SMTV_APP_KEY"


def _dotenv() -> str:
    try:
        text = (Path.cwd() / ".env").read_text(encoding="utf-8")
    except (OSError, ValueError):
        return ""
    for line in text.splitlines():
        name, sep, value = line.strip().partition("=")
        if sep and name.strip() == ENV:
            return value.strip().strip("\"'")
    return ""


def _built_in() -> str:
    try:
        from . import _appkey      # type: ignore[attr-defined]
    except ImportError:
        return ""
    return str(getattr(_appkey, "KEY", "") or "").strip()


def get() -> str:
    """The key, or an empty string when this copy has none."""
    return os.environ.get(ENV, "").strip() or _dotenv() or _built_in()
