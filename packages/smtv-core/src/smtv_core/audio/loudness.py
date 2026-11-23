"""Loudness of a finished clip: −14 LUFS, the level platforms play shorts back at.

Two passes. A single-pass loudnorm misses the target by up to 4 LU on wide-range stream audio, so the clip is measured
first (ebur128, integrated loudness) and then one static gain is applied with a sample-peak limiter at −2 dBFS, which
keeps AAC true peaks near −1 dBTP. The video stream is copied, not re-encoded.
"""
from __future__ import annotations

import math
import re
import sys
from .. import proc
from pathlib import Path

TARGET_LUFS = -14.0
TOLERANCE_LU = 0.5       # closer than this: the clip is left as it is
MAX_GAIN_DB = 20.0       # a near-silent clip is not blown up into noise
PEAK_LIMIT = 0.794328    # −2 dBFS
SILENCE_LUFS = -70.0     # what ebur128 reports for silence or a file without sound


class LoudnessError(Exception):
    pass


def gain_db(integrated_lufs: float) -> float | None:
    """The gain that brings the clip to the target, or None when nothing should change."""
    if not math.isfinite(integrated_lufs) or integrated_lufs <= SILENCE_LUFS:
        return None
    gain = TARGET_LUFS - integrated_lufs
    return None if abs(gain) < TOLERANCE_LU else min(MAX_GAIN_DB, gain)


def measure_args(src: Path, duration_s: float) -> list[str]:
    """ffmpeg printing the integrated loudness once, at the end of the clip."""
    tail = max(0.0, duration_s - 0.2)
    return ["ffmpeg", "-hide_banner", "-v", "error", "-nostdin", "-i", str(src), "-vn",
            "-af", f"ebur128=metadata=1,aselect=gte(t\\,{tail:.3f}),ametadata=print:key=lavfi.r128.I:file=-", "-f", "null", "-"]


def parse_measure(output: str) -> float:
    """The last integrated loudness ffmpeg printed; NaN when there is none."""
    found = re.findall(r"lavfi\.r128\.I=(\S+)", output)
    try:
        return float(found[-1]) if found else math.nan
    except ValueError:
        return math.nan


def audio_filter(gain: float) -> str:
    return f"volume={gain:.2f}dB,alimiter=limit={PEAK_LIMIT}:level=false:latency=true"


def apply_args(src: Path, out: Path, gain: float) -> list[str]:
    return ["ffmpeg", "-hide_banner", "-v", "error", "-nostdin", "-y", "-i", str(src), "-map", "0:v:0", "-map", "0:a:0", "-c:v", "copy",
            "-af", audio_filter(gain), "-c:a", "aac", "-b:a", "384k", "-ar", "48000", "-ac", "2",
            "-map_metadata", "-1", "-movflags", "+faststart", str(out)]


def normalize(path: Path, duration_s: float) -> float | None:
    """Bring the clip at `path` to −14 LUFS in place. Returns the applied gain, or None when the clip was left alone."""
    try:
        done = proc.run(measure_args(path, duration_s), proc.limit(duration_s), what="ffmpeg (loudness measure)")
    except proc.TimedOut as e:
        raise LoudnessError(str(e)) from e
    if done.returncode != 0:
        raise LoudnessError(f"loudness measure failed on {path.name}: {done.stderr.strip()[-400:]}")
    measured = parse_measure(done.stdout)
    if not math.isfinite(measured):        # ffmpeg printed no reading: say so in the run log, keep the clip as it is
        print(f"loudness: no reading for {path.name}, its volume is left as it is", file=sys.stderr)
        return None
    gain = gain_db(measured)
    if gain is None:
        return None
    tmp = path.with_name(path.stem + ".loud" + path.suffix)
    try:
        done = proc.run(apply_args(path, tmp, gain), proc.limit(duration_s), what="ffmpeg (loudness gain)")
    except proc.TimedOut as e:
        tmp.unlink(missing_ok=True)
        raise LoudnessError(str(e)) from e
    if done.returncode != 0:
        tmp.unlink(missing_ok=True)
        raise LoudnessError(f"loudness gain failed on {path.name}: {done.stderr.strip()[-400:]}")
    tmp.replace(path)
    return gain
