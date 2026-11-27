"""One call to one model: prompt text (+ optional images) in, parsed JSON answer out.

Providers: any OpenAI-compatible server (OpenAI, OpenRouter, Groq, Ollama, LM Studio, vLLM), Claude, Gemini, and two
CLIs signed in with the person's own subscription: Codex CLI (ChatGPT) and Claude Code CLI (`claude -p`). The answer format is requested in each provider's own way; callers
still validate the answer against the full schema, since a provider may ignore the format.

Errors:
  QuotaExceeded — the account is out of credit or over its quota: retrying will not help, the user must act.
  Overloaded    — rate limited or the service is busy, still failing after retries: worth trying again later.
  ProviderError — anything else (bad key, bad model id, unreadable answer).
"""
from __future__ import annotations

import base64
import copy
import http.client
import json
import mimetypes
import os
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .. import proc
from ..settings import ModelSettings, get_secret

TRANSPORT_DROP = {"allOf", "if", "then", "else", "multipleOf", "$defs", "exclusiveMinimum"}


class ProviderError(Exception):
    status: int | None = None     # the HTTP status of the provider's refusal, when there was one


class QuotaExceeded(ProviderError):
    pass


class Overloaded(ProviderError):
    pass


@dataclass
class Answer:
    data: object
    raw: str
    seconds: float
    tokens_in: int | None = None
    tokens_out: int | None = None


def transport_schema(schema: dict) -> dict:
    """The schema without keywords providers often reject; `$ref` to `$defs` is inlined first."""
    defs = schema.get("$defs", {})

    def walk(node):
        if isinstance(node, dict):
            if "$ref" in node and node["$ref"].startswith("#/$defs/"):
                return walk(copy.deepcopy(defs[node["$ref"].split("/")[-1]]))
            return {k: walk(v) for k, v in node.items() if k not in TRANSPORT_DROP}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(schema)


def parse_json(text: str):
    """The JSON object in a model's text: plain, inside a ```json fence, or the outermost {...}."""
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        a, b = text.find("{"), text.rfind("}")
        if a >= 0 and b > a:
            try:
                return json.loads(text[a:b + 1])
            except json.JSONDecodeError:
                pass
    raise ProviderError("the model's answer is not JSON")


def _image(path: Path) -> tuple[str, str]:
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return mime, base64.b64encode(path.read_bytes()).decode("ascii")


def _key(m: ModelSettings, optional: bool = False) -> str:
    name = m.key_name()
    try:
        value = get_secret(name) if name else None
    except Exception as e:  # noqa: BLE001 — a locked keychain or a damaged key file: an error with words, not a crash
        raise ProviderError(f"the key of {m.provider_id or m.provider} cannot be read ({type(e).__name__}): "
                            "unlock the keychain or save the key again in «Settings → Providers»") from e
    if not value and not _own_server(m):   # no key saved: SMTV_<KIND>_API_KEY, as before stage 19 — only for that
        value = os.environ.get(f"SMTV_{m.provider.upper()}_API_KEY", "").strip() or None   # kind's own server
    if not value and not optional:
        raise ProviderError(f"no key for {m.provider_id or m.provider}: add it in «Settings → Providers»")
    return value or ""


def _key_optional(m: ModelSettings) -> bool:
    """A local server or an own address may take no key; every known cloud service must have one."""
    from ..presets import preset_of_url
    return m.provider == "openai" and preset_of_url(m.base_url) == "custom"


def _own_server(m: ModelSettings) -> bool:
    """An OpenAI-compatible server other than OpenAI itself (OpenRouter, Ollama, LM Studio): an OpenAI key from the
    environment is never sent there."""
    return m.provider == "openai" and "api.openai.com" not in m.base_url


def _clean(text: str, key: str | None) -> str:
    """An error text without the key: some providers repeat a part of a wrong key in their answer."""
    from .keycheck import redact
    return redact(text, key)


def _sleep_hint(detail: str, headers) -> float | None:
    """How long the service asks to wait: `Retry-After` (seconds) or Gemini's `RetryInfo.retryDelay` («30s»)."""
    try:
        after = (headers or {}).get("Retry-After") if hasattr(headers, "get") else None
        if after:
            return min(60.0, max(1.0, float(after)))
    except (TypeError, ValueError):
        pass
    try:
        for d in (json.loads(detail).get("error") or {}).get("details") or []:
            delay = str((d or {}).get("retryDelay") or "")
            if delay.endswith("s"):
                return min(60.0, max(1.0, float(delay[:-1])))
    except (ValueError, AttributeError, TypeError):
        pass
    return None


def out_of_money(code: int, detail: str) -> bool:
    """A refusal that waiting will not fix: no money or the day's quota is spent (QuotaExceeded).

    Judged by the codes the services document, not by words: a free Gemini key over its per-minute limit also says
    «exceeded your current quota… billing», and OpenAI's per-minute limit links to the billing page — both pass in
    a minute. OpenAI: `error.code` (or `type`) `insufficient_quota`. Gemini: a `QuotaFailure` whose `quotaId` is a
    per-day one. Claude: 400 «credit balance is too low». 402 always.
    """
    if code == 402:
        return True
    low = detail.lower()
    if code == 400 and "credit balance" in low:
        return True
    if code != 429:
        return False
    try:
        err = json.loads(detail).get("error") or {}
    except (ValueError, AttributeError):
        err = {}
    if not isinstance(err, dict):
        err = {}
    if "insufficient_quota" in (str(err.get("code")), str(err.get("type"))):
        return True
    ids = [str(v.get("quotaId") or "") for d in err.get("details") or [] if isinstance(d, dict)
           for v in d.get("violations") or [] if isinstance(v, dict)]
    if ids:
        return any("perday" in i.lower() for i in ids) and not any("perminute" in i.lower() for i in ids)
    return "insufficient_quota" in low      # a body that is not the documented JSON but names it


def send_json(url: str, data: bytes, headers: dict, timeout: float, retries: int = 2, key: str | None = None) -> dict:
    """POST and read a JSON answer from a paid service: the one retry policy of models and cloud speech.

    Retried with a growing pause (or the pause the service names): 429 rate limits, 5xx, and failures before the
    request was sent (no connection, connection refused). Not retried: no money or quota (QuotaExceeded), other refusals
    (ProviderError), and **no answer in `timeout` after the request was sent** — the service may have done the work and
    charged for it; the person presses «Продолжить» instead of SMTV paying again by itself. No error text carries `key`.
    """
    for attempt in range(retries + 1):
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = _clean(e.read().decode("utf-8", "replace")[:800], key)
            if out_of_money(e.code, detail):
                raise QuotaExceeded(f"HTTP {e.code}: {detail[:500]}") from e
            if e.code in (429, 529) or e.code >= 500:
                if attempt < retries:
                    time.sleep(_sleep_hint(detail, e.headers) or 5 * (attempt + 1))
                    continue
                raise Overloaded(f"HTTP {e.code} after {retries + 1} attempts: {detail[:500]}") from e
            err = ProviderError(f"HTTP {e.code}: {detail[:500]}")
            err.status = e.code
            raise err from e
        except urllib.error.URLError as e:
            # urllib wraps failures of connecting and sending: the service never got the whole request
            if attempt < retries:
                time.sleep(5 * (attempt + 1))
                continue
            raise Overloaded(_clean(f"could not reach the service: {getattr(e, 'reason', e)}", key)) from e
        except TimeoutError as e:
            raise Overloaded(f"the service did not answer in {timeout:.0f} s; it may still have done the work, "
                             "so Clip It! does not ask again by itself") from e
        except (OSError, http.client.HTTPException) as e:
            # the connection dropped after the request was sent (urllib wraps only connecting and sending in URLError):
            # the service may have done the work and charged for it, so no second paid call by itself (decision 3)
            raise Overloaded(_clean(f"the connection broke while waiting for the answer: {e}; it may still have done "
                                    "the work, so Clip It! does not ask again by itself", key)) from e
        except ValueError as e:
            raise ProviderError("the service's answer is not JSON: is the server address right?") from e
    raise ProviderError("unreachable")


def _post(url: str, body: dict, headers: dict, timeout: float, retries: int = 2, key: str | None = None) -> dict:
    """POST JSON to a model service (`send_json`)."""
    return send_json(url, json.dumps(body).encode("utf-8"), {"Content-Type": "application/json", **headers}, timeout,
                     retries, key)


# A server that refuses `response_format: json_schema` says so in its own words; these are the ones seen in the
# documentation of the services of `presets.py`. Any 400/422 that names the response format or the schema counts.
SCHEMA_REFUSED = re.compile(r"response_format|json_schema|schema|structured|guided", re.I)
_no_schema: set[tuple[str, str]] = set()      # (server, model) that refused the schema once: «object» from then on


def schema_hint(prompt: str, schema: dict) -> str:
    """The prompt for «object» mode: the server is not given the schema, so the prompt carries it (and the word JSON,
    which OpenAI-compatible servers require for `json_object`)."""
    return (f"{prompt}\n\nAnswer with one JSON object only, matching this JSON Schema exactly:\n"
            f"{json.dumps(transport_schema(schema), ensure_ascii=False)}")


def check_schema(data, schema: dict) -> None:
    """The answer of a server that was not given the schema is checked against it here (ProviderError if it does not
    match): such a server is only asked for «a JSON object»."""
    from jsonschema import Draft202012Validator
    errors = sorted(Draft202012Validator(transport_schema(schema)).iter_errors(data), key=lambda e: list(e.path))
    if errors:
        where = "/".join(str(x) for x in errors[0].path) or "the answer"
        raise ProviderError(f"the answer does not match the schema ({where}: {errors[0].message[:160]})")


def call_openai(m: ModelSettings, prompt: str, schema: dict, images: list[Path]) -> Answer:
    if m.api == "ollama":
        return call_ollama(m, prompt, schema, images)
    key = _key(m, optional=_key_optional(m))
    mode = m.json_mode
    if mode == "schema" and (m.base_url, m.model) in _no_schema:
        mode = "object"
    try:
        return _openai_once(m, prompt, schema, images, key, mode)
    except ProviderError as e:
        # the server refused the schema: one more try asking only for a JSON object, that answer checked against the schema
        if mode != "schema" or e.status not in (400, 422) or not SCHEMA_REFUSED.search(str(e)):
            raise
        answer = _openai_once(m, prompt, schema, images, key, "object")
        _no_schema.add((m.base_url, m.model))
        return answer


def _openai_once(m: ModelSettings, prompt: str, schema: dict, images: list[Path], key: str, mode: str) -> Answer:
    text_in = schema_hint(prompt, schema) if mode == "object" else prompt
    content = [{"type": "text", "text": text_in}]
    for path in images:
        mime, b64 = _image(path)
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
    body = {"model": m.model, "messages": [{"role": "user", "content": content}]}
    if mode == "schema":
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "answer", "schema": transport_schema(schema), "strict": False}}
    elif mode == "object":
        body["response_format"] = {"type": "json_object"}
    started = time.monotonic()
    reply = _post(f"{m.base_url.rstrip('/')}/chat/completions", body, {"Authorization": f"Bearer {key}"} if key else {}, m.timeout_s, key=key)
    seconds = time.monotonic() - started
    try:
        text = reply["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as e:
        raise ProviderError(_clean(f"unexpected reply: {json.dumps(reply)[:300]}", None)) from e
    usage = reply.get("usage") or {}
    data = parse_json(text)
    if mode == "object":
        check_schema(data, schema)
    return Answer(data, text, seconds, usage.get("prompt_tokens"), usage.get("completion_tokens"))


def call_ollama(m: ModelSettings, prompt: str, schema: dict, images: list[Path]) -> Answer:
    """Ollama's own /api/chat with the context window set by the prompt's length (`ollama.py`); the schema as `format`
    (Ollama shapes the answer by it, so the caller's own check is enough)."""
    from . import ollama
    text, tin, tout, seconds = ollama.chat(m.base_url, m.model, prompt, transport_schema(schema), images, m.timeout_s,
                                           lambda url, body, headers, timeout: _post(url, body, headers, timeout, retries=1))
    return Answer(parse_json(text), text, seconds, tin if isinstance(tin, int) else None, tout if isinstance(tout, int) else None)


def call_anthropic(m: ModelSettings, prompt: str, schema: dict, images: list[Path]) -> Answer:
    content = []
    for path in images:
        mime, b64 = _image(path)
        content.append({"type": "image", "source": {"type": "base64", "media_type": mime, "data": b64}})
    content.append({"type": "text", "text": prompt})
    body = {"model": m.model, "max_tokens": m.max_tokens,
            "tools": [{"name": "answer", "description": "Return the answer in the required JSON shape.", "input_schema": transport_schema(schema)}],
            "tool_choice": {"type": "tool", "name": "answer"}, "messages": [{"role": "user", "content": content}]}
    key = _key(m)
    started = time.monotonic()
    reply = _post("https://api.anthropic.com/v1/messages", body, {"x-api-key": key, "anthropic-version": "2023-06-01"}, m.timeout_s, key=key)
    seconds = time.monotonic() - started
    for block in reply.get("content") or []:
        if block.get("type") == "tool_use":
            usage = reply.get("usage") or {}
            return Answer(block.get("input"), json.dumps(block.get("input"), ensure_ascii=False), seconds, usage.get("input_tokens"), usage.get("output_tokens"))
    raise ProviderError(_clean(f"no tool answer: {json.dumps(reply)[:300]}", None))


def call_gemini(m: ModelSettings, prompt: str, schema: dict, images: list[Path]) -> Answer:
    parts = [{"text": prompt}]
    for path in images:
        mime, b64 = _image(path)
        parts.append({"inline_data": {"mime_type": mime, "data": b64}})
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"responseMimeType": "application/json", "responseJsonSchema": transport_schema(schema)}}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{m.model}:generateContent"
    key = _key(m)
    started = time.monotonic()
    reply = _post(url, body, {"x-goog-api-key": key}, m.timeout_s, key=key)
    seconds = time.monotonic() - started
    try:
        text = "".join(p.get("text", "") for p in reply["candidates"][0]["content"]["parts"])
    except (KeyError, IndexError, TypeError) as e:
        raise ProviderError(_clean(f"unexpected reply: {json.dumps(reply)[:300]}", None)) from e
    usage = reply.get("usageMetadata") or {}
    return Answer(parse_json(text), text, seconds, usage.get("promptTokenCount"), usage.get("candidatesTokenCount"))


# B12: `codex exec` sends its own long instructions and the definitions of its tools with every call — 15 thousand input
# tokens on an empty question (Codex CLI 0.163, 23.11), more than most of our prompts. SMTV asks for one JSON answer and
# never lets it use a tool, so the tools are switched off and its instructions replaced by two sentences: 6 thousand on
# the same question. `-c features.<name>=false` and an unknown `-c` key are ignored by a CLI that does not know them
# (`--disable <name>` would stop it), so an older or newer Codex still runs, only without the saving.
CODEX_TOOLS_OFF = ("shell_tool", "unified_exec", "apps", "browser_use", "browser_use_external", "computer_use", "image_generation",
                   "multi_agent", "plugins", "memories", "goals", "view_image", "skill_search", "tool_suggest", "sleep_tool", "hooks",
                   "in_app_browser", "code_mode_host")
CODEX_INSTRUCTIONS = ("You answer one request with JSON that matches the given output schema. "
                      "Do not use tools, files or the network; everything you need is in the request and its images.\n")
CODEX_LEAN = True


def codex_lean_args(work: Path) -> list[str]:
    """The arguments that leave out Codex's tools and its own instructions (CODEX_TOOLS_OFF)."""
    if not CODEX_LEAN:
        return []
    instructions = work / "instructions.md"
    try:
        instructions.write_text(CODEX_INSTRUCTIONS, encoding="utf-8")
    except OSError:                       # a full disk or a locked folder: the call goes as before B12, only dearer
        return []
    args = []
    for name in CODEX_TOOLS_OFF:
        args += ["-c", f"features.{name}=false"]
    return args + ["-c", 'web_search="disabled"', "-c", f"model_instructions_file={json.dumps(str(instructions), ensure_ascii=False)}"]


def call_codex(m: ModelSettings, prompt: str, schema: dict, images: list[Path]) -> Answer:
    """`codex exec` with the user's own Codex sign-in: read-only sandbox in an empty folder, no user config, no tools."""
    binary = shutil.which(m.codex_bin or "codex")
    if not binary:
        raise ProviderError("the Codex CLI is not installed: install it and run `codex login` once")
    with tempfile.TemporaryDirectory(prefix="smtv-codex-") as tmp:
        work = Path(tmp)
        schema_path, last_path = work / "schema.json", work / "answer.txt"
        schema_path.write_text(json.dumps(transport_schema(schema)), encoding="utf-8")
        base = [binary, "exec", "--ignore-user-config", "--ephemeral", "--skip-git-repo-check", "--sandbox", "read-only", "-C", str(work),
                "--json", "-c", f'model_reasoning_effort="{m.reasoning_effort}"', "--output-schema", str(schema_path), "-o", str(last_path)]
        tail_args = (["-m", m.model] if m.model else []) + (["--image", ",".join(str(p.resolve()) for p in images)] if images else []) + ["-"]
        lean = codex_lean_args(work)
        started = time.monotonic()
        for argv in ([base + lean + tail_args, base + tail_args] if lean else [base + tail_args]):
            try:
                done = proc.run(argv, m.timeout_s, what="codex", input=prompt)
            except proc.TimedOut as e:
                raise Overloaded(f"codex did not answer within {m.timeout_s:.0f} s") from e
            except OSError as e:
                raise ProviderError(f"the Codex CLI could not be started: {e}") from e
            # a CLI that refuses the B12 settings themselves is asked once more the way it was before them
            if done.returncode == 0 or not any(h in (done.stderr or "").lower() for h in ("config", "instructions", "feature")):
                break
        seconds = time.monotonic() - started
        if done.returncode != 0:
            tail = (done.stderr or done.stdout)[-500:]
            if any(h in tail.lower() for h in ("usage limit", "rate limit", "quota")):
                raise QuotaExceeded(f"codex: {tail}")
            raise ProviderError(f"codex exit {done.returncode}: {tail}")
        if not last_path.exists():
            raise ProviderError("codex wrote no answer")
        text = last_path.read_text(encoding="utf-8")
    tokens_in, tokens_out = codex_usage(done.stdout)
    return Answer(parse_json(text), text, seconds, tokens_in, tokens_out)


def codex_usage(stdout: str) -> tuple[int | None, int | None]:
    """(input, output) tokens from `codex exec --json` (its `turn.completed` events), or (None, None) when it says none.
    Cached input is part of the input; reasoning is part of the output."""
    tin = tout = None
    for line in (stdout or "").splitlines():
        if '"turn.completed"' not in line:
            continue
        try:
            usage = json.loads(line).get("usage") or {}
        except ValueError:
            continue
        if isinstance(usage.get("input_tokens"), int):
            tin = (tin or 0) + usage["input_tokens"]
        if isinstance(usage.get("output_tokens"), int):
            tout = (tout or 0) + usage["output_tokens"]
    return tin, tout


def claude_code_argv(m: ModelSettings, binary: str, schema: dict) -> list[str]:
    """`claude -p` as SMTV runs it: one answer, no tools, no session kept, no MCP servers or project settings, the answer
    shaped by the schema. The person's own sign-in stays as it is (no --bare: it would skip the subscription)."""
    argv = [binary, "-p", "--output-format", "json", "--json-schema", json.dumps(transport_schema(schema)), "--tools", "",
            "--no-session-persistence", "--strict-mcp-config", "--setting-sources", "", "--disable-slash-commands"]
    if m.model:
        argv += ["--model", m.model]
    return argv


def call_claude_code(m: ModelSettings, prompt: str, schema: dict, images: list[Path]) -> Answer:
    """The Claude Code CLI with the person's own Claude subscription, text only (frames are not passed: agents that
    read frames are not given this provider)."""
    if images:
        raise ProviderError("the Claude Code CLI is called with text only: choose another provider for agents that read frames")
    binary = shutil.which(m.claude_bin or "claude")
    if not binary:
        raise ProviderError("the Claude Code CLI is not installed: install it and sign in once by running `claude`")
    with tempfile.TemporaryDirectory(prefix="smtv-claude-") as tmp:
        started = time.monotonic()
        try:
            done = proc.run(claude_code_argv(m, binary, schema), m.timeout_s, what="claude", input=prompt, cwd=tmp)
        except proc.TimedOut as e:
            raise Overloaded(f"claude did not answer within {m.timeout_s:.0f} s") from e
        except OSError as e:
            raise ProviderError(f"the Claude Code CLI could not be started: {e}") from e
        seconds = time.monotonic() - started
    out = (done.stdout or "").strip()
    try:
        reply = json.loads(out) if out else {}
    except ValueError:
        reply = {}
    text = str(reply.get("result") or "")
    if done.returncode == 0 and not reply:
        raise ProviderError(f"claude gave no readable answer: {(done.stderr or out)[-300:]}")
    if done.returncode != 0 or reply.get("is_error"):
        tail = (text or done.stderr or out)[-500:]
        if any(h in tail.lower() for h in ("usage limit", "rate limit", "limit reached", "quota")):
            raise QuotaExceeded(f"claude: {tail}")
        raise ProviderError(f"claude exit {done.returncode}: {tail}")
    usage = reply.get("usage") or {}
    tokens_in = None
    if isinstance(usage.get("input_tokens"), int):
        tokens_in = usage["input_tokens"] + sum(v for k, v in usage.items() if k.startswith("cache_") and k.endswith("_tokens") and isinstance(v, int))
    tokens_out = usage.get("output_tokens") if isinstance(usage.get("output_tokens"), int) else None
    data = reply.get("structured_output")
    if not isinstance(data, dict):
        data = parse_json(text)
        raw = text
    else:
        raw = json.dumps(data, ensure_ascii=False)
    return Answer(data, raw, seconds, tokens_in, tokens_out)


STREAMMOMENT_TRIES = 4
# The server waits up to 630 s for the model; a call still «in flight» there is waited for at least that long with the
# same key, so its answer (already paid) is picked up instead of a second, paid call under a new key.
STREAMMOMENT_IN_FLIGHT_WAIT_S = 30
STREAMMOMENT_IN_FLIGHT_WAITS = 25


def call_streammoment(m: ModelSettings, prompt: str, schema: dict, images: list[Path]) -> Answer:
    """Our key (stage 22): the agent's own prompt to StreamMoment's server, which calls the model with our key and takes
    the cost from the account's balance. One idempotency key for every try of this call: a retry after a lost answer
    gets the stored one and is never charged twice."""
    import uuid
    from .. import account, prompts as prompts_mod
    if not m.agent:
        raise ProviderError("StreamMoment answers only Clip It!'s own agents: this call has no agent")
    body = {"agent": m.agent, "prompts_version": prompts_mod.version(), "prompt": prompt, "schema": transport_schema(schema),
            "images": [dict(zip(("mime", "data"), _image(path))) for path in images]}
    headers = {"Idempotency-Key": uuid.uuid4().hex}
    started = time.monotonic()
    attempt = waits = 0
    while True:
        try:
            status, answer = account.authorized("POST", "/api/smtv/model/call", body, headers, timeout=max(m.timeout_s + 360, 660))
        except account.NotSignedIn as e:
            raise ProviderError(str(e)) from e
        except account.AccountError as e:      # nothing answered: maybe it did get the call; the same key tries again
            attempt += 1
            if attempt < STREAMMOMENT_TRIES:
                time.sleep(5 * attempt)
                continue
            raise Overloaded(f"{e}. {e.hint}".strip()) from e
        if status == 200:
            data = answer.get("data")
            tokens_in = answer.get("tokens_in") if isinstance(answer.get("tokens_in"), int) else None
            tokens_out = answer.get("tokens_out") if isinstance(answer.get("tokens_out"), int) else None
            return Answer(data, json.dumps(data, ensure_ascii=False), time.monotonic() - started, tokens_in, tokens_out)
        error = str(answer.get("error") or f"http_{status}")
        if status == 402:
            raise QuotaExceeded("not enough tokens on the StreamMoment balance: buy a package in «Settings → Account»")
        if status == 409 and error == "in_flight":
            waits += 1
            if waits <= STREAMMOMENT_IN_FLIGHT_WAITS:
                time.sleep(STREAMMOMENT_IN_FLIGHT_WAIT_S)
                continue
            raise Overloaded("StreamMoment is still answering this call: try again later")
        if status == 503:
            attempt += 1
            if attempt < STREAMMOMENT_TRIES:      # the model is busy: wait, same key
                time.sleep(10 * attempt)
                continue
            raise Overloaded(f"StreamMoment: the model is busy ({error}); try again later")
        raise ProviderError(f"StreamMoment refused the call: {error}")


CALLS = {"openai": call_openai, "anthropic": call_anthropic, "gemini": call_gemini, "codex": call_codex, "claude_code": call_claude_code,
         "streammoment": call_streammoment}


def call(m: ModelSettings, prompt: str, schema: dict, images: list[Path] | None = None) -> Answer:
    if m.provider not in CALLS:
        raise ProviderError("no provider is set up: add one in «Settings → Providers» or with `smtv model set`")
    if m.provider not in ("codex", "claude_code", "streammoment") and not m.model:
        raise ProviderError(f"no model id for {m.provider_id or m.provider}: choose it in «Settings → Agents»")
    return CALLS[m.provider](m, prompt, schema, images or [])
