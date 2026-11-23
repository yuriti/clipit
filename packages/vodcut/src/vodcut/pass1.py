"""Scan: the model reads the whole transcript in overlapping windows and marks candidate episodes.

Windows are cut by budget (target 600 s, 300-720 s, 120 s overlap, cut at speech gaps >= 1 s), eight per request,
several requests at once. Each window of an answer is validated on its own against the window's segment ids: valid
windows are kept, and one repair per request asks again only for the rest. Episodes seen in two overlapping windows
are merged.
"""
from __future__ import annotations

import concurrent.futures as cf
import threading

from jsonschema import Draft202012Validator
from smtv_core import prompts

DEFAULTS = dict(window_target_s=600, overlap_s=120, window_min_s=300, window_max_s=720, per_request=8, min_episode_s=5, max_episode_s=900)


def hms(seconds: float) -> str:
    t = int(seconds)
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def build_windows(segments, target=600, overlap=120, wmin=300, wmax=720):
    """Windows of whole segments; cut at the gap >= 1 s nearest the target length (within [wmin, wmax])."""
    cuts = {i for i in range(1, len(segments)) if segments[i]["start"] - segments[i - 1]["end"] >= 1.0}
    out, a, k = [], 0, 0
    while a < len(segments):
        t0, end_t = segments[a]["start"], segments[-1]["end"]
        if end_t - t0 <= wmax:
            b = len(segments)
        else:
            cand = [i for i in range(a + 1, len(segments)) if wmin <= segments[i]["start"] - t0 <= wmax]
            if not cand:
                b = next((i for i in range(a + 1, len(segments)) if segments[i]["start"] - t0 > wmax), len(segments))
            else:
                good = [i for i in cand if i in cuts] or cand
                b = min(good, key=lambda i: abs(segments[i]["start"] - t0 - target))
        window = segments[a:b]
        out.append({"id": f"w{k:02d}", "start": window[0]["start"], "end": window[-1]["end"], "segments": window, "first_idx": a, "last_idx": b - 1})
        k += 1
        if b >= len(segments):
            break
        back_t = segments[b]["start"] - overlap
        cand = [i for i in range(a + 1, b) if segments[i]["start"] >= back_t]
        if not cand:
            a = b
            continue
        good = [i for i in cand if i in cuts] or cand
        a = min(good, key=lambda i: abs(segments[i]["start"] - back_t))
    return out


def render(window, meta: str) -> str:
    lines = [f"WINDOW {window['id']} ({hms(window['start'])}-{hms(window['end'])}), {len(window['segments'])} segments{meta}"]
    for s in window["segments"]:
        lines.append(f"{s['sid']} | {hms(s['start'])} | {s['text'].strip()}")
    return "\n".join(lines)


_EPISODE = None


def _episode_validator():
    """The schema of one episode, from the answer's schema: a provider without strict schemas (Ollama, Claude Code) may
    drop a field or send a string instead of an object, and that must be a window error (repaired), never a crash later."""
    global _EPISODE
    if _EPISODE is None:
        _EPISODE = Draft202012Validator(prompts.schema("pass1")["properties"]["windows"]["items"]["properties"]["episodes"]["items"])
    return _EPISODE


def episode_errors(e) -> list[str]:
    """What is wrong with one episode of an answer; a text too long is cut later, not refused."""
    if not isinstance(e, dict):
        return ["not_an_object"]
    return [f"{'/'.join(map(str, x.absolute_path)) or 'episode'}:{x.validator}" for x in _episode_validator().iter_errors(e)
            if x.validator != "maxLength"]


def validate(response, windows, min_s=5, max_s=900):
    """Errors and the accepted episodes (with recording times and segment indexes attached)."""
    errors, episodes, by_id = [], [], {w["id"]: w for w in windows}
    if not isinstance(response, dict) or not isinstance(response.get("windows"), list):
        return ["no_windows"], []
    for rw in response["windows"]:
        w = by_id.get(rw.get("window_id")) if isinstance(rw, dict) else None
        if w is None:
            continue
        pos = {s["sid"]: i for i, s in enumerate(w["segments"])}
        by_sid = {s["sid"]: s for s in w["segments"]}
        found = rw.get("episodes") if rw.get("episodes") is not None else []
        if not isinstance(found, list):
            errors.append(f"{w['id']}:episodes_not_a_list")
            continue
        if rw.get("window_has_nothing") != (len(found) == 0):
            errors.append(f"{w['id']}:window_has_nothing_inconsistent")
        seen = set()
        for e in found:
            wrong = episode_errors(e)
            if wrong:
                errors.append(f"{w['id']}:episode_schema:{','.join(wrong[:3])}")
                continue
            a, b, c = e.get("start_segment_id"), e.get("end_segment_id"), e.get("anchor_segment_id")
            if a not in pos or b not in pos or c not in pos:
                errors.append(f"{w['id']}:unknown_segment_id:{a},{b},{c}")
                continue
            if not pos[a] <= pos[c] <= pos[b]:
                errors.append(f"{w['id']}:order_must_be_start<=anchor<=end:{a},{c},{b}")
                continue
            duration = by_sid[b]["end"] - by_sid[a]["start"]
            if not min_s <= duration <= max_s:
                errors.append(f"{w['id']}:duration_{duration:.0f}s_outside_{min_s}-{max_s}s:{a}-{b}")
                continue
            if (a, b) in seen:
                continue
            seen.add((a, b))
            segs = w["segments"][pos[a]:pos[b] + 1]
            span = max(w["end"] - w["start"], 1e-9)
            e = dict(e)
            e["why_interesting"] = str(e.get("why_interesting") or "")[:240]
            e["one_liner"] = bool(e.get("one_liner")) or duration < 10
            e.update({"window_id": w["id"], "start_s": by_sid[a]["start"], "end_s": by_sid[b]["end"], "anchor_s": by_sid[c]["start"], "duration_s": round(duration, 1),
                      "start_idx": w["first_idx"] + pos[a], "end_idx": w["first_idx"] + pos[b], "anchor_idx": w["first_idx"] + pos[c],
                      "center_offset": abs((by_sid[a]["start"] + by_sid[b]["end"]) / 2 - (w["start"] + w["end"]) / 2) / span,
                      "text_preview": " ".join(s["text"].strip() for s in segs)[:300]})
            episodes.append(e)
    return errors, episodes


def validate_windows(response, windows, min_s=5, max_s=900):
    """{window id: (errors, episodes)}, each window judged on its own entry of the answer."""
    if not isinstance(response, dict) or not isinstance(response.get("windows"), list):
        return {w["id"]: (["no_windows"], []) for w in windows}
    entries = [rw for rw in response["windows"] if isinstance(rw, dict)]
    out = {}
    for w in windows:
        mine = [rw for rw in entries if rw.get("window_id") == w["id"]]
        out[w["id"]] = ([f"{w['id']}:{'answered_twice' if mine else 'missing'}"], []) if len(mine) != 1 else validate({"windows": mine}, [w], min_s, max_s)
    return out


def merge(episodes):
    """Merge when the anchor lies inside the other episode or the segment overlap is >= 60 % of the smaller one, and the types are compatible."""
    def compatible(t1, t2):
        return t1 == t2 or "other" in (t1, t2)

    merged = []
    for e in sorted(episodes, key=lambda e: (e["start_idx"], e["end_idx"])):
        e = dict(e, source_window_ids=[e["window_id"]])
        target = None
        for m in merged:
            inter = min(m["end_idx"], e["end_idx"]) - max(m["start_idx"], e["start_idx"]) + 1
            if inter <= 0:
                continue
            smaller = min(m["end_idx"] - m["start_idx"], e["end_idx"] - e["start_idx"]) + 1
            anchor_in = m["start_idx"] <= e["anchor_idx"] <= m["end_idx"] or e["start_idx"] <= m["anchor_idx"] <= e["end_idx"]
            if (anchor_in or inter / smaller >= 0.6) and compatible(m["episode_type"], e["episode_type"]):
                target = m
                break
        if target is None:
            merged.append(e)
            continue
        best = e if e["center_offset"] < target["center_offset"] else target
        for key in ("why_interesting", "episode_type", "has_setup", "has_payoff", "depends_on_video", "standalone_clip_candidate", "one_liner"):
            target[key] = best[key]
        if target["episode_type"] == "other" and e["episode_type"] != "other":
            target["episode_type"] = e["episode_type"]
        if e["start_idx"] < target["start_idx"]:
            target.update({k: e[k] for k in ("start_idx", "start_s", "start_segment_id")})
        if e["end_idx"] > target["end_idx"]:
            target.update({k: e[k] for k in ("end_idx", "end_s", "end_segment_id")})
        target["asr_quality_concern"] = target["asr_quality_concern"] or e["asr_quality_concern"]
        target["source_window_ids"].append(e["window_id"])
        target["duration_s"] = round(target["end_s"] - target["start_s"], 1)
    for i, m in enumerate(merged):
        m["episode_id"] = f"e{i:03d}"
    return merged


def window_key(w) -> str:
    """A window's name in the saved answers: its id and its span, so answers of another transcript never match."""
    return f"{w['id']}@{w['start']:.3f}-{w['end']:.3f}"


def run(segments, asker, *, meta: str = "", workers: int = 4, progress=None, known: dict | None = None, on_answer=None,
        **options) -> dict:
    """segments: filtered segments with 'sid'. Returns {'episodes', 'requests', 'windows', 'missing', 'model_errors'}.

    `known` — episodes of windows answered in an earlier run ({window_key: [episodes]}): those windows are not asked
    again. `on_answer({window_key: [episodes]})` gets every window answered well as soon as its request is back, so an
    interrupted or partly failed scan keeps what it paid for. A window without a good answer (the model failed, or its
    answer stayed wrong after the repair) is in `missing` and is asked again by the next run.
    """
    o = {**DEFAULTS, **options}
    windows = build_windows(segments, o["window_target_s"], o["overlap_s"], o["window_min_s"], o["window_max_s"])
    known = dict(known or {})
    todo = [w for w in windows if window_key(w) not in known]
    policy, schema = prompts.text("vod/pass1-prompt.txt"), prompts.schema("pass1")
    groups = [todo[i:i + o["per_request"]] for i in range(0, len(todo), o["per_request"])]
    done, lock, model_errors = [len(windows) - len(todo)], threading.Lock(), []

    def build(group):
        return (policy.rstrip() + "\n\nWindows to read:\n\n" + "\n\n".join(render(w, meta) for w in group)
                + '\n\nReturn {"windows":[...]} with one entry per window above, in order.')

    def check(meta_r, response, group):
        if response is None:
            error = meta_r.get("error") or "not_json"
            return {w["id"]: ([error], []) for w in group}, [error]
        results = validate_windows(response, group, o["min_episode_s"], o["max_episode_s"])
        return results, [e for w in group for e in results[w["id"]][0]]

    def one(gi, group):
        record = {"request": gi, "windows": [w["id"] for w in group]}
        response, meta_r = asker.ask(build(group), schema, purpose="scan")
        results, errors = check(meta_r, response, group)
        record["first"] = {**meta_r, "errors": errors}
        failed = [w for w in group if results[w["id"]][0]]
        if failed and "error" not in meta_r:
            repair = (build(failed) + "\n\nYour previous answer for these windows was rejected by validation: " + "; ".join(errors)[:800]
                      + ". Fix exactly these problems and return the JSON for the windows above again.")
            response, meta_r = asker.ask(repair, schema, purpose="scan_repair")
            fixed, errors = check(meta_r, response, failed)
            record["repair"] = {**meta_r, "windows": [w["id"] for w in failed], "errors": errors}
            results.update(fixed)
        record["windows_invalid"] = [w["id"] for w in group if results[w["id"]][0]]
        good = {window_key(w): results[w["id"]][1] for w in group if not results[w["id"]][0]}
        with lock:
            known.update(good)
            if meta_r.get("error") and meta_r["error"] != "stopped":
                model_errors.append(meta_r["error"])
            done[0] += len(group)
            if good and on_answer:
                on_answer(dict(good))
            if progress:
                progress(done[0], len(windows))
        return record

    with cf.ThreadPoolExecutor(max(1, workers)) as pool:
        records = list(pool.map(lambda x: one(*x), enumerate(groups)))
    episodes = [e for w in windows for e in known.get(window_key(w), [])]
    return {"windows": len(windows), "requests": records, "episodes": merge(episodes),
            "missing": [w["id"] for w in windows if window_key(w) not in known], "model_errors": model_errors}
