"""A pause the person asked for: the job stops at its next safe point, so nothing it has done is lost.

The page writes FILE into the job folder. The job looks for it between its steps (`checkpoint`): finding it, the job
writes `cancelled` with `graceful: true` to its journal and stops by raising Paused, which its command turns into a
clean exit. A run started again removes the file first. Stopping at once (killing the process) stays possible; the step
it interrupts is then done again.
"""
from __future__ import annotations

from pathlib import Path

from .events import CANCELLED, Journal

FILE = "pause.request"


class Paused(Exception):
    """The job stopped at a safe point because a pause was asked for."""


def ask(job: Path) -> None:
    (Path(job) / FILE).write_text("pause\n", encoding="utf-8")


def requested(job: Path) -> bool:
    return (Path(job) / FILE).exists()


def clear(job: Path) -> None:
    (Path(job) / FILE).unlink(missing_ok=True)


def checkpoint(job: Path, journal: Journal, stage: str) -> None:
    """Between two steps: stop here when a pause was asked for. `stage` is the step that would come next."""
    if requested(job):
        clear(job)
        journal.emit(CANCELLED, by="user", stage=stage, graceful=True)
        raise Paused(stage)
