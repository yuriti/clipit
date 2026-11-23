"""«Settings → Speech» (stage 20): every speech model SMTV can use, which one each language takes, and what is on disk.

Models:
  gigaam    GigaAM-v3 (Russian), on this computer, onnx-asr.
  parakeet  Parakeet-TDT v3 (25 European languages), on this computer, onnx-asr.
  whisper   Whisper large-v3-turbo (~99 languages), on this computer, faster-whisper: NVIDIA card or the processor
            (on a Mac only the processor: slower).
  groq      Whisper large-v3-turbo at Groq, by the person's own Groq key (a provider in «Settings → Providers»).
  openai    OpenAI whisper-1, by the person's own OpenAI key. The sound leaves the computer for both cloud ones.

Which model a language takes: the person's choice for it (`tools.smtv.speech.<language>`, or `*` for every language without
a row of its own) while that model knows the language; otherwise the default — Russian → GigaAM, Parakeet's 25 languages
→ Parakeet, any other → Whisper on this computer. Models live only in `SMTV_HOME/models`; nothing needs administrator
rights, and removing a model is removing its folder.
"""
from __future__ import annotations

import importlib.util
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .. import paths
from .engines import GIGAAM, PARAKEET, PARAKEET_LANGUAGES, complete, downloading_mark, folder_mb, installed as onnx_installed

# The languages Whisper was trained on (its tokenizer's list), ISO 639-1; `haw` and `yue` have no two-letter code.
WHISPER_LANGUAGES = frozenset(
    "en zh de es ru ko fr ja pt tr pl ca nl ar sv it id hi fi vi he uk el ms cs ro da hu ta no th ur hr bg lt la mi ml cy "
    "sk te fa lv bn sr az sl kn et mk br eu is hy ne mn bs kk sq sw gl mr pa si km sn yo so af oc ka be tg sd gu am yi lo "
    "uz fo ht ps tk nn mt sa lb my bo tl mg as tt haw ln ha ba jw su yue".split())
# Rows of the language table besides Russian and Parakeet's: the most asked-for others; the rest share one row («*»)
SHOWN_OTHER = ("ja", "zh", "ko", "ar", "hi", "tr", "vi", "id", "th", "he", "fa", "kk", "uz", "be", "ka", "hy", "az")
OTHERS = "*"


@dataclass(frozen=True)
class SpeechModel:
    id: str
    title: str
    where: str                    # local | cloud
    languages: frozenset          # what it transcribes
    license: str
    size_mb: int = 0              # the download (local)
    speed_x: float | None = None  # times faster than real time, by our own measurement; None: not measured
    speed_how: str = ""
    runs_on: str = ""             # local: processor / NVIDIA card
    preset: str = ""              # cloud: the provider preset whose key it uses
    price_hour: float | None = None   # cloud: US dollars per hour of sound, from the provider's price list
    words: str = "word"           # word timings: word
    package: str = ""             # a Python package it needs beyond the core's own
    folder: str = ""              # its folder in the models folder (local)
    links: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "where": self.where, "languages": len(self.languages), "license": self.license,
                "size_mb": self.size_mb, "speed_x": self.speed_x, "speed_how": self.speed_how, "runs_on": self.runs_on,
                "preset": self.preset, "price_hour": self.price_hour, "package": self.package, "links": dict(self.links)}


GIGAAM_M = SpeechModel("gigaam", "GigaAM-v3", "local", frozenset({"ru"}), "MIT", GIGAAM.size_mb, 54, "12-core desktop processor",
                       "processor; NVIDIA card with smtv-core[gpu]", folder="gigaam",
                       links={"model": "https://github.com/salute-developers/GigaAM"})
PARAKEET_M = SpeechModel("parakeet", "Parakeet-TDT v3", "local", frozenset(PARAKEET_LANGUAGES), "CC-BY-4.0 (NVIDIA)", PARAKEET.size_mb,
                         33, "12-core desktop processor", "processor; NVIDIA card with smtv-core[gpu]", folder="parakeet",
                         links={"model": "https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3"})
WHISPER_M = SpeechModel("whisper", "Whisper large-v3-turbo", "local", WHISPER_LANGUAGES, "MIT (OpenAI)", 1550, 11,
                        "Mac M3 Max, Metal; the processor alone 3×",
                        "NVIDIA card (CUDA 12), Metal on a Mac with Apple silicon (experimental), or the processor",
                        package="faster_whisper",
                        folder="whisper", links={"model": "https://huggingface.co/mobiuslabsgmbh/faster-whisper-large-v3-turbo",
                                                 "engine": "https://github.com/SYSTRAN/faster-whisper"})
GROQ_M = SpeechModel("groq", "Whisper large-v3-turbo · Groq", "cloud", WHISPER_LANGUAGES, "Groq terms of service", preset="groq",
                     price_hour=0.04, links={"price": "https://groq.com/pricing", "terms": "https://groq.com/terms-of-use"})
OPENAI_M = SpeechModel("openai", "Whisper (whisper-1) · OpenAI", "cloud", WHISPER_LANGUAGES, "OpenAI terms of use", preset="openai",
                       price_hour=0.36, links={"price": "https://openai.com/api/pricing/", "terms": "https://openai.com/policies/terms-of-use/"})
MODELS = {m.id: m for m in (GIGAAM_M, PARAKEET_M, WHISPER_M, GROQ_M, OPENAI_M)}
ONNX = {"gigaam": GIGAAM, "parakeet": PARAKEET}


def code(language: str | None) -> str:
    """'ru', 'en', 'pt'… from 'ru-RU', 'pt_BR', 'EN'. «latin» (a Latin-script language, `language.detect`) stays."""
    return (language or "").strip().lower().replace("_", "-").split("-")[0]


def default_for(language: str) -> str:
    c = code(language)
    if c == "ru":
        return "gigaam"
    if c in PARAKEET_LANGUAGES or c == "latin":
        return "parakeet"
    return "whisper"


def knows(model: SpeechModel, language: str) -> bool:
    c = code(language)
    if c == "latin":            # some Latin-script language: Parakeet and Whisper both tell which by themselves
        return model.id != "gigaam"
    return c in model.languages


def known_language(language: str) -> bool:
    c = code(language)
    return c == "latin" or c in WHISPER_LANGUAGES or c in PARAKEET_LANGUAGES


def chosen(settings) -> dict:
    """The person's choices: {language or «*»: model id}."""
    raw = ((settings.tools.get("smtv") or {}).get("speech") or {}) if settings is not None else {}
    return {k: v for k, v in raw.items() if isinstance(k, str) and v in MODELS}


def has_own_row(language: str) -> bool:
    c = code(language)
    return c == "ru" or c in PARAKEET_LANGUAGES or c in SHOWN_OTHER


def model_for(language: str, settings=None) -> tuple[SpeechModel, str]:
    """(model, source) for a language: «own» — the person's choice, «default» — the rule above."""
    c = code(language)
    own = chosen(settings)
    pick = own.get("en" if c == "latin" else c)
    if pick is None and not has_own_row(c) and c != "latin":
        pick = own.get(OTHERS)
    if pick and knows(MODELS[pick], c):
        return MODELS[pick], "own"
    return MODELS[default_for(c)], "default"


def set_choice(settings, language: str, model_id: str | None) -> None:
    """The model for a language (or «*»); None: back to the default."""
    key = OTHERS if language == OTHERS else code(language)
    if key != OTHERS and not known_language(key):
        raise ValueError(f"unknown language {language!r}")
    speech = settings.tools.setdefault("smtv", {}).setdefault("speech", {})
    if model_id is None:
        speech.pop(key, None)
        return
    model = MODELS.get(model_id)
    if model is None:
        raise ValueError(f"unknown speech model {model_id!r}")
    if key != OTHERS and not knows(model, key):
        raise ValueError(f"{model.title} does not transcribe {key}")
    if key == OTHERS and model.id in ("gigaam", "parakeet"):
        raise ValueError(f"{model.title} does not transcribe the other languages")
    speech[key] = model.id


# --- on this computer ------------------------------------------------------------------------------------------

def folder(model: SpeechModel, models_dir: Path | None = None) -> Path:
    return (models_dir or paths.models_dir()) / model.folder


def package_ready(model: SpeechModel) -> bool:
    return not model.package or importlib.util.find_spec(model.package) is not None


def is_installed(model: SpeechModel, models_dir: Path | None = None) -> bool:
    if model.where == "cloud":
        return True
    if model.id in ONNX:
        return onnx_installed(ONNX[model.id], models_dir)
    return complete(folder(model, models_dir), "model.bin", "config.json")


def on_disk_mb(model: SpeechModel, models_dir: Path | None = None) -> int:
    return folder_mb(folder(model, models_dir)) if model.where == "local" else 0


def remove(model: SpeechModel, models_dir: Path | None = None) -> bool:
    """Deletes the model's folder; True when there was one. Cloud models have nothing here."""
    if model.where != "local":
        raise ValueError(f"{model.title} is not on this computer")
    f = folder(model, models_dir)
    base = (models_dir or paths.models_dir()).resolve()
    downloading_mark(f).unlink(missing_ok=True)
    if f.is_symlink():                      # a link to a model kept elsewhere: only the link goes, never what it points to
        f.unlink()
        return True
    if not f.exists():
        return False
    if f.resolve().parent != base:
        raise ValueError(f"{f} is not inside {base}")
    shutil.rmtree(f)
    return True


# --- the recognizer a language gets ----------------------------------------------------------------------------

def cloud_providers(model: SpeechModel, settings) -> list:
    """The person's switched-on providers of the model's service (OpenAI or Groq), the first one with a key first."""
    from ..settings import OPENAI, get_secret
    found = []
    for p in settings.enabled() if settings is not None else []:
        if p.kind != OPENAI:
            continue
        url = p.base_url or ""
        if p.preset == model.preset or (model.preset == "openai" and "api.openai.com" in url) or \
                (model.preset == "groq" and "api.groq.com" in url):
            try:
                has = bool(get_secret(p.key_name() or ""))
            except Exception:  # noqa: BLE001 — a locked keychain: this provider has no usable key now
                has = False
            found.append((p, has))
    return [p for p, has in sorted(found, key=lambda x: not x[1]) if has] + [p for p, has in found if not has]


def cloud_key(model: SpeechModel, settings) -> str:
    """The key of the first provider of the model's service that has one; an error with words when there is none."""
    from ..llm.providers import ProviderError
    from ..settings import get_secret
    service = "Groq" if model.preset == "groq" else "OpenAI"
    for p in cloud_providers(model, settings):
        try:
            key = get_secret(p.key_name() or "")
        except Exception as e:  # noqa: BLE001
            raise ProviderError(f"the key of {p.name or p.id} cannot be read ({type(e).__name__})") from e
        if key:
            return key
    raise ProviderError(f"{model.title} needs your {service} key: add a {service} provider in «Settings → Providers»")


def recognizer(model: SpeechModel, language: str, settings=None, models_dir: Path | None = None):
    """The recognizer of a model for a language, not loaded yet (`load()` downloads a local model that is not here)."""
    if model.id in ONNX:
        from .engines import Recognizer
        return Recognizer(ONNX[model.id], models_dir)
    if model.id == "whisper":
        if not package_ready(model):
            raise RuntimeError("Whisper on this computer needs the faster-whisper package: "
                               "reinstall SMTV with vodcut, or choose another model in «Settings → Speech»")
        from .whisper import WhisperRecognizer
        return WhisperRecognizer(code(language), models_dir)
    from .cloud import CloudRecognizer
    return CloudRecognizer(model.id, lambda: cloud_key(model, settings), code(language))
