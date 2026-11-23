"""Ad blur: sponsor overlays, betting offers and promo codes are blurred for the whole clip.

The model looks at five frames (fit/banner-prompt.txt) and returns one fixed box per advertising slot, in the pixels of
the frames it was shown. validate_answer() checks the answer and turns each box into fractions of the frame, padded by
3 % of its own size per side. The renderer blurs these rectangles on the normalized 1920x1080 source, before the layout
crops it, so a banner is blurred wherever it ends up in the 9:16 frame.
"""
from __future__ import annotations

import math

from .layout import SOURCE_H, SOURCE_W

MAX_REGIONS = 8
FRAMES = 5
PAD = 0.03
BLUR_RADIUS_PX = 20


class AdBlurError(ValueError):
    pass


def _number(v) -> bool:
    return type(v) in (int, float) and math.isfinite(v)


def validate_answer(answer, width: int, height: int) -> list[dict]:
    """A model answer → [{'id', 'label', 'confidence', 'needs_review', 'rect': fractions of the frame}]. Raises AdBlurError.

    Every region is blurred, ambiguous ones too: nobody reviews them, and a blurred corner costs less than a shown ad."""
    if not isinstance(answer, dict) or not isinstance(answer.get("regions"), list) or len(answer["regions"]) > MAX_REGIONS:
        raise AdBlurError("response_invalid")
    regions, ids = [], set()
    for item in answer["regions"]:
        if not isinstance(item, dict):
            raise AdBlurError("region_invalid")
        rid, label, confidence = item.get("id"), item.get("label"), item.get("confidence")
        if (not isinstance(rid, str) or not 1 <= len(rid) <= 80 or rid in ids or not isinstance(label, str) or len(label) > 500
                or not _number(confidence) or not 0 <= confidence <= 1 or type(item.get("needs_review")) is not bool):
            raise AdBlurError("region_invalid")
        ids.add(rid)
        observed = item.get("observed_frames")
        if not isinstance(observed, list) or not observed or any(type(i) is not int or not 0 <= i < FRAMES for i in observed):
            raise AdBlurError("evidence_invalid")
        b = item.get("box")
        if (not isinstance(b, dict) or set(b) != {"x", "y", "width", "height"} or not all(_number(v) for v in b.values())
                or min(b["x"], b["y"]) < 0 or min(b["width"], b["height"]) <= 0 or b["x"] + b["width"] > width or b["y"] + b["height"] > height):
            raise AdBlurError("box_invalid")
        x = max(0, b["x"] - PAD * b["width"]) / width
        y = max(0, b["y"] - PAD * b["height"]) / height
        right = min(width, b["x"] + (1 + PAD) * b["width"]) / width
        bottom = min(height, b["y"] + (1 + PAD) * b["height"]) / height
        regions.append({"id": rid, "label": label, "confidence": confidence, "needs_review": item["needs_review"],
                        "rect": {"x": x, "y": y, "width": right - x, "height": bottom - y}})
    return regions


def to_source_pixels(rect: dict, frame_w: int, frame_h: int) -> tuple[int, int, int, int] | None:
    """(width, height, x, y) of a frame-fraction rectangle on the 1920x1080 normalized source, which is the frame scaled to
    cover 1920x1080 and cropped in the middle. None when the rectangle falls outside that crop."""
    scale = max(SOURCE_W / frame_w, SOURCE_H / frame_h)
    ox, oy = (frame_w * scale - SOURCE_W) / 2, (frame_h * scale - SOURCE_H) / 2
    left = max(0, math.floor(rect["x"] * frame_w * scale - ox))
    top = max(0, math.floor(rect["y"] * frame_h * scale - oy))
    right = min(SOURCE_W, math.ceil((rect["x"] + rect["width"]) * frame_w * scale - ox))
    bottom = min(SOURCE_H, math.ceil((rect["y"] + rect["height"]) * frame_h * scale - oy))
    if right - left < 1 or bottom - top < 1:
        return None
    return right - left, bottom - top, left, top


def blur(width: int, height: int) -> str:
    """boxblur for a region: radius 20, smaller for a thin region. ffmpeg wants a radius below half of each plane, and
    the chroma planes of yuv420p are half the luma one rounded up: a 238×77 banner took 19 on chroma and ffmpeg refused
    it (allowed < 19), so the whole clip failed (stage 15). The production formula (vod/recap.py)."""
    luma = max(1, min(BLUR_RADIUS_PX, width // 2 - 1, height // 2 - 1))
    chroma = max(0, min(luma, (width + 1) // 2 // 2 - 1, (height + 1) // 2 // 2 - 1))   # 0: no chroma blur on a tiny box
    return f"boxblur={luma}:1" if chroma == luma else f"boxblur={luma}:1:{chroma}:1"


def filter_chain(inp: str, out: str, boxes: list[tuple[int, int, int, int]]) -> str:
    """The filter that blurs `boxes` (width, height, x, y) on `inp`; a plain pass-through without boxes."""
    if not boxes:
        return f"{inp}null{out}"
    parts, cur = [], inp
    for i, (w, h, x, y) in enumerate(boxes):
        nxt = out if i == len(boxes) - 1 else f"[ad{i + 1}]"
        parts += [f"{cur}split=2[ad{i}base][ad{i}crop]",
                  f"[ad{i}crop]crop={w}:{h}:{x}:{y},{blur(w, h)}[ad{i}blur]",
                  f"[ad{i}base][ad{i}blur]overlay={x}:{y}{nxt}"]
        cur = nxt
    return ";".join(parts)
