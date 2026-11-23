"""The 9:16 layout of a clip: which part of the source goes where.

scene_only                  one crop fills 1080x1920
streamer_scene_split        webcam 1080x640 on top, scene 1080x1280 below
streamer_scene_split_equal  webcam 1080x960 on top, scene 1080x960 below

Crops are fractions of the source frame. The model proposes them (fit/layout-prompt.txt); validate() turns its answer
into a layout and keeps the streamer's camera in the clip whenever one is visible.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

W, H = 1080, 1920
SOURCE_W, SOURCE_H = 1920, 1080      # every source is first scaled and cropped to this
FULL_CAMERA_AREA = 0.6               # a webcam this large is shown alone
SLOTS = {"streamer_scene_split": (640, 1280), "streamer_scene_split_equal": (960, 960)}
FULL = {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}


class LayoutError(ValueError):
    pass


@dataclass(frozen=True)
class Layout:
    mode: str                        # scene_only | streamer_scene_split | streamer_scene_split_equal
    scene_crop: dict
    streamer_crop: dict | None = None

    def as_dict(self) -> dict:
        return {"mode": self.mode, "scene_crop": self.scene_crop, "streamer_crop": self.streamer_crop}


DEFAULT = Layout("scene_only", FULL)


def _rect(r) -> dict:
    if not isinstance(r, dict) or set(r) != {"x", "y", "width", "height"} or any(type(v) not in (int, float) or not math.isfinite(v) for v in r.values()):
        raise LayoutError("rectangle_invalid")
    if min(r["x"], r["y"]) < 0 or min(r["width"], r["height"]) <= 0 or r["x"] + r["width"] > 1.0001 or r["y"] + r["height"] > 1.0001:
        raise LayoutError("rectangle_out_of_bounds")
    return {k: float(v) for k, v in r.items()}


def validate(a) -> Layout:
    """A model answer → Layout. The streamer's camera is never hidden: a large one is shown alone, a small one on top."""
    if not isinstance(a, dict) or a.get("layout") not in ("streamer_only", "scene_only", "streamer_scene_split", "streamer_scene_split_equal"):
        raise LayoutError("mode_invalid")
    for key in ("webcam_region", "streamer_crop", "scene_crop"):
        if a.get(key) is not None:
            _rect(a[key])
    mode, camera = a["layout"], a.get("webcam_region")
    if mode == "scene_only" and camera is not None:
        streamer = a.get("streamer_crop") or camera
        if camera["width"] * camera["height"] >= FULL_CAMERA_AREA:
            return Layout("scene_only", _rect(streamer))
        return Layout("streamer_scene_split", _rect(a.get("scene_crop")), _rect(streamer))
    if mode in ("streamer_only", "scene_only"):
        return Layout("scene_only", _rect(a.get("streamer_crop" if mode == "streamer_only" else "scene_crop")))
    return Layout(mode, _rect(a.get("scene_crop")), _rect(a.get("streamer_crop")))


def pixels(r: dict) -> tuple[int, int, int, int]:
    """(width, height, x, y) on the 1920x1080 normalized source, clamped inside it."""
    x = min(max(math.floor(r["x"] * SOURCE_W), 0), SOURCE_W - 1)
    y = min(max(math.floor(r["y"] * SOURCE_H), 0), SOURCE_H - 1)
    w = min(max(math.ceil(r["width"] * SOURCE_W), 1), SOURCE_W - x)
    h = min(max(math.ceil(r["height"] * SOURCE_H), 1), SOURCE_H - y)
    return w, h, x, y


# --- a steady choice (stage 14) ---------------------------------------------------------------------------
# Asked again, a model gave another layout for the same clip (20.11: split, then split_equal) and, every time, other
# crops (21.11, five asks of one clip: the height of the streamer crop 0.20–0.28, the width of the scene crop 0.47–0.66),
# while the webcam it found stayed the same to 0.001. What it sees is steady; how it composes is not — the prompt leaves
# that choice open, and Codex has no temperature to turn down. So the layout is put to a vote: several answers, the
# layout most of them chose (a tie goes by PREFERENCE), every edge of a crop the median of those answers, snapped
# outwards to a grid of SNAP. The webcam is in the clip when at least half of the answers saw one.
# Measured on the same clip (21.11, Codex): one model answers split or split_equal for the same frames about 3 : 7, so a
# majority of three still flipped the layout once in three tries. The two splits differ only in the height of the webcam
# slot, so when the answers do not agree on it the slot the webcam fills best decides (fewest blurred bars), and the crops
# are the median of every split answer: a clip whose answers disagree gets the same layout every time.
# The crops themselves: the answers agree on where the action and the face are (the centres of their crops moved by
# ±0.02) but not on how close to go (the width of the scene crop 0.47–0.70). So in a split the model gives the centre and
# the size follows a rule (steady_split): the largest rectangle of the slot's own shape — it fills the slot, no blurred
# bars — inside the webcam for the streamer, and beside the webcam for the scene, so the streamer is not seen twice.

PREFERENCE = ("streamer_scene_split", "streamer_scene_split_equal", "streamer_only", "scene_only")
SNAP = 0.01
CENTRE_SNAP = 0.05       # the centre of a crop in a split moves in steps of 5 % of the frame: the answers' ±0.02 falls into one


def _median(values: list[float]) -> float:
    s = sorted(values)
    mid = len(s) // 2
    return s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2


def median_rect(rects: list[dict], outwards: bool = True) -> dict:
    """Each edge the median of the rectangles' edges, snapped to SNAP — outwards (a crop keeps what it showed) or to the
    nearest step (the webcam: no strip of the game beside it) — and kept inside the frame."""
    lo, hi = (math.floor, math.ceil) if outwards else (round, round)
    eps = 1e-6 if outwards else 0.0
    left = lo(_median([r["x"] for r in rects]) / SNAP + eps) * SNAP
    top = lo(_median([r["y"] for r in rects]) / SNAP + eps) * SNAP
    right = hi(_median([r["x"] + r["width"] for r in rects]) / SNAP - eps) * SNAP
    bottom = hi(_median([r["y"] + r["height"] for r in rects]) / SNAP - eps) * SNAP
    left, top, right, bottom = max(0.0, left), max(0.0, top), min(1.0, right), min(1.0, bottom)
    return {"x": round(left, 4), "y": round(top, 4), "width": round(max(right - left, SNAP), 4), "height": round(max(bottom - top, SNAP), 4)}


def _kind(answer: dict, layout: Layout) -> str:
    """The choice an answer made: a split, the streamer alone, or the scene alone."""
    if layout.mode != "scene_only":
        return layout.mode
    return "streamer_only" if answer.get("webcam_region") is not None else "scene_only"


def _centre(rects: list[dict]) -> tuple[float, float]:
    snap = lambda v: round(v / CENTRE_SNAP) * CENTRE_SNAP  # noqa: E731
    return snap(_median([r["x"] + r["width"] / 2 for r in rects])), snap(_median([r["y"] + r["height"] / 2 for r in rects]))


def fit_inside(bounds: dict, aspect: float, centre: tuple[float, float]) -> dict:
    """The largest rectangle of `aspect` (width / height in source pixels) inside `bounds`, as close to `centre` as it
    fits, its edges on the SNAP grid."""
    bw, bh = bounds["width"] * SOURCE_W, bounds["height"] * SOURCE_H
    w, h = (bh * aspect, bh) if bw / bh > aspect else (bw, bw / aspect)
    w, h = w / SOURCE_W, h / SOURCE_H
    x = min(max(centre[0] - w / 2, bounds["x"]), bounds["x"] + bounds["width"] - w)
    y = min(max(centre[1] - h / 2, bounds["y"]), bounds["y"] + bounds["height"] - h)
    snap = lambda v: round(round(v / SNAP) * SNAP, 4)  # noqa: E731
    x0, y0 = max(snap(x), round(bounds["x"], 4)), max(snap(y), round(bounds["y"], 4))
    x1 = min(snap(x + w), round(bounds["x"] + bounds["width"], 4))
    y1 = min(snap(y + h), round(bounds["y"] + bounds["height"], 4))
    return {"x": x0, "y": y0, "width": round(max(x1 - x0, SNAP), 4), "height": round(max(y1 - y0, SNAP), 4)}


def cover(crop: dict, aspect: float = W / H) -> dict:
    """The crop grown to the shape `aspect` around its own centre, as large as it must be to hold the crop and no larger
    than the picture (then the largest such rectangle, shifted to stay inside): a person filling the frame fills the
    9:16 clip, with no blurred bars above and below (stage 15)."""
    cw, ch = crop["width"] * SOURCE_W, crop["height"] * SOURCE_H
    w, h = (cw, cw / aspect) if cw / ch > aspect else (ch * aspect, ch)
    shrink = min(1.0, SOURCE_W / w, SOURCE_H / h)
    w, h = w * shrink / SOURCE_W, h * shrink / SOURCE_H
    cx, cy = crop["x"] + crop["width"] / 2, crop["y"] + crop["height"] / 2
    x = min(max(cx - w / 2, 0.0), 1.0 - w)
    y = min(max(cy - h / 2, 0.0), 1.0 - h)
    return {"x": round(x, 4), "y": round(y, 4), "width": round(w, 4), "height": round(h, 4)}


def beside(camera: dict) -> dict:
    """The largest part of the frame left, right, above or below the webcam (the whole frame when it fills it)."""
    right, bottom = camera["x"] + camera["width"], camera["y"] + camera["height"]
    sides = [{"x": 0.0, "y": 0.0, "width": camera["x"], "height": 1.0}, {"x": right, "y": 0.0, "width": 1.0 - right, "height": 1.0},
             {"x": 0.0, "y": 0.0, "width": 1.0, "height": camera["y"]}, {"x": 0.0, "y": bottom, "width": 1.0, "height": 1.0 - bottom}]
    best = max(sides, key=lambda r: r["width"] * r["height"])
    return best if best["width"] * best["height"] >= 0.25 else FULL


def steady_split(mode: str, camera: dict, scene_crops: list[dict], streamer_crops: list[dict]) -> Layout:
    """A split from the webcam, the slot shapes and the centres the answers gave."""
    top, bottom = SLOTS[mode]
    scene_bounds = beside(camera)
    scene = fit_inside(scene_bounds, W / bottom, _centre([_clip(r, scene_bounds) for r in scene_crops]))
    streamer = fit_inside(camera, W / top, _centre([_clip(r, camera) for r in streamer_crops]))
    return Layout(mode, scene, streamer)


def _clip(r: dict, bounds: dict) -> dict:
    """`r` cut to `bounds`; `bounds` itself when they do not meet."""
    x0, y0 = max(r["x"], bounds["x"]), max(r["y"], bounds["y"])
    x1, y1 = min(r["x"] + r["width"], bounds["x"] + bounds["width"]), min(r["y"] + r["height"], bounds["y"] + bounds["height"])
    return {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0} if x1 > x0 and y1 > y0 else bounds


WEBCAM_INSET = 0.03       # of the webcam box on each side, when its real edges could not be looked at


def inset(box: dict, share: float = WEBCAM_INSET) -> dict:
    dx, dy = box["width"] * share, box["height"] * share
    return {"x": round(box["x"] + dx, 4), "y": round(box["y"] + dy, 4), "width": round(box["width"] - 2 * dx, 4),
            "height": round(box["height"] - 2 * dy, 4)}


def _inside(camera: dict, refine) -> dict:
    """The webcam box moved inside the camera itself: by its real edges when they can be looked at, else by a margin."""
    if refine is not None:
        try:
            found = refine(camera)
            if found and found["width"] >= camera["width"] / 2 and found["height"] >= camera["height"] / 2:
                return found
        except Exception:  # noqa: BLE001 — no frames to look at: the margin keeps the slot clean anyway
            pass
    return inset(camera)


def best_split(camera: dict) -> str:
    """The split whose webcam slot is closest in shape to the webcam itself (in pixels of the 1920x1080 source)."""
    aspect = camera["width"] * SOURCE_W / max(camera["height"] * SOURCE_H, 1e-6)
    return min(SLOTS, key=lambda m: (abs(math.log(aspect / (W / SLOTS[m][0]))), PREFERENCE.index(m)))


def vote(answers: list, refine=None) -> tuple[Layout, dict | None, list[str]]:
    """(layout, webcam region or None, the choice of each usable answer). Raises LayoutError when none is usable.
    `refine` moves the voted webcam box onto the camera's real edges (render/camera.py); without it the box is only
    pulled in by WEBCAM_INSET, so no strip of a frame or of the game reaches the webcam slot."""
    usable = []
    for a in answers:
        try:
            usable.append((a, validate(a)))
        except LayoutError:
            continue
    if not usable:
        raise LayoutError("no_usable_answer")
    kinds = [_kind(a, lay) for a, lay in usable]
    cams = [_rect(a["webcam_region"]) for a, _ in usable if a.get("webcam_region") is not None]
    camera = median_rect(cams, outwards=False) if 2 * len(cams) >= len(usable) else None
    if camera is not None:
        camera = _inside(camera, refine)
    allowed = [k for k in PREFERENCE if camera is None or k != "scene_only"]   # a camera most answers saw is never left out
    winner = min((k for k in set(kinds) if k in allowed), key=lambda k: (-kinds.count(k), PREFERENCE.index(k)), default=None)
    if winner is None:            # the camera's answers were all unusable as a layout: put it on top of the whole frame
        return Layout("streamer_scene_split", FULL, camera), camera, kinds
    splits = {"streamer_scene_split", "streamer_scene_split_equal"}
    if winner in splits and camera is not None:
        if splits <= set(kinds):
            winner = best_split(camera)
        chosen = [lay for k, (_, lay) in zip(kinds, usable) if k in splits]
        return steady_split(winner, camera, [lay.scene_crop for lay in chosen], [lay.streamer_crop for lay in chosen]), camera, kinds
    chosen = [lay for k, (_, lay) in zip(kinds, usable) if k == winner]
    scene = median_rect([lay.scene_crop for lay in chosen])
    # one picture fills the clip — the streamer alone, or the game when there is no webcam: the crop takes the clip's
    # shape around the model's centre, no narrow band on a blurred background (stage 15)
    scene = cover(scene)
    streamer = median_rect([lay.streamer_crop for lay in chosen]) if chosen[0].streamer_crop is not None else None
    return Layout(chosen[0].mode, scene, streamer), camera, kinds


# --- a layout from the frames themselves (B12) ------------------------------------------------------------------
# The webcam found on this computer (look.py) gives the same layouts the vote did, without a model call: the split
# whose slot fits the webcam best (best_split — the vote's own tie-break), the streamer crop around the face, the scene
# crop the largest of the slot's shape beside the webcam, around the middle of the picture (a game keeps its action in
# the middle); one picture — a camera filling the frame, or no webcam — around the face, else the middle.


def _point(cx: float, cy: float) -> dict:
    return {"x": max(0.0, cx - 0.005), "y": max(0.0, cy - 0.005), "width": 0.01, "height": 0.01}


def from_frames(camera: dict | None, face: dict | None) -> Layout:
    """The layout for a webcam box (None: no webcam box) and the streamer's face (None: not seen)."""
    if camera is not None:
        mode = best_split(camera)
        fx, fy = (face["x"] + face["width"] / 2, face["y"] + face["height"] / 2) if face else \
            (camera["x"] + camera["width"] / 2, camera["y"] + camera["height"] / 2)
        return steady_split(mode, camera, [_point(0.5, 0.5)], [_point(fx, fy)])
    cx = face["x"] + face["width"] / 2 if face else 0.5
    return Layout("scene_only", cover({"x": max(0.0, cx - 0.005), "y": 0.0, "width": 0.01, "height": 1.0}))
