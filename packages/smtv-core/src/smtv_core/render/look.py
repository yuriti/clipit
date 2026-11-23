"""Where the streamer's webcam is, found on the frames on this computer (B12): a model is asked only when this leaves a
doubt.

Measured 23.11 on one 26-minute recording: the layout took 12 model calls and half of all its tokens, while the webcam
of a stream sits in one place for the whole recording. So, from a few frames taken at different moments:

1. faces (faces.py, YuNet). The streamer's face in a webcam box stays in one place: a face at the same spot in most
   frames is the candidate;
2. the box around it: the webcam's picture (a room) barely changes from frame to frame, the game around it changes a
   lot. Going out from the face, each side of the box is where that quiet turns sharply into motion; a side with no
   such line is the edge of the picture;
3. the box must look like a webcam (shape, size, the face inside it at a sensible size), else it is a doubt;
4. camera.refine puts it on the camera's real edges, inside an overlay frame.

A large face that moves around with no box around it is a camera filling the picture (IRL, «just chatting»): no webcam
box, the clip is the picture around the face. Anything else — no face, two candidates, a box that does not look like a
webcam — is «unsure», and the caller asks the model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import numpy as np

from .. import proc
from . import camera, faces

WORK_W, WORK_H = camera.WORK_W, camera.WORK_H
SAME_X, SAME_Y = 0.04, 0.06       # a face this close to another one (centres, of the frame) is the same face
STEADY = 0.6                      # ... and in at least this share of the frames it stays put
MIN_FACE = 0.03                   # a smaller face (of the frame's height) is too small to tell anything
BIG_FACE = 0.15                   # a face this tall is a camera filling the picture, not a webcam box
QUIET_GAP = 2, 10                 # a side is looked at over these many pixels on each side of the line
JUMP = 4.0                        # outside moves at least this many times more than inside ...
JUMP_MIN = 10.0                   # ... and at least this much (std of grey levels across the frames)
EDGE = 0.012                      # a side this close to the edge of the picture is on it
MAX_AREA = 0.45                   # a webcam box covers less of the picture than this
ASPECT = 0.5, 2.6                 # width / height in pixels of the source: 9:16 to wider than 16:9
FACE_IN_BOX = 0.1, 0.8            # the face's height in the box's height


@dataclass
class Look:
    kind: str                         # overlay | full | none (no webcam: known for this recording) | unsure
    camera: dict | None = None        # overlay: the webcam box, fractions of the frame
    face: dict | None = None          # the streamer's face (the steady one, or the largest), fractions of the frame
    reason: str = ""
    known: bool = False               # the webcam found earlier on this recording, not found again here
    candidates: int = 0               # small faces that stay put: each may be a webcam box the frames could not settle
    faces: list[list[faces.Face]] = field(default_factory=list, repr=False)


def bgr(path: Path) -> np.ndarray:
    """A frame as BGR at the work size."""
    done = proc.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(path), "-vf", f"scale={WORK_W}:{WORK_H}",
                     "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], 60, what="ffmpeg", text=False)
    if done.returncode != 0 or len(done.stdout) != WORK_W * WORK_H * 3:
        raise RuntimeError(f"could not read {Path(path).name}: {done.stderr.decode(errors='replace')[-200:]}")
    return np.frombuffer(done.stdout, dtype=np.uint8).reshape(WORK_H, WORK_W, 3)


def grey(image: np.ndarray) -> np.ndarray:
    return image.astype(np.float32) @ np.array([0.114, 0.587, 0.299], np.float32)


def steady_faces(found: list[list[faces.Face]]) -> list[tuple[dict, float]]:
    """The faces that stay put — (median box, the share of frames it is in) —, the steadiest first."""
    if not found:
        return []
    groups: list[list[faces.Face]] = []
    for f in sorted((f for frame in found for f in frame if f.height >= MIN_FACE), key=lambda f: -f.score):
        cx, cy = f.centre
        for g in groups:
            gx, gy = g[0].centre
            if abs(cx - gx) < SAME_X and abs(cy - gy) < SAME_Y:
                g.append(f)
                break
        else:
            groups.append([f])
    out = []
    for g in groups:
        share = sum(1 for frame in found if any(f in g for f in frame)) / len(found)
        if share >= STEADY:
            out.append(({k: float(np.median([getattr(f, k) for f in g])) for k in ("x", "y", "width", "height")}, share,
                        sum(f.score for f in g)))
    out.sort(key=lambda t: (-t[1], -t[2]))
    return [(box, share) for box, share, _ in out]


def inside(face: dict, box: dict, slack: float = 0.01) -> bool:
    return (box["x"] - slack <= face["x"] and face["x"] + face["width"] <= box["x"] + box["width"] + slack
            and box["y"] - slack <= face["y"] and face["y"] + face["height"] <= box["y"] + box["height"] + slack)


def _profile(std: np.ndarray, columns: bool, a: int, b: int) -> np.ndarray:
    """The motion along one axis: per column (or row) the median over the band [a, b) of the other axis."""
    return np.median(std[a:b, :], axis=0) if columns else np.median(std[:, a:b], axis=1)


def _jump(p: np.ndarray, i: int, outward: int) -> bool:
    """Going out (outward = ±1) at i: quiet inside, motion outside."""
    near, far = QUIET_GAP
    if outward > 0:
        inside, outside = p[max(0, i - far):i - near], p[i + near:i + far]
    else:
        inside, outside = p[i + near:i + far], p[max(0, i - far):i - near]
    return inside.size > 3 and outside.size > 3 and float(outside.mean()) >= max(JUMP_MIN, JUMP * float(inside.mean()))


def box_around(std: np.ndarray, face: dict) -> dict:
    """The box around the face where quiet turns into motion, in fractions of the frame; a side with no such line is
    the edge of the picture."""
    h, w = std.shape
    fx0, fy0 = int(face["x"] * w), int(face["y"] * h)
    fx1, fy1 = int((face["x"] + face["width"]) * w), int((face["y"] + face["height"]) * h)
    fw, fh = max(fx1 - fx0, 1), max(fy1 - fy0, 1)
    cols = _profile(std, True, max(0, fy0 - fh), min(h, fy1 + fh))
    rows = _profile(std, False, max(0, fx0 - fw), min(w, fx1 + fw))
    far = QUIET_GAP[1]
    left = next((x for x in range(fx0 - fw // 2, far, -1) if _jump(cols, x, -1)), 0)
    right = next((x for x in range(fx1 + fw // 2, w - far) if _jump(cols, x, 1)), w)
    top = next((y for y in range(fy0 - fh // 2, far, -1) if _jump(rows, y, -1)), 0)
    bottom = next((y for y in range(fy1 + fh // 2, h - far) if _jump(rows, y, 1)), h)
    return {"x": left / w, "y": top / h, "width": (right - left) / w, "height": (bottom - top) / h}


def doubt(box: dict, face: dict) -> str | None:
    """Why the box does not look like a webcam box, or None."""
    left, top = box["x"] <= EDGE, box["y"] <= EDGE
    right, bottom = box["x"] + box["width"] >= 1 - EDGE, box["y"] + box["height"] >= 1 - EDGE
    if left and right or top and bottom:
        return "no edge of a webcam on two opposite sides"
    if box["width"] * box["height"] > MAX_AREA:
        return f"the box covers {box['width'] * box['height']:.0%} of the picture"
    aspect = box["width"] * camera.WORK_W / max(box["height"] * camera.WORK_H, 1e-6)
    if not ASPECT[0] <= aspect <= ASPECT[1]:
        return f"a box of shape {aspect:.2f} is no webcam"
    share = face["height"] / max(box["height"], 1e-6)
    if not FACE_IN_BOX[0] <= share <= FACE_IN_BOX[1]:
        return f"the face takes {share:.0%} of the box's height"
    if not (box["x"] <= face["x"] and face["x"] + face["width"] <= box["x"] + box["width"] + 1e-3
            and box["y"] <= face["y"] and face["y"] + face["height"] <= box["y"] + box["height"] + 1e-3):
        return "the face is not inside the box"
    return None


def holds(std: np.ndarray, box: dict) -> bool:
    """The frames still show this webcam box: quiet inside and motion outside on most of its sides that are not on the
    edge of the picture (a known webcam checked on a clip where no face was found)."""
    h, w = std.shape
    x0, y0 = round(box["x"] * w), round(box["y"] * h)
    x1, y1 = round((box["x"] + box["width"]) * w), round((box["y"] + box["height"]) * h)
    cols = _profile(std, True, y0, max(y1, y0 + 1))
    rows = _profile(std, False, x0, max(x1, x0 + 1))
    checks = []
    for at, size, p, outward in ((x0, w, cols, -1), (x1, w, cols, 1), (y0, h, rows, -1), (y1, h, rows, 1)):
        if EDGE * size < at < (1 - EDGE) * size:
            checks.append(any(_jump(p, at + d, outward) for d in range(-4, 5)))
    return bool(checks) and 2 * sum(checks) > len(checks)


def motion(images: list[np.ndarray]) -> np.ndarray:
    """How much each pixel changes across the frames (std of grey levels)."""
    return np.stack([grey(i) for i in images]).std(axis=0)


def look(images: list[np.ndarray], known: Sequence[dict] = (), faceless: Sequence[dict] = ()) -> Look:
    """The webcam on these frames (BGR at the work size, taken at different moments). `known`: webcam boxes already
    found on this recording — a steady face inside one of them, or (no face) the same quiet box, is that webcam again;
    `faceless`: those of them the model found on frames with no face at all (an avatar, a camera in the dark): on
    frames with no face either they are the webcam again. Raises faces.FacesUnavailable."""
    found = [faces.detect(i) for i in images]
    steady = steady_faces(found)
    std = None
    for box in known:
        hit = next((f for f, _ in steady if inside(f, box)), None)
        if hit is not None:
            return Look("overlay", camera=box, face=hit, reason="the webcam found before: the face is in it", faces=found, known=True)
    if known and not steady:
        std = motion(images)
        for box in known:
            if holds(std, box):
                return Look("overlay", camera=box, reason="the webcam found before: its box is still there", faces=found, known=True)
        if faceless and not any(found):
            return Look("overlay", camera=faceless[0], reason="the webcam found before on frames with no face: none here either",
                        faces=found, known=True)
    largest = [max(frame, key=lambda f: f.height) for frame in found if frame]
    big = [f for f in largest if f.height >= BIG_FACE]
    big_face = {k: float(np.median([getattr(f, k) for f in big])) for k in ("x", "y", "width", "height")} if big else None
    small = [(f, share) for f, share in steady if f["height"] < BIG_FACE]
    if len(small) > 1:            # two streamers, or a face in the game that stays put: the model tells which is the webcam
        return Look("unsure", face=small[0][0], reason=f"{len(small)} faces stay put: which one is the streamer's", faces=found,
                    candidates=len(small))
    why: str | None = ""
    boxes: list[tuple[dict, dict, float]] = []
    if small:
        std = motion(images) if std is None else std
        for face, share in small:
            box = box_around(std, face)
            why = doubt(box, face)
            if why is None:
                boxes.append((box, face, share))
    if len(boxes) == 1:
        box, face, share = boxes[0]
        return Look("overlay", camera=camera.refine([grey(i) for i in images], box), face=face,
                    reason=f"a face in {share:.0%} of the frames, in a still box", faces=found)
    if 2 * len(big) >= len(images):
        return Look("full", face=big_face, reason=f"a large face in {len(big)} of {len(images)} frames: the camera is the picture",
                    faces=found)
    if small:
        return Look("unsure", face=small[0][0], reason=f"a steady face, but {why}", faces=found, candidates=len(small))
    if not any(found):
        return Look("unsure", reason="no face on the frames", faces=found)
    return Look("unsure", face=big_face, reason="faces, but none that stays in a webcam box", faces=found)
