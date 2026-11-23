import shutil
import subprocess

import pytest

from smtv_core.render import captions, ffmpeg, fonts
from smtv_core.render.layout import FULL, Layout, LayoutError, pixels, validate

CAM = {"x": 0.75, "y": 0.0, "width": 0.25, "height": 0.3}
GAME = {"x": 0.0, "y": 0.1, "width": 0.75, "height": 0.9}


def answer(layout, webcam=None, streamer=None, scene=None):
    return {"layout": layout, "live_chat_side": "none", "webcam_region": webcam, "streamer_crop": streamer, "scene_crop": scene,
            "screen_essential": True, "stable_across_frames": True, "needs_review": False, "reason": "x", "uncertainties": []}


def test_streamer_camera_is_never_dropped():
    small = validate(answer("scene_only", webcam=CAM, scene=GAME))
    assert small.mode == "streamer_scene_split" and small.streamer_crop == CAM
    big_cam = {"x": 0.0, "y": 0.0, "width": 0.9, "height": 0.9}
    assert validate(answer("scene_only", webcam=big_cam, scene=GAME)) == Layout("scene_only", big_cam)
    assert validate(answer("streamer_only", webcam=CAM, streamer=CAM)).scene_crop == CAM
    assert validate(answer("streamer_scene_split", webcam=CAM, streamer=CAM, scene=GAME)).mode == "streamer_scene_split"


def test_bad_rectangles_are_rejected():
    with pytest.raises(LayoutError):
        validate(answer("scene_only", scene={"x": 0.5, "y": 0, "width": 0.9, "height": 1}))
    with pytest.raises(LayoutError):
        validate({"layout": "nonsense"})


def test_pixels_clamp_inside_the_source():
    assert pixels(FULL) == (1920, 1080, 0, 0)
    assert pixels({"x": 0.999, "y": 0.999, "width": 0.5, "height": 0.5}) == (2, 2, 1918, 1078)


def test_filter_graph_shapes():
    g = ffmpeg.filter_graph(Layout("scene_only", FULL), None, None)
    assert "boxblur=30:2" in g and "1080:h=1920" in g          # 16:9 into 9:16: blurred background
    split = ffmpeg.filter_graph(Layout("streamer_scene_split", GAME, CAM), captions_path := None, None)  # noqa: F841
    assert "vstack=inputs=2" in split and "h=640" in split and "h=1280" in split
    assert "960" in ffmpeg.filter_graph(Layout("streamer_scene_split_equal", GAME, CAM), None, None)


def test_caption_groups_and_ass():
    w = lambda text, s, e, seg=0: {"text": text, "s": s, "e": e, "seg": seg}  # noqa: E731
    words = [w("так", 0, 300), w("чат,", 350, 600), w("мы", 650, 800), w("вернулись.", 850, 1300), w("короче", 2500, 2800),
             w("вчера", 2850, 3100), w("{скобки}", 3150, 3400)]
    groups = captions.groups_of(words)
    assert [len(g) for g in groups] == [4, 3]                      # sentence end, then a pause > 600 ms
    ass = captions.build_ass(words, 5000, hook="Заказал пиццу соседу, а он оценил доставку")
    assert "PlayResX: 1080" in ass and "Montserrat Black" in ass
    assert "ВЕРНУЛИСЬ." in ass and "\\{СКОБКИ\\}" in ass          # upper case in any alphabet, braces escaped
    assert "\\N" in ass                                             # a long hook is split into two rows
    for line in ass.splitlines():
        if line.startswith("Dialogue:"):
            end = line.split(",")[2]
            h, m, s = end.split(":")
            assert int(h) * 3600 + int(m) * 60 + float(s) <= 5.0


def test_text_width_grows_with_text_and_size():
    assert fonts.text_width("WWW", 96) > fonts.text_width("WW", 96) > 0
    assert fonts.text_width("ПИЦЦА", 96) == pytest.approx(2 * fonts.text_width("ПИЦЦА", 48))


def test_clip_words_in_clip_time():
    segs = [{"start": 9.0, "end": 12.0, "words": [{"word": " a", "start": 9.0, "end": 9.4}, {"word": " b", "start": 10.2, "end": 10.6}]}]
    assert captions.clip_words(segs, 10.0, 11.0) == [{"text": "b", "s": 200, "e": 600, "seg": 0}]


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
def test_real_render_without_captions(tmp_path):
    src = tmp_path / "src.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=30", "-f", "lavfi",
                    "-i", "sine=frequency=440:sample_rate=48000", "-t", "6", "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac", str(src)], check=True)
    out = ffmpeg.render(src, tmp_path / "clip.mp4", 1.0, 4.0, Layout("streamer_scene_split", GAME, CAM))
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height:format=duration", "-of", "json", str(out)],
                           capture_output=True, text=True, check=True).stdout
    assert '"width": 1080' in probe and '"height": 1920' in probe and '"codec_type": "audio"' in probe
    import json
    assert abs(float(json.loads(probe)["format"]["duration"]) - 3.0) < 0.2


def test_filter_graph_with_ad_blur_and_bleep():
    g = ffmpeg.filter_graph(Layout("scene_only", FULL), None, None, blur_boxes=[(300, 150, 100, 50)], bleep="aeval='x':c=same")
    assert "setsar=1[raw];[raw]split=2[ad0base][ad0crop]" in g and "overlay=100:50[src]" in g and "[src]crop=" in g
    assert "[0:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=N/SR/TB,aeval='x':c=same[aout]" in g
    plain = ffmpeg.filter_graph(Layout("scene_only", FULL), None, None)
    assert "[raw]" not in plain and "asetpts" not in plain and "setsar=1[src]" in plain


def test_peak_replaces_the_captions_at_the_end():
    from smtv_core.render import peak
    w = lambda text, s, e: {"text": text, "s": s, "e": e, "seg": 0}  # noqa: E731
    words = [w("так", 0, 300), w("вот.", 350, 600), w("я", 1000, 1100), w("победил", 1150, 1600)]
    p = peak.choose(words, 2500)
    ass = captions.build_ass(words, 2500, peak=p)
    dialogue = [line for line in ass.splitlines() if line.startswith("Dialogue:")]
    assert any(line.startswith("Dialogue: 83,0:00:01.00,0:00:02.50") and line.endswith("}Я") for line in dialogue)
    assert any(line.startswith("Dialogue: 83,0:00:01.15") and line.endswith("}ПОБЕДИЛ") for line in dialogue)
    assert not any(line.startswith("Dialogue: 61") and line.endswith("}ПОБЕДИЛ") for line in dialogue)   # no ordinary caption under it
    assert all(line.split(",")[2] <= "0:00:01.00" for line in dialogue if line.startswith("Dialogue: 6"))
    assert "Dialogue: 83" not in captions.build_ass(words, 2500)


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")
def test_real_render_with_ad_blur_bleep_and_loudness(tmp_path):
    from smtv_core.audio import bleep, loudness
    src = tmp_path / "src.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=30", "-f", "lavfi",
                    "-i", "sine=frequency=440:sample_rate=48000", "-t", "5", "-af", "volume=-12dB", "-c:v", "libx264", "-preset", "ultrafast",
                    "-c:a", "aac", str(src)], check=True)
    out = ffmpeg.render(src, tmp_path / "clip.mp4", 1.0, 4.0, Layout("scene_only", FULL), blur_boxes=[(300, 150, 100, 50)],
                        bleep=bleep.audio_filter([(1.0, 1.3)]), loudness=True)
    done = subprocess.run(loudness.measure_args(out, 3.0), capture_output=True, text=True, check=True)
    assert abs(loudness.parse_measure(done.stdout) - loudness.TARGET_LUFS) < 1.0
    assert not (tmp_path / "clip.part.mp4").exists()


def test_hook_card_stays_off_the_streamer_face():
    import re
    from smtv_core.render.layout import SLOTS

    def card(seam, hook):
        line = next(x for x in captions.build_ass([], 5000, hook=hook, seam=seam).splitlines() if x.startswith("Dialogue: 75"))
        cy = int(re.search(r"\\pos\(540,(\d+)\)", line).group(1))
        h = max(float(v) for v in re.findall(r"[ ,](\d+) b", line))     # the rounded rectangle's largest y
        return cy - h / 2, cy + h / 2

    top, _ = card(None, "Короткий")
    assert top < 300 and captions.seam_y("scene_only") is None
    for mode, (cam_h, _) in SLOTS.items():
        assert captions.seam_y(mode) == cam_h
        for hook in ("Короткий", "Ваня Дмитриенко просочился в поставку и всех удивил"):
            upper, lower = card(cam_h, hook)
            assert upper >= cam_h - 80 - 1 and lower > cam_h        # off the face band [80, cam_h - 80], across the seam


def test_a_failure_keeps_ffmpegs_first_words():
    from smtv_core.render.ffmpeg import reason
    err = "[Parsed_boxblur_6] Invalid chroma_param radius value 19\n" + "Could not open encoder before EOF\n" * 40
    assert reason(err).startswith("[Parsed_boxblur_6] Invalid chroma_param") and reason(err).endswith("EOF") and len(reason(err)) < 620


def test_a_streamer_filling_the_frame_fills_the_clip_without_bars():
    """Stage 15: a just-chatting stream (the camera is the whole picture) came out with blurred bars above and below,
    because the model's crop was wider than 9:16; production fills the clip."""
    from smtv_core.render.layout import cover, vote
    whole = {"x": 0.0125, "y": 0.0111, "width": 0.975, "height": 0.9778}
    person = {"x": 0.36, "y": 0.23, "width": 0.32, "height": 0.77}
    layout, camera, kinds = vote([answer("scene_only", webcam=whole, scene=person)] * 3)
    assert kinds == ["streamer_only"] * 3 and layout.mode == "scene_only"
    cw, ch, x, y = pixels(layout.scene_crop)
    assert abs(cw / ch - 1080 / 1920) < 0.01 and not ffmpeg.needs_background(cw, ch, 1080, 1920)
    assert x < 0.52 * 1920 < x + cw and cw >= 0.3 * 1920                  # the person (centre 0.52) stays in the picture
    edge = cover({"x": 0.9, "y": 0.5, "width": 0.1, "height": 0.2})       # near the edge: shifted inside, not cut
    assert edge["x"] + edge["width"] <= 1.0 and edge["y"] + edge["height"] <= 1.0
    game_only = vote([answer("scene_only", scene=FULL)] * 3)[0]          # no webcam: the middle of the game fills the clip
    gw, gh, gx, _ = pixels(game_only.scene_crop)
    assert gh == 1080 and abs(gw / gh - 1080 / 1920) < 0.01 and abs(gx + gw / 2 - 960) < 10
    left = vote([answer("scene_only", scene={"x": 0.0, "y": 0.2, "width": 0.4, "height": 0.6})] * 3)[0]   # the action on the left
    lw, lh, lx, _ = pixels(left.scene_crop)
    assert abs(lx + lw / 2 - 384) < 10 and abs(lw / lh - 1080 / 1920) < 0.01 and not ffmpeg.needs_background(lw, lh, 1080, 1920)
