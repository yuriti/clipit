import math
import shutil
import subprocess

import pytest

from smtv_core.audio import bleep, loudness

HAS_FFMPEG = bool(shutil.which("ffmpeg"))


# --- loudness ---------------------------------------------------------------------------------------

def test_gain_brings_the_clip_to_minus_14():
    assert loudness.gain_db(-20.0) == pytest.approx(6.0)
    assert loudness.gain_db(-9.0) == pytest.approx(-5.0)        # a loud clip is turned down too
    assert loudness.gain_db(-14.3) is None                       # within half a LU: left alone
    assert loudness.gain_db(-50.0) == 20.0                       # a near-silent clip is not blown up
    assert loudness.gain_db(-70.0) is None and loudness.gain_db(math.nan) is None   # silence, no sound


def test_measure_output_is_parsed_from_the_last_value():
    out = "[Parsed_ametadata_2] frame:1 pts:0\nlavfi.r128.I=-30.5\nlavfi.r128.I=-21.37\n"
    assert loudness.parse_measure(out) == -21.37
    assert math.isnan(loudness.parse_measure("")) and math.isnan(loudness.parse_measure("lavfi.r128.I=nan-ish"))


def test_two_pass_commands():
    m = loudness.measure_args("in.mp4", 10.0)
    assert "ebur128=metadata=1,aselect=gte(t\\,9.800),ametadata=print:key=lavfi.r128.I:file=-" in m
    a = loudness.apply_args("in.mp4", "out.mp4", 6.0)
    assert a[a.index("-af") + 1] == "volume=6.00dB,alimiter=limit=0.794328:level=false:latency=true"
    assert a[a.index("-c:v") + 1] == "copy"


def _tone(path, volume_db, seconds=4):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=30", "-f", "lavfi",
                    "-i", "sine=frequency=440:sample_rate=48000", "-t", str(seconds), "-af", f"volume={volume_db}dB",
                    "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", str(path)], check=True)


def _lufs(path, seconds):
    done = subprocess.run(loudness.measure_args(path, seconds), capture_output=True, text=True, check=True)
    return loudness.parse_measure(done.stdout)


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_real_quiet_clip_reaches_minus_14(tmp_path):
    clip = tmp_path / "clip.mp4"
    _tone(clip, -12)
    before = _lufs(clip, 4)
    assert before < -25
    gain = loudness.normalize(clip, 4)
    assert gain == pytest.approx(-14 - before)
    assert abs(_lufs(clip, 4) - (-14)) < 1.0
    assert loudness.normalize(clip, 4) is None                   # already there: untouched


# --- bleep ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("word,hit", [
    ("пидор", True), ("Пидорасы!", True), ("нигер,", True), ("faggot", True), ("хохлы", True), ("пидoр", True),  # Latin o
    ("блядь", False), ("сука", False), ("нахуй", False), ("пиздец", False), ("долбоёб", False), ("fuck", False),
    ("хачапури", False), ("жидкость", False), ("привет", False), ("", False)])
def test_only_slurs_are_bleeped(word, hit):
    assert bleep.is_bleeped(word) is hit


def test_lists_are_per_language():
    assert bleep.languages() == ["en", "ru"]
    assert bleep.pattern(("en",)).match("faggot") and not bleep.pattern(("en",)).match("пидор")


@pytest.mark.parametrize("start,end,span", [(10.0, 10.3, (10.025, 10.275)), (10.0, 10.12, (9.96, 10.16)),
                                            (10.0, 13.2, (10.2, 10.6)), (0.02, 0.1, (0.0, 0.2))])
def test_tone_sits_on_the_middle_of_the_word(start, end, span):
    assert bleep.span(start, end) == span


def test_tones_from_clip_words():
    words = [{"text": "ну", "s": 0, "e": 200}, {"text": "пидор", "s": 1000, "e": 1300}]
    assert bleep.tones(words) == [(1.025, 1.275)]


def test_audio_filter_text():
    assert bleep.audio_filter([]) == ""
    assert bleep.audio_filter([(1.0, 1.25), (3.5, 3.9)]) == (
        "aeval='0.07*sin(2*PI*1000*t)+(val(ch)-0.07*sin(2*PI*1000*t))*clip(max((1.000-t)/0.015+1,(t-1.250)/0.015+1),0,1)"
        "*clip(max((3.500-t)/0.015+1,(t-3.900)/0.015+1),0,1)':c=same")


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
def test_real_bleep_replaces_the_sound_only_over_the_span(tmp_path):
    out = tmp_path / "bleep.wav"
    graph = f"[0:a]asetpts=N/SR/TB,{bleep.audio_filter([(1.0, 1.4)])}[a]"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "2",
                    "-filter_complex", graph, "-map", "[a]", str(out)], check=True)
    stats = subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-i", str(out), "-af",
                            "atrim=0:0.9,astats=metadata=1:reset=0,ametadata=print:key=lavfi.astats.Overall.Peak_level:file=-", "-f", "null", "-"],
                           capture_output=True, text=True).stdout
    assert "-inf" in stats.splitlines()[-1]                      # silence stays silence before the word
    stats = subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-i", str(out), "-af",
                            "atrim=1.05:1.35,astats=metadata=1:reset=0,ametadata=print:key=lavfi.astats.Overall.Peak_level:file=-", "-f", "null", "-"],
                           capture_output=True, text=True).stdout
    peak = float(stats.strip().splitlines()[-1].split("=")[1])
    assert -25 < peak < -20                                      # 0.07 ≈ −23 dBFS tone over the word
