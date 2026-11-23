"""Which rated episodes become clips: every strong and good one, the best first, at most 30 per request — as production does
(stage 15: the 2.5 per hour cap left good episodes out; production made 20 clips from 5.7 h)."""
from __future__ import annotations

import math

VERDICTS = ("strong", "good")
MAX_CLIPS = 30
EXPECTED_PER_HOUR = 3.5            # only for the time estimate: production made 20 clips from 5.7 h, 10 from 2 h
MIN_TRIM_S = 8.0


def limit(duration_s: float) -> int:
    """At most this many clips from a recording: the request's cap, whatever its length."""
    return MAX_CLIPS


def expected(duration_s: float) -> int:
    """About how many clips a recording gives, for the time estimate before the analysis."""
    return max(1, min(MAX_CLIPS, math.ceil(EXPECTED_PER_HOUR * duration_s / 3600)))


def pick(rated: list[dict], duration_s: float, max_clips: int | None = None) -> list[dict]:
    """Clips in stream order, each with its rank by score (1 = best)."""
    usable = []
    for e in rated:
        if e.get("status") != "ok" or e.get("verdict") not in VERDICTS:
            continue
        trim = e.get("trim") or {"start_s": e["episode_start_s"], "end_s": e["episode_end_s"]}
        if trim["end_s"] - trim["start_s"] < MIN_TRIM_S:
            continue
        usable.append((e, trim))
    usable.sort(key=lambda x: (-x[0]["score"], x[1]["start_s"]))
    chosen = usable[: max_clips or limit(duration_s)]
    clips = [{"rank": rank, "episode_id": e["episode_id"], "start_s": round(t["start_s"], 2), "end_s": round(t["end_s"], 2),
              "duration_s": round(t["end_s"] - t["start_s"], 1), "title": e["title"], "score": e["score"], "verdict": e["verdict"],
              "format": e["format"], "reason": e["reason"], "depends_on_video": e["depends_on_video"]}
             for rank, (e, t) in enumerate(chosen, 1)]
    clips.sort(key=lambda c: c["start_s"])
    for i, c in enumerate(clips, 1):
        c["id"] = f"clip{i:02d}"
    return clips
