"""The analysis: link or file → audio → transcript → episode scan → rating → clips.json.

Every step writes its result into the job folder, and a rerun skips the steps already done: an interrupted
6-hour stream continues where it stopped.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from smtv_core import paths, prompts
from smtv_core.events import DONE, EPISODE_FOUND, EPISODE_RATED, ERROR, PROGRESS, STAGE, Journal
from smtv_core.asr import filtered_segments
from smtv_core.asr import catalog as speech
from smtv_core.asr.engines import GIGAAM, PARAKEET, Recognizer, engine_for, installed, load_watched, transcribe, wav_duration
from smtv_core.asr.language import choose, detect
from smtv_core.pause import Paused, checkpoint
from smtv_core.settings import Settings

from . import avatar, fit, ingest, pass1, pass2, pick
from .model import Asker


class RunError(Exception):
    pass


def job_dir(source: str, base: Path | None = None) -> Path:
    """One folder per recording: the same link or file always lands in the same folder, and two recordings never share one.

    A readable part (the file's name in Latin letters, the recording's id) and a short hash of what makes the recording
    itself (`ingest.source_key`): «Стрим вчера.mp4» in two folders are two jobs; `…/videos/123` and `…/videos/123?t=1h`
    are one. The name always passes the server's check of job names (a letter or a digit first).
    """
    prefix = paths.safe_name(ingest.readable_name(source), fallback="video", limit=60)
    return (base or paths.data_dir() / "vodcut") / f"{prefix}_{paths.short_hash(ingest.source_key(source))}"


def _save(path: Path, data) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def _load(path: Path):
    """The step's saved result; None when it is not there or unreadable — then the step is made again."""
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
    except (OSError, ValueError):
        return None


SCAN_ANSWERS, RATING_ANSWERS = "pass1.windows.json", "pass2.items.json"   # every good answer, kept as it comes


def _answers(path: Path):
    """(the answers kept so far, a function that keeps new ones): a failed or stopped step does not pay for them again."""
    kept = _load(path)
    kept = kept if isinstance(kept, dict) else {}

    def keep(got: dict) -> None:
        kept.update(got)
        _save(path, kept)
    return dict(kept), keep


def _enough(missing: int, total: int, model_errors: list[str], what: str) -> None:
    """Stops the run when the model answered none or fewer than half of the parts: clips from the rest would be a guess.
    What was answered is kept (SCAN_ANSWERS, RATING_ANSWERS), so «Продолжить» asks only for the rest."""
    answered = total - missing
    if total and (answered == 0 or answered < total / 2):
        reason = model_errors[0] if model_errors else "ответы не подошли по форме даже после повторного вопроса"
        raise RunError(f"Модель не ответила на {missing} из {total} {what}. Причина: {reason}. "
                       "Проверьте модель в настройках и нажмите «Продолжить»: полученные ответы сохранены, "
                       "спросим только остальное."[:900])


def source_facts(info: dict, job: Path, duration: float) -> dict:
    """The `source_ready` event's data: the recording's title, channel, platform, length, link or file, and the channel's
    picture (a job file), fetched here once when it is a Twitch or YouTube channel — best effort, never a failure."""
    picture = avatar.existing(job)
    if not picture and avatar.channel_page(info) and avatar.due(job):
        picture = avatar.fetch(job, job.parent / ".avatars")
    facts = {"kind": info.get("kind") or "link", "title": info.get("title") or "", "channel": info.get("channel") or "",
             "platform": info.get("platform") or "", "duration_s": round(float(duration or 0), 1),
             "source": info.get("url") or info.get("path") or "", "language": info.get("language") or "", "avatar": picture or ""}
    return {k: v for k, v in facts.items() if v not in ("", None)} | {"kind": facts["kind"]}


def run(source: str, asker: Asker, *, job: Path | None = None, language: str = "auto", channel: str = "", context: str = "a stream",
        workers: int = 4, max_clips: int | None = None, journal: Journal | None = None,
        recognizer_for: Callable[[str], Recognizer] | None = None, precise: bool = False) -> dict:
    """Every step and its outcome go to the job's journal (events.jsonl); an error is written there before it is raised."""
    job = job or job_dir(source)
    own = journal is None
    journal = journal or Journal(job, tool="vodcut")
    if asker.journal is None:
        asker.journal = journal
    try:
        return _run(source, asker, job, journal, language=language, channel=channel, context=context, workers=workers,
                    max_clips=max_clips, recognizer_for=recognizer_for, precise=precise)
    except Paused:
        raise                       # a pause is not an error: the job said so itself (`cancelled`, graceful)
    except RunError as e:
        journal.emit(ERROR, stage="analysis", message=str(e))
        raise
    except Exception as e:
        journal.emit(ERROR, stage="analysis", message=f"{type(e).__name__}: {e}"[:1000])
        raise
    finally:
        if own:
            journal.close()


def _run(source: str, asker: Asker, job: Path, journal: Journal, *, language: str, channel: str, context: str, workers: int,
         max_clips: int | None, recognizer_for: Callable[[str], Recognizer] | None, precise: bool = False) -> dict:
    emit = journal.emit
    timings: dict[str, float] = {}
    steps = 6 if precise else 5         # the sixth: Fit, the exact cut by words (the «precise» switch)

    t = time.monotonic()
    emit(STAGE, name="audio", step=1, steps=steps, source=source)
    shown = [-1]

    def on_progress(done: int, total: int) -> None:          # the audio through StreamMoment: every 5 % of its segments
        pct = int(100 * done / max(total, 1))
        if pct // 5 > shown[0]:
            shown[0] = pct // 5
            emit(PROGRESS, stage="download", percent=pct, done=done, total=total)

    info = ingest.ingest(source, job, on_wait=lambda place: emit(PROGRESS, stage="download", queue=place), on_progress=on_progress)
    wav = job / "audio.wav"
    duration = info.get("duration_s") or wav_duration(wav)
    emit("source_ready", **source_facts(info, job, duration))   # what the request is about, for every reader at once
    timings["audio_s"] = round(time.monotonic() - t, 1)
    emit(PROGRESS, stage="audio", duration_s=round(duration, 1), seconds=timings["audio_s"])

    # a pause asked for on the page stops the job here, between two steps: what is done stays done (smtv_core.pause)
    checkpoint(job, journal, "speech")
    t = time.monotonic()
    transcript = _load(job / "transcript.json")
    if transcript is None:
        def download_tick():
            shown = [-1]

            def tick(mb, total):
                pct = int(100 * mb / max(total, 1))
                if pct // 5 > shown[0]:
                    shown[0] = pct // 5
                    emit(PROGRESS, stage="model", percent=pct, done=mb, total=total)
            return tick

        def listen(lang: str) -> Recognizer:
            """GigaAM or Parakeet, only to tell the language; one not on this computer yet is downloaded now."""
            engine = engine_for(lang)
            if installed(engine):
                return Recognizer(engine).load()
            emit(STAGE, name="model", step=2, steps=steps, engine=engine.name, language=lang)
            try:
                return load_watched(engine, download_tick())
            except Exception as e:  # noqa: BLE001 — the network, the disk, the model host: the reason goes to the person
                raise RunError(f"could not download the {engine.name} speech model (about {engine.size_mb / 1024:.1f} GB) for "
                               f"{'Russian' if lang == 'ru' else lang}: {type(e).__name__}: {e}"[:600]) from e

        def load(lang: str):
            """The model chosen for `lang` in «Settings → Speech» (by default GigaAM for Russian, Parakeet for its 25
            languages, Whisper for the rest); a local one not on this computer yet is downloaded now, with its progress."""
            settings = Settings.load()
            model, _source = speech.model_for(lang, settings)
            if model.id in speech.ONNX:
                return listen(lang)
            try:
                rec = speech.recognizer(model, lang, settings)     # a cloud model takes the key of the person's provider
            except RuntimeError as e:
                raise RunError(str(e)) from e
            if model.where == "local" and not speech.is_installed(model):
                emit(STAGE, name="model", step=2, steps=steps, engine=model.id, language=lang)
                try:
                    from smtv_core.asr import whisper
                    whisper.download(progress=download_tick())
                except Exception as e:  # noqa: BLE001
                    raise RunError(f"could not download the {model.title} speech model (about {model.size_mb / 1024:.1f} GB): "
                                   f"{type(e).__name__}: {e}"[:600]) from e
            return rec.load()

        make = recognizer_for or load
        hear = recognizer_for or listen
        lang = language
        if lang == "auto":
            lang = choose(info.get("language"))      # the recording's own language when it says one
            if lang is None:
                emit(STAGE, name="language", step=2, steps=steps)
                if recognizer_for is None and not installed(PARAKEET) and not installed(GIGAAM) and \
                        speech.is_installed(speech.WHISPER_M) and speech.package_ready(speech.WHISPER_M):
                    # only Whisper is here (chosen for every language): it tells the language itself, nothing is downloaded
                    from smtv_core.asr import whisper
                    lang = whisper.detect_language(wav) or "latin"
                elif recognizer_for is not None or installed(PARAKEET):
                    lang = detect(wav, hear("latin"))
                else:
                    # no Parakeet here: GigaAM listens (it writes other languages in Latin letters); unclear → Russian
                    lang = detect(wav, hear("ru"), fallback="ru")
        if not speech.known_language(lang):
            raise RunError(f"no speech model for language {lang!r}")
        engine = speech.model_for(lang, Settings.load())[0]
        rec = make(lang)                              # a model not here yet downloads first, with its own progress
        emit(STAGE, name="speech", step=2, steps=steps, engine=engine.id, language=lang, duration_s=round(duration, 1))
        shown = [-1]

        def tick(done_s, total_s):
            step = int(10 * done_s / max(total_s, 1e-9))
            if step > shown[0]:
                shown[0] = step
                emit(PROGRESS, stage="speech", percent=min(100, step * 10))

        segs = transcribe(wav, rec, progress=tick)
        transcript = {"language": lang, "engine": engine.id, "segments": segs}
        if not filtered_segments(segs):
            # not kept: a rerun (another model, a key added) listens again instead of reading «no speech» from here
            raise RunError(f"no speech found in the recording ({engine.title})")
        _save(job / "transcript.json", transcript)
    segments = filtered_segments(transcript["segments"])
    timings["speech_s"] = round(time.monotonic() - t, 1)
    if not segments:
        raise RunError("no speech found in the recording")

    platform = info.get("platform") or "stream"
    meta = f"; stream: {platform} recording" + (f" {info['id']}" if info.get("id") else "") + (f" channel {channel or info.get('channel')}" if channel or info.get("channel") else "")

    checkpoint(job, journal, "scan")
    t = time.monotonic()
    scan = _load(job / "pass1.json")
    complete = scan is not None        # every window answered: the scan is final; otherwise a rerun asks the rest
    if scan is None:
        emit(STAGE, name="scan", step=3, steps=steps, segments=len(segments))
        known, keep = _answers(job / SCAN_ANSWERS)
        scan = pass1.run(segments, asker, meta=meta, workers=workers, known=known, on_answer=keep,
                         progress=lambda n, total: emit(PROGRESS, stage="scan", done=n, total=total))
        if asker.quota_error:
            raise RunError(f"the model refused: out of quota or credit. {asker.quota_error[:200]}")
        _enough(len(scan["missing"]), scan["windows"], scan["model_errors"], "частей записи")
        complete = not scan["missing"]
        if complete:
            _save(job / "pass1.json", scan)
        else:
            emit(PROGRESS, stage="missing", step="scan", done=len(scan["missing"]), total=scan["windows"])
        for e in scan["episodes"]:
            emit(EPISODE_FOUND, episode_id=e["episode_id"], start_s=e["start_s"], end_s=e["end_s"], episode_type=e.get("episode_type"),
                 why_interesting=e.get("why_interesting"), text_preview=e.get("text_preview", "")[:200])
    timings["scan_s"] = round(time.monotonic() - t, 1)

    checkpoint(job, journal, "rating")
    t = time.monotonic()
    rating = _load(job / "pass2.json") if complete else None
    if rating is None:
        emit(STAGE, name="rating", step=4, steps=steps, episodes=len(scan["episodes"]))
        known, keep = _answers(job / RATING_ANSWERS)
        rating = pass2.run(segments, scan["episodes"], asker, channel=channel or info.get("channel") or "", context=context, workers=workers,
                           known=known, on_answer=keep, progress=lambda n, total: emit(PROGRESS, stage="rating", done=n, total=total))
        if asker.quota_error:
            raise RunError(f"the model refused: out of quota or credit. {asker.quota_error[:200]}")
        missing = rating.get("missing", [])
        _enough(len(missing), len(rating["episodes"]), rating.get("model_errors", []), "найденных моментов")
        if missing:
            emit(PROGRESS, stage="missing", step="rating", done=len(missing), total=len(rating["episodes"]))
        elif complete:
            _save(job / "pass2.json", rating)
        for e in rating["episodes"]:
            emit(EPISODE_RATED, **{k: e.get(k) for k in ("episode_id", "status", "verdict", "score", "format", "title", "reason", "trim")
                                   if e.get(k) is not None})
    timings["rating_s"] = round(time.monotonic() - t, 1)

    checkpoint(job, journal, "pick")
    emit(STAGE, name="pick", step=5, steps=steps)
    clips = pick.pick(rating["episodes"], duration, max_clips)
    if precise and clips:
        checkpoint(job, journal, "fit")
        t = time.monotonic()
        emit(STAGE, name="fit", step=6, steps=steps, clips=len(clips))
        clips = fit.refine(job, clips, transcript["segments"], duration, asker, workers=workers, emit=emit)
        if asker.quota_error:
            raise RunError(f"the model refused: out of quota or credit. {asker.quota_error[:200]}")
        timings["fit_s"] = round(time.monotonic() - t, 1)
    result = {"source": info, "duration_s": round(duration, 1), "language": transcript["language"], "speech_engine": transcript["engine"],
              "prompts_version": prompts.version(), "model": f"{asker.model_for('scan').provider}/{asker.model_for('scan').model or 'default'}",
              "episodes_found": len(scan["episodes"]), "episodes_rated": sum(1 for e in rating["episodes"] if e.get("status") == "ok"),
              "tokens": {"in": asker.tokens_in, "out": asker.tokens_out}, "timings": timings, "precise": precise, "clips": clips}
    _save(job / "clips.json", result)
    emit(DONE, stage="analysis", file="clips.json", **{k: result[k] for k in ("duration_s", "episodes_found", "episodes_rated", "tokens", "timings")},
         clips=[{k: c[k] for k in ("id", "start_s", "end_s", "duration_s", "score", "title")} for c in clips])
    return result
