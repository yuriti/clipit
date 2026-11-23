"""Pure parts of speech recognition: windows over the audio, tokens to words, stitching at window seams, segments.

No numpy and no model here, so these are tested without downloading anything.

A long recording is cut into windows on a fixed grid; each window takes `pad` extra seconds on both sides so no word
is cut in half. A word belongs to the window on whose side of the grid line it starts; duplicates at a seam are
dropped. Words are then grouped into transcript segments.
"""
from __future__ import annotations

import math
import re

NORM = re.compile(r"[^\w]+", re.U)
SENTENCE_END = (".", "!", "?", "…")
# A segment is closed at a sentence end once it is at least SEGMENT_MIN_S long (one-sentence segments make the episode
# scan propose 2-4 s one-liners), at a pause, or at the caps.
SEGMENT_MIN_S, SEGMENT_MAX_S, SEGMENT_MAX_WORDS = 4.0, 20.0, 40
SEGMENT_GAP_S, SEGMENT_BREAK_S = 1.0, 1.5


def norm(text: str) -> str:
    return NORM.sub("", text.lower().replace("ё", "е"))


def plan_windows(start: float, end: float, grid: float, pad: float) -> list[dict]:
    """Windows over [start, end): grid lines every `grid` seconds from start, each window `pad` wider on both sides."""
    n = max(1, math.ceil((end - start - 0.5) / grid))
    lines = [start + k * grid for k in range(n)] + [end]
    return [{"grid_start": a, "grid_end": b, "start": max(start, a - pad), "end": min(end, b + pad)} for a, b in zip(lines, lines[1:])]


def _finish(words: list[dict], offset: float, frame_s: float) -> list[dict]:
    out = []
    for k, w in enumerate(words):
        end = w["last"] + frame_s
        if k + 1 < len(words):
            end = min(end, words[k + 1]["first"])
        out.append({"word": w["word"], "start": round(w["first"] + offset, 3), "end": round(max(end, w["first"] + 0.02) + offset, 3),
                    "probability": round(math.exp(sum(w["lp"]) / len(w["lp"])), 5)})
    return out


def words_space_tokens(tokens, timestamps, logprobs, offset: float, frame_s: float) -> list[dict]:
    """GigaAM: a word starts with a space, or follows GigaAM's lone space token."""
    words, space = [], True
    logprobs = logprobs or [0.0] * len(tokens)
    for token, t, lp in zip(tokens, timestamps, logprobs):
        if not token.strip():
            space = True
            continue
        if token.startswith(" ") or space or not words:
            words.append({"word": " " + token.strip(), "first": t, "last": t, "lp": [lp]})
            space = False
        else:
            words[-1]["word"] += token
            words[-1]["last"] = t
            words[-1]["lp"].append(lp)
    return _finish(words, offset, frame_s)


def words_marker_tokens(tokens, timestamps, logprobs, offset: float, frame_s: float, marker: str = "▁") -> list[dict]:
    """Parakeet (SentencePiece): a word starts with the ▁ marker. onnx-asr may already give it as a leading space."""
    words = []
    logprobs = logprobs or [0.0] * len(tokens)
    for token, t, lp in zip(tokens, timestamps, logprobs):
        starts = token.startswith(marker) or token.startswith(" ")
        piece = token.lstrip(marker).lstrip(" ")
        if not piece:
            continue
        if starts or not words:
            words.append({"word": " " + piece, "first": t, "last": t, "lp": [lp]})
        else:
            words[-1]["word"] += piece
            words[-1]["last"] = t
            words[-1]["lp"].append(lp)
    return _finish(words, offset, frame_s)


def stitch_windows(windows: list[dict], per_window: list[list[dict]]) -> list[dict]:
    """Words of every window kept on its side of the grid lines, seam duplicates dropped."""
    kept: list[dict] = []
    prev: list[dict] = []
    for i, (w, words) in enumerate(zip(windows, per_window)):
        lo = w["grid_start"] if i else -1e12
        hi = w["grid_end"] if i < len(windows) - 1 else 1e12
        mine = [x for x in words if lo <= x["start"] < hi]
        mine = [x for x in mine if not any(abs(x["start"] - p["start"]) < 0.3 and norm(x["word"]) == norm(p["word"]) for p in prev[-12:])]
        kept.extend(mine)
        prev = mine
    return kept


def segments(words: list[dict]) -> list[dict]:
    """Words -> transcript segments: closed at a sentence end once >= SEGMENT_MIN_S long, at a pause, or at the caps."""
    out, cur = [], []
    for k, w in enumerate(words):
        cur.append(w)
        nxt = words[k + 1] if k + 1 < len(words) else None
        length = w["end"] - cur[0]["start"]
        gap = nxt["start"] - w["end"] if nxt else 0.0
        if (nxt is None or gap > SEGMENT_BREAK_S or len(cur) >= SEGMENT_MAX_WORDS or length >= SEGMENT_MAX_S
                or (length >= SEGMENT_MIN_S and (w["word"].rstrip().endswith(SENTENCE_END) or gap > SEGMENT_GAP_S))):
            out.append({"start": cur[0]["start"], "end": cur[-1]["end"], "text": "".join(x["word"] for x in cur).strip(), "words": cur})
            cur = []
    return out


def filtered_segments(segs: list[dict]) -> list[dict]:
    """Drop recognition loops, a phrase repeated three or more times, and empty segments."""
    from collections import Counter
    texts = [norm(s["text"]) for s in segs]
    counts = Counter(t for t in texts if len(t) >= 12)
    keep = []
    for i, (s, t) in enumerate(zip(segs, texts)):
        if (i and t and t == texts[i - 1]) or (len(t) >= 12 and counts[t] >= 3) or not s["text"].strip():
            continue
        keep.append(s)
    return keep


def with_ids(segs: list[dict]) -> list[dict]:
    """Segment ids the episode scan refers to: s00000, s00001, …"""
    for i, s in enumerate(segs):
        s["sid"] = f"s{i:05d}"
    return segs
