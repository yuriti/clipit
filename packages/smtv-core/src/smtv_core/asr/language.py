"""Which language a stream is in, without an extra model.

Parakeet v3 transcribes 25 languages without being told which one. A few short samples from the stream go through it,
and the writing system of the text decides: Cyrillic → Russian (GigaAM, unless Ukrainian letters show up),
Latin → English or another Latin-script language (Parakeet handles all of them the same way).
"""
from __future__ import annotations

import unicodedata
from pathlib import Path

from .engines import PARAKEET, PARAKEET_LANGUAGES, Recognizer, read_wav, wav_duration

UKRAINIAN = set("іїєґІЇЄҐ")
SAMPLE_S = 30.0
SAMPLE_AT = (0.15, 0.5, 0.85)   # spread over the stream: the start is often a waiting screen with music


def guess(text: str) -> str | None:
    """'ru', 'uk', 'latin' (any Latin-script language) or None when there are too few letters to tell."""
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 40:
        return None
    if any(c in UKRAINIAN for c in letters):
        return "uk"
    cyr = sum(1 for c in letters if "CYRILLIC" in unicodedata.name(c, ""))
    lat = sum(1 for c in letters if "LATIN" in unicodedata.name(c, ""))
    if cyr > 2 * lat:
        return "ru"
    if lat > 2 * cyr:
        return "latin"
    return None


def detect(wav: Path, recognizer: Recognizer | None = None, fallback: str = "latin") -> str:
    """'ru', 'uk' or 'latin' by the writing system of a few samples. Works with either model: Parakeet writes each
    language in its own letters, and GigaAM writes speech that is not Russian in Latin letters (checked on stage 15:
    an English tournament came out «fall and agan a anken the frown…», Russian streams in Cyrillic). `fallback` when
    the samples have no clear speech."""
    rec = recognizer or Recognizer(PARAKEET).load()
    duration = wav_duration(wav)
    starts = [max(0.0, min(duration - SAMPLE_S, duration * f)) for f in SAMPLE_AT]
    clips = [read_wav(wav, s, s + SAMPLE_S) for s in starts]
    text = " ".join(w["word"] for words in rec.recognize(clips, starts) for w in words)
    return guess(text) or fallback


def choose(hint: str | None, models_dir: Path | None = None) -> str | None:
    """The language without listening, or None when it has to be detected: the recording says which language it is in
    (YouTube does; Twitch VODs and files do not) — that one, if a model knows it. Without a hint the samples are
    listened to (with Parakeet when it is here, else with GigaAM); a language other than Russian then gets Parakeet,
    downloaded at that moment (stage 15: never Russian by default for a stream in another language). Since stage 20 any
    language Whisper knows counts as well: it gets Whisper, or the model chosen for it in «Settings → Speech»."""
    from .catalog import WHISPER_LANGUAGES
    code = (hint or "").strip().lower().replace("_", "-").split("-")[0]
    if code == "ru" or code in PARAKEET_LANGUAGES or code in WHISPER_LANGUAGES:
        return code
    return None
