"""The ffmpeg command for one 9:16 clip: source piece → layout → burned captions → H.264/AAC MP4.

Formulas and constants follow the production renderer: the source is normalized to 1920x1080, every slot is a crop
fitted into its box; when the crop's shape differs from the box, the empty area gets a blurred copy of the crop
(boxblur 30:2) and the crop sits in the middle (CONTAIN). Encoding: libx264 superfast CRF 20, High@4.2, GOP 0.5 s, bt709,
AAC 48 kHz stereo. Everything runs on the processor.

Optional details: ad boxes blurred on the normalized source before the layout, a tone over bleeped words, and a
second pass bringing the clip to −14 LUFS.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .. import proc
from ..audio import loudness as loud
from .adblur import filter_chain as blur_chain
from .layout import SLOTS, SOURCE_H, SOURCE_W, H, W, Layout, pixels

FPS = 30


def needs_background(cw: int, ch: int, tw: int, th: int) -> bool:
    scale = min(tw / cw, th / ch)
    return tw - cw * scale > 2 or th - ch * scale > 2


def slot(inp: str, out: str, crop: dict, tw: int, th: int, prefix: str) -> str:
    cw, ch, x, y = pixels(crop)
    c = f"crop={cw}:{ch}:{x}:{y}"
    if not needs_background(cw, ch, tw, th):
        return f"{inp}{c},scale=w={tw}:h={th}:flags=lanczos,setsar=1{out}"
    return ";".join([
        f"{inp}{c}[{prefix}c]",
        f"[{prefix}c]split=2[{prefix}bi][{prefix}fi]",
        f"[{prefix}bi]scale=w={tw}:h={th}:force_original_aspect_ratio=increase:flags=lanczos,crop={tw}:{th},boxblur=30:2,setsar=1[{prefix}b]",
        f"[{prefix}fi]scale=w={tw}:h={th}:force_original_aspect_ratio=decrease:flags=lanczos,setsar=1[{prefix}f]",
        f"[{prefix}b][{prefix}f]overlay=x=(W-w)/2:y=(H-h)/2:shortest=1{out}",
    ])


def layout_filter(inp: str, out: str, layout: Layout) -> str:
    if layout.mode == "scene_only":
        return slot(inp, out, layout.scene_crop, W, H, "s")
    top, bottom = SLOTS[layout.mode]
    return ";".join([
        f"{inp}split=2[cam_in][scene_in]",
        slot("[cam_in]", "[cam]", layout.streamer_crop, W, top, "t"),
        slot("[scene_in]", "[scene]", layout.scene_crop, W, bottom, "b"),
        f"[cam][scene]vstack=inputs=2{out}",
    ])


def _escape_filter_path(path: Path, windows: bool | None = None) -> str:
    """A path as a filter option value inside a filter graph, without quotes: escaped for the option (`\\ ' :`) and
    then for the graph (`\\ ' [ ] , ;`). Quotes would not do: ffmpeg has no way to put `'` inside '…', so a profile
    like C:\\Users\\O'Brien broke every clip. Windows backslashes become `/`, which ffmpeg and libass accept."""
    windows = os.sep == "\\" if windows is None else windows
    text = str(path).replace("\\", "/") if windows else str(path)
    text = re.sub(r"([\\':])", r"\\\1", text)
    return re.sub(r"([\\'\[\],;])", r"\\\1", text)


def filter_graph(layout: Layout, ass: Path | None, fonts_dir: Path | None, fps: int = FPS, blur_boxes=(), bleep: str = "") -> str:
    """blur_boxes: (width, height, x, y) on the 1920x1080 source; bleep: the audio filter of smtv_core.audio.bleep."""
    norm = f"[0:v]fps={fps},scale={SOURCE_W}:{SOURCE_H}:force_original_aspect_ratio=increase:flags=lanczos,crop={SOURCE_W}:{SOURCE_H},setsar=1"
    parts = [f"{norm}[raw];{blur_chain('[raw]', '[src]', list(blur_boxes))}" if blur_boxes else f"{norm}[src]",
             layout_filter("[src]", "[laid]", layout)]
    if ass:
        fonts = f":fontsdir={_escape_filter_path(fonts_dir)}" if fonts_dir else ""
        parts.append(f"[laid]ass=filename={_escape_filter_path(ass)}{fonts}[vout]")
    else:
        parts.append("[laid]null[vout]")
    # The bleep's time t must start at 0 on the clip's first sample.
    parts.append("[0:a]aresample=48000,aformat=channel_layouts=stereo" + (f",asetpts=N/SR/TB,{bleep}" if bleep else "") + "[aout]")
    return ";".join(parts)


def args(src: Path, out: Path, start_s: float, end_s: float, layout: Layout, ass: Path | None = None, fonts_dir: Path | None = None,
         threads: int = 0, blur_boxes=(), bleep: str = "") -> list[str]:
    g = FPS // 2
    return ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-ss", f"{start_s:.3f}", "-to", f"{end_s:.3f}", "-i", str(src),
            "-filter_complex", filter_graph(layout, ass, fonts_dir, blur_boxes=blur_boxes, bleep=bleep), "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "superfast", "-profile:v", "high", "-level:v", "4.2", "-crf", "20", "-maxrate", "10M", "-bufsize", "20M",
            "-g", str(g), "-keyint_min", str(g), "-sc_threshold", "0", "-bf", "2", "-flags", "+cgop", "-threads:v", str(threads),
            "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-map_metadata", "-1", "-movflags", "+faststart", str(out)]


class RenderError(Exception):
    pass


def reason(stderr: str, size: int = 600) -> str:
    """ffmpeg's own words, cut to `size`: its first lines name the cause, the last ones only the knock-on failures."""
    text = (stderr or "").strip()
    if len(text) <= size:
        return text
    return text[: size * 2 // 3].rstrip() + " … " + text[-size // 3:].lstrip()


def render(src: Path, out: Path, start_s: float, end_s: float, layout: Layout, ass: Path | None = None, fonts_dir: Path | None = None, *,
           blur_boxes=(), bleep: str = "", loudness: bool = False) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.stem + ".part" + out.suffix)
    try:
        done = proc.run(args(src, tmp, start_s, end_s, layout, ass, fonts_dir, blur_boxes=blur_boxes, bleep=bleep),
                        proc.limit(end_s - start_s, floor_s=600, per_s=20), what=f"ffmpeg on {out.name}")
    except proc.TimedOut as e:
        tmp.unlink(missing_ok=True)
        raise RenderError(str(e)) from e
    if done.returncode != 0:
        tmp.unlink(missing_ok=True)
        raise RenderError(f"ffmpeg failed on {out.name}: {reason(done.stderr)}")
    if loudness:
        try:
            loud.normalize(tmp, end_s - start_s)
        except loud.LoudnessError as e:
            tmp.unlink(missing_ok=True)
            raise RenderError(str(e)) from e
    tmp.replace(out)
    return out
