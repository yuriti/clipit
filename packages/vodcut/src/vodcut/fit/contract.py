"""Fit's answer: title, score, trim and clip format, and the checks of a trim against the window's words.

From StreamMoment's Fit (externals/media-analysis/runtime/fit/contract.py). The schema is the one in the prompts
repository (`schemas/fit.json`); a test keeps the two equal. One change: the window may be shorter than 70 s (a recording
shorter than that), so the trim checks take the window's length; for 70 s they are the production checks word for word.
"""
from __future__ import annotations

import json

VERSION = "shorts-fit-format-v2"
WINDOW_MS = 70000
MIN_TRIM_MS = 15000
FOCUS_MS = (35000, 55000)
CLIP_FORMATS = ["story", "explanation", "dialogue", "reaction", "comedy", "visual_moment", "unknown"]


def object_schema(properties: dict) -> dict:
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


TRIM_SCHEMA = object_schema({
    "start_ms": {"type": "integer", "minimum": 0, "maximum": 55000},
    "end_ms": {"type": "integer", "minimum": 15000, "maximum": 70000},
    "event_start_word_id": {"type": "string"},
    "event_end_word_id": {"type": "string"},
    "focus_relation": {"enum": ["event_overlaps_focus", "event_precedes_focus_possible_delay"]},
})
ITEM_SCHEMA = object_schema({
    "clip_format": {"type": "string", "enum": CLIP_FORMATS},
    "id": {"type": "string"},
    "title": {"type": "string", "minLength": 1, "maxLength": 120, "pattern": r"^[^\r\n]+$"},
    "fit_score": {"type": ["integer", "null"], "minimum": 0, "maximum": 100, "multipleOf": 5},
    "trim": {"anyOf": [TRIM_SCHEMA, {"type": "null"}]},
})
# Unknown evidence never produces an automatic trim; without trim_required a missing trim caps the score.
ITEM_SCHEMA["allOf"] = [
    {"if": {"properties": {"fit_score": {"type": "null"}}}, "then": {"properties": {"trim": {"type": "null"}}}},
    {"if": {"properties": {"trim": {"type": "null"}}}, "then": {"properties": {"fit_score": {"anyOf": [{"type": "null"}, {"type": "integer", "maximum": 40}]}}}},
]
MODEL_SCHEMA = object_schema({"clips": {"type": "array", "items": ITEM_SCHEMA, "minItems": 1, "maxItems": 4}})
# Strict structured output rejects allOf/if-then; those two rules are checked locally per item.
TRANSPORT_SCHEMA = object_schema({"clips": {"type": "array", "items": {k: v for k, v in ITEM_SCHEMA.items() if k != "allOf"},
                                            "minItems": 1, "maxItems": 4}})
BATCH = 4  # at most this many windows in one request (the schema's maxItems)


def conditional_errors(item: dict) -> list[str]:
    score, trim = item.get("fit_score"), item.get("trim")
    if score is None and trim is not None:
        return ["null_score_requires_null_trim"]
    if trim is None and type(score) is int and score > 40:
        return ["null_trim_requires_score_at_most_40"]
    return []


def evidence_errors(item: dict, words: list, boundary_words: list, window_ms: int = WINDOW_MS) -> list[str]:
    """What is wrong with the trim against the words: bounds, cut words, event words, the focus relation."""
    errors: list[str] = []
    trim = item.get("trim")
    if trim is None:
        return errors
    a, b = trim.get("start_ms"), trim.get("end_ms")
    if type(a) is not int or type(b) is not int:
        return ["noninteger_trim_bounds"]
    if not (0 <= a < b <= window_ms and MIN_TRIM_MS <= b - a <= WINDOW_MS):
        errors.append("invalid_trim_duration_or_bounds")
    if any(w[1] < a < w[2] or w[1] < b < w[2] for w in boundary_words):
        errors.append("trim_cuts_word")
    ids = [w[0] for w in words]
    first, last = trim.get("event_start_word_id"), trim.get("event_end_word_id")
    if first not in ids or last not in ids:
        return errors + ["unknown_event_word_id"]
    if ids.index(first) > ids.index(last):
        return errors + ["reversed_event_word_ids"]
    event = words[ids.index(first):ids.index(last) + 1]
    if not all(a <= w[1] < w[2] <= b for w in event):
        errors.append("event_outside_trim")
    start, end = min(w[1] for w in event), max(w[2] for w in event)
    if trim["focus_relation"] == "event_overlaps_focus" and not (start < FOCUS_MS[1] and end > FOCUS_MS[0]):
        errors.append("event_does_not_overlap_focus")
    if trim["focus_relation"] == "event_precedes_focus_possible_delay" and end > FOCUS_MS[0]:
        errors.append("event_not_before_focus")
    return errors


def parse_response(raw: str) -> tuple[dict, bool]:
    """(answer, clean): the JSON itself, or the one {"clips": [...]} object found inside other text."""
    try:
        return json.loads(raw), True
    except json.JSONDecodeError:
        found = []
        for pos, char in enumerate(raw):
            if char != "{":
                continue
            try:
                x, _ = json.JSONDecoder().raw_decode(raw[pos:])
            except json.JSONDecodeError:
                continue
            if isinstance(x, dict) and isinstance(x.get("clips"), list):
                found.append(x)
        if len(found) != 1:
            raise ValueError("No unique response object")
        return found[0], False
