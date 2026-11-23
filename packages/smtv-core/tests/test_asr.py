from pathlib import Path

import pytest

from smtv_core import prompts
from smtv_core.asr import engines, language, words


def test_plan_windows_covers_the_range_with_padding():
    ws = words.plan_windows(0, 50, grid=18, pad=3)
    assert [(w["grid_start"], w["grid_end"]) for w in ws] == [(0, 18), (18, 36), (36, 50)]
    assert ws[1]["start"] == 15 and ws[1]["end"] == 39 and ws[0]["start"] == 0 and ws[-1]["end"] == 50


def test_gigaam_tokens_to_words():
    out = words.words_space_tokens([" при", "вет", " ", "мир"], [0.0, 0.04, 0.3, 0.5], None, offset=10, frame_s=0.04)
    assert [w["word"] for w in out] == [" привет", " мир"]
    assert out[0]["start"] == 10.0 and out[0]["end"] <= out[1]["start"]


def test_parakeet_marker_tokens_to_words():
    out = words.words_marker_tokens(["▁hel", "lo", "▁wor", "ld", " again"], [0.0, 0.08, 0.4, 0.48, 0.9], None, offset=0, frame_s=0.08)
    assert [w["word"] for w in out] == [" hello", " world", " again"]


def test_stitch_keeps_each_word_once_at_the_seam():
    ws = words.plan_windows(0, 36, grid=18, pad=3)
    w = lambda text, t: {"word": " " + text, "start": t, "end": t + 0.3, "probability": 1.0}  # noqa: E731
    first = [w("a", 1.0), w("b", 17.5), w("c", 18.2)]          # c is past the grid line: belongs to the second window
    second = [w("b", 17.5), w("c", 18.2), w("d", 30.0)]        # b starts before the line: belongs to the first
    assert [x["word"].strip() for x in words.stitch_windows(ws, [first, second])] == ["a", "b", "c", "d"]


def test_segments_close_at_sentence_end_and_pause():
    w = lambda text, t: {"word": " " + text, "start": t, "end": t + 0.4, "probability": 1.0}  # noqa: E731
    seq = [w("one", 0), w("two", 1), w("three", 2), w("four", 3), w("five.", 4.2), w("after", 4.7), w("pause", 8.0)]
    segs = words.with_ids(words.segments(seq))
    assert [s["text"] for s in segs] == ["one two three four five.", "after", "pause"]
    assert [s["sid"] for s in segs] == ["s00000", "s00001", "s00002"]


def test_filtered_segments_drop_loops():
    seg = lambda text: {"text": text, "start": 0, "end": 1, "words": []}  # noqa: E731
    loop = "subtitles by the community"
    out = words.filtered_segments([seg("hello there"), seg(loop), seg(loop), seg("ok"), seg(loop), seg(" ")])
    assert [s["text"] for s in out] == ["hello there", "ok"]


def test_language_guess_and_engine_choice():
    assert language.guess("Короче, вчера после стрима заказал пиццу, приложение пишет, что курьер у подъезда") == "ru"
    assert language.guess("Вчора після стріму замовив піцу, і кур'єр сказав, що він біля їхнього під'їзду") == "uk"
    assert language.guess("so yesterday I ordered a pizza after stream and the courier was outside my door") == "latin"
    assert language.guess("ok ok") is None
    assert engines.engine_for("ru") is engines.GIGAAM
    assert engines.engine_for("uk") is engines.PARAKEET and engines.engine_for("latin") is engines.PARAKEET
    with pytest.raises(ValueError):
        engines.engine_for("ja")


def test_bundled_prompts_are_english_and_have_schemas():
    for name in ("vod/pass1-prompt.txt", "vod/pass2-prompt.txt", "vod/recap-prompt.txt", "fit/prompt-policy.txt"):
        assert not any("Ѐ" <= c <= "ӿ" for c in prompts.text(name)), name
    for name in ("pass1", "pass2", "fit", "recap", "critic", "layout", "banner"):
        assert prompts.schema(name)["type"] == "object"
    assert prompts.version() == "1.1.0"


# --- the language without listening, and models that download on first use -----------------------------------

def test_auto_language_takes_the_recordings_own_else_it_is_listened_to(tmp_path):
    from smtv_core.asr.language import choose
    assert choose("en", tmp_path) == "en" and choose("ru-RU", tmp_path) == "ru" and choose("de_DE", tmp_path) == "de"
    # stage 15: no hint is never «Russian» unheard, with or without Parakeet on this computer
    assert choose(None, tmp_path) is None and choose("", tmp_path) is None and choose("xx", tmp_path) is None


def test_gigaam_tells_another_language_by_its_latin_letters():
    from smtv_core.asr import language

    english = "fall and agan a anken the frown the kavestadafutipto sniperona good position avrili lusty for eir blaking"
    russian = "я не знаю клининг не могу заказать никак так так робот пылесос я думаю отдать кому то"
    assert language.guess(english) == "latin" and language.guess(russian) == "ru" and language.guess("ну") is None


def test_a_missing_model_downloads_with_progress_and_says_so(tmp_path, monkeypatch):
    from smtv_core.asr import engines
    seen = []

    def fake_load(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "big.bin").write_bytes(b"x" * (3 * 1024 * 1024))
        (self.dir / "encoder-model.onnx").write_bytes(b"x")
        import time
        time.sleep(0.15)
        return self

    monkeypatch.setattr(engines.Recognizer, "load", fake_load)
    engines.load_watched(engines.PARAKEET, lambda mb, total: seen.append((mb, total)), tmp_path, every_s=0.05)
    assert seen[-1] == (2432, 2432) and any(mb == 3 for mb, _ in seen[:-1])
    seen.clear()
    engines.load_watched(engines.PARAKEET, lambda mb, total: seen.append(mb), tmp_path)        # here now: no download, no progress
    assert seen == []


def test_a_model_downloads_on_first_use_even_when_its_folder_is_there_empty(tmp_path, monkeypatch):
    import sys
    import types

    from smtv_core.asr import engines
    seen = {}

    class Model:
        def with_timestamps(self):
            return self

    def load_model(name, path, providers=None):
        seen["existed"] = Path(path).exists()           # onnx-asr downloads only into a folder that is not there yet
        return Model()

    monkeypatch.setitem(sys.modules, "onnx_asr", types.SimpleNamespace(load_model=load_model))
    (tmp_path / "gigaam").mkdir()
    (tmp_path / "gigaam" / "config.json").write_text("{}", encoding="utf-8")       # left by an interrupted download, no model in it
    engines.Recognizer(engines.GIGAAM, tmp_path).load()
    assert seen["existed"] is False
    (tmp_path / "gigaam").mkdir()
    (tmp_path / "gigaam" / "v3_e2e_rnnt_encoder.onnx").write_bytes(b"x")
    engines.Recognizer(engines.GIGAAM, tmp_path).load()
    assert seen["existed"] is True and (tmp_path / "gigaam" / "v3_e2e_rnnt_encoder.onnx").exists()   # a model on disk stays
