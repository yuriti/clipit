"""Fit as the cutter only: a trim is always returned, weakness goes only into fit_score.

From StreamMoment's Fit (externals/media-analysis/runtime/fit/trim_required.py). In VodCut, as in production's new chain,
pass 2 alone judges a moment and Fit only cuts it: an answer without a trim would leave nothing to cut. Production
measured it on saved requests: 0 answers without a trim of 125 (44 of 124 with the plain policy), the same speed.
The edits apply to prompt-policy.txt as it is; each must apply exactly once, or the policy file changed under it.
"""
from __future__ import annotations

import copy

from .contract import TRIM_SCHEMA

EDITS = (
    ("Return only JSON matching the schema: id, title, fit_score, trim, clip_format.",
     "Return only JSON matching the schema: id, trim, fit_score, clip_format, title."),
    ("return fit_score=null and trim=null. This means unknown, not zero.",
     "still return the best available trim with fit_score at most 40."),
    ("An ordinary understandable but uninteresting episode gets a low numeric score, not null.",
     "An ordinary understandable but uninteresting episode gets a low score."),
    ("Propose the most coherent single interval of 15000–70000 ms if one exists, even with a low numeric fit_score.",
     "Always propose the most coherent single interval of 15000–70000 ms around the main event, even with a low fit_score."),
    ("If no coherent interval related to the focus zone can meet the duration without replacing the event, return trim=null and fit_score from 0 to 40, or null for critical uncertainty.",
     "A trim is always required. If no fully coherent interval related to the focus zone meets the duration without replacing the event, return the closest admissible interval around the main event and express the defect only through fit_score (0–40)."),
    ("If no coherent admissible interval exists, return trim=null with fit_score <=40 or null for critical uncertainty, and clip_format=unknown.",
     "If no fully coherent interval exists, still return the closest admissible one, with fit_score <=40."),
    ("insufficient evidence, or trim=null.", "or insufficient evidence."),
)
REPAIR_OLD = " If no trim can satisfy all rules, return trim=null with fit_score at most 40 or null."
REPAIR_NEW = " A trim is required: if no trim can satisfy all rules, return the closest admissible one with fit_score at most 40."
ORDER = ("id", "trim", "fit_score", "clip_format", "title")


def policy(text: str) -> str:
    for old, new in EDITS:
        if text.count(old) != 1:
            raise RuntimeError(f"fit trim_required: anchor not found once: {old[:60]}")
        text = text.replace(old, new)
    return text


def repair(text: str) -> str:
    if text.count(REPAIR_OLD) != 1:
        raise RuntimeError("fit trim_required: repair anchor not found once")
    return text.replace(REPAIR_OLD, REPAIR_NEW)


def schema(value: dict) -> dict:
    """The response schema with a trim required, an integer score and the fields in the order they are decided."""
    value = copy.deepcopy(value)
    item = value["properties"]["clips"]["items"]
    item.pop("allOf", None)
    props = item["properties"]
    props["trim"] = copy.deepcopy(TRIM_SCHEMA)
    props["fit_score"] = {**props["fit_score"], "type": "integer"}
    item["properties"] = {key: props[key] for key in ORDER}
    item["required"] = list(ORDER)
    return value
