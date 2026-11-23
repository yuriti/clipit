"""Swear words starred in text burned into a clip (captions, hook): the first letter stays, the next two become stars.

The sound is not touched: swearing is heard as said; only slurs get a tone (smtv_core.audio.bleep). The rule and the
lists are the production ones (`maskProfanityForDisplay` in StreamMoment's shorts policy), so a clip reads the same on
YouTube and TikTok whichever made it: «БЛЯДЬ» → «Б**ДЬ», «НАХУЙ» → «Н**УЙ».
"""
from __future__ import annotations

import re
import unicodedata

from ..audio import bleep

CANDIDATE = re.compile(r"[^\W_]+(?:[._-][^\W_]+)*")
ENGLISH = re.compile(r"^(?:fuck(?:ed|er|ers|ing|s)?|motherfuck(?:er|ers|ing)?|shit(?:s|ted|ting|ty)?|bullshit|bitch(?:es|ing)?|"
                     r"asshole(?:s)?|cunt(?:s)?)$")
RUSSIAN = [re.compile(p) for p in (
    r"^(?:бля+[а-яё]*|бла+(?:дь|ть)[а-яё]*)$",
    r"^(?:бялт[ьъ]?[а-яё]*)$",
    r"^(?:(?:(?:вы|до|за|на|над|от|пере|по|под|при|про|раз|у)?[её]+б+|(?:в|вз|об|раз|с)ъ[её]+б+)[а-яё]*)$",
    r"^(?:(?:в|вз|вы|до|за|на|над|об|от|пере|по|под|при|про|рас|раз|с|у)?п+и+з+д+[а-яё]*)$",
    r"^(?:(?:а|до|за|на|не|ни|о|от|по|под|при|про|раз|с)?ху+(?:й|я|е|ё|и|ев|ёв)[а-яё]*)$",
    r"^(?:сук(?:а+|и|у|е|ой|ою|ам|ами|ах|ин|ина|ины|иной|иного|иному|иным|иных|иную|онок|онки|онку|онке|онкам|онками|онках)|"
    r"суч(?:ка|ки|ку|ке|кой|ек|онок|онки|онку|онке|онкам|онками|онках))$",
    r"^(?:муд(?:ак|ила|озвон|ень|оеб)[а-яё]*)$",
    r"^(?:(?:долбо|мозго)[её]б[а-яё]*)$",
    r"^(?:г[ао]ндон[а-яё]*)$",
    r"^(?:залуп[а-яё]*)$",
    r"^(?:манд(?:а|ы|е|у|ой|ою|ам|ами|ах))$",
    r"^(?:дроч[а-яё]*)$",
)]
TRANSLIT = re.compile(r"^(?:blya(?:d|t)?[^\W\d_]*|e+b(?:at|al|an|ash|lan|lo|nya|uch|yob)[^\W\d_]*|yo+b(?:an|at|lo|nut)[^\W\d_]*|"
                      r"pizd[^\W\d_]*|(?:na|po|za|o)?(?:hui|huy|khui)(?:$|ara|ev|lo|nya|ov|sos)[^\W\d_]*|suka[^\W\d_]*|"
                      r"cyka[^\W\d_]*|mudak[^\W\d_]*|dolboe+b[^\W\d_]*|gandon[^\W\d_]*)$")
ALLOW = re.compile(r"^(?:блямб[а-яё]*|бляшк[а-яё]*)$")
LOOKALIKE = str.maketrans({"0": "о", "3": "з", "6": "б", "a": "а", "e": "е", "i": "и", "k": "к", "m": "м", "o": "о", "p": "р",
                           "c": "с", "t": "т", "x": "х", "y": "у"})


def _normal(word: str) -> str:
    text = re.sub(r"[._-]", "", unicodedata.normalize("NFKC", word).upper().lower())
    return text.translate(LOOKALIKE) if re.search(r"[а-яё]", text) else text


def is_profane(word: str) -> bool:
    w = _normal(word)
    if ALLOW.match(w):
        return False
    return bool(ENGLISH.match(w) or TRANSLIT.match(w) or any(p.match(w) for p in RUSSIAN) or bleep.is_bleeped(word))


def _star(word: str) -> str:
    chars = list(word)
    letters = [i for i, c in enumerate(chars) if c.isalnum()]
    for i in (letters if len(letters) <= 2 else letters[1:-1][:2]):
        chars[i] = "*"
    return "".join(chars)


def mask(text: str) -> str:
    """`text` with every swear word starred."""
    out = CANDIDATE.sub(lambda m: _star(m.group(0)) if is_profane(m.group(0)) else m.group(0), text or "")
    return re.sub(r"\*{3,}", "**", out)


def masked(words: list[dict]) -> list[dict]:
    """Clip words {'text', …} with swear words starred, for the captions."""
    return [{**w, "text": mask(w["text"])} for w in words]
