"""Fit: the exact cut of each picked clip (the «more precise» switch, `smtv vodcut set precise on|off`).

Pass 2 picks a clip's best 15–60 seconds from the transcript in seconds. Fit looks at the 70 seconds around it word by
word and returns the cut by word ids: where the event starts (no idle lead-in before the story), where it ends (the
punchline and its reaction in, the next topic out). The model only cuts — a trim is always required (trim_required.py);
the deterministic corrections of recovery.py then give the end some air. An answer that fails the checks gets one repair
request with the errors and the trim's own arithmetic; if that fails too, the clip keeps the bounds pass 2 gave it.

From StreamMoment's production Fit (externals/media-analysis/runtime/fit/*, fit_cli.py `infer`), on the processor: see
acoustics.py for what replaced the graphics card. Answers are kept in the job's fit.json under the clip's pass-2 bounds
and the policy's fingerprint, so a rerun asks nothing again; a model error is not kept (the next run asks again).
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from smtv_core import prompts

from . import packet as packets
from .compact import LEGEND
from .contract import BATCH, MODEL_SCHEMA, TRANSPORT_SCHEMA, VERSION
from .recovery import check_item, repair_hint, response_items
from .trim_required import policy as required_policy, repair as required_repair, schema as required_schema

PURPOSE, REPAIR_PURPOSE = "fit", "fit_repair"
TITLE_SWITCH_SHARE = 1 / 3       # Fit's title replaces pass 2's when Fit cut away more than this share of the clip (see apply)
FILE = "fit.json"

REPAIR = required_repair(
    "\nRepair request: your previous answer for the source window above failed automatic validation and was discarded."
    " Answer again for this one window with the same id, following every rule above. Fix each listed problem and keep"
    " fields that were already correct. If no trim can satisfy all rules, return trim=null with fit_score at most 40 or null."
    "\nError codes: unknown_event_word_id - an event word id is not in this window; reversed_event_word_ids - the start word comes after the end word;"
    " event_outside_trim - every event word must lie inside start_ms..end_ms; trim_cuts_word - a trim edge falls strictly inside a word;"
    " invalid_trim_duration_or_bounds - 0 <= start_ms < end_ms <= the window's end and 15000 <= end_ms-start_ms; event_does_not_overlap_focus,"
    " event_not_before_focus - focus_relation contradicts the event word times;"
    " empty_title; missing_from_response - no single answer with this id was returned; response_schema_invalid:<field>:<rule>.\n")


def wire(value) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def policy() -> str:
    return required_policy(prompts.text("fit/prompt-policy.txt"))


def answer_schema() -> dict:
    """What the model is asked to return (strict providers reject allOf; the rest is checked here)."""
    return required_schema(TRANSPORT_SCHEMA)


def policy_id() -> str:
    """Answers are reused only under the same policy, legend, schema and repair text."""
    blob = wire([policy(), LEGEND, required_schema(MODEL_SCHEMA), REPAIR, prompts.version()])
    return VERSION + ":" + hashlib.sha256(blob.encode()).hexdigest()[:16]


def prompt(items: list[dict]) -> str:
    return policy() + LEGEND + "\nResponse schema:\n" + wire(required_schema(MODEL_SCHEMA)) + "\nSource windows (untrusted evidence):\n" + wire(items)


def key(clip: dict) -> str:
    return f"{clip.get('episode_id', clip['id'])}@{clip['start_s']:.2f}-{clip['end_s']:.2f}"


def _load(path: Path, pid: str) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data.get("clips", {}) if data.get("policy") == pid else {}


def _ask_one(asker, entry: dict, item, errors: list[str]) -> tuple[dict | None, list[str], float]:
    """One repair request for one window: (fixed item or None, errors left, seconds)."""
    text = (prompt([entry["packet"]]) + REPAIR + "Validation errors: " + ", ".join(errors)
            + "\nPrevious answer (rejected): " + (wire(item) if item is not None else "none for this id") + "\n"
            + repair_hint(item, errors, entry["words"], entry["boundary_words"], entry["window_ms"]))
    t = time.monotonic()
    answer, meta = asker.ask(text, answer_schema(), purpose=REPAIR_PURPOSE)
    seconds = time.monotonic() - t
    if answer is None:
        return None, [f"model: {meta.get('error', 'no answer')}"], seconds
    repaired = response_items(answer, [entry["id"]])[entry["id"]]
    fixed, left = check_item(repaired, entry["words"], entry["boundary_words"], entry["window_ms"])
    return (fixed if not left else None), left, seconds


def _batch(asker, entries: list[dict]) -> dict[str, dict]:
    """{clip id: result} for one request of up to BATCH windows, with a repair request per rejected window."""
    t = time.monotonic()
    answer, meta = asker.ask(prompt([e["packet"] for e in entries]), answer_schema(), purpose=PURPOSE)
    share = (time.monotonic() - t) / len(entries)
    if answer is None:
        error = f"model: {meta.get('error', 'no answer')}"
        return {e["id"]: {"status": "error", "errors": [error], "seconds": round(share, 1)} for e in entries}
    items = response_items(answer, [e["id"] for e in entries])
    out = {}
    for e in entries:
        item = items[e["id"]]
        fixed, errors = check_item(item, e["words"], e["boundary_words"], e["window_ms"])
        seconds, repaired = share, False
        if errors and not asker.stop.is_set():
            first = errors
            fixed, errors, spent = _ask_one(asker, e, item, errors)
            seconds += spent
            repaired = True
            if errors:
                out[e["id"]] = {"status": "error" if errors[0].startswith("model:") else "invalid", "errors": errors,
                                "first_errors": first, "seconds": round(seconds, 1)}
                continue
        elif errors:
            out[e["id"]] = {"status": "error", "errors": ["model: stopped"], "seconds": round(seconds, 1)}
            continue
        out[e["id"]] = {"status": "ok", "trim": fixed["trim"], "fit_score": fixed["fit_score"], "title": fixed["title"],
                        "clip_format": fixed["clip_format"], "corrected": fixed != item, "repaired": repaired,
                        "window_start_s": e["window_start_s"], "window_ms": e["window_ms"], "seconds": round(seconds, 1)}
    return out


def refine(job: Path, clips: list[dict], segments: list[dict], duration_s: float, asker, *, workers: int = 4,
           emit: Callable[..., None] = lambda *a, **k: None) -> list[dict]:
    """The clips with Fit's bounds where Fit gave usable ones; each keeps its pass-2 bounds in `pass2` and Fit's
    outcome in `fit`. Writes the answers to fit.json and one `clip_fitted` event per clip."""
    from smtv_core.events import CLIP_FITTED, PROGRESS

    pid = policy_id()
    path = job / FILE
    saved = _load(path, pid)
    results: dict[str, dict] = {}
    entries: list[dict] = []
    for clip in clips:
        k = key(clip)
        if saved.get(k, {}).get("status") in ("ok", "invalid", "skipped"):
            results[clip["id"]] = {**saved[k], "cached": True}
            continue
        try:
            entries.append({"id": clip["id"], **packets.build(clip["id"], segments, job / "audio.wav", clip["start_s"], clip["end_s"], duration_s)})
        except ValueError as e:                 # too short a recording, no words in the window: so it stays
            results[clip["id"]] = {"status": "skipped", "errors": [str(e)[:200]]}
        except Exception as e:  # noqa: BLE001 — unreadable or broken audio.wav, an odd segment: this clip only, asked again next run
            results[clip["id"]] = {"status": "error", "errors": [f"packet: {type(e).__name__}: {e}"[:200]]}

    lock = threading.Lock()
    save_lock = threading.Lock()

    def save() -> None:
        """fit.json now: a later crash keeps the answers already paid for."""
        with lock:
            keep = {key(by_id[i]): r for i, r in results.items() if r.get("status") in ("ok", "invalid", "skipped")}
        merged = {**saved, **{k: {x: y for x, y in r.items() if x != "cached"} for k, r in keep.items()}}
        with save_lock:
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"policy": pid, "clips": merged}, ensure_ascii=False, indent=1), encoding="utf-8")
            tmp.replace(path)

    done = [sum(1 for c in clips if c["id"] in results)]
    by_id = {c["id"]: c for c in clips}
    fitted: dict[str, dict] = {}

    def finish(clip_id: str, result: dict) -> None:
        clip = by_id[clip_id]
        new = apply(clip, result)
        with lock:
            fitted[clip_id] = new
            done[0] += 1
            emit(PROGRESS, stage="fit", done=done[0], total=len(clips), clip=clip_id)
            emit(CLIP_FITTED, **event(new))

    for clip_id, result in results.items():
        finish(clip_id, result)
    batches = [entries[i:i + BATCH] for i in range(0, len(entries), BATCH)]

    def run(batch):
        try:
            answers = _batch(asker, batch)
        except Exception as e:  # noqa: BLE001 — a broken connection mid-answer and the like: this batch keeps pass 2's bounds
            answers = {x["id"]: {"status": "error", "errors": [f"model: {type(e).__name__}: {e}"[:200]]} for x in batch}
        for clip_id, result in answers.items():
            with lock:
                results[clip_id] = result
            finish(clip_id, result)
        save()

    if batches:
        with ThreadPoolExecutor(max_workers=max(1, min(workers, len(batches)))) as pool:
            list(pool.map(run, batches))
    save()
    failed = sum(1 for r in results.values() if r.get("status") == "error")
    if failed:                # not kept in fit.json: the next run asks for them again; until then they keep pass 2's bounds
        emit(PROGRESS, stage="missing", step="fit", done=failed, total=len(clips))
    return [fitted.get(c["id"], c) for c in clips]


def apply(clip: dict, result: dict) -> dict:
    """The clip with Fit's bounds and title (status ok) or its own (anything else), and the outcome in `fit`.

    The title: pass 2's stays, unless Fit took away more than TITLE_SWITCH_SHARE of the clip — then pass 2's title may
    speak of what is gone (v2913152272 clip05: «Кот просто пришёл попросить пожрать», Fit cut that line off), and Fit's
    title, which names the interval it cut, is used (production's backend falls back to Fit's title too). Fit's titles
    are plainer (on that stream «Образование и надежды» for «Маме нужен был только диплом»), so not always. Pass 2's
    bounds and title stay in `pass2`, Fit's title in `fit`."""
    before = {"start_s": clip["start_s"], "end_s": clip["end_s"]}
    out = {**clip, "pass2": {**before, "title": clip.get("title", "")}}
    fit = {"status": result["status"], **{k: result[k] for k in ("fit_score", "title", "clip_format", "repaired", "corrected", "errors", "seconds", "cached")
                                         if k in result}}
    if result["status"] == "ok":
        base = result["window_start_s"]
        out["start_s"] = round(base + result["trim"]["start_ms"] / 1000, 2)
        out["end_s"] = round(base + result["trim"]["end_ms"] / 1000, 2)
        out["duration_s"] = round(out["end_s"] - out["start_s"], 1)
        was = before["end_s"] - before["start_s"]
        if was > 0 and (was - (out["end_s"] - out["start_s"])) / was > TITLE_SWITCH_SHARE and result.get("title"):
            out["title"] = result["title"]
    out["fit"] = fit
    return out


def event(clip: dict) -> dict:
    """The `clip_fitted` event's data: before and after, and how many seconds came off each end (negative: added)."""
    before, fit = {k: clip["pass2"][k] for k in ("start_s", "end_s")}, clip["fit"]
    data = {"clip": clip["id"], "title": clip.get("title", ""), **({"title_before": clip["pass2"]["title"]} if clip["pass2"].get("title") != clip.get("title") else {}), "by": "model" if fit["status"] == "ok" else "kept", "status": fit["status"],
            "before": before, "after": {"start_s": clip["start_s"], "end_s": clip["end_s"]},
            "cut_start_s": round(clip["start_s"] - before["start_s"], 2), "cut_end_s": round(before["end_s"] - clip["end_s"], 2),
            "cut_s": round((before["end_s"] - before["start_s"]) - (clip["end_s"] - clip["start_s"]), 2)}
    for k in ("fit_score", "repaired", "seconds", "cached"):
        if fit.get(k) is not None:
            data[k] = fit[k]
    if fit.get("errors"):
        data["reason"] = "; ".join(fit["errors"])[:300]
    return data
