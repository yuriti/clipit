"""What SMTV is doing right now: for the page's header and window title, the Dock badge, notifications and the idle
shutdown when the page is in a browser.

The window and the jobs are not tied together: a closed window never stops a job. Everything here is read from the jobs'
event journals (the public contract), never from the job processes' output.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from smtv_core import events

from . import i18n
from .jobs import Tail

IDLE_MINUTES = 5          # browser mode: no open page and no running job for this long, and `smtv app` stops by itself

@dataclass
class JobProgress:
    """One running job, folded from its journal events since its run started."""
    tool: str
    job: str
    started: float
    stage: str | None = None
    clips_total: int | None = None
    clips_ready: int = 0
    clips_failed: int = 0
    render_started: float | None = None
    last_clip_t: float | None = None

    def feed(self, e: dict) -> None:
        kind, data, t = e.get("type"), e.get("data") or {}, float(e.get("t") or 0)
        if kind == "stage":
            self.stage = data.get("name") or self.stage
            if self.stage == "render":
                self.render_started, self.clips_ready, self.clips_failed = t, 0, 0
                if isinstance(data.get("clips"), int):
                    self.clips_total = data["clips"]
        elif kind == "clip_ready":
            self.clips_ready += 1
            self.last_clip_t = t
        elif kind == "clip_failed":
            self.clips_failed += 1
            self.last_clip_t = t
        elif kind == "done" and data.get("stage") == "analysis" and isinstance(data.get("clips"), list):
            self.clips_total = len(data["clips"])

    def eta_s(self) -> float | None:
        """Seconds left, once the first clip of the montage is out: the time per clip so far, times the clips left."""
        made = self.clips_ready + self.clips_failed
        if self.stage != "render" or not self.clips_total or not made or not self.render_started or not self.last_clip_t:
            return None
        per = (self.last_clip_t - self.render_started) / made
        return max(0.0, per * (self.clips_total - made))

    def as_dict(self) -> dict:
        eta = self.eta_s()
        return {"tool": self.tool, "job": self.job, "started": self.started, "stage": self.stage, "clips_ready": self.clips_ready,
                "clips_failed": self.clips_failed, "clips_total": self.clips_total, "eta_s": round(eta) if eta is not None else None}


class Tracker:
    """Running jobs of a Runner, each with its journal read incrementally (no full re-read every poll)."""

    def __init__(self, runner):
        self.runner = runner
        self.jobs: dict[tuple[str, str], tuple[JobProgress, Tail]] = {}
        self.lock = threading.Lock()

    def snapshot(self) -> dict:
        with self.lock:
            running = {(r.tool, r.job): r for r in list(self.runner.runs.values()) if not r.finished.is_set()}
            for key in [k for k in self.jobs if k not in running]:
                del self.jobs[key]
            for key, run in running.items():
                if key not in self.jobs:
                    self.jobs[key] = (JobProgress(run.tool, run.job, run.started), Tail(Path(run.folder) / events.FILE_NAME, run.first))
                progress, tail = self.jobs[key]
                for e in tail.read():
                    progress.feed(e)
            jobs = [p.as_dict() for p, _ in self.jobs.values()]
        return summary(jobs)


def summary(jobs: list[dict]) -> dict:
    totals = [j["clips_total"] for j in jobs]
    known = all(isinstance(x, int) for x in totals) and bool(jobs)
    etas = [j["eta_s"] for j in jobs]
    return {"running": len(jobs), "jobs": sorted(jobs, key=lambda j: j["started"]),
            "clips_ready": sum(j["clips_ready"] for j in jobs), "clips_total": sum(totals) if known else None,
            "eta_s": max(etas) if jobs and all(e is not None for e in etas) else None}


def finished_text(status: str, title: str, clips: int, lang: str = "en") -> tuple[str, str] | None:
    """A system notification for a job that ended while nobody may be looking: (title, message), or None (cancelled)."""
    name = title or i18n.text("notify_the_job", lang)
    if status == "done":
        return i18n.text("notify_done_title", lang), i18n.text("notify_done_body", lang, name=name, clips=clips)
    if status == "failed":
        return i18n.text("notify_failed_title", lang), i18n.text("notify_failed_body", lang, name=name)
    return None


@dataclass
class IdleWatch:
    """Stop after `idle_s` with no open page and no running job (only when the page is in a browser: SMTV's own window
    ends the process when it closes)."""
    idle_s: float
    busy: Callable[[], bool]          # an open page or a running job
    keep: Callable[[], bool]          # anything that keeps SMTV up regardless
    clock: Callable[[], float] = time.monotonic
    since: float | None = field(default=None)

    def should_stop(self) -> bool:
        if self.busy() or self.keep():
            self.since = None
            return False
        now = self.clock()
        if self.since is None:
            self.since = now
        return now - self.since >= self.idle_s
