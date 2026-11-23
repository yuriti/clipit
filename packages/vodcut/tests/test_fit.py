"""Fit moved from production (stage 11): the contract, the packet, trim_required, recovery of a crooked answer, the step."""
import json
import math
import wave

import numpy as np
import pytest

from smtv_core import prompts
from smtv_core.events import contract as event_contract
from smtv_core.llm import Answer
from smtv_core.settings import ModelSettings

from vodcut import fit
from vodcut.fit import acoustics, contract, packet, recovery, trim_required
from vodcut.fit.compact import expand
from vodcut.model import Asker
from test_analysis import FakeRecognizer, assert_contract, fake_caller, make_segments, run_demo, write_wav


# ---------- the contract ---------------------------------------------------------------------------------------------

def test_the_answer_schema_is_the_one_in_the_prompts_repository():
    assert contract.MODEL_SCHEMA == prompts.schema("fit")


def test_trim_required_edits_apply_once_to_the_bundled_policy():
    text = prompts.text("fit/prompt-policy.txt")
    edited = trim_required.policy(text)
    assert edited != text and "trim=null and fit_score from 0 to 40" not in edited and "A trim is always required." in edited
    with pytest.raises(RuntimeError, match="anchor"):
        trim_required.policy(text.replace("Return only JSON matching the schema: id, title, fit_score, trim, clip_format.", "changed"))
    assert "A trim is required" in fit.REPAIR and "trim=null" not in fit.REPAIR


def test_trim_required_schema_needs_a_trim_and_an_integer_score():
    schema = trim_required.schema(contract.TRANSPORT_SCHEMA)
    item = schema["properties"]["clips"]["items"]
    assert list(item["properties"]) == ["id", "trim", "fit_score", "clip_format", "title"] == item["required"]
    assert item["properties"]["fit_score"]["type"] == "integer" and "anyOf" not in item["properties"]["trim"]
    assert "allOf" not in json.dumps(schema)


WORDS = [["1-word-1", 1000, 1400, "Короче,", 0.9], ["1-word-2", 1500, 1900, "вчера", 0.9],
         ["2-word-1", 36000, 36400, "соседу", 0.9], ["2-word-2", 40000, 40500, "пицца.", 0.9]]


def trim(a, b, first="1-word-1", last="2-word-2", rel="event_overlaps_focus"):
    return {"id": "c", "trim": {"start_ms": a, "end_ms": b, "event_start_word_id": first, "event_end_word_id": last, "focus_relation": rel},
            "fit_score": 60, "clip_format": "story", "title": "Пицца"}


@pytest.mark.parametrize("item,errors", [
    (trim(1000, 41000), []),
    (trim(1000, 12000), ["invalid_trim_duration_or_bounds", "event_outside_trim"]),
    (trim(1200, 41000), ["trim_cuts_word", "event_outside_trim"]),
    (trim(1000, 41000, first="nope"), ["unknown_event_word_id"]),
    (trim(1000, 41000, first="2-word-2", last="1-word-1"), ["reversed_event_word_ids"]),
    (trim(1000, 41000, last="1-word-2"), ["event_does_not_overlap_focus"]),
    (trim(1000, 41000, rel="event_precedes_focus_possible_delay"), ["event_not_before_focus"]),
])
def test_evidence_errors_are_production_s(item, errors):
    assert contract.evidence_errors(item, WORDS, WORDS) == errors


def test_a_short_window_bounds_the_trim():
    assert contract.evidence_errors(trim(1000, 41000), WORDS, WORDS, window_ms=40000) == ["invalid_trim_duration_or_bounds"]


# ---------- recovery of a crooked answer -----------------------------------------------------------------------------

def test_a_trim_leaving_out_an_edge_word_by_under_a_second_is_widened():
    item = trim(1450, 40000)                              # leaves out «Короче,» and «пицца.», each by under a second
    fixed, errors = recovery.check_item(json.loads(json.dumps(item)), WORDS, WORDS)
    assert errors == [] and fixed["trim"]["start_ms"] == 1000 and fixed["trim"]["end_ms"] >= 40500


def test_far_outside_is_not_widened_but_reported():
    _, errors = recovery.check_item(trim(1600, 41000, first="1-word-1"), WORDS, WORDS)
    assert "event_outside_trim" in errors


def test_focus_relation_is_set_from_the_word_times():
    fixed, errors = recovery.check_item(trim(1000, 41000, rel="event_precedes_focus_possible_delay"), WORDS, WORDS)
    assert errors == [] and fixed["trim"]["focus_relation"] == "event_overlaps_focus"


def test_the_end_gets_air_after_the_last_word_but_not_into_the_next_speech():
    words = WORDS + [["3-word-1", 41300, 41700, "Ладно,", 0.9]]
    fixed, errors = recovery.check_item(trim(1000, 40500), words, words)
    assert errors == [] and fixed["trim"]["end_ms"] == 41300 - recovery.NEXT_SPEECH_GUARD_MS
    fixed, _ = recovery.check_item(trim(1000, 40500), WORDS, WORDS)
    assert fixed["trim"]["end_ms"] == 40500 + recovery.TRIM_TAIL_MS


def test_a_null_trim_or_a_missing_item_is_an_error_with_trim_required():
    item = dict(trim(1000, 41000), trim=None, fit_score=20)
    assert recovery.check_item(item, WORDS, WORDS)[1][0].startswith("response_schema_invalid:trim")
    assert recovery.check_item(None, WORDS, WORDS)[1] == ["missing_from_response"]


def test_answers_are_found_in_text_and_doubled_ids_are_dropped():
    raw = 'Here you go: {"clips": [{"id": "a"}, {"id": "b"}, {"id": "b"}]} done'
    answer = recovery.parse_answer(raw)
    assert recovery.response_items(answer, ["a", "b", "c"]) == {"a": {"id": "a"}, "b": None, "c": None}
    assert recovery.parse_answer("no json") is None


def test_the_repair_hint_gives_word_safe_ways_to_reach_fifteen_seconds():
    words = [["w1", 20000, 20500, "раз", 0.9], ["w2", 29000, 29400, "два", 0.9], ["w3", 34800, 35300, "три", 0.9]]
    hint = recovery.repair_hint(trim(25000, 30000, "w2", "w2"), ["invalid_trim_duration_or_bounds"], words, words)
    assert "10000 ms short" in hint and "start_ms=15000" in hint and "end_ms=40000" in hint and "«три»" in hint


# ---------- acoustics on the processor ------------------------------------------------------------------------------

def production_pitch(audio, rate, rms_gate):
    """Production's estimate_pitch (compact25_flow7_audio.py) with np.correlate, for comparison."""
    frame_size, hop = round(rate * 0.05), round(rate * 0.02)
    min_lag, max_lag = max(1, rate // 400), rate // 65
    pitches = []
    for start in range(0, max(1, len(audio) - frame_size + 1), hop):
        frame = audio[start:start + frame_size].astype(np.float64)
        if len(frame) < frame_size or float(np.sqrt(np.mean(frame * frame))) < rms_gate:
            continue
        frame -= np.mean(frame)
        if float(np.dot(frame, frame)) <= 1e-9:
            continue
        correlation = np.correlate(frame, frame, mode="full")[len(frame) - 1:]
        search = correlation[min_lag:min(max_lag + 1, len(correlation))]
        offset = int(np.argmax(search))
        if float(search[offset] / max(correlation[0], 1e-9)) < 0.25:
            continue
        pitches.append(rate / (min_lag + offset))
    values = np.asarray(pitches)
    return {"pitch_hz_median": float(np.median(values)) if values.size else 0.0, "pitch_hz_std": float(np.std(values)) if values.size else 0.0}


def voice(seconds=4.0, rate=16000):
    t = np.arange(int(seconds * rate)) / rate
    f0 = 180 + 40 * np.sin(2 * math.pi * 0.5 * t)
    phase = 2 * math.pi * np.cumsum(f0) / rate
    sig = 0.3 * np.sin(phase) + 0.1 * np.sin(2 * phase) + 0.01 * np.random.default_rng(1).standard_normal(t.size)
    sig[: rate // 2] = 0.0005 * np.random.default_rng(2).standard_normal(rate // 2)   # half a second of near silence
    return sig


def test_pitch_through_the_fft_equals_production_s_correlation():
    audio = voice()
    ours = acoustics._pitch(audio, 16000, 0.01)
    theirs = production_pitch(audio, 16000, 0.01)
    assert ours == pytest.approx(theirs, rel=1e-9) and 150 < ours["pitch_hz_median"] < 230


def test_delivery_has_the_packet_s_keys_and_sees_the_silence():
    d = acoustics.delivery(voice())
    assert set(d) == {"silence_ratio", "rms_dynamic_range_db", "energy_begin_db", "energy_middle_db", "energy_final_db",
                      "energy_peak_position", "pitch_hz_median", "pitch_hz_std"}
    assert 0.08 < d["silence_ratio"] < 0.2 and d["energy_begin_db"] < d["energy_final_db"]


def test_pauses_are_gaps_between_words():
    assert acoustics.pauses([(100, 400), (500, 900), (2000, 2500)], 3000) == [[900, 2000], [2500, 3000]]


# ---------- the packet -----------------------------------------------------------------------------------------------

def write_voice_wav(path, seconds):
    with wave.open(str(path), "w") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(16000)
        sig = np.tile(voice(), int(seconds // 4) + 1)[: int(seconds * 16000)]
        w.writeframes((sig * 32767).astype("<i2").tobytes())


def test_the_packet_is_a_lossless_window_around_the_clip(tmp_path):
    write_voice_wav(tmp_path / "a.wav", 600)
    segs = make_segments()
    segs[22]["words"][0]["end"] = segs[22]["words"][0]["start"] + 9.0        # GigaAM stretched a word over the silence
    built = packet.build("clip01", segs, tmp_path / "a.wav", 200.0, 240.9, 600.0)
    assert built["window_ms"] == 70000 and built["window_start_s"] == pytest.approx(185.45)
    p = built["packet"]
    assert p["context_window_ms"] == [0, 70000] and p["activity_focus_ms"] == [14550, 55450]
    ids = [w[0] for w in built["words"]]
    assert len(ids) == len(set(ids)) and all(0 <= w[1] < w[2] <= 70000 for w in built["words"])
    stretched = next(w for w in built["words"] if w[3] == "story" and w[1] == 220000 - 185450)
    assert stretched[2] - stretched[1] == 1000                                 # capped: max(1000, 200 × 5 letters)
    ev = p["acoustic_evidence"]
    assert ev["sound_events"] == [] and "no speaker diarization" in ev["note"] and ev["fully_contained_pauses_ms"]
    assert set(ev["focus_35_55_seconds"]["delivery"]) >= {"silence_ratio", "pitch_hz_median"}
    blocks = p["speaker_context"]["speech_blocks"]
    assert blocks and all(b["attribution_status"] == "unknown" and b["speaker_id"] is None for b in blocks)
    assert expand(p)["speaker_context"]["speech_blocks"][0]["text"] == " ".join(r[3] for r in blocks[0]["words"])


def test_the_window_stays_inside_the_recording_and_short_ones_are_their_own_length(tmp_path):
    assert packet.window(590.0, 598.0, 600.0) == (530000, 70000)
    assert packet.window(1.0, 20.0, 600.0) == (0, 70000)
    assert packet.window(10.0, 46.6, 62.2) == (0, 62200)
    with pytest.raises(packet.TooShort):
        packet.window(1.0, 20.0, 25.0)


# ---------- the step -------------------------------------------------------------------------------------------------

def packets_in(prompt):
    return json.loads(prompt.split("Source windows (untrusted evidence):\n", 1)[1].split("\nRepair request:", 1)[0])


def fit_answer(prompt, *, bad=False):
    """A model that cuts each window to its 'story' words; `bad`: the first answer cuts too short."""
    out = []
    for p in packets_in(prompt):
        rows = [w for b in p["speaker_context"]["speech_blocks"] for w in b["words"]]
        story = [w for w in rows if w[3] in ("story", "part") or (w[3].isdigit() and 20 <= int(w[3]) <= 24)]
        first, last = story[0], story[-1]
        end = first[2] + 5000 if bad else last[2]
        out.append({"id": p["id"], "trim": {"start_ms": first[1], "end_ms": end, "event_start_word_id": first[0],
                                            "event_end_word_id": first[0] if bad else last[0], "focus_relation": "event_overlaps_focus"},
                    "fit_score": 70, "clip_format": "story", "title": "История"})
    return {"clips": out}


def caller_with_fit(calls, bad_first=False):
    def caller(model, prompt, schema, images=None):
        if "Source windows (untrusted evidence)" in prompt:
            repair = "Repair request:" in prompt
            calls.append("fit_repair" if repair else "fit")
            data = fit_answer(prompt, bad=bad_first and not repair)
            return Answer(data, json.dumps(data), 0.1, 300, 50)
        return fake_caller(model, prompt, schema)
    return caller


def demo_precise(tmp_path, monkeypatch, caller):
    job = tmp_path / "job"

    def fake_ingest(source, job_dir, **_):
        write_wav(job_dir / "audio.wav")
        return {"kind": "file", "title": "demo", "platform": "file", "channel": "demo", "duration_s": 600.0}

    monkeypatch.setattr("vodcut.pipeline.ingest.ingest", fake_ingest)
    monkeypatch.setattr("vodcut.pipeline.transcribe", lambda wav, rec, progress=None: make_segments())
    from vodcut import pipeline
    return job, pipeline.run("demo.mp4", Asker(ModelSettings(provider="openai", model="m"), caller), job=job, language="ru",
                             recognizer_for=lambda lang: FakeRecognizer(), precise=True)


def test_precise_cuts_the_clip_to_its_words_and_writes_its_events(tmp_path, monkeypatch):
    from smtv_core import events
    calls = []
    job, result = demo_precise(tmp_path, monkeypatch, caller_with_fit(calls))
    [clip] = result["clips"]
    assert calls == ["fit"]
    assert clip["pass2"] == {"start_s": 200.0, "end_s": 240.9, "title": "The story"} and clip["fit"]["status"] == "ok"
    assert clip["title"] == "The story"                                               # Fit moved it little: pass 2's title stays
    assert clip["start_s"] == 200.0 and clip["end_s"] == pytest.approx(242.4, abs=0.05)        # last word 241.4 + a second of air
    got = events.read(job)
    assert [e["data"]["name"] for e in got if e["type"] == "stage"] == ["audio", "speech", "scan", "rating", "pick", "fit"]
    assert [e["data"]["steps"] for e in got if e["type"] == "stage"] == [6] * 6
    [fitted] = [e["data"] for e in got if e["type"] == "clip_fitted"]
    assert fitted["by"] == "model" and fitted["before"] == {"start_s": 200.0, "end_s": 240.9} and fitted["cut_start_s"] == 0.0
    assert fitted["title"] == "The story" and "title_before" not in fitted
    assert fitted["cut_end_s"] == pytest.approx(-1.5, abs=0.05) and fitted["cut_s"] == pytest.approx(-1.5, abs=0.05)
    assert [e["data"]["purpose"] for e in got if e["type"] == "model_call"][-1] == "fit"
    assert "fit_s" in got[-1]["data"]["timings"] and got[-1]["data"]["clips"][0]["end_s"] == clip["end_s"]
    assert_contract(job)
    saved = json.loads((job / "fit.json").read_text(encoding="utf-8"))
    assert saved["policy"] == fit.policy_id() and list(saved["clips"].values())[0]["status"] == "ok"

    demo_precise(tmp_path, monkeypatch, caller_with_fit(calls))                       # a rerun asks nothing again
    assert calls == ["fit"]
    assert [e["data"].get("cached") for e in events.read(job) if e["type"] == "clip_fitted"] == [None, True]


def test_a_crooked_answer_gets_one_repair_request(tmp_path, monkeypatch):
    calls = []
    job, result = demo_precise(tmp_path, monkeypatch, caller_with_fit(calls, bad_first=True))
    assert calls == ["fit", "fit_repair"] and result["clips"][0]["fit"]["repaired"] is True
    assert result["clips"][0]["end_s"] > 241


def test_a_failed_repair_keeps_the_picked_bounds_and_is_not_asked_again(tmp_path, monkeypatch):
    calls = []

    def caller(model, prompt, schema, images=None):
        if "Source windows (untrusted evidence)" in prompt:
            calls.append(1)
            data = fit_answer(prompt, bad=True)                                    # wrong both times
            return Answer(data, "", 0.1)
        return fake_caller(model, prompt, schema)

    job, result = demo_precise(tmp_path, monkeypatch, caller)
    clip = result["clips"][0]
    assert len(calls) == 2 and clip["fit"]["status"] == "invalid" and (clip["start_s"], clip["end_s"], clip["title"]) == (200.0, 240.9, "The story")
    assert "invalid_trim_duration_or_bounds" in clip["fit"]["errors"]
    assert_contract(job)
    demo_precise(tmp_path, monkeypatch, caller)
    assert len(calls) == 2                                                         # production: an invalid answer after its repair is final


def test_a_model_error_keeps_the_bounds_and_the_next_run_asks_again(tmp_path, monkeypatch):
    from smtv_core.llm import ProviderError
    calls = []

    def broken(model, prompt, schema, images=None):
        if "Source windows (untrusted evidence)" in prompt:
            calls.append(1)
            raise ProviderError("timeout")
        return fake_caller(model, prompt, schema)

    job, result = demo_precise(tmp_path, monkeypatch, broken)
    clip = result["clips"][0]
    assert clip["fit"]["status"] == "error" and (clip["start_s"], clip["end_s"]) == (200.0, 240.9)
    from smtv_core import events
    missing = [e["data"] for e in events.read(job) if e["type"] == "progress" and e["data"]["stage"] == "missing"]
    assert missing == [{"stage": "missing", "step": "fit", "done": 1, "total": 1}]          # B26: the person is told
    assert_contract(job)
    demo_precise(tmp_path, monkeypatch, broken)
    assert len(calls) == 2


def test_without_precise_nothing_changes(tmp_path, monkeypatch):
    job, result = run_demo(tmp_path, monkeypatch)
    assert "fit" not in result["clips"][0] and not (job / "fit.json").exists() and result["precise"] is False


def test_the_command_line_prints_the_cut(tmp_path):
    from vodcut import console
    line = console.line({"type": "clip_fitted", "data": {"clip": "clip01", "by": "model", "status": "ok", "before": {"start_s": 10.04, "end_s": 46.64},
                                                         "after": {"start_s": 13.5, "end_s": 47.6}, "cut_start_s": 3.46, "cut_end_s": -0.96, "cut_s": 2.5}}, tmp_path)
    assert line == "  clip01 0:00:10–0:00:46 → 0:00:13–0:00:47  start +3.5 s, end +1.0 s, 34.1 s"
    assert console.line({"type": "stage", "data": {"name": "fit", "step": 6, "steps": 6, "clips": 3}}, tmp_path) == "6/6 Cutting 3 clips exactly by words (Fit)"


def test_clip_fitted_is_declared_in_the_event_contract():
    assert "clip_fitted" in event_contract.types() and tuple(map(int, event_contract.version().split("."))) >= (1, 3)


def test_fit_s_title_replaces_pass_2_s_only_when_most_of_the_clip_is_gone():
    clip = {"id": "clip05", "start_s": 5884.0, "end_s": 5935.84, "title": "Кот просто пришёл попросить пожрать"}
    result = {"status": "ok", "window_start_s": 5874.92, "window_ms": 70000, "title": "Кот под кроватью", "fit_score": 75,
              "trim": {"start_ms": 19160, "end_ms": 38120}}
    cut = fit.apply(clip, result)
    assert (cut["start_s"], cut["end_s"], cut["title"]) == (5894.08, 5913.04, "Кот под кроватью") and cut["pass2"]["title"] == clip["title"]
    data = fit.event(cut)
    assert data["title_before"] == clip["title"] and data["cut_s"] == pytest.approx(32.88)
    small = fit.apply(clip, {**result, "trim": {"start_ms": 12000, "end_ms": 58000}})
    assert small["title"] == clip["title"] and "title_before" not in fit.event(small)


def test_a_crash_in_one_batch_keeps_pass_2_bounds_and_the_other_answers(tmp_path, monkeypatch):
    calls = []

    def caller(model, prompt, schema, images=None):
        if "Source windows (untrusted evidence)" in prompt:
            calls.append(1)
            raise ConnectionResetError("reset mid-answer")                         # not a ProviderError
        return fake_caller(model, prompt, schema)

    job, result = demo_precise(tmp_path, monkeypatch, caller)
    clip = result["clips"][0]
    assert clip["fit"]["status"] == "error" and "ConnectionResetError" in clip["fit"]["errors"][0] and clip["end_s"] == 240.9
    assert_contract(job)
    demo_precise(tmp_path, monkeypatch, caller)
    assert len(calls) == 2                                                         # asked again: an error is not kept


def test_unreadable_audio_is_an_error_asked_again_not_a_skip(tmp_path, monkeypatch):
    import wave as wave_module
    calls = []
    monkeypatch.setattr(acoustics, "read_window", lambda *a, **k: (_ for _ in ()).throw(wave_module.Error("file does not start with RIFF id")))
    job, result = demo_precise(tmp_path, monkeypatch, caller_with_fit(calls))
    assert result["clips"][0]["fit"]["status"] == "error" and calls == []
    assert json.loads((job / "fit.json").read_text(encoding="utf-8"))["clips"] == {}
