"""The job's event journal: one numbered line per event in `events.jsonl` inside the job folder.

This is a public contract (see `schema.json` and `contract.py`). Every tool writes what happened during a job here: a
stage began, progress, an episode was found, a model call took this long and these tokens, a clip is ready, an error,
the end. Everything that shows a job reads the same lines: the command line prints them as text, the page streams them
(a reconnecting page asks for everything after the last number it saw), subscribers get them as they are written, and
later the cloud and MCP.

A line is {"n": number, "t": unix time, "type": ..., "v": contract version, "job": job id, "tool": tool name, "data": {...}}.

Rules the contract keeps:
- events are facts in the past tense; the pipeline calls its steps itself and in order, an event never starts a step;
- events carry short data and paths of job files relative to the job folder, never whole transcripts or frames;
- commands (cancel, render again) are a separate API, not events;
- no outside bus: the journal file and subscribers in the process.

Numbers go up by one and continue after a rerun of the same job. Writing is safe from several threads of one process;
one job is written by one process at a time.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Callable, Iterator

from . import contract
from . import subscribers as installed
from .subscribers import Subscriber, Subscription

FILE_NAME = "events.jsonl"
VERSION = contract.version()

STAGE, PROGRESS, MODEL_CALL, ERROR, DONE = "stage", "progress", "model_call", "error", "done"
EPISODE_FOUND, EPISODE_RATED = "episode_found", "episode_rated"
LAYOUT_CHOSEN, ADS_FOUND, CLIP_READY, CLIP_FAILED = "layout_chosen", "ads_found", "clip_ready", "clip_failed"
CLIP_FITTED = "clip_fitted"   # Fit cut a clip (VodCut's «precise» switch): bounds before and after
CLIP_CHECKED, CLIP_FIXED, CLIP_REVIEWED = "clip_checked", "clip_fixed", "clip_reviewed"   # the critic (stage 14): a look, its one edit, the outcome
CANCELLED = "cancelled"   # the page, after stopping the job process at once; or the job itself, paused at a safe point (graceful)
QUEUED = "queued"         # SMTV put the job in its queue behind another job of the same tool (written by SMTV, not by the job)
TYPES = contract.types()


def _lines(path: Path) -> Iterator[dict]:
    """Complete, readable events in file order. A line still being written (no newline yet) or broken by a crash is skipped."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return
    for line in raw.split(b"\n")[:-1]:  # the part after the last newline is not finished
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and isinstance(event.get("n"), int):
            yield event


def read(path: Path, after: int = 0) -> list[dict]:
    """Events with a number greater than `after` (0: all). `path` is the journal file or the job folder."""
    path = Path(path)
    if path.is_dir():
        path = path / FILE_NAME
    return [e for e in _lines(path) if e["n"] > after]


def last_number(path: Path) -> int:
    return max((e["n"] for e in _lines(Path(path))), default=0)


class Journal:
    """Writes the events of one job.

    `echo` gets every event right after it is written, in the writing thread (the command line prints it).
    `subscribe` adds code that gets every event in its own thread. Installed subscribers (entry points
    "smtv.subscribers") are added unless `subscribers` is given; pass [] for none.
    """

    def __init__(self, job: Path, *, tool: str, echo: Callable[[dict], None] | None = None,
                 subscribers: list[tuple[str, Subscriber]] | None = None):
        job = Path(job)
        job.mkdir(parents=True, exist_ok=True)
        self.folder, self.job_id, self.tool = job, job.name, tool
        self.path = job / FILE_NAME
        self.echo = echo
        self._lock = threading.Lock()
        self._subs: list[Subscription] = []
        self._n = last_number(self.path)
        if self.path.exists() and self.path.stat().st_size:
            with self.path.open("rb") as f:
                f.seek(-1, 2)
                torn = f.read(1) != b"\n"
            if torn:  # a crash in the middle of a line: close it so the next event starts on its own line
                with self.path.open("ab") as f:
                    f.write(b"\n")
        for name, fn in (installed.load() if subscribers is None else subscribers):
            self.subscribe(fn, name=name)

    @property
    def last(self) -> int:
        return self._n

    def emit(self, type: str, **data) -> dict:  # noqa: A002 — the field is called type everywhere it is read
        if type not in TYPES:
            raise ValueError(f"unknown event type {type!r}")
        with self._lock:
            n = self._n + 1        # counted only once written: a failed write leaves no gap in the numbers
            event = {"n": n, "t": round(time.time(), 3), "type": type, "v": VERSION, "job": self.job_id, "tool": self.tool, "data": data}
            line = json.dumps(event, ensure_ascii=False, default=str) + "\n"
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line)
            self._n = n
            for sub in self._subs:
                sub.offer(event)
            if self.echo:
                self.echo(event)
        return event

    def subscribe(self, fn: Subscriber, *, after: int | None = None, name: str | None = None) -> Subscription:
        """`fn` gets every event from now on; with `after`, first every event in the journal after that number (catching
        up), then the live ones, with no gap and no repeat."""
        with self._lock:  # no event can be written between reading the history and joining the live stream
            backlog = self.read(after) if after is not None else []
            sub = Subscription(name or getattr(fn, "__name__", "subscriber"), fn, backlog, self._subscriber_failed)
            self._subs.append(sub)
        return sub

    def _subscriber_failed(self, name: str, error: Exception) -> None:
        self.emit(ERROR, stage="subscriber", subscriber=name, message=f"{type(error).__name__}: {error}"[:500])

    def close(self, timeout: float = 5.0) -> None:
        """Gives subscribers up to `timeout` seconds in all to take the events already written, then lets them go."""
        deadline = time.monotonic() + timeout
        with self._lock:
            subs, self._subs = self._subs, []
        for sub in subs:
            sub.stop(max(0.0, deadline - time.monotonic()))

    def read(self, after: int = 0) -> list[dict]:
        return read(self.path, after)

    def __enter__(self) -> Journal:
        return self

    def __exit__(self, *exc) -> None:
        self.close()
