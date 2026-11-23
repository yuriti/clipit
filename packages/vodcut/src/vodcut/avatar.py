"""The channel's picture for the list of requests: a small round avatar, so a person tells channels apart at a glance.

Taken from the channel's public page (its `og:image`), the same page a browser opens: no keys, no private APIs.
Twitch: https://www.twitch.tv/<login>; YouTube: the channel's own page. Kept once per channel in
`<data>/vodcut/.avatars/` and copied into each job folder as `avatar.<ext>`, which the page serves like any job file.
Best effort: no network, an unknown channel or a page without a picture leaves the request with the tool's icon, and
the attempt is not repeated for a day.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

PAGE_LIMIT, IMAGE_LIMIT, TIMEOUT_S, RETRY_S = 3_000_000, 1_000_000, 10, 86_400
AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
IMAGE_HOSTS = {"static-cdn.jtvnw.net", "yt3.ggpht.com", "yt3.googleusercontent.com"}
TYPES = {"image/jpeg": ".jpg", "image/png": ".png"}
NAMES = ("avatar.jpg", "avatar.png")
MISS = "avatar.none"
TWITCH_LOGIN = re.compile(r"^[A-Za-z0-9_]{2,25}$")
YOUTUBE_ID = re.compile(r"^UC[A-Za-z0-9_-]{22}$")
OG_IMAGE = re.compile(r"""<meta[^>]+property=["']og:image["'][^>]+content=["']([^"']+)["']""", re.I)

_running: set[str] = set()
_lock = threading.Lock()


def channel_page(source: dict) -> tuple[str, str] | None:
    """(cache key, public page) of the recording's channel, or None for a file or an unknown channel."""
    platform = str(source.get("platform") or "").lower()
    if platform.startswith("twitch"):
        login = str(source.get("channel_id") or source.get("channel") or "")
        return (f"twitch-{login.lower()}", f"https://www.twitch.tv/{login.lower()}") if TWITCH_LOGIN.match(login) else None
    if platform.startswith("youtube"):
        cid = str(source.get("channel_id") or "")
        if YOUTUBE_ID.match(cid):
            return f"youtube-{cid}", f"https://www.youtube.com/channel/{cid}"
    return None


def image_url(page: str, platform: str) -> str | None:
    """The channel picture named by the page, only from the platform's own image hosts (Twitch's generic logo is no picture)."""
    m = OG_IMAGE.search(page)
    if not m:
        return None
    url = html.unescape(m.group(1))
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in IMAGE_HOSTS:
        return None
    if platform.startswith("twitch") and "profile_image" not in parts.path:
        return None
    return url


def _get(url: str, limit: int) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept-Language": "en"})
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as r:   # noqa: S310 — https only, checked by the callers
        data = r.read(limit + 1)
        if len(data) > limit:
            raise ValueError("too big")
        return data, (r.headers.get_content_type() or "")


def existing(folder: Path) -> str | None:
    return next((n for n in NAMES if (folder / n).is_file()), None)


def fetch(folder: Path, cache: Path) -> str | None:
    """Puts the channel's picture into the job folder; its file name, or None (and a note not to try again for a day)."""
    try:
        source = json.loads((folder / "source.json").read_text(encoding="utf-8"))
        where = channel_page(source)
        if not where:
            return None
        key, page = where
        cache.mkdir(parents=True, exist_ok=True)
        kept = next((cache / f"{key}{ext}" for ext in TYPES.values() if (cache / f"{key}{ext}").is_file()), None)
        if not kept:
            text, _ = _get(page, PAGE_LIMIT)
            url = image_url(text.decode("utf-8", "replace"), source.get("platform") or "")
            if not url:
                raise ValueError("no channel picture on its page")
            data, ctype = _get(url, IMAGE_LIMIT)
            if ctype not in TYPES:
                raise ValueError(f"not a picture: {ctype}")
            kept = cache / f"{key}{TYPES[ctype]}"
            part = kept.with_name(kept.name + f".{os.getpid()}.part")   # a picture half written is never taken for one
            part.write_bytes(data)
            part.replace(kept)
        name = "avatar" + kept.suffix
        part = folder / f"{name}.part"
        shutil.copyfile(kept, part)
        part.replace(folder / name)
        return name
    except Exception as e:  # noqa: BLE001 — a picture is decoration: the request keeps the tool's icon
        try:
            (folder / MISS).write_text(f"{int(time.time())} {type(e).__name__}: {str(e)[:200]}", encoding="utf-8")
        except OSError:
            pass
        return None          # why is kept in avatar.none; nothing is printed: the command line shows the job, not this


def due(folder: Path, now: float | None = None) -> bool:
    """Whether to look for the picture: none yet, and no failed attempt in the last day."""
    try:
        when = float((folder / MISS).read_text(encoding="utf-8").split()[0])
    except (OSError, ValueError, IndexError):
        return True
    return (now or time.time()) - when > RETRY_S


def ensure(folder: Path, cache: Path) -> str | None:
    """The picture's file name if it is there; otherwise starts looking for it in the background (once at a time)."""
    name = existing(folder)
    if name or not due(folder):
        return name
    try:
        if not channel_page(json.loads((folder / "source.json").read_text(encoding="utf-8"))):
            return None       # a file, or no channel known: nothing to look for
    except (OSError, ValueError):
        return None
    key = str(folder)
    with _lock:
        if key in _running:
            return None
        _running.add(key)

    def run():
        try:
            fetch(folder, cache)
        finally:
            with _lock:
                _running.discard(key)
    threading.Thread(target=run, name="vodcut-avatar", daemon=True).start()
    return None
