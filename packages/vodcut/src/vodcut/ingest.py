"""From a link or a file to a 16 kHz mono WAV plus what is known about the recording.

A file of one's own always works, without an account or the internet. A link goes through the StreamMoment account
(smtv_core.media, stage 23): our server streams the platform's segments, only the audio for the analysis; the video is
fetched later, piece by piece, for the clips that are actually cut. With «Download on this computer» on, yt-dlp on this
computer does it instead (local_download.py, at the person's own risk).
"""
from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qsl, urlencode, urlsplit

from smtv_core import media, proc

from . import local_download, options

PROBE_TIMEOUT_S = 60          # ffmpeg -i reads only the header; a file on a hung network drive must not hold the job
LEFTOVERS = (".part", ".ytdl", ".temp", ".tmp")   # half-written downloads: never taken for the whole file
# Parts of a link that do not change the recording: where to start, the playlist around it, who shared it.
NOT_THE_RECORDING = {"t", "start", "list", "index", "si", "feature", "pp", "ab_channel", "time_continue", "utm_source",
                     "utm_medium", "utm_campaign"}


class IngestError(Exception):
    pass


def is_link(source: str) -> bool:
    return bool(re.match(r"^https?://", source.strip(), re.I))


def source_key(source: str) -> str:
    """What makes a recording itself, so one recording always lands in one folder whatever the link looks like.

    A file: its full path. YouTube: `youtube:<id>` for watch?v=, youtu.be/, /live/, /shorts/, /embed/. Twitch:
    `twitch:<video id>` or `twitch:channel:<name>`. Any other link: its address without where-to-start and playlist parts.
    """
    if not is_link(source):
        return "file:" + str(Path(source).expanduser().resolve())
    parts = urlsplit(source.strip())
    host = (parts.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    path = re.sub(r"/+$", "", parts.path)
    query = dict(parse_qsl(parts.query, keep_blank_values=False))
    if host in ("youtube.com", "music.youtube.com", "youtube-nocookie.com"):
        found = query.get("v") or (re.match(r"^/(?:live|shorts|embed|v)/([^/?#]+)", path) or [None, None])[1]
        if found:
            return f"youtube:{found}"
    if host == "youtu.be" and path.strip("/"):
        return f"youtube:{path.strip('/').split('/')[0]}"
    if host.endswith("twitch.tv"):
        video = re.search(r"/videos?/(\d+)", path)
        if video:
            return f"twitch:{video.group(1)}"
        name = path.strip("/").split("/")[0].lower()
        if name:
            return f"twitch:channel:{name}"
    kept = urlencode(sorted((k, v) for k, v in query.items() if k.lower() not in NOT_THE_RECORDING))
    return f"link:{host}{path}" + (f"?{kept}" if kept else "")


def readable_name(source: str) -> str:
    """The readable part of a job folder's name: the file's name, or the recording's id from the link."""
    if not is_link(source):
        return Path(source).stem
    key = source_key(source)
    if key.startswith(("youtube:", "twitch:")):
        return key.split(":")[-1]
    return urlsplit(source.strip()).path.rstrip("/").split("/")[-1] or (urlsplit(source.strip()).hostname or "")


def _file_facts(path: Path) -> dict:
    try:
        st = path.stat()
    except OSError:
        return {}
    return {"size": st.st_size, "mtime": int(st.st_mtime)}


def _has_ffmpeg() -> bool:
    return bool(shutil.which("ffmpeg"))


def _need_ffmpeg() -> None:
    if not _has_ffmpeg():
        raise IngestError("ffmpeg not found: run `smtv doctor` for how to install it")


def _ffmpeg_to_wav(src: Path, wav: Path) -> None:
    _need_ffmpeg()
    tmp = wav.with_suffix(".part.wav")
    try:
        done = proc.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(src), "-vn", "-ac", "1",
                         "-ar", "16000", "-c:a", "pcm_s16le", str(tmp)],
                        proc.limit(_probe_duration(src) or 0, floor_s=1800, per_s=0.5), what="ffmpeg (audio)")
    except proc.TimedOut as e:
        tmp.unlink(missing_ok=True)
        raise IngestError(f"could not read the audio of {src.name}: {e}") from None
    if done.returncode != 0:
        tmp.unlink(missing_ok=True)
        raise Unreadable(f"ffmpeg could not read the audio of {src.name}: {done.stderr.strip()[-400:]}")
    tmp.replace(wav)


class Unreadable(IngestError):
    """ffmpeg read the file and found it broken (a download cut short): a time limit is not this."""


def _probe_duration(path: Path) -> float | None:
    try:
        return proc.probe(str(path), PROBE_TIMEOUT_S).duration_s
    except proc.TimedOut:
        return None


def file_info(path: Path) -> dict:
    """What is known about a file without reading its sound: name, length, and its size and time to notice a change."""
    return {"kind": "file", "path": str(path), "title": path.stem, "channel": "", "platform": "file",
            "duration_s": _probe_duration(path), **_file_facts(path)}


def from_file(path: Path, job: Path) -> dict:
    path = path.expanduser().resolve()
    if not path.exists():
        raise IngestError(f"file not found: {path}")
    info = file_info(path)
    _ffmpeg_to_wav(path, job / "audio.wav")
    return info


def from_service(url: str, job: Path, on_wait: Callable[[int], None] | None = None,
                 on_progress: Callable[[int, int], None] | None = None) -> tuple[Path, dict]:
    """The audio through StreamMoment: (the audio file, what is known about the recording)."""
    downloaded = job / "source_audio.mp4"
    try:
        with media.Ticket(url, on_wait=on_wait) as ticket:
            ticket.fetch("audio", downloaded, on_progress=on_progress)
            src = ticket.source
    except media.MediaError as e:
        raise IngestError(f"could not download {url}: {e}") from e
    return downloaded, {"kind": "link", "via": "streammoment", "url": src.get("url") or url, "title": src.get("title") or "",
                        "platform": src.get("platform") or "", "channel": src.get("channel") or "", "id": src.get("id") or "",
                        "duration_s": src.get("duration_s"),
                        "channel_id": src.get("channel_id") or "",     # its picture for the list of requests (avatar.py)
                        "language": src.get("language") or "",
                        "date": src.get("date") or ""}                 # the recap's prompt names the stream's day


DOWNLOADED_INFO = "source_audio.json"    # what is known about a link's audio already downloaded, until it is turned into audio.wav


def _write_json(path: Path, data) -> None:
    """Whole or not at all: a full disk or a crash never leaves a half-written file that breaks every later run."""
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def _read_json(path: Path):
    """The file's JSON, or None when it is not there or unreadable (written half by an older SMTV)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _downloaded(job: Path) -> Path | None:
    """The link's audio downloaded by an earlier run, when it is whole (its facts were written after the download)."""
    if _read_json(job / DOWNLOADED_INFO) is None:
        return None
    found = [p for p in sorted(job.glob("source_audio.*")) if p.name != DOWNLOADED_INFO and not p.name.endswith(LEFTOVERS)]
    return found[0] if found else None


def from_link(url: str, job: Path, on_wait: Callable[[int], None] | None = None,
              on_progress: Callable[[int, int], None] | None = None) -> dict:
    _need_ffmpeg()                    # before the download: it may cost hours of the day, and without ffmpeg it is wasted
    downloaded = _downloaded(job)
    if downloaded is not None:
        info = _read_json(job / DOWNLOADED_INFO)       # fetched before, not turned into audio.wav yet: not fetched again
    elif options.local_download():
        try:
            downloaded, info = local_download.audio(url, job)
        except local_download.LocalDownloadError as e:
            raise IngestError(str(e)) from e
    else:
        downloaded, info = from_service(url, job, on_wait, on_progress)
    if downloaded is not None and _read_json(job / DOWNLOADED_INFO) is None:
        _write_json(job / DOWNLOADED_INFO, info)
    try:
        _ffmpeg_to_wav(downloaded, job / "audio.wav")
    except Unreadable:
        # a broken download is not kept as «fetched»: the next «Продолжить» fetches it again instead of the same error
        downloaded.unlink(missing_ok=True)
        (job / DOWNLOADED_INFO).unlink(missing_ok=True)
        raise
    downloaded.unlink(missing_ok=True)
    (job / DOWNLOADED_INFO).unlink(missing_ok=True)
    return info


def _belongs(saved: dict, source: str, key: str) -> bool:
    """Whether the facts saved in a job folder are about this recording. An older SMTV saved no key: its link or path says."""
    theirs = saved.get("source_key") or (source_key(saved["url"]) if saved.get("url") else
                                         source_key(saved["path"]) if saved.get("path") else None)
    return theirs is None or theirs == key


def _changed(saved: dict, source: str) -> bool:
    """A file whose size or time differ from when its audio was read: the recording in the folder is not this file."""
    if is_link(source) or "size" not in saved:
        return False
    now = _file_facts(Path(source).expanduser().resolve())
    return bool(now) and (now.get("size"), now.get("mtime")) != (saved.get("size"), saved.get("mtime"))


def ingest(source: str, job: Path, on_wait: Callable[[int], None] | None = None,
           on_progress: Callable[[int, int], None] | None = None) -> dict:
    """Writes job/audio.wav and job/source.json; a finished step is not repeated. `on_wait(place)`: our queue (0 = its
    turn came), `on_progress(done, total)`: segments of the audio downloaded.

    The folder's saved work is taken only when it is about this recording (`source_key`); a folder made for another
    recording, or a file changed since, is refused instead of giving it someone else's clips.
    """
    job.mkdir(parents=True, exist_ok=True)
    saved_file, key = job / "source.json", source_key(source)
    saved = _read_json(saved_file)
    if saved is not None and not _belongs(saved, source, key):
        raise IngestError(f"В папке {job.name} уже лежит другая запись ({saved.get('title') or saved.get('url') or saved.get('path')}). "
                          "Создайте новую заявку — для каждой записи своя папка.")
    if saved is not None and _changed(saved, source):
        raise IngestError(f"Файл «{Path(source).name}» изменился после прошлого запуска. Удалите эту заявку и создайте новую.")
    if (job / "audio.wav").exists():
        if saved is not None:
            return saved
        # the audio is here but its facts were lost (a full disk, an older SMTV): they are made again, the audio is kept
        info = file_info(Path(source).expanduser().resolve()) if not is_link(source) else \
            {"kind": "link", "url": source, "title": "", "platform": "", "channel": ""}
    else:
        info = from_link(source, job, on_wait, on_progress) if is_link(source) else from_file(Path(source), job)
    info = {**info, "source_key": key}
    _write_json(saved_file, info)
    return info
