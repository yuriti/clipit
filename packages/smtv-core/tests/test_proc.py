"""Stage 15: ffmpeg and yt-dlp never hang a job; a file's length and size come from ffmpeg itself (smtv_core.proc)."""
import os
import shutil
import subprocess
import sys
import time

import pytest

from smtv_core import proc
from smtv_core.audio import loudness
from smtv_core.render import ffmpeg, frames
from smtv_core.render.layout import DEFAULT


def test_a_program_that_hangs_is_stopped_with_its_children(tmp_path):
    pidfile = tmp_path / "child.pid"
    # the program starts a child that would outlive it; both go when the limit is reached
    script = f"import subprocess,sys,time; c=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); open(r'{pidfile}','w').write(str(c.pid)); time.sleep(60)"
    t = time.monotonic()
    with pytest.raises(proc.TimedOut, match="hanging tool did not finish in 1 s"):
        proc.run([sys.executable, "-c", script], 1.0, what="hanging tool")
    assert time.monotonic() - t < 15
    child = int(pidfile.read_text(encoding="utf-8"))
    time.sleep(0.3)
    # Windows: no such process is OSError «invalid parameter» (and os.kill would end a living one, so it still fails)
    with pytest.raises(OSError if sys.platform == "win32" else ProcessLookupError):
        os.kill(child, 0)


def test_a_program_that_finishes_gives_its_output_and_code():
    done = proc.run([sys.executable, "-c", "import sys; print('out'); sys.stderr.write('err'); sys.exit(3)"], 30)
    assert (done.returncode, done.stdout.strip(), done.stderr) == (3, "out", "err")


def test_limits_grow_with_the_media():
    assert proc.limit(10) == 300 and proc.limit(100) == 1000 and proc.limit(60, floor_s=600, per_s=20) == 1200


def hang(*a, **kw):
    raise proc.TimedOut("ffmpeg did not finish in 1 s and was stopped")


def test_render_frames_and_loudness_turn_a_hang_into_their_own_error(tmp_path, monkeypatch):
    monkeypatch.setattr(proc, "run", hang)
    out = tmp_path / "clip.mp4"
    (tmp_path / "clip.part.mp4").write_bytes(b"half")
    with pytest.raises(ffmpeg.RenderError, match="did not finish"):
        ffmpeg.render(tmp_path / "src.mp4", out, 0, 10, DEFAULT)
    assert not (tmp_path / "clip.part.mp4").exists() and not out.exists()
    with pytest.raises(proc.TimedOut):
        frames.extract(tmp_path / "src.mp4", [1.0], tmp_path / "frames")
    with pytest.raises(proc.TimedOut):
        frames.size(tmp_path / "f.jpg")
    with pytest.raises(loudness.LoudnessError, match="did not finish"):
        loudness.normalize(out, 10)


def test_an_unreadable_frame_size_is_an_error_not_a_crash_on_split(tmp_path, monkeypatch):
    import subprocess
    monkeypatch.setattr(proc, "run", lambda cmd, t, **kw: subprocess.CompletedProcess(cmd, 1, "", "moov atom not found"))
    with pytest.raises(RuntimeError, match="moov atom not found"):
        frames.size(tmp_path / "f.jpg")


def test_output_that_is_not_utf8_does_not_break_a_finished_program():
    done = proc.run([sys.executable, "-c", "import sys; sys.stderr.buffer.write(b'\\xff\\xfe bad'); sys.exit(1)"], 30)
    assert done.returncode == 1 and "bad" in done.stderr


# --- the length and picture size, from ffmpeg itself (no ffprobe) ------------------------------------------------------

VIDEO_LOG = """Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'stream.mp4':
  Metadata:
    major_brand     : isom
  Duration: 01:02:03.45, start: 0.000000, bitrate: 5124 kb/s
  Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(tv, bt709, progressive), 1920x1080 [SAR 1:1 DAR 16:9], 4956 kb/s, 60 fps, 60 tbr, 15360 tbn (default)
  Stream #0:1[0x2](und): Audio: aac (LC) (mp4a / 0x6134706D), 48000 Hz, stereo, fltp, 160 kb/s (default)
At least one output file must be specified
"""


def test_the_length_and_size_are_read_from_what_ffmpeg_prints():
    found = proc.read_probe(VIDEO_LOG)
    assert found.duration_s == pytest.approx(3723.45) and found.size == (1920, 1080)
    # a codec tag (0x31637661) is not a size; an audio-only file has none; an unknown length is None
    audio = proc.read_probe("  Duration: 00:00:07.00, start: 0.0\n  Stream #0:0: Audio: mp3, 44100 Hz, stereo\n")
    assert audio.duration_s == 7.0 and audio.size is None
    live = proc.read_probe("  Duration: N/A, start: 0.0\n  Stream #0:0: Video: h264 (Main), yuv420p, 1080x1920, 30 fps\n")
    assert live.duration_s is None and live.size == (1080, 1920)
    image = proc.read_probe("  Duration: 00:00:00.04, start: 0.0\n  Stream #0:0: Video: mjpeg (Baseline), yuvj420p(pc), 640x360, 25 fps\n")
    assert image.size == (640, 360)
    assert proc.read_probe("x.mp4: Invalid data found when processing input\n") == proc.Probe(None, None, "x.mp4: Invalid data found when processing input\n")


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="no ffmpeg here")
def test_a_real_ffmpeg_reads_the_length_and_size_of_a_file_it_made(tmp_path):
    out = tmp_path / "v.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "color=c=red:s=320x240:d=2",
                    "-f", "lavfi", "-i", "anullsrc", "-shortest", "-c:v", "libx264", str(out)], check=True, timeout=120)
    found = proc.probe(str(out), 30)
    assert found.size == (320, 240) and found.duration_s == pytest.approx(2.0, abs=0.2)
