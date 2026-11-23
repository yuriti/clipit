"""Subscribers inside the process: code that gets every event of a job right after it is written to the journal.

A package declares one in the entry point group "smtv.subscribers", the same way tools plug into "smtv.tools":

    [project.entry-points."smtv.subscribers"]
    notify = "my_package.notify:on_event"     # a callable taking one event (a dict)

Every subscriber runs in its own thread with its own queue: a slow subscriber does not slow the job, and a failing one
does not stop it (its first failure is logged and written to the journal as an error event). If the queue overflows,
events are dropped for that subscriber only; it can catch up by reading the journal after the last number it saw.
Subscribers observe facts; they never drive the pipeline, which calls its steps itself, in order.
"""
from __future__ import annotations

import logging
import queue
import threading
from importlib.metadata import entry_points
from typing import Callable

ENTRY_POINT_GROUP = "smtv.subscribers"
QUEUE_LIMIT = 10_000
log = logging.getLogger("smtv.events")

Subscriber = Callable[[dict], None]


def load() -> list[tuple[str, Subscriber]]:
    """Installed subscribers. One that fails to load is logged and skipped: a job never fails because of a subscriber."""
    found = []
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        try:
            fn = ep.load()
        except Exception as e:  # noqa: BLE001 — any import error of a third-party package
            log.warning("subscriber %s not loaded: %s: %s", ep.name, type(e).__name__, e)
            continue
        if callable(fn):
            found.append((ep.name, fn))
        else:
            log.warning("subscriber %s is not callable", ep.name)
    return found


class Subscription:
    """One subscriber's thread and queue. Events from `backlog` (history) come first, then live ones."""

    def __init__(self, name: str, fn: Subscriber, backlog: list[dict], on_failure: Callable[[str, Exception], None]):
        self.name, self.fn, self.on_failure = name, fn, on_failure
        self.queue: queue.Queue = queue.Queue(QUEUE_LIMIT)
        self.backlog = backlog
        self.delivered = self.failures = self.dropped = 0
        self.thread = threading.Thread(target=self._loop, name=f"smtv-subscriber-{name}", daemon=True)
        self.thread.start()

    def offer(self, event: dict) -> None:
        try:
            self.queue.put_nowait(event)
        except queue.Full:
            if not self.dropped:
                log.warning("subscriber %s is too slow: events are dropped for it; it can read them from the journal", self.name)
            self.dropped += 1

    def _deliver(self, event: dict) -> None:
        try:
            self.fn(event)
            self.delivered += 1
        except Exception as e:  # noqa: BLE001 — a subscriber's error must not reach the job
            self.failures += 1
            log.warning("subscriber %s failed on event %s: %s: %s", self.name, event.get("n"), type(e).__name__, e)
            if self.failures == 1:
                self.on_failure(self.name, e)

    def _loop(self) -> None:
        for event in self.backlog:
            self._deliver(event)
        self.backlog = []
        while True:
            event = self.queue.get()
            if event is None:
                return
            self._deliver(event)

    def stop(self, timeout: float) -> bool:
        """Lets the queued events through, then ends the thread. False when the subscriber did not finish in time."""
        try:
            self.queue.put(None, timeout=timeout)
        except queue.Full:
            return False
        self.thread.join(timeout)
        return not self.thread.is_alive()
