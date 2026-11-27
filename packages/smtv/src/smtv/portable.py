"""The Windows ZIP is portable: whatever it writes stays in its own folder (`smtv_core.paths.portable_top`).

Its window's start (`desktop.run_app`) comes here first:
- a folder it cannot write into (put into Program Files, a read-only drive) is said plainly, with what to do, and the
  window does not open: it never falls back to %APPDATA% quietly;
- the files at the top a person never opens are hidden (the DLLs, the ._pth, data\\), so Explorer shows ClipIt.exe,
  the how-to text, app\\ and Clips\\; once the window runs, an update in place is settled (`settle`);
- once, when 0.1.0's settings are in %APPDATA%\\smtv and this folder has none yet, it asks whether to copy the settings
  and AI keys here (a copy: the old folder stays, and the window says where it is). Speech models are not copied:
  they download again on first use (the question says their size), so two sets of models never fill the disk unasked.
Nothing here makes a shortcut or writes outside the folder.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Callable

from smtv_core import paths

from . import i18n

MIGRATION_MARK = "migration.json"     # in data\run: the question was asked; never again, whatever the answer


def ask_windows(text: str, title: str = "Clip It!") -> bool:
    import ctypes
    return ctypes.windll.user32.MessageBoxW(None, text, title, 0x04 | 0x20) == 6   # type: ignore[attr-defined]  # Yes/No; IDYES


def say_windows(text: str, title: str = "Clip It!") -> None:
    import ctypes
    ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)   # type: ignore[attr-defined]


def start(lang: str, top: Path | None = None, ask: Callable[[str], bool] | None = None,
          say: Callable[[str], None] | None = None, hide=None) -> bool:
    """False when the window must not open (the folder cannot be written; the person was told why)."""
    top = top or paths.portable_top()
    if top is None:
        return True
    problem = paths.portable_problem(top)
    if problem:
        (say or say_windows)(i18n.text("portable_readonly", lang, folder=str(top), error=problem))
        return False
    from . import launcher
    try:
        launcher.hide_parts(top, hide)
        launcher.hide_parts(top, hide, names=(paths.PORTABLE_DATA,))
    except OSError as e:
        print(f"portable: could not hide the program's files ({e})")
    offer_migration(top, lang, ask or ask_windows)
    return True


def settle(top: Path | None = None) -> str | None:
    """Once the window runs (under its instance lock): an update in place is confirmed and its leftovers go — never
    while a swap runs, never the old program before the new one started (zipupdate.settle)."""
    top = top or paths.portable_top()
    if top is None:
        return None
    from . import zipupdate
    from .updates import pid_alive
    try:
        return zipupdate.settle(top, pid_alive)
    except OSError as e:
        print(f"portable: the update's leftovers stay for now ({e})")
        return None


# --- 0.1.0's settings, once ---------------------------------------------------------------------------------------

def old_files(old_home: Path, old_key: Path) -> list[Path]:
    """What 0.1.0 (installed, or a ZIP before 0.1.1) kept that is worth taking: settings and AI keys."""
    found = [old_home / "settings.json", old_home / "secrets.json", old_key]
    return [f for f in found if f.is_file()]


def old_key_file() -> Path:
    import os
    local = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(local) / "smtv" / "secrets.key"


def offer_migration(top: Path, lang: str, ask: Callable[[str], bool], old_home: Path | None = None,
                    old_key: Path | None = None) -> str | None:
    """Asks once to copy 0.1.0's settings and keys into this folder: "copied", "declined", None (nothing to ask)."""
    data = top / paths.PORTABLE_DATA
    mark = data / "run" / MIGRATION_MARK
    if mark.exists() or (data / "settings.json").exists():
        return None
    old_home = old_home or paths.standard_home("win32")
    files = old_files(old_home, old_key or old_key_file())
    if not (old_home / "settings.json").is_file() or old_home.resolve() == data.resolve():
        return None
    models = old_home / "models"
    models_gb = sum(f.stat().st_size for f in models.rglob("*") if f.is_file()) / 1e9 if models.is_dir() else 0.0
    yes = ask(i18n.text("portable_migrate", lang, folder=str(old_home), models=f"{models_gb:.1f}"))
    answer = "declined"
    if yes:
        data.mkdir(parents=True, exist_ok=True)
        for f in files:
            shutil.copy2(f, data / f.name)        # secrets.key from %LOCALAPPDATA% lands beside the keys it opens
        answer = "copied"
    mark.parent.mkdir(parents=True, exist_ok=True)
    mark.write_text(json.dumps({"answer": answer, "from": str(old_home)}), encoding="utf-8")
    print(f"portable: 0.1.0's settings in {old_home}: {answer}", file=sys.stderr)
    return answer
