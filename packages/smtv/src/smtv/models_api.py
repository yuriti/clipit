"""The window's side of stage 20: local model servers, Ollama's models, and «Settings → Speech».

- «Find on this computer»: the usual addresses of Ollama, LM Studio, vLLM and llama.cpp asked at once (`presets.discover`).
- Ollama: its installed models (size, «reads images», window), the recommended ones of `models.json` with their size,
  «Download» (`/api/pull`, in the background, with progress) and «Remove» (`/api/delete`).
- Speech: every model (where it runs, languages, licence, size, speed, on disk or not), the model of each language, and
  «Download» / «Remove» of the local ones (the models folder only).

Downloads run in background threads, one per model; the window asks for their progress while one runs. Nothing here
installs a program or needs administrator rights.
"""
from __future__ import annotations

import re
import threading
import time
from typing import Callable

from smtv_core import agents as agents_mod
from smtv_core import presets
from smtv_core.asr import catalog as speech
from smtv_core.llm import ollama
from smtv_core.settings import OPENAI, Settings, get_secret

MODEL_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/+-]{0,159}$")
SPEECH_LANGUAGES = ["ru", *sorted(speech.PARAKEET_LANGUAGES - {"ru"}), *speech.SHOWN_OTHER]


class Refused(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


class Downloads:
    """Background downloads, one per key: {"status": running|done|error|cancelled, "done", "total", "unit", "detail"}.
    A finished one is kept a few minutes for the window to show how it ended."""

    KEEP_S = 300.0

    def __init__(self, on_change: Callable[[], None] | None = None):
        self.items: dict[str, dict] = {}
        self.stops: dict[str, threading.Event] = {}
        self.lock = threading.Lock()
        self.on_change = on_change or (lambda: None)

    def running(self, key: str) -> bool:
        with self.lock:
            return (self.items.get(key) or {}).get("status") == "running"

    def start(self, key: str, work: Callable[[Callable[..., None], threading.Event], None], unit: str = "mb",
              done_hook: Callable[[], None] | None = None) -> dict:
        with self.lock:
            if (self.items.get(key) or {}).get("status") == "running":
                raise Refused(409, "downloading", "it is being downloaded already")
            self._forget_old()
            stop = threading.Event()
            self.stops[key] = stop
            self.items[key] = {"status": "running", "done": 0, "total": 0, "unit": unit, "detail": "", "at": time.time()}

        def progress(done: int, total: int, detail: str = "") -> None:
            with self.lock:
                item = self.items.get(key)
                if item and item["status"] == "running":
                    item.update(done=int(done), total=int(total), detail=detail[:120])

        def run() -> None:
            status, detail = "done", ""
            try:
                work(progress, stop)        # finished without an error: done, even if «cancel» came too late to stop it
            except Exception as e:  # noqa: BLE001 — the reason is shown in the window (no key is involved in a download)
                status, detail = ("cancelled", "") if stop.is_set() else ("error", f"{type(e).__name__}: {e}"[:400])
                print(f"download {key}: {status} {detail}")
            with self.lock:
                self.items[key].update(status=status, detail=detail, at=time.time())
                self.stops.pop(key, None)
                self._forget_old()
            # what follows must never leave the thread dead with the window thinking it still runs (C12)
            for hook in (done_hook, self.on_change):
                if hook is None:
                    continue
                try:
                    hook()
                except Exception as e:  # noqa: BLE001 — the download itself has ended and says so
                    print(f"download {key}: after the end: {type(e).__name__}: {e}")

        threading.Thread(target=run, name=f"download {key}", daemon=True).start()
        return self.state(key)

    def _forget_old(self) -> None:
        """Finished downloads older than KEEP_S go (C22): not only when their own key is read."""
        now = time.time()
        for k in [k for k, i in self.items.items() if i["status"] != "running" and now - i["at"] > self.KEEP_S]:
            self.items.pop(k, None)

    def cancel(self, key: str) -> dict:
        with self.lock:
            stop = self.stops.get(key)
        if stop:
            stop.set()
        return self.state(key)

    def state(self, key: str) -> dict | None:
        with self.lock:
            item = self.items.get(key)
            if item and item["status"] != "running" and time.time() - item["at"] > self.KEEP_S:
                self.items.pop(key, None)
                return None
            return dict(item) if item else None

    def prefixed(self, prefix: str) -> dict:
        with self.lock:
            keys = [k for k in self.items if k.startswith(prefix)]
        return {k[len(prefix):]: s for k in keys if (s := self.state(k))}


# --- local servers and Ollama ----------------------------------------------------------------------------------

def discover(settings: Settings) -> dict:
    """The local servers found at their usual addresses, and which of them is on the list of providers already."""
    rows = []
    for found in presets.discover():
        added = next((p.id for p in settings.providers if p.kind == OPENAI and p.preset == found["preset"]), None)
        rows.append({**found, "label": presets.BY_ID[found["preset"]].label, "added": added,
                     "install_url": presets.BY_ID[found["preset"]].key_url, "models": found["models"][:50],
                     "count": len(found["models"])})
    return {"servers": rows}


def ollama_state(p, downloads: Downloads) -> dict:
    """Installed models and the recommended ones for an Ollama provider; a server that does not answer says why."""
    table = agents_mod.known_models("ollama")
    try:
        installed = ollama.models(p.base_url)
        running, detail = True, ""
    except ollama.OllamaError as e:
        installed, running, detail = [], False, str(e)[:300]
    have = {m["id"] for m in installed} | {m["id"].removesuffix(":latest") for m in installed}
    for m in installed:
        info = table.get(m["id"]) or {}
        m["recommended"] = m["id"] in table
        if m["images"] is None and "images" in info:
            m["images"] = info["images"]
    recommended = [{"id": mid, "label": info.get("label") or mid, "size_gb": info.get("size_gb"), "vram_gb": info.get("vram_gb"),
                    "images": bool(info.get("images")), "level": info.get("level"), "installed": mid in have,
                    "for": sorted({a for a, cols in agents_mod.table().get("agents", {}).items()
                                   if (cols.get("ollama") or {}).get("model") == mid})}
                   for mid, info in table.items()]
    return {"provider": p.id, "base_url": p.base_url, "running": running, "detail": detail, "installed": installed,
            "recommended": recommended, "pulls": downloads.prefixed(f"ollama:{p.id}:"), "install_url": "https://ollama.com/download"}


def ollama_pull(p, model: str, downloads: Downloads, done_hook: Callable[[], None]) -> dict:
    if not MODEL_NAME.match(model or ""):
        raise Refused(400, "bad_model", "model: its name as `ollama pull` takes it, e.g. qwen3:14b")

    def work(progress, stop):
        ollama.pull(p.base_url, model, lambda e: progress(e["completed"], e["total"], e["status"]), stop)

    return downloads.start(f"ollama:{p.id}:{model}", work, unit="bytes", done_hook=done_hook)


def ollama_delete(p, model: str, downloads: Downloads) -> None:
    if not MODEL_NAME.match(model or ""):
        raise Refused(400, "bad_model", "model: its name as Ollama lists it")
    if downloads.running(f"ollama:{p.id}:{model}"):
        raise Refused(409, "downloading", "it is being downloaded: cancel the download first")
    try:
        ollama.delete(p.base_url, model)
    except ollama.OllamaError as e:
        raise Refused(502, "ollama", str(e)[:300]) from None


# --- «Settings → Speech» ----------------------------------------------------------------------------------------

def _cloud_status(model, settings: Settings) -> dict:
    found = speech.cloud_providers(model, settings)
    if not found:
        return {"provider": None, "provider_name": "", "key": False}
    p = found[0]
    try:
        key = bool(get_secret(p.key_name() or ""))
    except Exception:  # noqa: BLE001 — a locked keychain: shown as no key
        key = False
    return {"provider": p.id, "provider_name": p.name or p.id, "key": key}


def speech_state(settings: Settings, downloads: Downloads, busy: Callable[[], bool] = lambda: False) -> dict:
    models = []
    for m in speech.MODELS.values():
        row = {**m.as_dict(), "installed": speech.is_installed(m), "package": speech.package_available(m),
               "package_mb": speech.package_mb(m),
               "on_disk_mb": speech.on_disk_mb(m), "download": downloads.state(f"speech:{m.id}")}
        if m.where == "cloud":
            row.update(_cloud_status(m, settings))
        models.append(row)
    own = speech.chosen(settings)
    langs = []
    for code in SPEECH_LANGUAGES:
        model, source = speech.model_for(code, settings)
        langs.append({"code": code, "model": model.id, "source": source, "default": speech.default_for(code),
                      "choices": [m.id for m in speech.MODELS.values() if speech.knows(m, code)]})
    other_default = "whisper"
    langs.append({"code": speech.OTHERS, "model": own.get(speech.OTHERS, other_default), "source": "own" if speech.OTHERS in own else "default",
                  "default": other_default, "choices": [m.id for m in speech.MODELS.values() if m.id not in ("gigaam", "parakeet")],
                  "count": len(speech.WHISPER_LANGUAGES - set(SPEECH_LANGUAGES))})
    return {"models": models, "languages": langs, "folder": str(speech.folder(speech.WHISPER_M).parent), "busy": busy()}


def speech_download(model_id: str, downloads: Downloads, busy: bool = False) -> dict:
    model = speech.MODELS.get(model_id)
    if model is None or model.where != "local":
        raise Refused(404, "no_model", f"no speech model {model_id} to download")
    if not speech.package_available(model):
        raise Refused(400, "no_package", "this model needs the faster-whisper package: reinstall Clip It! with vodcut")
    if speech.is_installed(model):
        raise Refused(409, "installed", "it is on this computer already")
    if busy:      # a request may be downloading the same model into the same folder right now
        raise Refused(409, "busy", "a request is running: download the model when it ends, or let the request download it")

    def work(progress, stop):
        if model.id in speech.ONNX:
            from smtv_core.asr.engines import load_watched
            load_watched(speech.ONNX[model.id], lambda done, total: progress(done, total))
        else:
            from smtv_core.asr import whisper
            speech.ensure_package(model, lambda done, total: progress(done, total))   # the app's Whisper engine first
            whisper.download(progress=lambda done, total: progress(done, total))

    return downloads.start(f"speech:{model.id}", work, unit="mb")


def speech_remove(model_id: str, downloads: Downloads, busy: bool) -> None:
    model = speech.MODELS.get(model_id)
    if model is None or model.where != "local":
        raise Refused(404, "no_model", f"no speech model {model_id} on this computer")
    if downloads.running(f"speech:{model.id}"):
        raise Refused(409, "downloading", "it is being downloaded: wait for the download to end")
    if busy:
        raise Refused(409, "busy", "a request is running: remove the model when it ends")
    try:
        speech.remove(model)
    except (OSError, ValueError) as e:
        raise Refused(500, "not_removed", f"{type(e).__name__}: {e}"[:300]) from None


def speech_choose(settings: Settings, body: dict) -> None:
    language, model = body.get("language"), body.get("model")
    if not isinstance(language, str) or not (language == speech.OTHERS or re.match(r"^[a-z]{2,3}$", language)):
        raise Refused(400, "bad_language", "language: a two-letter code or *")
    if model is not None and not isinstance(model, str):
        raise Refused(400, "bad_model", "model: a speech model id, or null for the default")
    try:
        speech.set_choice(settings, language, model)
    except ValueError as e:
        raise Refused(400, "bad_choice", str(e)) from None
