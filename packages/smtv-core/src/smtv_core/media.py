"""Recordings by link, through StreamMoment (stage 23).

SMTV does not download from Twitch or YouTube itself: a link goes to our server, which takes the platform's HLS segments
and passes them straight on — nothing is stored there, nothing is transcoded. It works only with a StreamMoment account
(stage 22); a file of one's own always works without one. Only what the job needs is fetched: first the audio, later
only the pieces of video under the clips and the recap.

    with media.Ticket(url, on_wait=...) as ticket:      # our queue: «waiting, N-th», then ready
        ticket.source                                   # title, channel, length, date of the recording
        ticket.fetch("audio", dest)                     # the whole audio track, segments 16 at once, in order
        ticket.fetch("video", dest, start_s, end_s)     # only the segments over [start, end]; returns where dest starts

The server's API: docs/features/smtv-account.md of the StreamMoment repository («Ссылки через StreamMoment»).
"""
from __future__ import annotations

import http.client
import json
import re
import threading
import ssl
import time
import urllib.error
import urllib.request
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from . import account

FRAGMENTS_AT_ONCE = 16          # the server allows 16 segments of one ticket in flight
SEGMENT_TIMEOUT_S = 60.0
SEGMENT_ATTEMPTS = 5
WAIT_POLL_S = 3.0
QUEUE_WAIT_S = 6 * 3600.0       # our queue: a long wait is still a wait, not a failure
WAIT_NET_TOLERANCE_S = 600.0    # while waiting in it, the network may drop this long in a row before the place is given up (B4)
SIGN_IN = "streammoment_sign_in"        # in the error text: the window shows its own explanation
TWITCH_VOD = re.compile(r"^https?://(www\.|m\.)?twitch\.tv/(\w{1,40}/)?(videos|v)/\d{5,20}/?(\?.*)?$", re.I)
YOUTUBE = re.compile(r"^https?://([a-z0-9-]+\.)?(youtube\.com|youtu\.be)/", re.I)

OWN_DOWNLOAD = "«Download links myself»"     # VodCut's switch, named as the window names it
# Sign-in to a StreamMoment account is not open yet (0.1.0): a link without it says how to go on now, never «sign in».
NO_ACCOUNT = (f"Links through a StreamMoment account are coming soon. For now: choose the recording file, or turn on {OWN_DOWNLOAD} "
              f"in VodCut's settings and install yt-dlp (smtv doctor shows the command) [{SIGN_IN}]")

MESSAGES = {
    "not_signed_in": NO_ACCOUNT,
    "not_open": NO_ACCOUNT,
    "media_unsupported": "Links from this site do not open through StreamMoment yet (Twitch only for now): choose the recording "
                         f"file, or turn on {OWN_DOWNLOAD} in VodCut's settings (at your own risk)",
    "media_link_invalid": "This does not look like a link to a recording (a Twitch VOD looks like twitch.tv/videos/123…)",
    "media_not_found": "Twitch has no such recording: it may have been deleted or the link is mistyped",
    "media_restricted": "Twitch gives this recording only to subscribers or not at all: choose the recording file",
    "media_too_long": "The recording is longer than StreamMoment takes in one request: cut it into parts as files",
    "media_daily_limit": "Today's hours of links through StreamMoment are used up: tomorrow, or choose the recording file now",
    "media_too_many": "Two links of this account are already downloading: wait for one of them",
    "media_segment_gone": "Twitch no longer gives a part of this recording: it may have been deleted",
    "media_live": "The stream is still going: its recording can be processed when it ends",
}


class MediaError(Exception):
    """Something the person can act on; `code` is the server's code or ours."""

    def __init__(self, code: str, message: str = "", retryable: bool = False):
        super().__init__(message or MESSAGES.get(code) or f"StreamMoment refused the link: {code}")
        self.code, self.retryable = code, retryable


def supported(url: str) -> bool:
    """A link StreamMoment downloads today (the server decides; this only saves a round trip in the window)."""
    return bool(TWITCH_VOD.match(url.strip()))


def unsupported_message(url: str) -> str:
    if YOUTUBE.match(url.strip()):
        return ("YouTube links do not open through StreamMoment yet: download the recording and choose the file, or turn on "
                f"{OWN_DOWNLOAD} in VodCut's settings (at your own risk: YouTube may ask to sign in)")
    return MESSAGES["media_unsupported"]


def _error(status: int, answer: dict) -> MediaError:
    code = str((answer or {}).get("error") or f"http_{status}")
    if status == 404 and code in ("Not Found", "http_404"):      # our server without these addresses: links are off there
        return MediaError("not_open")
    retryable = status in (429, 502, 503) and code not in ("media_daily_limit", "media_too_many", "media_segment_gone")
    return MediaError(code, retryable=retryable)


def _json(method: str, path: str, body: dict | None = None) -> dict:
    try:
        status, answer = account.authorized(method, path, body)
    except account.NotSignedIn as e:
        raise MediaError("not_signed_in") from e
    except account.AccountError as e:
        if e.code == "not_open":
            raise MediaError("not_open") from e
        raise MediaError(e.code, f"{e}{(' ' + e.hint) if e.hint else ''}", retryable=e.code in ("unreachable", "server_unavailable")) from e
    if status != 200:
        raise _error(status, answer)
    return answer


def _bytes(path: str, timeout: float = SEGMENT_TIMEOUT_S) -> bytes:
    """One segment through our server; one token refresh on 401."""
    for force in (False, True):
        try:
            token = account.access_token(force=force)
        except account.NotSignedIn as e:
            raise MediaError("not_signed_in") from e
        request = urllib.request.Request(account.server() + path, headers={"Authorization": f"Bearer {token}", "User-Agent": "smtv"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                expected = response.headers.get("Content-Length")
                data = response.read()
            if expected is not None and len(data) != int(expected):
                raise MediaError("segment_short", "a segment came cut short", retryable=True)
            return data
        except urllib.error.HTTPError as e:
            if e.code == 401 and not force:
                continue
            try:
                answer = json.loads(e.read().decode("utf-8") or "{}")
            except ValueError:
                answer = {}
            raise _error(e.code, answer if isinstance(answer, dict) else {}) from e
        except http.client.HTTPException as e:       # IncompleteRead: the segment broke off midway; tried again
            raise MediaError("segment_short", f"a segment came cut short: {type(e).__name__}", retryable=True) from e
        except (urllib.error.URLError, TimeoutError, OSError, ssl.SSLError) as e:
            raise MediaError("unreachable", f"streammoment.tv did not answer: {str(getattr(e, 'reason', e))[:160]}", retryable=True) from e
    raise MediaError("not_signed_in")


def info(url: str) -> dict:
    """What the recording is (title, channel, length, still live) without a place in the queue and without counting
    the day's hours: the window's estimate."""
    if not supported(url):
        raise MediaError("media_unsupported", unsupported_message(url))
    return dict(_json("POST", "/api/smtv/media/info", {"url": url}).get("source") or {})


class Ticket:
    """One link in our server's queue. Waits for its turn on open; opens again by itself if the server forgot it
    (SMTV slept longer than the server keeps an idle ticket)."""

    def __init__(self, url: str, on_wait: Callable[[int], None] | None = None, *, wait_s: float = QUEUE_WAIT_S,
                 sleep: Callable[[float], None] = time.sleep):
        self.url, self.on_wait, self.wait_s, self.sleep = url, on_wait, wait_s, sleep
        self.id = ""
        self.source: dict = {}
        self._playlists: dict[str, dict] = {}
        self._reopen = threading.Lock()
        self._open()

    def _open(self, reopened: bool = False) -> None:
        if not supported(self.url):
            raise MediaError("media_unsupported", unsupported_message(self.url))
        opened = _json("POST", "/api/smtv/media/open", {"url": self.url})
        if not isinstance(opened, dict) or not opened.get("ticket"):
            raise MediaError("bad_answer", "StreamMoment answered without a download ticket: try again later", retryable=True)
        self.id, self.source = str(opened["ticket"]), dict(opened.get("source") or {})
        self._playlists.clear()
        state, place, deadline = opened.get("state"), int(opened.get("position") or 0), time.monotonic() + self.wait_s
        lost: float | None = None       # since when the queue has not answered
        while state != "ready":
            if self.on_wait:
                self.on_wait(place)
            if time.monotonic() > deadline:
                self.close()
                raise MediaError("queue_timeout", "StreamMoment's queue did not move for hours: try again later", retryable=True)
            self.sleep(WAIT_POLL_S)
            try:
                now = _json("GET", f"/api/smtv/media/{self.id}")
            except MediaError as e:
                # a passing network failure (Wi-Fi dropped for a moment, our server restarting) keeps the place: the
                # ticket lives on the server. Only a failure lasting WAIT_NET_TOLERANCE_S, or a refusal, gives it up.
                # A server that forgot the ticket (restarted) gives a new one once: a place at the end, not an error.
                if e.code == "media_ticket_expired" and not reopened:
                    print(f"media: the queue forgot ticket {self.id}; taking a new place")
                    return self._open(reopened=True)
                if not e.retryable:
                    raise
                lost = lost if lost is not None else time.monotonic()
                if time.monotonic() - lost > WAIT_NET_TOLERANCE_S:
                    raise
                print(f"media: the queue did not answer for ticket {self.id} ({e.code}), still waiting: {str(e)[:160]}")
                continue
            lost = None
            state, place = now.get("state"), int(now.get("position") or 0)
        if self.on_wait:
            self.on_wait(0)

    def _again(self, run):
        """`run()`, and once more on a fresh ticket if the server no longer knows this one. Segments are fetched 16 at a
        time: only the first of them opens the new ticket, the others see the new id and go on with it."""
        seen = self.id
        try:
            return run()
        except MediaError as e:
            if e.code != "media_ticket_expired":
                raise
            with self._reopen:
                if self.id == seen:
                    self._open()
            return run()

    def playlist(self, track: str) -> dict:
        if track not in self._playlists:
            self._playlists[track] = self._again(lambda: _json("GET", f"/api/smtv/media/{self.id}/{track}"))
        return self._playlists[track]

    def _segment(self, track: str, name: str) -> bytes:
        delay, attempt, slow = 1.0, 0, 0.2
        while True:
            try:
                return self._again(lambda: _bytes(f"/api/smtv/media/{self.id}/{track}/{name}"))
            except MediaError as e:
                if e.code == "media_slow_down" and slow < 30:      # our server's place in flight frees a moment later: not a failure
                    self.sleep(slow)
                    slow *= 1.5
                    continue
                attempt += 1
                if not e.retryable or attempt >= SEGMENT_ATTEMPTS:
                    raise
                self.sleep(delay)
                delay = min(delay * 2, 15.0)

    def fetch(self, track: str, dest: Path, start_s: float | None = None, end_s: float | None = None,
              on_progress: Callable[[int, int], None] | None = None) -> float:
        """Writes the segments of `track` over [start_s, end_s] (all when None) to `dest`, in order, `FRAGMENTS_AT_ONCE`
        at a time; the init segment (fMP4) first. Returns the start of the first segment in the recording. A half-written
        file never stays at `dest`."""
        listing = self.playlist(track)
        segments = [s for s in listing["segments"]
                    if (start_s is None or s["start"] + s["duration"] > start_s) and (end_s is None or s["start"] < end_s)]
        if not segments:
            raise MediaError("media_out_of_range", "the recording has no video at this time")
        names = ([listing["init"]] if listing.get("init") else []) + [s["name"] for s in segments]
        part = dest.with_name(dest.name + ".part")
        dest.parent.mkdir(parents=True, exist_ok=True)
        pool = ThreadPoolExecutor(max_workers=FRAGMENTS_AT_ONCE)
        try:
            with open(part, "wb") as out:
                pending: list[Future] = []
                ahead = iter(names)
                done = 0
                for name in ahead:              # at most twice as many as in flight are held in memory
                    pending.append(pool.submit(self._segment, track, name))
                    if len(pending) >= FRAGMENTS_AT_ONCE * 2:
                        break
                while pending:
                    out.write(pending.pop(0).result())
                    done += 1
                    if on_progress:
                        on_progress(done, len(names))
                    nxt = next(ahead, None)
                    if nxt is not None:
                        pending.append(pool.submit(self._segment, track, nxt))
            part.replace(dest)
        except BaseException:
            # a failed segment: the ones not started yet are not fetched, and the ones in flight are not waited for
            # (their retries would hold the error for minutes); they finish on their own, nothing reads them
            pool.shutdown(wait=False, cancel_futures=True)
            part.unlink(missing_ok=True)
            raise
        pool.shutdown()
        return float(segments[0]["start"])

    def close(self) -> None:
        if not self.id:
            return
        try:
            _json("DELETE", f"/api/smtv/media/{self.id}")
        except MediaError:
            pass                        # the server frees an idle ticket by itself after a minute and a half
        self.id = ""

    def __enter__(self) -> "Ticket":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
