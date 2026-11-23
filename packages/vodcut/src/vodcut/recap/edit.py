"""The edit of a recap: jump cuts between words, webcam shots on the emotion peaks, the cold open, the chapters.

Ported from production (`vod/recap.py`, edit stage) with what this computer measures: the loudness at 10 Hz from the
job's own audio and where the webcam is (the core layout agent). Production also tracks the face in the webcam
(MediaPipe) to score the expression and to zoom on a full-camera stream; VodCut does not, so a peak here is loudness plus
the story's own peaks, and a stream whose camera is the whole picture gets no zoom.
"""
from __future__ import annotations

from smtv_core.audio import bleep

WIDTH, HEIGHT = 1920, 1080
# Speech recognition ends a word early (production, 25.10: «не успевает договаривать»), so a cut keeps 0.35 s after a word
# and 0.12 s before the next, then moves to the quietest 100 ms nearby (SNAP_S).
CUTS = {"tight": {"gap_s": 0.7, "after_s": 0.35, "before_s": 0.12}, "loose": {"gap_s": 8.0, "after_s": 3.0, "before_s": 1.5}}
SNAP_S, WORD_GUARD_S = 0.15, (0.25, 0.08)
JOIN_FADE_S, PART_FADE_S = 0.025, 0.03
TAIL_S = {"tight": 1.2, "loose": 3.0}        # silence kept after the last word of a part (the reaction)
LOUD_DB, LOUD_PAD_S = 8.0, 0.3               # a pause this much louder than the part's median is a reaction, not dead air
PEAK_KEEP_S = (1.0, 2.0)                     # never cut around an emotion peak
MIN_PIECE_S, JOIN_S = 0.35, 0.12
EFFECT = {"punch": (0.6, 1.6), "focus": (1.0, 2.0)}   # seconds before / after the peak
PEAK_SPACING_S, PEAKS_PER_MIN, PEAK_MIN_SCORE = 15.0, 3, 1.2
CAM_FILL = 0.85                              # punch-in: the webcam takes this share of the frame height
END_FADE_S = 1.2
INTRO_CLIPS, INTRO_BEFORE_S, INTRO_AFTER_S, INTRO_SPACING_S = 5, 0.45, 0.65, 30.0
MAX_VIDEO_S = 1800


class EditError(RuntimeError):
    pass


# ---- jump cuts ----------------------------------------------------------------------------------------------------
def loud_spans(levels, start_s, end_s, *, step_s=0.1, threshold_db=LOUD_DB, pad_s=LOUD_PAD_S):
    """Spans (source time) where the audio is `threshold_db` above the part's median: laughter, screams."""
    if not levels:
        return []
    median = sorted(levels)[len(levels) // 2]
    spans: list[list[float]] = []
    for i, level in enumerate(levels):
        if level >= median + threshold_db:
            a, b = start_s + i * step_s - pad_s, start_s + (i + 1) * step_s + pad_s
            if spans and a <= spans[-1][1]:
                spans[-1][1] = b
            else:
                spans.append([a, b])
    return [(max(start_s, a), min(end_s, b)) for a, b in spans]


def quietest(levels, start_s, lo, hi, target, step_s=0.1):
    """Centre of the quietest bin within [lo, hi]; of bins equally quiet to 1 dB the one nearest `target`."""
    bins = [(round(level), abs(start_s + i * step_s + step_s / 2 - target), start_s + i * step_s + step_s / 2) for i, level in enumerate(levels)
            if lo <= start_s + i * step_s + step_s / 2 <= hi]
    return min(bins)[2] if bins else None


def snap_cut(a, b, levels, start_s, *, after_word=None, before_word=None):
    """A cut [a, b] moved to quiet audio near its edges, never into the words around it; None when nothing is left."""
    lo = after_word + WORD_GUARD_S[0] if after_word is not None else a - SNAP_S
    hi = before_word - WORD_GUARD_S[1] if before_word is not None else b + SNAP_S
    if levels:
        a = quietest(levels, start_s, max(lo, a - SNAP_S / 3), a + SNAP_S, a) or a
        b = quietest(levels, start_s, b - SNAP_S, min(hi, b + SNAP_S / 3), b) or b
    a, b = max(a, lo), min(b, hi)
    return (a, b) if b - a > 0.1 else None


def keep_pieces(part, words, *, levels=(), peaks=(), tail_s=None):
    """The source spans of a part that stay after the jump cuts. A pause longer than the pace's gap loses its middle;
    loud stretches (non-verbal reactions) and the seconds around an emotion peak are kept."""
    start, end, pace = part["start_s"], part["end_s"], part.get("pace", "tight")
    rule = CUTS[pace]
    inside = [w for w in words if w["start"] >= start and w["end"] <= end + 0.3]
    levels = list(levels)
    protected = loud_spans(levels, start, end) + [(p - PEAK_KEEP_S[0], p + PEAK_KEEP_S[1]) for p in peaks]
    cuts = []
    if inside:
        if inside[0]["start"] - start > rule["gap_s"] + rule["before_s"]:
            cuts.append(snap_cut(start, inside[0]["start"] - rule["before_s"], levels, start, before_word=inside[0]["start"]))
        for prev, nxt in zip(inside, inside[1:]):
            if nxt["start"] - prev["end"] > rule["gap_s"]:
                cuts.append(snap_cut(prev["end"] + rule["after_s"], nxt["start"] - rule["before_s"], levels, start,
                                     after_word=prev["end"], before_word=nxt["start"]))
        keep_tail = tail_s or TAIL_S[pace]
        if end - inside[-1]["end"] > keep_tail:
            cuts.append(snap_cut(inside[-1]["end"] + keep_tail, end, levels, start, after_word=inside[-1]["end"]))
    pieces = [(start, end)]
    for a, b in (c for c in cuts if c):
        holes = [(a, b)]
        for p, q in protected:          # a protected span splits the cut into what is left of it
            holes = [hh for x, y in holes for hh in ((x, min(y, p)), (max(x, q), y)) if hh[1] - hh[0] > 0.05]
        for x, y in holes:
            pieces = [s for u, v in pieces for s in ((u, min(v, x)), (max(u, y), v)) if s[1] - s[0] > 0]
    joined: list[tuple[float, float]] = []
    for a, b in pieces:
        if joined and a - joined[-1][1] < JOIN_S:
            joined[-1] = (joined[-1][0], b)
        else:
            joined.append((a, b))
    return [(round(a, 3), round(b, 3)) for a, b in joined if b - a >= MIN_PIECE_S]


class Timeline:
    """Source time ↔ output time of one part's kept pieces."""

    def __init__(self, pieces):
        self.pieces, self.starts, t = [tuple(p) for p in pieces], [], 0.0
        for a, b in self.pieces:
            self.starts.append(t)
            t += b - a
        self.duration = t

    def out(self, source_s):
        """Output time of a source instant; one inside a cut maps to the next kept frame (None after the last)."""
        for (a, b), at in zip(self.pieces, self.starts):
            if source_s < a:
                return at
            if source_s <= b:
                return at + source_s - a
        return None


def part_bleeps(words, timeline) -> list[list[float]]:
    """Tones over the part's kept slurs, in the part's output time (smtv_core.audio.bleep)."""
    tones = []
    for w in words:
        if not bleep.is_bleeped(w["text"]):
            continue
        if not any(x - 0.05 <= w["start"] and w["end"] <= y + 0.05 for x, y in timeline.pieces):
            continue
        a, b = timeline.out(w["start"]), timeline.out(w["end"])
        if a is not None and b is not None and b >= a:
            tones.append(list(bleep.span(a, max(b, a + 0.05))))
    return tones


# ---- webcam shots -------------------------------------------------------------------------------------------------
def emotion_scores(levels, start_s, *, story_peaks=(), step_s=0.1):
    """[(source_s, score)] at 10 Hz: loudness over the part's median (6 dB = 1) and a bonus near the story's peaks."""
    if not levels:
        return []
    median = sorted(levels)[len(levels) // 2]
    scores = []
    for i, level in enumerate(levels):
        t = start_s + i * step_s
        score = (level - median) / 6.0 + (1.5 if any(abs(t - p) <= 1.5 for p in story_peaks) else 0.0)
        scores.append((round(t, 2), round(score, 3)))
    return scores


def pick_peaks(scores, *, spacing_s=PEAK_SPACING_S, min_score=PEAK_MIN_SCORE, limit=None):
    """Highest scores first, at least `spacing_s` apart, smoothed over half a second."""
    if not scores:
        return []
    values = [s for _, s in scores]
    smooth = [sum(values[max(0, i - 2):i + 3]) / len(values[max(0, i - 2):i + 3]) for i in range(len(values))]
    chosen: list[tuple[float, float]] = []
    for i in sorted(range(len(smooth)), key=lambda i: -smooth[i]):
        if smooth[i] < min_score or (limit is not None and len(chosen) >= limit):
            break
        if all(abs(scores[i][0] - t) >= spacing_s for t, _ in chosen):
            chosen.append((scores[i][0], round(smooth[i], 3)))
    return sorted(chosen)


def even(value) -> int:
    return int(value) // 2 * 2


def punch_rect(cam):
    """The 16:9 source rectangle of a punch-in, in pixels of the 1920×1080 source: around the webcam (fractions of the
    frame) so it fills CAM_FILL of the height. None without a webcam."""
    if not cam:
        return None
    height = min(HEIGHT, cam["height"] * HEIGHT / CAM_FILL)
    cx, cy = (cam["x"] + cam["width"] / 2) * WIDTH, (cam["y"] + cam["height"] / 2) * HEIGHT
    width, height = even(height * WIDTH / HEIGHT), even(height)
    x = even(min(max(0.0, cx - width / 2), WIDTH - width))
    y = even(min(max(0.0, cy - height / 2), HEIGHT - height))
    return {"x": x, "y": y, "width": width, "height": height}


def cam_rect(cam):
    if not cam:
        return None
    rect = {"x": even(cam["x"] * WIDTH), "y": even(cam["y"] * HEIGHT), "width": even(cam["width"] * WIDTH), "height": even(cam["height"] * HEIGHT)}
    rect["width"], rect["height"] = min(rect["width"], WIDTH - rect["x"]), min(rect["height"], HEIGHT - rect["y"])
    return rect if rect["width"] >= 32 and rect["height"] >= 32 else None


def webcam_shots(peaks, timeline, *, punch, focus, first="punch"):
    """Peaks → [{kind, start_s, end_s, peak_s, score}] in the part's output time; the kinds take turns."""
    shots, kind = [], first
    for peak_s, score in peaks:
        at = timeline.out(peak_s)
        if at is None:
            continue
        if not focus:
            kind = "punch"
        elif not punch:
            kind = "focus"
        before, after = EFFECT[kind]
        a, b = max(0.0, at - before), min(timeline.duration, at + after)
        if b - a < 1.0 or any(a < s["end_s"] + 1.0 and b > s["start_s"] - 1.0 for s in shots):
            continue
        shots.append({"kind": kind, "start_s": round(a, 2), "end_s": round(b, 2), "peak_s": round(peak_s, 2), "score": score})
        kind = "focus" if kind == "punch" else "punch"
    return sorted(shots, key=lambda s: s["start_s"])


# ---- the whole video ----------------------------------------------------------------------------------------------
def plan(story: dict, signals: dict, words: list[dict], facts: dict) -> dict:
    """recap.json: every part with its kept pieces, tones, webcam shots and ad boxes in output time; the cold open; the
    chapters with their start in the video; the description."""
    parts, t = [], 0.0
    for part in story["parts"]:
        signal = signals.get(str(part["index"])) or {}
        levels = signal.get("levels") or []
        candidates = pick_peaks(emotion_scores(levels, part["start_s"], story_peaks=part["peaks_s"]))
        closing = part is story["parts"][-1]           # the goodbye's last word stays clear of the fade to black
        pieces = keep_pieces(part, words, levels=levels, peaks=[p for p, _ in candidates] + part["peaks_s"],
                             tail_s=END_FADE_S + 0.8 if closing else None)
        if not pieces:
            continue
        timeline = Timeline(pieces)
        parts.append({**{k: part[k] for k in ("index", "chapter", "start_s", "end_s", "role", "pace", "why", "music")},
                      "pieces": [list(p) for p in pieces], "out_start_s": round(t, 2), "duration_s": round(timeline.duration, 2),
                      "bleeps": part_bleeps(words, timeline), "peaks": candidates, "cam": signal.get("cam"), "shots": [],
                      "blur": [list(b) for b in signal.get("ads") or []]})
        t += timeline.duration
    if not parts:
        raise EditError("nothing of the story was left after the cuts")
    budget = int(PEAKS_PER_MIN * t / 60)               # a few per minute over the whole video, the strongest win
    allowed = {(i, peak[0]) for i, peak in sorted(((p["index"], pk) for p in parts for pk in p["peaks"]), key=lambda x: -x[1][1])[:budget]}
    kind = "punch"
    for part in parts:
        punch, focus = punch_rect(part["cam"]), cam_rect(part["cam"])
        if not punch and not focus:
            continue
        part["shots"] = webcam_shots([pk for pk in part["peaks"] if (part["index"], pk[0]) in allowed], Timeline(part["pieces"]),
                                     punch=punch, focus=focus, first=kind)
        part["punch_rect"], part["cam_rect"] = punch, focus
        if part["shots"]:
            kind = "focus" if part["shots"][-1]["kind"] == "punch" else "punch"
    intro = cold_open(parts, words)
    for part in parts:                                  # the parts follow the cold open
        part["out_start_s"] = round(part["out_start_s"] + intro["duration_s"], 2)
    chapters, seen = [], set()
    for part in parts:
        if part["chapter"] not in seen:
            seen.add(part["chapter"])
            chapters.append({"start_s": part["out_start_s"], "title": story["chapters"][part["chapter"]]["title"], "stream_s": part["start_s"]})
    total = round(intro["duration_s"] + t, 2)
    if total > MAX_VIDEO_S:
        raise EditError(f"the recap would be {total / 60:.1f} min, over the 30 min limit")
    return {"version": 1, "title": story["title"], "hook": story["hook"], "intro": intro, "parts": parts, "chapters": chapters,
            "duration_s": total, "source_s": story["source_s"],
            "music_risk": [{"index": p["index"], "stream_s": [p["start_s"], p["end_s"]]} for p in parts if p["music"]],
            "shots": {k: sum(1 for p in parts for s in p["shots"] if s["kind"] == k) for k in ("punch", "focus")},
            "ads_blurred": len({tuple(b) for p in parts for b in p["blur"]}),
            "description": description(facts, story["hook"], chapters)}


def cold_open(parts, words=(), count=INTRO_CLIPS):
    """The 5–6 s teaser before the stream: ~1.1 s around each of the strongest peaks (one per part, 30 s apart), in
    stream order, zoomed on the webcam where the part has one. A clip keeps the tones of its own slurs."""
    ranked = sorted(((score, t, p) for p in parts for t, score in p["peaks"]), key=lambda x: -x[0])
    chosen, used = [], set()
    for score, t, part in ranked:
        if part["index"] in used or any(abs(t - c[1]) < INTRO_SPACING_S for c in chosen):
            continue
        chosen.append((score, t, part))
        used.add(part["index"])
        if len(chosen) == count:
            break
    clips = []
    for score, t, part in sorted(chosen, key=lambda c: c[1]):
        a, b = max(part["start_s"], t - INTRO_BEFORE_S), min(part["end_s"], t + INTRO_AFTER_S)
        tones = [list(bleep.span(w["start"] - a, w["end"] - a)) for w in words if a <= w["start"] and w["end"] <= b and bleep.is_bleeped(w["text"])]
        clips.append({"index": part["index"], "from_s": round(a, 2), "to_s": round(b, 2), "peak_s": t, "score": score, "rect": part.get("punch_rect"),
                      "bleeps": tones, "blur": part["blur"]})
    return {"clips": clips, "duration_s": round(sum(c["to_s"] - c["from_s"] for c in clips), 2)}


def stamp(seconds) -> str:
    s = int(seconds)
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}" if s >= 3600 else f"{s // 60:02d}:{s % 60:02d}"


def chapters_text(chapters) -> str:
    """YouTube chapters: the first at 00:00 (the cold open opens chapter 1)."""
    return "\n".join(f"{stamp(c['start_s'] if i else 0)} {c['title']}" for i, c in enumerate(chapters)) + "\n"


TEXT = {"en": {"stream": "Stream «{title}», {duration}.", "streamer": "Streamer: {channel}", "full": "Full stream: {url}"},
        "ru": {"stream": "Стрим «{title}», {duration}.", "streamer": "Стример: {channel}", "full": "Полный стрим: {url}"}}


def description(facts: dict, hook: str, chapters) -> str:
    """Viewer text: the hook, the stream, the chapters (YouTube turns them into chapters), the links. In the stream's
    language where VodCut has it, else English."""
    words = TEXT.get(facts.get("language") or "", TEXT["en"])
    from .story import human_duration
    lines = [hook, "", words["stream"].format(title=(facts.get("title") or "").strip(), duration=human_duration(float(facts.get("duration_s") or 0), facts.get("language") or "en")), ""]
    lines += chapters_text(chapters).rstrip("\n").split("\n")
    if facts.get("channel") or facts.get("url"):
        lines.append("")
    if facts.get("channel"):
        lines.append(words["streamer"].format(channel=facts["channel"]))
    if facts.get("url"):
        lines.append(words["full"].format(url=facts["url"]))
    return "\n".join(lines).strip()
