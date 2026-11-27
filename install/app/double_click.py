"""Python's start inside the Windows app (build.py puts this file into app/Lib/site-packages/sitecustomize.py, which
Python runs on every start): the ZIP keeps what it writes in its own folder, and the .pth files of site-packages, which
Python skips under a ._pth file, are read. (A double click on ClipIt.exe is not here: ClipIt.exe is launcher_win.c.)
"""
from __future__ import annotations

import os
import sys


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
