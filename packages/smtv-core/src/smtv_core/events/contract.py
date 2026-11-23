"""The public event contract: a versioned JSON schema for the envelope and for the data of every event type.

`schema.json` next to this file is the contract. A new field or a new type raises the minor version; renaming or
removing a field or a type, or changing what it means, raises the major version (the same rule as the prompts).
Readers ignore fields they do not know, so a minor version never breaks a subscriber.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).parent


@lru_cache(maxsize=1)
def schema() -> dict:
    return json.loads((HERE / "schema.json").read_text(encoding="utf-8"))


def version() -> str:
    return schema()["version"]


def types() -> tuple[str, ...]:
    return tuple(schema()["types"])


def validate(event: dict) -> list[str]:
    """Why this event breaks the contract; empty when it fits."""
    doc = schema()
    errors = [f"envelope {'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}" for e in Draft202012Validator(doc["envelope"]).iter_errors(event)]
    data_schema = doc["types"].get(event.get("type"))
    if data_schema is not None and isinstance(event.get("data"), dict):
        errors += [f"{event['type']} {'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}"
                   for e in Draft202012Validator(data_schema).iter_errors(event["data"])]
    return errors


def undeclared(event: dict) -> list[str]:
    """Data fields the schema does not name. Our own tools must declare every field they write (a minor version)."""
    props = schema()["types"].get(event.get("type"), {}).get("properties", {})
    return sorted(k for k in event.get("data", {}) if k not in props)
