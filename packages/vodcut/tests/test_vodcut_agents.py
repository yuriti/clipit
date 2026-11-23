"""VodCut's agents (stage 10): declared in its Tool, and the pipeline and the renderer really call each agent's model."""
import json

import pytest

from smtv_core import agents
from smtv_core.events import read
from smtv_core.llm import Answer
from smtv_core.settings import ModelSettings, Provider, Settings

from vodcut import render, tool as vodcut_tool
from vodcut.agents import AGENTS
from vodcut.model import Asker
from test_analysis import fake_caller, run_demo
from test_render_step import CAM, GAME, clip, make_job


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)


def test_vodcut_declares_its_agents_and_uses_the_shared_ones():
    assert [a.id for a in vodcut_tool.tool.agents] == ["scan", "rating", "fit", "recap", "layout", "banner", "critic"]
    own = [a for a in vodcut_tool.tool.agents if not a.shared]
    assert [a.id for a in own] == ["scan", "rating", "fit", "recap"]
    recap = own[3]
    assert recap.calls() == ("recap",) and recap.needs.level == "strong" and recap.schema == "recap" and not recap.needs.images
    assert all(agents.recommendation("recap", p) for p in ("codex", "openai", "anthropic", "gemini"))
    fit = own[2]
    assert fit.calls() == ("fit", "fit_repair") and fit.needs.level == "medium" and fit.schema == "fit"
    assert all(agents.recommendation("fit", p) for p in ("codex", "openai", "anthropic", "gemini"))   # models.json has a row
    assert agents.CORE["layout"] in vodcut_tool.tool.agents and agents.CORE["banner"] in vodcut_tool.tool.agents
    scan = own[0]
    assert scan.calls() == ("scan", "scan_repair") and scan.needs.level == "strong" and not scan.needs.images


def test_the_pipeline_calls_each_agent_with_its_own_model(tmp_path, monkeypatch):
    s = Settings(model=ModelSettings(provider="anthropic", model="claude-haiku-5-5"))
    agents.set_model(s, "vodcut", AGENTS[0], "anthropic", "claude-opus-4-1")          # chosen in «Settings → Agents»
    s.save()
    called = []

    def caller(model, prompt, schema, images=None):
        called.append(("scan" if "Windows to read:" in prompt else "rating", model.provider, model.model))
        return fake_caller(model, prompt, schema)

    asker = vodcut_tool._asker(Settings.load())
    monkeypatch.setattr("test_analysis.Asker", lambda model, caller_: Asker(model, caller_, models=asker.models))
    job, _ = run_demo(tmp_path, monkeypatch, caller=caller)
    assert {c for c in called if c[0] == "scan"} == {("scan", "anthropic", "claude-opus-4-1")}
    assert {c for c in called if c[0] == "rating"} == {("rating", "anthropic", "claude-sonnet-5-5")}   # recommended
    models = {e["data"]["purpose"]: e["data"]["model"] for e in read(job) if e["type"] == "model_call"}
    assert models == {"scan": "anthropic/claude-opus-4-1", "rating": "anthropic/claude-sonnet-5-5"}


def test_layout_and_banner_get_their_models_and_fall_back_when_the_provider_is_gone(tmp_path, monkeypatch):
    job = make_job(tmp_path, [clip("clip01")])
    monkeypatch.setattr(render.frames, "extract", lambda src, times, out, **kw: [tmp_path / f"f{i}.jpg" for i in range(5)])
    monkeypatch.setattr(render.frames, "size", lambda p: (1280, 720))
    monkeypatch.setattr(render.ffmpeg, "render", lambda src, out, *a, **kw: (out.write_bytes(b"mp4"), out)[1])
    called = {}

    def caller(model, prompt, schema, images=None):
        if "verdict" in schema.get("properties", {}):
            called["critic"] = model.model
            data = {"verdict": "pass", "score": 90, "issues": [], "wish": None, "fix": None, "summary": "fine"}
        elif "layout" in schema.get("properties", {}):
            called["layout"] = model.model
            data = {"layout": "scene_only", "live_chat_side": "none", "webcam_region": CAM, "streamer_crop": CAM, "scene_crop": GAME,
                    "screen_essential": True, "stable_across_frames": True, "needs_review": False, "reason": "x", "uncertainties": []}
        else:
            called["banner"] = model.model
            data = {"regions": []}
        return Answer(data, json.dumps(data), 0.1)

    s = Settings(model=ModelSettings(provider="openai", model="gpt-6.2-sol"))
    agents.set_model(s, "vodcut", agents.LAYOUT, "openai", "gpt-6.2-astra")
    render.render_all(job, Asker(agents.default_connection(s), caller, models=agents.models_for(s, "vodcut", AGENTS)))
    assert called == {"layout": "gpt-6.2-astra", "banner": "gpt-6.1-terra", "critic": "gpt-6.2-sol"}
    # OpenAI is removed, Codex added: the layout choice for OpenAI is not used any more
    s.providers = [Provider(id="codex", kind="codex", name="Codex CLI")]
    called.clear()
    (job / "clips" / "clip01.mp4").unlink()
    (job / "scene.json").unlink()            # B12: the recording's ad slots are kept there; a new job asks again
    render.render_all(job, Asker(agents.default_connection(s), caller, models=agents.models_for(s, "vodcut", AGENTS)))
    assert called == {"layout": "", "banner": "", "critic": ""}


def test_each_agent_calls_its_own_provider_when_several_are_connected(tmp_path, monkeypatch):
    """Stage 19: scan on Claude Code, rating on a second OpenAI key, layout and banner on Codex — each call really goes to
    the provider and model chosen for its agent, with that provider's key."""
    s = Settings(providers=[Provider(id="codex", kind="codex", name="Codex CLI"),
                            Provider(id="claude-code", kind="claude_code", name="Claude Code CLI"),
                            Provider(id="openai-2", kind="openai", name="OpenAI — work", base_url="https://api.openai.com/v1")])
    by_id = {a.id: a for a in AGENTS}
    agents.set_model(s, "vodcut", by_id["scan"], "claude-code", "claude-opus-5-5")
    agents.set_model(s, "vodcut", by_id["rating"], "openai-2", "gpt-6.2-sol")
    s.save()
    called = []

    def caller(model, prompt, schema, images=None):
        called.append(("scan" if "Windows to read:" in prompt else "rating", model.provider_id, model.provider, model.model, model.key_ref))
        return fake_caller(model, prompt, schema)

    asker = vodcut_tool._asker(Settings.load())
    monkeypatch.setattr("test_analysis.Asker", lambda model, caller_: Asker(model, caller_, models=asker.models))
    job, _ = run_demo(tmp_path, monkeypatch, caller=caller)
    assert {c for c in called if c[0] == "scan"} == {("scan", "claude-code", "claude_code", "claude-opus-5-5", "")}
    assert {c for c in called if c[0] == "rating"} == {("rating", "openai-2", "openai", "gpt-6.2-sol", "provider.openai-2")}
    models = {e["data"]["purpose"]: e["data"]["model"] for e in read(job) if e["type"] == "model_call"}
    assert models == {"scan": "claude_code/claude-opus-5-5", "rating": "openai/gpt-6.2-sol"}
    # the frames go to Codex, never to Claude Code, which cannot pass them
    pick = agents.models_for(Settings.load(), "vodcut", AGENTS)
    assert {pick(p).provider_id for p in ("layout", "banner", "critic")} == {"codex"}
