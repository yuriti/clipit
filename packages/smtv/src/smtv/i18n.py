"""The window's words in files, one per language (stage 27): `web/i18n/en.json` is the source, every other language
(`ru.json`, and whatever translators add through Weblate) has the same keys. A key a language lacks is shown in
English. The page loads the files itself (app.js); this module serves the same words to the Python side: the native
dialogs, system notifications, the «soon» list (soon.json) and the pages a phone or a browser gets when it is refused.

Texts are `{name}` templates; a missing value is left empty, as in the page.
"""
from __future__ import annotations

import json
import locale
import os
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

FOLDER = Path(__file__).with_name("web") / "i18n"
SOURCE = "en"
_CODE = re.compile(r"[a-z]{2,3}(?:-[A-Z][A-Za-z]{1,3})?")   # en, ru, pt-BR, zh-Hans: the file names Weblate writes


def languages(folder: Path | None = None) -> list[str]:
    """The languages SMTV (or a tool, by its `i18n` folder) has words for: English first, then the rest by code."""
    codes = sorted(p.stem for p in (folder or FOLDER).glob("*.json") if _CODE.fullmatch(p.stem))
    return [SOURCE, *[c for c in codes if c != SOURCE]]


@lru_cache(maxsize=None)
def strings(lang: str, folder: Path | None = None) -> dict[str, str]:
    """One language's words: the window's, or a tool's (`folder`, its `i18n`). The window's English is part of the
    package: a missing or broken en.json is a bug and raises; any other file that does not load counts as empty, so its
    words come in English (a tool's own English: as their keys)."""
    if not _CODE.fullmatch(lang or ""):
        return {}
    path = (folder or FOLDER) / f"{lang}.json"
    if lang == SOURCE and folder is None:
        return json.loads(path.read_text(encoding="utf-8"))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, ValueError) as e:     # said in the log: the window then speaks English, never silently
        print(f"i18n: {path} does not load ({type(e).__name__}: {e}); its words are shown in English")
        return {}
    if not isinstance(data, dict):
        print(f"i18n: {path} is not an object of words; its words are shown in English")
        return {}
    return {k: v for k, v in data.items() if isinstance(v, str) and v}


def texts(key: str, folder: Path | None = None) -> dict[str, str]:
    """{language: text} of one key, for the page to pick its language from (`txt` in app.js): from a tool's folder when
    its English has the key, else from the window's. A key nobody has is shown as it is (a plugin may write plain
    English): {"en": key}."""
    for f in ([folder] if folder is not None else []) + [None]:
        if strings(SOURCE, f).get(key):
            return {lang: own for lang in languages(f) if (own := strings(lang, f).get(key))}
    return {SOURCE: key} if key else {}


def text(key: str, lang: str = SOURCE, **values) -> str:
    """The text of `key` in `lang`, else in English, else the key itself; `{name}` filled from `values`."""
    raw = strings(lang).get(key) or strings(SOURCE).get(key) or key
    return re.sub(r"\{(\w+)\}", lambda m: str(values.get(m.group(1), "")), raw)


def best(wanted: list[str] | tuple[str, ...]) -> str:
    """The first of the wanted languages SMTV has (pt-BR as it is, else pt), else English."""
    have = languages()
    lower = {c.lower(): c for c in have}
    for raw in wanted:
        code = (raw or "").strip().replace("_", "-").split(".")[0].split("@")[0].lower()
        if not code or code in ("c", "posix", "*"):
            continue
        if code in lower:
            return lower[code]
        base = code.split("-")[0]
        if base in lower:
            return lower[base]
    return SOURCE


def from_accept_language(header: str | None) -> str:
    """The best language for a browser's Accept-Language header (its order of preference; q values are ignored)."""
    return best([part.split(";")[0] for part in (header or "").split(",")])


def system() -> str:
    """The system's own language, as SMTV has it (a program started from an icon has no LANG on macOS)."""
    wanted: list[str] = []
    if sys.platform == "darwin":
        try:
            out = subprocess.run(["defaults", "read", "-g", "AppleLanguages"], capture_output=True, text=True, timeout=5).stdout
            wanted += [x.strip(' \t"(),') for x in out.splitlines() if x.strip(' \t"(),')]
        except (OSError, subprocess.TimeoutExpired):
            pass
    if sys.platform == "win32":
        try:
            import ctypes
            langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()  # type: ignore[attr-defined]
            wanted.append(locale.windows_locale.get(langid, ""))
        except (AttributeError, OSError):
            pass
    wanted += [x for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE") for x in os.environ.get(var, "").split(":")]
    return best([w for w in wanted if w])
