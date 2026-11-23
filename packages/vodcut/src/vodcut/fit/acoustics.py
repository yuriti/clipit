"""What Fit hears in a window, computed on the processor from what VodCut already has: the audio and the words.

Production fills this part of the packet on the PC's graphics card: Sortformer finds who speaks when (speaker turns, and
pauses are the gaps between turns), AST finds sound events (laughter, music, game effects, shouts), and plain DSP
measures loudness and pitch over 35–55 s. SMTV runs on computers without such a card, so here:

- loudness and pitch over the focus seconds — the same DSP as production (`compact25_flow7_audio.dsp_features`, numpy
  only), the eight values the packet keeps: silence share, loudness range, loudness at the beginning, middle and end,
  where the loudest moment is, median pitch and its spread;
- pauses — gaps of at least 250 ms between recognised words (production: gaps between Sortformer's speaker turns). A
  word's end is first cut to a plausible length (GigaAM stretches some words over the silence after them);
- speaker turns — none: every word's speaker is unknown, the packet's note says so;
- sound events — none: no laughter, music or effects detection without AST.
"""
from __future__ import annotations

import re
import wave
from pathlib import Path

import numpy as np

PAUSE_MIN_MS = 250
# A word ends at most max(STRETCH_MIN_MS, STRETCH_MS_PER_LETTER × letters) after its start (production's
# fit/vod_words.py: GigaAM marked «тарелка.» over 7 s of quiet game noise; median speech is 53 ms per letter).
STRETCH_MIN_MS, STRETCH_MS_PER_LETTER = 1000, 200
RATE = 16000


def spoken_limit_ms(text: str) -> int:
    return max(STRETCH_MIN_MS, STRETCH_MS_PER_LETTER * len(re.findall(r"\w", text)))


def read_window(wav: Path, start_s: float, length_s: float) -> tuple[np.ndarray, int]:
    """Samples in [-1, 1] of [start, start + length) of a 16-bit PCM WAV (VodCut's audio.wav: mono, 16 kHz)."""
    with wave.open(str(wav), "rb") as f:
        rate, channels, width = f.getframerate(), f.getnchannels(), f.getsampwidth()
        if width != 2:
            raise ValueError(f"audio.wav: {8 * width}-bit samples, expected 16-bit PCM")
        first = max(0, int(round(start_s * rate)))
        f.setpos(min(first, f.getnframes()))
        raw = f.readframes(int(round(length_s * rate)))
    data = np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    return data, rate


def _percentile(values: np.ndarray, q: float, fallback: float = 0.0) -> float:
    return float(np.percentile(values, q)) if values.size else fallback


def _pitch(audio: np.ndarray, rate: int, rms_gate: float) -> dict:
    frame_size, hop = round(rate * 0.05), round(rate * 0.02)
    min_lag, max_lag = max(1, rate // 400), rate // 65
    pitches = []
    for start in range(0, max(1, len(audio) - frame_size + 1), hop):
        frame = audio[start:start + frame_size].astype(np.float64)
        if len(frame) < frame_size or float(np.sqrt(np.mean(frame * frame))) < rms_gate:
            continue
        frame = frame - np.mean(frame)
        if float(np.dot(frame, frame)) <= 1e-9:
            continue
        # the autocorrelation through the FFT: the same values as np.correlate, a few times faster on long frames
        n = 1 << (2 * frame_size - 1).bit_length()
        spectrum = np.fft.rfft(frame, n)
        correlation = np.fft.irfft(spectrum * np.conj(spectrum), n)[:frame_size]
        search = correlation[min_lag:min(max_lag + 1, len(correlation))]
        if search.size == 0:
            continue
        offset = int(np.argmax(search))
        if float(search[offset] / max(correlation[0], 1e-9)) < 0.25:
            continue
        pitches.append(rate / (min_lag + offset))
    values = np.asarray(pitches, dtype=np.float64)
    return {"pitch_hz_median": float(np.median(values)) if values.size else 0.0,
            "pitch_hz_std": float(np.std(values)) if values.size else 0.0}


def delivery(audio: np.ndarray, rate: int = RATE) -> dict:
    """The packet's `delivery` values over these samples (production's dsp_features, only the keys the packet keeps)."""
    frame_size, hop = round(rate * 0.04), round(rate * 0.02)
    count = max(0, (len(audio) - frame_size) // hop + 1)
    if count:
        idx = np.arange(frame_size)[None, :] + hop * np.arange(count)[:, None]
        rms = np.sqrt(np.mean(audio[idx] ** 2, axis=1))
    else:
        rms = np.asarray([], dtype=np.float64)
    rms_db = 20 * np.log10(np.maximum(rms, 1e-8)) if rms.size else np.asarray([], dtype=np.float64)
    median_db = float(np.median(rms_db)) if rms_db.size else -160.0
    silence_gate_db = max(-55.0, median_db - 18.0)
    thirds = np.array_split(rms_db, 3) if rms_db.size else [np.asarray([])] * 3
    peak_index = int(np.argmax(rms_db)) if rms_db.size else 0
    out = {
        "silence_ratio": float(np.mean(rms_db <= silence_gate_db)) if rms_db.size else 1.0,
        "rms_dynamic_range_db": _percentile(rms_db, 90) - _percentile(rms_db, 10) if rms_db.size else 0.0,
        "energy_begin_db": float(np.mean(thirds[0])) if thirds[0].size else -160.0,
        "energy_middle_db": float(np.mean(thirds[1])) if thirds[1].size else -160.0,
        "energy_final_db": float(np.mean(thirds[2])) if thirds[2].size else -160.0,
        "energy_peak_position": peak_index / max(1, len(rms_db) - 1),
    }
    rms_gate = max(10 ** (-55 / 20), float(np.median(rms)) * 0.25 if rms.size else 0.0)
    out.update(_pitch(audio, rate, rms_gate))
    return {k: round(v, 3) for k, v in out.items()}


def pauses(spans_ms: list[tuple[int, int]], window_ms: int) -> list[list[int]]:
    """Gaps of at least PAUSE_MIN_MS with no recognised word, inside [0, window_ms]; the edges count as speech-free too."""
    out, cursor = [], 0
    for a, b in sorted(spans_ms):
        a, b = max(0, a), min(window_ms, b)
        if a - cursor >= PAUSE_MIN_MS:
            out.append([cursor, a])
        cursor = max(cursor, b)
    if window_ms - cursor >= PAUSE_MIN_MS:
        out.append([cursor, window_ms])
    return out
