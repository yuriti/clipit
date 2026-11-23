"""One stream of the window's own events (stage 8): requests that appeared, changed or went away, what runs now, tokens
spent, the state of updates. It replaces the page's polls every 2–4 s.

One thread looks at everything about once a second, and only while a window listens; every open stream gets the same
look and sends what changed since its own last send. A new or reconnected stream starts with the whole picture
(`snapshot`), so nothing is lost between two connections and no event numbers are needed. A change made through the API
(start, pause, delete, an update) pokes the thread, so the window sees it at once.

Events (SSE `event:` names; `data:` is JSON):
- `snapshot` — {"boot": this start of the server (a page that saw another one reloads), "jobs": [...], "activity": {...}, "usage": {...}, "update": {...}, "crash": {...}}
- `job` — one request, as GET /api/jobs/<tool>/<job> returns it (new or changed)
- `job_gone` — {"tool", "id"}: the request was deleted
- `activity`, `usage`, `update`, `crash` — the new value of that part (`crash`: crash files, `smtv_core.crash.state`)
"""
from __future__ import annotations

import json
import threading
import time
from typing import Callable

LOOK_S = 1.0          # how often the thread looks while a window listens
HEARTBEAT_S = 15.0


class Hub:
    def __init__(self, look: Callable[[], dict], stopping: threading.Event, every: float = LOOK_S):
        self.look, self.stopping, self.every = look, stopping, every
        self.cond = threading.Condition()
        self.state: dict | None = None
        self.version = 0
        self.listeners = 0
        self._poked = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    # --- the one thread ---------------------------------------------------------------------------------------

    def _start(self) -> None:
        with self._lock:
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run, name="smtv-hub", daemon=True)
                self._thread.start()

    def refresh(self) -> dict:
        """Look now; tell every stream if anything changed. Returns the current state."""
        try:
            new = self.look()
        except Exception as e:  # noqa: BLE001 — one bad look must not end the window's stream
            print(f"hub: {type(e).__name__}: {e}")
            from smtv_core import crash
            crash.record(e, where="server", stage="window events")
            return self.state or {}
        with self.cond:
            if new != self.state:
                self.state = new
                self.version += 1
                self.cond.notify_all()
            return self.state

    def _run(self) -> None:
        while not self.stopping.is_set():
            if self.listeners:
                self.refresh()
            self._poked.wait(self.every)
            self._poked.clear()
        with self.cond:
            self.cond.notify_all()

    def poke(self) -> None:
        """Something changed through the API: look at once instead of within a second."""
        self._poked.set()

    # --- one stream -------------------------------------------------------------------------------------------

    def stream(self, write: Callable[[bytes], None], flush: Callable[[], None] = lambda: None) -> None:
        """Writes SSE to one window until the server stops or the window goes away (an OSError from write)."""
        with self.cond:
            self.listeners += 1
        self._start()
        try:
            state = self.refresh()      # fresh: while nobody listened, the last look may be old
            with self.cond:
                version = self.version
            write(b"retry: 1500\n\n")
            write(_sse("snapshot", _snapshot(state)))
            flush()
            sent, beat = state, time.monotonic()
            while not self.stopping.is_set():
                with self.cond:
                    if self.version == version:
                        self.cond.wait(min(HEARTBEAT_S, max(0.1, HEARTBEAT_S - (time.monotonic() - beat))))
                    version, state = self.version, self.state
                if self.stopping.is_set():
                    break
                if state is not sent and state is not None:
                    for chunk in diff(sent, state):
                        write(chunk)
                    sent = state
                if time.monotonic() - beat >= HEARTBEAT_S:
                    write(b": ping\n\n")
                    beat = time.monotonic()
                flush()
        finally:
            with self.cond:
                self.listeners -= 1


def _key(j: dict) -> str:
    return f"{j['tool']}/{j['id']}"


def _snapshot(state: dict) -> dict:
    return {"boot": state.get("boot"), "jobs": list((state.get("jobs") or {}).values()), "activity": state.get("activity"),
            "usage": state.get("usage"), "update": state.get("update"), "crash": state.get("crash")}


def _sse(event: str, data) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


def diff(old: dict, new: dict) -> list[bytes]:
    """SSE chunks that bring a window from `old` to `new`."""
    out = []
    a, b = old.get("jobs") or {}, new.get("jobs") or {}
    for key, job in b.items():
        if a.get(key) != job:
            out.append(_sse("job", job))
    for key, job in a.items():
        if key not in b:
            out.append(_sse("job_gone", {"tool": job["tool"], "id": job["id"]}))
    for part in ("activity", "usage", "update", "crash"):
        if old.get(part) != new.get(part):
            out.append(_sse(part, new.get(part)))
    return out


def jobs_by_key(jobs: list[dict]) -> dict:
    return {_key(j): j for j in jobs}
