"""B12: the critic looks at the made clips a batch at a time, and the recap uses what the clips found. What happens when
a pause or a failure falls between making a clip and checking it, and that the recap asks the model nothing the clips
already decided."""
from __future__ import annotations

import json

import pytest

from smtv_core import events, pause
from smtv_core.llm import Answer
from smtv_core.render import look
from smtv_core.settings import ModelSettings
from vodcut import render
from vodcut.model import Asker
from vodcut.recap import signals

from test_render_step import CAM, GAME, clip, make_job

CAMERA = {"x": 0.0, "y": 0.33, "width": 0.17, "height": 0.29}
FACE = {"x": 0.06, "y": 0.4, "width": 0.04, "height": 0.09}
LAYOUT = {"layout": "streamer_scene_split", "live_chat_side": "none", "webcam_region": CAM, "streamer_crop": CAM, "scene_crop": GAME,
          "screen_essential": True, "stable_across_frames": True, "needs_review": False, "reason": "x", "uncertainties": []}
PASS = {"verdict": "pass", "score": 80, "issues": [], "wish": None, "fix": None, "summary": "fine"}
FIX = {"verdict": "fix", "score": 60, "issues": [], "wish": "captions up", "fix": "captions_upper", "summary": "captions on the face"}


class Model:
    """The layout, banner and critic answers; critic calls are recorded by the clip ids they carry. `critic` gives the
    verdict for a clip id (a callable, or a dict), or raises."""

    def __init__(self, critic=lambda cid, round_: PASS):
        self.critic, self.calls = critic, []

    def __call__(self, model, prompt, schema, images=None):
        props = schema["properties"]
        if "regions" in props:
            self.calls.append(("banner",))
            return Answer({"regions": [], "excluded": [], "notes": ""}, "", 0.1)
        if "webcam_region" in props:
            self.calls.append(("layout",))
            return Answer(LAYOUT, "", 0.1)
        round_ = 2 if "already a revised version" in prompt else 1
        if "reviews" in props:                                  # several clips: the ids are in the order of the prompt
            ids = props["reviews"]["items"]["properties"]["video"]["enum"]
            clips = [prompt.split(f"=== {v} ===")[1].split("Video title: ")[1].split(".")[0].split()[-1] for v in ids]
            self.calls.append(("critic", round_, clips))
            return Answer({"reviews": [{"video": v, **self.critic(c, round_)} for v, c in zip(ids, clips)]}, "", 0.1)
        cid = prompt.split("Video title: ")[1].split(".")[0].split()[-1]
        self.calls.append(("critic", round_, [cid]))
        return Answer(self.critic(cid, round_), "", 0.1)

    def count(self, kind):
        return sum(1 for c in self.calls if c[0] == kind)


def job_of(tmp_path, monkeypatch, n=3):
    job = make_job(tmp_path, [clip(f"clip0{i}") for i in range(1, n + 1)])
    (tmp_path / "video.mp4").write_bytes(b"video")

    def extract(src, times, out, **kw):
        out.mkdir(parents=True, exist_ok=True)
        paths = [out / f"frame{i}.jpg" for i in range(len(times))]
        for p in paths:
            p.write_bytes(b"jpg")
        return paths
    monkeypatch.setattr(render.frames, "extract", extract)
    monkeypatch.setattr(render.frames, "size", lambda p: (1280, 720))
    monkeypatch.setattr(look, "bgr", lambda p: None)
    monkeypatch.setattr(look, "look", lambda images, known=(), faceless=(): look.Look(
        "overlay", camera=known[0] if known else CAMERA, face=FACE,
        reason="the webcam found before: the face is in it" if known else "a face in a still box", known=bool(known)))
    made = []

    def ffmpeg(src, out, start, end, layout, ass, fonts_dir, **kw):
        made.append(out.name)
        out.write_bytes(f"{layout.mode}|{ass.read_text(encoding='utf-8').count('Default')}".encode())
        return out
    monkeypatch.setattr(render.ffmpeg, "render", ffmpeg)
    return job, made


def reviewed(job):
    return [(e["data"]["clip"], e["data"]["outcome"]) for e in events.read(job) if e["type"] == "clip_reviewed"]


def test_a_pause_before_the_critic_keeps_the_made_clips_and_the_next_run_only_checks_them(tmp_path, monkeypatch):
    job, made = job_of(tmp_path, monkeypatch)
    model = Model()
    real = render.ffmpeg.render

    def pause_after_clip02(src, out, *a, **k):
        done = real(src, out, *a, **k)
        if out.name == "clip02.mp4":
            pause.ask(job)                                  # the person pauses while clip02 is encoded
        return done
    monkeypatch.setattr(render.ffmpeg, "render", pause_after_clip02)
    with pytest.raises(pause.Paused):
        render.render_all(job, Asker(ModelSettings(provider="openai", model="m"), model))
    rows = {r["id"]: r for r in json.loads((job / "renders.json").read_text(encoding="utf-8"))}
    assert made == ["clip01.mp4", "clip02.mp4"] and set(rows) == {"clip01", "clip02"}
    assert all(r["status"] == "done" and "critic" not in r for r in rows.values())    # made, recorded, not yet checked
    assert model.count("critic") == 0
    monkeypatch.setattr(render.ffmpeg, "render", real)
    report = render.render_all(job, Asker(ModelSettings(provider="openai", model="m"), model))
    assert made == ["clip01.mp4", "clip02.mp4", "clip03.mp4"]                       # the two made clips are not made again
    assert [c for c in model.calls if c[0] == "critic"] == [("critic", 1, ["clip01", "clip02", "clip03"])]   # one call
    assert [(r["id"], r["critic"]["outcome"]) for r in report] == [("clip01", "passed"), ("clip02", "passed"), ("clip03", "passed")]
    assert reviewed(job) == [("clip01", "passed"), ("clip02", "passed"), ("clip03", "passed")]


def test_a_critic_failing_in_the_middle_of_a_batch_loses_no_clip_and_the_rerun_checks_each_once(tmp_path, monkeypatch):
    job, made = job_of(tmp_path, monkeypatch)

    def critic(cid, round_):
        if round_ == 2:
            raise ConnectionResetError("the connection dropped")     # the check of the edits breaks
        return PASS if cid == "clip01" else FIX
    model = Model(critic)
    report = render.render_all(job, Asker(ModelSettings(provider="openai", model="m"), model))
    assert [r["status"] for r in report] == ["done"] * 3 and made == ["clip01.mp4", "clip02.mp4", "clip03.mp4", "clip02.fix.mp4", "clip03.fix.mp4"]
    assert [r["critic"]["outcome"] for r in report] == ["passed", "unchecked", "unchecked"]
    assert "ConnectionResetError" in report[1]["critic"]["reason"]
    assert not list((job / "clips").glob("*.fix.*"))               # the unfinished edits are cleaned away
    assert (job / "clips" / "clip02.mp4").read_bytes().startswith(b"streamer_scene_split_equal|")   # the first version stays
    assert reviewed(job) == [("clip01", "passed"), ("clip02", "unchecked"), ("clip03", "unchecked")]   # one each
    assert not [e for e in events.read(job) if e["type"] == "clip_failed"]
    # the next run: the two unchecked clips are checked together, not made again; clip01 is left alone
    model.critic = lambda cid, round_: PASS
    calls_before = len(model.calls)
    report = render.render_all(job, Asker(ModelSettings(provider="openai", model="m"), model))
    assert [c for c in model.calls[calls_before:] if c[0] == "critic"] == [("critic", 1, ["clip02", "clip03"])]
    assert len(made) == 5 and [r["critic"]["outcome"] for r in report] == ["passed"] * 3
    assert sorted(reviewed(job)) == sorted([("clip01", "passed"), ("clip02", "unchecked"), ("clip03", "unchecked"),
                                            ("clip02", "passed"), ("clip03", "passed")])


def test_six_clips_are_checked_in_two_batches_and_reported_in_clip_order(tmp_path, monkeypatch):
    job, made = job_of(tmp_path, monkeypatch, n=6)
    real = render.ffmpeg.render
    monkeypatch.setattr(render.ffmpeg, "render", lambda src, out, *a, **k: (_ for _ in ()).throw(RuntimeError("disk full"))
                        if out.name == "clip03.mp4" else real(src, out, *a, **k))
    model = Model()
    report = render.render_all(job, Asker(ModelSettings(provider="openai", model="m"), model))
    assert [c for c in model.calls if c[0] == "critic"] == [("critic", 1, ["clip01", "clip02", "clip04", "clip05"]), ("critic", 1, ["clip06"])]
    assert [(r["id"], r["status"]) for r in report] == [("clip01", "done"), ("clip02", "done"), ("clip03", "failed"), ("clip04", "done"),
                                                       ("clip05", "done"), ("clip06", "done")]
    ready = [e["data"]["clip"] for e in events.read(job) if e["type"] == "clip_ready"]
    assert ready == ["clip01", "clip02", "clip04", "clip05", "clip06"]


def test_the_recap_uses_the_webcam_and_the_ads_the_clips_found(tmp_path, monkeypatch):
    job, _ = job_of(tmp_path, monkeypatch)
    model = Model()
    render.render_all(job, Asker(ModelSettings(provider="openai", model="m"), model), options={"critic": False})
    assert model.calls == [("banner",)]                                  # the clips: no layout question, one banner question
    scene = json.loads((job / "scene.json").read_text(encoding="utf-8"))
    assert scene["cameras"][0]["camera"] == CAMERA and scene["ads"]["frames"] >= 4
    (job / "recap").mkdir()
    video = tmp_path / "video.mp4"
    monkeypatch.setattr(signals, "fetch", lambda info, p, folder: (str(video), 0.0))
    monkeypatch.setattr(signals, "levels", lambda *a: [])
    story = {"parts": [{"index": i, "start_s": 100.0 * i, "end_s": 100.0 * i + 20, "peaks_s": []} for i in range(7)]}
    recap_model = Model()
    found = signals.collect(job, story, {"kind": "file"}, Asker(ModelSettings(provider="openai", model="m"), recap_model))
    assert recap_model.calls == []                                       # the recap asks the model nothing
    assert all(part["cam"] == CAMERA and part["cam_by"].startswith("local: the webcam found before") for part in found.values())
    assert all(part["ads_by"] == "model: the recording" and part["ads"] == [] for part in found.values())
