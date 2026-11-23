"""Ready-made settings of the OpenAI-compatible kind (stage 20): local model servers and cloud services.

A preset is only an address, a way to ask for JSON and a few words for the window: the call is the OpenAI-compatible one
of stage 19 (`llm/providers.py`), except Ollama, which is called through its own `/api/chat` so the size of the context
window can be set (`llm/ollama.py`).

Local servers need no key and are installed by the person; «Find on this computer» asks each local address
(`discover`). Cloud services take the person's own key; SMTV connects none of them by itself.

json_mode: «schema» — the server is given the JSON schema of the answer (`response_format: json_schema`); «object» —
only «answer with a JSON object» (`json_object`), the schema goes into the prompt. A server that refuses the schema gets
one more try with «object», and that answer is checked against the schema (`providers.call_openai`).
Addresses and JSON modes as the services document them (checked 2026-11-21 from their public documentation; none was
called with a key).
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Preset:
    id: str
    label: str
    base_url: str
    json_mode: str = "schema"     # schema | object
    local: bool = False           # a server on this computer: no key, «Find on this computer»
    key_url: str = ""             # where a person gets a key (cloud) or the program (local)
    key_hint: str = ""
    default_model: str = ""       # a stable alias of the service's main model, when it has one
    api: str = "openai"           # openai | ollama (its own /api/chat, with the window size)
    note: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _local_host() -> str:
    """Where the local model servers are. On this computer: 127.0.0.1. In Docker (stage 21) the image sets
    SMTV_LOCAL_HOST=host.docker.internal: Ollama and the others run on the host, not in the container."""
    host = os.environ.get("SMTV_LOCAL_HOST", "").strip().lower()
    return host if re.fullmatch(r"[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?", host) else "127.0.0.1"


LOCAL_HOST = _local_host()

PRESETS_LIST = (
    # stage 19
    Preset("openai", "OpenAI", "https://api.openai.com/v1", key_url="https://platform.openai.com/api-keys", key_hint="sk-…"),
    Preset("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", key_url="https://openrouter.ai/settings/keys", key_hint="sk-or-…"),
    Preset("custom", "OpenAI-compatible", ""),
    # local servers (stage 20): the person installs them; SMTV only finds and calls them
    Preset("ollama", "Ollama", f"http://{LOCAL_HOST}:11434", local=True, key_url="https://ollama.com/download", api="ollama",
           note="Models are downloaded and removed right here; the window size is set by the length of the prompt."),
    Preset("lmstudio", "LM Studio", f"http://{LOCAL_HOST}:1234/v1", local=True, key_url="https://lmstudio.ai/download",
           note="Load a model in LM Studio and start its server (Developer → Start server)."),
    Preset("vllm", "vLLM", f"http://{LOCAL_HOST}:8000/v1", local=True, key_url="https://docs.vllm.ai/en/latest/getting_started/installation/",
           note="vllm serve <model>: NVIDIA card, Linux or WSL."),
    Preset("llamacpp", "llama.cpp", f"http://{LOCAL_HOST}:8080/v1", local=True, key_url="https://github.com/ggml-org/llama.cpp",
           note="llama-server -m <model.gguf>"),
    # cloud services (stage 20): the person's own key
    Preset("deepseek", "DeepSeek", "https://api.deepseek.com/v1", "object", key_url="https://platform.deepseek.com/api_keys",
           key_hint="sk-…", default_model="deepseek-chat"),
    Preset("groq", "Groq", "https://api.groq.com/openai/v1", key_url="https://console.groq.com/keys", key_hint="gsk_…",
           note="The same key also transcribes speech (Whisper) in «Settings → Speech»."),
    Preset("mistral", "Mistral", "https://api.mistral.ai/v1", key_url="https://console.mistral.ai/api-keys",
           default_model="mistral-large-latest"),
    Preset("xai", "xAI (Grok)", "https://api.x.ai/v1", key_url="https://console.x.ai", key_hint="xai-…"),
    Preset("together", "Together AI", "https://api.together.xyz/v1", key_url="https://api.together.ai/settings/api-keys"),
    Preset("fireworks", "Fireworks AI", "https://api.fireworks.ai/inference/v1", key_url="https://fireworks.ai/account/api-keys",
           key_hint="fw_…"),
    Preset("qwen", "Qwen (DashScope)", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1", "object",
           key_url="https://modelstudio.console.alibabacloud.com/", key_hint="sk-…"),
    Preset("kimi", "Kimi (Moonshot)", "https://api.moonshot.ai/v1", "object", key_url="https://platform.moonshot.ai/console/api-keys",
           key_hint="sk-…"),
    Preset("glm", "GLM (Z.ai)", "https://api.z.ai/api/paas/v4", "object", key_url="https://z.ai/manage-apikey/apikey-list"),
    Preset("cerebras", "Cerebras", "https://api.cerebras.ai/v1", key_url="https://cloud.cerebras.ai", key_hint="csk-…"),
)
BY_ID = {p.id: p for p in PRESETS_LIST}
LOCAL = tuple(p.id for p in PRESETS_LIST if p.local)
CLOUD = tuple(p.id for p in PRESETS_LIST if not p.local and p.id not in ("openai", "openrouter", "custom"))


def get(preset: str) -> Preset | None:
    return BY_ID.get(preset or "")


def preset_of_url(url: str) -> str:
    """Which preset an address belongs to (settings written before the preset was kept): custom when none."""
    url = (url or "").rstrip("/")
    for p in PRESETS_LIST:
        if p.base_url and not p.local and url.startswith(p.base_url.rstrip("/")):
            return p.id
    return "custom"


def is_local_url(url: str) -> bool:
    host = (url or "").split("://", 1)[-1].split("/", 1)[0].rsplit(":", 1)[0].strip("[]").lower()
    return host in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "host.docker.internal", LOCAL_HOST) or host.endswith(".local")


# --- «Find on this computer» -----------------------------------------------------------------------------------

def _get(url: str, timeout: float) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, method="GET"), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8") or "{}")


def probe(preset: Preset, base_url: str | None = None, timeout: float = 1.5) -> dict:
    """Is this local server running: {"preset", "base_url", "found", "models": [ids], "detail"}. Only a server that answers
    with its list of models counts — another program on the same port does not."""
    base = (base_url or preset.base_url).rstrip("/")
    try:
        if preset.api == "ollama":
            reply = _get(f"{base}/api/tags", timeout)
            rows = reply.get("models")
            ids = [m.get("name") for m in rows or [] if isinstance(m, dict) and isinstance(m.get("name"), str)]
        else:
            reply = _get(f"{base}/models", timeout)
            rows = reply.get("data")
            ids = [m.get("id") for m in rows or [] if isinstance(m, dict) and isinstance(m.get("id"), str)]
        if not isinstance(rows, list):
            return {"preset": preset.id, "base_url": base, "found": False, "models": [], "detail": "another program answers there"}
        return {"preset": preset.id, "base_url": base, "found": True, "models": sorted(ids), "detail": ""}
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return {"preset": preset.id, "base_url": base, "found": False, "models": [], "detail": str(getattr(e, "reason", e))[:200]}
    except (ValueError, AttributeError, TypeError):    # not JSON, or JSON of another shape: another program
        return {"preset": preset.id, "base_url": base, "found": False, "models": [], "detail": "another program answers there"}


def discover(timeout: float = 1.5) -> list[dict]:
    """Every local server at its usual address, asked at the same time (a second at most)."""
    local = [BY_ID[i] for i in LOCAL]
    with ThreadPoolExecutor(max_workers=len(local)) as pool:
        return list(pool.map(lambda p: probe(p, timeout=timeout), local))
