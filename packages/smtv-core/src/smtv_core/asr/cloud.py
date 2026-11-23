"""Whisper in the cloud by the person's own key (stage 20): Groq (whisper-large-v3-turbo) and OpenAI (whisper-1).

Both take one file of at most 25 MB per request and give word timings with `response_format=verbose_json` and
`timestamp_granularities[]=word` (OpenAI's gpt-4o-transcribe gives none, so it is not offered). The recording is cut into
windows of plain 16 kHz mono WAV — 32 KB a second, so a window is at most about 12 minutes — with a few seconds of
overlap, and the windows are stitched like the local models' (`words.stitch_windows`).

The key is the one of the person's provider of that service in «Settings → Providers»: it goes only to that service
and never into an error text or a log. The sound leaves the computer; the window says so before this model is chosen.
"""
from __future__ import annotations

import io
import math
import uuid
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .engines import SR, wav_duration
from .words import plan_windows, stitch_windows

LIMIT_BYTES = 25 * 1024 * 1024          # both services: 25 MB per file
SAFE_BYTES = 24 * 1000 * 1000           # what a window may take, with room for the form around the file
BYTES_PER_S = SR * 2                    # 16-bit mono
WAV_HEADER = 44
PAD_S = 2.0
MAX_GRID_S = 600.0                      # ten minutes: a failed request repeats little

SERVICES = {
    "groq": {"url": "https://api.groq.com/openai/v1/audio/transcriptions", "model": "whisper-large-v3-turbo"},
    "openai": {"url": "https://api.openai.com/v1/audio/transcriptions", "model": "whisper-1"},
}


@dataclass(frozen=True)
class CloudEngine:
    name: str
    size_mb: int = 0


def grid_s(limit_bytes: int = SAFE_BYTES, pad_s: float = PAD_S) -> float:
    """The longest grid step whose window (the step and an overlap on both sides) stays within `limit_bytes`."""
    longest = (limit_bytes - WAV_HEADER) / BYTES_PER_S
    return min(MAX_GRID_S, math.floor(longest - 2 * pad_s))


def windows(start_s: float, end_s: float, limit_bytes: int = SAFE_BYTES) -> list[dict]:
    return plan_windows(start_s, end_s, grid_s(limit_bytes), PAD_S)


def wav_bytes(wav: Path, start_s: float, end_s: float) -> bytes:
    """[start_s, end_s) of a 16 kHz mono 16-bit WAV as a WAV file of its own, without decoding the samples."""
    with wave.open(str(wav)) as src:
        if (src.getframerate(), src.getnchannels(), src.getsampwidth()) != (SR, 1, 2):
            raise ValueError(f"{wav} must be 16 kHz mono 16-bit")
        a = int(start_s * SR)
        src.setpos(min(a, src.getnframes()))
        frames = src.readframes(max(0, int(end_s * SR) - a))
    out = io.BytesIO()
    with wave.open(out, "wb") as dst:
        dst.setnchannels(1)
        dst.setsampwidth(2)
        dst.setframerate(SR)
        dst.writeframes(frames)
    return out.getvalue()


def form(fields: dict, file_bytes: bytes, filename: str = "audio.wav") -> tuple[bytes, str]:
    """multipart/form-data: the fields (a list value repeats the field) and the file."""
    boundary = "smtv" + uuid.uuid4().hex
    parts = []
    for name, value in fields.items():
        for v in value if isinstance(value, list) else [value]:
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{v}\r\n'.encode("utf-8"))
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                 f"Content-Type: audio/wav\r\n\r\n".encode("utf-8") + file_bytes + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def words_of(reply: dict, offset: float) -> list[dict]:
    """The service's word list → our words, shifted by `offset`. No probabilities: the services give none."""
    out = []
    for w in reply.get("words") or []:
        text = str(w.get("word") or "").strip()
        try:
            start, end = float(w["start"]), float(w["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if text:
            s = round(start + offset, 3)
            out.append({"word": " " + text, "start": s, "end": round(max(end + offset, s + 0.02), 3)})
    return out


def _send(url: str, body: bytes, content_type: str, key: str, timeout: float, retries: int = 2) -> dict:
    """The same retry policy as the models (`providers.send_json`): an upload that got no answer in time is not paid
    for a second time by SMTV itself."""
    from ..llm.providers import send_json
    return send_json(url, body, {"Content-Type": content_type, "Authorization": f"Bearer {key}"}, timeout, retries, key)


class CloudRecognizer:
    """Same use as `engines.Recognizer`: load() checks there is a key; transcribe_file() sends the windows one by one."""

    def __init__(self, service: str, key_of: Callable[[], str], language: str | None = None, timeout: float = 300,
                 send: Callable[..., dict] | None = None):
        if service not in SERVICES:
            raise ValueError(f"no cloud speech service {service!r}")
        self.service = service
        self.engine = CloudEngine(service)
        self.language = language if language and language != "latin" else None
        self.key_of = key_of
        self.timeout = timeout
        self.send = send or _send
        self.key = ""

    def load(self) -> "CloudRecognizer":
        self.key = self.key_of()
        return self

    def transcribe_file(self, wav: Path, start_s: float = 0.0, end_s: float | None = None,
                        progress: Callable[[float, float], None] | None = None) -> list[dict]:
        end_s = wav_duration(wav) if end_s is None else end_s
        spec = SERVICES[self.service]
        fields = {"model": spec["model"], "response_format": "verbose_json", "timestamp_granularities[]": ["word", "segment"],
                  "temperature": "0"}
        if self.language:
            fields["language"] = self.language
        plan = windows(start_s, end_s)
        per_window = []
        for w in plan:
            chunk = wav_bytes(wav, w["start"], w["end"])
            if len(chunk) > LIMIT_BYTES:          # never sent: the service would refuse it after a long upload
                raise ValueError(f"a window of {len(chunk)} bytes is over the 25 MB limit")
            body, ctype = form(fields, chunk)
            reply = self.send(spec["url"], body, ctype, self.key, self.timeout)
            words = words_of(reply, w["start"])
            if not words and str(reply.get("text") or "").strip():
                # text without word timings: the service ignored timestamp_granularities — never clips without times
                from ..llm.providers import ProviderError
                raise ProviderError(f"{self.service} gave the text without word timings: choose another speech model")
            per_window.append(words)
            if progress:
                progress(w["end"] - start_s, end_s - start_s)
        return stitch_windows(plan, per_window)
