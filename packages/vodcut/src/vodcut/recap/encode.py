"""The recap's video: the cold open and every part encoded on their own, then joined; the cover.

Ported from production (`vod/recap.py`, render stage). Production encodes HEVC on NVENC in Docker on the PC; here:
- H.264 on the processor, `libx264 veryfast crf 21` (production's fallback), at 30 frames a second — half the frames of
  a 60 fps stream, half the processor time; YouTube plays a 30 fps recap as well;
- H.264 on NVENC (`h264_nvenc p5`, 60 fps) when the computer has an NVIDIA card ffmpeg can use (probed once).
- `-filter_complex_threads 1`: production measured that an ad patch's overlay sliced over every core cost more than the
  blur itself, and one filter thread halved the part encodes with blur (04.11).
- `-reinit_filter 0`: Twitch pieces change frame properties mid-file, and a rebuilt graph restarts the timestamps.
- the webcam branch of a shot sees only the frames of its own spans, plus one frame every half second and the frame
  before each shot, so the overlay never holds the frames in between (production, 01.11: 23 GB for one part without it).
No captions are burned in (production, 24.10: the recap reads better without them), no chapter labels on the picture.

A part already encoded by exactly the same command is kept (its `.json` key), so a stopped recap goes on where it was.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Callable

from smtv_core import proc
from smtv_core.audio import bleep
from smtv_core.render.adblur import blur as blur_filter

from .edit import END_FADE_S, HEIGHT, JOIN_FADE_S, PART_FADE_S, WIDTH, Timeline

FOCUS_HEIGHT = 900
LEAD_S = 0.02


class EncodeError(RuntimeError):
    pass


def _ffmpeg(argv: list[str], *, timeout: float = 3600, **_run_kwargs):
    """Same call shape as subprocess.run (capture_output/text are accepted and ignored: proc.run always captures UTF-8).
    One ffmpeg through proc.run: a time limit that stops it with its children, UTF-8 output whatever the code page,
    no console window on Windows. A program that hangs is an EncodeError like any other failure."""
    try:
        return proc.run(argv, timeout, what=f"ffmpeg ({Path(argv[-1]).name})")
    except proc.TimedOut as e:
        raise EncodeError(str(e)) from None


def concat_line(path: Path) -> str:
    """One line of ffmpeg's concat list. Inside '…' a quote is written as '\\'' (close, escaped quote, open): a folder
    like «O'Brien» would otherwise break the join of every recap."""
    return "file '" + path.resolve().as_posix().replace("'", "'\\''") + "'\n"


@lru_cache(maxsize=1)
def encoder() -> str:
    """'nvenc' when ffmpeg can encode on an NVIDIA card here (a real one-frame encode, not just the build's list), else 'cpu'."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return "cpu"
    try:
        listed = proc.run([ffmpeg, "-hide_banner", "-encoders"], 20, what="ffmpeg -encoders").stdout
        if "h264_nvenc" not in listed:
            return "cpu"
        probe = proc.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-f", "lavfi", "-i", "color=black:s=256x144:d=0.2",
                          "-c:v", "h264_nvenc", "-f", "null", "-"], 30, what="ffmpeg (nvenc probe)")
        return "nvenc" if probe.returncode == 0 else "cpu"
    except (OSError, proc.TimedOut):
        return "cpu"


def fps(kind: str) -> int:
    return 60 if kind == "nvenc" else 30


def video_args(kind: str) -> list[str]:
    rate = fps(kind)
    if kind == "nvenc":
        codec = ["-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq", "-rc", "vbr", "-cq", "23", "-b:v", "0", "-spatial-aq", "1"]
    else:
        codec = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "21"]
    return [*codec, "-maxrate", "10M", "-bufsize", "20M", "-profile:v", "high", "-g", str(rate * 2), "-r", str(rate), "-pix_fmt", "yuv420p",
            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv"]


AUDIO = ["-c:a", "pcm_s16le", "-ar", "48000", "-ac", "2"]
HEAD = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
FILTER_THREADS = ["-filter_complex_threads", "1"]
NO_REINIT = ["-reinit_filter", "0"]


def between(spans, digits=3) -> str:
    return "+".join(f"between(t,{a:.{digits}f},{b:.{digits}f})" for a, b in spans)


def blur_chain(inp: str, out: str, boxes, tag: str) -> list[str]:
    """Ad boxes (width, height, x, y) on the 1920×1080 picture blurred; each box its own crop → boxblur → overlay."""
    chains, cur = [], inp
    for i, (w, h, x, y) in enumerate(boxes):
        nxt = out if i == len(boxes) - 1 else f"[{tag}{i + 1}]"
        chains.append(f"{cur}split=2[{tag}b{i}][{tag}c{i}];[{tag}c{i}]crop={w}:{h}:{x}:{y}:exact=1,{blur_filter(w, h)}[{tag}p{i}];"
                      f"[{tag}b{i}][{tag}p{i}]overlay=x={x}:y={y}:format=yuv420,format=yuv420p{nxt}")
        cur = nxt
    return chains if boxes else [f"{inp}null{out}"]


def part_filter(part: dict, *, offset: float, last: bool, rate: int) -> str:
    """filter_complex of one part: its kept pieces selected from the piece file (whose time 0 is recording time
    `offset`), ads blurred, webcam shots as overlays on their spans, tones over slurs, fades, −14 LUFS."""
    keep = between([(a - offset, b - offset) for a, b in part["pieces"]])
    punch = [(s["start_s"], s["end_s"]) for s in part["shots"] if s["kind"] == "punch"]
    focus = [(s["start_s"], s["end_s"]) for s in part["shots"] if s["kind"] == "focus"]
    branches = 1 + bool(punch) + bool(focus)
    keepalive = f"not(mod(n,{rate // 2}))"
    chains = [f"[0:v]fps={rate},select='{keep}',setpts=N/{rate}/TB,scale={WIDTH}:{HEIGHT},setsar=1,format=yuv420p[raw]"]
    chains += blur_chain("[raw]", "[src]", [tuple(b) for b in part.get("blur") or []], "ad")
    chains.append("[src]" + (f"split={branches}[base]" + ("[pz]" if punch else "") + ("[fz]" if focus else "") if branches > 1 else "null[base]"))
    current = "base"
    if punch:
        r = part["punch_rect"]
        chains.append(f"[pz]select='{between([(a - LEAD_S, b) for a, b in punch], 2)}+{keepalive}',crop={r['width']}:{r['height']}:{r['x']}:{r['y']},"
                      f"scale={WIDTH}:{HEIGHT}:flags=lanczos,setsar=1,format=yuv420p[pv]")
        chains.append(f"[{current}][pv]overlay=0:0:enable='{between(punch, 2)}':format=yuv420[afterp]")
        current = "afterp"
    if focus:
        c = part["cam_rect"]
        chains.append(f"[fz]select='{between([(a - LEAD_S, b) for a, b in focus], 2)}+{keepalive}',split[fb][fc]")
        chains.append(f"[fb]scale=384:216,boxblur=6:2,scale={WIDTH}:{HEIGHT},eq=brightness=-0.18:saturation=0.8[bg]")
        chains.append(f"[fc]crop={c['width']}:{c['height']}:{c['x']}:{c['y']},scale=-2:{FOCUS_HEIGHT}:flags=lanczos,pad=iw+12:ih+12:6:6:color=white@0.9[cam]")
        chains.append("[bg][cam]overlay=(W-w)/2:(H-h)/2:format=yuv420,format=yuv420p[fv]")
        chains.append(f"[{current}][fv]overlay=0:0:enable='{between(focus, 2)}':format=yuv420[afterf]")
        current = "afterf"
    duration = part["duration_s"]
    tail = [f"fade=t=out:st={max(0.0, duration - END_FADE_S):.2f}:d={END_FADE_S}"] if last else []   # no end card: picture and sound fade
    chains.append(f"[{current}]" + ",".join(tail + ["format=yuv420p"]) + "[v]")
    joins = Timeline(part["pieces"]).starts[1:]
    dips = "volume=eval=frame:volume='" + "*".join(f"min(1,abs(t-{c:.3f})/{JOIN_FADE_S})" for c in joins) + "'," if joins else ""
    ending = END_FADE_S if last else PART_FADE_S
    tone = bleep.audio_filter([tuple(b) for b in part.get("bleeps") or []])
    chains.append(f"[0:a]aresample=48000,asetnsamples=n=160:p=0,aselect='{keep}',asetpts=N/SR/TB,{dips}{tone + ',' if tone else ''}"
                  f"afade=t=in:d={PART_FADE_S},afade=t=out:st={max(0.0, duration - ending):.3f}:d={ending},"
                  "aformat=channel_layouts=stereo,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")
    return ";".join(chains)


def part_command(part: dict, signal: dict, out: Path, *, last: bool, kind: str) -> list[str]:
    graph = part_filter(part, offset=signal["offset"], last=last, rate=fps(kind))
    return [*HEAD, *FILTER_THREADS, *NO_REINIT, "-i", signal["video"], "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
            *video_args(kind), *AUDIO, str(out)]


def intro_command(intro: dict, signals: dict, out: Path, *, kind: str) -> list[str]:
    """The cold open: each clip cut from its part's piece, ads blurred, zoomed on the webcam where the part has a
    punch-in, a white flash between clips, the sound faded at every cut."""
    rate = fps(kind)
    inputs, chains, labels = [], [], []
    for k, clip in enumerate(intro["clips"]):
        signal = signals[str(clip["index"])]
        length = clip["to_s"] - clip["from_s"]
        inputs += [*NO_REINIT, "-ss", f"{clip['from_s'] - signal['offset']:.3f}", "-t", f"{length:.3f}", "-i", signal["video"]]
        chains.append(f"[{k}:v]trim=duration={length:.3f},setpts=PTS-STARTPTS,scale={WIDTH}:{HEIGHT},setsar=1,format=yuv420p[c{k}r]")
        chains += blur_chain(f"[c{k}r]", f"[c{k}s]", [tuple(b) for b in clip.get("blur") or []], f"c{k}ad")
        r = clip.get("rect")
        zoom = f"crop={r['width']}:{r['height']}:{r['x']}:{r['y']},scale={WIDTH}:{HEIGHT}:flags=lanczos,setsar=1," if r else ""
        flash = "fade=t=in:st=0:d=0.1:color=white," if k else ""
        chains.append(f"[c{k}s]{zoom}fps={rate},{flash}format=yuv420p[v{k}]")
        tone = bleep.audio_filter([tuple(b) for b in clip.get("bleeps") or []])
        chains.append(f"[{k}:a]atrim=duration={length:.3f},asetpts=PTS-STARTPTS,{tone + ',' if tone else ''}aresample=48000,aformat=channel_layouts=stereo,"
                      f"afade=t=in:d={PART_FADE_S},afade=t=out:st={max(0.0, length - PART_FADE_S):.3f}:d={PART_FADE_S}[a{k}]")
        labels.append(f"[v{k}][a{k}]")
    chains.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=1[cv][ca];[ca]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]")
    return [*HEAD, *FILTER_THREADS, *inputs, "-filter_complex", ";".join(chains), "-map", "[cv]", "-map", "[a]", *video_args(kind), *AUDIO, str(out)]


def key_of(argv: list[str]) -> str:
    """What an output was made from: the command and the size and time of the files it reads."""
    inputs = []
    for i, arg in enumerate(argv[:-1]):
        if i and argv[i - 1] == "-i":
            try:
                st = Path(arg).stat()
                inputs.append([arg, st.st_size, st.st_mtime_ns])
            except OSError:
                inputs.append([arg, None, None])
    return hashlib.sha256(json.dumps([argv, inputs], ensure_ascii=False).encode("utf-8")).hexdigest()


def made(argv: list[str]) -> bool:
    out = Path(argv[-1])
    try:
        mark = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))
        return out.is_file() and mark.get("key") == key_of(argv) and mark.get("size") == out.stat().st_size
    except (OSError, ValueError):
        return False


def run(argv: list[str], *, runner=None, timeout: float = 4 * 3600) -> bool:
    """One ffmpeg; False when its output was there already, made by the same command. Raises EncodeError."""
    if made(argv):
        return False
    runner = runner or _ffmpeg
    out = Path(argv[-1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").unlink(missing_ok=True)
    done = runner(argv, capture_output=True, text=True, timeout=timeout)
    if done.returncode != 0:
        out.unlink(missing_ok=True)
        raise EncodeError(f"ffmpeg failed on {out.name}: {(done.stderr or '').strip()[-600:]}")
    out.with_suffix(".json").write_text(json.dumps({"key": key_of(argv), "size": out.stat().st_size}), encoding="utf-8")
    return True


def concat(listing: list[Path], out: Path, *, runner=None) -> None:
    runner = runner or _ffmpeg
    lst = out.with_name("concat.txt")
    lst.write_text("".join(concat_line(p) for p in listing), encoding="utf-8")
    tmp = out.with_name(out.stem + ".part.mp4")
    done = runner([*HEAD, "-f", "concat", "-safe", "0", "-i", str(lst), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(tmp)],
                  capture_output=True, text=True, timeout=3600)
    if done.returncode != 0:
        tmp.unlink(missing_ok=True)
        raise EncodeError(f"ffmpeg could not join the parts: {(done.stderr or '').strip()[-600:]}")
    tmp.replace(out)


def cover_moment(recap: dict) -> tuple[int, float]:
    """(part index, recording second) of the cover: the strongest peak of a part with a webcam, else of any part, else
    the middle of the first highlight."""
    with_cam = [p for p in recap["parts"] if p.get("punch_rect")] or recap["parts"]
    peaks = sorted(((s, p["index"], t) for p in with_cam for t, s in p["peaks"]), reverse=True)
    if peaks:
        return peaks[0][1], peaks[0][2]
    part = next((p for p in recap["parts"] if p["role"] == "highlight"), recap["parts"][0])
    return part["index"], (part["start_s"] + part["end_s"]) / 2


def cover_command(recap: dict, signals: dict, out: Path) -> list[str]:
    """One frame of the recording at the cover moment, 1280×720, the part's ads blurred; zoomed on the webcam as the
    punch-in shows it, when the part has one (the streamer's face at the strongest reaction says more than the game)."""
    index, at = cover_moment(recap)
    part = next(p for p in recap["parts"] if p["index"] == index)
    signal = signals[str(index)]
    chains = [f"[0:v]scale={WIDTH}:{HEIGHT},setsar=1,format=yuv420p[raw]"] + blur_chain("[raw]", "[b]", [tuple(b) for b in part.get("blur") or []], "ad")
    r = part.get("punch_rect")
    zoom = f"crop={r['width']}:{r['height']}:{r['x']}:{r['y']}," if r else ""
    chains.append(f"[b]{zoom}scale=1280:720:flags=lanczos[v]")
    return [*HEAD, "-ss", f"{max(0.0, at - signal['offset']):.3f}", "-i", signal["video"], "-filter_complex", ";".join(chains), "-map", "[v]",
            "-frames:v", "1", "-q:v", "2", str(out)]


def render(recap: dict, signals: dict, folder: Path, *, kind: str | None = None, runner=None,
           progress: Callable[[int, int, bool], None] = lambda *_: None, between_parts: Callable[[], None] = lambda: None) -> dict:
    """recap/video.mp4 and recap/cover.jpg. `progress(done, total, encoded)` after every piece; `between_parts` is called
    before each encode (a pause stops there). Returns {encoder, fps, encoded, kept}."""
    kind = kind or encoder()
    runner = runner or _ffmpeg
    work = folder / "work"
    work.mkdir(parents=True, exist_ok=True)
    commands = []
    if (recap.get("intro") or {}).get("clips"):
        commands.append(intro_command(recap["intro"], signals, work / "intro.mkv", kind=kind))
    for part in recap["parts"]:
        commands.append(part_command(part, signals[str(part["index"])], work / f"part{part['index']:03d}.mkv",
                                     last=part is recap["parts"][-1], kind=kind))
    encoded = kept = 0
    for n, argv in enumerate(commands, 1):
        between_parts()
        if run(argv, runner=runner):
            encoded += 1
        else:
            kept += 1
        progress(n, len(commands), True)
    concat([Path(a[-1]) for a in commands], folder / "video.mp4", runner=runner)
    cover = cover_command(recap, signals, folder / "cover.jpg")
    done = runner(cover, capture_output=True, text=True, timeout=300)
    if done.returncode != 0:
        raise EncodeError(f"ffmpeg could not take the cover: {(done.stderr or '').strip()[-400:]}")
    return {"encoder": "h264_nvenc" if kind == "nvenc" else "libx264", "fps": fps(kind), "encoded": encoded, "kept": kept}
