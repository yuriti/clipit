"""User settings: a JSON file in the settings folder. Keys live apart from it: in the system keychain when there is one,
otherwise encrypted in a file of their own (`vault.py`).

The window (smtv serve) and the `smtv model` commands write these settings; nobody has to edit a .env file.

Providers (stage 19): a list of connections, several of one kind allowed under different keys and names («OpenAI —
personal», «OpenAI — work»). Each agent of each tool takes a provider and a model of it (`agents.py`). Settings written
by SMTV before stage 19 had one connection (`model`): it becomes one provider with the same key, and every agent keeps
the model it had.
"""
from __future__ import annotations

import json
import os
import re
import secrets as _random
import shutil
import sys
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from . import paths, presets as presets_mod
from .filelock import ProcessLock

# Kinds of provider. `streammoment` (stage 22): our key behind a StreamMoment account (`account.py`) — no key here, the
# model is our server's choice, paid from the account's balance.
OPENAI, ANTHROPIC, GEMINI, CODEX, CLAUDE_CODE, STREAMMOMENT = "openai", "anthropic", "gemini", "codex", "claude_code", "streammoment"
KINDS = (OPENAI, ANTHROPIC, GEMINI, CODEX, CLAUDE_CODE, STREAMMOMENT)
CLI_KINDS = (CODEX, CLAUDE_CODE)          # sign in on their own with the person's subscription: no key here
KEYLESS_KINDS = CLI_KINDS + (STREAMMOMENT,)   # no key of the person; an empty model id is the service's own choice
RESERVED_KINDS: tuple[str, ...] = ()
PROVIDERS = (OPENAI, ANTHROPIC, GEMINI, CODEX)   # the kinds of the one connection before stage 19 (their old key names)
# The presets of the OpenAI-compatible kind (stage 20: local servers and cloud services, `presets.py`): id -> address
PRESETS = {p.id: p.base_url for p in presets_mod.PRESETS_LIST}
PROVIDER_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")
KEYRING_SERVICE = "smtv"


@dataclass
class ModelSettings:
    """One model of one provider, as a call needs it. Made from a `Provider` for each agent; never saved."""
    provider: str = ""            # the kind: openai | anthropic | gemini | codex | claude_code
    model: str = ""               # model id exactly as the provider names it; empty = the CLI's own default
    base_url: str = "https://api.openai.com/v1"   # openai only: any OpenAI-compatible server
    api: str = "openai"           # openai kind: openai (/chat/completions) | ollama (its own /api/chat, stage 20)
    json_mode: str = "schema"     # openai only: schema | object | none
    timeout_s: float = 300.0
    max_tokens: int = 16000       # anthropic only
    codex_bin: str = "codex"
    claude_bin: str = "claude"
    reasoning_effort: str = "medium"   # codex only
    price_in: float = 0.0         # US dollars per million input tokens (the built-in table, `prices.py`); 0: unknown
    price_out: float = 0.0
    key_ref: str = ""             # the name its key is saved under; empty: the name before stage 19
    provider_id: str = ""         # which provider of the list
    agent: str = ""               # which agent this connection was made for (StreamMoment's server checks its prompt)

    def cost(self, tokens_in: int | None, tokens_out: int | None) -> float | None:
        """What a call cost by the prices set here, or None when there are no prices or no token counts."""
        if not (self.price_in or self.price_out) or (tokens_in is None and tokens_out is None):
            return None
        return round(((tokens_in or 0) * self.price_in + (tokens_out or 0) * self.price_out) / 1e6, 6)

    def key_name(self) -> str | None:
        """Which secret this provider needs, or None (the CLIs sign in on their own)."""
        if self.provider in KEYLESS_KINDS:
            return None
        return self.key_ref or f"{self.provider}_api_key"


@dataclass
class Provider:
    """One connection of the list."""
    id: str                       # PROVIDER_ID; the agents' choices refer to it
    kind: str
    name: str = ""
    preset: str = ""              # openai kind: openai | openrouter | custom (any OpenAI-compatible address)
    base_url: str = ""
    json_mode: str = "schema"
    reasoning_effort: str = "medium"
    bin: str = ""                 # the CLI's program; empty: codex / claude on PATH
    timeout_s: float = 300.0
    max_tokens: int = 16000
    default_model: str = ""       # for agents the table has no model for (a custom server); the one model before stage 19
    key_ref: str = ""             # the key's name; empty: provider.<id>
    enabled: bool = True

    def key_name(self) -> str | None:
        return None if self.kind in KEYLESS_KINDS else (self.key_ref or f"provider.{self.id}")

    def table_key(self) -> str | None:
        """Its column in the tables of models, recommendations and prices; None for a server the tables do not know."""
        if self.kind == OPENAI:
            url = self.base_url or PRESETS["openai"]
            if "api.openai.com" in url:
                return "openai"
            if "openrouter.ai" in url:
                return "openrouter"
            if self.preset and self.preset != "custom":       # a preset the models table has a column for (ollama)
                from .agents import table
                if self.preset in (table().get("models") or {}):
                    return self.preset
            return None
        return self.kind

    def needs_key(self) -> bool:
        """A key must be saved: every cloud service; not the CLIs, a local server or an own address (it may need none)."""
        if self.kind in KEYLESS_KINDS:
            return False
        if self.kind == OPENAI:
            return not self.local() and presets_mod.preset_of_url(self.base_url or PRESETS["openai"]) != "custom"
        return True

    def api(self) -> str:
        """How it is called: «ollama» for the Ollama preset (its own /api/chat), «openai» otherwise."""
        preset = presets_mod.get(self.preset) if self.kind == OPENAI else None
        return preset.api if preset else "openai"

    def local(self) -> bool:
        """A server on this computer (a local preset, or an own address on localhost): no key, nothing leaves it."""
        if self.kind != OPENAI:
            return False
        preset = presets_mod.get(self.preset)
        return bool(preset and preset.local) or presets_mod.is_local_url(self.base_url)

    def connection(self, model: str | None = None) -> ModelSettings:
        m = ModelSettings(provider=self.kind, model=self.default_model if model is None else model, json_mode=self.json_mode,
                          timeout_s=self.timeout_s, max_tokens=self.max_tokens, reasoning_effort=self.reasoning_effort,
                          key_ref=self.key_name() or "", provider_id=self.id)
        if self.kind == OPENAI:
            m.base_url = self.base_url or PRESETS["openai"]
            m.api = self.api()
        if self.kind == CODEX and self.bin:
            m.codex_bin = self.bin
        if self.kind == CLAUDE_CODE and self.bin:
            m.claude_bin = self.bin
        return m

    @classmethod
    def from_dict(cls, raw: dict) -> "Provider | None":
        known = {f.name for f in fields(cls)}
        data = {k: v for k, v in raw.items() if k in known}
        if not isinstance(data.get("id"), str) or not PROVIDER_ID.match(data["id"]) or data.get("kind") not in KINDS + RESERVED_KINDS:
            return None
        try:
            return cls(**data)
        except TypeError:
            return None


def _from_legacy(raw: dict) -> Provider | None:
    """The one connection of SMTV before stage 19 as a provider: id = its kind, so the agents' choices
    ({"provider": "openai", "model": …}) keep pointing at it; the same key under its old name."""
    kind = raw.get("provider")
    if kind not in PROVIDERS:
        return None
    p = Provider(id=kind, kind=kind, default_model=str(raw.get("model") or ""), key_ref="" if kind == CODEX else f"{kind}_api_key")
    if kind == OPENAI:
        p.base_url = str(raw.get("base_url") or PRESETS["openai"])
        p.preset = "openai" if "api.openai.com" in p.base_url else "openrouter" if "openrouter.ai" in p.base_url else "custom"
        if raw.get("json_mode") in ("schema", "object", "none"):
            p.json_mode = raw["json_mode"]
    if kind == CODEX:
        p.bin = "" if raw.get("codex_bin") in (None, "", "codex") else str(raw["codex_bin"])
    if raw.get("reasoning_effort") in ("minimal", "low", "medium", "high"):
        p.reasoning_effort = raw["reasoning_effort"]
    for k in ("timeout_s", "max_tokens"):
        if isinstance(raw.get(k), (int, float)) and raw[k] > 0:
            setattr(p, k, type(getattr(p, k))(raw[k]))
    p.name = default_name(kind, p.preset)
    return p


NAMES = {**{p.id: p.label for p in presets_mod.PRESETS_LIST}, ANTHROPIC: "Claude API", GEMINI: "Gemini",
         CODEX: "Codex CLI", CLAUDE_CODE: "Claude Code CLI", STREAMMOMENT: "StreamMoment"}


def default_name(kind: str, preset: str = "") -> str:
    return NAMES.get(preset if kind == OPENAI else kind) or NAMES.get(kind, kind)


@dataclass
class Settings:
    providers: list[Provider] = field(default_factory=list)
    tools: dict = field(default_factory=dict)   # per-tool settings, owned by each tool
    model: ModelSettings | None = None          # before stage 19: one connection. Read once, turned into a provider
    unknown: list = field(default_factory=list, repr=False)   # providers this version cannot read (a newer SMTV's): kept as they are

    def __post_init__(self):
        if self.model is not None:
            if not self.providers and self.model.provider:
                legacy = _from_legacy(asdict(self.model))
                if legacy:
                    self.providers.append(legacy)
            self.model = None

    def provider(self, pid: str) -> Provider | None:
        return next((p for p in self.providers if p.id == pid), None)

    def enabled(self) -> list[Provider]:
        return [p for p in self.providers if p.enabled and p.kind in KINDS]

    def new_id(self, kind: str) -> str:
        base = kind.replace("_", "-")
        taken = {p.id for p in self.providers} | {r.get("id") for r in self.unknown if isinstance(r, dict)}
        if base not in taken:
            return base
        n = 2
        while f"{base}-{n}" in taken:
            n += 1
        return f"{base}-{n}"

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        path = path or paths.settings_file()
        if not path.exists():
            return cls()
        try:
            raw = json.loads(_read(path))
            if not isinstance(raw, dict):
                raise ValueError(f"a {type(raw).__name__}, not an object")
        except FileNotFoundError:
            return cls()
        except (ValueError, UnicodeDecodeError) as e:     # the content is broken; a file that cannot be opened is not
            _set_aside(path, e)
            return cls()
        providers, unknown = [], []
        for r in raw.get("providers") or []:
            p = Provider.from_dict(r) if isinstance(r, dict) else None
            if p is not None and not any(o.id == p.id for o in providers):
                providers.append(p)
            else:     # written by a newer SMTV, or edited by hand: not shown, never lost on the next save
                unknown.append(r)
                print(f"smtv: a provider in {path.name} is not understood by this version and is left as it is: "
                      f"{str(r.get('kind') if isinstance(r, dict) else type(r).__name__)[:40]}", file=sys.stderr)
        if "providers" not in raw:
            legacy = _from_legacy(raw.get("model") or {})
            providers = [legacy] if legacy else []
        return cls(providers=providers, tools=raw.get("tools") or {}, unknown=unknown)

    def save(self, path: Path | None = None) -> Path:
        path = path or paths.settings_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        # a file of its own per write: two writers (the window and `smtv model`) never replace each other's half-file
        tmp = path.with_name(f"{path.stem}.{os.getpid()}.{_random.token_hex(4)}.tmp")
        taken = {p.id for p in self.providers}
        kept = [r for r in self.unknown if not (isinstance(r, dict) and r.get("id") in taken)]
        body = {"providers": [asdict(p) for p in self.providers] + kept, "tools": self.tools}
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(json.dumps(body, ensure_ascii=False, indent=2))
                f.flush()
                os.fsync(f.fileno())
            _replace(tmp, path)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
        return path

    @classmethod
    @contextmanager
    def edit(cls, path: Path | None = None):
        """`with Settings.edit() as s: s.tools[...] = ...` — load, change and save as one step.

        One edit at a time in this process and on this computer (the window, a job and `smtv model` are separate
        processes): a switch flipped while a provider is added never loses either change. Nothing is saved when the
        block raises.
        """
        with lock():
            s = cls.load(path)
            yield s
            s.save(path)


# --- one edit at a time ------------------------------------------------------------------------------------

BROKEN: list[Path] = []   # copies of unreadable settings files set aside by this process, the newest last


def _replace(tmp: Path, path: Path, tries: int = 20) -> None:
    """os.replace that waits out a moment of «file in use»: on Windows a reader (another SMTV process, an antivirus)
    holding settings.json open makes the replace fail with PermissionError for that moment."""
    for attempt in range(tries):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == tries - 1:
                raise
            time.sleep(0.02 * (attempt + 1))


def _read(path: Path, tries: int = 5) -> str:
    """The file's text. A moment of «file in use» (an antivirus scan on Windows, a save under way) is waited out; a file
    that stays unreadable raises OSError — it is never taken for a broken one and set aside with the person's settings."""
    for attempt in range(tries):
        try:
            return path.read_text(encoding="utf-8")
        except FileNotFoundError:
            raise
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(0.1 * (attempt + 1))
    raise OSError(f"{path} could not be read")


def _set_aside(path: Path, error: Exception) -> None:
    """An unreadable settings file (empty after a power cut, edited by hand) is kept aside, never thrown away.

    SMTV then starts with empty settings: a broken file must not stop the window, `smtv doctor` or a job.
    """
    stamp = time.strftime("%Y%m%d-%H%M%S")
    copy = path.with_name(f"{path.stem}.broken-{stamp}.json")
    n = 2
    while copy.exists():
        copy = path.with_name(f"{path.stem}.broken-{stamp}-{n}.json")
        n += 1
    try:
        os.replace(path, copy)
    except OSError:
        try:                     # cannot move it (held open on Windows): keep a copy before the next save writes over it
            shutil.copy2(path, copy)
        except OSError:
            copy = path
    if copy not in BROKEN:
        BROKEN.append(copy)
    print(f"smtv: the settings file could not be read ({type(error).__name__}: {str(error)[:120]}); "
          f"it is kept as {copy.name} and Clip It! starts with empty settings", file=sys.stderr)


def broken_notice() -> str | None:
    """The name of the kept copy when settings had to be set aside, or None. The window words it in its own language
    (`set_broken` in web/i18n)."""
    return BROKEN[-1].name if BROKEN else None


_LOCK = ProcessLock(lambda: paths.home() / "run" / "settings.lock", "settings")


def lock() -> ProcessLock:
    """The one settings lock: `with lock(): load, change, save`."""
    return _LOCK


def _keyring():
    if os.environ.get("SMTV_NO_KEYCHAIN", "").strip() == "1":     # tests, and anyone who prefers the encrypted file
        return None
    try:
        import keyring  # type: ignore
        from keyring.backends import fail  # type: ignore
    except ImportError:
        return None
    return None if isinstance(keyring.get_keyring(), fail.Keyring) else keyring


def _vault():
    from .vault import Vault
    return Vault(paths.secrets_file(), paths.secrets_key_file())


def secrets_backend() -> str:
    """Where keys are kept: 'keychain' or 'file' (encrypted, in the SMTV folder)."""
    return "keychain" if _keyring() else "file"


def get_secret(name: str) -> str | None:
    """An environment variable SMTV_<NAME> wins, then the keychain, then the encrypted file."""
    if not name:
        return None
    env = os.environ.get("SMTV_" + re.sub(r"[^A-Za-z0-9]", "_", name).upper(), "").strip()
    if env:
        return env
    kr = _keyring()
    if kr:
        value = kr.get_password(KEYRING_SERVICE, name)
        if value:
            return value
    return _vault().get(name)


def set_secret(name: str, value: str) -> str:
    """Store a key; returns where it went. Never logs or prints the value."""
    kr = _keyring()
    if kr:
        kr.set_password(KEYRING_SERVICE, name, value)
        return "keychain"
    _vault().set(name, value)
    return "file"


def delete_secret(name: str) -> None:
    """Forget a key wherever it is kept. A key that is not there is not an error."""
    kr = _keyring()
    if kr:
        try:
            kr.delete_password(KEYRING_SERVICE, name)
        except Exception as e:  # noqa: BLE001 — keyring raises PasswordDeleteError for a key it does not have
            if type(e).__name__ != "PasswordDeleteError":
                raise
    if paths.secrets_file().exists():
        _vault().delete(name)


def secret_names(settings: Settings | None = None) -> list[str]:
    """Every name a key may be saved under on this computer: each provider's, the old ones, the phone key, the file's."""
    names = {f"{k}_api_key" for k in PROVIDERS if k != CODEX} | {"phone_key"}
    for p in (settings or Settings.load()).providers:
        if p.key_name():
            names.add(p.key_name())
    try:
        names.update(_vault().names())
    except Exception:  # noqa: BLE001 — a damaged file has no names to give; reading a key from it says so
        pass
    return sorted(names)
