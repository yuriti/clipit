"""From clips.json to finished 9:16 MP4 files.

For every clip: get its piece of video (from the file, or only that piece from the link), take five frames, find the
streamer's webcam on them (on this computer; the model only on a doubt — B12, scene.py) and choose the layout from it
(the webcam stays in the frame), blur the recording's ad slots (one model question per recording), write the captions,
the hook and the peak lines, run ffmpeg with the ad blur and the bleep, bring the sound to −14 LUFS. The critic looks at
the finished clips a few at a time. What is on is decided by the switches in options.py.
A finished clip is not rendered again; a failed one is reported and the others go on.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from smtv_core import critic, media, proc, prompts
from smtv_core.audio import bleep
from smtv_core.events import ADS_FOUND, CLIP_FAILED, CLIP_READY, DONE, ERROR, LAYOUT_CHOSEN, PROGRESS, STAGE, Journal
from smtv_core.render import adblur, captions, ffmpeg, frames, peak, profanity
from smtv_core.render import camera as webcam
from smtv_core.render.fonts import FONTS_DIR
from smtv_core.render.layout import DEFAULT, FULL_CAMERA_AREA, Layout, LayoutError, from_frames, vote
from smtv_core.pause import checkpoint

from . import local_download
from . import options as opts
from .model import Asker
from .scene import Scene

PIECE_PAD_S = local_download.PIECE_PAD_S     # one margin for both ways of fetching a piece
HOOK_MS = 3000
LAYOUT_VOTES = 3          # stage 14: three answers put to a vote (smtv_core.render.layout.vote) — since B12 only when the first is unsure
LAYOUT_CACHE = "layouts.json"
PIECE_TIMEOUT_FLOOR_S = 600     # joining a piece of video without re-encoding: never more than 10 minutes
LAYOUT_RULE = "6"         # part of the cache key: a choice made by an older rule is made again (6: the frames first, B12)
MODEL_FRAME_WIDTH = 768   # frames the model looks at for the layout and the ads (B12; they were 1280)
AD_FRAMES = 5             # the banner prompt reads five frames


_tickets: dict[str, media.Ticket] = {}
_tickets_lock = threading.Lock()


def _ticket(url: str) -> media.Ticket:
    """One ticket of our queue per link for the whole render (and the recap after it): clips do not queue one by one."""
    with _tickets_lock:
        ticket = _tickets.get(url)
        if ticket is None or not ticket.id:
            ticket = _tickets[url] = media.Ticket(url)
        return ticket


def close_tickets() -> None:
    """The slot in our queue goes to the next one; an unclosed ticket frees itself on the server after a minute and a half."""
    with _tickets_lock:
        for ticket in _tickets.values():
            ticket.close()
        _tickets.clear()


def _remux(src: Path, dest: Path) -> None:
    """Segments as one MP4 starting at 0, without re-encoding (their own timestamps are those of the whole recording)."""
    tmp = dest.with_name(dest.stem + ".remux.mp4")
    done = proc.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src), "-map", "0", "-c", "copy",
                     "-movflags", "+faststart", str(tmp)], PIECE_TIMEOUT_FLOOR_S, what=f"ffmpeg ({dest.stem})")
    if done.returncode != 0:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg could not join the piece {dest.stem}: {done.stderr.strip()[-400:]}")
    os.replace(tmp, dest)


def fetch_piece(info: dict, start_s: float, end_s: float, dest: Path) -> tuple[Path, float]:
    """(video file, offset): the file itself for a local source; for a link only [start, end] plus a little margin, through
    StreamMoment (whole HLS segments, so the piece starts at the segment before `start`) or, with «Download on this
    computer» on, through yt-dlp here."""
    if info.get("kind") == "file":
        return Path(info["path"]), 0.0
    offset_file = dest.with_name(dest.name + ".offset")
    if dest.exists():
        try:
            return dest, float(offset_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return dest, max(0.0, start_s - PIECE_PAD_S)       # a piece made by yt-dlp before stage 23
    offset_file.unlink(missing_ok=True)        # left from a piece that was dropped: never paired with a new one
    if opts.local_download():
        return local_download.piece(info["url"], start_s, end_s, dest)      # its offset is start − pad, as before stage 23
    a, b = max(0.0, start_s - PIECE_PAD_S), end_s + PIECE_PAD_S
    raw = dest.with_name(dest.stem + ".segments")
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        offset = _ticket(info["url"]).fetch("video", raw, a, b)
        offset_file.write_text(f"{offset:.3f}", encoding="utf-8")    # before the piece: a piece is never there without it
        _remux(raw, dest)
    except media.MediaError as e:
        offset_file.unlink(missing_ok=True)
        raise RuntimeError(f"the piece {dest.stem} did not download through StreamMoment: {e}") from e
    except BaseException:
        offset_file.unlink(missing_ok=True)
        raise
    finally:
        raw.unlink(missing_ok=True)
    return dest, offset


def _fingerprint(prompt: str, shots: list[Path], model: str, votes: int) -> str:
    """The same frames, words, prompt, model and number of votes: the same question."""
    h = hashlib.sha256(f"{LAYOUT_RULE}|{model}|{votes}|{prompts.version()}\n{prompt}".encode("utf-8"))
    for p in map(Path, shots):
        h.update(p.read_bytes() if p.is_file() else str(p).encode("utf-8"))
    return h.hexdigest()


def _cache_read(job: Path | None) -> dict:
    if job is None:
        return {}
    try:
        data = json.loads((job / LAYOUT_CACHE).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _cache_write(job: Path, clip_id: str, entry: dict) -> None:
    data = _cache_read(job)
    data[clip_id] = entry
    tmp = job / (LAYOUT_CACHE + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(job / LAYOUT_CACHE)


def _uncertain(answer) -> bool:
    """The model says itself it is not sure of the layout: then two more answers are asked and put to a vote."""
    return isinstance(answer, dict) and (answer.get("needs_review") is True or answer.get("stable_across_frames") is False)


def _for_model(shots: list[Path], work: Path) -> list[Path]:
    """Smaller copies of the frames for the model (B12): a webcam and a banner are as clear at 768 px; the original
    frames stay for the local look, which needs every pixel of an edge. The originals when a copy cannot be made."""
    try:
        return frames.shrink(shots, work / "small", MODEL_FRAME_WIDTH)
    except Exception:  # noqa: BLE001 — larger pictures cost a few tokens more, nothing else
        return list(shots)


def choose_layout(asker: Asker | None, video: Path, start_s: float, end_s: float, words: list[dict], work: Path,
                  shots: list[Path] | None = None, *, job: Path | None = None, clip_id: str = "",
                  votes: int = LAYOUT_VOTES, scene: Scene | None = None) -> tuple[dict, str, dict]:
    """(layout dict with the webcam region under "camera", how it was chosen, {"votes", "cached"}).

    The webcam is looked for on the frames on this computer first (B12, smtv_core.render.look; scene.py keeps it for
    the next clips of the recording). Only a doubt goes to the model: one answer, and two more put to a vote
    (smtv_core.render.layout.vote) when that answer says itself it is not sure. A choice is kept in the job
    (layouts.json) by its frames, so rendering the same clip again decides nothing again. Without a webcam answer
    (no model, no usable answer) the whole frame is shown."""
    scene = scene or Scene(job)
    if shots is None:
        try:
            shots = frames.extract(video, frames.sample_times(start_s, end_s), work)
        except Exception:  # noqa: BLE001 — no frames: with a model the clip fails as before; without one the whole frame
            if asker is not None:
                raise
            return {**DEFAULT.as_dict(), "camera": None}, "default: no model", {}
    width, height = frames.size(shots[0]) if asker is not None else (0, 0)
    evidence = {"duration_seconds": round(end_s - start_s, 2), "source_width": width, "source_height": height,
                "frame_times_seconds": [round(t - start_s, 2) for t in frames.sample_times(start_s, end_s)],
                "transcript": [{"start_ms": w["s"], "end_ms": w["e"], "text": w["text"]} for w in words], "audio_directly_sent": False}
    prompt = prompts.text("fit/layout-prompt.txt").rstrip() + "\nClip evidence:\n" + json.dumps(evidence, ensure_ascii=False)
    m = asker.model_for("layout") if asker is not None else None
    key = _fingerprint(prompt, shots, f"{m.provider}/{m.model}" if m else "none", votes)
    known = _cache_read(job).get(clip_id) if clip_id else None
    if isinstance(known, dict) and known.get("key") == key and isinstance(known.get("layout"), dict):
        return known["layout"], known.get("how", "model"), {"votes": known.get("votes") or [], "cached": True}

    def keep(chosen: dict, how: str, kinds: list[str]) -> None:
        if job is not None and clip_id:
            try:
                _cache_write(job, clip_id, {"key": key, "layout": chosen, "how": how, "votes": kinds})
            except OSError:
                (job / (LAYOUT_CACHE + ".tmp")).unlink(missing_ok=True)   # the clip goes on; the next render decides again

    found = scene.look(shots)
    if found.kind != "unsure":
        camera = found.camera if found.kind == "overlay" else None
        chosen = {**from_frames(camera, found.face).as_dict(), "camera": camera}
        how = f"local: {found.reason}"[:300]
        if found.kind == "overlay" and not found.known:
            scene.remember(found, camera, "local")
        keep(chosen, how, [])
        return chosen, how, {"votes": [], "cached": False}
    if asker is None:
        return {**DEFAULT.as_dict(), "camera": None}, "default: no model", {}
    small = _for_model(shots, work)
    ask = lambda _: asker.ask(prompt, prompts.schema("layout"), images=small, purpose="layout")  # noqa: E731
    replies = [ask(0)]
    if votes > 1 and replies[0][0] is not None and _uncertain(replies[0][0]):
        with ThreadPoolExecutor(max_workers=votes - 1) as pool:
            replies += list(pool.map(ask, range(votes - 1)))
    asked = len(replies)
    answers = [a for a, _ in replies if a is not None]
    errors = sorted({str(m.get("error")) for a, m in replies if a is None and m.get("error")})
    if not answers:
        return {**DEFAULT.as_dict(), "camera": None}, ("default: " + ("; ".join(errors) or "no answer"))[:300], {}
    try:
        layout, camera, kinds = vote(answers, refine=lambda box: webcam.refine_files(shots, box))
    except LayoutError as e:
        return {**DEFAULT.as_dict(), "camera": None}, f"default: model answer rejected ({e})", {}
    chosen = {**layout.as_dict(), "camera": camera}
    how = ("model" if asked == 1 else f"model: vote of {len(kinds)}" if len(kinds) == asked else
           f"model: vote of {len(kinds)} of {asked}" + (" (" + "; ".join(errors) + ")" if errors else ""))
    how = f"{how} ({found.reason})"[:300]
    # only a full vote is kept: a choice made on fewer answers is asked again next time
    if len(kinds) == asked:
        keep(chosen, how, kinds)
        box = camera if camera is not None and camera["width"] * camera["height"] < FULL_CAMERA_AREA else None
        scene.remember(found, box, f"model, {clip_id or 'a clip'}", full=camera is not None and box is None)
    return chosen, how, {"votes": kinds, "cached": False}


def find_ads(asker: Asker | None, shots: list[Path], start_s: float, end_s: float) -> tuple[list[tuple[int, int, int, int]], str]:
    """(boxes to blur on the 1920x1080 source, how they were found). Without a usable answer nothing is blurred."""
    if asker is None:
        return [], "none: no model"
    width, height = frames.size(shots[0])
    evidence = {"duration_seconds": round(end_s - start_s, 2), "source_width": width, "source_height": height,
                "frame_times_seconds": [round(t - start_s, 2) for t in frames.sample_times(start_s, end_s)]}
    prompt = prompts.text("fit/banner-prompt.txt").rstrip() + "\nClip evidence:\n" + json.dumps(evidence, ensure_ascii=False)
    answer, meta = asker.ask(prompt, prompts.schema("banner"), images=shots, purpose="banner")
    if answer is None:
        return [], f"none: {meta.get('error', 'no answer')}"
    try:
        regions = adblur.validate_answer(answer, width, height)
    except adblur.AdBlurError as e:
        return [], f"none: model answer rejected ({e})"
    boxes = [b for r in regions if (b := adblur.to_source_pixels(r["rect"], width, height))]
    return boxes, "model"


def recording_ads(asker: Asker | None, scene: Scene, frames_of_recording) -> tuple[list[tuple[int, int, int, int]], str]:
    """The ad slots of the whole recording (B12): one banner question on five frames spread over it, kept in the scene
    for every clip and the recap. `frames_of_recording()` gives those frames (it may fetch pieces of video)."""
    if asker is None:
        return [], "none: no model"
    return scene.ad_boxes(lambda shots: find_ads(asker, shots, 0.0, float(len(shots))), frames_of_recording)


def spread(items: list, n: int) -> list:
    """n items evenly spread over the list (all of them when there are not more)."""
    if len(items) <= n:
        return list(items)
    return [items[round(i * (len(items) - 1) / (n - 1))] for i in range(n)] if n > 1 else [items[len(items) // 2]]


def _recording_frames(job: Path, info: dict, clips: list[dict]) -> list[Path]:
    """AD_FRAMES frames spread over the recording, from the pieces of the clips about to be made (they are fetched
    anyway; a fetched piece stays for its clip): the middle of each of a few clips spread over it, or more frames of
    each when there are fewer clips."""
    chosen = spread(sorted(clips, key=lambda c: c["start_s"]), AD_FRAMES)
    per = -(-AD_FRAMES // max(len(chosen), 1))
    shots: list[Path] = []
    for clip in chosen:
        try:
            video, offset = fetch_piece(info, clip["start_s"], clip["end_s"], job / "pieces" / f"{clip['id']}.mp4")
        except Exception:  # noqa: BLE001 — that clip will report its own failure; the others still show the recording
            continue
        start, end = clip["start_s"] - offset, clip["end_s"] - offset
        times = spread(frames.sample_times(start, end)[1:-1], per) if per < 5 else frames.sample_times(start, end)
        shots += frames.extract(video, times, job / "frames" / "recording" / clip["id"], width=MODEL_FRAME_WIDTH)
    return spread(shots, AD_FRAMES)


def _fix_files(item: critic.Item) -> tuple[Path, Path]:
    return item.video.with_name(item.video.stem + ".fix.mp4"), item.video.with_name(item.video.stem + ".fix.ass")


def _check_all(asker: Asker, items: list[critic.Item], emit, options: dict) -> list[critic.Outcome]:
    """The critic on the finished clips, a few in one call (B12). Whatever breaks inside it, the clips that are already
    made stay done: the outcome is «unchecked» with the reason, and the files of an unfinished edit are cleaned away."""
    decided: dict[int, critic.Outcome] = {}
    try:
        critic.review_many(lambda pr, sc, im, pu: asker.ask(pr, sc, im, purpose=pu), items, emit, peak_lines=options["peak_lines"],
                           outcomes=decided)
        error = None
    except Exception as e:  # noqa: BLE001 — the critic is a check; its failure never takes away a finished clip
        error = e
    try:
        outcomes = []
        for n, item in enumerate(items):
            fix_mp4, fix_ass = _fix_files(item)
            if n in decided:                     # decided before anything broke: its outcome and its edit stay
                if decided[n].outcome == "fixed" and fix_ass.exists():
                    try:
                        os.replace(fix_ass, item.video.with_suffix(".ass"))
                    except OSError:
                        pass
                outcomes.append(decided[n])
                continue
            if not fix_mp4.exists() and fix_ass.exists():      # the edited video already replaced the clip: its captions follow it
                try:
                    os.replace(fix_ass, item.video.with_suffix(".ass"))
                except OSError:
                    pass
            outcome = critic.Outcome("unchecked", item.decision, f"the critic failed: {type(error).__name__}: {error}"[:400])
            emit("clip_reviewed", clip=item.clip, **outcome.as_event())
            outcomes.append(outcome)
        return outcomes
    finally:
        for item in items:
            for path in _fix_files(item):
                path.unlink(missing_ok=True)


def _in_job(path: Path, job: Path) -> str:
    """A job file as events name it: relative to the job folder."""
    return Path(path).relative_to(job).as_posix()


def render_all(job: Path, asker: Asker | None, *, only: set[str] | None = None, journal: Journal | None = None,
               options: dict | None = None) -> list[dict]:
    """Renders the clips and writes every step to the job's journal (events.jsonl)."""
    options = {**opts.DEFAULTS, **(options or {})}
    own = journal is None
    journal = journal or Journal(job, tool="vodcut")
    if asker is not None and asker.journal is None:
        asker.journal = journal
    try:
        return _render_all(job, asker, only, journal, options)
    finally:
        close_tickets()
        if own:
            journal.close()


RENDERS = "renders.json"


def _read_json_file(path: Path, emit=None, what: str = ""):
    """A job file's data, or None when it is missing. A file that cannot be read is not taken for an empty one: it is
    kept aside as <name>.bad, the journal says so, and None is returned (the step then works as if nothing was recorded)."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        aside = path.with_name(path.name + ".bad")
        try:
            os.replace(path, aside)
        except OSError:
            aside = path
        if emit is not None:
            emit(ERROR, stage="render", message=f"{path.name} could not be read ({type(e).__name__}: {e}); kept as {aside.name}, "
                                               f"{what or 'its records are made again'}"[:500])
        return None


def _write_json_file(path: Path, data) -> None:
    """Whole or not at all: written next to the file and moved into place."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def _earlier_rows(job: Path, emit=None) -> dict[str, dict]:
    """{clip id: its row} from the last renders.json."""
    rows = _read_json_file(job / RENDERS, emit, "clips without a record are made again")
    if not isinstance(rows, list):
        return {}
    return {r["id"]: r for r in rows if isinstance(r, dict) and "id" in r}


def _rendered_bounds(job: Path, rows: dict[str, dict] | None = None) -> dict[str, tuple[float, float]]:
    """{clip id: (start_s, end_s)} the clips in clips/ were rendered with, from the last renders.json."""
    rows = _earlier_rows(job) if rows is None else rows
    return {cid: (r["start_s"], r["end_s"]) for cid, r in rows.items() if "start_s" in r and "end_s" in r}


def _needs_model_again(row: dict | None, asker, options: dict) -> str | None:
    """Why a finished clip is made or checked again now that a model answers, or None.

    «layout»: its layout is the whole frame only because no model answer was usable (out of quota, busy, no model);
    «ads»: the ad blur is on but the banner question got no usable answer, so nothing was blurred;
    «critic»: the critic is on but never gave a verdict on it (the process ended between the encode and the check)."""
    if asker is None:
        return None
    if row is None:
        return "critic" if options.get("critic") else None
    if str(row.get("layout_by") or "").startswith("default:"):
        return "layout"
    if options.get("ad_blur") and str(row.get("ads_by") or "").startswith("none:"):
        return "ads"
    if options.get("critic") and (row.get("critic") or {}).get("outcome") in (None, "unchecked"):
        return "critic"
    return None


def drop_stale(job: Path, clip: dict, rendered: dict[str, tuple[float, float]]) -> bool:
    """A clip whose bounds changed since its video was made (Fit moved them, or Fit was switched off) is made again: its
    mp4, captions and piece of video go. Without a record of the bounds (a job rendered before stage 11) the clip was
    rendered at the bounds pass 2 gave it. True when something was dropped."""
    before = rendered.get(clip["id"])
    if before is None:
        p2 = clip.get("pass2") or clip
        before = (p2["start_s"], p2["end_s"])
    if abs(before[0] - clip["start_s"]) < 0.01 and abs(before[1] - clip["end_s"]) < 0.01:
        return False
    dropped = False
    for path in (job / "clips" / f"{clip['id']}.mp4", job / "clips" / f"{clip['id']}.ass", job / "pieces" / f"{clip['id']}.mp4",
                 job / "pieces" / f"{clip['id']}.mp4.offset"):
        if path.exists():
            path.unlink()
            dropped = True
    return dropped


def _render_all(job: Path, asker: Asker | None, only: set[str] | None, journal: Journal, options: dict) -> list[dict]:
    emit = journal.emit
    earlier = _earlier_rows(job, emit)
    _read_json_file(job / LAYOUT_CACHE, emit, "the layouts are asked again")    # a broken cache is reported once and set aside
    rendered = _rendered_bounds(job, earlier)
    rows = dict(earlier)                     # every clip's latest row; renders.json is rewritten after each clip
    result = json.loads((job / "clips.json").read_text(encoding="utf-8"))
    info = result["source"]
    segments = json.loads((job / "transcript.json").read_text(encoding="utf-8"))["segments"]
    out_dir = job / "clips"
    report = []
    clips = [c for c in result["clips"] if not only or c["id"] in only]
    stopped = None                           # the model is out of quota: the clips left are not made with a worse layout

    def keep(row: dict) -> None:
        rows[row["id"]] = row
        try:
            _write_json_file(job / RENDERS, list(rows.values()))
        except OSError as e:          # the clips go on; the file is written again after the next clip and at the end
            (job / (RENDERS + ".tmp")).unlink(missing_ok=True)
            emit(ERROR, stage="render", message=f"renders.json could not be written: {type(e).__name__}: {e}"[:500])

    def fail(clip: dict, error: str) -> None:
        row = {"id": clip["id"], "status": "failed", "error": error}
        report.append(row)
        if (rows.get(clip["id"]) or {}).get("status") != "done" or not (out_dir / f"{clip['id']}.mp4").exists():
            keep(row)                        # a clip that is still on disk keeps the row it was made with
        emit(CLIP_FAILED, clip=clip["id"], title=clip["title"], error=error)

    emit(STAGE, name="render", clips=len(clips), options=options, model=asker is not None)
    held: dict[str, str] = {}
    for clip in clips:                       # first: files of clips whose bounds moved go (before any piece is fetched)
        try:
            if drop_stale(job, clip, rendered):
                rows.pop(clip["id"], None)
        except OSError as e:      # Windows: the clip is open in a player or held by an antivirus; only this clip waits
            held[clip["id"]] = (f"Старый файл клипа не удаляется — он открыт в другой программе. Закройте его и запустите монтаж снова. "
                                f"({type(e).__name__}: {e})")[:400]
    scene = Scene(job)
    said_faces = False
    todo = [c for c in clips if c["id"] not in held and (not (out_dir / f"{c['id']}.mp4").exists()
                                                         or _needs_model_again(rows.get(c["id"]), asker, options))]
    checks: list[tuple[dict, critic.Item, dict]] = []      # made clips waiting for the critic: looked at a batch at a time

    def check_now() -> None:
        """The critic on the clips waiting for it, in calls of up to critic.BATCH clips (B12); then they are ready."""
        if not checks or asker is None:
            return
        for clip, _, _ in checks:
            emit(PROGRESS, stage="render", clip=clip["id"], step="critic")
        reviews = _check_all(asker, [item for _, item, _ in checks], emit, options)
        for (clip, item, row), review in zip(checks, reviews):
            row = {**row, "layout": review.decision.mode, "critic": review.as_event()}
            keep(row)
            report.append(row)
            emit(CLIP_READY, clip=clip["id"], title=clip["title"], start_s=clip["start_s"], end_s=clip["end_s"],
                 **{k: v for k, v in row.items() if k not in ("id", "status", "file", "start_s", "end_s")}, file=_in_job(item.video, job))
        checks.clear()
    for i, clip in enumerate(clips, 1):
        out = out_dir / f"{clip['id']}.mp4"
        if clip["id"] in held:
            fail(clip, held[clip["id"]])
            continue
        if stopped:
            fail(clip, stopped)
            continue
        again = _needs_model_again(rows.get(clip["id"]), asker, options) if out.exists() else None
        if out.exists() and again is None:
            row = {"id": clip["id"], "status": "done", "file": str(out), "start_s": clip["start_s"], "end_s": clip["end_s"]}
            note = (rows.get(clip["id"]) or {}).get("critic")
            if note:
                row["critic"] = note
            report.append(row)
            emit(CLIP_READY, clip=clip["id"], title=clip["title"], file=_in_job(out, job), existing=True, **({"critic": note} if note else {}))
            continue
        checkpoint(job, journal, "render")      # between two clips: a paused montage keeps every clip made so far
        emit(PROGRESS, stage="render", done=i, total=len(clips), clip=clip["id"], title=clip["title"])
        try:
            step = lambda name: emit(PROGRESS, stage="render", clip=clip["id"], step=name)  # noqa: E731
            step("video")
            video, offset = fetch_piece(info, clip["start_s"], clip["end_s"], job / "pieces" / f"{clip['id']}.mp4")
            start, end = clip["start_s"] - offset, clip["end_s"] - offset
            words = captions.clip_words(segments, clip["start_s"], clip["end_s"])
            duration_ms = (end - start) * 1000
            step("frames")
            made_with = _cache_read(job).get(clip["id"]) if again == "critic" else None
            checking_only = isinstance(made_with, dict) and isinstance(made_with.get("layout"), dict)
            if again == "critic" and not checking_only:
                again = None                  # what it was made with is not known: it is made again, then checked
            try:                              # the frames serve the webcam found on this computer too (B12)
                shots = frames.extract(video, frames.sample_times(start, end), job / "frames" / clip["id"])
            except Exception:  # noqa: BLE001 — without a model (or only checking) the whole frame / the old layout, as before B12
                if asker is not None and not checking_only:
                    raise
                shots = None
            if checking_only and isinstance(made_with, dict):     # only checked: the layout it was made with
                layout, how, chose = made_with["layout"], made_with.get("how", "model"), {"votes": made_with.get("votes") or [], "cached": True}
            elif shots is None:
                layout, how, chose = {**DEFAULT.as_dict(), "camera": None}, "default: no model", {}
            else:
                layout, how, chose = choose_layout(
                    asker, video, start, end, words, job / "frames" / clip["id"], shots=shots, job=job, clip_id=clip["id"], scene=scene)
            if options["ad_blur"] and shots and asker is not None and not asker.quota_error:
                boxes, ads_by = recording_ads(asker, scene, lambda: _recording_frames(job, info, todo or [clip]))
            elif options["ad_blur"] and asker is None:
                boxes, ads_by = [], "none: no model"      # made again with the blur once a model answers
            else:
                boxes, ads_by = [], "off"
            if asker is not None and asker.quota_error:
                stopped = f"the model refused: out of quota or credit, the clips left are not made. {asker.quota_error}"[:400]
                emit(ERROR, stage="render", message=stopped)
                fail(clip, stopped)
                continue
            if asker is not None and how.startswith("default:"):
                emit(ERROR, stage="render", message=f"{clip['id']}: no usable layout answer, the whole frame is shown; "
                                                    f"the next render asks again ({how})"[:500])
            if asker is not None and ads_by.startswith("none:"):
                emit(ERROR, stage="render", message=f"{clip['id']}: no usable ad answer, nothing is blurred; "
                                                    f"the next render asks again ({ads_by})"[:500])
            if "faces cannot be looked for here" in how and not said_faces:
                said_faces = True                # once a job: every clip now asks the model, as before B12
                emit(ERROR, stage="render", message=f"the webcam is not looked for on this computer, the model is asked for every clip: {how}"[:500])
            emit(LAYOUT_CHOSEN, clip=clip["id"], mode=layout["mode"], by=how, **chose,
                 **({"frames": [_in_job(p, job) for p in shots]} if shots and all(job in Path(p).parents for p in shots) else {}))
            emit(ADS_FOUND, clip=clip["id"], count=len(boxes), boxes=[list(b) for b in boxes], by=ads_by)
            tones = bleep.tones(words) if options["bleep"] else []
            shown = profanity.masked(bleep.masked(words) if options["bleep"] else words)   # swearing starred on screen, as in production
            accent = peak.choose(shown, duration_ms) if options["peak_lines"] else None
            decision = critic.Decision(layout["mode"], layout["scene_crop"], layout["streamer_crop"], layout.get("camera"), hook=profanity.mask(clip["title"]))

            def make(d: critic.Decision, path: Path, video=video, start=start, end=end, shown=shown, duration_ms=duration_ms,
                     accent=accent, boxes=boxes, tones=tones) -> Path:
                ass = path.with_suffix(".ass")
                ass.write_text(captions.build_ass(shown, duration_ms, hook=d.hook or "", hook_end_ms=HOOK_MS, position=d.captions, peak=accent,
                                                  seam=captions.seam_y(d.mode)), encoding="utf-8")
                return ffmpeg.render(video, path, start, end, Layout(d.mode, d.scene_crop, d.streamer_crop), ass, FONTS_DIR,
                                     blur_boxes=boxes, bleep=bleep.audio_filter(tones), loudness=options["loudness"])

            row = {"id": clip["id"], "status": "done", "file": str(out), "start_s": clip["start_s"], "end_s": clip["end_s"],
                   "layout": decision.mode, "layout_by": how,
                   "ads_blurred": len(boxes), "ads_by": ads_by, "bleeps": len(tones), "peak": list(accent.lines) if accent else None,
                   "loudness": options["loudness"]}
            if again == "critic":
                step("critic")               # made earlier but never checked: only the check is done now, the clip is not made again
                earlier_row = rows.get(clip["id"]) or {}
                row.update({k: earlier_row[k] for k in ("layout", "layout_by", "ads_blurred", "ads_by", "bleeps", "peak", "loudness")
                            if k in earlier_row})
            else:
                step("captions")
                out_dir.mkdir(parents=True, exist_ok=True)
                step("encode")
                make(decision, out)
                keep(row)                    # made: recorded before the check, so a check cut short is done on the next run
            if options["critic"] and asker is not None:
                facts = {"duration_s": end - start, "channel": info.get("channel"), "stream_title": info.get("title"), "title": clip["title"]}
                checks.append((clip, critic.Item(clip["id"], out, decision, facts, job / "critic" / clip["id"], make), row))
                if len(checks) >= critic.BATCH:
                    check_now()
                continue
            report.append(row)
            emit(CLIP_READY, clip=clip["id"], title=clip["title"], start_s=clip["start_s"], end_s=clip["end_s"],
                 **{k: v for k, v in row.items() if k not in ("id", "status", "file", "start_s", "end_s")}, file=_in_job(out, job))
        except Exception as e:  # noqa: BLE001 — one broken clip must not stop the others; the reason is reported
            fail(clip, f"{type(e).__name__}: {e}"[:400])
    check_now()
    order = {c["id"]: n for n, c in enumerate(clips)}
    report.sort(key=lambda r: order.get(r["id"], len(order)))
    # rows of clips not rendered this time (only=…) stay: their bounds tell drop_stale what their files were made at
    _write_json_file(job / RENDERS, list(rows.values()))
    if options.get("critic") and asker is not None:
        unchecked = sum(1 for r in report if r.get("status") == "done" and (r.get("critic") or {}).get("outcome") in (None, "unchecked"))
        if unchecked:          # the person sees «done»; this says the check did not happen for these (the next render asks)
            emit(PROGRESS, stage="missing", step="critic", done=unchecked, total=len(report))
    emit(DONE, stage="render", file=RENDERS, folder=_in_job(out_dir, job),
         report=[{**r, "file": _in_job(Path(r["file"]), job)} if "file" in r else r for r in report])
    return report
