"""SMTV.exe opened with a double click (the Windows ZIP): no arguments, so SMTV's window starts.

build.py puts this file into the Windows app as Lib/site-packages/sitecustomize.py, which every Python of that folder
runs on start. SMTV.exe is Python's own windowless program (pythonw.exe) byte for byte: Smart App Control lets it run
by its reputation, and any new or changed program would be blocked, so the start is done here, in Python. Only
SMTV.exe with nothing after it is touched: `SMTV.exe -m smtv …`, `SMTV.exe -c …`, python.exe, pythonw.exe, the
installer's icon and every job keep doing exactly what they say. It starts `SMTV.exe -m smtv app` as a new process
and ends this one, so the window runs in an interpreter that finished starting. SMTV_LAUNCH_CHECK=<file> (smoke.py)
writes what would start into that file instead of starting it.
"""
from __future__ import annotations

import json
import os
import sys


def command(executable: str, orig_argv: list[str]) -> list[str] | None:
    """What a double click on SMTV.exe starts, or None when this is any other start."""
    if os.path.splitext(os.path.basename(executable))[0].lower() != "smtv":
        return None
    if len(orig_argv) != 1:              # anything given (-m, -c, a file): Python does what it says
        return None
    return [executable, "-m", "smtv", "app"]


def main(start=None, end=os._exit) -> None:
    try:
        argv = command(sys.executable, list(getattr(sys, "orig_argv", [sys.executable, "?"])))
        if argv is None:
            return
        check = os.environ.get("SMTV_LAUNCH_CHECK")
        if check:
            with open(check, "w", encoding="utf-8") as f:
                json.dump(argv, f)
        else:
            if start is None:
                import subprocess
                start = subprocess.Popen
            start(argv, close_fds=True)
    except Exception:  # noqa: BLE001 — never stops a Python from starting; a failed start ends as before: silently
        return
    end(0)


if __name__ == "sitecustomize":
    main()
