"""Still frames of a clip for the model to look at (layout, ad blur, review)."""
from __future__ import annotations

from pathlib import Path

from .. import proc

FRAME_WIDTH = 1280
FRAME_TIMEOUT_S = 120
PROBE_TIMEOUT_S = 60


def sample_times(start_s: float, end_s: float) -> list[float]:
    """Five instants: just after the start, a quarter, the middle, three quarters, just before the end."""
    d = end_s - start_s
    return [start_s + min(0.5, d / 10), start_s + d * 0.25, start_s + d * 0.5, start_s + d * 0.75, end_s - min(0.5, d / 10)]


def extract(src: Path, times: list[float], out_dir: Path, width: int = FRAME_WIDTH) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, t in enumerate(times):
        path = out_dir / f"frame{i}.jpg"
        done = proc.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-ss", f"{t:.3f}", "-i", str(src),
                               "-frames:v", "1", "-vf", f"scale={width}:-2", "-q:v", "3", str(path)], FRAME_TIMEOUT_S, what="ffmpeg (a frame)")
        if done.returncode != 0 or not path.exists():
            raise RuntimeError(f"could not take a frame at {t:.1f} s: {done.stderr.strip()[-300:]}")
        paths.append(path)
    return paths


def shrink(paths: list[Path], out_dir: Path, width: int) -> list[Path]:
    """Copies of the frames `width` pixels wide (the model sees enough of a webcam or a banner on a smaller picture)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out = []
    for i, src in enumerate(paths):
        path = out_dir / f"frame{i}.jpg"
        done = proc.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(src), "-vf", f"scale={width}:-2",
                         "-q:v", "3", str(path)], FRAME_TIMEOUT_S, what="ffmpeg (a smaller frame)")
        if done.returncode != 0 or not path.exists():
            raise RuntimeError(f"could not make a smaller copy of {Path(src).name}: {done.stderr.strip()[-300:]}")
        out.append(path)
    return out


def size(path: Path) -> tuple[int, int]:
    done = proc.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(path)],
                    PROBE_TIMEOUT_S, what="ffprobe")
    out = done.stdout.strip()
    if done.returncode != 0 or "," not in out:
        raise RuntimeError(f"could not read the size of {Path(path).name}: {done.stderr.strip()[-300:]}")
    w, h = out.split(",")[:2]
    return int(w), int(h)
