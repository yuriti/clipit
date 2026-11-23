"""The critic (stage 14): exactly one edit at most, never «waits for a person», a bad answer leaves the clip as it is,
the webcam is never removed, the better of two versions stays; and the steady layout vote."""
import itertools
import json
import random

import numpy as np
import pytest

from smtv_core import critic, events
from smtv_core.critic import Decision, apply_fix
from smtv_core.events import Journal, contract
from smtv_core.render import layout as L

CAM = {"x": 0.0, "y": 0.32, "width": 0.17, "height": 0.3}
GAME = {"x": 0.17, "y": 0.0, "width": 0.83, "height": 1.0}
FULL = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
SPLIT = Decision("streamer_scene_split", GAME, CAM, CAM, hook="title")
OUTCOMES = {"passed", "fixed", "kept", "unchecked"}


@pytest.fixture(autouse=True)
def fake_frames(monkeypatch, tmp_path):
    def extract(src, times, out_dir, width=1280):
        out_dir.mkdir(parents=True, exist_ok=True)
        paths = []
        for i, _ in enumerate(times):
            p = out_dir / f"frame{i}.jpg"
            p.write_bytes(b"jpg" + src.read_bytes()[:8])
            paths.append(p)
        return paths
    monkeypatch.setattr("smtv_core.render.frames.extract", extract)


def verdict(v="pass", score=85, fix=None, wish=None):
    return {"verdict": v, "score": score, "issues": [{"code": "webcam_misplaced", "severity": "major", "where": "top", "detail": "x"}] if v != "pass" else [],
            "wish": wish, "fix": fix, "summary": f"{v} {score}"}


class Model:
    """Answers in turn; counts the calls and remembers the prompts."""
    def __init__(self, *answers):
        self.answers, self.prompts, self.images = list(answers), [], []

    def __call__(self, prompt, schema, images, purpose):
        assert purpose == "critic" and len(images) == critic.FRAME_COUNT
        self.prompts.append(prompt)
        self.images.append(images)
        a = self.answers.pop(0)
        return (None, {"error": a}) if isinstance(a, str) else (a, {"seconds": 1.0})


def run(tmp_path, model, decision=SPLIT, fail_render=False, **kw):
    video = tmp_path / "clip01.mp4"
    video.write_bytes(b"original")
    rendered = []

    def rerender(d, path):
        if fail_render:
            raise RuntimeError("ffmpeg broke")
        rendered.append(d)
        path.write_bytes(b"edited")
        return path

    journal = Journal(tmp_path / "job", tool="vodcut", subscribers=[])
    out = critic.review(model, "clip01", video, decision, {"duration_s": 30.0, "title": "t"}, tmp_path / "work", rerender, journal.emit, **kw)
    got = events.read(journal.path)
    for e in got:
        assert contract.validate(e) == [] and contract.undeclared(e) == [], e
    return out, rendered, video, got


def test_a_pass_makes_no_edit(tmp_path):
    out, rendered, video, got = run(tmp_path, Model(verdict("pass", 88)))
    assert out.outcome == "passed" and rendered == [] and video.read_bytes() == b"original"
    assert [e["type"] for e in got] == ["clip_checked", "clip_reviewed"]
    assert json.loads((tmp_path / "work" / "before" / "verdict.json").read_text(encoding="utf-8"))["score"] == 88


def test_exactly_one_edit_even_when_the_critic_asks_again(tmp_path):
    model = Model(verdict("fix", 55, "layout_split_equal", "give the face more room"), verdict("fix", 70, "captions_upper", "captions up"))
    out, rendered, video, got = run(tmp_path, model)
    assert len(rendered) == 1 and rendered[0].mode == "streamer_scene_split_equal" and rendered[0].streamer_crop == CAM
    assert out.outcome == "fixed" and out.decision.mode == "streamer_scene_split_equal" and video.read_bytes() == b"edited"
    assert not (tmp_path / "clip01.fix.mp4").exists() and len(model.prompts) == 2
    assert "already a revised version (edit made: layout_split_equal)" in model.prompts[1]
    assert [e["type"] for e in got] == ["clip_checked", "clip_fixed", "clip_checked", "clip_reviewed"]
    fixed = next(e["data"] for e in got if e["type"] == "clip_fixed")
    assert fixed["before"]["layout"] == "streamer_scene_split" and fixed["after"]["layout"] == "streamer_scene_split_equal"


def test_the_better_of_two_versions_stays_and_the_reason_is_written(tmp_path):
    out, rendered, video, got = run(tmp_path, Model(verdict("fix", 60, "drop_hook", "the hook covers the face"), verdict("fix", 40, "captions_upper")))
    assert len(rendered) == 1 and out.outcome == "kept" and video.read_bytes() == b"original" and out.decision == SPLIT
    assert not (tmp_path / "clip01.fix.mp4").exists()
    reviewed = got[-1]["data"]
    assert reviewed["outcome"] == "kept" and "40 < 60" in reviewed["reason"] and reviewed["fix"] == "drop_hook"


def test_an_unreadable_or_missing_answer_leaves_the_clip(tmp_path):
    for answer in ({"verdict": "maybe", "score": 50}, {"verdict": "fix", "score": "high"}, "model: HTTP 500", ["not", "a", "dict"]):
        out, rendered, video, got = run(tmp_path, Model(answer))
        assert out.outcome == "unchecked" and rendered == [] and video.read_bytes() == b"original"
        assert got[0]["data"]["by"] == "error" and got[-1]["data"]["outcome"] == "unchecked"


def test_a_failed_second_look_keeps_the_edit_the_critic_asked_for(tmp_path):
    out, rendered, video, _ = run(tmp_path, Model(verdict("fix", 50, "captions_center", "lower the captions"), "busy: timeout"))
    assert out.outcome == "fixed" and video.read_bytes() == b"edited" and "not rechecked" in out.reason


def test_the_visible_webcam_is_never_removed(tmp_path):
    out, rendered, video, _ = run(tmp_path, Model(verdict("fix", 50, "layout_scene_only", "show only the game")))
    assert out.outcome == "kept" and rendered == [] and "webcam" in out.reason
    assert apply_fix(Decision("scene_only", CAM, None, CAM), "layout_scene_only") is None        # the streamer alone stays too


def test_reject_and_a_fix_without_code_keep_the_clip(tmp_path):
    for answer in (verdict("reject", 20), verdict("fix", 50, None, "start two seconds later"), verdict("fix", 50, "peak_lower", "peak lower")):
        out, rendered, video, _ = run(tmp_path, Model(answer))
        assert out.outcome == "kept" and rendered == [] and video.read_bytes() == b"original"


def test_a_failed_edit_render_keeps_the_clip(tmp_path):
    out, rendered, video, _ = run(tmp_path, Model(verdict("fix", 50, "drop_hook")), fail_render=True)
    assert out.outcome == "kept" and "failed to render" in out.reason and video.read_bytes() == b"original"
    assert not (tmp_path / "clip01.fix.mp4").exists()


def test_nothing_ever_waits_for_a_person(tmp_path):
    rng = random.Random(14)
    fixes = [*critic.FIXES, "peak_lower", None, "nonsense"]
    for n in range(40):
        answers = [verdict(rng.choice(critic.VERDICTS), rng.randint(0, 100), rng.choice(fixes), rng.choice([None, "w"])) for _ in range(2)]
        if n % 5 == 0:
            answers[rng.randint(0, 1)] = "model: broken"
        out, rendered, _, got = run(tmp_path, Model(*answers), decision=rng.choice([SPLIT, Decision("scene_only", FULL)]))
        assert out.outcome in OUTCOMES and len(rendered) <= 1
        assert "needs_human" not in json.dumps([e["data"] for e in got])


def test_fixes_mirror_production_and_change_one_thing():
    eq = apply_fix(SPLIT, "layout_split_equal")
    assert (eq.mode, eq.streamer_crop, eq.scene_crop, eq.captions, eq.hook) == ("streamer_scene_split_equal", CAM, GAME, "lower", "title")
    assert apply_fix(SPLIT, "layout_streamer_split") is None                                     # already there
    alone = Decision("scene_only", FULL, None, CAM)
    split = apply_fix(alone, "layout_streamer_split")                 # the camera found by the layout goes on top, cut to the slot's shape,
    st = split.streamer_crop                                          # never past the camera; the game beside it
    assert st["x"] >= CAM["x"] and st["y"] >= CAM["y"] and st["x"] + st["width"] <= 0.17 + 1e-9 and st["y"] + st["height"] <= 0.62 + 1e-9
    assert st["width"] * 1920 / (st["height"] * 1080) == pytest.approx(1080 / 640, rel=0.08)
    assert split.scene_crop == {"x": 0.17, "y": 0.0, "width": 0.83, "height": 1.0}
    tight = apply_fix(SPLIT, "webcam_tighter").streamer_crop          # tighter: smaller on every side, inside the old crop
    assert tight["x"] > CAM["x"] and tight["x"] + tight["width"] < CAM["x"] + CAM["width"] and tight["height"] < CAM["height"]
    assert apply_fix(Decision("scene_only", FULL), "webcam_tighter") is None
    assert apply_fix(Decision("scene_only", FULL), "layout_streamer_split") is None             # no camera known: nothing to put on top
    assert apply_fix(SPLIT, "captions_upper").captions == "upper" and apply_fix(SPLIT, "captions_lower") is None
    assert apply_fix(SPLIT, "drop_hook").hook is None and apply_fix(apply_fix(SPLIT, "drop_hook"), "drop_hook") is None
    assert apply_fix(SPLIT, "peak_lower") is None


def test_the_prompt_offers_only_what_this_renderer_can_do():
    p = critic.build_prompt({"duration_s": 31.2, "title": "Кот"}, critic.frame_times(31.2))
    assert "peak_lower" not in p and "(peak) lower or higher" not in p and "no final large lines" in p
    assert "Frame 6: 30.8 s" in p and "Video title: Кот." in p
    assert "There is no edit for the peak lines" in critic.build_prompt({}, critic.frame_times(20), peak_lines=True)
    enum = critic.schema()["properties"]["fix"]["enum"]
    assert set(enum) == {*critic.FIXES, None} and "peak_lower" not in enum


# --- the steady layout vote ---------------------------------------------------------------------------------

def answer(mode, cam=CAM, streamer=CAM, scene=GAME):
    return {"layout": mode, "webcam_region": cam, "streamer_crop": streamer, "scene_crop": scene}


def jitter(r, d):
    return {**r, "x": round(r["x"] + d, 4), "width": round(r["width"] - d, 4)}


def test_the_vote_takes_the_majority_and_median_crops_whatever_the_order():
    answers = [answer("streamer_scene_split", scene=jitter(GAME, 0.01)), answer("streamer_scene_split_equal", scene=jitter(GAME, 0.08)),
               answer("streamer_scene_split", scene=jitter(GAME, -0.004))]
    results = {json.dumps(L.vote(list(p))[0].as_dict(), sort_keys=True) for p in itertools.permutations(answers)}
    assert len(results) == 1                                     # the order of the answers does not matter
    lay, cam, kinds = L.vote(answers)
    # the answers disagree on the split: the slot the near-square webcam fills best decides, not the majority
    assert lay.mode == "streamer_scene_split_equal" and sorted(kinds) == ["streamer_scene_split"] * 2 + ["streamer_scene_split_equal"]
    assert cam == L.inset({"x": 0.0, "y": 0.32, "width": 0.17, "height": 0.3})   # no frames to look at: pulled in by the margin
    # in a split the size follows the slot: the whole height of the frame beside the webcam, the shape of the 1080x960 slot
    sc, st = lay.scene_crop, lay.streamer_crop
    assert sc["y"] == 0.0 and sc["height"] == 1.0 and sc["x"] >= 0.17 and sc["width"] * 1920 / 1080 == pytest.approx(1.125, abs=0.02)
    assert st["x"] >= 0.0 and st["x"] + st["width"] <= 0.17 + 1e-9 and st["y"] >= 0.32 and st["y"] + st["height"] <= 0.62 + 1e-9


def test_crops_in_a_split_keep_the_model_centre_but_not_its_zoom():
    """Real answers of 21.11 disagreed on the zoom (scene width 0.40–0.72) and agreed on the centre: they now give one crop."""
    zooms = [{"x": 0.5 - w / 2, "y": 0.5 - h / 2, "width": w, "height": h} for w, h in ((0.47, 0.6), (0.7, 1.0), (0.56, 0.8), (0.4, 0.53))]
    picks = {json.dumps(L.vote([answer("streamer_scene_split_equal", scene=z) for z in trio])[0].as_dict(), sort_keys=True)
             for trio in itertools.combinations(zooms, 3)}
    assert len(picks) == 1
    lay = L.vote([answer("streamer_scene_split", scene=z) for z in zooms[:3]])[0]
    assert lay.scene_crop["width"] * 1920 / (lay.scene_crop["height"] * 1080) == pytest.approx(1080 / 1280, abs=0.02)   # the 1080x1280 slot
    # a webcam in the top right corner: the scene is the larger part beside it
    corner = {"x": 0.75, "y": 0.0, "width": 0.25, "height": 0.3}
    assert L.beside(corner) == {"x": 0.0, "y": 0.0, "width": 0.75, "height": 1.0}
    assert L.fit_inside({"x": 0.0, "y": 0.0, "width": 0.75, "height": 1.0}, 1.125, (0.9, 0.5))["x"] + 0.633 <= 0.75 + 0.01


def test_small_jitter_gives_the_same_crops():
    rng = random.Random(3)
    picks = set()
    for _ in range(5):
        answers = [answer("streamer_scene_split", streamer=jitter(CAM, rng.uniform(-0.002, 0.002)), scene=jitter(GAME, rng.uniform(-0.002, 0.002)))
                   for _ in range(3)]
        picks.add(json.dumps(L.vote(answers)[0].as_dict(), sort_keys=True))
    assert len(picks) <= 2


def test_a_camera_most_answers_saw_is_never_left_out():
    no_cam = answer("scene_only", cam=None, streamer=None, scene=FULL)
    lay, cam, kinds = L.vote([no_cam, answer("streamer_scene_split"), answer("streamer_scene_split_equal")])
    assert lay.streamer_crop is not None and cam is not None and lay.mode == "streamer_scene_split_equal"
    lay, cam, _ = L.vote([no_cam, no_cam, answer("streamer_scene_split")])
    assert lay.mode == "scene_only" and cam is None                  # one answer of three is not a camera


def test_a_vote_without_a_usable_answer_fails():
    with pytest.raises(L.LayoutError):
        L.vote([{"layout": "weird"}, None, {}])
    lay, _, kinds = L.vote([{"layout": "weird"}, answer("streamer_scene_split")])
    assert lay.mode == "streamer_scene_split" and kinds == ["streamer_scene_split"]


def test_when_the_answers_disagree_on_the_split_the_webcam_shape_decides():
    wide = {"x": 0.7, "y": 0.0, "width": 0.3, "height": 0.3}           # 576x324 px: a 16:9 webcam fills the 1080x640 slot
    a = [answer("streamer_scene_split_equal", cam=wide, streamer=wide), answer("streamer_scene_split_equal", cam=wide, streamer=wide),
         answer("streamer_scene_split", cam=wide, streamer=wide)]
    assert L.vote(a)[0].mode == "streamer_scene_split"
    assert L.best_split(CAM) == "streamer_scene_split_equal" and L.best_split(wide) == "streamer_scene_split"
    # every order and every mix of the two splits: one answer
    picks = {L.vote(list(p))[0].mode for n in range(1, 3) for p in itertools.permutations(
        [answer("streamer_scene_split")] * n + [answer("streamer_scene_split_equal")] * (3 - n))}
    assert picks == {"streamer_scene_split_equal"}
    # all agree: the model's own choice stays
    assert L.vote([answer("streamer_scene_split")] * 3)[0].mode == "streamer_scene_split"


def test_a_pass_after_the_edit_keeps_the_edit_even_with_a_lower_score_and_odd_answers(tmp_path):
    out, _, video, _ = run(tmp_path, Model(verdict("fix", 70, "drop_hook"), verdict("pass", 60)))
    assert out.outcome == "fixed" and video.read_bytes() == b"edited"           # the critic now passes it: the edit stays
    out, rendered, _, _ = run(tmp_path, Model({**verdict("pass", 80), "fix": "drop_hook"}))
    assert out.outcome == "passed" and rendered == []                           # a fix code with pass is not an edit
    assert critic.normalize({**verdict("pass"), "score": 85.0})["score"] == 85 and critic.normalize({**verdict("pass"), "score": 140})["score"] == 100
    assert critic.normalize({**verdict("pass"), "score": "85"}) is None


def test_frames_of_a_short_clip_stay_in_order():
    for d in (1.0, 1.5, 3.0, 31.2):
        t = critic.frame_times(d)
        assert t == sorted(t) and len(set(t)) == 6 and t[-1] < d


# --- the webcam by its real edges (render/camera.py) ------------------------------------------------------------

def stream_frames(n=5, seed=1):
    """Frames at the work size: a moving game everywhere, a still camera at x 0..160, y 175..336 inside a 6 px pink
    overlay frame (a dark 4 px strip inside it on the right), the room in the camera barely moving."""
    from smtv_core.render import camera as C
    rng = np.random.default_rng(seed)
    room = rng.uniform(30, 220, (C.WORK_H, C.WORK_W)).astype(np.float32)
    out = []
    for _ in range(n):
        coarse = rng.uniform(40, 230, (C.WORK_H // 30 + 2, C.WORK_W // 30 + 2))     # the game: smooth, different in every frame
        dy, dx = rng.integers(0, 30, 2)                                            # the picture moves
        f = np.kron(coarse, np.ones((30, 30)))[dy:dy + C.WORK_H, dx:dx + C.WORK_W].astype(np.float32)
        f[175:336, 0:160] = room[175:336, 0:160] + rng.normal(0, 3, (161, 160))
        f[175:181, 0:166] = f[330:336, 0:166] = 200.0                             # the pink frame, top and bottom
        f[175:336, 160:166] = 200.0                                               # and right
        f[181:330, 156:160] = 15.0                                                # a dark strip inside it
        out.append(f)
    return out


def test_the_webcam_box_moves_inside_the_overlay_frame():
    from smtv_core.render import camera as C
    frames = stream_frames()
    W, H = C.WORK_W, C.WORK_H
    box = {"x": 0.0, "y": 170 / H, "width": 172 / W, "height": 172 / H}          # the model's box: a little past the frame
    got = C.refine(frames, box)
    x0, y0 = got["x"] * W, got["y"] * H
    x1, y1 = x0 + got["width"] * W, y0 + got["height"] * H
    assert y0 >= 181 and y1 <= 330 and x1 <= 156                                  # no pink, no dark strip, no game
    assert x0 < 6 and y0 < 190 and y1 > 320 and x1 > 145                         # and not much of the camera lost
    box_inside = {"x": 0.0, "y": 185 / H, "width": 150 / W, "height": 140 / H}    # a box already inside: stays about the same
    again = C.refine(frames, box_inside)
    assert abs(again["y"] * H - 185) < 8 and again["width"] * W > 130


def test_in_a_vote_the_webcam_slot_never_shows_the_frame_on_either_split():
    from smtv_core.render import camera as C
    frames = stream_frames(seed=2)
    W, H = C.WORK_W, C.WORK_H
    cam = {"x": 0.0, "y": 170 / H, "width": 172 / W, "height": 172 / H}
    for mode in ("streamer_scene_split", "streamer_scene_split_equal"):
        lay, found, _ = L.vote([answer(mode, cam=cam, streamer=cam)] * 3, refine=lambda b: C.refine(frames, b))
        st = lay.streamer_crop
        assert st["y"] * H >= 181 - 0.5 and (st["y"] + st["height"]) * H <= 330 + 0.5 and (st["x"] + st["width"]) * W <= 156 + 0.5, mode
    lay, found, _ = L.vote([answer("streamer_scene_split", cam=cam, streamer=cam)] * 3, refine=lambda b: 1 / 0)   # no frames: a margin
    assert found == L.inset(L.median_rect([cam], outwards=False))


def test_the_critic_is_asked_about_a_frame_in_the_webcam_slot():
    p = critic.build_prompt({"duration_s": 30}, critic.frame_times(30))
    assert "webcam_frame" in p and "overlay frame" in p and "webcam_tighter" in p
    assert "webcam_frame" in critic.schema()["properties"]["issues"]["items"]["properties"]["code"]["enum"]
    v = critic.normalize({**verdict("fix", 60, "webcam_tighter"), "issues": [{"code": "webcam_frame", "severity": "major", "detail": "pink strip"}]})
    assert v["fix"] == "webcam_tighter" and v["issues"][0]["code"] == "webcam_frame"


# --- several clips in one call (B12) ------------------------------------------------------------------------------

class Batch:
    """Answers a call for several clips with the given verdict per video id (a str: an error for the whole call)."""
    def __init__(self, *answers):
        self.answers, self.calls = list(answers), []

    def __call__(self, prompt, schema, images, purpose):
        assert purpose == "critic"
        single = "reviews" not in schema["properties"]            # one clip alone: the question as before B12
        ids = ["video1"] if single else schema["properties"]["reviews"]["items"]["properties"]["video"]["enum"]
        self.calls.append((prompt, ids, len(images)))
        a = self.answers.pop(0)
        if isinstance(a, str):
            return None, {"error": a}
        return (a["video1"] if single else {"reviews": [{"video": v, **a[v]} for v in ids if v in a]}), {"seconds": 1.0}


def items(tmp_path, n, fail_render=()):
    out = []
    for k in range(n):
        video = tmp_path / f"clip0{k + 1}.mp4"
        video.write_bytes(f"original {k}".encode())

        def rerender(d, path, k=k):
            if k in fail_render:
                raise RuntimeError("ffmpeg broke")
            path.write_bytes(b"edited")
            return path
        out.append(critic.Item(f"clip0{k + 1}", video, SPLIT, {"duration_s": 30.0, "title": f"t{k}"}, tmp_path / "work" / f"clip0{k + 1}", rerender))
    return out


def test_three_clips_are_looked_at_in_one_call_and_their_edits_in_another(tmp_path):
    model = Batch({"video1": verdict(), "video2": verdict("fix", 60, "captions_upper", "captions up"), "video3": verdict("reject", 20)},
                  {"video1": verdict("pass", 80)})
    journal = Journal(tmp_path / "job", tool="vodcut", subscribers=[])
    got = critic.review_many(model, items(tmp_path, 3), journal.emit)
    assert [o.outcome for o in got] == ["passed", "fixed", "kept"] and got[1].decision.captions == "upper"
    assert len(model.calls) == 2 and model.calls[0][1] == ["video1", "video2", "video3"] and model.calls[1][1] == ["video1"]
    assert model.calls[0][2] == 3 * critic.BATCH_FRAMES                       # four small frames of each clip
    assert "=== video2 ===" in model.calls[0][0] and "Role: release editor" in model.calls[0][0]      # the anchor stays
    assert "already a revised version" in model.calls[1][0]
    assert (tmp_path / "clip02.mp4").read_bytes() == b"edited" and (tmp_path / "clip01.mp4").read_bytes() == b"original 0"
    for e in events.read(journal.path):
        assert contract.validate(e) == [] and contract.undeclared(e) == [], e


def test_a_clip_the_batch_answer_leaves_out_is_unchecked_and_the_others_keep_their_verdicts(tmp_path):
    model = Batch({"video1": verdict(), "video3": verdict("pass", 70)})
    got = critic.review_many(model, items(tmp_path, 3), lambda *a, **k: None)
    assert [o.outcome for o in got] == ["passed", "unchecked", "passed"] and "video2" in got[1].reason
    failed = critic.review_many(Batch("busy: 503"), items(tmp_path, 2), lambda *a, **k: None)
    assert [o.outcome for o in failed] == ["unchecked", "unchecked"] and all("503" in o.reason for o in failed)


def test_more_clips_than_a_batch_take_more_calls_and_one_clip_keeps_the_old_question(tmp_path):
    model = Batch(*[{f"video{k}": verdict() for k in range(1, 5)}] * 2)
    critic.review_many(model, items(tmp_path, 6), lambda *a, **k: None)
    assert [ids for _, ids, _ in model.calls] == [["video1", "video2", "video3", "video4"], ["video1", "video2"]]
    single = Model(verdict())
    critic.review_many(single, items(tmp_path, 1), lambda *a, **k: None)
    assert len(single.prompts) == 1 and "=== video" not in single.prompts[0]


def test_frames_of_one_clip_that_cannot_be_taken_leave_the_others_checked(tmp_path, monkeypatch):
    real = critic.stills.extract

    def extract(src, times, out_dir, width=1280):
        if "clip02" in str(out_dir):
            raise RuntimeError("no frames")
        return real(src, times, out_dir, width)
    monkeypatch.setattr(critic.stills, "extract", extract)
    model = Batch({"video1": verdict(), "video3": verdict()})
    got = critic.review_many(model, items(tmp_path, 3), lambda *a, **k: None)
    assert [o.outcome for o in got] == ["passed", "unchecked", "passed"] and "no frames" in got[1].reason
    assert model.calls[0][1] == ["video1", "video3"]


def test_an_edit_that_cannot_replace_the_clip_keeps_the_first_version_and_the_others_keep_their_outcomes(tmp_path, monkeypatch):
    model = Batch({"video1": verdict("fix", 60, "captions_upper", "up"), "video2": verdict()}, {"video1": verdict("pass", 80)})
    real = critic.os.replace

    def locked(src, dst):
        if str(dst).endswith("clip01.mp4"):
            raise PermissionError(13, "used by another process")
        return real(src, dst)
    monkeypatch.setattr(critic.os, "replace", locked)
    decided = {}
    got = critic.review_many(model, items(tmp_path, 2), lambda *a, **k: None, outcomes=decided)
    assert [o.outcome for o in got] == ["kept", "passed"] and "could not be replaced" in got[0].reason
    assert (tmp_path / "clip01.mp4").read_bytes() == b"original 0" and not (tmp_path / "clip01.fix.mp4").exists()
    assert set(decided) == {0, 1}
