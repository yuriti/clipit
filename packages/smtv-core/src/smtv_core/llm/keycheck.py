"""Is this key good? A free request to the provider (its list of models), never a paid model call.

Used by the page's "Check" button and by anything else that wants to know before a long job starts. The key is sent only
to the provider; it is never put in the answer, in an error text or in a log (`redact`).
"""
from __future__ import annotations

import json
import os
import re
import shutil
from .. import proc
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from ..settings import ModelSettings, get_secret

OK, NO_KEY, BAD_KEY, UNREACHABLE, NOT_INSTALLED, NOT_SIGNED_IN, ERROR = (
    "ok", "no_key", "bad_key", "unreachable", "not_installed", "not_signed_in", "error")

# Where a person gets a key, and what the window says about each kind. Model ids are not listed here: they change too
# often; a good key returns the live list.
HELP = {
    "openai": {"label": "OpenAI", "key_url": "https://platform.openai.com/api-keys", "key_hint": "sk-…",
               "note": "Also any OpenAI-compatible server: OpenRouter, Groq, Ollama, LM Studio, vLLM (change the server address)."},
    "anthropic": {"label": "Claude API", "key_url": "https://platform.claude.com/settings/keys", "key_hint": "sk-ant-…", "note": ""},
    "gemini": {"label": "Gemini", "key_url": "https://aistudio.google.com/apikey", "key_hint": "AIza…", "note": ""},
    "codex": {"label": "Codex CLI", "key_url": "https://learn.chatgpt.com/docs/codex/cli", "key_hint": "",
              "note": "Uses your own ChatGPT sign-in: install the Codex CLI and run `codex login` once. No key."},
    "claude_code": {"label": "Claude Code CLI", "key_url": "https://code.claude.com/docs/en/setup", "key_hint": "",
                    "note": "Uses your own Claude subscription: install Claude Code and sign in once by running `claude`. No key."},
}
# The presets of the OpenAI-compatible kind (labels, where to get a key) live in `presets.py`.
# The CLIs run on the person's own subscription: the window says so and links the rules in force (checked 2026-11-21).
RULES = {
    "codex": [("OpenAI Terms of Use", "https://openai.com/policies/terms-of-use/"),
              ("OpenAI Usage Policies", "https://openai.com/policies/usage-policies/"),
              ("Codex: sign-in", "https://learn.chatgpt.com/docs/auth")],
    "claude_code": [("Claude Code: legal and compliance", "https://code.claude.com/docs/en/legal-and-compliance"),
                    ("Anthropic Consumer Terms", "https://www.anthropic.com/legal/consumer-terms"),
                    ("Anthropic Usage Policy", "https://www.anthropic.com/legal/aup")],
}
STEPS = {
    "codex": ["Install the Codex CLI.", "Run `codex login` once in a terminal and sign in with ChatGPT.", "Press «Check»."],
    "claude_code": ["Install Claude Code.", "Run `claude` once in a terminal and sign in with your Claude subscription.", "Press «Check»."],
}

# keys of the stage 20 services too: Groq gsk_, xAI xai-, Cerebras csk-, Fireworks fw_ (also when the service masks a part)
_TOKENISH = re.compile(r"(sk-[A-Za-z0-9_\-*]{4,}|AIza[A-Za-z0-9_\-]{8,}|Bearer\s+\S+|(?:gsk_|xai-|csk-|fw_)[A-Za-z0-9_\-*.]{6,})")


@dataclass
class KeyCheck:
    status: str
    detail: str
    models: list[str] = field(default_factory=list)
    info: dict = field(default_factory=dict)      # model id -> {"images"?, "price"?: {"in", "out"}, "label"?} the provider said

    def as_dict(self) -> dict:
        return {"ok": self.status == OK, "status": self.status, "detail": self.detail, "models": self.models}


# More shapes of keys and tokens, for crash files and reports: GitHub, Hugging Face, Groq, Slack, JWTs, secrets in query
# strings, headers and JSON fields.
SHAPES = [
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{20,}|hf_[A-Za-z0-9]{16,}|gsk_[A-Za-z0-9]{16,}|xox[abposr]-[A-Za-z0-9-]{10,}|"
                r"sk-ant-[A-Za-z0-9_\-]{8,}|eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{5,})"), "[key]"),
    (re.compile(r"(?i)([?&](?:k|key|api_key|apikey|token|access_token|auth|sig|signature|client_secret|code)=)[^&\s\"'#]+"), r"\1[key]"),
    (re.compile(r"(?i)\b(authorization|x-api-key|x-goog-api-key|x-smtv-token|cookie|set-cookie)(\"?\s*[:=]\s*\"?)[^\"\n,}]+"), r"\1\2[key]"),
    (re.compile(r"(?i)(\"[a-z_]*(?:api_key|token|secret|password)\"\s*:\s*\")(?!\[)[^\"]+"), r"\1[key]"),
]


def redact_all(text: str, *secrets: str | None) -> str:
    """`redact` and every other shape of a key or a token (`SHAPES`)."""
    text = redact(text, *secrets)
    for pattern, repl in SHAPES:
        text = pattern.sub(repl, text)
    return text


def redact(text: str, *secrets: str | None) -> str:
    """The text without the secrets and without anything that looks like a key."""
    for s in secrets:
        if s:
            text = text.replace(s, "[key]")
    return _TOKENISH.sub("[key]", text)


def _get(url: str, headers: dict, timeout: float) -> dict:
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8") or "{}")


def _info(reply: dict) -> dict:
    """What a list of models says of each beyond its id: OpenRouter gives input modalities and prices per token,
    Anthropic and Gemini display names."""
    out = {}
    for row in reply.get("data") or reply.get("models") or []:
        if not isinstance(row, dict):
            continue
        mid = row.get("id") or str(row.get("name") or "").removeprefix("models/")
        if not isinstance(mid, str) or not mid:
            continue
        item = {}
        mods = (row.get("architecture") or {}).get("input_modalities")
        if isinstance(mods, list):
            item["images"] = "image" in mods
        pricing = row.get("pricing") or {}
        try:
            pin, pout = float(pricing["prompt"]), float(pricing["completion"])
            if pin >= 0 and pout >= 0:
                item["price"] = {"in": round(pin * 1e6, 4), "out": round(pout * 1e6, 4)}
        except (KeyError, TypeError, ValueError):
            pass
        label = row.get("display_name") or row.get("displayName")
        if isinstance(label, str):
            item["label"] = label
        if item:
            out[mid] = item
    return out


def _ids(reply: dict, key: str = "id") -> list[str]:
    rows = reply.get("data") or reply.get("models") or []
    out = []
    for row in rows:
        value = row.get(key) if isinstance(row, dict) else None
        if isinstance(value, str):
            out.append(value.removeprefix("models/"))
    return sorted(set(out))[:300]


def check(m: ModelSettings, key: str | None = None, timeout: float = 15, saved: bool = True) -> KeyCheck:
    """Checks `key` (or, with `saved`, the saved one or SMTV_<KIND>_API_KEY) against the provider in `m`."""
    if m.provider == "codex":
        binary = shutil.which(m.codex_bin or "codex")
        if not binary:
            return KeyCheck(NOT_INSTALLED, "Codex CLI not found")
        try:
            done = proc.run([binary, "login", "status"], timeout, what="codex")
        except (OSError, proc.TimedOut) as e:
            return KeyCheck(ERROR, f"codex login status: {type(e).__name__}")
        return KeyCheck(OK, "signed in") if done.returncode == 0 else KeyCheck(NOT_SIGNED_IN, "run: codex login")
    if m.provider == "claude_code":
        binary = shutil.which(m.claude_bin or "claude")
        if not binary:
            return KeyCheck(NOT_INSTALLED, "Claude Code not found")
        try:
            done = proc.run([binary, "auth", "status", "--json"], timeout, what="claude")
        except (OSError, proc.TimedOut) as e:
            return KeyCheck(ERROR, f"claude auth status: {type(e).__name__}")
        try:
            status = json.loads(done.stdout or "{}")
        except ValueError:
            status = {}
        signed_in = status.get("loggedIn") if isinstance(status, dict) else None
        if signed_in is True or (signed_in is None and done.returncode == 0):
            return KeyCheck(OK, "signed in")
        return KeyCheck(NOT_SIGNED_IN, "run: claude, then sign in")
    if m.provider not in HELP:
        return KeyCheck(ERROR, "choose a provider")
    key = (key or "").strip()
    if not key and saved:
        try:
            key = get_secret(m.key_name() or "") or ""
        except Exception as e:  # noqa: BLE001 — a locked keychain or a damaged key file: said, not a crash
            return KeyCheck(ERROR, f"the saved key cannot be read ({type(e).__name__})")
        if not key and m.key_name() and not (m.provider == "openai" and "api.openai.com" not in m.base_url):
            key = os.environ.get(f"SMTV_{m.provider.upper()}_API_KEY", "").strip()   # never to another server
    from ..presets import preset_of_url
    local_server = m.provider == "openai" and preset_of_url(m.base_url) == "custom"    # local, or an own address
    if m.provider == "openai" and m.api == "ollama":
        from . import ollama
        try:
            rows = ollama.models(m.base_url, timeout)
        except ollama.OllamaError as e:
            return KeyCheck(UNREACHABLE, str(e)[:300])
        return KeyCheck(OK, "Ollama answers", [r["id"] for r in rows],
                        {r["id"]: {"images": r["images"]} for r in rows if r["images"] is not None})
    if not key and not local_server:
        return KeyCheck(NO_KEY, "no key")
    if m.provider == "openai":
        url, headers, field_name = f"{m.base_url.rstrip('/')}/models", ({"Authorization": f"Bearer {key}"} if key else {}), "id"
    elif m.provider == "anthropic":
        url, headers, field_name = "https://api.anthropic.com/v1/models?limit=100", {"x-api-key": key, "anthropic-version": "2023-06-01"}, "id"
    else:
        url, headers, field_name = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200", {"x-goog-api-key": key}, "name"
    try:
        if m.provider == "openai" and "openrouter.ai" in m.base_url:
            # OpenRouter lists its models to anyone: the key itself is checked by its own page, /key (free)
            _get(f"{m.base_url.rstrip('/')}/key", headers, timeout)
        reply = _get(url, headers, timeout)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        status = BAD_KEY if e.code in (400, 401, 403) else ERROR
        return KeyCheck(status, redact(f"HTTP {e.code}: {body}", key))
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return KeyCheck(UNREACHABLE, redact(f"could not reach {url.split('?')[0]}: {getattr(e, 'reason', e)}", key))
    except ValueError:
        return KeyCheck(ERROR, "the answer is not JSON: is the server address right?")
    return KeyCheck(OK, "the key works", _ids(reply, field_name), _info(reply))
