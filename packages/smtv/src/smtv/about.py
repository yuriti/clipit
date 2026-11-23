"""Settings → About (stage 18): SMTV's version and changes, the core every plugin runs on, what is coming, and support.

What is coming lives in one file, `soon.json` beside this module, updated with each version: the «soon» plugin cards
(tools.SOON), the «soon» pages of the rail (Scheduled, Promotion, Campaigns), the «Add a plugin» window and the list in
About all read it. soon.json holds what each item is; its words are in the window's language files (`i18n`), under
`soon.<id>.<field>` (`points.1`, `points.2`, … for a list), so translators see them with the rest of the window. The support link is `SUPPORT_URL` here and nowhere else in the code.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, metadata
from pathlib import Path

from . import i18n

SUPPORT_URL = "https://boosty.to/smtv"
LICENSE = "MIT"
SOON_FILE = Path(__file__).with_name("soon.json")
KINDS = ("plugin", "page", "feature")
TEXT_FIELDS = ("title", "summary", "lead", "note")
LIST_FIELDS = ("points", "notes")


def _texts(key: str, words: dict[str, dict[str, str]]) -> dict[str, str]:
    """{language: text} of one key, for every language that has it; English always."""
    return {lang: d[key] for lang, d in words.items() if d.get(key)}


def parse_soon(data: dict, words: dict[str, dict[str, str]]) -> list[dict]:
    """The items of soon.json with their words from `words` ({language: {key: text}}, English required), checked: a
    known kind, a unique id, a title and a summary in English, nothing in English the file does not list, no dates."""
    en = words.get(i18n.SOURCE) or {}
    items, seen = [], set()
    for i, raw in enumerate(data.get("items") or []):
        where = f"soon.json item {i}"
        sid = raw.get("id")
        if not isinstance(sid, str) or not re.fullmatch(r"[a-z0-9-]{1,40}", sid) or sid in seen:
            raise ValueError(f"{where}: a unique id of a-z, 0-9 and dashes")
        if raw.get("kind") not in KINDS:
            raise ValueError(f"{where} ({sid}): kind is one of {', '.join(KINDS)}")
        if set(raw) - {"id", "kind", "icon"}:
            raise ValueError(f"{where} ({sid}): texts go to web/i18n/en.json as soon.{sid}.<field>, not into soon.json")
        seen.add(sid)
        item = {"id": sid, "kind": raw["kind"], "icon": str(raw.get("icon") or "")}
        for f in TEXT_FIELDS:
            if en.get(f"soon.{sid}.{f}"):
                item[f] = _texts(f"soon.{sid}.{f}", words)
        for f in LIST_FIELDS:
            n = 1
            while en.get(f"soon.{sid}.{f}.{n}"):
                n += 1
            if n > 1:
                item[f] = [_texts(f"soon.{sid}.{f}.{k}", words) for k in range(1, n)]
        if "title" not in item or "summary" not in item:
            raise ValueError(f"{where} ({sid}): needs soon.{sid}.title and soon.{sid}.summary in en.json")
        items.append(item)
    if not items:
        raise ValueError("soon.json lists nothing")
    stray = {k.split(".")[1] for k in en if k.startswith("soon.")} - seen
    if stray:
        raise ValueError(f"en.json has words for items soon.json does not list: {', '.join(sorted(stray))}")
    return items


@lru_cache(maxsize=1)
def soon() -> tuple[dict, ...]:
    """Everything announced, in the order of the file (the file ships inside the package: a broken one is a bug)."""
    words = {lang: i18n.strings(lang) for lang in i18n.languages()}
    return tuple(parse_soon(json.loads(SOON_FILE.read_text(encoding="utf-8")), words))


def soon_plugins() -> dict[str, str]:
    """The announced plugins, name → English summary (tools.SOON)."""
    return {x["id"]: x["summary"]["en"] for x in soon() if x["kind"] == "plugin"}


def soon_item(sid: str) -> dict | None:
    return next((x for x in soon() if x["id"] == sid), None)


def changes() -> list[dict]:
    """SMTV's own list of changes by version, newest first: the `## Changelog` section of the package description (the
    same text PyPI shows and the updater reads). From a source checkout it is read from the README beside the code, since
    an editable install keeps the description of the moment it was installed."""
    from .updates import changelog
    readme = Path(__file__).resolve().parents[2] / "README.md"
    text = ""
    if readme.is_file() and (readme.parent / "pyproject.toml").is_file():
        text = readme.read_text(encoding="utf-8")
    else:
        try:
            m = metadata("smtv")
            text = m.get_payload() or m.get("Description") or ""
        except PackageNotFoundError:
            text = ""
    return changelog(text)


def info(tools: list) -> dict:
    """What Settings → About shows."""
    from smtv_core import __version__ as core_version

    from . import __version__
    from .report import REPO_URL
    return {
        "version": __version__, "license": LICENSE, "repo": REPO_URL, "support": SUPPORT_URL,
        "changes": changes(),
        "core": {"package": "smtv-core", "version": core_version,
                 "plugins": [{"name": t.name, "title": t.page.title if t.page else t.name, "version": t.version} for t in tools]},
        "soon": list(soon()),
    }
