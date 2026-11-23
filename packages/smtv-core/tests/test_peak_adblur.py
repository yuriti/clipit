import pytest

from smtv_core.render import adblur, peak


def w(text, s, e):
    return {"text": text, "s": s, "e": e}


# --- peak lines -------------------------------------------------------------------------------------

def test_peak_is_the_last_phrase_split_literally():
    words = [w("ну", 0, 200), w("всё.", 250, 500), w("я", 1000, 1100), w("тебя", 1150, 1400), w("уничтожил", 1450, 2000)]
    p = peak.choose(words, 2600)
    assert p.lines == ("я тебя", "уничтожил")
    assert p.starts_ms == (1000, 1450) and p.end_ms == 2600


def test_long_phrase_keeps_its_ending():
    text = "это был самый длинный и совершенно невероятный вечер моей жизни".split()
    words = [w(t, i * 300, i * 300 + 250) for i, t in enumerate(text)]
    p = peak.choose(words, len(text) * 300)
    assert len(p.lines) <= 3 and all(len(line) <= 16 for line in p.lines)
    assert p.lines[-1].endswith("жизни")
    assert p.start_ms > 0


def test_one_word_makes_one_line():
    assert peak.choose([w("ЧТО?!", 0, 400)], 900).lines == ("ЧТО?!",)


def test_no_peak_when_the_phrase_ended_long_before_the_end_or_one_word_is_too_long():
    assert peak.choose([w("привет", 0, 500)], 5000) is None
    assert peak.choose([w("сверхзамечательнейший", 0, 500)], 800) is None
    assert peak.choose([], 1000) is None


def test_pause_ends_the_phrase():
    words = [w("раз", 0, 200), w("два", 1000, 1200), w("три", 1250, 1400)]
    assert [x["text"] for x in peak.last_phrase(words)] == ["два", "три"]


def test_split_words_balances_lines():
    assert peak.split_words(["один", "два", "три", "четыре"], 2) == ["один два", "три четыре"]
    assert peak.split_words(["слишкомдлинноеслово"], 1) is None


def test_slam_events():
    p = peak.Peak(("ТЫ", "СЕРЬЁЗНО?"), (1000, 1400), 3000)
    ev = peak.events(p, "&H4DE1FF&", "&H111111&", "&HFFFFFF&")
    assert [(e[0], e[1], e[2]) for e in ev] == [(83, 1000, 3000), (83, 1400, 3000)]
    assert "\\pos(540,1190)" in ev[0][3] and "\\pos(540,1350)" in ev[1][3]
    assert "\\1c&HFFFFFF&" in ev[0][3] and "\\1c&H4DE1FF&" in ev[1][3]          # the last line is coloured
    assert "\\fs176" in ev[1][3] and "\\fscx240" in ev[1][3] and ev[1][3].endswith("СЕРЬЁЗНО?")


# --- ad blur ----------------------------------------------------------------------------------------

def region(**over):
    r = {"id": "slot-1", "label": "betting banner", "confidence": 0.9, "needs_review": False, "reason": "promo code",
         "box": {"x": 100, "y": 50, "width": 200, "height": 100}, "observed_frames": [0, 2]}
    r.update(over)
    return r


def test_valid_answer_becomes_padded_fractions():
    [r] = adblur.validate_answer({"regions": [region()], "excluded": [], "notes": ""}, 1280, 720)
    rect = r["rect"]
    assert rect["x"] == pytest.approx(94 / 1280) and rect["y"] == pytest.approx(47 / 720)
    assert rect["x"] + rect["width"] == pytest.approx(306 / 1280) and rect["y"] + rect["height"] == pytest.approx(153 / 720)
    assert adblur.validate_answer({"regions": []}, 1280, 720) == []


@pytest.mark.parametrize("bad", [
    None, {"regions": "x"}, {"regions": [region(id=f"r{i}") for i in range(9)]},
    {"regions": [region(), region()]},                                   # duplicate id
    {"regions": [region(confidence=1.5)]}, {"regions": [region(needs_review="no")]},
    {"regions": [region(observed_frames=[])]}, {"regions": [region(observed_frames=[5])]},
    {"regions": [region(box={"x": 1200, "y": 0, "width": 100, "height": 10})]},   # past the right edge
    {"regions": [region(box={"x": 0, "y": 0, "width": 0, "height": 10})]},
    {"regions": [region(box={"x": 0, "y": 0, "width": 10, "height": 10, "z": 1})]},
    {"regions": [region(box={"x": float("nan"), "y": 0, "width": 10, "height": 10})]}])
def test_bad_answers_are_rejected(bad):
    with pytest.raises(adblur.AdBlurError):
        adblur.validate_answer(bad, 1280, 720)


def test_fractions_map_onto_the_normalized_source():
    full = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}
    assert adblur.to_source_pixels(full, 1280, 720) == (1920, 1080, 0, 0)
    assert adblur.to_source_pixels({"x": 0.5, "y": 0.5, "width": 0.25, "height": 0.25}, 1280, 720) == (480, 270, 960, 540)
    # a 4:3 frame is cropped top and bottom: a box in the top strip falls outside
    assert adblur.to_source_pixels({"x": 0.0, "y": 0.0, "width": 1.0, "height": 0.1}, 1280, 960) is None


def test_blur_filter_chain():
    assert adblur.filter_chain("[src]", "[clean]", []) == "[src]null[clean]"
    chain = adblur.filter_chain("[src]", "[clean]", [(300, 150, 100, 50), (10, 400, 1800, 0)])
    assert chain.split(";") == [
        "[src]split=2[ad0base][ad0crop]", "[ad0crop]crop=300:150:100:50,boxblur=20:1[ad0blur]", "[ad0base][ad0blur]overlay=100:50[ad1]",
        "[ad1]split=2[ad1base][ad1crop]", "[ad1crop]crop=10:400:1800:0,boxblur=4:1:1:1[ad1blur]", "[ad1base][ad1blur]overlay=1800:0[clean]"]


@pytest.mark.parametrize("box", [(238, 77, 1677, 11), (10, 400, 1800, 0), (41, 41, 3, 3), (300, 150, 100, 50), (4, 4, 0, 0)])
def test_every_blur_box_is_one_ffmpeg_accepts(tmp_path, box):
    """Stage 15: a 238×77 banner made ffmpeg refuse the chroma radius and the whole clip failed."""
    import shutil
    import subprocess
    if not shutil.which("ffmpeg"):
        pytest.skip("no ffmpeg")
    chain = adblur.filter_chain("[0:v]", "[v]", [box])
    done = subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=1920x1080:d=0.2", "-filter_complex", chain,
                           "-map", "[v]", "-pix_fmt", "yuv420p", "-f", "null", "-"], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
