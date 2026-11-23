"""B12: what a recording looks like is decided once for all its clips and its recap (scene.py, render.py)."""
from __future__ import annotations

import json

from smtv_core.render import faces, look
from smtv_core.llm import Answer
from smtv_core.settings import ModelSettings
from vodcut import render
from vodcut.model import Asker
from vodcut.scene import Scene

from test_render_step import CAM, GAME, clip, make_job

CAMERA = {"x": 0.0, "y": 0.33, "width": 0.17, "height": 0.29}
FACE = {"x": 0.06, "y": 0.4, "width": 0.04, "height": 0.09}
LAYOUT = {"layout": "streamer_scene_split", "live_chat_side": "none", "webcam_region": CAM, "streamer_crop": CAM, "scene_crop": GAME,
          "screen_essential": True, "stable_across_frames": True, "needs_review": False, "reason": "x", "uncertainties": []}


def job_of(tmp_path, monkeypatch, n=3):
    job = make_job(tmp_path, [clip(f"clip0{i}") for i in range(1, n + 1)])

    def extract(src, times, out, **kw):
        out.mkdir(parents=True, exist_ok=True)
        paths = [out / f"frame{i}.jpg" for i in range(len(times))]
        for p in paths:
            p.write_bytes(b"jpg")
        return paths
    monkeypatch.setattr(render.frames, "extract", extract)
    monkeypatch.setattr(render.frames, "size", lambda p: (1280, 720))
    monkeypatch.setattr(render.ffmpeg, "render", lambda src, out, start, end, layout, *a, **k: (out.write_bytes(layout.mode.encode()), out)[1])
    asked = []

    def caller(model, prompt, schema, images=None):
        kind = "banner" if "regions" in schema["properties"] else "layout"
        asked.append(kind)
        return Answer({"regions": [], "excluded": [], "notes": ""} if kind == "banner" else LAYOUT, "", 0.1)
    return job, Asker(ModelSettings(provider="openai", model="m"), caller), asked


def test_a_webcam_found_on_the_frames_asks_the_model_nothing_and_the_ads_are_asked_once(tmp_path, monkeypatch):
    job, asker, asked = job_of(tmp_path, monkeypatch)
    monkeypatch.setattr(look, "bgr", lambda p: None)
    monkeypatch.setattr(look, "look", lambda images, known=(), faceless=(): look.Look(
        "overlay", camera=CAMERA, face=FACE, reason="a face in a still box", known=bool(known)))
    report = render.render_all(job, asker, options={"critic": False})
    assert [r["status"] for r in report] == ["done"] * 3 and all(r["layout_by"].startswith("local:") for r in report)
    assert asked == ["banner"]                                   # no layout question; ONE banner question for three clips
    assert all(r["layout"] == "streamer_scene_split_equal" for r in report)
    saved = json.loads((job / "scene.json").read_text(encoding="utf-8"))
    assert saved["cameras"][0]["camera"] == CAMERA and saved["ads"]["boxes"] == [] and saved["ads"]["frames"] == 5
    (job / "clips" / "clip02.mp4").unlink()
    render.render_all(job, asker, options={"critic": False})
    assert asked == ["banner"]                                   # the next run: the ads and the webcam are known


def test_without_faces_here_the_model_decides_and_its_webcam_serves_the_next_clips(tmp_path, monkeypatch):
    job, asker, asked = job_of(tmp_path, monkeypatch)
    monkeypatch.setattr(look, "bgr", lambda p: None)

    def no_detector(images, known=(), faceless=()):
        raise faces.FacesUnavailable("onnxruntime is not installed")
    monkeypatch.setattr(look, "look", no_detector)
    report = render.render_all(job, asker, options={"critic": False})
    assert asked.count("layout") == 3 and asked.count("banner") == 1   # no detector: each clip asks, as before B12, minus the vote
    assert all("faces cannot be looked for here" in r["layout_by"] for r in report)


def test_a_recording_the_model_found_without_a_webcam_asks_no_more(tmp_path, monkeypatch):
    scene = Scene(tmp_path)
    unsure = look.Look("unsure", reason="faces, but none that stays in a webcam box", faces=[[]])
    monkeypatch.setattr(look, "bgr", lambda p: None)
    monkeypatch.setattr(look, "look", lambda images, known=(), faceless=(): unsure)
    scene.remember(unsure, None, "model, clip01")
    assert Scene(tmp_path).look([tmp_path / "f.jpg"]).kind == "unsure"      # one answer decides only its own clip
    scene.remember(unsure, None, "model, clip02", full=True)                # another answer that disagrees starts over
    assert Scene(tmp_path).look([tmp_path / "f.jpg"]).kind == "unsure"
    scene.remember(unsure, None, "model, clip03", full=True)
    again = Scene(tmp_path).look([tmp_path / "f.jpg"])
    assert again.kind == "full" and again.known and "model, clip03" in again.reason
    # a small face that stays put may be a webcam after all: that one is a question again
    steady = look.Look("unsure", face=FACE, reason="a steady face, but …", candidates=1, faces=[[]])
    monkeypatch.setattr(look, "look", lambda images, known=(), faceless=(): steady)
    assert Scene(tmp_path).look([tmp_path / "f.jpg"]).kind == "unsure"


def test_an_unusable_ad_answer_is_not_kept_and_asked_again(tmp_path):
    scene, calls = Scene(tmp_path), []

    def find(shots):
        calls.append(len(shots))
        return ([], "none: busy") if len(calls) == 1 else ([(10, 10, 5, 5)], "model")
    five = lambda: list("abcde")  # noqa: E731
    assert scene.ad_boxes(find, five) == ([], "none: busy")
    assert scene.ad_boxes(find, lambda: ["a"] * 5) == ([(10, 10, 5, 5)], "model")       # one frame five times: not kept
    assert scene.ad_boxes(find, five) == ([(10, 10, 5, 5)], "model")
    assert Scene(tmp_path).ad_boxes(find, lambda: 1 / 0) == ([(10, 10, 5, 5)], "model: the recording") and calls == [5, 5, 5]
    broken = Scene(tmp_path / "other")
    (tmp_path / "other").mkdir()
    assert broken.ad_boxes(find, lambda: 1 / 0)[1].startswith("none: frames of the recording: ZeroDivisionError")


def test_the_frames_for_the_ads_are_spread_over_the_recording():
    assert render.spread(list(range(10)), 5) == [0, 2, 4, 7, 9] and render.spread([1, 2], 5) == [1, 2]
    assert render.spread(list(range(7)), 1) == [3]


def test_a_webcam_found_later_is_never_overruled_by_no_webcam(tmp_path, monkeypatch):
    scene = Scene(tmp_path)
    unsure = look.Look("unsure", reason="faces, but none that stays in a webcam box", faces=[[]])
    scene.remember(unsure, None, "model, clip01")
    scene.remember(unsure, None, "model, clip02")
    scene.remember(look.Look("overlay", camera=CAMERA, face=FACE, faces=[[object()]]), CAMERA, "local")
    monkeypatch.setattr(look, "bgr", lambda p: None)
    monkeypatch.setattr(look, "look", lambda images, known=(), faceless=(): unsure)
    assert Scene(tmp_path).look([tmp_path / "f.jpg"]).kind == "unsure"      # the streamer stepped away: asked, not «none»


def test_a_camera_the_model_gave_while_faces_could_not_be_looked_for_is_not_faceless(tmp_path):
    scene = Scene(tmp_path)
    scene.remember(look.Look("unsure", reason="faces cannot be looked for here"), CAMERA, "model, clip01")
    scene.remember(look.Look("unsure", reason="no face", faces=[[], []]), {**CAMERA, "x": 0.5}, "model, clip02")
    assert [c["faceless"] for c in Scene(tmp_path).cameras] == [False, True]


def test_a_clip_made_without_a_model_gets_its_ads_blurred_once_one_answers(tmp_path, monkeypatch):
    job, asker, asked = job_of(tmp_path, monkeypatch, n=1)
    monkeypatch.setattr(look, "bgr", lambda p: None)
    monkeypatch.setattr(look, "look", lambda images, known=(), faceless=(): look.Look(
        "overlay", camera=CAMERA, face=FACE, reason="a face in a still box", known=bool(known)))
    [r] = render.render_all(job, None, options={"critic": False})
    assert r["layout_by"].startswith("local:") and r["ads_by"] == "none: no model"
    [r] = render.render_all(job, asker, options={"critic": False})
    assert asked == ["banner"] and r["ads_by"] == "model" and not r.get("existing")
