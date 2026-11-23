"""The job's events as lines of text for the command line. Events with no line (a model call, an episode) stay silent here
and are seen on the page."""
from __future__ import annotations

import sys
from pathlib import Path


def hms(seconds: float) -> str:
    t = int(seconds)
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}"


def _stage(d: dict, job: Path) -> str | None:
    name = d.get("name")
    n = f"{d.get('step', 0)}/{d.get('steps', 5)}"
    if name == "audio":
        return f"{n} Getting the audio → {job}"
    if name == "language":
        return f"{n} Finding the language of the speech"
    if name == "model":
        return f"{n} Downloading the {d['engine']} speech model for {'Russian' if d.get('language') == 'ru' else d.get('language')} (once)"
    if name == "speech":
        lang = d["language"]
        return f"{n} Speech to text: {d['engine']} ({'Russian' if lang == 'ru' else lang}), {d['duration_s'] / 3600:.1f} h of audio"
    if name == "scan":
        return f"{n} Scanning the transcript for episodes ({d['segments']} segments)"
    if name == "rating":
        return f"{n} Rating {d['episodes']} episodes"
    if name == "pick":
        return f"{n} Picking the clips"
    if name == "fit":
        return f"{n} Cutting {d['clips']} clips exactly by words (Fit)"
    if name == "render":
        return "\nRendering the clips"
    if name == "recap":
        return "\nMaking the recap of the whole stream"
    return None


def _progress(d: dict) -> str | None:
    stage = d.get("stage")
    if stage == "download":           # a link through StreamMoment: our queue, then the audio's segments
        if d.get("queue"):
            return f"    waiting in StreamMoment's queue: place {d['queue']}"
        return f"    downloading {d['percent']}%" if "percent" in d else None
    if stage == "speech":
        return f"    {d['percent']}%"
    if stage == "model":
        return f"    {d['percent']}% ({d['done'] / 1024:.1f} of {d['total'] / 1024:.1f} GB)"
    if stage == "scan":
        return f"    {d['done']}/{d['total']} windows"
    if stage == "rating":
        return f"    {d['done']}/{d['total']} batches"
    if stage == "render" and "title" in d:  # a clip begins; its inner steps are not printed
        return f"  {d['done']}/{d['total']} {d['clip']} {d['title']}"
    if stage == "recap":
        what = {"story": "the model writes the story", "video": "pieces of video", "look": "the webcam and the ads",
                "encode": "encoding"}.get(d.get("step"), d.get("step"))
        return f"  {what}" + (f" {d['done']}/{d['total']}" if "total" in d else "")
    return None


def _fitted(d: dict) -> str:
    if d["by"] != "model":
        return f"  {d['clip']} kept as picked: {d.get('reason', d['status'])}"[:300]
    b, a = d["before"], d["after"]
    return (f"  {d['clip']} {hms(b['start_s'])}–{hms(b['end_s'])} → {hms(a['start_s'])}–{hms(a['end_s'])}"
            f"  start {d['cut_start_s']:+.1f} s, end {-d['cut_end_s']:+.1f} s, {a['end_s'] - a['start_s']:.1f} s")


def _done(d: dict, job: Path) -> str | None:
    if d.get("stage") == "analysis":
        clips, t, tokens = d["clips"], d["timings"], d["tokens"]
        rows = [f"\n{len(clips)} clips from {d['duration_s'] / 3600:.1f} h ({d['episodes_found']} episodes found, {d['episodes_rated']} rated):"]
        rows += [f"  {c['id']}  {hms(c['start_s'])}–{hms(c['end_s'])}  {c['duration_s']:>5.1f} s  {c['score']:>3}  {c['title']}" for c in clips]
        rows.append(f"\nTime: audio {t.get('audio_s', 0):.0f} s, speech {t.get('speech_s', 0):.0f} s, scan {t.get('scan_s', 0):.0f} s, "
                    f"rating {t.get('rating_s', 0):.0f} s" + (f", fit {t['fit_s']:.0f} s." if "fit_s" in t else ".")
                    + (f" Tokens: {tokens['in']} in, {tokens['out']} out." if tokens["in"] else " Tokens: not reported by this model."))
        return "\n".join(rows)
    if d.get("stage") == "recap":
        if d.get("skipped"):
            return f"  No recap: {d.get('reason', '')}"
        return None
    if d.get("stage") == "render":
        report = d["report"]
        rows = [f"  {r['id']}  {r['status']:<6}  {job / r['file'] if r.get('file') else r.get('error')}" for r in report]
        ok = sum(1 for r in report if r["status"] == "done")
        rows.append(f"\n{ok} of {len(report)} clips in {job / d['folder']}")
        return "\n".join(rows)
    return None


def line(event: dict, job: Path) -> str | None:
    """The text the command line prints for this event of the job in folder `job`, or None."""
    kind, d = event["type"], event.get("data", {})
    if kind == "stage":
        return _stage(d, Path(job))
    if kind == "progress":
        return _progress(d)
    if kind == "clip_fitted":
        return _fitted(d)
    if kind == "recap_ready":
        return (f"Recap: {d['duration_s'] / 60:.1f} min from {d['source_s'] / 60:.1f} min of the stream, {d['parts']} parts, "
                f"{len(d.get('chapters') or [])} chapters, {d.get('encoder', '')}, {d.get('seconds', 0):.0f} s\n  {Path(job) / d['file']}\n  cover {Path(job) / d['cover']}")
    if kind == "recap_failed":
        return f"The recap failed: {d['error']}"[:400]
    if kind == "clip_failed":
        return f"    failed: {d['error']}"[:300]
    if kind == "error":  # a failed subscriber does not stop the job; it is logged, not printed as a stop
        return None if d.get("stage") == "subscriber" else f"Stopped: {d['message']}"
    if kind == "done":
        return _done(d, Path(job))
    if kind == "cancelled":
        return "Taken out of the queue." if d.get("stage") == "queue" else "Cancelled."
    if kind == "queued":
        return f"Queued in SMTV: place {d.get('position', '?')}" + (f", after {d['after']}" if d.get("after") else "") + "."
    return None


def printer(job: Path):
    """The journal's echo for the command line: prints each event's line, if it has one."""
    def show(event: dict) -> None:
        text = line(event, job)
        if text is not None:
            print(text, file=sys.stdout, flush=True)
    return show
