"""«Download on this computer»: links through yt-dlp on the person's own computer (stage 23).

Off by default. Links normally go through the StreamMoment account (smtv_core.media), and VodCut does not depend on
yt-dlp. This switch is for a setup without an account, at the person's own risk: platforms change every week, YouTube may
ask to sign in («confirm you're not a bot»), and VodCut never reads the browser or its cookies. yt-dlp is
installed separately into SMTV's environment (`install_hint()`; the package extra `vodcut[local]` names it).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from smtv_core import proc

from . import youtube

FRAGMENTS_AT_ONCE = 16
PIECE_TIMEOUT_FLOOR_S = 600     # a piece of video: at least 10 minutes, then 20 s per second of video
PIECE_TIMEOUT_PER_S = 20
SOCKET_TIMEOUT_S = 60
PIECE_PAD_S = 1.5


STALE_DAYS = 60      # platforms change every week; a yt-dlp older than this often no longer opens links


def install_argv() -> list[str] | None:
    """The command that installs or updates yt-dlp in SMTV's own environment, without administrator rights: uv's pip into
    this Python (a uv tool environment has no pip of its own), else this Python's pip. None: neither is here."""
    import importlib.util
    from smtv.updates import find_uv
    uv = find_uv()
    if uv:
        return [uv, "pip", "install", "--python", sys.executable, "--upgrade", "yt-dlp"]
    if importlib.util.find_spec("pip") is not None:
        return [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
    return None


def install_hint() -> str:
    """The command that puts yt-dlp into SMTV's own environment."""
    from smtv.tools import running_as_uv_tool
    if running_as_uv_tool():
        return "uv tool install --reinstall 'smtv[vodcut]' --with yt-dlp"
    return f"{sys.executable} -m pip install yt-dlp"


def version() -> str | None:
    """yt-dlp's version (a date: 2026.11.02), without importing it."""
    from importlib.metadata import PackageNotFoundError, version as dist_version
    try:
        return dist_version("yt-dlp")
    except PackageNotFoundError:
        return None


def age_days(text: str | None, today=None) -> int | None:
    """How old a yt-dlp version is, in days; None when the version is not a date."""
    import datetime as dt
    try:
        y, m, d = (int(x) for x in (text or "").split(".")[:3])
        made = dt.date(y, m, d)
    except (ValueError, TypeError):
        return None
    return ((today or dt.date.today()) - made).days


class LocalDownloadError(Exception):
    pass


def available() -> bool:
    return importlib.util.find_spec("yt_dlp") is not None


def _yt_dlp():
    try:
        import yt_dlp
    except ImportError as e:
        raise LocalDownloadError(f"«Download on this computer» is on, but yt-dlp is not installed: {install_hint()}") from e
    return yt_dlp


def _date(value) -> str:
    """yt-dlp's YYYYMMDD as YYYY-MM-DD; '' when it is not there."""
    text = str(value or "")
    return f"{text[:4]}-{text[4:6]}-{text[6:8]}" if len(text) == 8 and text.isdigit() else ""


LIVE = ("Эфир ещё идёт — дождитесь его конца. Запись появится на платформе после эфира, тогда и создайте заявку.")
LEFTOVERS = (".part", ".ytdl", ".temp", ".tmp")


def audio(url: str, job: Path) -> tuple[Path, dict]:
    """(the downloaded audio file, what is known about the recording). A stream still on the air is refused: yt-dlp would
    record it until it ends, hours later, and the request would look stuck all that time."""
    yt_dlp = _yt_dlp()
    opts = {"quiet": True, "no_warnings": True, "noprogress": True, "format": "bestaudio/best",
            "outtmpl": str(job / "source_audio.%(ext)s"), "noplaylist": True, "concurrent_fragment_downloads": FRAGMENTS_AT_ONCE,
            "socket_timeout": SOCKET_TIMEOUT_S}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            meta = ydl.extract_info(url, download=False)
            if meta.get("is_live") or meta.get("live_status") in ("is_live", "is_upcoming"):
                raise LocalDownloadError(LIVE)
            meta = ydl.process_ie_result(meta, download=True) or meta
            done = (meta.get("requested_downloads") or [{}])[0].get("filepath")
            downloaded = Path(done) if done else Path(ydl.prepare_filename(meta))
    except LocalDownloadError:
        raise
    except Exception as e:  # noqa: BLE001 — yt-dlp raises many types; the message is what the user needs
        if youtube.BOT_CHECK.search(str(e)):
            raise LocalDownloadError(f"could not download {url}: {youtube.sign_in_hint()}") from e
        raise LocalDownloadError(f"could not download {url}: {e}") from e
    if not downloaded.exists():
        # a half-downloaded .part is never taken for the whole file
        found = [p for p in sorted(job.glob("source_audio.*")) if not p.name.endswith(LEFTOVERS) and p.suffix != ".json"]
        if not found:
            raise LocalDownloadError(f"yt-dlp finished but no audio file appeared for {url}")
        downloaded = found[0]
    return downloaded, {
        "kind": "link", "via": "local", "url": meta.get("webpage_url") or url, "title": meta.get("title") or "",
        "platform": (meta.get("extractor_key") or "").lower(), "channel": meta.get("uploader") or meta.get("channel") or "",
        "id": meta.get("id") or "", "duration_s": meta.get("duration"),
        "channel_id": meta.get("channel_id") or meta.get("uploader_id") or "",   # its picture for the list of requests (avatar.py)
        "language": meta.get("language") or "",       # YouTube says it; Twitch VODs do not
        "date": _date(meta.get("upload_date"))}       # the recap's prompt names the stream's day


def probe(url: str) -> dict:
    yt_dlp = _yt_dlp()
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}) as ydl:
        try:
            meta = ydl.extract_info(url, download=False)
        except Exception as e:  # noqa: BLE001 — yt-dlp's own message says what is wrong with the link
            if youtube.BOT_CHECK.search(str(e)):
                raise ValueError(youtube.sign_in_hint()) from None
            raise ValueError(f"the link does not open: {str(e)[:200]}") from None
    return {"duration_s": float(meta.get("duration") or 0), "title": meta.get("title") or "", "channel": meta.get("uploader") or "",
            "kind": "link", "live": bool(meta.get("is_live"))}


def piece(url: str, start_s: float, end_s: float, dest: Path) -> tuple[Path, float]:
    """Only [start, end] plus a little margin, by yt-dlp in its own process: a download that stalls is stopped after a
    time limit, with the ffmpeg it started."""
    _yt_dlp()
    a, b = max(0.0, start_s - PIECE_PAD_S), end_s + PIECE_PAD_S
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "yt_dlp", "--quiet", "--no-warnings", "--no-progress", "--no-playlist",
           "-f", "bv*[height<=1080]+ba/b[height<=1080]/b", "--merge-output-format", "mp4", "-o", str(dest.with_suffix(".%(ext)s")),
           "--download-sections", f"*{a:.3f}-{b:.3f}", "--force-keyframes-at-cuts",
           "--concurrent-fragments", str(FRAGMENTS_AT_ONCE), "--socket-timeout", str(SOCKET_TIMEOUT_S), url]
    try:
        done = proc.run(cmd, proc.limit(b - a, floor_s=PIECE_TIMEOUT_FLOOR_S, per_s=PIECE_TIMEOUT_PER_S), what=f"yt-dlp ({dest.stem})")
    except proc.TimedOut:
        for left in dest.parent.glob(dest.stem + ".*"):
            left.unlink(missing_ok=True)        # a half-downloaded piece is never taken for a whole one
        raise
    if done.returncode != 0:
        for left in dest.parent.glob(dest.stem + ".*"):
            left.unlink(missing_ok=True)
        raise RuntimeError(f"yt-dlp could not download the piece {dest.stem}: {done.stderr.strip()[-400:]}")
    if not dest.exists():
        found = [p for p in sorted(dest.parent.glob(dest.stem + ".*")) if not p.name.endswith(LEFTOVERS)]
        if not found:
            raise RuntimeError(f"no video piece was downloaded for {dest.stem}")
        found[0].rename(dest)
    return dest, a
