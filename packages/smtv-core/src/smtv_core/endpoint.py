"""Where our server is: one answer for the account and for links."""
from __future__ import annotations

import os
import urllib.parse

SERVER = "https://streammoment.tv"


class BadServer(ValueError):
    pass


def allowed(url: str) -> bool:
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme == "https" or (parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost"))


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
    if allowed(url):
        return url
    raise BadServer("the StreamMoment address must be https://…, or http:// on this computer")
