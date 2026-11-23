"""Speech recognition models through onnx-asr: GigaAM-v3 for Russian, Parakeet-TDT v3 for 25 European languages.

Both run on the processor; with an NVIDIA card and onnxruntime-gpu installed (smtv-core[gpu]) the encoder runs on it.
Models are downloaded once into the models folder (GigaAM about 850 MB, Parakeet about 2.5 GB).
Measured on a 12-core desktop processor: GigaAM ~54x real time, Parakeet ~33x.
"""
from __future__ import annotations

import shutil
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .. import paths
from .words import plan_windows, segments, stitch_windows, with_ids, words_marker_tokens, words_space_tokens

SR = 16000

# Languages Parakeet-TDT v3 transcribes (ISO 639-1).
PARAKEET_LANGUAGES = {"bg", "hr", "cs", "da", "nl", "en", "et", "fi", "fr", "de", "el", "hu", "it", "lv", "lt", "mt",
                      "pl", "pt", "ro", "sk", "sl", "es", "sv", "ru", "uk"}


@dataclass(frozen=True)
class Engine:
    name: str
    onnx_model: str
    grid_s: float
    pad_s: float
    frame_s: float            # fallback when the model does not report its frame step
    to_words: Callable
    batch: int                # windows per recognize() call
    license: str
    size_mb: int = 0          # the downloaded model folder, for the download's progress


GIGAAM = Engine("gigaam", "gigaam-v3-e2e-rnnt", 18.0, 3.0, 0.04, words_space_tokens, 8, "MIT", 852)
PARAKEET = Engine("parakeet", "nemo-parakeet-tdt-0.6b-v3", 54.0, 3.0, 0.08, words_marker_tokens, 2, "CC-BY-4.0 (NVIDIA)", 2432)
ENGINES = {e.name: e for e in (GIGAAM, PARAKEET)}


def downloading_mark(folder: Path) -> Path:
    """A file beside a model folder that is there while the model downloads into it.

    It goes away only once the model has loaded: a download stopped half way (SMTV closed, power cut) leaves it, and the
    folder with an encoder but no decoder is then never taken for a model on this computer. Beside, not inside: onnx-asr
    downloads only into a folder that does not exist yet.
    """
    return folder.with_name(folder.name + ".downloading")


def complete(folder: Path, *must: str) -> bool:
    """A model folder holds a finished download: no download mark beside it, and the named files (or any `*.onnx`)."""
    if not folder.is_dir() or downloading_mark(folder).exists():
        return False
    return all((folder / f).is_file() for f in must) if must else any(folder.glob("*.onnx"))


def installed(engine: Engine, models_dir: Path | None = None) -> bool:
    """Whether the model is on this computer already: a finished download (`complete`)."""
    return complete((models_dir or paths.models_dir()) / engine.name)


def engine_for(language: str) -> Engine:
    """GigaAM for Russian, Parakeet for every other language it knows."""
    if language == "ru":
        return GIGAAM
    if language in PARAKEET_LANGUAGES or language == "latin":
        return PARAKEET
    raise ValueError(f"no speech model for language {language!r}; supported: {', '.join(sorted(PARAKEET_LANGUAGES))}")


def providers() -> list[str]:
    import onnxruntime as rt
    available = rt.get_available_providers()
    return (["CUDAExecutionProvider"] if "CUDAExecutionProvider" in available else []) + ["CPUExecutionProvider"]


class Recognizer:
    """A loaded model. load() downloads it on first use."""

    def __init__(self, engine: Engine, models_dir: Path | None = None):
        self.engine = engine
        self.dir = (models_dir or paths.models_dir()) / engine.name
        self.model = None
        self.frame_s = engine.frame_s

    def load(self) -> "Recognizer":
        import onnx_asr
        # onnx-asr takes an existing folder for a downloaded model and then never downloads: the folder must not be
        # made beforehand, and a folder left without the model (an interrupted or never started download) goes first.
        mark = downloading_mark(self.dir)
        if not installed(self.engine, self.dir.parent):
            if self.dir.is_dir():
                shutil.rmtree(self.dir)
            self.dir.parent.mkdir(parents=True, exist_ok=True)
            mark.write_text("", encoding="utf-8")
        self.model = onnx_asr.load_model(self.engine.onnx_model, self.dir, providers=providers()).with_timestamps()
        mark.unlink(missing_ok=True)
        asr = getattr(self.model, "asr", None)
        step, factor = getattr(asr, "window_step", None), getattr(asr, "_subsampling_factor", None)
        if step and factor:
            self.frame_s = step * factor
        return self

    def recognize(self, clips: list, offsets: list[float]) -> list[list[dict]]:
        results = self.model.recognize(clips)
        return [self.engine.to_words(r.tokens or [], r.timestamps or [], getattr(r, "logprobs", None), off, self.frame_s)
                for r, off in zip(results, offsets)]


def wav_duration(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def read_wav(path: Path, start_s: float, end_s: float):
    """Float32 mono samples of [start_s, end_s) from a 16 kHz 16-bit mono WAV, without loading the whole file."""
    import numpy as np
    with wave.open(str(path)) as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (SR, 1, 2):
            raise ValueError(f"{path} must be 16 kHz mono 16-bit")
        a = int(start_s * SR)
        w.setpos(min(a, w.getnframes()))
        raw = w.readframes(max(0, int(end_s * SR) - a))
    return np.frombuffer(raw, dtype="<i2").astype("float32") / 32768.0


def transcribe(wav: Path, recognizer: Recognizer, start_s: float = 0.0, end_s: float | None = None,
               progress: Callable[[float, float], None] | None = None) -> list[dict]:
    """Segments with words and ids for [start_s, end_s) of the WAV. A recognizer that reads the file its own way
    (Whisper here or in the cloud, stage 20) gives the words itself."""
    end_s = wav_duration(wav) if end_s is None else end_s
    own = getattr(recognizer, "transcribe_file", None)
    if own is not None:
        return with_ids(segments(own(wav, start_s, end_s, progress)))
    e = recognizer.engine
    windows = plan_windows(start_s, end_s, e.grid_s, e.pad_s)
    per_window: list[list[dict]] = []
    for i in range(0, len(windows), e.batch):
        group = windows[i:i + e.batch]
        clips = [read_wav(wav, w["start"], w["end"]) for w in group]
        per_window += recognizer.recognize(clips, [w["start"] for w in group])
        if progress:
            progress(group[-1]["end"] - start_s, end_s - start_s)
    return with_ids(segments(stitch_windows(windows, per_window)))


def folder_mb(folder: Path) -> int:
    """How much of a model is on disk (its folder, the download's own cache inside it included)."""
    if not folder.is_dir():
        return 0
    return sum(f.stat().st_size for f in folder.rglob("*") if f.is_file()) // (1024 * 1024)


def load_watched(engine: Engine, progress: Callable[[int, int], None] | None = None, models_dir: Path | None = None,
                 every_s: float = 2.0) -> Recognizer:
    """Recognizer(engine).load(), telling `progress(mb_done, mb_total)` while a model that is not here yet downloads."""
    import threading
    rec = Recognizer(engine, models_dir)
    if progress is None or installed(engine, models_dir):
        return rec.load()
    stop = threading.Event()

    def watch():
        while not stop.wait(every_s):
            progress(min(folder_mb(rec.dir), engine.size_mb), engine.size_mb)

    t = threading.Thread(target=watch, daemon=True)
    t.start()
    try:
        rec.load()
    finally:
        stop.set()
        t.join(timeout=5)
    progress(engine.size_mb, engine.size_mb)
    return rec
