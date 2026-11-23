"""Tokens spent on this computer: the sum of every `model_call` event in every job's journal (the public contract).

Shown at the bottom of the window's side rail. Locally it is a sum; later, with a StreamMoment account, a balance.
A journal is followed from where the last read stopped (`jobs.Tail`, as `activity.Tracker` does): a running job adds a
line a second, and only that line is read (B27: the whole journal was read again every second). A journal that got
shorter was replaced: it is counted again from its start.
"""
from __future__ import annotations

import threading
from pathlib import Path

from smtv_core import events

from .jobs import Tail


def _empty() -> dict:
    return {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "cost_known": False, "unreported": 0}


def _add(total: dict, part: dict) -> None:
    for k in ("calls", "tokens_in", "tokens_out", "unreported"):
        total[k] += part[k]
    total["cost_usd"] += part["cost_usd"]
    total["cost_known"] = total["cost_known"] or part["cost_known"]


def _count(value) -> int | None:
    """A token count: a whole number, not negative (True is not a count)."""
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _purpose_empty() -> dict:
    return {"calls": 0, "seconds": 0.0, "timed": 0, "errors": 0, "cost_usd": 0.0, "cost_known": False}


def _journal_empty() -> dict:
    return {**_empty(), "purposes": {}}


def add_event(out: dict, e: dict) -> None:
    """One event into a journal's usage (`_journal_empty`). A call without token counts (codex does not report them) is
    counted as unreported; `purposes` holds the same per purpose of the call (an agent's line on its card, stage 10)."""
    if e.get("type") != "model_call":
        return
    d = e.get("data")
    if not isinstance(d, dict):       # a damaged line counts for nothing and never breaks the sum of the others
        return
    out["calls"] += 1
    purpose = d.get("purpose") if isinstance(d.get("purpose"), str) else ""
    row = out["purposes"].setdefault(purpose, _purpose_empty())
    row["calls"] += 1
    if d.get("error"):
        row["errors"] += 1
    seconds = d.get("seconds")
    if isinstance(seconds, (int, float)) and not isinstance(seconds, bool) and seconds >= 0:
        row["seconds"] += float(seconds)
        row["timed"] += 1
    tin, tout = _count(d.get("tokens_in")), _count(d.get("tokens_out"))
    if tin is not None or tout is not None:
        out["tokens_in"] += tin or 0
        out["tokens_out"] += tout or 0
    else:
        out["unreported"] += 1
    cost = d.get("cost_usd")
    if isinstance(cost, (int, float)) and not isinstance(cost, bool) and cost >= 0:
        out["cost_usd"] += float(cost)
        out["cost_known"] = True
        row["cost_usd"] += float(cost)
        row["cost_known"] = True


def journal_usage(path: Path) -> dict:
    """One journal's model calls, read whole."""
    out = _journal_empty()
    for e in events.read(path):
        add_event(out, e)
    return out


class _Followed:
    """One journal followed: where its reading stopped, and its usage so far."""

    def __init__(self, path: Path):
        self.tail = Tail(path)
        self.part = _journal_empty()

    def catch_up(self) -> None:
        try:
            fresh = self.tail.read()
        except OSError as e:     # held by another program for a moment (Windows): the next ask reads it
            print(f"usage: {self.tail.path} is not readable now ({type(e).__name__}: {e})")
            return
        for e in fresh:
            add_event(self.part, e)


class Usage:
    """The sum over many journals, each read again only when it changed."""

    def __init__(self):
        self._cache: dict[Path, _Followed] = {}
        self._lock = threading.Lock()

    def _parts(self, journals: list[Path]) -> list[dict]:
        """Each journal's usage, with only its new lines read; journals gone from the list are forgotten."""
        parts = []
        with self._lock:
            alive = set()
            for path in journals:
                try:
                    size = path.stat().st_size
                except OSError:
                    continue
                alive.add(path)
                followed = self._cache.get(path)
                if followed is None or size < followed.tail.offset:     # new, or replaced by a shorter one
                    followed = self._cache[path] = _Followed(path)
                followed.catch_up()
                parts.append(followed.part)
            for gone in set(self._cache) - alive:
                del self._cache[gone]
        return parts

    def by_purpose(self, journals: list[Path]) -> dict:
        """{purpose: {"calls", "seconds" (sum over timed calls), "timed", "errors", "cost_usd", "cost_known"}}."""
        out: dict[str, dict] = {}
        for part in self._parts(journals):
            for purpose, row in part["purposes"].items():
                acc = out.setdefault(purpose, _purpose_empty())
                for k in ("calls", "seconds", "timed", "errors", "cost_usd"):
                    acc[k] += row[k]
                acc["cost_known"] = acc["cost_known"] or row["cost_known"]
        return out

    def total(self, journals: list[Path]) -> dict:
        total = _empty()
        for part in self._parts(journals):
            _add(total, part)
        total["tokens"] = total["tokens_in"] + total["tokens_out"]
        total["cost_usd"] = round(total["cost_usd"], 6)
        return total
