"""Crash files: an error nobody expected is written to `<SMTV home>/crashes/<time>.json` (the stack, where it happened,
the step, the versions), so `smtv report` can put it in a report and the window can offer «Report a problem».

Writing a crash file never raises and never stops what was going on: it is a note, not a handler. Anything that looks
like a key is cut out before the file is written (`keycheck.redact`); the report cuts the saved keys out once more.
Only the newest `KEEP` files stay.
"""
from __future__ import annotations

import json
import os
import re
import platform
import sys
import threading
import time
import traceback
from importlib import metadata
from pathlib import Path

from . import paths

FOLDER = "crashes"
KEEP = 50
SEEN = ".seen"                # the newest crash the window already offered to report
REPEAT_S = 600.0             # the same error from the same place again within this time: one file is enough
_lock = threading.Lock()
_hooks_for: str | None = None
_recent: dict[tuple, float] = {}


def folder() -> Path:
    return paths.home() / FOLDER


def versions() -> dict:
    """smtv, smtv-core and every installed tool, as the installed packages say."""
    out = {}
    for dist in ("smtv", "smtv-core"):
        try:
            out[dist] = metadata.version(dist)
        except metadata.PackageNotFoundError:
            pass
    try:
        for ep in metadata.entry_points(group="smtv.tools"):
            dist = getattr(ep, "dist", None)
            if dist is not None:
                out[dist.metadata["Name"]] = dist.version
    except Exception:  # noqa: BLE001 — versions are a nicety; a broken entry point must not cost the crash file
        pass
    return out


def _redact(text: str) -> str:
    from .llm.keycheck import redact_all
    return redact_all(text)


def record(error: BaseException | None = None, *, where: str, stage: str | None = None, tool: str | None = None,
           job: str | None = None, message: str | None = None, stack: str | None = None) -> Path | None:
    """Writes one crash file. `error` gives the type, message and stack; the window's own errors (JavaScript) come as
    `message` and `stack` instead. Returns the file, or None when it could not be written (said on stderr)."""
    try:
        done = getattr(error, "_smtv_crash", None) if error is not None else None
        if done is not None:
            return done                       # already written where it was caught; the hook sees it again on its way out
        kind = type(error).__name__ if error is not None else "Error"
        text = message if message is not None else (str(error) if error is not None else "")
        now = time.time()
        seen_key = (where, stage, kind, re.sub(r"\d+", "#", text[:300]))   # numbers differ from one repeat to the next
        with _lock:
            if now - _recent.get(seen_key, -REPEAT_S) < REPEAT_S:
                return None
        if stack is None and error is not None:
            stack = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        data = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(now)) + time.strftime("%z", time.localtime(now)),
            "where": where, "stage": stage, "tool": tool, "job": job,
            "type": kind, "message": _redact(text)[:4000], "stack": _redact(stack or "")[-20000:],
            "versions": versions(), "python": platform.python_version(), "system": f"{platform.system()} {platform.release()}",
            "pid": os.getpid(),
        }
        base = time.strftime("%Y%m%d-%H%M%S", time.localtime(now)) + f"-{int(now * 1000) % 1000:03d}"
        with _lock:
            target = folder()
            target.mkdir(parents=True, exist_ok=True)
            path = target / f"{base}.json"
            n = 1
            while path.exists():
                path = target / f"{base}-{n}.json"
                n += 1
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, path)
            _recent[seen_key] = now           # only a file that was written stops the repeats
            if len(_recent) > 500:
                for k in sorted(_recent, key=_recent.get)[:250]:
                    del _recent[k]
            for old in files()[KEEP:]:
                try:
                    old.unlink()
                except OSError:
                    pass
        if error is not None:
            try:
                error._smtv_crash = path          # type: ignore[attr-defined]
            except (AttributeError, TypeError):
                pass
        return path
    except Exception as e:  # noqa: BLE001 — a crash file that cannot be written must not hide the crash itself
        try:
            sys.stderr.write(f"smtv: could not write a crash file ({type(e).__name__}: {e})\n")
        except Exception:  # noqa: BLE001
            pass
        return None


def files() -> list[Path]:
    """Crash files, newest first."""
    try:
        return sorted((p for p in folder().glob("*.json") if p.is_file()), key=lambda p: p.name, reverse=True)
    except OSError:
        return []


def read(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def state() -> dict:
    """For the window: how many crash files there are, the newest one, and whether it was already offered."""
    all_ = files()
    newest = all_[0].name if all_ else None
    seen = seen_mark()
    return {"count": len(all_), "newest": newest, "unseen": bool(newest and newest > seen)}


def seen_mark() -> str:
    try:
        return (folder() / SEEN).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def mark_seen(name: str | None = None) -> bool:
    """The window offered crashes up to `name` (default: the newest). A crash newer than that is offered again.
    False when the mark could not be written (said on stderr): the window then offers the same crash once more."""
    newest = name or next((p.name for p in files()[:1]), None)
    if not newest or newest <= seen_mark():
        return True
    try:
        folder().mkdir(parents=True, exist_ok=True)
        (folder() / SEEN).write_text(newest, encoding="utf-8")
        return True
    except OSError as e:
        sys.stderr.write(f"smtv: could not mark crashes as seen ({type(e).__name__}: {e})\n")
        return False


def install_hooks(where: str) -> None:
    """Unhandled errors of this process (its main thread and every other thread) leave a crash file, then go on to the
    hooks that were there before (Python prints the traceback as usual). Once per process."""
    global _hooks_for
    if _hooks_for is not None:
        return
    _hooks_for = where
    before_sys, before_thread = sys.excepthook, threading.excepthook

    def on_error(kind, value, tb):
        if not issubclass(kind, (KeyboardInterrupt, SystemExit)):
            record(value.with_traceback(tb) if value is not None else None, where=where, stage="main")
        before_sys(kind, value, tb)

    def on_thread_error(args):
        if args.exc_type is not None and not issubclass(args.exc_type, SystemExit) and args.exc_value is not None:
            record(args.exc_value, where=where, stage=f"thread {args.thread.name if args.thread else '?'}")
        before_thread(args)

    sys.excepthook = on_error
    threading.excepthook = on_thread_error
