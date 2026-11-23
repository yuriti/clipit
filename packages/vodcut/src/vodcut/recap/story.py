"""The story of a recap: the model reads the rated episodes and the whole transcript and returns chapters of parts —
spans of the recording, each a highlight or the context around one, with its pace, emotion peaks and a music flag.

Ported from production (`vod/recap.py`, story stage). The answer is never trusted as it is: parts are put in stream
order, snapped to word starts, merged where they touch, cut out of muted spans and out of the picture's end; a story
over 28 minutes of source is asked once more. The recap ends on the streamer's own goodbye when the stream has one.
"""
from __future__ import annotations

import re

from smtv_core import prompts
from smtv_core.asr import filtered_segments

TARGET_MAX_S = 28 * 60          # source minutes the model may take; the jump cuts bring the video to ~20–28 min
MIN_PART_S, MUTED_MARGIN_S = 8.0, 0.5
TRANSCRIPT_BUDGET = 240_000     # characters; a longer stream keeps the speech around its rated episodes only
VIDEO_END_GUARD_S = 0.5         # every part ends this much before the picture does
HMS = re.compile(r"^(\d+):([0-5]\d):([0-5]\d)$")


class RecapError(RuntimeError):
    pass


def hms(seconds: float) -> str:
    s = int(max(0.0, seconds))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def parse_hms(text) -> float:
    m = HMS.match(str(text).strip()) if isinstance(text, str) else None
    if not m:
        raise ValueError(f"not h:mm:ss: {text!r}")
    return int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3])


def human_duration(seconds: float, language: str = "en") -> str:
    hours, minutes = int(seconds // 3600), int(seconds % 3600 // 60)
    h, m = ("ч", "мин") if language == "ru" else ("h", "min")
    return (f"{hours} {h} " if hours else "") + f"{minutes} {m}"


def episode_lines(episodes: list[dict]) -> str:
    lines = []
    for e in sorted(episodes, key=lambda e: e.get("episode_start_s", 0)):
        if e.get("status") != "ok":
            continue
        lines.append(f"{e['episode_id']} {hms(e['episode_start_s'])}–{hms(e['episode_end_s'])} {e.get('verdict')} {e.get('score')} "
                     f"{e.get('format')} «{e.get('title', '')}» — {e.get('reason', '')}")
    return "\n".join(lines)


def transcript_lines(segments: list[dict], episodes=(), budget: int = TRANSCRIPT_BUDGET) -> str:
    """The filtered transcript, a line per segment; over `budget` only the speech within 90 s of a rated (not skipped)
    episode stays and every hole becomes one "[…]" line."""
    lines = [(s["start"], f"{hms(s['start'])} {s['text'].strip()}") for s in filtered_segments(segments)]
    if sum(len(text) + 1 for _, text in lines) <= budget:
        return "\n".join(text for _, text in lines)
    near = [(e["episode_start_s"] - 90, e["episode_end_s"] + 90) for e in episodes if e.get("status") == "ok" and e.get("verdict") != "skip"]
    out, hole = [], False
    for start, text in lines:
        if any(a <= start <= b for a, b in near):
            out.append(text)
            hole = False
        elif not hole:
            out.append("[…]")
            hole = True
    return "\n".join(out)


def prompt(facts: dict, episodes: list[dict], segments: list[dict], muted=()) -> str:
    return prompts.fill(prompts.text("vod/recap-prompt.txt"), channel=facts.get("channel") or "unknown",
                        title=(facts.get("title") or "").strip(), date=facts.get("date") or "date unknown",
                        duration=human_duration(float(facts.get("duration_s") or 0)),
                        muted=", ".join(f"{hms(a)}–{hms(b)}" for a, b in muted) or "none",
                        episodes=episode_lines(episodes), transcript=transcript_lines(segments, episodes))


def words_of(segments: list[dict]) -> list[dict]:
    """Every word of the filtered transcript as {text, start, end}, in time order."""
    out = [{"text": (w.get("word") or w.get("text") or "").strip(), "start": float(w["start"]), "end": float(w["end"])}
           for s in filtered_segments(segments) for w in s.get("words") or () if w.get("start") is not None and w.get("end") is not None]
    return sorted(out, key=lambda w: w["start"])


def snap_part(start: float, end: float, words: list[dict], duration: float) -> tuple[float, float]:
    """Start on the nearest word start (±3 s), end after the last word that begins before the end, never before the
    model's own end (it was told to leave room for the reaction)."""
    starts = [w["start"] for w in words if abs(w["start"] - start) <= 3]
    begin = (min(starts, key=lambda t: abs(t - start)) if starts else start) - 0.2
    ends = [w["end"] for w in words if begin < w["start"] < end and w["end"] <= end + 1.5]
    finish = max(end, max(ends) + 0.4) if ends else end
    return round(max(0.0, begin), 2), round(min(duration, finish) if duration else finish, 2)


def subtract(span, ranges, margin: float = MUTED_MARGIN_S) -> list[tuple[float, float]]:
    """span minus every range (widened by margin): the pieces left, the short ones dropped."""
    pieces = [list(span)]
    for a, b in ranges:
        a, b = a - margin, b + margin
        left = []
        for x, y in pieces:
            if b <= x or a >= y:
                left.append([x, y])
                continue
            if a > x:
                left.append([x, a])
            if b < y:
                left.append([b, y])
        pieces = left
    return [(round(x, 2), round(y, 2)) for x, y in pieces if y - x >= MIN_PART_S]


def normalize(answer, segments: list[dict], *, muted=(), duration: float = 0.0) -> dict:
    """The model's chapters → chronological, non-overlapping, word-snapped parts outside the muted spans. Anything
    malformed (a chapter that is not an object, a bad timestamp, a part of less than 3 s) is left out, not fatal."""
    answer = answer if isinstance(answer, dict) else {}
    chapters = [c for c in answer.get("chapters") or [] if isinstance(c, dict)] if isinstance(answer.get("chapters"), list) else []
    words = words_of(segments)
    parts = []
    for chapter_index, chapter in enumerate(chapters):
        raws = chapter.get("parts") if isinstance(chapter.get("parts"), list) else []
        for raw in raws:
            if not isinstance(raw, dict):
                continue
            try:
                start, end = parse_hms(raw.get("start")), parse_hms(raw.get("end"))
            except ValueError:
                continue
            if end - start < 3 or (duration and start >= duration):
                continue
            begin, finish = snap_part(start, end, words, duration)
            peaks = []
            for text in raw.get("peaks") or []:
                try:
                    peaks.append(parse_hms(text))
                except ValueError:
                    pass
            for a, b in subtract((begin, finish), muted):
                parts.append({"chapter": chapter_index, "start_s": a, "end_s": b,
                              "role": raw.get("role") if raw.get("role") in ("highlight", "context") else "context",
                              "pace": raw.get("pace") if raw.get("pace") in ("tight", "loose") else "tight",
                              "why": str(raw.get("why") or "")[:240], "peaks_s": [p for p in peaks if a <= p <= b], "music": raw.get("music") is True})
    parts.sort(key=lambda p: p["start_s"])
    merged: list[dict] = []
    for part in parts:
        last = merged[-1] if merged else None
        if last and part["start_s"] < last["end_s"] + 1.0:
            last["end_s"] = max(last["end_s"], part["end_s"])
            last["role"] = "highlight" if "highlight" in (last["role"], part["role"]) else "context"
            last["pace"] = "loose" if "loose" in (last["pace"], part["pace"]) else "tight"
            last["peaks_s"] = sorted(set(last["peaks_s"] + part["peaks_s"]))
            last["music"] = last["music"] or part["music"]
            last["why"] = (last["why"] + " / " + part["why"]).strip(" /")[:400]
            continue
        merged.append(dict(part))
    chapter = 0
    for index, part in enumerate(merged):            # chapters never go back in time
        chapter = max(chapter, part["chapter"])
        part.update({"index": index, "chapter": chapter})
    titles = [str(c.get("title") or "").strip() for c in chapters]
    used = sorted({p["chapter"] for p in merged})
    renumber = {old: new for new, old in enumerate(used)}
    for part in merged:
        part["chapter"] = renumber[part["chapter"]]
    return {"title": str(answer.get("title") or "").strip()[:100], "hook": str(answer.get("hook") or "").strip()[:400],
            "chapters": [{"title": titles[old][:60] or f"{new + 1}"} for new, old in enumerate(used)], "parts": merged,
            "source_s": round(sum(p["end_s"] - p["start_s"] for p in merged), 1),
            "content_absent": answer.get("chapters") == []}     # the model said so; a malformed answer is asked again


# The streamer's goodbye, Russian and English (the two languages VodCut has bleep lists for).
FAREWELL = re.compile(
    r"спасибо( вам)?( всем)?( большое| огромное)? за (стрим|то что был|сегодня|вечер|компанию)|всем (пока|спасибо|до)|пока[- ]пока|"
    r"до (завтра|встречи|скорого|связи|понедельника|вторника|среды|четверга|пятницы|субботы|воскресенья)|спокойной ночи|всех люблю|"
    r"увидимся|отправляю (вас )?(с )?рейд|\bрейд(им)?\b|"
    r"thanks? (you )?(so much |all |guys |everyone )?for (watching|the stream|coming|hanging out|tonight)|see (you|ya) (all )?(tomorrow|next time|soon|later|on)|"
    r"good ?night (chat|everyone|guys)|bye[- ]bye|\braid(ing)?\b", re.I)
FAREWELL_WINDOW_S, FAREWELL_MAX_S, FAREWELL_TAIL_S, FAREWELL_MIN_S = 20 * 60, 90.0, 0.6, 1.0


def farewell_span(segments: list[dict], duration: float, muted=()) -> tuple[float, float] | None:
    """(start, end) of the goodbye in the stream's last 20 minutes: from the first farewell phrase of the closing run to
    the end of the last one's sentence, at most 90 s; None when the stream ends without one."""
    tail = [s for s in filtered_segments(segments) if s["start"] >= duration - FAREWELL_WINDOW_S and (not duration or s["start"] < duration)
            and not any(a <= s["start"] <= b for a, b in muted)]
    hits = [i for i, s in enumerate(tail) if FAREWELL.search(s["text"])]
    if not hits:
        return None
    last = hits[-1]
    first = min(h for h in hits if tail[last]["end"] - tail[h]["start"] <= FAREWELL_MAX_S)
    end = tail[last]["end"]
    for s in tail[last + 1:]:            # the sentence of the last farewell runs on until the next pause
        if s["start"] - end > 1.5:
            break
        end = s["end"]
    start = max(tail[first]["start"] - 0.3, end - FAREWELL_MAX_S)
    end = min(duration, end + FAREWELL_TAIL_S) if duration else end + FAREWELL_TAIL_S
    return (round(start, 2), round(end, 2)) if end - start >= FAREWELL_MIN_S else None


def close_with_farewell(story: dict, segments: list[dict], duration: float) -> int | None:
    """The recap ends on the goodbye: the last part runs on to its end, or the goodbye becomes the last part when the
    story stopped well before it. The index of the part changed or added, or None."""
    limit = duration - VIDEO_END_GUARD_S if duration else 0.0
    span = farewell_span(segments, limit, story.get("muted") or ())
    parts = story["parts"]
    if not span or not parts:
        return None
    start, end = span
    last = parts[-1]
    story["farewell"] = [start, end]
    if last["end_s"] >= end - 0.05:
        return None
    if last["end_s"] >= start - 20:
        last["end_s"] = end
        changed = last["index"]
    else:
        changed = max(p["index"] for p in parts) + 1
        parts.append({"index": changed, "chapter": last["chapter"], "start_s": start, "end_s": end, "role": "context", "pace": "tight",
                      "why": "goodbye: the end of the stream", "peaks_s": [], "music": False})
    story["source_s"] = round(sum(p["end_s"] - p["start_s"] for p in parts), 1)
    return changed


def fit_to_video(story: dict, duration: float) -> None:
    """Every part inside the recording: a part running past its end is cut there, or dropped when less than
    MIN_PART_S of it is left."""
    if not duration:
        return
    end = round(duration - VIDEO_END_GUARD_S, 2)
    kept = []
    for part in story["parts"]:
        if part["end_s"] <= end:
            kept.append(part)
        elif end - part["start_s"] >= MIN_PART_S:
            part["end_s"] = end
            part["peaks_s"] = [p for p in part["peaks_s"] if p <= end]
            kept.append(part)
    story["parts"] = kept
    story["source_s"] = round(sum(p["end_s"] - p["start_s"] for p in kept), 1)


def trim_to_limit(story: dict, limit_s: float = TARGET_MAX_S, min_part_s: float = 8.0) -> None:
    """A story still over the limit after the last answer is cut by rule, not thrown away (stage 15: a 5.7 h stream lost
    its recap over 28.3 min). Linking parts go first, the longest first, then the shortest highlights; the part at
    which the story fits is shortened at its end instead, when at least `min_part_s` of it stays."""
    parts = story["parts"]
    total = sum(p["end_s"] - p["start_s"] for p in parts)
    order = sorted((p for p in parts if p["role"] == "context"), key=lambda p: -(p["end_s"] - p["start_s"])) + \
        sorted((p for p in parts if p["role"] != "context"), key=lambda p: p["end_s"] - p["start_s"])
    dropped = set()
    for p in order:
        excess = total - limit_s
        if excess <= 0:
            break
        length = p["end_s"] - p["start_s"]
        if length - excess >= min_part_s:
            p["end_s"] = round(p["end_s"] - excess, 2)
            total -= excess
            break
        dropped.add(id(p))
        total -= length
    story["parts"] = [p for p in parts if id(p) not in dropped]
    story["source_s"] = round(sum(p["end_s"] - p["start_s"] for p in story["parts"]), 1)


def ask(asker, facts: dict, episodes: list[dict], segments: list[dict], *, muted=(), attempts: int = 2) -> dict:
    """The story, asked at most `attempts` times: no answer, or one over 28 minutes of source, is asked again.
    Raises RecapError when no usable story came back. A story with no parts (the model found nothing worth a recap) has
    `status: skipped`."""
    duration = float(facts.get("duration_s") or 0)
    text = prompt(facts, episodes, segments, muted)
    schema = prompts.schema("recap")
    tries, story = [], None
    for attempt in range(attempts):
        answer, meta = asker.ask(text, schema, purpose="recap")
        tries.append({k: v for k, v in meta.items() if k in ("error", "seconds", "schema_errors")})
        if answer is None:
            continue
        candidate = normalize(answer, segments, muted=muted, duration=duration)
        if candidate["content_absent"]:
            story = candidate
            break
        if not candidate["parts"]:
            continue                       # chapters came back, but not one part survived the checks
        story = candidate
        if candidate["source_s"] <= TARGET_MAX_S:
            break
        text += (f"\n\nYour previous answer gave {candidate['source_s'] / 60:.1f} min of source in {len(candidate['parts'])} parts (after the "
                 f"timestamps were checked). It must be at most {TARGET_MAX_S // 60} minutes: rebuild the story.")
    if story is None:
        raise RecapError("the model gave no usable story: " + "; ".join(str(t.get("error") or t.get("schema_errors") or "no parts") for t in tries)[:300])
    if story["source_s"] > TARGET_MAX_S:
        trim_to_limit(story)
        story["trimmed"] = True
    if story["source_s"] > TARGET_MAX_S or (not story["parts"] and not story["content_absent"]):
        raise RecapError(f"the story is {story['source_s'] / 60:.0f} min of source, over the {TARGET_MAX_S // 60} min limit")
    story.update({"muted": [list(r) for r in muted], "attempts": tries})
    if story["parts"]:
        fit_to_video(story, duration)
        close_with_farewell(story, segments, duration)
    if not story["parts"]:
        story["status"] = "skipped"
    return story
