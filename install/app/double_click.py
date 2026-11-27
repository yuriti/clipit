"""ClipIt.exe opened with a double click (the Windows ZIP): no arguments, so SMTV's window starts.

build.py puts this file into the Windows app as app/Lib/site-packages/sitecustomize.py, which Python runs on every
start. ClipIt.exe is python.org's own windowless program (pythonw.exe) byte for byte, signed by the Python Software
Foundation: Smart App Control lets it run by that signature, and any program of our own (unsigned) would be blocked,
so the start is done here, in Python. Only
ClipIt.exe with nothing after it is touched: `ClipIt.exe -m smtv …`, `ClipIt.exe -c …`, the installer's icon and every job
keep doing exactly what they say. It starts `ClipIt.exe -m smtv app` as a new process
and ends this one, so the window runs in an interpreter that finished starting. SMTV_LAUNCH_CHECK=<file> (smoke.py)
writes what would start into that file instead of starting it. In the Windows app's layout (app/ under ClipIt.exe) it
also reads the .pth files of site-packages, which Python skips there.
"""
from __future__ import annotations

import json
import os
import sys


NAMES = ("clipit", "smtv")     # ClipIt.exe since 0.1.1; SMTV.exe of an older copy still opens the window


def command(executable: str, orig_argv: list[str]) -> list[str] | None:
    """What a double click on ClipIt.exe starts, or None when this is any other start."""
    if os.path.splitext(os.path.basename(executable))[0].lower() not in NAMES:
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


def app_site(prefix: str) -> str | None:
    """The Windows app's site-packages (app/ under its top folder). Python takes its paths there from the ._pth file,
    which leaves the .pth files of site-packages unread: site.addsitedir reads them."""
    found = os.path.join(prefix, "app", "Lib", "site-packages")
    return found if os.path.isdir(found) else None


def portable() -> None:
    """The Windows ZIP keeps everything in its folder: its data, temporary files and caches (smtv_core.paths), set
    here, before anything else is imported, for this process and every one it starts."""
    try:
        from smtv_core import paths
        paths.apply_portable()
    except Exception:  # noqa: BLE001 — never stops a Python from starting; the window says what is wrong
        return


def read_pth_files() -> None:
    try:
        found = app_site(sys.prefix)
        if found:
            import site
            site.addsitedir(found)
    except Exception:  # noqa: BLE001 — never stops a Python from starting
        return


if __name__ == "sitecustomize":
    read_pth_files()
    portable()
    main()
