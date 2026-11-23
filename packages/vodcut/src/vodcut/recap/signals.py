"""What the edit needs to know about each part beyond the transcript.

  video   the part's piece of the recording (the file itself for a local video; for a link only that span, as the
          clips get theirs);
  levels  the loudness in dB at 10 Hz, from the job's own audio.wav: no video is decoded for it;
  cam     where the streamer's webcam is (fractions of the frame): looked for on this computer (B12, scene.py), the
          core layout agent only on a doubt;
  ads     ad overlays to blur (boxes on the 1920×1080 source): the core banner agent, once for the whole recording
          (shared with its clips through scene.json).

One frame per part; the webcam is looked at five parts at a time (the five frames the layout agent is made for), where
production asks one layout request per eight parts and one banner request per group of parts with the same scene. Production also measures when each ad is on screen (OpenCV, twice a second) and tracks
the face (MediaPipe); here an ad found in a group is blurred through all of its parts, and there is no face track.

signals.json: {part index: {span, video, offset, levels, cam, cam_by, ads, ads_by}}; an entry of another span (a new
story) is measured again.
"""
from __future__ import annotations

import itertools
import json
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from smtv_core import prompts
from smtv_core.render import frames
from smtv_core.render.layout import FULL_CAMERA_AREA, LayoutError, _rect, validate

from .. import render as clip_render
from ..scene import Scene

LEVEL_STEP_S = 0.1
LOOK_GROUP = 5             # parts per layout / banner request: the core prompts read five frames
FETCH_AT_ONCE = 3          # pieces of a link downloaded at once
LOOK_AT_ONCE = 4           # layout and banner requests at once (the clips' Fit asks four at once too)


def levels(wav: Path, start_s: float, end_s: float, step_s: float = LEVEL_STEP_S) -> list[float]:
    """dB of each `step_s` of [start, end] of a 16-bit mono WAV (RMS, full scale = 0 dB)."""
    import numpy as np
    with wave.open(str(wav), "rb") as w:
        rate, total = w.getframerate(), w.getnframes()
        first = max(0, int(start_s * rate))
        count = max(0, min(total, int(end_s * rate)) - first)
        if not count or w.getsampwidth() != 2:
            return []
        w.setpos(first)
        samples = np.frombuffer(w.readframes(count), dtype="<i2").astype(np.float32) / 32768.0
        if w.getnchannels() > 1:
            samples = samples.reshape(-1, w.getnchannels()).mean(axis=1)
    size = int(rate * step_s)
    n = len(samples) // size
    if not n:
        return []
    rms = np.sqrt(np.mean(samples[:n * size].reshape(n, size) ** 2, axis=1))
    return [round(float(v), 1) for v in 20 * np.log10(rms + 1e-6)]


def piece_name(part: dict) -> str:
    """A piece is named by its span: a part the story moved is fetched again, never read from the old file."""
    return f"part{part['index']:03d}-{part['start_s']:.2f}-{part['end_s']:.2f}.mp4"


def fetch(info: dict, part: dict, folder: Path) -> tuple[str, float]:
    """(video file, its time 0 in the recording) for one part. Local files are read where they are."""
    video, offset = clip_render.fetch_piece(info, part["start_s"], part["end_s"], folder / piece_name(part))
    return str(Path(video).resolve()), offset          # absolute: the encode may run from another folder


def webcam(asker, shots: list[Path]) -> tuple[dict | None, str]:
    """(webcam rectangle in fractions of the frame or None, how it was decided) from the core layout agent. A camera that
    is the whole picture is no webcam box to zoom on."""
    if asker is None:
        return None, "none: no model"
    width, height = frames.size(shots[0])
    evidence = {"duration_seconds": len(shots), "source_width": width, "source_height": height, "frame_times_seconds": list(range(len(shots))),
                "transcript": [], "audio_directly_sent": False,
                "note": "the frames come from different moments of one stream, one per part of a recap; only the webcam's place matters"}
    text = prompts.text("fit/layout-prompt.txt").rstrip() + "\nClip evidence:\n" + json.dumps(evidence, ensure_ascii=False)
    answer, meta = asker.ask(text, prompts.schema("layout"), images=shots, purpose="layout")
    if answer is None:
        return None, f"none: {meta.get('error', 'no answer')}"
    try:
        validate(answer)
        cam = _rect(answer["webcam_region"]) if answer.get("webcam_region") is not None else None
    except (LayoutError, KeyError, TypeError) as e:
        return None, f"none: model answer rejected ({e})"
    if cam is None:
        return None, "model: no webcam"
    if cam["width"] * cam["height"] >= FULL_CAMERA_AREA:
        return None, "model: the camera is the picture"
    return cam, "model"


def camera_of(asker, scene: Scene, shots: list[Path], work: Path) -> tuple[dict | None, str]:
    """(webcam rectangle or None, how it was decided): on this computer first (B12), the model on a doubt; what the
    model decides is kept in the scene for the other parts and the clips."""
    found = scene.look(shots)
    if found.kind == "overlay":
        if not found.known and len(set(map(str, shots))) >= 3:     # a box from one or two frames serves these parts only
            scene.remember(found, found.camera, "local")
        return found.camera, f"local: {found.reason}"[:300]
    if found.kind in ("full", "none"):
        return None, f"local: {found.reason}"[:300]
    cam, by = webcam(asker, clip_render._for_model(shots, work))
    if not by.startswith("none:"):
        scene.remember(found, cam, "model, the recap", full=by == "model: the camera is the picture")
    return cam, by


def _unlooked(entry: dict, ad_blur: bool) -> bool:
    """A part whose webcam or ads were not decided by the model: no answer (a 503, out of quota) is no decision, and is
    asked again by the next run instead of being kept as «no camera, no ads» for good."""
    cam_by, ads_by = entry.get("cam_by"), entry.get("ads_by")
    return cam_by is None or str(cam_by).startswith("none:") or \
        (ad_blur and (ads_by in (None, "off") or str(ads_by).startswith("none:")))


def collect(job: Path, story: dict, info: dict, asker, *, ad_blur: bool = True,
            progress: Callable[[str, int, int], None] = lambda *_: None,
            unlooked: Callable[[int, int], None] = lambda *_: None) -> dict:
    """signals.json for every part of the story (resumable: parts measured over the same span are kept).

    `unlooked(n, total)` is called once when the model left n parts without a decision on the webcam or the ads."""
    folder = job / "recap"
    path = folder / "signals.json"
    try:
        signals = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        signals = {}
    parts = story["parts"]
    for part in parts:
        entry = signals.get(str(part["index"]))
        if entry and entry.get("span") != [part["start_s"], part["end_s"]]:
            del signals[str(part["index"])]
    def save() -> None:          # whole or not at all: a half-written file would lose every piece measured so far
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(signals, ensure_ascii=False, indent=1), encoding="utf-8")
        tmp.replace(path)

    # the pieces of video, a few at once for a link; the loudness from the job's audio meanwhile
    todo = [p for p in parts if not Path((signals.get(str(p["index"])) or {}).get("video") or "/nonexistent").exists()]
    done = len(parts) - len(todo)
    progress("video", done, len(parts))
    with ThreadPoolExecutor(max_workers=FETCH_AT_ONCE if info.get("kind") != "file" else 1) as pool:
        for part, (video, offset) in zip(todo, pool.map(lambda p: fetch(info, p, folder / "pieces"), todo)):
            entry = signals.setdefault(str(part["index"]), {})
            entry.update({"span": [part["start_s"], part["end_s"]], "video": video, "offset": offset})
            done += 1
            progress("video", done, len(parts))
            save()
    wav = job / "audio.wav"
    for part in parts:
        entry = signals[str(part["index"])]
        if "levels" not in entry:
            entry["levels"] = levels(wav, part["start_s"], part["end_s"]) if wav.exists() else []
    save()

    # the webcam and the ads: one frame per part. The webcam is looked for on this computer, five parts at a time, and
    # the model asked only on a doubt (B12); the ad slots are one question for the whole recording, shared with its clips
    looking = [p for p in parts if _unlooked(signals[str(p["index"])], ad_blur)]
    groups = [looking[i:i + LOOK_GROUP] for i in range(0, len(looking), LOOK_GROUP)]
    scene = Scene(job)

    def shot(part: dict) -> list[Path]:
        entry = signals[str(part["index"])]
        moment = part["peaks_s"][0] if part["peaks_s"] else (part["start_s"] + part["end_s"]) / 2
        return frames.extract(Path(entry["video"]), [max(0.0, moment - entry["offset"])], folder / "frames" / f"part{part['index']:03d}")

    with ThreadPoolExecutor(max_workers=LOOK_AT_ONCE) as pool:
        taken = dict(zip((p["index"] for p in looking), pool.map(shot, looking)))
    every = [s for shots in taken.values() for s in shots]
    ads = clip_render.recording_ads(asker, scene, lambda: clip_render.spread(every, clip_render.AD_FRAMES)) \
        if ad_blur and every else ([], "off")

    def look(group: list[dict]) -> dict:
        shots = [s for part in group for s in taken[part["index"]]]
        shots += [shots[-1]] * (LOOK_GROUP - len(shots))
        cam, cam_by = camera_of(asker, scene, shots, folder / "frames")
        found: dict = {"cam": cam, "cam_by": cam_by}
        if ad_blur:
            found.update(ads=[list(b) for b in ads[0]], ads_by=ads[1])
        return found

    progress("look", 0, len(groups))
    results = iter([look(groups[0])] if groups else [])         # the first group alone: what it decides serves the others
    with ThreadPoolExecutor(max_workers=LOOK_AT_ONCE) as pool:       # then the rest side by side
        rest = pool.map(look, groups[1:])
        for n, (group, found) in enumerate(zip(groups, itertools.chain(results, rest)), 1):
            for part in group:
                signals[str(part["index"])].update(found)
            save()
            progress("look", n, len(groups))
    missed = sum(1 for p in parts if _unlooked(signals[str(p["index"])], ad_blur))
    if missed:
        unlooked(missed, len(parts))
    if not ad_blur:                        # switched off: nothing is blurred, what was found stays for when it is on again
        return {k: {**v, "ads": [], "ads_by": "off"} for k, v in signals.items()}
    return signals
