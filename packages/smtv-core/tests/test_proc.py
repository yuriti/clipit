"""Stage 15: ffmpeg, ffprobe and yt-dlp never hang a job (smtv_core.proc)."""
import os
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
