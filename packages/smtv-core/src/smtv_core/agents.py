"""Agents: a prompt with its answer schema, the step it serves and what it needs from a model (stage 10).

A tool declares its agents in `Tool.agents`. Agents shared by many tools — choosing the 9:16 layout, finding ad
banners and the critic of a finished clip — are declared here once (`CORE`); a tool that uses them lists them with `core("layout", "banner")`, and the
window shows the same card on the page of every such tool, marked «shared, from the core».

Which provider and model an agent uses (stage 19: several providers at once, chosen in «Settings → Agents»):
- the person's own choice for this agent — a provider of the list and a model of it — kept in the tool's settings
  (`tools.<tool>.agents.<agent>` = {provider: <provider id>, model}), while that provider is on the list, switched on and
  able to do what the agent needs;
- otherwise the first such provider of the list with the model recommended for this agent in `models.json` of the
  prompts repository (copied in with the prompts), or, for a server the table does not know (a custom OpenAI-compatible
  address), the provider's own default model.
So a provider switched off or removed sends its agents to the recommended models of the others.
An agent that reads frames is never given a provider that cannot pass them (the Claude Code CLI). A weaker model, or a
model the table says cannot read images, gets a warning, never a refusal — except where a tested recommendation says
the model holds.
Prices come from the built-in table `prices.json` (dollars per million tokens), never from the person; the CLIs are paid
by the subscription.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Callable

from . import prompts
from .settings import CLAUDE_CODE, CLI_KINDS, KEYLESS_KINDS, STREAMMOMENT, ModelSettings, Provider, Settings

LEVELS = ("light", "medium", "strong")
AGENT_ID = re.compile(r"^[a-z0-9_-]{1,40}$")


@dataclass(frozen=True)
class Needs:
    """What an agent needs from a model. How much text one call reads and why this level: its words
    `agent.<id>.needs` and `agent.<id>.why`."""
    level: str                      # light | medium | strong
    images: bool = False            # reads frames
    strict_json: bool = True        # the answer must match the schema exactly


@dataclass(frozen=True)
class Agent:
    """Its words are not here but in the language files (V9): the tool's `web/i18n/<language>.json` — the window's
    for the core's shared agents — under `agent.<id>.title`, `.short` (one plain sentence for a newcomer), `.does`
    (under «More»), `.stage` (the step of the tool it serves), `.needs` and `.why` (see `Needs`). A key the files lack
    is shown as it is."""
    id: str                         # [a-z0-9_-]: the key of models.json and of the tool's settings
    prompt: str                     # path in the prompts repository, e.g. "vod/pass1-prompt.txt"
    schema: str                     # answer schema name, e.g. "pass1"
    needs: Needs
    purposes: tuple[str, ...] = ()  # the `purpose` of its model_call events; empty: its id
    shared: bool = False            # declared in the core, used by many tools

    def calls(self) -> tuple[str, ...]:
        return self.purposes or (self.id,)

    def as_dict(self) -> dict:
        return {**asdict(self), "purposes": list(self.calls())}


LAYOUT = Agent(id="layout", shared=True, prompt="fit/layout-prompt.txt", schema="layout", needs=Needs(level="medium", images=True))

BANNER = Agent(id="banner", shared=True, prompt="fit/banner-prompt.txt", schema="banner", needs=Needs(level="medium", images=True))

CRITIC = Agent(id="critic", shared=True, prompt="vod/critic-prompt.txt", schema="critic", needs=Needs(level="medium", images=True))

CORE = {a.id: a for a in (LAYOUT, BANNER, CRITIC)}


def core(*ids: str) -> list[Agent]:
    """The shared agents a tool uses, by id."""
    return [CORE[i] for i in ids]


# --- the tables: prompts/models.json and prompts/prices.json ---------------------------------------------

@lru_cache(maxsize=1)
def table() -> dict:
    return json.loads((prompts.HERE / "models.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def price_table() -> dict:
    try:
        return json.loads((prompts.HERE / "prices.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"prices": {}}


def known_models(tkey: str | None) -> dict:
    """{model id: {"level", "images", "label"?}} the table knows for a provider's column (`Provider.table_key`)."""
    return dict(table().get("models", {}).get(tkey) or {}) if tkey else {}


def recommendation(agent_id: str, tkey: str | None) -> dict | None:
    """{"model", "tested": [...]} for an agent with a provider's column, or None when the table has none."""
    row = (table().get("agents", {}).get(agent_id) or {}).get(tkey) if tkey else None
    return {"model": row["model"], "tested": list(row.get("tested") or [])} if row else None


def price(tkey: str | None, model: str) -> dict | None:
    """{"in", "out"} dollars per million tokens from the built-in table, or None when unknown."""
    row = (price_table().get("prices", {}).get(tkey) or {}).get(model) if tkey else None
    if isinstance(row, dict) and isinstance(row.get("in"), (int, float)) and isinstance(row.get("out"), (int, float)):
        return {"in": float(row["in"]), "out": float(row["out"])}
    return None


def sees_images(kind: str) -> bool:
    """Can this kind of provider be given frames at all. The Claude Code CLI is called with text only."""
    return kind != CLAUDE_CODE


def suits(agent: Agent, p: Provider) -> bool:
    return not agent.needs.images or sees_images(p.kind)


def marks(agent: Agent, p: Provider | str | None, model: str, live: dict | None = None) -> dict:
    """What the window says about a model for an agent: recommended, tested (and how), images, price, warnings.
    `p` is a provider, or a table column; `live` is what the provider's own list says of this model (OpenRouter
    gives images and prices)."""
    kind = p.kind if isinstance(p, Provider) else (p or "")
    tkey = p.table_key() if isinstance(p, Provider) else p
    rec = recommendation(agent.id, tkey)
    tested = [r for r in (rec or {}).get("tested", []) if r.get("model") == model]
    info = known_models(tkey).get(model)
    live = live or {}
    images = (info or {}).get("images") if info is not None else live.get("images")
    if not sees_images(kind):
        images = False
    level = (info or {}).get("level")
    recommended = bool(rec) and rec["model"] == model
    warnings = []
    if level in LEVELS and LEVELS.index(level) < LEVELS.index(agent.needs.level) and not (recommended and tested):
        warnings.append("weaker")
    if agent.needs.images and images is False:
        warnings.append("no_images")
    if kind == STREAMMOMENT:
        cost = {"kind": "balance"}         # paid from the StreamMoment account's balance; the model is our server's
    elif kind in CLI_KINDS:
        cost = {"kind": "subscription"}
    else:
        known_price = price(tkey, model) or live.get("price")
        cost = {"kind": "table", **known_price} if known_price else {"kind": "unknown"}
    return {"recommended": recommended, "tested": tested, "known": info is not None, "level": level, "images": images,
            "label": (info or {}).get("label") or "", "warnings": warnings, "price": cost}


# --- the person's choice, kept in the tool's settings ---------------------------------------------------

def _own(settings: Settings, tool: str) -> dict:
    return ((settings.tools.get(tool) or {}).get("agents") or {})


def set_model(settings: Settings, tool: str, agent: Agent, provider_id: str, model: str) -> None:
    """The agent uses this provider and model from now on. A provider that is not on the list, switched off or cannot
    pass the frames the agent needs is refused."""
    p = settings.provider(provider_id)
    if p is None or not p.enabled:
        raise ValueError(f"no provider {provider_id} switched on: add it in «Settings → Providers»")
    if not suits(agent, p):
        raise ValueError(f"{p.name or p.id} cannot pass frames, and «{agent.id}» reads them")
    settings.tools.setdefault(tool, {}).setdefault("agents", {})[agent.id] = {"provider": p.id, "model": model}


def reset_model(settings: Settings, tool: str, agent_id: str) -> None:
    """Back to the recommended model of the first suitable provider."""
    own = _own(settings, tool)
    own.pop(agent_id, None)
    if not own and isinstance(settings.tools.get(tool), dict):
        settings.tools[tool].pop("agents", None)


def forget_provider(settings: Settings, provider_id: str) -> int:
    """A removed provider: every choice made for it goes, so its agents follow the recommendations of the others."""
    n = 0
    for tool in list(settings.tools):
        own = _own(settings, tool)
        for agent_id in [a for a, c in own.items() if isinstance(c, dict) and c.get("provider") == provider_id]:
            reset_model(settings, tool, agent_id)
            n += 1
    return n


def assign_recommended(settings: Settings, provider_id: str, users: dict[str, list[Agent]]) -> list[tuple[str, str, str]]:
    """«Give the agents this provider's recommended models»: every agent of every tool (`users` = {tool: its agents})
    that the provider suits and the table has a model for. Returns [(tool, agent, model)]."""
    p = settings.provider(provider_id)
    if p is None or not p.enabled:
        raise ValueError(f"no provider {provider_id} switched on")
    done = []
    for tool, tool_agents in users.items():
        for agent in tool_agents:
            rec = recommendation(agent.id, p.table_key())
            if rec is not None and suits(agent, p):
                set_model(settings, tool, agent, p.id, rec["model"])
                done.append((tool, agent.id, rec["model"]))
    return done


@dataclass
class Choice:
    model: ModelSettings            # the provider's connection with this agent's model: what is called
    source: str                     # own | recommended | connection | none
    provider: Provider | None = None
    instead_of: str = ""            # the person chose a provider that is off, removed or cannot do this: its name

    def as_dict(self, agent: Agent) -> dict:
        p = self.provider
        base = {"provider": p.id if p else "", "provider_name": (p.name or p.id) if p else "", "kind": p.kind if p else "",
                "model": self.model.model, "source": self.source, "instead_of": self.instead_of}
        return {**base, **marks(agent, p, self.model.model)} if p else {**base, **marks(agent, None, "")}


def default_of(agent: Agent, p: Provider) -> tuple[str, str] | None:
    """(model, source) an agent takes from a provider when nobody chose: the table's recommendation, else the
    provider's default model (a CLI's empty id = its own default). None: this provider has nothing for the agent."""
    if not p.enabled or not suits(agent, p):
        return None
    rec = recommendation(agent.id, p.table_key())
    if rec is not None:
        return rec["model"], "recommended"
    if p.default_model or p.kind in KEYLESS_KINDS:
        return p.default_model, "connection"
    return None


def _priced(p: Provider, model: str) -> ModelSettings:
    m = p.connection(model)
    cost = price(p.table_key(), model) if p.kind not in KEYLESS_KINDS else None
    if cost:
        m.price_in, m.price_out = cost["in"], cost["out"]
    return m


def _for(agent: Agent, m: ModelSettings) -> ModelSettings:
    m.agent = agent.id
    return m


def resolve(settings: Settings, tool: str, agent: Agent) -> Choice:
    own = _own(settings, tool).get(agent.id)
    instead_of = ""
    if isinstance(own, dict) and isinstance(own.get("model"), str):
        p = settings.provider(str(own.get("provider") or ""))
        if p is not None and p.enabled and suits(agent, p) and (own["model"] or p.kind in KEYLESS_KINDS):
            return Choice(_for(agent, _priced(p, own["model"])), "own", p)
        # the chosen provider is off or cannot do this: the recommended one of the others, and the window says so
        instead_of = (p.name or p.id) if p is not None else str(own.get("provider") or "")
    for p in settings.enabled():
        found = default_of(agent, p)
        if found:
            return Choice(_for(agent, _priced(p, found[0])), found[1], p, instead_of)
    return Choice(ModelSettings(), "none", None, instead_of)


def default_connection(settings: Settings) -> ModelSettings:
    """The first switched-on provider with its default model: for a call no agent declares."""
    for p in settings.enabled():
        if p.kind != STREAMMOMENT and (p.default_model or p.kind in CLI_KINDS or p.table_key()):   # StreamMoment takes only our agents
            return _priced(p, p.default_model)
    return ModelSettings()


def models_for(settings: Settings, tool: str, agents: list[Agent]) -> Callable[[str], ModelSettings]:
    """purpose of a call -> the model to call. A purpose no agent declares uses the first provider as it is."""
    by_purpose = {p: resolve(settings, tool, a).model for a in agents for p in a.calls()}
    fallback = default_connection(settings)
    return lambda purpose: by_purpose.get(purpose, fallback)
