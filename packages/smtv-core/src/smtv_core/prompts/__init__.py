"""The prompts and answer schemas, copied from the prompts repository at the version in VERSION.

Do not edit the files here by hand: change them in the prompts repository, release a version, copy it in.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent


def version() -> str:
    return (HERE / "VERSION").read_text(encoding="utf-8").strip()


@lru_cache(maxsize=None)
def text(name: str) -> str:
    """A prompt by its path in the prompts repository, e.g. "vod/pass1-prompt.txt"."""
    return (HERE / name).read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def schema(name: str) -> dict:
    """An answer schema by name, e.g. "pass1"."""
    return json.loads((HERE / "schemas" / f"{name}.json").read_text(encoding="utf-8"))


def fill(prompt: str, **values) -> str:
    """Placeholders replaced as plain text ({channel} -> value); braces of JSON examples stay as they are.

    In one pass: a value that itself holds `{transcript}` (a stream titled so) stays as it is and never pulls the
    transcript in a second time."""
    if not values:
        return prompt
    pattern = re.compile("|".join(re.escape("{" + k + "}") for k in values))
    return pattern.sub(lambda m: str(values[m.group(0)[1:-1]]), prompt)
