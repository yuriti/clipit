"""A job command typed in a terminal (`smtv vodcut run …`) and the one SMTV of this data folder (stage 16).

- SMTV runs: the command hands its job over to it (`POST /api/queue` with the session token from `run/session.json`),
  into its queue, and follows the job's journal here, printing its events as if it ran here. The job shows in SMTV's
  window like any request. Ctrl+C stops only the following; the job goes on in SMTV.
- No SMTV: the command takes the data folder's lock and runs by itself. Another terminal job holding the lock: it waits
  for it (a second executor on the same jobs and settings is exactly what the lock keeps out).
"""
from __future__ import annotations

import http.client
import json
import sys
import time
from pathlib import Path

from smtv_core import events

from . import instance, serve
from .jobs import Tail

WAIT_S, FOLLOW_S, LOST_LOOKS = 1.0, 0.5, 6


def run_command(tool, spec, args, tools, broken, lock: instance.Lock | None = None, wait: float = WAIT_S) -> int:
    lock = lock or instance.Lock()
    said = False
    while True:
        try:
            took = lock.take(instance.JOB, tool=tool.name, job=spec.folder.name)
        except OSError as e:
            print(f"Cannot lock the data folder ({instance.lock_file()}): {e}")
            return 2
        if took:
            try:
                return args.func(args, tools, broken) or 0
            finally:
                lock.release()
        other = instance.holder()
        if other is None:
            continue                       # free a moment ago (someone only looked): take it now
        if other.get("kind") not in (instance.SERVER, instance.JOB):
            session = _session()           # the holder wrote no note: a running SMTV still has its session file
            if instance.alive(session.get("pid")):
                other = {"kind": instance.SERVER, "port": session.get("port"), "pid": session.get("pid")}
        if other.get("kind") == instance.SERVER:
            return hand_over(tool, spec, other)
        if not said:
            print(f"Waiting: another job runs on this data folder ({other.get('job') or '?'}, process {other.get('pid') or '?'}); "
                  "this one starts when it ends. Ctrl+C to give up.", flush=True)
            said = True
        try:
            time.sleep(wait)
        except KeyboardInterrupt:
            print("\nGave up waiting; nothing was started.")
            return 130


def _session() -> dict:
    from .desktop import session_file
    try:
        data = json.loads(session_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _call(port: int, method: str, path: str, body: dict | None = None, token: str | None = None, timeout: float = 15.0):
    """(status, JSON answer); (None, {}) when SMTV does not answer."""
    from . import container
    headers = {"Host": f"{serve.HOST}:{port}", **container.auth_headers()}   # in Docker the page needs its access key too
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-SMTV-Token"] = token
    try:
        conn = http.client.HTTPConnection(serve.HOST, port, timeout=timeout)
        conn.request(method, path, body=data, headers=headers)
        res = conn.getresponse()
        raw = res.read(2_000_000)
        conn.close()
    except (OSError, http.client.HTTPException):
        return None, {}
    try:
        answer = json.loads(raw or b"{}")
    except ValueError:
        answer = {}
    return res.status, answer if isinstance(answer, dict) else {}


def hand_over(tool, spec, other: dict) -> int:
    page = tool.page
    folder = Path(spec.folder).resolve()
    if folder.parent != Path(page.jobs()).resolve():
        print(f"Clip It! is running (process {other.get('pid')}) and takes jobs only in its own data folder, not {folder}. "
              "Run the command without --out, or close Clip It! and run it again.")
        return 2
    session = _session()
    port = other.get("port") or session.get("port")
    if not port or session.get("port") != port or not session.get("token"):
        print(f"Clip It! is running (process {other.get('pid')}), but it did not say how to reach it. "
              "Close Clip It! and run the command again, or start the job from Clip It!'s window.")
        return 2
    code, job = _call(int(port), "POST", "/api/queue", {"tool": tool.name, "job": folder.name, "args": spec.args},
                      token=session["token"])
    if code != 201:
        why = job.get("message") or ("no answer" if code is None else f"HTTP {code}")
        print(f"Clip It! is running, but it did not take the job: {why}")
        return 2
    title = job.get("title") or job["id"]
    print(f"Clip It! is running: the job went to it and shows in its window (Home → {title}).", flush=True)
    return follow(int(port), tool.name, job, folder, spec.echo, token=session["token"])


def _place_text(place: dict | None) -> str:
    if not place:
        return "It waits in Clip It!'s queue."
    after = (place.get("after") or {}).get("title")
    return (f"It waits in Clip It!'s queue: place {place['position']} of {place['waiting']}"
            + (f", it starts after «{after}»." if after else "."))


def follow(port: int, tool: str, job: dict, folder: Path, echo=None, every: float = FOLLOW_S, token: str | None = None) -> int:
    """Prints the job's events until its run ends. Exit code: 0 done, paused or taken out of the queue; 1 failed, stopped
    without a word, deleted, or SMTV went away."""
    tail = Tail(folder / events.FILE_NAME, int(job.get("last") or 0))
    status, place, lost = job.get("status"), None, 0
    if status == "queued":
        place = job.get("queue")
        print(_place_text(place), flush=True)
    try:
        while True:
            for e in tail.read():
                if echo and e["type"] != "queued":
                    echo(e)
            code, info = _call(port, "GET", f"/api/jobs/{tool}/{folder.name}", token=token, timeout=5.0)
            if code == 404:
                print("The request was deleted in Clip It!")
                return 1
            if code != 200:
                lost += 1
                if lost >= LOST_LOOKS:
                    print("Clip It! stopped answering. The job stays as it was: see Clip It!'s window, or run the command again.")
                    return 1
            else:
                lost = 0
                status = info.get("status")
                if status == "queued" and info.get("queue") != place:
                    place = info.get("queue")
                    print(_place_text(place), flush=True)
                if status not in ("running", "queued"):
                    for e in tail.read():
                        if echo:
                            echo(e)
                    return 0 if status in ("done", "cancelled") else 1
            time.sleep(every)
    except KeyboardInterrupt:
        print("\nThis terminal stops following; the job goes on in Clip It!", file=sys.stdout)
        return 0
