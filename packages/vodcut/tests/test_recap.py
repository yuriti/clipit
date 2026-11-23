"""The recap (stage 12): the story from the model, the plan of parts, the chapters, the encode commands, the switch."""
import argparse
import json
import subprocess
from pathlib import Path

import pytest
from smtv_core.checks import OK, Check
from smtv_core.events import Journal, contract
from smtv_core.llm import Answer, ProviderError
from smtv_core.settings import ModelSettings, Settings

from vodcut import options
from vodcut import recap as recap_step
from vodcut import tool as tool_module
from vodcut.model import Asker
from vodcut.recap import edit, encode, signals, story

CAM = {"x": 0.75, "y": 0.0, "width": 0.25, "height": 0.3}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)


def speech(start, text, step=0.5):
    """A segment of words `step` seconds apart."""
    words = [{"word": " " + w, "start": round(start + i * step, 2), "end": round(start + i * step + 0.3, 2)} for i, w in enumerate(text.split())]
    return {"start": words[0]["start"], "end": words[-1]["end"], "text": text, "words": words}


SEGMENTS = [speech(100, "ну что погнали сегодня играем"), speech(140, "смотри какой там босс огромный"), speech(160, "мы его убили наконец"),
            speech(600, "а теперь история про кота"), speech(640, "кот пришёл и попросил поесть"),
            speech(1190, "всем спасибо за стрим до завтра")]
EPISODES = [{"episode_id": "e000", "episode_start_s": 138, "episode_end_s": 170, "status": "ok", "verdict": "good", "score": 70, "format": "story",
             "title": "Босс", "reason": "победа"},
            {"episode_id": "e001", "episode_start_s": 598, "episode_end_s": 650, "status": "ok", "verdict": "strong", "score": 82, "format": "story",
             "title": "Кот", "reason": "смешно"}]
FACTS = {"channel": "streamer", "title": "Игры", "duration_s": 1200.0, "language": "ru", "url": "https://www.twitch.tv/videos/1"}


def answer(*chapters, title="streamer: босс и кот", hook="Стрим про босса и кота."):
    return {"title": title, "hook": hook, "chapters": [{"title": t, "parts": parts} for t, parts in chapters]}


def part(start, end, role="highlight", pace="tight", peaks=(), music=False):
    return {"start": start, "end": end, "role": role, "pace": pace, "why": "x", "peaks": list(peaks), "music": music}


GOOD = answer(("Босс", [part("0:02:18", "0:02:45", peaks=["0:02:42"])]), ("Кот", [part("0:09:58", "0:10:45")]))


def asker_of(*answers):
    seen = []

    def caller(model, prompt, schema, images=None):
        seen.append({"prompt": prompt, "images": images, "schema": schema})
        data = answers[min(len(seen) - 1, len(answers) - 1)]
        if isinstance(data, Exception):
            raise data
        return Answer(data, "", 0.5)
    return Asker(ModelSettings(provider="openai", model="m"), caller), seen


# ---- the story --------------------------------------------------------------------------------------------------
def test_the_story_is_put_in_stream_order_snapped_merged_and_cut_out_of_muted_spans():
    raw = answer(("Кот", [part("0:09:58", "0:10:45")]),                                   # chapters in the wrong order
                 ("Босс", [part("0:02:18", "0:02:45", peaks=["0:02:42", "9:99:99"]), part("0:02:40", "0:03:10", pace="loose"),   # overlapping
                           part("bad", "0:04:00"), part("0:05:00", "0:05:01"), "not a part"]))
    raw["chapters"].append("not a chapter")
    s = story.normalize(raw, SEGMENTS, muted=[(620.0, 630.0)], duration=1200)
    spans = [(p["start_s"], p["end_s"]) for p in s["parts"]]
    assert spans == sorted(spans) and all(a < b for a, b in spans)
    assert s["parts"][0]["start_s"] == pytest.approx(139.8)          # snapped to the word «смотри» at 140.0, 0.2 s before it
    assert s["parts"][0]["pace"] == "loose" and s["parts"][0]["peaks_s"] == [162.0]    # merged: the looser pace, the valid peak
    cat = [p for p in s["parts"] if p["start_s"] > 500]
    assert [(round(a), round(b)) for a, b in ((p["start_s"], p["end_s"]) for p in cat)] == [(600, 620), (630, 645)]   # the muted span is cut out
    # chapters never go back in time: «Кот» was asked first but comes later, so its parts join the chapter before
    assert [p["chapter"] for p in s["parts"]] == [0, 0, 0] and [c["title"] for c in s["chapters"]] == ["Босс"]
    assert not s["content_absent"]


def test_a_crooked_answer_is_asked_again_and_then_the_story_is_used():
    asker, seen = asker_of({"chapters": "nonsense"}, GOOD)
    s = story.ask(asker, FACTS, EPISODES, SEGMENTS)
    assert len(seen) == 2 and [c["title"] for c in s["chapters"]] == ["Босс", "Кот"]
    assert "e001 0:09:58–0:10:50 strong 82" in seen[0]["prompt"] and "0:02:20 смотри какой там босс огромный" in seen[0]["prompt"]
    assert seen[0]["schema"]["properties"]["chapters"]["type"] == "array"


def test_no_usable_story_fails_with_the_reason():
    asker, seen = asker_of({"title": "x", "chapters": [{"title": "a", "parts": [part("0:01:00", "0:01:01")]}]}, ProviderError("connection reset"))
    with pytest.raises(story.RecapError, match="no usable story"):
        story.ask(asker, FACTS, EPISODES, SEGMENTS)
    assert len(seen) == 2


def test_a_story_over_28_minutes_is_asked_once_more_with_the_numbers():
    long = answer(("Всё", [part("0:00:10", "0:19:59"), part("0:20:00", "0:39:00")]))
    asker, seen = asker_of(long, GOOD)
    s = story.ask(asker, {**FACTS, "duration_s": 3600.0}, EPISODES, SEGMENTS)
    assert len(seen) == 2 and "It must be at most 28 minutes" in seen[1]["prompt"] and s["source_s"] < 28 * 60


def test_a_story_still_over_28_minutes_is_cut_by_rule_not_lost():
    """Stage 15: a 5.7 h stream lost its whole recap because two answers were 28.3 min of source."""
    parts = [{"start_s": 0.0, "end_s": 600.0, "role": "highlight"}, {"start_s": 700.0, "end_s": 1300.0, "role": "context"},
             {"start_s": 1400.0, "end_s": 1500.0, "role": "context"}, {"start_s": 1600.0, "end_s": 2300.0, "role": "highlight"}]
    s = {"parts": parts, "source_s": 2000.0}
    story.trim_to_limit(s)
    assert [(p["start_s"], p["end_s"]) for p in s["parts"]][1] == (700.0, 980.0) and s["source_s"] == 1680.0   # the longest link shortened
    s = {"parts": [{"start_s": 0.0, "end_s": 1000.0, "role": "highlight"}, {"start_s": 1100.0, "end_s": 1700.0, "role": "highlight"},
                   {"start_s": 2000.0, "end_s": 2105.0, "role": "highlight"}, {"start_s": 2200.0, "end_s": 2201.0, "role": "context"}],
         "source_s": 1706.0}
    story.trim_to_limit(s)
    assert [p["start_s"] for p in s["parts"]] == [0.0, 1100.0, 2000.0] and s["parts"][2]["end_s"] == 2080.0   # a 1 s link went, then a highlight shortened
    long = answer(("Всё", [part("0:00:10", "0:19:59"), part("0:20:00", "0:39:00")]))
    asker, seen = asker_of(long, long)
    got = story.ask(asker, {**FACTS, "duration_s": 3600.0}, EPISODES, SEGMENTS)
    assert len(seen) == 2 and got["trimmed"] and got["source_s"] <= 28 * 60 and got["parts"]


def test_an_empty_story_means_no_recap():
    asker, _ = asker_of(answer())
    assert story.ask(asker, FACTS, EPISODES, SEGMENTS)["status"] == "skipped"


def test_the_recap_ends_on_the_goodbye():
    asker, _ = asker_of(GOOD)
    s = story.ask(asker, FACTS, EPISODES, SEGMENTS)
    assert s["parts"][-1]["why"].startswith("goodbye") and s["parts"][-1]["start_s"] == pytest.approx(1189.7)
    assert s["parts"][-1]["end_s"] <= 1200 - story.VIDEO_END_GUARD_S


# ---- the edit ---------------------------------------------------------------------------------------------------
def test_long_pauses_are_cut_and_peaks_and_loud_reactions_are_kept():
    words = [{"text": "a", "start": 10.0, "end": 10.3}, {"text": "b", "start": 15.0, "end": 15.3}, {"text": "c", "start": 30.0, "end": 30.3}]
    p = {"start_s": 10.0, "end_s": 32.0, "pace": "tight"}
    pieces = edit.keep_pieces(p, words, peaks=[20.0])
    assert pieces[0][0] == 10.0 and pieces[-1][1] <= 32.0
    assert any(a <= 19.0 and b >= 22.0 for a, b in pieces)                  # 1 s before and 2 s after the peak stay
    assert sum(b - a for a, b in pieces) < 12                              # most of the 22 s of silence went
    loose = edit.keep_pieces({**p, "pace": "loose"}, words)
    assert sum(b - a for a, b in loose) > sum(b - a for a, b in pieces)     # gameplay keeps its pauses
    timeline = edit.Timeline(pieces)
    assert timeline.out(10.0) == 0 and timeline.out(31.0) == pytest.approx(timeline.duration - (pieces[-1][1] - 31.0))


def test_the_plan_puts_parts_after_the_cold_open_with_chapters_shots_and_ads():
    asker, _ = asker_of(GOOD)
    s = story.ask(asker, FACTS, EPISODES, SEGMENTS)
    levels = [-30.0] * 300
    levels[40:45] = [-5.0] * 5                                               # a scream 4 s into the first part
    sig = {str(p["index"]): {"levels": levels if p["index"] == 0 else [], "cam": CAM if p["index"] == 0 else None, "ads": [[100, 50, 10, 20]]} for p in s["parts"]}
    plan = edit.plan(s, sig, story.words_of(SEGMENTS), FACTS)
    first = plan["parts"][0]
    assert plan["intro"]["clips"] and first["out_start_s"] == plan["intro"]["duration_s"]
    assert first["shots"] and first["punch_rect"]["height"] == pytest.approx(0.3 * 1080 / edit.CAM_FILL, abs=2)
    assert all(p["blur"] == [[100, 50, 10, 20]] for p in plan["parts"]) and plan["ads_blurred"] == 1
    assert [c["title"] for c in plan["chapters"]] == ["Босс", "Кот"]
    assert plan["chapters"][0]["start_s"] == plan["intro"]["duration_s"]
    assert plan["duration_s"] == pytest.approx(plan["intro"]["duration_s"] + sum(p["duration_s"] for p in plan["parts"]), abs=0.05)
    starts = [p["out_start_s"] for p in plan["parts"]]
    assert starts == sorted(starts)


def test_chapters_start_at_zero_for_youtube_and_the_description_carries_them():
    chapters = [{"start_s": 5.4, "title": "Начало"}, {"start_s": 75.2, "title": "Кот"}, {"start_s": 3725.0, "title": "Конец"}]
    assert edit.chapters_text(chapters) == "00:00 Начало\n01:15 Кот\n1:02:05 Конец\n"
    text = edit.description(FACTS, "О чём стрим.", chapters)
    assert text.startswith("О чём стрим.\n\nСтрим «Игры», 20 мин.") and "01:15 Кот" in text
    assert "Стример: streamer" in text and "Полный стрим: https://www.twitch.tv/videos/1" in text
    assert edit.description({**FACTS, "language": "de"}, "", chapters).count("Stream «Игры», 20 min.") == 1


# ---- the encode -------------------------------------------------------------------------------------------------
def fake_run(returncode=0, stdout=""):
    calls = []

    def run(argv, **_k):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, returncode, stdout, "boom")
    return run, calls


def test_without_nvenc_the_processor_encodes(monkeypatch):
    encode.encoder.cache_clear()
    monkeypatch.setattr(encode.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    run, calls = fake_run(stdout=" V....D libx264  H.264\n")
    monkeypatch.setattr(encode.proc, "run", lambda a, *_x, **_k: run(a))
    assert encode.encoder() == "cpu" and len(calls) == 1
    encode.encoder.cache_clear()
    listed = {"n": 0}

    def listed_but_no_card(argv, **_k):          # the build knows NVENC, the computer has no NVIDIA card
        listed["n"] += 1
        return subprocess.CompletedProcess(argv, 0 if "-encoders" in argv else 1, " V....D h264_nvenc NVIDIA\n", "No NVENC capable devices found")
    monkeypatch.setattr(encode.proc, "run", lambda a, *_x, **_k: listed_but_no_card(a))
    assert encode.encoder() == "cpu" and listed["n"] == 2
    encode.encoder.cache_clear()
    cpu = encode.video_args("cpu")
    assert cpu[:6] == ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21"] and cpu[cpu.index("-r") + 1] == "30"
    assert "h264_nvenc" in encode.video_args("nvenc") and encode.fps("nvenc") == 60


def test_a_part_command_blurs_ads_zooms_on_peaks_and_runs_one_filter_thread():
    p = {"index": 3, "pieces": [[100.0, 104.0], [106.0, 110.0]], "duration_s": 8.0, "bleeps": [[1.0, 1.3]], "blur": [[120, 40, 10, 20]],
         "shots": [{"kind": "punch", "start_s": 1.0, "end_s": 3.0}, {"kind": "focus", "start_s": 5.0, "end_s": 7.0}],
         "punch_rect": {"x": 1400, "y": 0, "width": 680, "height": 382}, "cam_rect": {"x": 1440, "y": 0, "width": 480, "height": 324}}
    argv = encode.part_command(p, {"video": "/v/piece.mp4", "offset": 98.5}, Path("/w/part003.mkv"), last=True, kind="cpu")
    graph = argv[argv.index("-filter_complex") + 1]
    assert argv[argv.index("-filter_complex_threads") + 1] == "1" and "-reinit_filter" in argv
    assert "between(t,1.500,5.500)+between(t,7.500,11.500)" in graph               # the pieces in the piece file's own time
    assert "crop=120:40:10:20:exact=1,boxblur" in graph and "crop=680:382:1400:0" in graph and "crop=480:324:1440:0" in graph
    assert "fade=t=out" in graph and "aeval=" in graph and "loudnorm=I=-14" in graph and "fps=30" in graph
    assert argv[-1] == str(Path("/w/part003.mkv")) and "libx264" in argv


def test_a_part_made_by_the_same_command_is_kept(tmp_path):
    out = tmp_path / "part000.mkv"
    argv = ["ffmpeg", "-i", str(tmp_path / "in.mp4"), str(out)]
    (tmp_path / "in.mp4").write_bytes(b"x")
    run, calls = fake_run()

    def making(a, **k):
        Path(a[-1]).write_bytes(b"video")
        return run(a, **k)
    assert encode.run(argv, runner=making) is True and encode.run(argv, runner=making) is False and len(calls) == 1
    (tmp_path / "in.mp4").write_bytes(b"longer")                                  # a new piece: made again
    assert encode.run(argv, runner=making) is True
    with pytest.raises(encode.EncodeError, match="boom"):
        encode.run(["ffmpeg", "-i", "x", str(tmp_path / "bad.mkv")], runner=fake_run(returncode=1)[0])


# ---- the step, its events and the switch ------------------------------------------------------------------------
def make_job(tmp_path):
    job = tmp_path / "job"
    job.mkdir()
    (job / "clips.json").write_text(json.dumps({"source": {"kind": "file", "path": str(tmp_path / "v.mp4"), "title": "Игры", "channel": "streamer"},
                                                "duration_s": 1200.0, "clips": []}), encoding="utf-8")
    (job / "transcript.json").write_text(json.dumps({"language": "ru", "segments": SEGMENTS}, ensure_ascii=False), encoding="utf-8")
    (job / "pass2.json").write_text(json.dumps({"episodes": EPISODES}, ensure_ascii=False), encoding="utf-8")
    return job


def layout_answer():
    return {"layout": "streamer_scene_split", "live_chat_side": "none", "webcam_region": CAM, "streamer_crop": CAM,
            "scene_crop": {"x": 0, "y": 0, "width": 0.75, "height": 1}, "screen_essential": True, "stable_across_frames": True,
            "needs_review": False, "reason": "x", "uncertainties": []}


def test_the_recap_step_writes_its_files_and_events_that_fit_the_contract(tmp_path, monkeypatch):
    job = make_job(tmp_path)
    monkeypatch.setattr(signals, "fetch", lambda info, p, folder: (str(tmp_path / "v.mp4"), 0.0))
    monkeypatch.setattr(signals.frames, "extract", lambda src, times, out: [tmp_path / "f.jpg"])
    monkeypatch.setattr(signals.frames, "size", lambda p: (1280, 720))
    monkeypatch.setattr("vodcut.render.frames.size", lambda p: (1280, 720))
    banner = {"regions": [{"id": "r1", "label": "casino", "confidence": 0.9, "needs_review": False, "observed_frames": [0],
                           "box": {"x": 10, "y": 10, "width": 100, "height": 40}}]}

    def caller(model, prompt, schema, images=None):
        if images is None:
            return Answer(GOOD, "", 1.0)
        return Answer(layout_answer() if "webcam" in json.dumps(schema) else banner, "", 1.0)
    asker = Asker(ModelSettings(provider="openai", model="m"), caller)
    ran = []

    def runner(argv, **_k):
        ran.append(argv)
        Path(argv[-1]).parent.mkdir(parents=True, exist_ok=True)
        Path(argv[-1]).write_bytes(b"out")
        return subprocess.CompletedProcess(argv, 0, "", "")
    monkeypatch.setattr(encode, "_ffmpeg", runner)
    monkeypatch.setattr(encode, "encoder", lambda: "cpu")
    with Journal(job, tool="vodcut", subscribers=[]) as journal:
        data = recap_step.make(job, asker, journal)
    assert data and data["file"] == "recap/video.mp4" and data["cover"] == "recap/cover.jpg" and data["encoder"] == "libx264"
    assert data["ads_blurred"] == 1 and [c["title"] for c in data["chapters"]] == ["Босс", "Кот"]
    for name in ("story.json", "signals.json", "recap.json", "video.mp4", "cover.jpg", "chapters.txt", "description.txt"):
        assert (job / "recap" / name).exists(), name
    assert (job / "recap" / "chapters.txt").read_text(encoding="utf-8").startswith("00:00 Босс\n")
    events = Journal(job, tool="vodcut", subscribers=[]).read()
    for e in events:
        assert contract.validate(e) == [] and contract.undeclared(e) == [], e
    kinds = [e["type"] for e in events]
    assert kinds[0] == "stage" and "recap_ready" in kinds and kinds[-1] == "done"
    assert {e["data"]["purpose"] for e in events if e["type"] == "model_call"} == {"recap", "layout", "banner"}
    steps = [e["data"].get("step") for e in events if e["type"] == "progress"]
    assert steps[0] == "story" and "video" in steps and "look" in steps and steps[-1] == "encode"
    # a rerun asks nothing and encodes nothing: every part is kept
    ran.clear()
    with Journal(job, tool="vodcut", subscribers=[]) as journal:
        again = recap_step.make(job, Asker(ModelSettings(provider="openai", model="m"), lambda *a, **k: pytest.fail("asked again")), journal)
    assert again["existing"] is True and all("-filter_complex_threads" not in a for a in ran)


def test_a_failed_recap_is_reported_and_the_request_still_ends_done(tmp_path):
    job = make_job(tmp_path)
    asker, _ = asker_of(ProviderError("down"))
    with Journal(job, tool="vodcut", subscribers=[]) as journal:
        assert recap_step.make(job, asker, journal) is None
    events = Journal(job, tool="vodcut", subscribers=[]).read()
    assert [e["type"] for e in events][-2:] == ["recap_failed", "done"] and events[-1]["data"]["failed"] is True
    assert "no usable story" in events[-2]["data"]["error"]
    for e in events:
        assert contract.validate(e) == [] and contract.undeclared(e) == [], e
    from smtv.jobs import status
    assert status(job, None) == "done"


def test_the_switch_decides_whether_a_run_makes_the_recap(tmp_path, monkeypatch):
    from vodcut import pipeline
    monkeypatch.setattr(tool_module, "check_model", lambda s: Check("model", OK, "ok"))
    monkeypatch.setattr(pipeline, "run", lambda *a, **k: {"clips": [{"id": "clip01"}]})
    monkeypatch.setattr(tool_module, "_render", lambda job, settings, only: 0)
    made = []
    monkeypatch.setattr(tool_module, "_recap", lambda job, settings: made.append(job) or 0)
    args = argparse.Namespace(out=str(tmp_path / "job"), source="x.mp4", language="ru", channel=None, workers=1, max_clips=None, no_render=False)
    settings = Settings.load()
    options.set_option(settings, "recap", False)
    settings.save()
    assert tool_module._cmd_run(args, {}, {}) == 0 and made == []
    options.set_option(settings, "recap", True)
    settings.save()
    assert tool_module._cmd_run(args, {}, {}) == 0 and made == [tmp_path / "job"]
    assert options.load(Settings())["recap"] is options.RECAP_DEFAULT


def test_the_cover_is_the_strongest_reaction_zoomed_on_the_webcam_with_ads_blurred():
    recap = {"parts": [{"index": 0, "role": "context", "start_s": 0, "end_s": 50, "peaks": [[10.0, 1.5]], "blur": [], "punch_rect": None},
                       {"index": 1, "role": "highlight", "start_s": 60, "end_s": 90, "peaks": [[70.0, 1.3], [80.0, 2.4]], "blur": [[100, 40, 8, 8]],
                        "punch_rect": {"x": 1400, "y": 0, "width": 680, "height": 382}}]}
    assert encode.cover_moment(recap) == (1, 80.0)                     # a part with a webcam wins over a louder one without
    argv = encode.cover_command(recap, {"1": {"video": "/v/p1.mp4", "offset": 58.5}}, Path("/r/cover.jpg"))
    graph = argv[argv.index("-filter_complex") + 1]
    assert argv[argv.index("-ss") + 1] == "21.500" and "crop=100:40:8:8:exact=1" in graph and "crop=680:382:1400:0,scale=1280:720" in graph
    assert encode.cover_moment({"parts": [{**recap["parts"][0], "peaks": []}]}) == (0, 25.0)   # a calm stream: the middle of a part


def test_pieces_are_named_by_their_span_and_kept_as_absolute_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("vodcut.render.fetch_piece", lambda info, a, b, dest: (Path("job/recap/pieces") / dest.name, a - 1.5))
    video, offset = signals.fetch({"kind": "link"}, {"index": 2, "start_s": 100.0, "end_s": 130.5}, Path("job/recap/pieces"))
    assert Path(video).is_absolute() and video.endswith("part002-100.00-130.50.mp4") and offset == 98.5


@pytest.mark.parametrize("folder", ["it's", "O'Brien's VODs", "Моя папка", "a b"])
def test_the_join_list_reads_back_paths_with_quotes(tmp_path, folder):
    """A9: «'» inside '…' must be written '\\'' or ffmpeg's concat list breaks on a folder like O'Brien."""
    where = tmp_path / folder
    where.mkdir()
    line = encode.concat_line(where / "part000.mkv")
    assert line.startswith("file '") and line.endswith("'\n")
    # the shell-like rule ffmpeg follows: undo it and the path is back
    import shlex
    assert shlex.split(line[len("file "):])[0] == (where / "part000.mkv").resolve().as_posix()


@pytest.mark.skipif(not __import__("shutil").which("ffmpeg"), reason="ffmpeg is not installed")
def test_a_recap_joins_in_a_folder_with_a_quote_for_real(tmp_path):
    where = tmp_path / "O'Brien"
    where.mkdir()
    parts = []
    for i in range(2):
        p = where / f"p{i}.mkv"
        done = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-f", "lavfi", "-i", "color=black:s=64x36:d=0.3",
                               "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "0.3", "-c:v", "libx264", "-c:a", "pcm_s16le", str(p)],
                              capture_output=True, text=True)
        assert done.returncode == 0, done.stderr
        parts.append(p)
    encode.concat(parts, where / "video.mp4")
    assert (where / "video.mp4").stat().st_size > 0


def test_a_hanging_ffmpeg_is_an_encode_error(monkeypatch, tmp_path):
    """B6: the recap's ffmpeg runs through proc.run; a time limit hit is a plain EncodeError."""
    def hangs(argv, timeout_s, **kw):
        raise encode.proc.TimedOut("ffmpeg (x.mkv) did not finish in 1 s and was stopped")
    monkeypatch.setattr(encode.proc, "run", hangs)
    with pytest.raises(encode.EncodeError, match="did not finish"):
        encode.run(["ffmpeg", "-i", "x", str(tmp_path / "x.mkv")])


def test_a_failed_look_at_the_webcam_and_ads_is_asked_again_and_said_once(tmp_path, monkeypatch):
    """B3: a 503 on the look was kept as «none: …» for good — the recap had no camera and no blur, silently."""
    job = tmp_path / "job"
    (job / "recap").mkdir(parents=True)
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x")
    monkeypatch.setattr(signals, "fetch", lambda info, p, folder: (str(video), 0.0))
    monkeypatch.setattr(signals.frames, "extract", lambda src, times, out: [tmp_path / "f.jpg"])
    monkeypatch.setattr(signals, "levels", lambda *a: [])
    asked, said = [], []
    answers = iter([(None, "none: busy: HTTP 503"), (CAM, "model")])
    monkeypatch.setattr(signals, "webcam", lambda asker, shots: (asked.append("cam"), next(answers))[1])
    monkeypatch.setattr(signals.clip_render, "find_ads", lambda asker, shots, a, b: (asked.append("ads"), ([], "model"))[1])
    story = {"parts": [{"index": 0, "start_s": 10.0, "end_s": 20.0, "peaks_s": []}]}
    first = signals.collect(job, story, {"kind": "file"}, object(), unlooked=lambda n, t: said.append((n, t)))
    assert first["0"]["cam_by"].startswith("none:") and said == [(1, 1)]
    second = signals.collect(job, story, {"kind": "file"}, object(), unlooked=lambda n, t: said.append((n, t)))
    # B12: an ad answer on one frame serves these parts but is not kept for the recording, so it is asked again too
    assert asked == ["ads", "cam", "ads", "cam"] and second["0"]["cam_by"] == "model" and said == [(1, 1)]
    signals.collect(job, story, {"kind": "file"}, object())
    assert len(asked) == 4                     # decided: not asked a third time
