"""The streamer's webcam as it really is on the frames: the box a model gives is close, not exact.

Found on a real stream (21.11): the model's box reached a few pixels past the camera, so the webcam slot showed a pink
strip of the game under it and the dark edges of the streamer's overlay frame. So the box is checked against the
frames before anything is cut from it:

1. each side of the box is moved to the line where the picture changes sharply in EVERY frame (the camera's outer edge:
   the overlay stays put while the game and the room move), searched a little outside and inside the model's line;
2. from there, inwards, lines of one even colour in every frame are the overlay's frame, not the camera: they are
   skipped (up to FRAME_DEPTH of the box);
3. a small INSET more on each side, so a pixel of the frame or the game never reaches the slot.

A side on the edge of the picture stays there. A side where no edge is clear keeps the model's line plus the inset.
The result never grows past the model's box by more than the search allows outside, and never shrinks below half.
"""
from __future__ import annotations

from smtv_core import proc
from pathlib import Path

import numpy as np

WORK_W, WORK_H = 960, 540         # frames are looked at at this size: 2 px of the 1920x1080 source
OUTSIDE, INSIDE = 0.02, 0.03      # how far past / into the model's line an edge is looked for (of the whole frame)
FRAME_DEPTH = 0.08                # an overlay frame is at most this thick (of the box)
INSET = 0.012                     # and then this much more (of the box, at least 2 px of the work size)
EVEN = 9.0                        # a line of the frame: its pixels differ this little (std of grey levels) ...
STILL = 12.0                      # ... and its mean changes this little from frame to frame
EDGE_MIN = 10.0                   # an edge: the grey step across it, in every frame
AT_BORDER = 0.004                 # a side this close to the edge of the picture is on it


def grey(path: Path) -> np.ndarray:
    """A frame as grey levels at the work size."""
    done = proc.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(path), "-vf", f"scale={WORK_W}:{WORK_H}",
                     "-f", "rawvideo", "-pix_fmt", "gray", "-"], 60, what="ffmpeg", text=False)
    if done.returncode != 0 or len(done.stdout) != WORK_W * WORK_H:
        raise RuntimeError(f"could not read {path.name}: {done.stderr.decode(errors='replace')[-200:]}")
    return np.frombuffer(done.stdout, dtype=np.uint8).reshape(WORK_H, WORK_W).astype(np.float32)


def _lines(frames: list[np.ndarray], side: str, lo: int, hi: int) -> list[np.ndarray]:
    """Each frame turned so that the side's lines are rows, counted inwards from the outside, cut to [lo, hi) across."""
    out = []
    for f in frames:
        g = {"top": f, "bottom": f[::-1], "left": f.T, "right": f.T[::-1]}[side]
        out.append(g[:, lo:hi])
    return out


def _side(frames: list[np.ndarray], side: str, at: int, span: tuple[int, int], size: int, limit: int) -> int:
    """The position (in rows from the outside of the turned frame) where the camera itself starts on this side."""
    turned = _lines(frames, side, *span)
    n = turned[0].shape[0]
    a, b = max(1, at - round(OUTSIDE * limit)), min(n - 1, at + round(INSIDE * limit))
    start = at
    if b > a:
        steps = np.stack([np.abs(t[a:b + 1] - t[a - 1:b]).mean(axis=1) for t in turned])   # the step into row p, per frame
        weakest = steps.min(axis=0)                                                          # an edge must be there in every frame
        # the outermost line that is an edge in every frame: the camera's outer edge, not an edge of the room inside it
        strong = np.nonzero((weakest >= EDGE_MIN) & (weakest >= 2.5 * float(np.median(weakest))))[0]
        if strong.size:
            start = a + int(strong[0])
    return _past_frame(turned, start, size)


def _past_frame(turned: list[np.ndarray], start: int, size: int) -> int:
    """From `start` inwards past the lines of one even, still colour (the overlay's frame), then the inset."""
    q, end = start, min(turned[0].shape[0], start + max(1, round(FRAME_DEPTH * size)))
    while q < end:
        rows = [t[q] for t in turned]
        means = [float(r.mean()) for r in rows]
        if max(float(r.std()) for r in rows) > EVEN or max(means) - min(means) > STILL:
            break
        q += 1
    return q + max(2, round(INSET * size))


def refine(frames: list[np.ndarray], box: dict) -> dict:
    """The model's webcam box (fractions of the frame) moved onto the camera's real edges and inside its frame."""
    x0, y0 = round(box["x"] * WORK_W), round(box["y"] * WORK_H)
    x1, y1 = round((box["x"] + box["width"]) * WORK_W), round((box["y"] + box["height"]) * WORK_H)
    w, h = max(x1 - x0, 1), max(y1 - y0, 1)
    pad_x, pad_y = w // 5, h // 5                       # the middle of the other side: corners of a frame are not edges
    edges = {}
    for side, at, span, size, limit in (
            ("top", y0, (x0 + pad_x, x1 - pad_x), h, WORK_H), ("bottom", WORK_H - y1, (x0 + pad_x, x1 - pad_x), h, WORK_H),
            ("left", x0, (y0 + pad_y, y1 - pad_y), w, WORK_W), ("right", WORK_W - x1, (y0 + pad_y, y1 - pad_y), w, WORK_W)):
        if at <= AT_BORDER * limit:                      # the picture's own edge: only the frame and the inset
            edges[side] = _past_frame(_lines(frames, side, *span), 0, size)
        else:
            edges[side] = _side(frames, side, at, span, size, limit)
    nx0, ny0 = edges["left"], edges["top"]
    nx1, ny1 = WORK_W - edges["right"], WORK_H - edges["bottom"]
    if nx1 - nx0 < w / 2 or ny1 - ny0 < h / 2:           # a "frame" this thick is the picture itself: keep the box, inset only
        ix, iy = max(2, round(INSET * w)), max(2, round(INSET * h))
        nx0, ny0, nx1, ny1 = x0 + ix, y0 + iy, x1 - ix, y1 - iy
    return {"x": round(nx0 / WORK_W, 4), "y": round(ny0 / WORK_H, 4), "width": round((nx1 - nx0) / WORK_W, 4),
            "height": round((ny1 - ny0) / WORK_H, 4)}


def refine_files(paths: list[Path], box: dict) -> dict:
    return refine([grey(Path(p)) for p in paths], box)
