import pytest
import json

from smtv_core.llm import Answer
from smtv_core.settings import ModelSettings

from vodcut import render
from vodcut.model import Asker

CAM = {"x": 0.75, "y": 0.0, "width": 0.25, "height": 0.3}
GAME = {"x": 0.0, "y": 0.1, "width": 0.75, "height": 0.9}


def make_job(tmp_path, clips):
    job = tmp_path / "job"
    job.mkdir()
    (job / "clips.json").write_text(json.dumps({"source": {"kind": "file", "path": str(tmp_path / "video.mp4")}, "clips": clips}), encoding="utf-8")
    words = [{"word": " hello", "start": 10.0, "end": 10.4}, {"word": " world.", "start": 10.5, "end": 11.0}]
    (job / "transcript.json").write_text(json.dumps({"segments": [{"start": 10.0, "end": 11.0, "text": "hello world.", "words": words}]}), encoding="utf-8")
    return job


def clip(cid):
    return {"id": cid, "start_s": 10.0, "end_s": 30.0, "title": f"title {cid}"}


def test_layout_from_model_captions_written_and_one_failure_does_not_stop_others(tmp_path, monkeypatch):
    job = make_job(tmp_path, [clip("clip01"), clip("clip02")])
    monkeypatch.setattr(render.frames, "extract", lambda src, times, out, **kw: [tmp_path / f"f{i}.jpg" for i in range(5)])
    monkeypatch.setattr(render.frames, "size", lambda p: (1280, 720))
    rendered = []

    def fake_render(src, out, start, end, layout, ass, fonts_dir, **kw):
        if out.stem == "clip02":
            raise RuntimeError("disk full")
        rendered.append((out.stem, layout.mode, ass.read_text(encoding="utf-8")))
        out.write_bytes(b"mp4")
        return out

    monkeypatch.setattr(render.ffmpeg, "render", fake_render)
    seen = {}

    def caller(model, prompt, schema, images=None):
        if "webcam_region" in schema["properties"]:
            seen["images"], seen["prompt"] = images, prompt
        data = {"layout": "scene_only", "live_chat_side": "none", "webcam_region": CAM, "streamer_crop": CAM, "scene_crop": GAME,
                "screen_essential": True, "stable_across_frames": True, "needs_review": False, "reason": "x", "uncertainties": []}
        return Answer(data, "", 0.1)

    report = render.render_all(job, Asker(ModelSettings(provider="openai", model="m"), caller))
    assert [r["status"] for r in report] == ["done", "failed"] and "disk full" in report[1]["error"]
    name, mode, ass = rendered[0]
    assert mode == "streamer_scene_split"                   # the model chose scene_only with a webcam: the camera is kept
    assert "HELLO" in ass and "TITLE CLIP01" in ass
    assert len(seen["images"]) == 5 and '"source_width": 1280' in seen["prompt"]
    again = render.render_all(job, None, only={"clip01"})
    assert [{k: r[k] for k in ("id", "status", "file")} for r in again] == [{"id": "clip01", "status": "done", "file": str(job / "clips" / "clip01.mp4")}]


def test_without_a_usable_answer_the_whole_frame_is_used(tmp_path, monkeypatch):
    monkeypatch.setattr(render.frames, "extract", lambda src, times, out, **kw: [tmp_path / "f.jpg"] * 5)
    monkeypatch.setattr(render.frames, "size", lambda p: (1280, 720))
    asker = Asker(ModelSettings(provider="openai", model="m"), lambda m, p, s, images=None: Answer({"layout": "weird"}, "", 0.1))
    layout, how, _ = render.choose_layout(asker, tmp_path / "v.mp4", 0, 20, [], tmp_path / "frames")
    assert layout["mode"] == "scene_only" and layout["scene_crop"]["width"] == 1.0 and how.startswith("default")


def test_switches_reach_the_renderer(tmp_path, monkeypatch):
    job = make_job(tmp_path, [{**clip("clip01"), "end_s": 12.0}])
    segs = {"segments": [{"start": 10.0, "end": 12.0, "text": "ну ты пидор.", "words": [
        {"word": " ну", "start": 10.0, "end": 10.2}, {"word": " ты", "start": 10.3, "end": 10.5}, {"word": " пидор.", "start": 10.6, "end": 11.0}]}]}
    (job / "transcript.json").write_text(json.dumps(segs, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(render.frames, "extract", lambda src, times, out, **kw: [tmp_path / f"f{i}.jpg" for i in range(5)])
    monkeypatch.setattr(render.frames, "size", lambda p: (1280, 720))
    seen = {}

    def fake_render(src, out, start, end, layout, ass, fonts_dir, **kw):
        seen.update(kw, ass=ass.read_text(encoding="utf-8"))
        out.write_bytes(b"mp4")
        return out

    monkeypatch.setattr(render.ffmpeg, "render", fake_render)
    banner = {"regions": [{"id": "slot-1", "label": "promo", "confidence": 0.9, "needs_review": True, "reason": "code",
                           "box": {"x": 1000, "y": 600, "width": 200, "height": 100}, "observed_frames": [1]}], "excluded": [], "notes": ""}
    layout = {"layout": "scene_only", "live_chat_side": "none", "webcam_region": None, "streamer_crop": None, "scene_crop": GAME,
              "screen_essential": True, "stable_across_frames": True, "needs_review": False, "reason": "x", "uncertainties": []}

    def caller(model, prompt, schema, images=None):
        return Answer(banner if "regions" in schema["properties"] else layout, "", 0.1)

    asker = Asker(ModelSettings(provider="openai", model="m"), caller)
    [r] = render.render_all(job, asker, options={"critic": False})   # defaults: loudness, bleep, ad blur on; peak lines off
    assert seen["loudness"] is True and seen["bleep"].startswith("aeval=") and seen["blur_boxes"] == [(318, 160, 1491, 895)]
    assert "П**ОР." in seen["ass"] and "ПИДОР" not in seen["ass"]       # the captions star what the tone covers
    assert r["bleeps"] == 1 and r["ads_blurred"] == 1 and r["peak"] is None and asker.calls == 1 + 1     # B12: one sure layout answer, one banner

    (job / "clips" / "clip01.mp4").unlink()
    [r] = render.render_all(job, asker, options={"loudness": False, "bleep": False, "ad_blur": False, "peak_lines": True, "critic": False})
    assert seen["loudness"] is False and seen["bleep"] == "" and seen["blur_boxes"] == []
    # the same frames: the layout comes from layouts.json, no new layout request; no banner request when off
    # without the tone the slur is still starred on screen (stage 15: as production's captions)
    assert r["peak"] == ["ну ты", "п**ор."] and "\\fscx240" in seen["ass"] and asker.calls == 2


def test_ads_are_not_blurred_on_a_bad_answer(tmp_path, monkeypatch):
    monkeypatch.setattr(render.frames, "size", lambda p: (1280, 720))
    asker = Asker(ModelSettings(provider="openai", model="m"), lambda m, p, s, images=None: Answer({"regions": [{"id": 1}]}, "", 0.1))
    boxes, how = render.find_ads(asker, [tmp_path / "f.jpg"] * 5, 0, 20)
    assert boxes == [] and how.startswith("none: model answer rejected")
    assert render.find_ads(None, [], 0, 20) == ([], "none: no model")


def test_options_defaults_and_saving(tmp_path):
    from smtv_core.settings import Settings
    from vodcut import options

    s = Settings()
    assert options.load(s) == {"loudness": True, "bleep": True, "peak_lines": False, "ad_blur": True, "precise": True,
                               "critic": options.CRITIC_DEFAULT, "recap": options.RECAP_DEFAULT, "local_download": False}
    options.set_option(s, "peak_lines", True)
    s.tools["vodcut"]["bleep"] = "maybe"                                # anything not true/false falls back to the default
    path = s.save(tmp_path / "settings.json")
    assert options.load(Settings.load(path)) == {"loudness": True, "bleep": True, "peak_lines": True, "ad_blur": True, "precise": True,
                                                    "critic": options.CRITIC_DEFAULT, "recap": options.RECAP_DEFAULT, "local_download": False}
    import pytest
    with pytest.raises(KeyError):
        options.set_option(s, "nonsense", True)


def test_render_writes_its_events_and_prints_the_same_lines(tmp_path, monkeypatch, capsys):
    from smtv_core import events
    from smtv_core.events import Journal
    from vodcut import console

    job = make_job(tmp_path, [clip("clip01"), clip("clip02")])
    monkeypatch.setattr(render.frames, "extract", lambda src, times, out, **kw: [out / f"f{i}.jpg" for i in range(len(times))])
    monkeypatch.setattr(render.frames, "size", lambda p: (1280, 720))

    def fake_render(src, out, start, end, layout, ass, fonts_dir, **kw):
        if out.stem == "clip02":
            raise RuntimeError("disk full")
        out.write_bytes(b"mp4")
        return out

    monkeypatch.setattr(render.ffmpeg, "render", fake_render)
    layout = {"layout": "streamer_scene_split", "live_chat_side": "none", "webcam_region": CAM, "streamer_crop": CAM, "scene_crop": GAME,
              "screen_essential": True, "stable_across_frames": True, "needs_review": False, "reason": "x", "uncertainties": []}

    def caller(model, prompt, schema, images=None):
        return Answer({"regions": [], "excluded": [], "notes": ""} if "regions" in schema["properties"] else layout, "", 0.1, 50, 5)

    render.render_all(job, Asker(ModelSettings(provider="openai", model="m"), caller), journal=Journal(job, tool="vodcut", echo=console.printer(job)),
                      options={"critic": False})
    got = events.read(job)
    kinds = [e["type"] for e in got]
    assert kinds[0] == "stage" and got[0]["data"]["name"] == "render" and kinds[-1] == "done"
    # B12: one layout answer per clip (sure of itself), ONE banner question for the whole recording
    assert [e["data"]["purpose"] for e in got if e["type"] == "model_call"] == ["layout", "banner", "layout"]
    assert all(e["data"]["images"] == 5 and e["data"]["tokens_in"] == 50 for e in got if e["type"] == "model_call")
    assert [(e["data"]["clip"], e["data"]["mode"], e["data"]["by"].split(" (")[0]) for e in got if e["type"] == "layout_chosen"] == \
        [("clip01", "streamer_scene_split", "model"), ("clip02", "streamer_scene_split", "model")]
    assert [e["data"]["count"] for e in got if e["type"] == "ads_found"] == [0, 0]
    [ready] = [e["data"] for e in got if e["type"] == "clip_ready"]
    [failed] = [e["data"] for e in got if e["type"] == "clip_failed"]
    assert ready["clip"] == "clip01" and ready["file"] == "clips/clip01.mp4" and ready["layout"] == "streamer_scene_split"
    assert failed["clip"] == "clip02" and "disk full" in failed["error"]
    assert [r["status"] for r in got[-1]["data"]["report"]] == ["done", "failed"]
    assert capsys.readouterr().out.splitlines() == [
        "", "Rendering the clips",
        "  1/2 clip01 title clip01",
        "  2/2 clip02 title clip02",
        "    failed: RuntimeError: disk full",
        f"  clip01  done    {job / 'clips' / 'clip01.mp4'}",
        "  clip02  failed  RuntimeError: disk full",
        "", f"1 of 2 clips in {job / 'clips'}",
    ]

    render.render_all(job, None, only={"clip01"})                     # a rerun: the finished clip is reported, numbers go on
    again = events.read(job, after=len(got))
    assert again[0]["n"] == len(got) + 1
    assert [(e["type"], e["data"].get("existing")) for e in again] == [("stage", None), ("clip_ready", True), ("done", None)]
    from test_analysis import assert_contract
    assert_contract(job)


def test_events_of_the_other_render_branches_fit_the_contract(tmp_path, monkeypatch):
    from test_analysis import assert_contract
    job = make_job(tmp_path, [clip("clip01")])
    monkeypatch.setattr(render.frames, "extract", lambda src, times, out, **kw: [tmp_path / "f.jpg"] * 5)
    monkeypatch.setattr(render.frames, "size", lambda p: (1280, 720))
    monkeypatch.setattr(render.ffmpeg, "render", lambda src, out, *a, **kw: out.write_bytes(b"mp4"))
    asker = Asker(ModelSettings(provider="openai", model="m"), lambda m, p, s, images=None: Answer({"layout": "weird"}, "", 0.1))
    render.render_all(job, asker, options={"peak_lines": True})                     # rejected answers, schema errors, peak lines
    (job / "clips" / "clip01.mp4").unlink()
    render.render_all(job, None, options={"ad_blur": False})                         # no model at all
    assert_contract(job)


def test_a_clip_whose_bounds_fit_moved_is_rendered_again(tmp_path, monkeypatch):
    """Stage 11: a clip rendered before Fit (or at other bounds) is not taken from the old file."""
    moved = {**clip("clip01"), "start_s": 12.5, "end_s": 31.0, "pass2": {"start_s": 10.0, "end_s": 30.0}}
    same = {**clip("clip02"), "pass2": {"start_s": 10.0, "end_s": 30.0}}
    job = make_job(tmp_path, [moved, same])
    (job / "clips").mkdir()
    (job / "pieces").mkdir()
    for name in ("clips/clip01.mp4", "clips/clip01.ass", "pieces/clip01.mp4", "clips/clip02.mp4"):
        (job / name).write_bytes(b"old")
    made = []

    def fake_render(src, out, start, end, layout, ass, fonts_dir, **kw):
        made.append((out.stem, start, end))
        out.write_bytes(b"new")
        return out

    monkeypatch.setattr(render.ffmpeg, "render", fake_render)
    report = render.render_all(job, None)
    assert made == [("clip01", 12.5, 31.0)] and not (job / "pieces" / "clip01.mp4").exists()
    assert (job / "clips" / "clip02.mp4").read_bytes() == b"old"                      # its bounds did not move
    assert [(r["start_s"], r["end_s"]) for r in report] == [(12.5, 31.0), (10.0, 30.0)]
    moved["end_s"] = 29.0                                                            # Fit moved it again: renders.json knows the last bounds
    (job / "clips.json").write_text(json.dumps({**json.loads((job / "clips.json").read_text(encoding="utf-8")), "clips": [moved, same]}), encoding="utf-8")
    render.render_all(job, None)
    assert made[-1] == ("clip01", 12.5, 29.0) and len(made) == 2


def test_rendering_some_clips_keeps_the_other_rows_of_renders_json(tmp_path, monkeypatch):
    job = make_job(tmp_path, [clip("clip01"), clip("clip02")])
    monkeypatch.setattr(render.ffmpeg, "render", lambda src, out, *a, **k: (out.write_bytes(b"mp4"), out)[1])
    render.render_all(job, None)
    render.render_all(job, None, only={"clip02"})
    rows = json.loads((job / "renders.json").read_text(encoding="utf-8"))
    assert sorted(r["id"] for r in rows) == ["clip01", "clip02"] and all("start_s" in r for r in rows)


# --- stage 14: the critic and the steady layout ---------------------------------------------------------------

def critic_job(tmp_path, monkeypatch, verdicts):
    """A job of one clip; the model answers layout, banner and critic questions; ffmpeg writes which layout it got."""
    job = make_job(tmp_path, [clip("clip01")])

    def extract(src, times, out, **kw):
        out.mkdir(parents=True, exist_ok=True)
        paths = [out / f"frame{i}.jpg" for i in range(len(times))]
        for p in paths:
            p.write_bytes(b"jpg:" + (src.read_bytes()[:40] if src.exists() else b"source"))
        return paths

    monkeypatch.setattr(render.frames, "extract", extract)
    monkeypatch.setattr(render.frames, "size", lambda p: (1280, 720))

    def fake_render(src, out, start, end, layout, ass, fonts_dir, **kw):
        out.write_bytes(f"{layout.mode}|{'HOOK' if 'TITLE CLIP01' in ass.read_text(encoding="utf-8") else 'nohook'}".encode())
        return out

    monkeypatch.setattr(render.ffmpeg, "render", fake_render)
    asked = []
    layout = {"layout": "streamer_scene_split", "live_chat_side": "none", "webcam_region": CAM, "streamer_crop": CAM, "scene_crop": GAME,
              "screen_essential": True, "stable_across_frames": True, "needs_review": False, "reason": "x", "uncertainties": []}

    def caller(model, prompt, schema, images=None):
        props = schema["properties"]
        kind = "critic" if "verdict" in props else "banner" if "regions" in props else "layout"
        asked.append(kind)
        data = verdicts.pop(0) if kind == "critic" else {"regions": [], "excluded": [], "notes": ""} if kind == "banner" else layout
        return Answer(data, "", 0.1)

    return job, Asker(ModelSettings(provider="openai", model="m"), caller), asked


def test_with_the_critic_off_no_clip_is_checked(tmp_path, monkeypatch):
    from smtv_core import events
    job, asker, asked = critic_job(tmp_path, monkeypatch, [])
    [r] = render.render_all(job, asker, options={"critic": False})
    assert "critic" not in asked and "critic" not in r
    assert not [e for e in events.read(job) if e["type"].startswith("clip_checked") or e["type"] == "clip_reviewed"]
    assert not (job / "critic").exists()


def test_the_critic_edits_once_and_the_window_learns_why(tmp_path, monkeypatch):
    from smtv_core import events
    from test_analysis import assert_contract
    fix = {"verdict": "fix", "score": 55, "issues": [{"code": "text_overlap", "severity": "major", "where": "top", "detail": "hook on the face"}],
           "wish": "remove the hook", "fix": "drop_hook", "summary": "hook covers the face"}
    again = {"verdict": "fix", "score": 75, "issues": [], "wish": "captions up", "fix": "captions_upper", "summary": "better"}
    job, asker, asked = critic_job(tmp_path, monkeypatch, [fix, again])
    [r] = render.render_all(job, asker)                               # the critic is on by default
    assert asked.count("critic") == 2 and asked.count("layout") == 1
    assert (job / "clips" / "clip01.mp4").read_bytes() == b"streamer_scene_split|nohook"   # the edited version stays
    assert "TITLE CLIP01" not in (job / "clips" / "clip01.ass").read_text(encoding="utf-8") and not list((job / "clips").glob("*.fix.*"))
    assert r["critic"]["outcome"] == "fixed" and r["critic"]["fix"] == "drop_hook" and r["critic"]["score"] == 75
    got = events.read(job)
    kinds = [e["type"] for e in got]
    assert kinds.count("clip_fixed") == 1 and kinds.count("clip_checked") == 2 and kinds.index("clip_reviewed") < kinds.index("clip_ready")
    ready = next(e["data"] for e in got if e["type"] == "clip_ready")
    assert ready["critic"]["outcome"] == "fixed" and "remove the hook" in ready["critic"]["reason"]
    assert any(e["data"].get("step") == "critic" for e in got if e["type"] == "progress")
    # a rerun: the clip is not checked again, its note comes from renders.json
    render.render_all(job, asker)
    assert asked.count("critic") == 2
    assert events.read(job)[-2]["data"]["critic"]["outcome"] == "fixed"
    assert_contract(job)


def test_the_same_clip_gets_the_same_layout_without_asking_again(tmp_path, monkeypatch):
    job, asker, asked = critic_job(tmp_path, monkeypatch, [])
    shots = render.frames.extract(tmp_path / "video.mp4", [1, 2, 3, 4, 5], job / "frames" / "clip01")
    first = render.choose_layout(asker, tmp_path / "v.mp4", 10, 30, [], job / "frames", shots=shots, job=job, clip_id="clip01")
    second = render.choose_layout(asker, tmp_path / "v.mp4", 10, 30, [], job / "frames", shots=shots, job=job, clip_id="clip01")
    assert asked == ["layout"] and first[0] == second[0] and first[2]["cached"] is False and second[2]["cached"] is True
    assert first[2]["votes"] == ["streamer_scene_split"] and first[0]["camera"]["width"] == pytest.approx(0.25 * 0.94)   # fake frames: pulled in by the margin
    shots[2].write_bytes(b"another picture")                           # other frames: a new question
    third = render.choose_layout(asker, tmp_path / "v.mp4", 10, 30, [], job / "frames", shots=shots, job=job, clip_id="clip01")
    assert asked == ["layout"] * 2 and third[2]["cached"] is False


def test_a_crashing_critic_leaves_the_clip_done(tmp_path, monkeypatch):
    from smtv_core import events
    from test_analysis import assert_contract
    job, asker, asked = critic_job(tmp_path, monkeypatch, [])
    caller = asker.caller

    def crashing(model, prompt, schema, images=None):
        if "verdict" in schema["properties"]:
            raise ConnectionResetError("the connection dropped")
        return caller(model, prompt, schema, images)

    asker.caller = crashing
    [r] = render.render_all(job, asker)
    assert r["status"] == "done" and r["critic"]["outcome"] == "unchecked" and "ConnectionResetError" in r["critic"]["reason"]
    assert (job / "clips" / "clip01.mp4").read_bytes() == b"streamer_scene_split|HOOK" and not list((job / "clips").glob("*.fix.*"))
    assert not [e for e in events.read(job) if e["type"] == "clip_failed"]
    missing = [e["data"] for e in events.read(job) if e["type"] == "progress" and e["data"]["stage"] == "missing"]
    assert missing == [{"stage": "missing", "step": "critic", "done": 1, "total": 1}]      # B26: «done» says one is unchecked
    assert_contract(job)


def test_a_layout_edit_reaches_the_file_and_renders_json(tmp_path, monkeypatch):
    from smtv_core import events
    fix = {"verdict": "fix", "score": 60, "issues": [], "wish": "equal halves", "fix": "layout_split_equal", "summary": "face small"}
    ok = {"verdict": "pass", "score": 80, "issues": [], "wish": None, "fix": None, "summary": "fine"}
    job, asker, _ = critic_job(tmp_path, monkeypatch, [fix, ok])
    [r] = render.render_all(job, asker)
    assert (job / "clips" / "clip01.mp4").read_bytes() == b"streamer_scene_split_equal|HOOK"
    saved = json.loads((job / "renders.json").read_text(encoding="utf-8"))[0]
    ready = next(e["data"] for e in events.read(job) if e["type"] == "clip_ready")
    assert r["layout"] == saved["layout"] == ready["layout"] == "streamer_scene_split_equal" and saved["critic"]["outcome"] == "fixed"


def test_an_unsure_first_answer_is_put_to_a_vote_and_an_incomplete_vote_is_not_kept(tmp_path, monkeypatch):
    """B12: one layout answer; two more and a vote only when it says itself it is not sure."""
    job, asker, asked = critic_job(tmp_path, monkeypatch, [])
    caller, calls = asker.caller, []

    def unsure(model, prompt, schema, images=None):
        answer = caller(model, prompt, schema, images)
        return Answer({**answer.data, "needs_review": True}, "", 0.1)

    def flaky(model, prompt, schema, images=None):
        calls.append(1)
        if len(calls) > 1:                                        # the two extra answers fail
            from smtv_core.llm import ProviderError
            raise ProviderError("busy")
        return unsure(model, prompt, schema, images)

    asker.caller = flaky
    shots = render.frames.extract(tmp_path / "video.mp4", [1, 2, 3, 4, 5], job / "frames" / "clip01")
    layout, how, info = render.choose_layout(asker, tmp_path / "v.mp4", 10, 30, [], job / "frames", shots=shots, job=job, clip_id="clip01")
    assert len(calls) == 3 and layout["mode"] == "streamer_scene_split" and "vote of 1 of 3" in how and "busy" in how
    assert not (job / "layouts.json").exists() and not (job / "scene.json").exists()      # asked again next time
    asker.caller = unsure
    layout, how, info = render.choose_layout(asker, tmp_path / "v.mp4", 10, 30, [], job / "frames", shots=shots, job=job, clip_id="clip01")
    assert how.startswith("model: vote of 3") and info["votes"] == ["streamer_scene_split"] * 3
    assert "clip01" in json.loads((job / "layouts.json").read_text(encoding="utf-8"))
    asker.caller = lambda m, p, s, images=None: (_ for _ in ()).throw(__import__("smtv_core.llm", fromlist=["ProviderError"]).ProviderError("down"))
    layout, how, info = render.choose_layout(asker, tmp_path / "v.mp4", 10, 30, [], job / "frames", shots=shots, job=job, clip_id="clip02")
    assert layout["mode"] == "scene_only" and how.startswith("default: model: down")


def test_a_clip_file_held_by_another_program_fails_only_that_clip(tmp_path, monkeypatch):
    """B11 (Windows): the old file of a moved clip cannot be removed (open in a player): the other clips are made."""
    moved = {**clip("clip01"), "start_s": 12.5, "end_s": 31.0, "pass2": {"start_s": 10.0, "end_s": 30.0}}
    job = make_job(tmp_path, [moved, clip("clip02")])
    (job / "clips").mkdir()
    (job / "clips" / "clip01.mp4").write_bytes(b"old")
    real_unlink = render.Path.unlink

    def held(self, *a, **k):
        if self.name == "clip01.mp4" and self.parent.name == "clips":
            raise PermissionError(13, "The process cannot access the file because it is being used by another process")
        return real_unlink(self, *a, **k)
    monkeypatch.setattr(render.Path, "unlink", held)

    def fake_render(src, out, start, end, layout, ass, fonts_dir, **kw):
        out.write_bytes(b"new")
        return out
    monkeypatch.setattr(render.ffmpeg, "render", fake_render)
    report = {r["id"]: r for r in render.render_all(job, None)}
    assert report["clip02"]["status"] == "done" and report["clip01"]["status"] == "failed"
    assert "открыт в другой программе" in report["clip01"]["error"]
