"""The critic: frames of a finished 9:16 clip go to a vision model with an editor's checklist (prompt
`vod/critic-prompt.txt`, schema `critic`). Moved from production (`vod/critic.py` and the backend's `code-fix.ts`); one
module for every tool that makes clips (VodCut now, LiveCut later).

What it checks: the streamer's webcam is in its place, the face is not covered by the hook or the captions, the layout
suits the clip, no black bars or empty slots.

What it does (owner's rule: no clip ever waits for a person, everything is decided by a rule):
- pass, reject, or a fix the editor cannot make by itself → the clip stays as it is;
- a fix it can make → exactly ONE edit (another layout, captions higher or lower, no hook), the clip is rendered again
  and the critic looks once more. The better of the two versions stays: the new one when its score is not lower than
  the old one's (or the critic now passes it), the old one otherwise. Never a second edit.
- an unreadable or missing answer → the clip stays as it is; the reason is written down.
The streamer's visible webcam is never removed: an edit to a layout without the camera is not made when the clip has one.

The tool gives `ask` (a model call), `rerender` (renders a Decision to a file) and `emit` (its journal); every step
— the checks, the edit, the outcome — goes to the journal as clip_checked, clip_fixed and clip_reviewed.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Callable

from . import prompts
from .render import frames as stills
from .render.layout import SLOTS, W, beside, fit_inside, inset

FRAME_WIDTH = 540
FRAME_COUNT = 6
BATCH = 4                         # clips in one critic call (B12)
BATCH_FRAMES = 4                  # frames of each clip in a batch: the start with the hook, two in the middle, the end
BATCH_WIDTH = 432                 # ... this wide: a 9:16 frame at 432×768 still shows the captions and the hook
VERDICTS = ("pass", "fix", "reject")
ISSUE_CODES = ("text_too_small", "text_overlap", "text_cut_off", "hook_unreadable", "webcam_misplaced", "webcam_frame", "webcam_missing",
               "game_not_visible", "subject_cut", "black_bars", "low_quality", "wrong_cut", "too_short", "other")
LAYOUT_FIXES = {"layout_streamer_split": "streamer_scene_split", "layout_split_equal": "streamer_scene_split_equal",
                "layout_scene_only": "scene_only"}
CAPTION_FIXES = {"captions_lower": "lower", "captions_center": "center", "captions_upper": "upper"}
# Our renderer has no place for the peak lines other than their own, so the peak edits of production are never offered.
FIXES = (*LAYOUT_FIXES, *CAPTION_FIXES, "drop_hook", "webcam_tighter")
TIGHTER = 0.06                    # webcam_tighter: the webcam crop this much smaller on each side, the same shape
PEAK_LINE = "  • the final large lines (peak) lower or higher;\n"
PEAK_CODES = " peak_lower, peak_upper, peak_default — final large lines lower, higher, default place;"
PLAIN_ENDING = ("This format has no final large lines (peak): the video ends with ordinary captions and a short pause after the "
                "last word. That is normal, not a defect.")
NO_PEAK_FIX = "There is no edit for the peak lines: do not suggest one."

Ask = Callable[[str, dict, list, str], tuple[dict | None, dict]]      # (prompt, schema, images, purpose) -> (answer, meta)
Emit = Callable[..., object]


@dataclass(frozen=True)
class Decision:
    """What a clip was rendered with: the part the critic can change by itself."""
    mode: str                         # scene_only | streamer_scene_split | streamer_scene_split_equal
    scene_crop: dict
    streamer_crop: dict | None = None
    camera: dict | None = None        # the webcam on the source, when the layout model saw one
    captions: str = "lower"           # lower | center | upper
    hook: str | None = None           # the hook card's text; None: no hook

    def brief(self) -> dict:
        return {"layout": self.mode, "captions": self.captions, "hook": self.hook is not None}

    def as_dict(self) -> dict:
        return asdict(self)


def apply_fix(d: Decision, fix: str) -> Decision | None:
    """The decision with the fix made, or None when the fix changes nothing or is not allowed (it would hide the visible
    webcam, or a split is asked for without a known camera). Mirrors applyCodeFix of production."""
    if fix in LAYOUT_FIXES:
        mode = LAYOUT_FIXES[fix]
        if mode == d.mode:
            return None
        if mode == "scene_only":
            if d.camera is not None or d.streamer_crop is not None:
                return None               # the streamer's visible camera is never removed
            return replace(d, mode=mode)
        if d.streamer_crop is None and d.camera is None:
            return None                   # no camera to put on top
        # from a whole-frame clip: the camera cut to the slot's shape (no blurred fields), the face in its upper part
        streamer = d.streamer_crop or fit_inside(d.camera, W / SLOTS[mode][0],
                                                 (d.camera["x"] + d.camera["width"] / 2, d.camera["y"] + d.camera["height"] * 0.45))
        # from a whole-frame clip: the scene is the part of the frame beside the webcam, so the streamer is not seen twice
        scene = d.scene_crop if d.streamer_crop is not None else beside(d.camera)
        return replace(d, mode=mode, streamer_crop=streamer, scene_crop=scene)
    if fix in CAPTION_FIXES:
        return None if d.captions == CAPTION_FIXES[fix] else replace(d, captions=CAPTION_FIXES[fix])
    if fix == "drop_hook":
        return None if d.hook is None else replace(d, hook=None)
    if fix == "webcam_tighter":
        return None if d.streamer_crop is None else replace(d, streamer_crop=inset(d.streamer_crop, TIGHTER))
    return None


def frame_times(duration_s: float, count: int = FRAME_COUNT) -> list[float]:
    """Just after the start, evenly through the middle, just before the end."""
    duration_s = max(float(duration_s), 1.0)
    edge = min(0.4, duration_s / (2 * (count - 1)))      # a short clip keeps its frames in time order
    inner = [duration_s * (i + 1) / (count - 1) for i in range(count - 2)]
    return [round(edge, 2)] + [round(t, 2) for t in inner] + [round(duration_s - edge, 2)]


def policy(peak_lines: bool) -> str:
    text = prompts.text("vod/critic-prompt.txt").replace(PEAK_LINE, "").replace(PEAK_CODES, "")
    return text.rstrip("\n") + "\n\n" + (NO_PEAK_FIX if peak_lines else PLAIN_ENDING) + "\n"


def _meta_lines(facts: dict, revision: dict | None) -> list[str]:
    lines = [f"Duration: {facts.get('duration_s', 0):.1f} s.",
             f"Channel: {facts.get('channel') or '—'}; stream: {(facts.get('stream_title') or '—')[:100]}.",
             f"Video title: {facts.get('title') or '—'}.",
             f"Layout: {facts.get('layout') or '—'}; captions: {facts.get('captions') or 'lower'}; hook: {'yes' if facts.get('hook') else 'no'}."]
    if revision:
        lines.append(f"This is already a revised version (edit made: {revision.get('fix')}); the previous wish: {revision.get('wish') or '—'}.")
    return lines


def build_prompt(facts: dict, times: list[float], *, peak_lines: bool = False, revision: dict | None = None) -> str:
    lines = _meta_lines(facts, revision)
    listing = "\n".join(f"Frame {i + 1}: {t:.1f} s" for i, t in enumerate(times))
    return (policy(peak_lines) + "\n\nVideo metadata:\n" + "\n".join(lines) + "\n\nFrames:\n" + listing
            + '\n\nReturn {"verdict":…,"score":…,"issues":[…],"wish":…,"fix":…,"summary":…}.')


def schema() -> dict:
    """The answer schema with only the fixes this renderer can make."""
    s = json.loads(json.dumps(prompts.schema("critic")))
    s["properties"]["fix"]["enum"] = [*FIXES, None]
    return s


def normalize(answer) -> dict | None:
    """A usable verdict or None. A fix code outside the offered ones, or with any verdict but fix, is dropped."""
    score = answer.get("score") if isinstance(answer, dict) else None
    if isinstance(score, float) and score.is_integer():
        score = int(score)
    if not isinstance(answer, dict) or answer.get("verdict") not in VERDICTS or type(score) is not int:
        return None
    answer = {**answer, "score": score}
    issues = [{"code": i["code"], "severity": i.get("severity") if i.get("severity") in ("minor", "major") else "minor",
               "detail": str(i.get("detail") or "")[:300]}
              for i in (answer.get("issues") or []) if isinstance(i, dict) and i.get("code") in ISSUE_CODES]
    fix = answer.get("fix") if answer["verdict"] == "fix" and answer.get("fix") in FIXES else None
    wish = str(answer.get("wish") or "").strip()[:200] or None
    return {"verdict": answer["verdict"], "score": max(0, min(100, answer["score"])), "issues": issues[:10],
            "wish": wish if answer["verdict"] == "fix" else None, "fix": fix, "summary": str(answer.get("summary") or "").strip()[:300]}


def look(ask: Ask, video: Path, facts: dict, work: Path, *, peak_lines: bool = False, revision: dict | None = None) -> tuple[dict | None, str]:
    """(verdict, error). Frames of the video → the model → a checked verdict, kept in work/verdict.json."""
    times = frame_times(facts.get("duration_s") or 20.0)
    (work / "verdict.json").unlink(missing_ok=True)          # a verdict of an earlier run must not pass for this one
    try:
        shots = stills.extract(video, times, work / "frames", width=FRAME_WIDTH)
    except Exception as e:  # noqa: BLE001 — no frames, no check: the clip stays and the reason is written down
        return None, f"frames: {type(e).__name__}: {e}"[:300]
    answer, meta = ask(build_prompt(facts, times, peak_lines=peak_lines, revision=revision), schema(), shots, "critic")
    if answer is None:
        return None, str(meta.get("error") or "no answer")[:300]
    verdict = normalize(answer)
    if verdict is None:
        errors = meta.get("schema_errors") or []
        return None, ("the answer is not a verdict" + (": " + "; ".join(errors[:3]) if errors else ""))[:300]
    work.mkdir(parents=True, exist_ok=True)
    (work / "verdict.json").write_text(json.dumps({**verdict, "seconds": meta.get("seconds")}, ensure_ascii=False, indent=1), encoding="utf-8")
    return verdict, ""


def look_together(ask: Ask, group: list[tuple[Path, dict, Path, dict | None]], *, peak_lines: bool = False) -> list[tuple[dict | None, str]]:
    """(verdict, error) for each clip of a group, from ONE model call: the same instructions, every clip's metadata and
    frames, one verdict per clip. A clip whose frames cannot be taken, or that the answer leaves out, gets its error;
    the others keep their verdicts."""
    ids = [f"video{k + 1}" for k in range(len(group))]
    result: list[tuple[dict | None, str]] = [(None, "")] * len(group)
    shots, blocks, n = [], [], 0
    for k, (video, facts, work, revision) in enumerate(group):
        (work / "verdict.json").unlink(missing_ok=True)       # a verdict of an earlier run must not pass for this one
        times = frame_times(facts.get("duration_s") or 20.0, BATCH_FRAMES)
        try:
            taken = stills.extract(video, times, work / "frames", width=BATCH_WIDTH)
        except Exception as e:  # noqa: BLE001 — no frames, no check for this clip: the others are still looked at
            result[k] = (None, f"frames: {type(e).__name__}: {e}"[:300])
            continue
        listing = "\n".join(f"Frame {n + j + 1}: {t:.1f} s" for j, t in enumerate(times))
        n += len(taken)
        shots += taken
        blocks.append((k, f"\n\n=== {ids[k]} ===\nVideo metadata:\n" + "\n".join(_meta_lines(facts, revision)) + "\n\nFrames:\n" + listing))
    if not blocks:
        return result
    asked = [ids[k] for k, _ in blocks]
    prompt = (policy(peak_lines) + f"\n\nBelow are {len(blocks)} different videos, each with its own metadata and frames (the frames "
              "are numbered through all videos, in the order given). Judge each video on its own, as if it were the only one, "
              "and give one verdict per video." + "".join(b for _, b in blocks)
              + '\n\nReturn {"reviews":[{"video":…,"verdict":…,"score":…,"issues":[…],"wish":…,"fix":…,"summary":…}, …]}: '
              "one review per video, its video id as written above.")
    answer, meta = ask(prompt, batch_schema(asked), shots, "critic")
    if answer is None:
        error = str(meta.get("error") or "no answer")[:300]
        return [(None, error) if k in dict(blocks) else r for k, r in enumerate(result)]
    by_id = {r.get("video"): r for r in answer.get("reviews") or [] if isinstance(r, dict)}
    for k, _ in blocks:
        verdict = normalize(by_id.get(ids[k]))
        if verdict is None:
            result[k] = (None, f"the answer has no usable verdict for this clip ({ids[k]} of {len(blocks)})")
            continue
        work = group[k][2]
        work.mkdir(parents=True, exist_ok=True)
        (work / "verdict.json").write_text(json.dumps({**verdict, "seconds": meta.get("seconds"), "batch": len(blocks)},
                                                      ensure_ascii=False, indent=1), encoding="utf-8")
        result[k] = (verdict, "")
    return result


def batch_schema(ids: list[str]) -> dict:
    """The answer schema for several clips: the critic's schema per clip, with the clip's id."""
    one = schema()
    item = {**one, "properties": {"video": {"type": "string", "enum": ids}, **one["properties"]}, "required": ["video", *one["required"]]}
    return {"type": "object", "properties": {"reviews": {"type": "array", "items": item}}, "required": ["reviews"], "additionalProperties": False}


@dataclass
class Outcome:
    """What the critic did with one clip. outcome: passed | fixed | kept | unchecked."""
    outcome: str
    decision: Decision                 # what the clip that stays was rendered with
    reason: str
    fix: str | None = None
    score: int | None = None           # of the version that stays
    score_before: int | None = None
    wish: str | None = None
    verdict: str | None = None         # the first verdict

    def as_event(self) -> dict:
        out = {"outcome": self.outcome, "reason": self.reason, "fix": self.fix, "verdict": self.verdict, "score": self.score,
               "score_before": self.score_before, "wish": self.wish}
        return {k: v for k, v in out.items() if v is not None}


def _checked(emit: Emit, clip: str, round_: int, verdict: dict | None, error: str) -> None:
    if verdict is None:
        emit("clip_checked", clip=clip, round=round_, by="error", error=error)
    else:
        emit("clip_checked", clip=clip, round=round_, by="model", verdict=verdict["verdict"], score=verdict["score"],
             issues=[i["code"] for i in verdict["issues"]], **({"fix": verdict["fix"]} if verdict["fix"] else {}),
             **({"wish": verdict["wish"]} if verdict["wish"] else {}), summary=verdict["summary"])


@dataclass
class Item:
    """One finished clip for the critic: its file, what it was made with, its facts, its folder for the critic's files
    and how to render it again with another decision."""
    clip: str
    video: Path
    decision: Decision
    facts: dict
    work: Path
    rerender: Callable[[Decision, Path], Path]


def review(ask: Ask, clip: str, video: Path, decision: Decision, facts: dict, work: Path,
           rerender: Callable[[Decision, Path], Path], emit: Emit, *, peak_lines: bool = False) -> Outcome:
    """Checks one finished clip and makes at most one edit. `video` ends up holding the version that stays."""
    return review_many(ask, [Item(clip, Path(video), decision, facts, work, rerender)], emit, peak_lines=peak_lines)[0]


def review_many(ask: Ask, items: list[Item], emit: Emit, *, peak_lines: bool = False, batch: int = BATCH,
                outcomes: dict[int, Outcome] | None = None) -> list[Outcome]:
    """Checks finished clips, at most `batch` in one model call (B12: every call carries the same instructions, so
    fewer calls cost fewer tokens), and makes at most one edit per clip; the edited versions are looked at again
    together. Each `video` ends up holding the version that stays."""
    facts = [{**it.facts, **it.decision.brief()} for it in items]
    firsts = looks(ask, [(it.video, f, it.work / "before", None) for it, f in zip(items, facts)], peak_lines=peak_lines, batch=batch)
    outcomes = {} if outcomes is None else outcomes      # filled as each clip is decided: a failure later keeps them
    again: list[tuple[int, Decision, Path, dict]] = []

    def done(i: int, o: Outcome) -> None:
        emit("clip_reviewed", clip=items[i].clip, **o.as_event())
        outcomes[i] = o

    for i, (it, (first, error)) in enumerate(zip(items, firsts)):
        _checked(emit, it.clip, 1, first, error)
        if first is None:
            done(i, Outcome("unchecked", it.decision, f"no verdict: {error}"))
            continue
        base = dict(verdict=first["verdict"], score=first["score"], wish=first["wish"])
        if first["verdict"] == "pass":
            done(i, Outcome("passed", it.decision, first["summary"] or "pass", **base))
            continue
        if first["verdict"] == "reject":
            done(i, Outcome("kept", it.decision, f"reject, kept as it is: {first['summary']}".strip(), **base))
            continue
        if first["fix"] is None:
            done(i, Outcome("kept", it.decision, f"no edit the editor can make: {first['wish'] or first['summary']}".strip(), **base))
            continue
        fixed = apply_fix(it.decision, first["fix"])
        if fixed is None:
            why = "it would hide the streamer's webcam" if LAYOUT_FIXES.get(first["fix"]) == "scene_only" else "it changes nothing here"
            done(i, Outcome("kept", it.decision, f"{first['fix']} not made: {why}", fix=first["fix"], **base))
            continue
        candidate = it.video.with_name(it.video.stem + ".fix" + it.video.suffix)
        try:
            it.rerender(fixed, candidate)
        except Exception as e:  # noqa: BLE001 — a failed edit leaves the clip as it was; the reason is written down
            candidate.unlink(missing_ok=True)
            done(i, Outcome("kept", it.decision, f"{first['fix']} failed to render: {type(e).__name__}: {e}"[:300], fix=first["fix"], **base))
            continue
        emit("clip_fixed", clip=it.clip, fix=first["fix"], before=it.decision.brief(), after=fixed.brief(),
             **({"wish": first["wish"]} if first["wish"] else {}))
        again.append((i, fixed, candidate, first))
    seconds = looks(ask, [(candidate, {**facts[i], **fixed.brief()}, items[i].work / "after",
                           {"fix": first["fix"], "wish": first["wish"]}) for i, fixed, candidate, first in again],
                    peak_lines=peak_lines, batch=batch)
    for (i, fixed, candidate, first), (second, error) in zip(again, seconds):
        it = items[i]
        _checked(emit, it.clip, 2, second, error)
        if second is None and error.startswith("frames:"):
            candidate.unlink(missing_ok=True)       # a version whose frames cannot be read is not put in place of a good clip
            done(i, Outcome("kept", it.decision, f"{first['fix']} made, but the new version could not be read ({error}); the first version stays"[:400],
                            fix=first["fix"], score=first["score"], score_before=first["score"], wish=first["wish"], verdict=first["verdict"]))
            continue
        if second is None or second["verdict"] == "pass" or second["score"] >= first["score"]:
            try:
                os.replace(candidate, it.video)
            except OSError as e:                    # Windows: the clip is open in a player; the first version stays
                candidate.unlink(missing_ok=True)
                done(i, Outcome("kept", it.decision, f"{first['fix']} made, but the clip could not be replaced ({e}); the first version stays"[:400],
                                fix=first["fix"], score=first["score"], score_before=first["score"], wish=first["wish"], verdict=first["verdict"]))
                continue
            reason = (f"{first['fix']}: {first['wish'] or first['summary']}" if second is None or second["verdict"] == "pass"
                      else f"{first['fix']}: {first['wish'] or first['summary']} (after it: {second['verdict']}, {second['score']} ≥ {first['score']})")
            if second is None:
                reason += f"; not rechecked: {error}"
            done(i, Outcome("fixed", fixed, reason[:400], fix=first["fix"], score=second["score"] if second else None,
                            score_before=first["score"], wish=first["wish"], verdict=first["verdict"]))
            continue
        candidate.unlink(missing_ok=True)
        done(i, Outcome("kept", it.decision, (f"{first['fix']} made it worse ({second['score']} < {first['score']}: {second['summary']}); "
                                              f"the first version stays")[:400],
                        fix=first["fix"], score=first["score"], score_before=first["score"], wish=first["wish"], verdict=first["verdict"]))
    return [outcomes[i] for i in range(len(items))]


def looks(ask: Ask, todo: list[tuple[Path, dict, Path, dict | None]], *, peak_lines: bool, batch: int = BATCH) -> list[tuple[dict | None, str]]:
    """(verdict, error) for each (video, facts, work folder, revision): one clip alone as before B12, several in calls
    of at most `batch` clips."""
    if len(todo) <= 1 or batch <= 1:
        return [look(ask, v, f, w, peak_lines=peak_lines, revision=r) for v, f, w, r in todo]
    out: list[tuple[dict | None, str]] = []
    for i in range(0, len(todo), batch):
        group = todo[i:i + batch]
        if len(group) == 1:
            out.append(look(ask, *group[0][:3], peak_lines=peak_lines, revision=group[0][3]))
        else:
            out += look_together(ask, group, peak_lines=peak_lines)
    return out
