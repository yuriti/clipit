import json
import wave

import pytest

from smtv_core.llm import Answer, QuotaExceeded
from smtv_core.settings import ModelSettings

from vodcut import pass1, pass2, pick, pipeline
from vodcut.model import Asker


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))      # never the settings of this computer
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)


def make_segments(n=60, step=10.0):
    """n segments every `step` seconds; segment 20-24 tell a story."""
    segs = []
    for i in range(n):
        t = i * step
        text = f"story part {i}" if 20 <= i <= 24 else f"callout {i}"
        ws = [{"word": " " + x, "start": t + k * 0.5, "end": t + k * 0.5 + 0.4, "probability": 1.0} for k, x in enumerate(text.split())]
        segs.append({"sid": f"s{i:05d}", "start": t, "end": ws[-1]["end"], "text": text, "words": ws})
    return segs


EP = {"episode_type": "story", "why_interesting": "a story", "one_liner": False, "has_setup": True, "has_payoff": True, "continues_before": False,
      "continues_after": False, "needs_context_before": False, "needs_context_after": False, "depends_on_video": "no", "asr_quality_concern": False,
      "standalone_clip_candidate": True}


def scan_answer(prompt):
    """A model that finds the story in every window whose text contains it."""
    windows = [line.split()[1] for line in prompt.splitlines() if line.startswith("WINDOW ")]
    out = []
    for wid in windows:
        has = "s00020 |" in prompt and wid == "w00"
        eps = [dict(EP, start_segment_id="s00020", end_segment_id="s00024", anchor_segment_id="s00024")] if has else []
        out.append({"window_id": wid, "episodes": eps, "window_has_nothing": not eps})
    return {"windows": out}


def rate_answer(prompt):
    ids = [line.split()[1] for line in prompt.splitlines() if line.startswith("### ")]
    return {"items": [{"episode_id": i, "format": "story", "verdict": "strong", "score": 85, "best_start": "0:03:20", "best_end": "0:04:01",
                       "depends_on_video": "no", "title": "The story", "reason": "clear payoff"} for i in ids]}


def fake_caller(model, prompt, schema, images=None):
    data = scan_answer(prompt) if "Windows to read:" in prompt else rate_answer(prompt)
    return Answer(data, json.dumps(data), 0.1, 100, 20)


def test_windows_and_validation():
    segs = make_segments(120, 10.0)
    ws = pass1.build_windows(segs)
    assert len(ws) >= 2 and ws[1]["start"] < ws[0]["end"]  # overlapping
    bad = {"windows": [{"window_id": "w00", "episodes": [dict(EP, start_segment_id="s99999", end_segment_id="s00024", anchor_segment_id="s00024")],
                        "window_has_nothing": False}]}
    errors, episodes = pass1.validate(bad, ws[:1])
    assert errors and not episodes


def test_scan_repairs_only_failed_windows():
    segs = make_segments()
    calls = []

    def caller(model, prompt, schema, images=None):
        calls.append(prompt)
        data = scan_answer(prompt)
        if len(calls) == 1:
            data["windows"][0]["window_has_nothing"] = True  # inconsistent on purpose
        return Answer(data, "", 0.1)

    result = pass1.run(segs, Asker(ModelSettings(provider="openai", model="m"), caller), workers=1)
    assert len(calls) == 2 and "rejected by validation" in calls[1]
    assert [e["start_segment_id"] for e in result["episodes"]] == ["s00020"]


def test_rating_snaps_to_words_and_prompt_is_english():
    segs = make_segments()
    scan = pass1.run(segs, Asker(ModelSettings(provider="openai", model="m"), fake_caller), workers=1)
    seen = []

    def caller(model, prompt, schema, images=None):
        seen.append(prompt)
        return fake_caller(model, prompt, schema)

    rated = pass2.run(segs, scan["episodes"], Asker(ModelSettings(provider="openai", model="m"), caller), channel="demo", workers=1)["episodes"]
    assert rated[0]["status"] == "ok" and rated[0]["trim"]["start_s"] == 200.0
    assert "Episodes:" in seen[0] and "Transcript:" in seen[0] and not any("Ѐ" <= c <= "ӿ" for c in seen[0])


def test_pick_limits_and_orders():
    rated = [{"status": "ok", "episode_id": f"e{i}", "verdict": "strong" if i % 2 else "maybe", "score": 50 + i, "format": "story", "title": f"t{i}",
              "reason": "", "depends_on_video": "no", "episode_start_s": i * 100, "episode_end_s": i * 100 + 30,
              "trim": {"start_s": i * 100, "end_s": i * 100 + 30}} for i in range(20)]
    clips = pick.pick(rated, duration_s=3600)
    assert len(clips) == 10 and all(c["verdict"] == "strong" for c in clips)        # every strong one, no cap per hour
    assert [c["start_s"] for c in clips] == sorted(c["start_s"] for c in clips) and clips[0]["id"] == "clip01"
    assert pick.limit(12 * 3600) == 30 and pick.limit(1800) == 30
    assert len(pick.pick(rated * 3, duration_s=600)) == 30                           # the request's cap stays
    assert pick.expected(5.7 * 3600) == 20 and pick.expected(1800) == 2


def write_wav(path, seconds=600):
    with wave.open(str(path), "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x00\x00" * 16000 * seconds)


class FakeRecognizer:
    class engine:  # noqa: N801
        name, grid_s = "fake", 18.0


def test_pipeline_end_to_end_and_resume(tmp_path, monkeypatch):
    job = tmp_path / "job"

    def fake_ingest(source, job_dir, **_):
        job_dir.mkdir(parents=True, exist_ok=True)
        write_wav(job_dir / "audio.wav")
        info = {"kind": "file", "title": "demo", "platform": "file", "channel": "demo", "duration_s": 600.0}
        (job_dir / "source.json").write_text(json.dumps(info), encoding="utf-8")
        return info

    monkeypatch.setattr(pipeline.ingest, "ingest", fake_ingest)
    monkeypatch.setattr(pipeline, "transcribe", lambda wav, rec, progress=None: make_segments())
    calls = []

    def caller(model, prompt, schema, images=None):
        calls.append(1)
        return fake_caller(model, prompt, schema)

    asker = Asker(ModelSettings(provider="openai", model="m"), caller)
    result = pipeline.run("demo.mp4", asker, job=job, language="ru", recognizer_for=lambda lang: FakeRecognizer())
    assert [c["title"] for c in result["clips"]] == ["The story"] and (job / "clips.json").exists()
    first_calls = len(calls)
    pipeline.run("demo.mp4", asker, job=job, language="ru", recognizer_for=lambda lang: FakeRecognizer())
    assert len(calls) == first_calls  # nothing asked again: transcript, scan and rating are reused


def test_quota_stops_the_run(tmp_path, monkeypatch):
    job = tmp_path / "job"
    monkeypatch.setattr(pipeline.ingest, "ingest", lambda s, j, **_: (j.mkdir(parents=True, exist_ok=True), write_wav(j / "audio.wav"), {"platform": "file"})[2])
    monkeypatch.setattr(pipeline, "transcribe", lambda wav, rec, progress=None: make_segments())

    def broke(*_a, **_k):
        raise QuotaExceeded("insufficient_quota")

    with pytest.raises(pipeline.RunError, match="quota"):
        pipeline.run("x.mp4", Asker(ModelSettings(provider="openai", model="m"), broke), job=job, language="ru",
                     recognizer_for=lambda lang: FakeRecognizer())
    assert not (job / "pass1.json").exists()  # a failed scan is not saved as if it were done


def run_demo(tmp_path, monkeypatch, journal=None, caller=fake_caller):
    job = tmp_path / "job"

    def fake_ingest(source, job_dir, **_):
        write_wav(job_dir / "audio.wav")
        return {"kind": "file", "title": "demo", "platform": "file", "channel": "demo", "duration_s": 600.0}

    def fake_transcribe(wav, rec, progress=None):
        for k in range(0, 601, 150):
            progress(k, 600)
        return make_segments()

    monkeypatch.setattr(pipeline.ingest, "ingest", fake_ingest)
    monkeypatch.setattr(pipeline, "transcribe", fake_transcribe)
    asker = Asker(ModelSettings(provider="openai", model="m"), caller)
    return job, pipeline.run("demo.mp4", asker, job=job, language="ru", journal=journal, recognizer_for=lambda lang: FakeRecognizer())


def assert_contract(job):
    """Every event the job wrote fits its schema and declares every field it carries."""
    from smtv_core import events
    from smtv_core.events import contract
    for e in events.read(job):
        assert contract.validate(e) == [], e
        assert contract.undeclared(e) == [], e
        assert e["tool"] == "vodcut" and e["job"] == job.name


def test_pipeline_writes_its_events_and_a_rerun_continues_the_numbers(tmp_path, monkeypatch):
    from smtv_core import events
    job, _ = run_demo(tmp_path, monkeypatch)
    got = events.read(job)
    assert_contract(job)
    assert [e["n"] for e in got] == list(range(1, len(got) + 1))
    kinds = [e["type"] for e in got]
    assert kinds[0] == "stage" and kinds[-1] == "done" and got[-1]["data"]["stage"] == "analysis"
    stages = [e["data"]["name"] for e in got if e["type"] == "stage"]
    assert stages == ["audio", "speech", "scan", "rating", "pick"]
    assert [e["data"]["percent"] for e in got if e["data"].get("stage") == "speech"] == [0, 20, 50, 70, 100]
    calls = [e["data"] for e in got if e["type"] == "model_call"]
    assert {c["purpose"] for c in calls} == {"scan", "rating"} and all(c["tokens_in"] == 100 and c["tokens_out"] == 20 and "seconds" in c for c in calls)
    [found] = [e["data"] for e in got if e["type"] == "episode_found"]
    [rated] = [e["data"] for e in got if e["type"] == "episode_rated"]
    assert found["episode_id"] == rated["episode_id"] and rated["verdict"] == "strong" and rated["title"] == "The story"
    assert kinds.index("episode_found") < kinds.index("episode_rated") < len(kinds) - 1
    assert got[-1]["data"]["clips"][0]["title"] == "The story"

    run_demo(tmp_path, monkeypatch)                                    # everything is reused: only the frame of the run is written again
    again = events.read(job, after=len(got))
    assert again[0]["n"] == len(got) + 1
    assert [e["type"] for e in again] == ["stage", "source_ready", "progress", "stage", "done"]   # the source is told on every run
    assert got[-1]["data"]["file"] == "clips.json" and "trim" not in got[-1]["data"]["clips"][0]   # short data and a job file, not the whole list
    assert_contract(job)


def test_command_line_prints_the_same_lines_as_before(tmp_path, monkeypatch, capsys):
    from smtv_core.events import Journal
    from vodcut import console
    job, _ = run_demo(tmp_path, monkeypatch, journal=Journal(tmp_path / "job", tool="vodcut", echo=console.printer(tmp_path / "job")))
    assert capsys.readouterr().out.splitlines() == [
        f"1/5 Getting the audio → {job}",
        "2/5 Speech to text: gigaam (Russian), 0.2 h of audio",
        "    0%", "    20%", "    50%", "    70%", "    100%",
        "3/5 Scanning the transcript for episodes (60 segments)",
        "    1/1 windows",
        "4/5 Rating 1 episodes",
        "    1/1 batches",
        "5/5 Picking the clips",
        "",
        "1 clips from 0.2 h (1 episodes found, 1 rated):",
        "  clip01  0:03:20–0:04:00   40.9 s   85  The story",
        "",
        "Time: audio 0 s, speech 0 s, scan 0 s, rating 0 s. Tokens: 200 in, 40 out.",
    ]


def test_an_error_is_written_before_the_run_stops(tmp_path, monkeypatch, capsys):
    from smtv_core import events
    from smtv_core.events import Journal
    from vodcut import console

    def broke(*_a, **_k):
        raise QuotaExceeded("insufficient_quota")

    with pytest.raises(pipeline.RunError):
        run_demo(tmp_path, monkeypatch, journal=Journal(tmp_path / "job", tool="vodcut", echo=console.printer(tmp_path / "job")), caller=broke)
    last = events.read(tmp_path / "job")[-1]
    assert last["type"] == "error" and "quota" in last["data"]["message"]
    assert capsys.readouterr().out.splitlines()[-1].startswith("Stopped: the model refused: out of quota")
    assert not any(e["type"] == "model_call" and e["data"].get("error") == "stopped" for e in events.read(tmp_path / "job"))
    assert_contract(tmp_path / "job")


def test_what_the_request_is_about_is_an_event_as_soon_as_the_audio_is_in(tmp_path, monkeypatch):
    from smtv_core import events
    job, _ = run_demo(tmp_path, monkeypatch)
    got = events.read(job / events.FILE_NAME)
    kinds = [e["type"] for e in got]
    assert kinds[:2] == ["stage", "source_ready"]                     # right after «getting the audio» began and ended
    src = got[1]["data"]
    assert src == {"kind": "file", "title": "demo", "channel": "demo", "platform": "file", "duration_s": 600.0}   # empty fields are left out
    assert "avatar" not in src                                        # a file has no channel picture to look for


def test_a_channel_picture_goes_into_the_event_when_there_is_one(tmp_path, monkeypatch):
    from vodcut import avatar, pipeline
    (tmp_path / "job").mkdir()
    calls = []
    monkeypatch.setattr(avatar, "fetch", lambda folder, cache: calls.append(folder) or "avatar.png")
    info = {"kind": "link", "url": "https://www.twitch.tv/videos/1", "title": "t", "channel": "someone", "platform": "twitchvod", "channel_id": "someone"}
    facts = pipeline.source_facts(info, tmp_path / "job", 3600)
    assert facts["avatar"] == "avatar.png" and facts["source"] == "https://www.twitch.tv/videos/1" and calls == [tmp_path / "job"]
    (tmp_path / "job" / "avatar.png").write_bytes(b"x")
    assert pipeline.source_facts(info, tmp_path / "job", 3600)["avatar"] == "avatar.png" and len(calls) == 1   # kept: not fetched again


def test_a_pause_stops_between_two_steps_and_a_rerun_goes_on_from_there(tmp_path, monkeypatch):
    from smtv_core import events, pause
    from smtv_core.pause import Paused
    job = tmp_path / "job"
    job.mkdir()
    pause.ask(job)                                                  # asked while the audio was being fetched
    with pytest.raises(Paused):
        run_demo(tmp_path, monkeypatch)
    got = events.read(job / events.FILE_NAME)
    assert got[-1]["type"] == "cancelled" and got[-1]["data"] == {"by": "user", "stage": "speech", "graceful": True}
    assert not pause.requested(job)                                 # the request is used up
    assert not (job / "transcript.json").exists()                  # stopped before speech: nothing half done
    run_demo(tmp_path, monkeypatch)                                 # «Continue»: goes on and finishes
    assert events.read(job / events.FILE_NAME)[-1]["type"] == "done"


def _english_job(tmp_path, monkeypatch, hint=None):
    job = tmp_path / "job"

    def fake_ingest(source, job_dir, **_):
        job_dir.mkdir(parents=True, exist_ok=True)
        write_wav(job_dir / "audio.wav")
        info = {"kind": "file", "title": "demo", "platform": "file", "channel": "demo", "duration_s": 600.0, "language": hint}
        (job_dir / "source.json").write_text(json.dumps(info), encoding="utf-8")
        return info

    monkeypatch.setattr(pipeline.ingest, "ingest", fake_ingest)
    monkeypatch.setattr(pipeline, "transcribe", lambda wav, rec, progress=None: make_segments())
    return job


def test_without_parakeet_a_stream_in_another_language_downloads_it_instead_of_going_russian(tmp_path, monkeypatch):
    """Stage 15: an English file went to GigaAM as Russian because Parakeet was not here."""
    from smtv_core import events
    from test_analysis import assert_contract
    job = _english_job(tmp_path, monkeypatch)
    here = {"gigaam"}
    loaded, used = [], []

    class Rec:
        def __init__(self, engine):
            self.engine = engine

    monkeypatch.setattr(pipeline, "installed", lambda engine: engine.name in here)
    monkeypatch.setattr(pipeline.Recognizer, "load", lambda self: (loaded.append(self.engine.name), self)[1])
    monkeypatch.setattr(pipeline, "detect", lambda wav, rec, fallback="latin": (used.append((rec.engine.name, fallback)), "latin")[1])

    def download(engine, tick):
        tick(1200, engine.size_mb)
        tick(engine.size_mb, engine.size_mb)
        here.add(engine.name)
        return Rec(engine)

    monkeypatch.setattr(pipeline, "load_watched", download)
    seen_engine = []
    monkeypatch.setattr(pipeline, "transcribe", lambda wav, rec, progress=None: (seen_engine.append(rec.engine.name), make_segments())[1])
    asker = Asker(ModelSettings(provider="openai", model="m"), lambda m, p, s, images=None: fake_caller(m, p, s))
    pipeline.run("demo.mp4", asker, job=job)
    assert used == [("gigaam", "ru")] and seen_engine == ["parakeet"]          # GigaAM listened; Parakeet transcribed
    got = events.read(job)
    model = [e["data"] for e in got if e["type"] in ("stage", "progress") and (e["data"].get("name") or e["data"].get("stage")) == "model"]
    assert model[0] == {"name": "model", "step": 2, "steps": 5, "engine": "parakeet", "language": "latin"}
    assert [m["percent"] for m in model[1:]] == [49, 100]
    assert json.loads((job / "transcript.json").read_text(encoding="utf-8"))["engine"] == "parakeet"
    assert_contract(job)


def test_a_failed_model_download_stops_with_the_reason(tmp_path, monkeypatch):
    from smtv_core import events
    job = _english_job(tmp_path, monkeypatch, hint="en")
    monkeypatch.setattr(pipeline, "installed", lambda engine: False)

    def offline(engine, tick):
        raise OSError("Connection refused by huggingface.co")

    monkeypatch.setattr(pipeline, "load_watched", offline)
    asker = Asker(ModelSettings(provider="openai", model="m"), lambda m, p, s, images=None: fake_caller(m, p, s))
    with pytest.raises(pipeline.RunError, match="could not download the parakeet speech model .* Connection refused"):
        pipeline.run("demo.mp4", asker, job=job)
    assert any(e["type"] == "error" and "could not download" in e["data"]["message"] for e in events.read(job))
    assert not (job / "transcript.json").exists()


# --- stage 20: the speech model chosen in «Settings → Speech» -------------------------------------------------------

def _groq_settings():
    from smtv_core import presets
    from smtv_core.settings import OPENAI, Provider, Settings, set_secret
    s = Settings(providers=[Provider(id="groq", kind=OPENAI, preset="groq", base_url=presets.BY_ID["groq"].base_url)])
    s.tools["smtv"] = {"speech": {"ru": "groq"}}
    s.save()
    set_secret("provider.groq", "gsk_test_0123456789abcdefKEY")


def test_a_language_set_to_the_cloud_is_heard_there_with_the_persons_key(tmp_path, monkeypatch):
    from smtv_core.asr import cloud
    _groq_settings()
    job = tmp_path / "job"
    monkeypatch.setattr(pipeline.ingest, "ingest", lambda s, j, **_: (j.mkdir(parents=True, exist_ok=True), write_wav(j / "audio.wav", 60), {"platform": "file"})[2])
    heard = []

    def transcribe_file(self, wav, start, end, progress):
        heard.append((self.service, self.key, self.language))
        return [w for seg in make_segments(5, 10.0) for w in seg["words"]]
    monkeypatch.setattr(cloud.CloudRecognizer, "transcribe_file", transcribe_file)
    result = pipeline.run("x.mp4", Asker(ModelSettings(provider="openai", model="m"), fake_caller), job=job, language="ru")
    assert heard == [("groq", "gsk_test_0123456789abcdefKEY", "ru")]
    assert result["speech_engine"] == "groq" and json.loads((job / "transcript.json").read_text(encoding="utf-8"))["engine"] == "groq"
    assert "gsk_test" not in (job / "events.jsonl").read_text(encoding="utf-8")


def test_no_speech_is_not_kept_so_a_rerun_listens_again(tmp_path, monkeypatch):
    from smtv_core.asr import cloud
    _groq_settings()
    job = tmp_path / "job"
    monkeypatch.setattr(pipeline.ingest, "ingest", lambda s, j, **_: (j.mkdir(parents=True, exist_ok=True), write_wav(j / "audio.wav", 60), {"platform": "file"})[2])
    monkeypatch.setattr(cloud.CloudRecognizer, "transcribe_file", lambda self, *a: [])
    asker = Asker(ModelSettings(provider="openai", model="m"), fake_caller)
    with pytest.raises(pipeline.RunError, match="no speech"):
        pipeline.run("x.mp4", asker, job=job, language="ru")
    assert not (job / "transcript.json").exists()


def test_a_cloud_model_without_a_key_stops_with_where_to_add_it(tmp_path, monkeypatch):
    from smtv_core.settings import Settings
    s = Settings()
    s.tools["smtv"] = {"speech": {"ru": "openai"}}
    s.save()
    job = tmp_path / "job"
    monkeypatch.setattr(pipeline.ingest, "ingest", lambda s, j, **_: (j.mkdir(parents=True, exist_ok=True), write_wav(j / "audio.wav", 60), {"platform": "file"})[2])
    with pytest.raises(Exception, match="OpenAI provider"):
        pipeline.run("x.mp4", Asker(ModelSettings(provider="openai", model="m"), fake_caller), job=job, language="ru")
    assert "OpenAI provider" in (job / "events.jsonl").read_text(encoding="utf-8")


def _ja_whisper(monkeypatch, tmp_path):
    from smtv_core.settings import Settings
    s = Settings()
    s.tools["smtv"] = {"speech": {"ja": "whisper"}}
    s.save()
    monkeypatch.setattr(pipeline.ingest, "ingest", lambda s, j, **_: (j.mkdir(parents=True, exist_ok=True), write_wav(j / "audio.wav", 60), {"platform": "file"})[2])


def test_whisper_without_its_package_is_a_run_error(tmp_path, monkeypatch):
    from smtv_core.asr import catalog
    _ja_whisper(monkeypatch, tmp_path)
    monkeypatch.setattr(catalog, "package_ready", lambda m: False)
    with pytest.raises(pipeline.RunError, match="faster-whisper"):
        pipeline.run("x.mp4", Asker(ModelSettings(provider="openai", model="m"), fake_caller), job=tmp_path / "job", language="ja")
    assert not (tmp_path / "job" / "transcript.json").exists()


def test_whisper_is_downloaded_with_progress_and_a_failed_download_names_the_model(tmp_path, monkeypatch):
    from smtv_core.asr import catalog, whisper
    _ja_whisper(monkeypatch, tmp_path)
    monkeypatch.setattr(catalog, "package_ready", lambda m: True)

    def no_room(models_dir=None, progress=None, every_s=2.0):
        progress(300, 1550)
        raise OSError("no room on the disk")
    monkeypatch.setattr(whisper, "download", no_room)
    job = tmp_path / "job"
    with pytest.raises(pipeline.RunError, match=r"Whisper large-v3-turbo.*1\.5 GB.*no room"):
        pipeline.run("x.mp4", Asker(ModelSettings(provider="openai", model="m"), fake_caller), job=job, language="ja")
    events = [json.loads(x) for x in (job / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    assert any(e["type"] == "stage" and e["data"].get("name") == "model" and e["data"].get("engine") == "whisper" for e in events)
    assert any(e["type"] == "progress" and e["data"].get("stage") == "model" for e in events)


# --- В3 (ревью В2): a model that fails is an error, what it answered is kept, the rest is asked again ---------------

def _job_with(tmp_path, monkeypatch):
    job = tmp_path / "job"
    monkeypatch.setattr(pipeline.ingest, "ingest", lambda s, j, **_: (j.mkdir(parents=True, exist_ok=True), write_wav(j / "audio.wav"),
                                                                       {"platform": "file", "duration_s": 600.0})[2])
    monkeypatch.setattr(pipeline, "transcribe", lambda wav, rec, progress=None: make_segments(240, 10.0))   # 40 min: several windows
    return job


def _run(job, caller, journal=None):
    return pipeline.run("x.mp4", Asker(ModelSettings(provider="openai", model="m"), caller), job=job, language="ru", workers=1,
                        journal=journal, recognizer_for=lambda lang: FakeRecognizer())


@pytest.mark.parametrize("answer", ["error", "empty"])
def test_a_model_that_never_answers_usefully_fails_the_run_and_keeps_no_scan(tmp_path, monkeypatch, answer):
    from smtv_core import events
    from smtv_core.llm import ProviderError
    job = _job_with(tmp_path, monkeypatch)

    def caller(model, prompt, schema, images=None):
        if answer == "error":
            raise ProviderError("HTTP 401: invalid api key")
        return Answer({}, "{}", 0.1)

    with pytest.raises(pipeline.RunError, match="Модель не ответила на \\d+ из \\d+ частей записи") as err:
        _run(job, caller)
    if answer == "error":
        assert "HTTP 401" in str(err.value)
    assert not (job / "pass1.json").exists() and not (job / "clips.json").exists()
    assert [e for e in events.read(job) if e["type"] == "error"]


def test_a_rating_model_that_never_answers_fails_the_run_and_keeps_no_rating(tmp_path, monkeypatch):
    from smtv_core.llm import ProviderError
    job = _job_with(tmp_path, monkeypatch)

    def caller(model, prompt, schema, images=None):
        if "Windows to read:" in prompt:
            return fake_caller(model, prompt, schema)
        raise ProviderError("HTTP 500")

    with pytest.raises(pipeline.RunError, match="найденных моментов.*HTTP 500"):
        _run(job, caller)
    assert (job / "pass1.json").exists() and not (job / "pass2.json").exists()


def test_a_rerun_after_a_failed_scan_asks_only_the_missing_windows(tmp_path, monkeypatch):
    from smtv_core import events
    from smtv_core.llm import ProviderError
    job = _job_with(tmp_path, monkeypatch)
    windows = len(pass1.build_windows(pipeline.filtered_segments(make_segments(240, 10.0))))
    assert windows >= 3
    asked = []

    def flaky(model, prompt, schema, images=None):
        if "Windows to read:" in prompt:
            ids = [line.split()[1] for line in prompt.splitlines() if line.startswith("WINDOW ")]
            asked.append(ids)
            if "w01" in ids:
                raise ProviderError("HTTP 503")
        return fake_caller(model, prompt, schema)

    monkeypatch.setattr(pass1, "DEFAULTS", {**pass1.DEFAULTS, "per_request": 1})
    result = _run(job, flaky)                          # one window of several failed: the run goes on with the rest
    assert result["clips"] and not (job / "pass1.json").exists() and not (job / "pass2.json").exists()
    missing = [e["data"] for e in events.read(job) if e["type"] == "progress" and e["data"]["stage"] == "missing"]
    assert missing == [{"stage": "missing", "step": "scan", "done": 1, "total": windows}]
    asked.clear()
    _run(job, lambda m, p, s, i=None: fake_caller(m, p, s))    # the model works again: only w01 is asked
    rerun = []

    def counting(model, prompt, schema, images=None):
        rerun.append(prompt)
        return fake_caller(model, prompt, schema)
    assert (job / "pass1.json").exists() and (job / "pass2.json").exists()
    _run(job, counting)
    assert rerun == []                                 # now complete: nothing asked a third time


def test_only_the_missing_window_is_asked_again(tmp_path, monkeypatch):
    from smtv_core.llm import ProviderError
    job = _job_with(tmp_path, monkeypatch)
    monkeypatch.setattr(pass1, "DEFAULTS", {**pass1.DEFAULTS, "per_request": 1})
    asked = []

    def caller(fail):
        def call(model, prompt, schema, images=None):
            if "Windows to read:" in prompt:
                ids = [line.split()[1] for line in prompt.splitlines() if line.startswith("WINDOW ")]
                asked.append(ids)
                if fail and "w01" in ids:
                    raise ProviderError("HTTP 503")
            return fake_caller(model, prompt, schema)
        return call

    _run(job, caller(True))
    asked.clear()
    _run(job, caller(False))
    assert asked == [["w01"]]


def test_a_rerun_after_a_failed_rating_asks_only_the_missing_episodes(tmp_path, monkeypatch):
    from smtv_core.llm import ProviderError
    job = _job_with(tmp_path, monkeypatch)
    rated = []

    def broke(model, prompt, schema, images=None):
        if "Windows to read:" in prompt:
            return fake_caller(model, prompt, schema)
        raise ProviderError("HTTP 500")

    with pytest.raises(pipeline.RunError):
        _run(job, broke)

    def works(model, prompt, schema, images=None):
        if "Episodes:" in prompt:
            rated.append(prompt)
        return fake_caller(model, prompt, schema)

    _run(job, works)
    assert len(rated) == 1 and (job / "pass2.items.json").exists()
    rated.clear()
    (job / "pass2.json").unlink()                     # even without the final file the kept verdicts are enough
    _run(job, works)
    assert rated == []


def test_an_episode_without_its_type_is_a_window_error_not_a_crash():
    """A12: a provider without a strict schema drops a field or sends a string: the window is invalid, nothing raises."""
    segs = make_segments(120, 10.0)
    windows = pass1.build_windows(segs)[:2]
    good = dict(EP, start_segment_id=windows[0]["segments"][1]["sid"], end_segment_id=windows[0]["segments"][3]["sid"],
                anchor_segment_id=windows[0]["segments"][2]["sid"])
    broken = {k: v for k, v in good.items() if k != "episode_type"}
    answer = {"windows": [{"window_id": windows[0]["id"], "episodes": [broken], "window_has_nothing": False},
                          {"window_id": windows[1]["id"], "episodes": ["a string"], "window_has_nothing": False}]}
    results = pass1.validate_windows(answer, windows)
    assert all(results[w["id"]][0] and not results[w["id"]][1] for w in windows)
    assert pass1.validate_windows({"windows": [{"window_id": windows[0]["id"], "episodes": "nothing", "window_has_nothing": True}]},
                                  windows[:1])[windows[0]["id"]][0]


def test_a_scan_with_a_broken_episode_repairs_it_and_never_crashes_in_the_merge():
    segs = make_segments()
    calls = []

    def caller(model, prompt, schema, images=None):
        calls.append(prompt)
        data = scan_answer(prompt)
        if len(calls) == 1:
            for w in data["windows"]:
                for e in w["episodes"]:
                    del e["episode_type"]
        return Answer(data, "", 0.1)

    result = pass1.run(segs, Asker(ModelSettings(provider="openai", model="m"), caller), workers=1)
    assert len(calls) == 2 and "episode_schema" in calls[1] and result["episodes"][0]["episode_type"] == "story"


def test_a_long_why_interesting_is_cut_not_refused():
    segs = make_segments()
    w = pass1.build_windows(segs)[0]
    e = dict(EP, why_interesting="x" * 400, start_segment_id="s00020", end_segment_id="s00024", anchor_segment_id="s00024")
    errors, episodes = pass1.validate({"windows": [{"window_id": w["id"], "episodes": [e], "window_has_nothing": False}]}, [w])
    assert not errors and len(episodes[0]["why_interesting"]) == 240


@pytest.mark.parametrize("name", ["стрим_23_11.mp4", "_x.mp4", "Мой стрим.mp4", "Стрим вчера.mkv", "it's [x], a;b.mp4", ".mp4"])
def test_every_job_folder_passes_the_servers_check(tmp_path, name):
    import re
    job_id = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,120}$")      # smtv.serve.JOB_ID
    folder = pipeline.job_dir(str(tmp_path / name), tmp_path / "jobs")
    assert job_id.match(folder.name), folder.name


def test_two_recordings_with_russian_names_get_two_folders_and_one_link_one_folder(tmp_path):
    a = pipeline.job_dir(str(tmp_path / "x" / "Стрим вчера.mp4"), tmp_path)
    b = pipeline.job_dir(str(tmp_path / "y" / "Нарезка.mkv"), tmp_path)
    c = pipeline.job_dir(str(tmp_path / "z" / "Стрим вчера.mp4"), tmp_path)
    assert len({a, b, c}) == 3 and a.name.startswith("Strim-vchera_")
    assert pipeline.job_dir("https://www.twitch.tv/videos/123", tmp_path) == pipeline.job_dir("https://www.twitch.tv/videos/123?t=1h", tmp_path)


def test_a_model_error_on_a_rating_batch_is_not_asked_again_by_itself():
    """B2 / decision 3: after an error (a timeout may have been paid for) the batch waits for «Продолжить»."""
    segs = make_segments()
    scan = pass1.run(segs, Asker(ModelSettings(provider="openai", model="m"), fake_caller), workers=1)
    calls = []

    def caller(model, prompt, schema, images=None):
        calls.append(1)
        from smtv_core.llm import Overloaded
        raise Overloaded("the service did not answer in 300 s; it may still have done the work")

    out = pass2.run(segs, scan["episodes"], Asker(ModelSettings(provider="openai", model="m"), caller), workers=1)
    batches = -(-len(scan["episodes"]) // 8)
    assert len(calls) == batches and out["missing"]
