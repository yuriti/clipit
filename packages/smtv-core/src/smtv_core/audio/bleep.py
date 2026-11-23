"""The bleep: slurs against groups of people are covered by a tone; ordinary swearing is heard as it is.

The words live in bleep_words/<language>.txt, one regular expression per line. Every list is checked whatever the
stream's language, because streamers mix languages. The tone sits on the middle of the word, so its first and last
sounds stay and the phrase keeps its sense.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

WORDS_DIR = Path(__file__).with_name("bleep_words")

# Word times from speech recognition are rough (±0.1 s, and a word before a pause may be marked seconds long), so the
# word is taken as at most MAX_WORD_S from its start, and the tone covers SHARE of it with PAD_S of slack, within
# MIN_S–MAX_S, around its middle.
MAX_WORD_S, PAD_S, SHARE, MIN_S, MAX_S = 0.8, 0.2, 0.5, 0.2, 0.4
TONE_HZ, TONE_GAIN, FADE_S = 1000, 0.07, 0.015

# Latin letters that look like Cyrillic ones, used to dodge filters ("пидoр" with a Latin o).
_LOOKALIKE = str.maketrans({"0": "о", "3": "з", "6": "б", "a": "а", "e": "е", "i": "и", "k": "к", "m": "м", "o": "о", "p": "р",
                            "c": "с", "t": "т", "x": "х", "y": "у"})


def languages() -> list[str]:
    return sorted(p.stem for p in WORDS_DIR.glob("*.txt") if not p.name.startswith("."))   # not ._ru.txt a Mac copy left


def _lines(language: str) -> list[str]:
    text = (WORDS_DIR / f"{language}.txt").read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]


@lru_cache(maxsize=None)
def pattern(langs: tuple[str, ...] | None = None) -> re.Pattern:
    """One expression for the given lists (all of them by default)."""
    alternatives = [line for lang in (langs or tuple(languages())) for line in _lines(lang)]
    return re.compile("^(?:" + "|".join(f"(?:{a})" for a in alternatives) + ")$")


def normalize(word: str) -> str:
    text = re.sub(r"^[\W_]+|[\W_]+$", "", unicodedata.normalize("NFKC", word).lower()).replace(".", "").replace("_", "").replace("-", "")
    return text.translate(_LOOKALIKE) if re.search("[а-яё]", text) else text


def is_bleeped(word: str) -> bool:
    return bool(pattern().match(normalize(word)))


def span(start_s: float, end_s: float) -> tuple[float, float]:
    """The tone's (from, to) for a word marked start_s–end_s."""
    end_s = min(end_s, start_s + MAX_WORD_S)
    size = min(MAX_S, max(MIN_S, (end_s - start_s + PAD_S) * SHARE))
    middle = (start_s + end_s) / 2
    begin = max(0.0, middle - size / 2)
    return round(begin, 3), round(begin + size, 3)


def tones(words: list[dict]) -> list[tuple[float, float]]:
    """Tones for clip words {'text', 's', 'e'} (ms, clip time), in seconds of clip time."""
    return [span(w["s"] / 1000, w["e"] / 1000) for w in words if is_bleeped(w["text"])]


def audio_filter(spans: list[tuple[float, float]]) -> str:
    """The ffmpeg audio filter (no trailing comma) that replaces the sound with the tone over the spans, with a short fade
    at each edge; '' when there is nothing to cover. Time t must start at 0 at the clip's first sample."""
    if not spans:
        return ""
    wave = f"{TONE_GAIN}*sin(2*PI*{TONE_HZ}*t)"
    keep = "*".join(f"clip(max(({a:.3f}-t)/{FADE_S}+1,(t-{b:.3f})/{FADE_S}+1),0,1)" for a, b in spans)
    return f"aeval='{wave}+(val(ch)-{wave})*{keep}':c=same"


def star(word: str) -> str:
    """п**ор: the first and last letters stay, two inner ones are starred (a word of two letters is starred whole)."""
    chars = list(word)
    letters = [i for i, c in enumerate(chars) if c.isalnum()]
    for i in (letters if len(letters) <= 2 else letters[1:-1][:2]):
        chars[i] = "*"
    return "".join(chars)


def masked(words: list[dict]) -> list[dict]:
    """Clip words with every bleeped word starred, so the captions do not show what the sound covers."""
    return [{**w, "text": star(w["text"])} if is_bleeped(w["text"]) else w for w in words]
