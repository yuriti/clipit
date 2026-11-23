"""Ollama through its own API (stage 20), not its OpenAI-compatible one.

Why: Ollama gives every model a small context window (2–8 thousand tokens, by version) and silently cuts a longer prompt
from the start; the OpenAI-compatible path cannot change it. A transcript of an hour of a stream is tens of thousands of
tokens, so the cut would leave the model a few minutes of the stream without a word of warning. Here every call sets
`options.num_ctx` by the length of its own prompt (`num_ctx`), and a prompt longer than the model's own window is an
error, never a cut.

Also here: the list of models with «reads images» (`/api/tags` + `/api/show`), downloading (`/api/pull`, with progress)
and removing (`/api/delete`) a model. Ollama itself is installed by the person; SMTV never installs or starts it.
"""
from __future__ import annotations

import json
import math
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

def _default_url() -> str:
    from ..presets import LOCAL_HOST      # 127.0.0.1, or host.docker.internal in Docker (stage 21)
    return f"http://{LOCAL_HOST}:11434"


DEFAULT_URL = _default_url()
CHARS_PER_TOKEN = 2.5        # Cyrillic text in Qwen/Gemma tokenizers: ~2.5–3 characters a token; English ~4. Counted low on purpose
IMAGE_TOKENS = 1100          # one frame (Qwen-VL at 540 px is under a thousand)
ANSWER_TOKENS = 8192         # room for the answer (and a thinking model's thinking)
MIN_CTX, STEP_CTX, MAX_CTX = 8192, 4096, 262144

_shown: dict[tuple[str, str], dict] = {}
_shown_lock = threading.Lock()


class OllamaError(Exception):
    pass


def root(base_url: str) -> str:
    """The server's own address: the OpenAI-compatible «…/v1» of a hand-typed address goes."""
    url = (base_url or DEFAULT_URL).rstrip("/")
    return url[:-3] if url.endswith("/v1") else url


def num_ctx(prompt: str, images: int = 0, limit: int | None = None) -> int:
    """The context window one call needs: the prompt's tokens (counted high), its frames and room for the answer, rounded
    up to a step so the server reuses a loaded model for calls of a similar size. At most the model's own window
    (`limit`); a prompt that does not fit even there is an error (`OllamaError`), never a silent cut."""
    frames = images * IMAGE_TOKENS
    need = math.ceil(len(prompt) / CHARS_PER_TOKEN) + frames + ANSWER_TOKENS
    ctx = max(MIN_CTX, math.ceil(need / STEP_CTX) * STEP_CTX)
    cap = min(limit or MAX_CTX, MAX_CTX)
    surely = math.ceil(len(prompt) / 3) + frames      # a low count (Cyrillic is ~2.5, English ~4): the answer's own count checks the rest
    if surely + 1024 > cap:
        raise OllamaError(f"the prompt (at least {surely} tokens) does not fit the model's window ({cap} tokens): "
                          "choose a model with a larger window, or another provider for this agent")
    return min(ctx, cap)


def _request(method: str, url: str, body: dict | None, timeout: float):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"} if data else {})
    return urllib.request.urlopen(req, timeout=timeout)


def _json(method: str, url: str, body: dict | None = None, timeout: float = 10) -> dict:
    try:
        with _request(method, url, body, timeout) as r:
            text = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        try:
            detail = json.loads(detail).get("error") or detail
        except (ValueError, AttributeError):
            pass
        raise OllamaError(f"Ollama: HTTP {e.code}: {detail}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise OllamaError(f"Ollama is not running at {url.split('/api/')[0]} ({getattr(e, 'reason', e)}): "
                          "start it, or install it from ollama.com") from e
    try:
        return json.loads(text or "{}")
    except ValueError as e:
        raise OllamaError("the answer is not JSON: is this the address of Ollama?") from e


def show(base_url: str, model: str, timeout: float = 10) -> dict:
    """{"images": bool, "context": int | None, "thinking": bool} of an installed model, kept for this process."""
    key = (root(base_url), model)
    with _shown_lock:
        if key in _shown:
            return _shown[key]
    reply = _json("POST", f"{root(base_url)}/api/show", {"model": model}, timeout)
    caps = reply.get("capabilities") or []
    context = None
    for k, v in (reply.get("model_info") or {}).items():
        if k.endswith(".context_length") and isinstance(v, int):
            context = v
    # an older Ollama has no capabilities: a projector (clip) in the model's families means it reads images
    families = (reply.get("details") or {}).get("families") or []
    info = {"images": "vision" in caps or (not caps and "clip" in families), "context": context, "thinking": "thinking" in caps}
    if context is not None:          # an answer without the window is asked again next time
        with _shown_lock:
            _shown[key] = info
    return info


def models(base_url: str, timeout: float = 10, details: bool = True) -> list[dict]:
    """Installed models: {"id", "size_bytes", "params", "quant", "images", "context"}."""
    reply = _json("GET", f"{root(base_url)}/api/tags", None, timeout)
    out = []
    for row in reply.get("models") or []:
        if not isinstance(row, dict) or not isinstance(row.get("name"), str):
            continue
        d = row.get("details") or {}
        item = {"id": row["name"], "size_bytes": int(row.get("size") or 0), "params": d.get("parameter_size") or "",
                "quant": d.get("quantization_level") or "", "images": None, "context": None}
        if details:
            try:
                item.update({k: v for k, v in show(base_url, row["name"], timeout).items() if k in ("images", "context")})
            except OllamaError:
                pass      # the list stays; this one model is shown without «reads images»
        out.append(item)
    return sorted(out, key=lambda m: m["id"])


def delete(base_url: str, model: str, timeout: float = 30) -> None:
    _json("DELETE", f"{root(base_url)}/api/delete", {"model": model}, timeout)
    with _shown_lock:
        _shown.pop((root(base_url), model), None)


def pull(base_url: str, model: str, progress: Callable[[dict], None] | None = None, stop: threading.Event | None = None,
         timeout: float = 60) -> None:
    """Downloads a model, telling `progress({"status", "completed", "total"})` (bytes, of the largest layer being
    fetched). Raises OllamaError with Ollama's own reason (no such model, no room, no network)."""
    try:
        r = _request("POST", f"{root(base_url)}/api/pull", {"model": model, "stream": True}, timeout)
    except urllib.error.HTTPError as e:
        raise OllamaError(f"Ollama: HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise OllamaError(f"Ollama is not running ({getattr(e, 'reason', e)})") from e
    with r:
        done = False
        for raw in r:
            if stop is not None and stop.is_set():
                raise OllamaError("cancelled")
            try:
                event = json.loads(raw.decode("utf-8"))
            except ValueError:
                continue
            if event.get("error"):
                raise OllamaError(f"Ollama: {event['error']}")
            if progress:
                progress({"status": str(event.get("status") or ""), "completed": int(event.get("completed") or 0),
                          "total": int(event.get("total") or 0)})
            if event.get("status") == "success":
                done = True
        if not done:
            raise OllamaError("the download stopped before Ollama said it was done")


def chat(base_url: str, model: str, prompt: str, schema: dict | None, images: list[Path], timeout: float,
         post: Callable[..., dict]) -> tuple[str, int | None, int | None, float]:
    """One answer through /api/chat: (text, tokens in, tokens out, seconds). `post` is the providers' POST with its retries
    and error kinds; the schema goes as `format` (Ollama 0.5+ follows a JSON schema)."""
    import base64
    limit = None
    try:
        limit = show(base_url, model).get("context")
    except OllamaError:
        pass       # the call itself says what is wrong (no such model, not running)
    try:
        ctx = num_ctx(prompt, len(images), limit)
    except OllamaError as e:
        from .providers import ProviderError
        raise ProviderError(str(e)) from e
    message = {"role": "user", "content": prompt}
    if images:
        message["images"] = [base64.b64encode(p.read_bytes()).decode("ascii") for p in images]
    body = {"model": model, "messages": [message], "stream": False, "format": schema if schema is not None else "json",
            "options": {"num_ctx": ctx}}
    started = time.monotonic()
    reply = post(f"{root(base_url)}/api/chat", body, {}, timeout)
    seconds = time.monotonic() - started
    text = ((reply.get("message") or {}).get("content") or "") if isinstance(reply, dict) else ""
    used = reply.get("prompt_eval_count")
    from .providers import ProviderError
    if isinstance(used, int) and used >= ctx - 64:
        # Ollama read as many tokens as the window holds: the start of the prompt was cut. Never an answer from a cut prompt
        raise ProviderError(f"the prompt did not fit the window of {ctx} tokens and Ollama cut it: choose a model with a "
                            "larger window, or another provider for this agent")
    if reply.get("done_reason") == "length":
        raise ProviderError(f"the answer was cut at its length limit (window {ctx} tokens): the model ran out of room")
    return text, used, reply.get("eval_count"), seconds
