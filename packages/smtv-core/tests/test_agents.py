"""Agents (stages 10 and 19): declarations, the recommended model for each provider, several providers at once, the
person's choice of provider and model and its fallback, the filter by images, warnings, prices from the built-in table,
and settings from before stage 19."""
import json
import os

import pytest

from smtv_core import agents, prompts
from smtv_core.agents import Agent, Needs
from smtv_core.settings import ModelSettings, Provider, Settings


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    for key in list(os.environ):
        if key.startswith("SMTV_") and key != "SMTV_HOME":
            monkeypatch.delenv(key)
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)


def connected(provider, model="", **kw):
    """Settings as SMTV wrote them before stage 19: one connection. Read, it is one provider."""
    return Settings(model=ModelSettings(provider=provider, model=model, **kw))


def prov(pid, kind, **kw):
    return Provider(id=pid, kind=kind, name=kw.pop("name", pid), **kw)


def test_core_declares_the_shared_agents_once_with_their_prompts():
    assert set(agents.CORE) == {"layout", "banner", "critic"}
    for a in agents.CORE.values():
        assert a.shared and a.needs.images and a.needs.level in agents.LEVELS
        assert agents.AGENT_ID.match(a.id)
        assert prompts.text(a.prompt).strip() and prompts.schema(a.schema)
        # its words are in the window's language files (V9): smtv/tests/test_i18n.py checks them
    assert agents.core("banner", "layout") == [agents.BANNER, agents.LAYOUT]


def test_the_bundled_table_matches_the_prompts_version():
    t = agents.table()
    assert t["prompts"]["version"] == prompts.version()
    for agent_id in ("layout", "banner", "critic"):
        for provider in ("codex", "openai", "anthropic", "gemini"):
            assert agents.recommendation(agent_id, provider) is not None


@pytest.mark.parametrize("provider,expected", [("codex", ""), ("anthropic", "claude-sonnet-5-5"), ("openai", "gpt-6.1-terra"),
                                               ("gemini", "gemini-3.7-flash")])
def test_by_default_the_recommended_model_of_the_connected_provider(provider, expected):
    choice = agents.resolve(connected(provider, "something-else"), "vodcut", agents.LAYOUT)
    assert (choice.model.provider, choice.model.model, choice.source) == (provider, expected, "recommended")


def test_only_codex_was_tested_and_the_table_says_so():
    tested = agents.marks(agents.LAYOUT, "codex", "")
    assert tested["recommended"] and tested["tested"] and tested["tested"][0]["date"] == "2026-11-20"
    untested = agents.marks(agents.LAYOUT, "anthropic", "claude-sonnet-5-5")
    assert untested["recommended"] and untested["tested"] == []


def test_an_openai_compatible_server_keeps_its_own_model():
    s = connected("openai", "qwen2.5-vl", base_url="http://localhost:11434/v1")
    choice = agents.resolve(s, "vodcut", agents.LAYOUT)
    assert (choice.model.model, choice.source) == ("qwen2.5-vl", "connection")


def test_an_agent_the_table_does_not_know_uses_the_connection():
    mine = Agent(id="mine", prompt="vod/pass1-prompt.txt", schema="pass1", needs=Needs(level="light"))
    choice = agents.resolve(connected("anthropic", "claude-haiku-5-5"), "demo", mine)
    assert (choice.model.model, choice.source) == ("claude-haiku-5-5", "connection")


def test_a_chosen_model_is_kept_in_the_tools_settings_and_used(isolated_home):
    s = connected("anthropic", "claude-opus-5-5")
    agents.set_model(s, "vodcut", agents.LAYOUT, "anthropic", "claude-haiku-5-5")
    s.save()
    again = Settings.load()
    assert again.tools["vodcut"]["agents"]["layout"] == {"provider": "anthropic", "model": "claude-haiku-5-5"}
    choice = agents.resolve(again, "vodcut", agents.LAYOUT)
    assert (choice.model.model, choice.source, choice.provider.id) == ("claude-haiku-5-5", "own", "anthropic")
    # another tool that uses the same shared agent keeps its own choice
    assert agents.resolve(again, "livecut", agents.LAYOUT).source == "recommended"
    agents.reset_model(again, "vodcut", "layout")
    assert "agents" not in again.tools["vodcut"]
    assert agents.resolve(again, "vodcut", agents.LAYOUT).model.model == "claude-sonnet-5-5"


def test_several_providers_of_one_kind_each_with_its_own_key(isolated_home):
    from smtv_core.settings import get_secret, set_secret
    s = Settings(providers=[prov("openai", "openai", name="OpenAI — personal", base_url="https://api.openai.com/v1"),
                            prov("openai-2", "openai", name="OpenAI — work", base_url="https://api.openai.com/v1")])
    set_secret(s.providers[0].key_name(), "sk-personal-0000000000")
    set_secret(s.providers[1].key_name(), "sk-work-00000000000000")
    agents.set_model(s, "vodcut", agents.LAYOUT, "openai-2", "gpt-6.2-astra")
    s.save()
    again = Settings.load()
    assert [p.name for p in again.providers] == ["OpenAI — personal", "OpenAI — work"]
    work = agents.resolve(again, "vodcut", agents.LAYOUT).model
    assert (work.provider_id, work.model, work.key_ref) == ("openai-2", "gpt-6.2-astra", "provider.openai-2")
    assert get_secret(work.key_name()) == "sk-work-00000000000000"
    personal = agents.resolve(again, "vodcut", agents.BANNER).model       # no choice: the first provider of the list
    assert (personal.provider_id, get_secret(personal.key_name())) == ("openai", "sk-personal-0000000000")
    assert again.new_id("openai") == "openai-3"


def test_switching_off_or_removing_a_provider_sends_its_agents_to_the_others():
    s = Settings(providers=[prov("anthropic", "anthropic"), prov("gemini", "gemini")])
    agents.set_model(s, "vodcut", agents.LAYOUT, "gemini", "gemini-2.5-pro")
    assert agents.resolve(s, "vodcut", agents.LAYOUT).model.model == "gemini-2.5-pro"
    s.provider("gemini").enabled = False                          # switched off: its agents go to the recommended of the rest
    choice = agents.resolve(s, "vodcut", agents.LAYOUT)
    assert (choice.provider.id, choice.model.model, choice.source) == ("anthropic", "claude-sonnet-5-5", "recommended")
    s.provider("gemini").enabled = True                           # back on: the choice is kept
    assert agents.resolve(s, "vodcut", agents.LAYOUT).model.model == "gemini-2.5-pro"
    s.providers.remove(s.provider("gemini"))                      # removed: the choice goes too
    assert agents.forget_provider(s, "gemini") == 1
    assert "agents" not in s.tools["vodcut"]
    assert agents.resolve(s, "vodcut", agents.LAYOUT).provider.id == "anthropic"
    s.providers.clear()
    assert agents.resolve(s, "vodcut", agents.LAYOUT).source == "none"
    with pytest.raises(ValueError):
        agents.set_model(s, "vodcut", agents.LAYOUT, "anthropic", "x")


def test_an_agent_that_reads_frames_is_never_given_a_provider_that_cannot_pass_them():
    s = Settings(providers=[prov("claude-code", "claude_code"), prov("codex", "codex")])
    # scan reads text: the first provider, Claude Code; layout reads frames: Claude Code is skipped
    assert agents.resolve(s, "vodcut", agents.LAYOUT).provider.id == "codex"
    with pytest.raises(ValueError, match="frames"):
        agents.set_model(s, "vodcut", agents.LAYOUT, "claude-code", "claude-sonnet-5-5")
    # a choice made by hand in the file is not obeyed either
    s.tools["vodcut"] = {"agents": {"layout": {"provider": "claude-code", "model": "claude-sonnet-5-5"}}}
    assert agents.resolve(s, "vodcut", agents.LAYOUT).provider.id == "codex"
    only = Settings(providers=[prov("claude-code", "claude_code")])
    assert agents.resolve(only, "vodcut", agents.LAYOUT).source == "none"
    assert agents.marks(agents.LAYOUT, only.providers[0], "claude-sonnet-5-5")["warnings"] == ["no_images"]
    assert agents.suits(agents.LAYOUT, only.providers[0]) is False


def test_assigning_a_providers_recommended_models():
    s = Settings(providers=[prov("codex", "codex"), prov("claude-code", "claude_code")])
    scan = Agent(id="scan", prompt="vod/pass1-prompt.txt", schema="pass1", needs=Needs(level="strong"))
    done = agents.assign_recommended(s, "claude-code", {"vodcut": [scan, agents.LAYOUT]})
    assert done == [("vodcut", "scan", "claude-opus-5-5")]        # layout needs frames: left as it was
    assert agents.resolve(s, "vodcut", scan).provider.id == "claude-code"
    assert agents.resolve(s, "vodcut", agents.LAYOUT).provider.id == "codex"


def test_a_weaker_model_or_one_without_images_gets_a_warning_not_a_refusal(monkeypatch):
    assert agents.marks(agents.LAYOUT, "anthropic", "claude-haiku-5-5")["warnings"] == ["weaker"]
    assert agents.marks(agents.LAYOUT, "anthropic", "claude-opus-5-5")["warnings"] == []
    assert agents.marks(agents.LAYOUT, "anthropic", "claude-unknown")["known"] is False
    table = json.loads(json.dumps(agents.table()))
    table["models"]["openai"]["text-only"] = {"level": "strong", "images": False}
    monkeypatch.setattr(agents, "table", lambda: table)
    assert agents.marks(agents.LAYOUT, "openai", "text-only")["warnings"] == ["no_images"]
    s = connected("openai")
    agents.set_model(s, "vodcut", agents.LAYOUT, "openai", "text-only")
    assert agents.resolve(s, "vodcut", agents.LAYOUT).model.model == "text-only"      # still used


def test_scan_in_codex_is_luna_tested_on_stage_15():
    rec = agents.recommendation("scan", "codex")
    assert rec["model"] == "gpt-6-luna"
    luna = [r for r in rec["tested"] if r["model"] == "gpt-6-luna"]
    assert luna and "104" in luna[0]["result"] and "32" in luna[0]["result"]
    scan = Agent(id="scan", prompt="vod/pass1-prompt.txt", schema="pass1", needs=Needs(level="strong"))
    m = agents.marks(scan, "codex", "gpt-6-luna")
    assert m["recommended"] and m["tested"] and m["warnings"] == []        # a tested recommendation is not «weaker»
    assert agents.resolve(connected("codex"), "vodcut", scan).model.model == "gpt-6-luna"


def test_every_recommendation_says_whether_it_was_tested():
    for agent_id, row in agents.table()["agents"].items():
        for column, rec in row.items():
            assert isinstance(rec["tested"], list), (agent_id, column)
            for run in rec["tested"]:
                assert run["date"] and run["result"] and run["with"]


def test_prices_come_from_the_built_in_table_and_the_clis_are_by_subscription():
    s = connected("anthropic", "claude-sonnet-5-5", price_in=99.0, price_out=99.0)    # the old prices of the person: gone
    layout = agents.resolve(s, "vodcut", agents.LAYOUT).model
    assert (layout.price_in, layout.price_out) == (2.0, 10.0)
    assert layout.cost(1_000_000, 0) == 2.0
    agents.set_model(s, "vodcut", agents.LAYOUT, "anthropic", "claude-unknown")
    assert agents.resolve(s, "vodcut", agents.LAYOUT).model.cost(1_000_000, 0) is None
    assert agents.marks(agents.LAYOUT, "anthropic", "claude-unknown")["price"] == {"kind": "unknown"}
    assert agents.marks(agents.LAYOUT, "openrouter", "anthropic/claude-sonnet-5.5")["price"] == {"kind": "table", "in": 2.0, "out": 10.0}
    assert agents.marks(agents.LAYOUT, "codex", "")["price"] == {"kind": "subscription"}
    assert agents.resolve(connected("codex"), "vodcut", agents.LAYOUT).model.cost(1000, 1000) is None
    # a price the provider's own list gives (OpenRouter) for a model the table does not know
    live = {"price": {"in": 0.5, "out": 1.5}, "images": True}
    assert agents.marks(agents.LAYOUT, "openrouter", "x/new-model", live)["price"] == {"kind": "table", "in": 0.5, "out": 1.5}


def test_openrouter_has_its_own_ids_and_a_custom_server_its_default_model():
    s = Settings(providers=[prov("openrouter", "openai", preset="openrouter", base_url="https://openrouter.ai/api/v1")])
    assert s.providers[0].table_key() == "openrouter"
    assert agents.resolve(s, "vodcut", agents.LAYOUT).model.model == "anthropic/claude-sonnet-5.5"
    own = Settings(providers=[prov("custom", "openai", preset="custom", base_url="http://127.0.0.1:11434/v1")])
    assert agents.resolve(own, "vodcut", agents.LAYOUT).source == "none"     # nothing to call yet
    own.providers[0].default_model = "qwen2.5-vl"
    assert (agents.resolve(own, "vodcut", agents.LAYOUT).model.model, agents.resolve(own, "vodcut", agents.LAYOUT).source) == ("qwen2.5-vl", "connection")


def test_models_for_maps_every_purpose_of_an_agent():
    scan = Agent(id="scan", purposes=("scan", "scan_repair"), prompt="vod/pass1-prompt.txt",
                 schema="pass1", needs=Needs(level="strong"))
    s = connected("anthropic", "claude-haiku-5-5")
    agents.set_model(s, "vodcut", scan, "anthropic", "claude-opus-5-5")
    pick = agents.models_for(s, "vodcut", [scan, agents.LAYOUT])
    assert pick("scan").model == pick("scan_repair").model == "claude-opus-5-5"
    assert pick("layout").model == "claude-sonnet-5-5"
    assert pick("something").model == "claude-haiku-5-5"


# --- settings from before stage 19 ------------------------------------------------------------------------

def test_old_settings_become_one_provider_with_the_same_key_and_the_same_models(isolated_home):
    from smtv_core import paths
    from smtv_core.settings import get_secret, set_secret
    paths.home().mkdir(parents=True)
    paths.settings_file().write_text(json.dumps({
        "model": {"provider": "openai", "model": "gpt-6.2-sol", "base_url": "https://api.openai.com/v1", "json_mode": "object",
                  "price_in": 2.0, "price_out": 8.0, "codex_bin": "codex", "reasoning_effort": "high", "timeout_s": 120},
        "tools": {"vodcut": {"loudness": True, "agents": {"scan": {"provider": "openai", "model": "gpt-6.2-astra"}}}}}), encoding="utf-8")
    set_secret("openai_api_key", "sk-old-key-0000000000")
    s = Settings.load()
    assert len(s.providers) == 1
    p = s.providers[0]
    assert (p.id, p.kind, p.name, p.preset, p.json_mode, p.reasoning_effort, p.timeout_s, p.default_model) == (
        "openai", "openai", "OpenAI", "openai", "object", "high", 120.0, "gpt-6.2-sol")
    assert get_secret(p.key_name()) == "sk-old-key-0000000000"            # the same key, nothing to type again
    scan = Agent(id="scan", prompt="vod/pass1-prompt.txt", schema="pass1", needs=Needs(level="strong"))
    assert agents.resolve(s, "vodcut", scan).model.model == "gpt-6.2-astra"            # the choice made in its card
    assert agents.resolve(s, "vodcut", agents.LAYOUT).model.model == "gpt-6.1-terra"   # the recommendation, as before
    assert s.tools["vodcut"]["loudness"] is True
    s.save()
    raw = json.loads(paths.settings_file().read_text(encoding="utf-8"))
    assert "model" not in raw and raw["providers"][0]["key_ref"] == "openai_api_key"
    assert agents.resolve(Settings.load(), "vodcut", scan).model.model == "gpt-6.2-astra"


@pytest.mark.parametrize("old,kind,model", [({"provider": "codex", "model": ""}, "codex", ""),
                                             ({"provider": "openai", "model": "llama3", "base_url": "http://localhost:11434/v1"}, "openai", "llama3"),
                                             ({"provider": "gemini", "model": "gemini-2.5-pro"}, "gemini", "gemini-2.5-pro")])
def test_every_old_connection_moves(isolated_home, old, kind, model):
    from smtv_core import paths
    paths.home().mkdir(parents=True)
    paths.settings_file().write_text(json.dumps({"model": old, "tools": {}}), encoding="utf-8")
    p = Settings.load().providers[0]
    assert (p.kind, p.default_model) == (kind, model)
    if old.get("base_url"):
        assert (p.preset, p.base_url, p.table_key()) == ("custom", old["base_url"], None)
        assert agents.resolve(Settings.load(), "vodcut", agents.LAYOUT).model.model == "llama3"   # its own model, as before


def test_no_old_connection_means_no_provider(isolated_home):
    from smtv_core import paths
    paths.home().mkdir(parents=True)
    paths.settings_file().write_text(json.dumps({"model": {"provider": ""}, "tools": {}}), encoding="utf-8")
    assert Settings.load().providers == []


def test_a_provider_a_newer_smtv_wrote_is_kept_on_save(isolated_home):
    from smtv_core import paths
    paths.home().mkdir(parents=True)
    future = {"id": "streammoment", "kind": "something-from-the-future", "name": "Future"}
    paths.settings_file().write_text(json.dumps({"providers": [{"id": "codex", "kind": "codex"}, future], "tools": {}}), encoding="utf-8")
    s = Settings.load()
    assert [p.id for p in s.providers] == ["codex"] and s.new_id("streammoment") == "streammoment-2"
    s.save()
    assert json.loads(paths.settings_file().read_text(encoding="utf-8"))["providers"][1] == future


def test_the_window_says_when_a_chosen_provider_is_not_used():
    s = Settings(providers=[prov("anthropic", "anthropic", name="Claude — work"), prov("gemini", "gemini")])
    agents.set_model(s, "vodcut", agents.LAYOUT, "anthropic", "claude-opus-5-5")
    s.provider("anthropic").enabled = False
    d = agents.resolve(s, "vodcut", agents.LAYOUT).as_dict(agents.LAYOUT)
    assert (d["provider"], d["source"], d["instead_of"]) == ("gemini", "recommended", "Claude — work")
    s.provider("anthropic").enabled = True
    assert agents.resolve(s, "vodcut", agents.LAYOUT).as_dict(agents.LAYOUT)["instead_of"] == ""
