"""Stage 15: what used to fail silently in the render — a hanging download, a model out of quota halfway, a broken
renders.json, a clip made but never checked."""
import json
import subprocess

import pytest

from smtv_core import events, proc
from smtv_core.llm import Answer, QuotaExceeded
from smtv_core.settings import ModelSettings

from vodcut import render
from vodcut.model import Asker
from test_render_step import CAM, GAME, clip, critic_job, make_job

LAYOUT = {"layout": "streamer_scene_split", "live_chat_side": "none", "webcam_region": CAM, "streamer_crop": CAM, "scene_crop": GAME,
          "screen_essential": True, "stable_across_frames": True, "needs_review": False, "reason": "x", "uncertainties": []}
PASS = {"verdict": "pass", "score": 80, "issues": [], "wish": None, "fix": None, "summary": "fine"}


# --- a download that hangs ---------------------------------------------------------------------------------------

def local_on(monkeypatch):
    from vodcut import local_download, options
    monkeypatch.setattr(options, "local_download", lambda: True)
    monkeypatch.setattr(local_download, "_yt_dlp", lambda: object())


def test_a_stalled_piece_download_is_stopped_and_leaves_nothing_half_done(tmp_path, monkeypatch):
    """«Download on this computer» (yt-dlp here): a download that hangs is stopped, nothing half-done stays."""
    seen = {}
    local_on(monkeypatch)

    def stalls(cmd, timeout_s, **kw):
        seen["cmd"], seen["timeout"] = cmd, timeout_s
        (tmp_path / "pieces" / "clip01.mp4.part").write_bytes(b"half")
        raise proc.TimedOut("yt-dlp (clip01) did not finish in 600 s and was stopped")

    monkeypatch.setattr(proc, "run", stalls)
    with pytest.raises(proc.TimedOut):
        render.fetch_piece({"kind": "link", "url": "https://www.twitch.tv/videos/1"}, 100, 130, tmp_path / "pieces" / "clip01.mp4")
    assert not list((tmp_path / "pieces").iterdir())
    assert "--socket-timeout" in seen["cmd"] and "*98.500-131.500" in seen["cmd"] and seen["timeout"] >= 600


def test_a_failed_piece_download_says_why(tmp_path, monkeypatch):
    local_on(monkeypatch)
    monkeypatch.setattr(proc, "run", lambda cmd, t, **kw: subprocess.CompletedProcess(cmd, 1, "", "ERROR: HTTP Error 403"))
    with pytest.raises(RuntimeError, match="HTTP Error 403"):
        render.fetch_piece({"kind": "link", "url": "https://x/1"}, 10, 20, tmp_path / "pieces" / "clip01.mp4")


def test_a_hanging_ffmpeg_fails_its_clip_and_the_others_go_on(tmp_path, monkeypatch):
    job = make_job(tmp_path, [clip("clip01"), clip("clip02")])

    def fake(src, out, *a, **kw):
        if out.stem == "clip01":
            raise render.ffmpeg.RenderError("ffmpeg on clip01.mp4 did not finish in 600 s and was stopped")
        out.write_bytes(b"mp4")
        return out

    monkeypatch.setattr(render.ffmpeg, "render", fake)
    report = render.render_all(job, None)
    assert [r["status"] for r in report] == ["failed", "done"] and "did not finish" in report[0]["error"]


# --- out of quota halfway --------------------------------------------------------------------------------------

def quota_job(tmp_path, monkeypatch, clips=3):
    job, asker, asked = critic_job(tmp_path, monkeypatch, [])
    (job / "clips.json").write_text(json.dumps({**json.loads((job / "clips.json").read_text(encoding="utf-8")),
                                                "clips": [clip(f"clip0{i}") for i in range(1, clips + 1)]}), encoding="utf-8")
    return job, asker, asked


def test_out_of_quota_halfway_stops_the_clips_left_instead_of_the_whole_frame(tmp_path, monkeypatch):
    job, asker, asked = quota_job(tmp_path, monkeypatch)
    caller = asker.caller

    def runs_out(model, prompt, schema, images=None):
        if len(asked) >= 2 and "verdict" not in schema["properties"]:     # clip01: its layout and the recording's banner, then nothing
            raise QuotaExceeded("insufficient_quota")
        if "verdict" in schema["properties"]:
            asked.append("critic")
            return Answer(dict(PASS), "", 0.1)
        return caller(model, prompt, schema, images)

    asker.caller = runs_out
    report = render.render_all(job, asker)
    assert [r["status"] for r in report] == ["done", "failed", "failed"]
    assert all("out of quota" in r["error"] for r in report[1:])
    assert sorted(p.name for p in (job / "clips").glob("*.mp4")) == ["clip01.mp4"]     # no clip made with a worse layout
    got = events.read(job)
    assert any(e["type"] == "error" and e["data"]["stage"] == "render" and "quota" in e["data"]["message"] for e in got)
    assert not [e for e in got if e["type"] == "layout_chosen" and e["data"]["clip"] != "clip01"]
    # the quota is back: the next render makes the two clips left and leaves clip01 alone
    def answer(s):
        if "reviews" in s["properties"]:              # B12: the critic looks at the two clips in one call
            return {"reviews": [{**PASS, "video": v} for v in s["properties"]["reviews"]["items"]["properties"]["video"]["enum"]]}
        return dict(PASS) if "verdict" in s["properties"] else {"regions": [], "excluded": [], "notes": ""} if "regions" in s["properties"] else LAYOUT
    fresh = Asker(ModelSettings(provider="openai", model="m"), lambda m, p, s, images=None: Answer(answer(s), "", 0.1))
    again = render.render_all(job, fresh)
    assert [r["status"] for r in again] == ["done"] * 3 and [r.get("critic", {}).get("outcome") for r in again] == ["passed"] * 3
    # B12: the critic looks at the clips after all are made, so clip01's check came after the quota ran out: it is
    # checked now, with the two new clips in one call, and not made again
    assert sorted(p.name for p in (job / "clips").glob("*.mp4")) == ["clip01.mp4", "clip02.mp4", "clip03.mp4"]
    first_run = [e for e in events.read(job) if e["type"] == "clip_reviewed" and e["data"]["clip"] == "clip01"]
    assert [e["data"]["outcome"] for e in first_run] == ["unchecked", "passed"]


def test_a_clip_left_with_the_whole_frame_for_want_of_a_model_is_made_again_when_one_answers(tmp_path, monkeypatch):
    job, asker, asked = critic_job(tmp_path, monkeypatch, [dict(PASS)])
    [r] = render.render_all(job, None)                                   # no model: the whole frame
    assert r["status"] == "done" and (job / "clips" / "clip01.mp4").read_bytes().startswith(b"scene_only")
    [r] = render.render_all(job, asker)
    assert (job / "clips" / "clip01.mp4").read_bytes().startswith(b"streamer_scene_split") and r["layout_by"].startswith("model")
    [r] = render.render_all(job, asker)                                  # chosen by the model now: left alone
    assert asked.count("layout") == 1 and r.get("critic", {}).get("outcome") == "passed"      # B12: one answer, sure of itself


# --- renders.json --------------------------------------------------------------------------------------------

def test_a_broken_renders_json_is_reported_and_kept_aside_not_read_as_empty(tmp_path, monkeypatch):
    job = make_job(tmp_path, [clip("clip01")])
    monkeypatch.setattr(render.ffmpeg, "render", lambda src, out, *a, **k: (out.write_bytes(b"mp4"), out)[1])
    (job / "renders.json").write_text('[{"id": "clip01", "start_', encoding="utf-8")
    (job / "layouts.json").write_text("{oops", encoding="utf-8")
    render.render_all(job, None)
    errors = [e["data"]["message"] for e in events.read(job) if e["type"] == "error"]
    assert any("renders.json could not be read" in m and "renders.json.bad" in m for m in errors)
    assert any("layouts.json could not be read" in m for m in errors)
    assert (job / "renders.json.bad").read_text(encoding="utf-8").startswith('[{"id"') and (job / "layouts.json.bad").exists()
    assert json.loads((job / "renders.json").read_text(encoding="utf-8"))[0]["id"] == "clip01"


def test_renders_json_is_never_left_half_written(tmp_path, monkeypatch):
    job = make_job(tmp_path, [clip("clip01"), clip("clip02")])
    monkeypatch.setattr(render.ffmpeg, "render", lambda src, out, *a, **k: (out.write_bytes(b"mp4"), out)[1])
    render.render_all(job, None)
    good = (job / "renders.json").read_text(encoding="utf-8")
    real = json.dumps

    def dies(data, *a, **kw):
        text = real(data, *a, **kw)
        raise OSError("disk full after " + str(len(text)))

    (job / "clips" / "clip02.mp4").unlink()
    monkeypatch.setattr(render.json, "dumps", dies)
    with pytest.raises(OSError):
        render.render_all(job, None)
    monkeypatch.setattr(render.json, "dumps", real)
    assert (job / "renders.json").read_text(encoding="utf-8") == good


def test_renders_json_is_written_after_every_clip(tmp_path, monkeypatch):
    job = make_job(tmp_path, [clip("clip01"), clip("clip02")])
    seen = []

    def fake(src, out, *a, **k):
        if (job / "renders.json").exists():
            seen.append([r["id"] for r in json.loads((job / "renders.json").read_text(encoding="utf-8"))])
        out.write_bytes(b"mp4")
        return out

    monkeypatch.setattr(render.ffmpeg, "render", fake)
    render.render_all(job, None)
    assert seen == [["clip01"]]                       # clip01's row was there before clip02 was made


# --- a clip made but not checked -------------------------------------------------------------------------------

def test_a_clip_made_but_never_checked_is_checked_on_the_next_run_without_being_made_again(tmp_path, monkeypatch):
    job, asker, asked = critic_job(tmp_path, monkeypatch, [dict(PASS)])
    caller = asker.caller

    def killed(model, prompt, schema, images=None):
        if "verdict" in schema["properties"]:
            raise KeyboardInterrupt                   # the process ends while the critic looks
        return caller(model, prompt, schema, images)

    asker.caller = killed
    with pytest.raises(KeyboardInterrupt):
        render.render_all(job, asker)
    [row] = json.loads((job / "renders.json").read_text(encoding="utf-8"))
    assert row["status"] == "done" and "critic" not in row and (job / "clips" / "clip01.mp4").exists()
    made = []
    real = render.ffmpeg.render
    monkeypatch.setattr(render.ffmpeg, "render", lambda *a, **k: (made.append(a[1]), real(*a, **k))[1])
    asker.caller = caller
    [r] = render.render_all(job, asker)
    assert made == [] and asked.count("critic") == 1 and r["critic"]["outcome"] == "passed"
    assert json.loads((job / "renders.json").read_text(encoding="utf-8"))[0]["critic"]["outcome"] == "passed"
    assert asked.count("layout") == 1                 # the layout came from the job's cache


# --- after the silent-failure review ---------------------------------------------------------------------------

def test_ads_not_looked_for_for_want_of_an_answer_are_looked_for_again(tmp_path, monkeypatch):
    job, asker, asked = critic_job(tmp_path, monkeypatch, [dict(PASS), dict(PASS)])
    caller = asker.caller
    busy = [True]

    def flaky(model, prompt, schema, images=None):
        if "regions" in schema["properties"] and busy[0]:
            from smtv_core.llm import ProviderError
            raise ProviderError("503")
        return caller(model, prompt, schema, images)

    asker.caller = flaky
    [r] = render.render_all(job, asker)
    assert r["ads_by"].startswith("none:")
    assert any(e["type"] == "error" and "nothing is blurred" in e["data"]["message"] for e in events.read(job))
    busy[0] = False
    [r] = render.render_all(job, asker)
    assert r["ads_by"] == "model" and asked.count("banner") == 1


def test_a_failed_write_of_renders_json_does_not_stop_the_clips(tmp_path, monkeypatch):
    job = make_job(tmp_path, [clip("clip01"), clip("clip02")])
    monkeypatch.setattr(render.ffmpeg, "render", lambda src, out, *a, **k: (out.write_bytes(b"mp4"), out)[1])
    real, calls = render._write_json_file, []

    def flaky(path, data):
        calls.append(1)
        if len(calls) == 1:
            raise OSError("disk full")
        real(path, data)

    monkeypatch.setattr(render, "_write_json_file", flaky)
    report = render.render_all(job, None)
    assert [r["status"] for r in report] == ["done", "done"]
    assert sorted(r["id"] for r in json.loads((job / "renders.json").read_text(encoding="utf-8"))) == ["clip01", "clip02"]
    assert any(e["type"] == "error" and "could not be written" in e["data"]["message"] for e in events.read(job))


def test_a_clip_only_checked_keeps_the_layout_it_was_made_with(tmp_path, monkeypatch):
    job, asker, asked = critic_job(tmp_path, monkeypatch, [dict(PASS)])
    render.render_all(job, asker, options={"critic": False})
    assert asked.count("layout") == 1
    cache = json.loads((job / "layouts.json").read_text(encoding="utf-8"))
    cache["clip01"]["key"] = "made by an older rule"                                  # choose_layout would ask again
    (job / "layouts.json").write_text(json.dumps(cache), encoding="utf-8")
    [r] = render.render_all(job, asker)
    assert asked.count("layout") == 1 and r["layout"] == "streamer_scene_split" and r["critic"]["outcome"] == "passed"


def test_swearing_is_starred_in_the_burned_captions_and_hook(tmp_path, monkeypatch):
    """Stage 15: VodCut burned «БЛЯДЬ» as said; production stars it («Б**ДЬ»)."""
    job = make_job(tmp_path, [{**clip("clip01"), "title": "Ну блядь опять"}])
    words = [{"word": " ну", "start": 10.0, "end": 10.2}, {"word": " блядь,", "start": 10.3, "end": 10.7}, {"word": " опять.", "start": 10.8, "end": 11.0}]
    (job / "transcript.json").write_text(json.dumps({"segments": [{"start": 10.0, "end": 11.0, "text": "ну блядь, опять.", "words": words}]},
                                                    ensure_ascii=False), encoding="utf-8")
    seen = {}
    monkeypatch.setattr(render.ffmpeg, "render", lambda src, out, s, e, layout, ass, fonts, **k: (seen.update(ass=ass.read_text(encoding="utf-8")),
                                                                                                    out.write_bytes(b"mp4"), out)[2])
    render.render_all(job, None)
    assert "Б**ДЬ" in seen["ass"] and "БЛЯДЬ" not in seen["ass"]


# --- pieces through StreamMoment (stage 23) ----------------------------------------------------------------------

class FakeTicket:
    made: list = []

    def __init__(self, url, on_wait=None):
        self.id, self.closed = "t1", 0
        FakeTicket.made.append(self)

    def fetch(self, track, dest, start_s=None, end_s=None, on_progress=None):
        assert track == "video"
        dest.write_bytes(b"segments")
        return 90.0

    def close(self):
        self.closed += 1
        self.id = ""


def through_streammoment(monkeypatch):
    from smtv_core import media
    from vodcut import options
    FakeTicket.made = []
    monkeypatch.setattr(options, "local_download", lambda: False)
    monkeypatch.setattr(media, "Ticket", FakeTicket)
    monkeypatch.setattr(render, "_remux", lambda src, dest: dest.write_bytes(src.read_bytes()))


def test_a_piece_through_streammoment_keeps_its_offset_and_a_dropped_one_takes_none_along(tmp_path, monkeypatch):
    through_streammoment(monkeypatch)
    info = {"kind": "link", "url": "https://www.twitch.tv/videos/2934906889"}
    dest = tmp_path / "pieces" / "clip01.mp4"
    assert render.fetch_piece(info, 95, 121, dest) == (dest, 90.0)
    assert (tmp_path / "pieces" / "clip01.mp4.offset").read_text(encoding="utf-8") == "90.000"
    assert not (tmp_path / "pieces" / "clip01.segments").exists()
    assert render.fetch_piece(info, 95, 121, dest) == (dest, 90.0), "the kept piece is used with its own offset"
    assert len(FakeTicket.made) == 1, "one ticket for the whole render"
    render.close_tickets()
    assert FakeTicket.made[0].closed == 1 and not render._tickets
    # Fit moved the clip: its piece and the offset go together
    render.drop_stale(tmp_path, {"id": "clip01", "start_s": 200, "end_s": 230}, {"clip01": (95, 121)})
    assert not list((tmp_path / "pieces").iterdir())


def test_a_piece_that_failed_leaves_no_offset(tmp_path, monkeypatch):
    from smtv_core import media
    through_streammoment(monkeypatch)

    def refuses(self, *a, **kw):
        raise media.MediaError("media_segment_gone")

    monkeypatch.setattr(FakeTicket, "fetch", refuses)
    with pytest.raises(RuntimeError, match="did not download through StreamMoment.*no longer gives"):
        render.fetch_piece({"kind": "link", "url": "https://www.twitch.tv/videos/2934906889"}, 95, 121, tmp_path / "pieces" / "clip01.mp4")
    assert not list((tmp_path / "pieces").glob("*"))
    render.close_tickets()


def test_render_gives_its_queue_place_back_even_when_a_clip_fails(tmp_path, monkeypatch):
    through_streammoment(monkeypatch)
    job = make_job(tmp_path, [clip("clip01")])
    data = json.loads((job / "clips.json").read_text(encoding="utf-8"))
    data["source"] = {"kind": "link", "url": "https://www.twitch.tv/videos/2934906889"}
    (job / "clips.json").write_text(json.dumps(data), encoding="utf-8")

    def broken(*a, **kw):
        raise render.ffmpeg.RenderError("ffmpeg failed")

    monkeypatch.setattr(render.ffmpeg, "render", broken)
    report = render.render_all(job, None)
    assert report[0]["status"] == "failed"
    assert [t.closed for t in FakeTicket.made] == [1] and not render._tickets


def test_a_clip_left_unchecked_without_a_known_layout_is_made_again_not_checked_with_another(tmp_path, monkeypatch):
    job, asker, asked = critic_job(tmp_path, monkeypatch, [dict(PASS), dict(PASS)])
    render.render_all(job, asker, options={"critic": False})
    rows = json.loads((job / "renders.json").read_text(encoding="utf-8"))
    rows[0].pop("critic", None)
    (job / "renders.json").write_text(json.dumps(rows), encoding="utf-8")
    (job / "layouts.json").unlink()                       # what it was made with is not known any more
    made = []
    real = render.ffmpeg.render
    monkeypatch.setattr(render.ffmpeg, "render", lambda *a, **k: (made.append(a[1]), real(*a, **k))[1])
    [r] = render.render_all(job, asker)
    assert made and r["critic"]["outcome"] == "passed"   # made again with the layout chosen now, then checked
