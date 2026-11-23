"""Rating: the model judges every scanned episode (verdict, score, best 15–60 s stretch, title).

Eight episodes per request, several requests at once, one more try for episodes missing from an answer. The model's
best_start/best_end (whole seconds) are snapped to word boundaries so they become an exact trim.
"""
from __future__ import annotations

import concurrent.futures as cf
import threading

from smtv_core import prompts

CONTEXT_S = 20.0
VERDICTS = ("strong", "good", "maybe", "skip")
FORMATS = ("story", "joke", "conflict", "banter_with_chat", "reaction", "confession", "rant", "explanation",
           "reading_donation", "gameplay_commentary", "game_dialogue", "other")


def judge_hms(seconds: float) -> str:
    t = int(seconds)
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}"


def parse_hms(text: str) -> int:
    h, m, s = (int(x) for x in str(text).split(":"))
    return h * 3600 + m * 60 + s


def valid_item(item, ids) -> bool:
    if not isinstance(item, dict) or item.get("episode_id") not in ids:
        return False
    return (item.get("verdict") in VERDICTS and item.get("format") in FORMATS and isinstance(item.get("score"), int) and 0 <= item["score"] <= 100
            and isinstance(item.get("title"), str) and item["title"].strip() and isinstance(item.get("reason"), str)
            and item.get("depends_on_video") in ("no", "partly", "yes") and isinstance(item.get("best_start"), str) and isinstance(item.get("best_end"), str))


def block(episode, segments) -> str:
    a, b = episode["start_s"] - CONTEXT_S, episode["end_s"] + CONTEXT_S
    lines = []
    for s in segments:
        if s["end"] < a or s["start"] > b:
            continue
        mark = ">>" if episode["start_s"] - 0.5 <= s["start"] <= episode["end_s"] + 0.5 else "  "
        lines.append(f"{mark} {judge_hms(s['start'])} {s['text'].strip()}")
    head = f"### {episode['episode_id']} ({judge_hms(episode['start_s'])}–{judge_hms(episode['end_s'])}, {int(episode['end_s'] - episode['start_s'])} s)"
    return head + "\nTranscript:\n" + "\n".join(lines)


def snap_to_words(segments, start_s, end_s, lo, hi):
    """Clamp [start_s, end_s] to [lo, hi] and move the edges to word boundaries: the nearest word start / word end."""
    words = [w for s in segments if s["end"] >= lo - 1 and s["start"] <= hi + 1 for w in s.get("words", ())]
    start_s, end_s = max(lo, start_s), min(hi, end_s)
    if end_s <= start_s or not words:
        return None
    starts = [w["start"] for w in words if lo <= w["start"] <= hi]
    ends = [w["end"] for w in words if lo <= w["end"] <= hi]
    if not starts or not ends:
        return None
    snapped_start = min(starts, key=lambda t: abs(t - start_s))
    snapped_end = min(ends, key=lambda t: abs(t - end_s))
    if snapped_end - snapped_start < 3:
        return None
    return {"start_s": round(snapped_start, 3), "end_s": round(snapped_end, 3), "duration_s": round(snapped_end - snapped_start, 1)}


def episode_key(e) -> str:
    """An episode's name in the saved verdicts: its span, which stays when a later scan renumbers the episodes."""
    return f"{float(e['start_s']):.3f}-{float(e['end_s']):.3f}"


def run(segments, episodes, asker, *, channel: str = "", context: str = "a stream", batch: int = 8, workers: int = 4, progress=None,
        known: dict | None = None, on_answer=None) -> dict:
    """Returns {'episodes': [...rated...], 'requests': [...], 'missing': [episode ids], 'model_errors': [...]}.

    `known` — verdicts from an earlier run ({episode_key: verdict}): those episodes are not asked again;
    `on_answer({episode_key: verdict})` gets every good verdict as soon as it is back.
    """
    policy = prompts.fill(prompts.text("vod/pass2-prompt.txt"), channel=channel or "unknown", context=context or "a stream")
    schema = prompts.schema("pass2")
    ordered = sorted(episodes, key=lambda e: e["start_s"])
    known = dict(known or {})
    results = {e["episode_id"]: known[episode_key(e)] for e in ordered if episode_key(e) in known}
    todo = [e for e in ordered if e["episode_id"] not in results]
    by_id = {e["episode_id"]: e for e in ordered}
    batches = [todo[i:i + batch] for i in range(0, len(todo), batch)]
    log, lock, done, model_errors = [], threading.Lock(), [0], []

    def one(bi, group):
        ids = {e["episode_id"] for e in group}
        for attempt in range(2):
            prompt = policy.rstrip() + "\n\nEpisodes:\n\n" + "\n\n".join(block(e, segments) for e in group)
            response, meta = asker.ask(prompt, schema, purpose="rating")
            got = {}
            if response and isinstance(response.get("items"), list):
                got = {it["episode_id"]: it for it in response["items"] if valid_item(it, ids)}
            with lock:
                log.append({"batch": bi, "attempt": attempt, **meta, "returned": len(got), "expected": len(ids)})
                results.update(got)
                if meta.get("error") and meta["error"] != "stopped":
                    model_errors.append(meta["error"])
                if got and on_answer:
                    on_answer({episode_key(by_id[i]): it for i, it in got.items()})
            missing = ids - set(got)
            # a second ask only for an answer that came back short; after a model error (a timeout may have been paid
            # for) the batch stays missing and «Продолжить» asks it again (decision 3)
            if not missing or asker.stop.is_set() or meta.get("error"):
                break
            group = [e for e in group if e["episode_id"] in missing]
            ids = missing
        with lock:
            done[0] += 1
            if progress:
                progress(done[0], len(batches))

    with cf.ThreadPoolExecutor(max(1, workers)) as pool:
        list(pool.map(lambda x: one(*x), enumerate(batches)))
    rated = []
    for e in ordered:
        row = {"episode_id": e["episode_id"], "episode_start_s": e["start_s"], "episode_end_s": e["end_s"], "episode_type": e.get("episode_type"),
               "why_interesting": e.get("why_interesting"), "text_preview": e.get("text_preview", "")}
        verdict = results.get(e["episode_id"])
        if verdict is None:
            rated.append({**row, "status": "no_verdict"})
            continue
        try:
            best_start, best_end = parse_hms(verdict["best_start"]), parse_hms(verdict["best_end"])
        except (ValueError, KeyError):
            best_start, best_end = e["start_s"], e["end_s"]
        lo, hi = e["start_s"] - CONTEXT_S, e["end_s"] + CONTEXT_S
        trim = snap_to_words(segments, best_start, best_end, lo, hi) or snap_to_words(segments, e["start_s"], e["end_s"], lo, hi)
        rated.append({**row, "status": "ok", "verdict": verdict["verdict"], "score": verdict["score"], "format": verdict["format"],
                      "title": verdict["title"].strip(), "reason": verdict["reason"], "depends_on_video": verdict["depends_on_video"], "trim": trim})
    log.sort(key=lambda r: (r["batch"], r["attempt"]))
    return {"episodes": rated, "requests": log, "missing": [r["episode_id"] for r in rated if r["status"] != "ok"],
            "model_errors": model_errors}
