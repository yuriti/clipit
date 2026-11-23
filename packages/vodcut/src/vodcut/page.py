"""VodCut's places in SMTV's window: «Stream recording» under «New request», its view of an open request, its switches in
Settings, its card under Plugins; and the server side of them: starting a job from the form, the time estimate, the job
summary, the switches.

The look lives in web/ (section.js, section.css); it reads the job's events like every other reader.
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import sys
from pathlib import Path

from smtv_core import paths, proc
from smtv_core.settings import Settings
from smtv_core.tool import JobStart, Page, RequestKind

from . import avatar, ingest, local_download, options, pick
from .fit.contract import BATCH as FIT_BATCH

WEB = Path(__file__).parent / "web"
LANGUAGE = re.compile(r"^(auto|[a-z]{2,3})$")

# Seconds per hour of stream, measured on a 2.35 h Twitch VOD on an M-series Mac without a graphics card (20.11.2026),
# and per clip for the render. An estimate, not a promise: the network and the model's speed change it.
AUDIO_LINK_S_PER_H, AUDIO_FILE_S_PER_H = 25.0, 6.0
SPEECH_CPU_S_PER_H, SPEECH_GPU_S_PER_H = 100.0, 15.0
SCAN_S_PER_H, RATING_S_PER_H, MODEL_FLOOR_S = 13.0, 8.0, 10.0
RENDER_LINK_S_PER_CLIP, RENDER_FILE_S_PER_CLIP = 66.0, 36.0
# The critic (the «critic» switch, stage 14), same VOD and Mac (21.11.2026): a check 7–11 s per clip; an edit (a render
# and a second check, 33–39 s) is rare, so a little is added for it.
CRITIC_S_PER_CLIP = 12.0
# Fit (the «precise» switch, 21.11.2026, same VOD, codex exec): one request of up to 4 clips took 12–13 s, requests run
# side by side (4 at once), the packets themselves take ~0.03 s per clip on the processor.
FIT_S_PER_REQUEST, FIT_AT_ONCE = 13.0, 4
# The recap (the «recap» switch, stage 12), same VOD and Mac (21.11.2026): story 34 s, 11.2 min of the stream fetched in
# 13 pieces 187 s, webcam and ads 80 s (asked one by one then, side by side now), 14 encodes 85 s → a 10.7 min video in
# 389 s. A longer stream gives a longer story (at most 28 min of source), so the estimate grows with it up to ~2.5×.
RECAP_STORY_S, RECAP_LINK_S_PER_MIN, RECAP_FILE_S_PER_MIN, RECAP_LOOK_S = 35.0, 25.0, 9.0, 40.0


def jobs() -> Path:
    return paths.data_dir() / "vodcut"


def _source(fields: dict) -> str:
    source = str(fields.get("source") or "").strip()
    if not source:
        raise ValueError("paste a link or choose a file")
    if not ingest.is_link(source):
        path = Path(source).expanduser()
        if not path.is_file():
            raise ValueError(f"no such file: {path}")
        source = str(path.resolve())
    return source


def start(fields: dict) -> JobStart:
    from .pipeline import job_dir

    source = _source(fields)
    language = str(fields.get("language") or "auto").strip().lower()
    if not LANGUAGE.match(language):
        raise ValueError("language: auto or a two-letter code such as ru, en, de")
    args = ["run", source, "--language", language]
    max_clips = fields.get("max_clips")
    if max_clips not in (None, "", 0):
        try:
            n = int(max_clips)
        except (TypeError, ValueError):
            raise ValueError("clips: a whole number") from None
        if not 1 <= n <= 100:
            raise ValueError("clips: from 1 to 100")
        args += ["--max-clips", str(n)]
    channel = str(fields.get("channel") or "").strip()
    if channel:
        args += [f"--channel={channel[:80]}"]          # a name starting with «-» is not read as an option
    if fields.get("no_render"):
        args.append("--no-render")
    folder = job_dir(source, jobs())
    return JobStart(folder=folder, args=[*args, "--out", str(folder)])


def _probe(source: str) -> dict:
    """Duration and title of a recording without downloading it."""
    if not ingest.is_link(source):
        try:
            done = proc.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", source],
                            30, what="ffprobe")
        except proc.TimedOut:
            raise ValueError("this file did not open in 30 seconds: is it on a drive that is not answering?") from None
        try:
            return {"duration_s": float(done.stdout.strip()), "title": Path(source).stem, "kind": "file"}
        except ValueError:
            raise ValueError("this file has no readable duration: is it a video?") from None
    if options.local_download():
        return local_download.probe(source)
    from smtv_core import media
    try:
        src = media.info(source)                  # no place in the queue, no hours of the day counted
    except media.MediaError as e:
        raise ValueError(str(e)) from None
    return {"duration_s": float(src.get("duration_s") or 0), "title": src.get("title") or "", "channel": src.get("channel") or "",
            "kind": "link", "live": bool(src.get("live"))}


def _has_gpu() -> bool:
    if not shutil.which("nvidia-smi"):
        return False
    try:
        from smtv_core.asr.engines import providers
        return any("CUDA" in p for p in providers())
    except Exception:  # noqa: BLE001 — no onnxruntime build with CUDA: the processor does the work
        return False


def estimate(fields: dict) -> dict:
    source = _source(fields)
    info = _probe(source)
    hours = info["duration_s"] / 3600
    if hours <= 0:
        raise ValueError("the recording's length is unknown (a stream still going?)")
    from .pipeline import job_dir

    folder = job_dir(source, jobs())
    gpu = _has_gpu()
    # about 3.5 clips per hour (production's yield); a short recording at most one per 45 s of it
    clips = int(fields.get("max_clips") or 0) or min(pick.expected(info["duration_s"]), max(1, int(info["duration_s"] // 45)))
    link = info["kind"] == "link"
    done_clips = len(list((folder / "clips").glob("clip*.mp4"))) if (folder / "clips").is_dir() else 0
    steps = [
        ("audio", 0 if (folder / "audio.wav").exists() else (AUDIO_LINK_S_PER_H if link else AUDIO_FILE_S_PER_H) * hours + 3),
        ("speech", 0 if (folder / "transcript.json").exists() else (SPEECH_GPU_S_PER_H if gpu else SPEECH_CPU_S_PER_H) * hours + 5),
        ("scan", 0 if (folder / "pass1.json").exists() else SCAN_S_PER_H * hours + MODEL_FLOOR_S),
        ("rating", 0 if (folder / "pass2.json").exists() else RATING_S_PER_H * hours + MODEL_FLOOR_S),
    ]
    switches = options.load(Settings.load())
    if switches["precise"]:
        requests = math.ceil(clips / FIT_BATCH)
        steps.append(("fit", 0 if (folder / "fit.json").exists() else math.ceil(requests / FIT_AT_ONCE) * FIT_S_PER_REQUEST))
    if not fields.get("no_render"):
        per_clip = (RENDER_LINK_S_PER_CLIP if link else RENDER_FILE_S_PER_CLIP) + (CRITIC_S_PER_CLIP if switches["critic"] else 0.0)
        steps.append(("render", max(0, clips - done_clips) * per_clip))
        if switches["recap"]:
            made = (folder / "recap" / "video.mp4").exists()
            minutes = min(28.0, max(5.0, 4.8 * hours))             # minutes of the stream the story takes (11.2 of 2.35 h)
            steps.append(("recap", 0 if made else RECAP_STORY_S + RECAP_LOOK_S + minutes * (RECAP_LINK_S_PER_MIN if link else RECAP_FILE_S_PER_MIN)))
    return {"duration_s": round(info["duration_s"], 1), "title": info.get("title", ""), "channel": info.get("channel", ""),
            "clips": clips, "gpu": gpu, "resumes": folder.exists() and any(s == 0 for _, s in steps),
            "seconds": round(sum(s for _, s in steps)), "steps": [{"name": n, "seconds": round(s)} for n, s in steps]}


def describe(folder: Path) -> dict:
    out: dict = {}
    try:
        src = json.loads((folder / "source.json").read_text(encoding="utf-8"))
        out = {"title": src.get("title") or "", "channel": src.get("channel") or "", "platform": src.get("platform") or "",
               "duration_s": src.get("duration_s"), "source": src.get("url") or src.get("path") or ""}
    except FileNotFoundError:
        pass                     # a job just started: its recording is not known yet
    except (OSError, ValueError, AttributeError) as e:
        sys.stderr.write(f"vodcut: {folder.name}/source.json unreadable: {type(e).__name__}: {e}\n")
    clips_dir = folder / "clips"
    out["clips"] = len(list(clips_dir.glob("clip*.mp4"))) if clips_dir.is_dir() else 0
    if (folder / "recap" / "video.mp4").exists():
        out["recap"] = True
    picture = avatar.ensure(folder, jobs() / ".avatars")     # looked for in the background the first time
    if picture:
        out["avatar"] = picture
    return out


def list_options(settings: Settings) -> list[dict]:
    return [{"name": k, "value": v, "about": options.ABOUT[k]} for k, v in options.load(settings).items()]


def again(folder: Path, args: list) -> JobStart:
    """A new request from a finished one: the same recording and choices in a new folder next to it (<name>-2, -3…).
    The audio already fetched is taken over (a hard link where the disk allows), so the new run starts at speech to text;
    the rest — speech, episodes, clips — is made anew. Except when the model left parts of the old request unanswered
    (no pass1.json or pass2.json, but answers kept): then its text and answers go along too, and only the rest is asked."""
    args = [str(a) for a in args]
    if "--out" in args:
        i = args.index("--out")
        del args[i:i + 2]
    stem, n = re.sub(r"-\d+$", "", folder.name), 2
    while (folder.parent / f"{stem}-{n}").exists():
        n += 1
    new = folder.parent / f"{stem}-{n}"
    new.mkdir(parents=True)
    from .pipeline import RATING_ANSWERS, SCAN_ANSWERS
    names = ["audio.wav", "source.json", "avatar.png", "avatar.jpg"]
    partial = not ((folder / "pass1.json").exists() and (folder / "pass2.json").exists())
    if partial and any((folder / n).exists() for n in (SCAN_ANSWERS, RATING_ANSWERS)):
        names += ["transcript.json", SCAN_ANSWERS, RATING_ANSWERS, "pass1.json"]
    for name in names:
        old = folder / name
        if old.is_file():
            try:
                os.link(old, new / name)
            except OSError:
                shutil.copy2(old, new / name)
    return JobStart(folder=new, args=[*args, "--out", str(new)])


def command_job(args) -> JobStart | None:
    """`smtv vodcut run | render | recap` typed in a terminal, as the window would run it (stage 16): while SMTV runs, the
    gateway hands it over to SMTV's queue. Commands that are not jobs, or a render or recap with nothing to work on (the
    command says so itself), give None."""
    from . import console
    from .pipeline import job_dir

    which = getattr(args, "vodcut_command", None)
    if which == "run":
        source = args.source if ingest.is_link(args.source) else str(Path(args.source).expanduser().resolve())
        folder = Path(args.out).expanduser().resolve() if args.out else job_dir(source, jobs())
        out = ["run", source, "--language", str(args.language)]
        if args.channel:
            out += [f"--channel={args.channel}"]
        if args.max_clips:
            out += ["--max-clips", str(args.max_clips)]
        if args.workers != 4:
            out += ["--workers", str(args.workers)]
        if args.no_render:
            out.append("--no-render")
        return JobStart(folder, [*out, "--out", str(folder)], echo=console.printer(folder))
    if which in ("render", "recap"):
        candidate = Path(args.job).expanduser().resolve()
        folder = candidate if (candidate / "clips.json").exists() else job_dir(args.job, jobs())
        if not (folder / "clips.json").exists():
            return None
        out = [which, str(folder)] + (["--clips", str(args.clips)] if which == "render" and args.clips else [])
        return JobStart(folder, out, echo=console.printer(folder))
    return None


ICON = '<circle cx="6" cy="6.5" r="2.5"/><circle cx="6" cy="17.5" r="2.5"/><path d="M8 8.2 20 18M8 15.8 20 6"/>'
RECORDING_ICON = ('<rect x="3" y="4" width="18" height="16" rx="2.5"/>'
                  '<path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/>')

# words: `request.title`, `request.about` and `tool.about` in web/i18n/<language>.json
REQUEST = RequestKind(title="request.title", about="request.about", icon=RECORDING_ICON)

page = Page(title="VodCut", folder=WEB, jobs=jobs, start=start, estimate=estimate, describe=describe,
            options=list_options, set_option=options.set_option, request=REQUEST, about="tool.about", icon=ICON, pause=True, again=again,
            command_job=command_job)
