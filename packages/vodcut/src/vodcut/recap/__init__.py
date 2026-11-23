"""The recap (the «recap» switch): one stream becomes a 20–30 minute 16:9 video — the stream itself, cut down, in stream
order, at a fast pace, with the webcam brought forward when the streamer reacts. Ported from production
(`externals/media-analysis/runtime/vod/recap.py` and `recap_signals.py`).

Steps, all in <job>/recap/:
  story    the recap agent reads the rated episodes and the whole transcript → story.json (story.py);
  signals  each part's piece of video, its loudness, where the webcam is, the ads (signals.py) → signals.json;
  edit     jump cuts, webcam shots on the peaks, the cold open, the chapters (edit.py) → recap.json;
  render   the parts encoded and joined, the cover (encode.py) → video.mp4, cover.jpg, chapters.txt, description.txt.

Nothing is published: the files are the result. Every step is skipped on a rerun when its file is there and still fits.
A recap that fails is reported (`recap_failed`) and leaves the clips as they are.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from smtv_core.events import DONE, PROGRESS, STAGE, Journal
from smtv_core.pause import Paused, checkpoint

from . import edit, encode, signals as signals_step, story as story_step
from .story import RecapError

RECAP_READY, RECAP_FAILED = "recap_ready", "recap_failed"
FOLDER = "recap"


def _save(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def facts_of(job: Path, result: dict, transcript: dict) -> dict:
    """What the story's prompt and the description say about the stream."""
    info = result.get("source") or {}
    return {"channel": info.get("channel") or "", "title": info.get("title") or "", "date": info.get("date") or "",
            "duration_s": float(result.get("duration_s") or info.get("duration_s") or 0), "url": info.get("url") or "",
            "language": transcript.get("language") or ""}


def ready_data(folder: Path, recap: dict, extra: dict) -> dict:
    return {"file": f"{FOLDER}/video.mp4", "cover": f"{FOLDER}/cover.jpg", "chapters_file": f"{FOLDER}/chapters.txt",
            "description_file": f"{FOLDER}/description.txt", "title": recap["title"], "duration_s": recap["duration_s"],
            "source_s": recap["source_s"], "parts": len(recap["parts"]),
            "chapters": [{"start_s": c["start_s"], "title": c["title"]} for c in recap["chapters"]],
            "shots": recap["shots"], "ads_blurred": recap["ads_blurred"], "music_risk": len(recap["music_risk"]), **extra}


def make(job: Path, asker, journal: Journal, *, ad_blur: bool = True, step: int | None = None, steps: int | None = None) -> dict | None:
    """The recap of a job whose analysis is done. Returns what `recap_ready` said, or None when the model found nothing
    worth a recap or the recap failed (both in the journal). A pause asked for stops it between two parts (Paused)."""
    emit = journal.emit
    if asker is not None and asker.journal is None:
        asker.journal = journal         # every model call of the recap goes to the job's journal (model_call)
    folder = job / FOLDER
    started = time.monotonic()
    emit(STAGE, name="recap", model=asker is not None, **({"step": step, "steps": steps} if step else {}))
    try:
        result = _load(job / "clips.json")
        transcript = _load(job / "transcript.json")
        pass2 = _load(job / "pass2.json")
        if not (result and transcript and pass2):
            raise RecapError("the analysis is not finished: clips.json, transcript.json or pass2.json is missing")
        facts = facts_of(job, result, transcript)
        segments = transcript["segments"]

        story = _load(folder / "story.json")
        if story is None:
            if asker is None:
                raise RecapError("no model is connected: the story of a recap is written by it")
            emit(PROGRESS, stage="recap", step="story")
            story = story_step.ask(asker, facts, pass2["episodes"], segments)
            if asker.quota_error:
                raise RecapError(f"the model refused: out of quota or credit. {asker.quota_error[:200]}")
            _save(folder / "story.json", story)
        if story.get("status") == "skipped":
            emit(DONE, stage="recap", skipped=True, reason="the model found nothing worth a recap", file=f"{FOLDER}/story.json")
            return None

        checkpoint(job, journal, "recap")
        from ..render import close_tickets
        try:
            found = signals_step.collect(job, story, result.get("source") or {}, asker, ad_blur=ad_blur,
                                         progress=lambda what, done, total: emit(PROGRESS, stage="recap", step=what, done=done, total=total),
                                         unlooked=lambda n, total: emit(PROGRESS, stage="missing", step="look", done=n, total=total))
        finally:
            close_tickets()             # the pieces are here: the slot in StreamMoment's queue goes to the next one
        recap = edit.plan(story, found, story_step.words_of(segments), facts)
        _save(folder / "recap.json", recap)
        (folder / "chapters.txt").write_text(edit.chapters_text(recap["chapters"]), encoding="utf-8")
        (folder / "description.txt").write_text(recap["description"] + "\n", encoding="utf-8")

        rendered = encode.render(recap, found, folder,
                                 progress=lambda done, total, _: emit(PROGRESS, stage="recap", step="encode", done=done, total=total),
                                 between_parts=lambda: checkpoint(job, journal, "recap"))
        data = ready_data(folder, recap, {**rendered, "seconds": round(time.monotonic() - started, 1), "existing": rendered["encoded"] == 0})
        _save(folder / "ready.json", data)
        emit(RECAP_READY, **data)
        emit(DONE, stage="recap", file=f"{FOLDER}/recap.json")
        return data
    except Paused:
        raise
    except Exception as e:  # noqa: BLE001 — the recap is extra: its failure is reported and the clips stay
        error = f"{type(e).__name__}: {e}"[:600]
        emit(RECAP_FAILED, error=error)
        emit(DONE, stage="recap", failed=True, reason=error)   # the request is finished: its clips are there
        return None
