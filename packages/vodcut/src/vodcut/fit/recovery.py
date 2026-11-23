"""Checking a model's answer and saving what can be saved from a crooked one.

From StreamMoment's Fit (externals/media-analysis/runtime/fit/recovery.py): the checks and the small deterministic
corrections, without production's ledger of paid requests and its Cursor/Codex stores (VodCut keeps its own fit.json).

- `check_item`: one returned assessment against the schema and the words; a malformed sibling never affects it;
- `normalize_trim`: a trim that leaves out the declared event's edge words by at most one second is widened to them;
- `normalize_focus_relation`: an event overlapping 35–55 s declared as "preceding" it gets the right relation;
- `natural_tail`: air after the last word, or the rest of a sentence cut in the middle (the plain shorts ending);
- `repair_hint`: for a too-short trim, its own arithmetic and word-safe edges that reach 15 s, for the repair request;
- `parse_answer`, `response_items`: the answer's text to one item per requested id, None where missing or doubled.

The window may be shorter than 70 s (see contract.py); every 70 000 of production is the window's length here.
"""
from __future__ import annotations

import copy
import itertools
import re

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from .contract import MIN_TRIM_MS, MODEL_SCHEMA, WINDOW_MS, evidence_errors, parse_response
from .trim_required import schema as required_schema

RESPONSE_SCHEMA = required_schema(MODEL_SCHEMA)   # VodCut always asks for a trim
ITEM_VALIDATOR = Draft202012Validator(RESPONSE_SCHEMA["properties"]["clips"]["items"])


def normalize_trim(item: dict, words: list, boundary_words: list, window_ms: int = WINDOW_MS) -> dict:
    """Include the declared event's edge words, at most one second per edge."""
    if evidence_errors(item, words, boundary_words, window_ms) != ["event_outside_trim"]:
        return item
    fixed = copy.deepcopy(item)
    trim = fixed["trim"]
    ids = [w[0] for w in words]
    event = words[ids.index(trim["event_start_word_id"]):ids.index(trim["event_end_word_id"]) + 1]
    start = min(trim["start_ms"], min(w[1] for w in event))
    end = max(trim["end_ms"], max(w[2] for w in event))
    if trim["start_ms"] - start > 1000 or end - trim["end_ms"] > 1000:
        return item
    trim.update(start_ms=start, end_ms=end)
    if evidence_errors(fixed, words, boundary_words, window_ms):
        return item
    ITEM_VALIDATOR.validate(fixed)
    return fixed


# The plain shorts ending: the trim gets air after its last spoken word, so the render has a natural tail instead of a
# cut on the last syllable. The end moves to the last word's end + TRIM_TAIL_MS, never into the next speech
# (NEXT_SPEECH_GUARD_MS before it) nor past the window. When the streamer talks on without a pause there is no air to
# give: the trim then runs on, at most CLOSE_MAX_MS past the model's last word, through the rest of a sentence cut in the
# middle, or through a short closing remark (at most REMARK_MAX_WORDS words followed by a REMARK_PAUSE_MS stop).
# Production's A/B of 12.11.2026 on vika_karter: 4 of 19 shorts ended 0–0.04 s after the last word without it.
TRIM_TAIL_MS = 1000
NEXT_SPEECH_GUARD_MS = 80
TAIL_MIN_MS = 500
MID_SENTENCE_GAP_MS = 1000
CLOSE_MAX_MS = 2500
REMARK_MAX_WORDS = 3
REMARK_PAUSE_MS = 1000
DASHES = ("—", "–", "-")
_TERMINAL = re.compile(r'[.!?…]["\'»”)\]]*$')


def _text(word):
    return str(word[3]).strip() if len(word) > 3 and word[3] is not None else None


def _spoken(word):
    text = _text(word)
    return text is None or bool(re.search(r"\w", text))


def _terminal(word):
    text = _text(word) or ""
    core = re.sub(r'["\'»”)\]]+$', "", text)
    if core.endswith(".") and not core.endswith("..") and (re.fullmatch(r"\W*\w\.", core) or re.search(r"\w\.\w", core)):
        return False  # «т.», «е.», «т.е.»: an abbreviation
    return bool(_TERMINAL.search(text))


def _sentence_start(word):
    return next((ch for ch in _text(word) or "" if ch.isalpha()), "").isupper()


def _closing_end(last, following, dash=None, window_ms=WINDOW_MS):
    """The end (ms) of the last word the trim keeps: `last`, or a later word of `following` that closes the sentence or
    reaches a pause, starting within CLOSE_MAX_MS of `last` and ending inside the window."""
    if _text(last) is None:
        return last[2]
    reach = list(itertools.takewhile(lambda w: w[1] <= last[2] + CLOSE_MAX_MS and w[2] <= window_ms, following))

    def gap(i):  # silence after reach[i] (i = -1: after `last`); None when nothing follows
        word, nxt = (last if i < 0 else reach[i]), following[i + 1] if i + 1 < len(following) else None
        return None if nxt is None else nxt[1] - word[2]

    kept = -1
    held = dash is not None and last[2] <= dash[1] < (following[0][1] if following else window_ms)
    if not _terminal(last) and following and (gap(-1) <= MID_SENTENCE_GAP_MS or held) and not _sentence_start(following[0]):
        kept = next((i for i, w in enumerate(reach) if _terminal(w)), None)
        if kept is None:
            return last[2]
    g = gap(kept)
    if g is not None and g < TAIL_MIN_MS:
        end = next((i for i in range(kept + 1, len(reach)) if _terminal(reach[i])), None)
        if end is not None and end - kept <= REMARK_MAX_WORDS and (gap(end) is None or gap(end) >= REMARK_PAUSE_MS):
            kept = end
    return last[2] if kept < 0 else reach[kept][2]


def natural_tail(item: dict, words: list, boundary_words: list, window_ms: int = WINDOW_MS) -> dict:
    """The trim with air after its last word; unchanged when the trim already leaves that much."""
    trim = item.get("trim") if isinstance(item, dict) else None
    if not isinstance(trim, dict) or type(trim.get("end_ms")) is not int or type(trim.get("start_ms")) is not int:
        return item
    end = trim["end_ms"]
    spoken = [w for w in boundary_words if _spoken(w)]
    inside = [w for w in spoken if trim["start_ms"] <= w[1] and w[2] <= end]
    if not inside:
        return item
    last_word = max(inside, key=lambda w: (w[2], w[1]))
    following = sorted((w for w in spoken if w[1] >= last_word[2]), key=lambda w: (w[1], w[2]))
    dash = next((w for w in sorted(boundary_words, key=lambda w: w[1]) if w[1] >= last_word[2] and _text(w) in DASHES), None)
    last = max(last_word[2], _closing_end(last_word, following, dash, window_ms))
    after = [w[1] for w in spoken if w[1] >= last]
    target = min(last + TRIM_TAIL_MS, (min(after) - NEXT_SPEECH_GUARD_MS) if after else window_ms, window_ms)
    target = word_safe(target, boundary_words, -1)
    if target <= end:
        return item
    fixed = copy.deepcopy(item)
    fixed["trim"]["end_ms"] = int(target)
    return fixed if not evidence_errors(fixed, words, boundary_words, window_ms) else item


def normalize_focus_relation(item: dict, words: list, boundary_words: list, window_ms: int = WINDOW_MS) -> dict:
    """An event that overlaps 35–55 s declared as preceding it gets the overlap relation; nothing else changes."""
    if evidence_errors(item, words, boundary_words, window_ms) != ["event_not_before_focus"]:
        return item
    fixed = copy.deepcopy(item)
    fixed["trim"]["focus_relation"] = "event_overlaps_focus"
    return fixed if not evidence_errors(fixed, words, boundary_words, window_ms) else item


def word_safe(edge: int, boundary_words: list, outward: int) -> int:
    """The edge moved out of any word it falls strictly inside: to that word's start, or its end when outward > 0."""
    while True:
        inside = [w for w in boundary_words if w[1] < edge < w[2]]
        if not inside:
            return edge
        edge = max(w[2] for w in inside) if outward > 0 else min(w[1] for w in inside)


def repair_hint(item, errors: list[str], words: list, boundary_words: list, window_ms: int = WINDOW_MS) -> str:
    """The rejected trim's own arithmetic and word-safe edges that reach 15 s, with the words they add.

    With a bare error code the model sent the same short trim back; with bare numbers it copied an edge that cut a word.
    """
    trim = item.get("trim") if isinstance(item, dict) else None
    if "invalid_trim_duration_or_bounds" not in errors or not isinstance(trim, dict):
        return ""
    a, b = trim.get("start_ms"), trim.get("end_ms")
    if type(a) is not int or type(b) is not int:
        return ""
    hint = f"Trim check: start_ms={a}, end_ms={b}, end_ms-start_ms={b - a} ms."
    if not 0 <= a < b <= window_ms:
        return hint + f" Required: 0 <= start_ms < end_ms <= {window_ms}.\n"
    if b - a > WINDOW_MS:
        return hint + f" That is longer than {WINDOW_MS} ms.\n"

    def said(lo, hi):
        text = " ".join(w[3] for w in words if lo <= w[1] and w[2] <= hi)
        return f"«{text}»" if text else "no speech"
    ways = []
    start = word_safe(b - MIN_TRIM_MS, boundary_words, -1)
    if start >= 0:
        ways.append(f"start_ms={start} adds {said(start, a)} before the event")
    end = word_safe(a + MIN_TRIM_MS, boundary_words, 1)
    if end <= window_ms:
        ways.append(f"end_ms={end} adds {said(b, end)} after it")
    return (hint + f" That is {MIN_TRIM_MS - (b - a)} ms short of the {MIN_TRIM_MS} ms minimum. Word-safe ways to reach it: " + "; or ".join(ways)
            + ". You may also move both edges. Speech of the same exchange right around the event is usually its setup or reaction, not another topic."
            " Do not return the same interval again.\n")


def check_item(item, words: list, boundary_words: list, window_ms: int = WINDOW_MS) -> tuple[dict, list[str]]:
    """(the item with the small corrections, what is still wrong). Empty errors: usable as it is."""
    if not isinstance(item, dict):
        return item, ["missing_from_response"]
    try:
        ITEM_VALIDATOR.validate(item)
    except ValidationError as error:
        return item, ["response_schema_invalid:" + ".".join(map(str, error.absolute_path)) + ":" + str(error.validator)]
    try:
        fixed = normalize_trim(item, words, boundary_words, window_ms)
    except ValidationError:
        fixed = item
    fixed = normalize_focus_relation(fixed, words, boundary_words, window_ms)
    fixed = natural_tail(fixed, words, boundary_words, window_ms)
    errors = evidence_errors(fixed, words, boundary_words, window_ms)
    if not fixed["title"].strip():
        errors.append("empty_title")
    return fixed, errors


def parse_answer(text: str) -> dict | None:
    try:
        response, _ = parse_response(text)
    except (ValueError, TypeError):
        return None
    return response if isinstance(response, dict) else None


def response_items(response, ids: list[str]) -> dict:
    """Each requested id with its single returned item; missing or duplicated ids get None."""
    clips = response.get("clips") if isinstance(response, dict) else None
    found: dict[str, list] = {}
    for clip in clips if isinstance(clips, list) else ():
        if isinstance(clip, dict) and isinstance(clip.get("id"), str):
            found.setdefault(clip["id"], []).append(clip)
    return {mid: found[mid][0] if len(found.get(mid, ())) == 1 else None for mid in ids}
