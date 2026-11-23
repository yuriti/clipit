"""Whisper large-v3-turbo on this computer through faster-whisper (stage 20).

Why faster-whisper and not onnx-asr, which runs GigaAM and Parakeet: onnx-asr 0.12 decodes Whisper with
`<|notimestamps|>`, so it gives text without word timings, and clips and captions need the time of every word.
faster-whisper (CTranslate2) gives word timings, runs on an NVIDIA card (CUDA 12) or on the processor (int8), and
is MIT like the model. On a Mac with Apple silicon it runs on Metal (CTranslate2's MPS backend, still experimental there:
any failure falls back to the processor); measured 21.11 on an M3 Max, a minute of Russian speech: Metal 11× real time,
the processor 3×, the same 135 words.

The recording is read in windows of 20 minutes (a 6-hour stream as one array would take 1.4 GB of memory), with a few
seconds of overlap; the windows are stitched like the other models' (`words.stitch_windows`).
"""
from __future__ import annotations

import platform
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .. import paths
from .engines import folder_mb, read_wav, wav_duration
from .words import plan_windows, stitch_windows

REPO = "mobiuslabsgmbh/faster-whisper-large-v3-turbo"     # what faster-whisper itself calls «large-v3-turbo»
GRID_S, PAD_S = 1200.0, 3.0


@dataclass(frozen=True)
class WhisperEngine:
    name: str = "whisper"
    size_mb: int = 1550


ENGINE = WhisperEngine()


def model_dir(models_dir: Path | None = None) -> Path:
    return (models_dir or paths.models_dir()) / "whisper"


def installed(models_dir: Path | None = None) -> bool:
    from .engines import complete
    return complete(model_dir(models_dir), "model.bin", "config.json")


def download(models_dir: Path | None = None, progress: Callable[[int, int], None] | None = None, every_s: float = 2.0) -> Path:
    """Fetches the model into the models folder (about 1.5 GB), telling `progress(mb_done, mb_total)`."""
    from faster_whisper.utils import download_model
    from .engines import downloading_mark
    target = model_dir(models_dir)
    target.mkdir(parents=True, exist_ok=True)
    mark = downloading_mark(target)
    mark.write_text("", encoding="utf-8")     # stays if the download stops half way: `installed` then says no
    stop = threading.Event()

    def watch():
        while not stop.wait(every_s):
            if progress:
                progress(min(folder_mb(target), ENGINE.size_mb), ENGINE.size_mb)

    t = threading.Thread(target=watch, daemon=True)
    t.start()
    try:
        download_model(REPO, output_dir=str(target))
    finally:
        stop.set()
        t.join(timeout=5)
    mark.unlink(missing_ok=True)
    if progress:
        progress(ENGINE.size_mb, ENGINE.size_mb)
    return target


def device() -> tuple[str, str]:
    """(device, compute type): the NVIDIA card in float16 when CTranslate2 sees one; Metal on a Mac with Apple silicon;
    else the processor in int8."""
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda", "float16"
    except Exception:  # noqa: BLE001 — no CUDA libraries: the processor
        pass
    if sys.platform == "darwin" and platform.machine() == "arm64":
        return "mps", "float16"
    return "cpu", "int8"


def detect_language(wav: Path, models_dir: Path | None = None) -> str | None:
    """The language of a recording by Whisper itself (three 30-second samples, the most frequent answer), for a computer
    that has only Whisper: no GigaAM or Parakeet is downloaded just to tell the language. None when nothing is clear."""
    from collections import Counter
    rec = WhisperRecognizer(None, models_dir).load()
    duration = wav_duration(wav)
    votes = Counter()
    for f in (0.15, 0.5, 0.85):
        start = max(0.0, min(duration - 30.0, duration * f))
        found, prob, _all = rec.model.detect_language(audio=read_wav(wav, start, start + 30.0), vad_filter=True)
        if found and prob >= 0.5:
            votes[found] += 1
    return votes.most_common(1)[0][0] if votes else None


def words_of(segments, offset: float) -> list[dict]:
    """faster-whisper's segments → our words ({"word": " text", "start", "end", "probability"}), shifted by `offset`."""
    out = []
    for seg in segments:
        for w in getattr(seg, "words", None) or []:
            text = (w.word or "").strip()
            if not text:
                continue
            start = round(float(w.start) + offset, 3)
            out.append({"word": " " + text, "start": start, "end": round(max(float(w.end) + offset, start + 0.02), 3),
                        "probability": round(float(w.probability), 5)})
    return out


class WhisperRecognizer:
    """Same use as `engines.Recognizer`: load(), then the pipeline calls transcribe_file()."""

    def __init__(self, language: str | None = None, models_dir: Path | None = None):
        self.engine = ENGINE
        self.language = language if language and language != "latin" else None     # None: Whisper tells by itself
        self.dir = model_dir(models_dir)
        self.model = None
        self.device = ""

    def load(self) -> "WhisperRecognizer":
        from faster_whisper import WhisperModel
        if not installed(self.dir.parent):
            download(self.dir.parent)
        dev, compute = device()
        try:
            self.model = WhisperModel(str(self.dir), device=dev, compute_type=compute)
        except Exception as e:  # noqa: BLE001 — a card without the CUDA 12 libraries, Metal refused: the processor
            if dev == "cpu":
                raise
            print(f"whisper: {dev} did not start ({type(e).__name__}: {str(e)[:200]}); using the processor", file=sys.stderr)
            dev = "cpu"
            self.model = WhisperModel(str(self.dir), device="cpu", compute_type="int8")
        self.device = dev
        return self

    def _to_processor(self, why: Exception) -> None:
        from faster_whisper import WhisperModel
        print(f"whisper: {self.device} failed while transcribing ({type(why).__name__}: {str(why)[:200]}); "
              "going on with the processor", file=sys.stderr)
        self.model = WhisperModel(str(self.dir), device="cpu", compute_type="int8")
        self.device = "cpu"

    def _window(self, audio, offset: float, end: float, total: tuple[float, float], progress) -> list[dict]:
        segments, _info = self.model.transcribe(audio, language=self.language, word_timestamps=True, vad_filter=True,
                                                condition_on_previous_text=False, beam_size=5)
        words = []
        for seg in segments:            # a generator: the window is transcribed while it is read
            words += words_of([seg], offset)
            if progress:
                progress(min(offset + float(seg.end), end) - total[0], total[1] - total[0])
        return words

    def transcribe_file(self, wav: Path, start_s: float = 0.0, end_s: float | None = None,
                        progress: Callable[[float, float], None] | None = None) -> list[dict]:
        end_s = wav_duration(wav) if end_s is None else end_s
        windows = plan_windows(start_s, end_s, GRID_S, PAD_S)
        per_window = []
        for w in windows:
            audio = read_wav(wav, w["start"], w["end"])
            try:
                words = self._window(audio, w["start"], w["end"], (start_s, end_s), progress)
            except Exception as e:  # noqa: BLE001 — the card or Metal failed mid-way: this window again on the processor
                if self.device == "cpu":
                    raise
                self._to_processor(e)
                words = self._window(audio, w["start"], w["end"], (start_s, end_s), progress)
            per_window.append(words)
        return stitch_windows(windows, per_window)
