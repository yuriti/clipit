"""The packet Fit's model reads for one clip: the 70-second window around it, its words with times, what is heard.

From StreamMoment's Fit (externals/media-analysis/runtime/fit/packet.py, the window from vod/ingest.py). The window is
70 s centred on the clip that pass 2 chose (production's backend builds the same window around the pass-2 trim) and
kept inside the recording; a recording shorter than 70 s is one window of its own length. Times in the packet are ms
from the window's start. The clip itself is the packet's search zone (`activity_focus_ms`), as production does for a
VOD moment. The acoustic part comes from acoustics.py (no graphics card: no speakers, no sound events).

Production reads the moment's words from the VOD transcript and checks the moment's audio by its hash; VodCut has both
in the job folder (transcript.json, audio.wav), so there is nothing to fetch and nothing to match.
"""
from __future__ import annotations

from pathlib import Path

from . import acoustics
from .compact import compact, expand
from .contract import FOCUS_MS, WINDOW_MS
from .speaker_context import merge_context

MIN_WINDOW_MS = 30000           # shorter recordings are not trimmed: a 15 s trim needs room around the event
FIXED_FOCUS_PROVENANCE = ("User-specified search zone; no per-source chat messages, measured spike intervals or reaction categories"
                          " supplied; do not infer laughter or exact causal delay")
EPISODE_FOCUS_PROVENANCE = ("Editor's episode interval from a transcript-only review of the whole recording; no chat, audio or reaction data."
                            " The main event is the episode inside it; its premise or payoff may lie a few seconds outside the interval."
                            " Not evidence of interest, laughter or success")
NOTE = ("Computed on a computer without a graphics card. There is no speaker diarization: no speaker turns, every word's speaker is"
        " unknown, which is not evidence of one or several voices. There is no sound-event detection: an empty sound_events list"
        " says nothing about laughter, music or game audio. Pauses are gaps of at least 250 ms between recognised words, not measured"
        " silence. The delivery summary (loudness and pitch measured from the audio) covers ONLY the focus coverage seconds.")


class TooShort(ValueError):
    pass


def window(start_s: float, end_s: float, duration_s: float) -> tuple[int, int]:
    """(window start in recording ms, window length in ms) around a clip [start_s, end_s]."""
    duration_ms = int(duration_s * 1000)
    length = min(WINDOW_MS, duration_ms)
    if length < MIN_WINDOW_MS:
        raise TooShort(f"the recording is {duration_s:.0f} s long; Fit needs at least {MIN_WINDOW_MS // 1000} s")
    center = round((round(start_s * 1000) + round(end_s * 1000)) / 2)
    begin = max(0, center - length // 2)
    return min(begin, max(0, duration_ms - length)), length


def valid_focus(value, window_ms: int = WINDOW_MS):
    """An episode zone [start_ms, end_ms] inside the window, at least 3 s long, or None."""
    if not isinstance(value, (list, tuple)) or len(value) != 2 or not all(type(x) is int for x in value):
        return None
    a, b = value
    return [a, b] if 0 <= a < b <= window_ms and b - a >= 3000 else None


def window_words(segments: list[dict], begin_ms: int, length_ms: int) -> tuple[list, list, list]:
    """(words fully inside, every word touching the window, intervals of edge words left out), as rows
    [word_id, start_ms, end_ms, text, confidence] in window time. Ids are "<segment>-word-<n>", local to the window:
    the speaker blocks never join words of two segments (speaker_context.py splits the id on "-word-")."""
    words, boundary, omitted = [], [], []
    seg_no = 0
    for seg in segments:
        if seg["end"] * 1000 <= begin_ms - 2000 or seg["start"] * 1000 >= begin_ms + length_ms + 2000:
            continue
        seg_no += 1
        for k, w in enumerate(seg.get("words") or [], 1):
            text = str(w.get("word") or w.get("text") or "").strip()
            if not text:
                continue
            a = round(w["start"] * 1000) - begin_ms
            b = round(w["end"] * 1000) - begin_ms
            b = max(a + 1, min(b, a + acoustics.spoken_limit_ms(text)))
            p = w.get("probability")
            row = [f"{seg_no}-word-{k}", a, b, text, round(float(p), 2) if isinstance(p, (int, float)) else None]
            if b <= 0 or a >= length_ms:
                continue
            boundary.append(row)
            if 0 <= a < b <= length_ms:
                words.append(row)
            else:
                omitted.append([max(a, 0), min(b, length_ms)])
    return words, boundary, omitted


def build(clip_id: str, segments: list[dict], wav: Path, clip_start_s: float, clip_end_s: float, duration_s: float) -> dict:
    """{"packet", "words", "boundary_words", "window_start_s", "window_ms"} for one clip."""
    begin, length = window(clip_start_s, clip_end_s, duration_s)
    words, boundary, omitted = window_words(segments, begin, length)
    if not words:
        raise ValueError("no recognised words in the clip's window")
    focus = valid_focus([round(clip_start_s * 1000) - begin, round(clip_end_s * 1000) - begin], length)
    coverage = list(FOCUS_MS) if length >= FOCUS_MS[1] else [max(0, length - (FOCUS_MS[1] - FOCUS_MS[0])), length]
    audio, rate = acoustics.read_window(wav, (begin + coverage[0]) / 1000, (coverage[1] - coverage[0]) / 1000)
    source = {
        "id": clip_id, "context_window_ms": [0, length],
        **({"activity_focus_ms": focus, "activity_focus_provenance": EPISODE_FOCUS_PROVENANCE} if focus else
           {"activity_focus_ms": list(FOCUS_MS), "activity_focus_provenance": FIXED_FOCUS_PROVENANCE}),
        "words": words, "boundary_text_omitted_intervals_ms": omitted,
        "acoustic_evidence": {
            "note": NOTE,
            f"focus_{coverage[0] // 1000}_{coverage[1] // 1000}_seconds": {
                "coverage": [coverage[0] // 1000, coverage[1] // 1000],
                "timebase": "summary ONLY within focus coverage; peak position0-1 within focus",
                "delivery": acoustics.delivery(audio, rate),
                "events": {},
            },
            "sound_events": [],
            "fully_contained_pauses_ms": acoustics.pauses([(w[1], w[2]) for w in boundary], length),
            "fully_contained_speaker_turns_ms": [],
        },
    }
    verbose, _, _ = merge_context(source)
    packet = compact(verbose)
    if expand(packet) != verbose:
        raise ValueError("compact_roundtrip_failed")
    return {"packet": packet, "words": words, "boundary_words": boundary, "window_start_s": begin / 1000, "window_ms": length}
