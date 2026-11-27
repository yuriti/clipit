"""`smtv uninstall` and the page's "Remove SMTV from this computer".

Removal is an explicit action, from the command line or SMTV's window (with the session token, after a confirmation),
and it removes:
- the SMTV icon (`launcher.remove`);
- the program: `uv tool uninstall smtv`, started after this process has quit (Windows keeps a running program's files);
  an install made another way (pip, a development checkout) is left alone and the command to remove it is printed;
- clips, jobs, settings and keys only when asked (`--data`, or the page's checkbox): it is the person's work. Only what
  SMTV made itself goes (its folders and files by name, `OWN`): SMTV_HOME may point to a folder with the person's own
  recordings, and those stay. The folder itself goes only when nothing else is left in it. Nothing is removed while
  another SMTV (a window on any port, a job in a terminal) uses the folder.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from smtv_core import paths

from .tools import running_as_uv_tool

PIP_HINT = "pip uninstall smtv smtv-core vodcut"
# What SMTV makes in its folder, by name: only these are ever removed with the data.
OWN = ("data", "models", "run", "logs", "crashes", "reports", "fix", "settings.json", "secrets.json", "secrets.key", "access-key")
OWN_PATTERNS = ("settings.broken-*.json", "settings.*.tmp", "secrets.json.*.tmp", "secrets.key.*.tmp")


def smtv_folder(folder: Path) -> bool:
    """Only a folder that is plainly SMTV's own is ever deleted whole (SMTV_HOME may point anywhere)."""
    try:
        folder = folder.resolve()
    except OSError:
        return False
    if folder in (Path.home().resolve(), Path(folder.anchor)) or len(folder.parts) < 3:
        return False
    names = {p.name for p in folder.iterdir()} if folder.is_dir() else set()
    return bool(names & {"settings.json", "data", "models", "secrets.json"}) and not (names & {".git", "Desktop", "Documents"})


def folder_size(folder: Path) -> int:
    total = 0
    for root, _dirs, files in os.walk(folder, followlinks=False):
        for f in files:
            try:
                total += (Path(root) / f).lstat().st_size
            except OSError:
                pass
    return total


@dataclass
class Plan:
    data_folder: str
    data_bytes: int
    program: str             # "uv" (removed after quitting), "app" (the desktop app: the person removes it the system's
                             # way, the window says how), "folder" (the Windows ZIP: its folder's contents go after
                             # quitting) or "manual" (the command is printed)
    program_command: list[str]
    done: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"data_folder": self.data_folder, "data_bytes": self.data_bytes, "program": self.program,
                "program_command": " ".join(self.program_command), "done": self.done, "notes": self.notes}


def plan() -> Plan:
    from .updates import APP_KINDS, install_kind
    home = paths.home()
    top = paths.portable_top()
    if top is not None:          # the Windows ZIP: everything is in its folder, clips included
        size = sum(folder_size(top / n) for n in (paths.PORTABLE_DATA, paths.PORTABLE_CLIPS) if (top / n).is_dir())
        return Plan(str(top), size, "folder", [])
    size = folder_size(home) if home.is_dir() else 0
    if install_kind() in APP_KINDS:
        return Plan(str(home), size, "app", [])
    uv = running_as_uv_tool()
    return Plan(str(home), size, "uv" if uv else "manual", ["uv", "tool", "uninstall", "smtv"] if uv else PIP_HINT.split())


APP_REMOVE = {"darwin": "drag Clip It! from Applications to the Trash",
              "win32": "Settings → Apps → Installed apps → Clip It! → Uninstall (the ZIP copy: delete its folder)"}


def own_paths(home: Path) -> list[Path]:
    """SMTV's own folders and files in `home`, and the key file wherever it lives (outside `home` on Windows)."""
    out = [home / n for n in OWN if (home / n).exists() or (home / n).is_symlink()]
    for pattern in OWN_PATTERNS:
        out += sorted(home.glob(pattern))
    key = paths.secrets_key_file()
    if key.exists() and key.parent != home:
        out.append(key)
    return out


def _remove(path: Path) -> list[str]:
    """Removes a file or a folder; returns what could not be removed (a file Windows keeps open, no rights)."""
    failed: list[str] = []
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path, onexc=lambda f, p, e: failed.append(f"{p}: {type(e).__name__}")) if sys.version_info >= (3, 12) \
                else shutil.rmtree(path, onerror=lambda f, p, e: failed.append(f"{p}: {e[0].__name__}"))
        else:
            path.unlink()
    except FileNotFoundError:
        pass
    except OSError as e:
        failed.append(f"{path}: {type(e).__name__}")
    return failed


def remove_data(home: Path, p: "Plan") -> list[Path]:
    """Removes SMTV's own data in `home`; returns what is still there (open files: removed after SMTV quits)."""
    left: list[Path] = []
    for path in own_paths(home):
        failed = _remove(path)
        if failed:
            left.append(path)
            p.notes += failed[:5]
        else:
            p.done.append(str(path))
    key = paths.secrets_key_file()
    if key.parent != home and key.parent.name == "smtv":
        try:
            key.parent.rmdir()          # only when empty
        except OSError:
            pass
    try:
        if home.is_dir() and not any(home.iterdir()):
            home.rmdir()
            p.done.append(str(home))
        elif home.is_dir() and not left:
            p.notes.append(f"в папке {home} остались ваши файлы: Clip It! их не трогает")
    except OSError:
        pass
    return left


def outer_temp() -> str:
    """A temporary folder outside the Windows ZIP's own one (which is removed with it): the system's."""
    return os.environ.get("SMTV_OUTER_TEMP") or tempfile.gettempdir()


def later_script(uv: str | None, leftovers: list[Path], wait_pid: int, log: Path, empty_dir: Path | None = None) -> list[str]:
    """A small script that waits for this process to end, then removes what Windows kept open and the program itself.

    A script file, not a `cmd /c "…"` line: paths with spaces and quotes inside a cmd line break (B23). It waits for the
    process by its id rather than a fixed few seconds, and writes what happened to `log`.
    """
    folder = Path(tempfile.mkdtemp(prefix="smtv-remove-", dir=outer_temp()))
    if sys.platform == "win32":
        lines = ["@echo off", "chcp 65001 >nul", ":wait",
                 f'tasklist /FI "PID eq {wait_pid}" /NH | find "{wait_pid}" >nul && (ping -n 2 127.0.0.1 >nul & goto wait)']
        for path in leftovers:
            lines.append(f'if exist "{path}\\*" (rd /s /q "{path}") else (del /f /q /a "{path}")' + f' >>"{log}" 2>&1')
        if uv:
            lines.append(f'"{uv}" tool uninstall smtv >>"{log}" 2>&1')
        if empty_dir:          # without /s: the folder goes only when nothing of the person's own is left in it
            lines.append(f'rd "{empty_dir}" >>"{log}" 2>&1')
        lines.append(f'echo done >>"{log}"')
        script = folder / "remove.cmd"
        script.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
        return ["cmd.exe", "/c", str(script)]
    lines = ["#!/bin/sh", f"while kill -0 {wait_pid} 2>/dev/null; do sleep 1; done"]
    for path in leftovers:
        lines.append(f"rm -rf {_sh(str(path))} >>{_sh(str(log))} 2>&1")
    if uv:
        lines.append(f"{_sh(uv)} tool uninstall smtv >>{_sh(str(log))} 2>&1")
    if empty_dir:
        lines.append(f"rmdir {_sh(str(empty_dir))} >>{_sh(str(log))} 2>&1")
    lines.append(f"echo done >>{_sh(str(log))}")
    script = folder / "remove.sh"
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ["/bin/sh", str(script)]


def _sh(a: str) -> str:
    import shlex
    return shlex.quote(a)


def _detached(argv: list[str]) -> None:
    kwargs: dict = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "close_fds": True}
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x00000008 | 0x08000000   # DETACHED_PROCESS | CREATE_NO_WINDOW
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(argv, cwd=outer_temp(), **kwargs)     # never inside a folder it removes


def _hold(home: Path):
    """The data folder's lock for the removal, or None when another SMTV uses the folder. The window removing SMTV holds
    it itself already (its own process): that is fine."""
    from . import instance
    lock = instance.Lock(home)
    if lock.take(instance.SERVER, removing=True):
        return lock
    info = instance.holder(home, wait=0.5) or {}
    return "self" if info.get("pid") == os.getpid() else None


def folder_leftovers(top: Path, data: bool) -> list[Path]:
    """What goes of the Windows ZIP's folder: the program's own files (zipupdate.ours), with `data` its data and clips
    too. Anything else a person put there stays, and so does the folder then."""
    from .zipupdate import ours
    names = {paths.PORTABLE_DATA.lower(), paths.PORTABLE_CLIPS.lower()} if data else set()
    return sorted(f for f in top.iterdir() if ours(f.name) or f.name.lower() in names)


def remove_folder(p: Plan, data: bool, spawn) -> Plan:
    """The Windows ZIP: Windows keeps a running program's files, so its folder's contents go right after it quits, by
    a small script from the system's temporary folder (the only thing it writes outside its folder)."""
    top = Path(p.data_folder)
    held = _hold(paths.home())
    if held is None:
        p.notes.append("Clip It! is running (a window or a job in a terminal): close it and try again")
        return p
    if held != "self":
        held.release()
    leftovers = folder_leftovers(top, data)
    log = Path(outer_temp()) / "clipit-remove.log"
    spawn(later_script(None, leftovers, os.getpid(), log, empty_dir=top if data else None))
    p.done.append(f"the program, settings and clips in {top}, right after Clip It! quits (the folder too, if nothing of "
                  "yours is left in it)" if data else
                  f"the program in {top}, right after Clip It! quits; your settings ({paths.PORTABLE_DATA}) and clips "
                  f"({paths.PORTABLE_CLIPS}) stay there")
    return p


def run(data: bool, spawn=_detached, system=None) -> Plan:
    """Removes SMTV. The program itself goes after this process quits; the caller quits right after."""
    from . import launcher
    from .updates import find_uv
    p = plan()
    if p.program == "folder":
        return remove_folder(p, data, spawn)
    try:       # the desktop app's icon belongs to the app: it goes when the app is removed the system's way
        made = launcher.remove(system or launcher.this_system()) if p.program != "app" else []
        p.done += made or []
    except (OSError, RuntimeError) as e:
        p.notes.append(f"the icon: {e}")
    leftovers: list[Path] = []
    if data:
        home = Path(p.data_folder)
        if home.is_dir() and smtv_folder(home):
            held = _hold(home)
            if held is None:
                p.notes.append("Clip It! is running (a window or a job in a terminal): data left as it is — close it and try again")
            else:
                try:
                    leftovers = remove_data(home, p)
                finally:
                    if held != "self":
                        held.release()
                if held != "self" and leftovers:
                    # on Windows the lock file under run/ cannot go while the lock is held: once released, try again
                    left_now = []
                    for path in leftovers:
                        if _remove(path):
                            left_now.append(path)
                        else:
                            p.done.append(str(path))
                            p.notes = [n for n in p.notes if not n.startswith(str(path))]
                    leftovers = left_now
                    try:
                        if home.is_dir() and not any(home.iterdir()):
                            home.rmdir()
                            p.done.append(str(home))
                            p.notes = [n for n in p.notes if "остались ваши файлы" not in n]
                        elif home.is_dir() and not leftovers and not any("остались ваши файлы" in n for n in p.notes):
                            p.notes.append(f"в папке {home} остались ваши файлы: Clip It! их не трогает")
                    except OSError:
                        pass
                if leftovers:
                    p.notes.append("some files were in use: they are removed right after Clip It! quits")
        elif home.is_dir():
            p.notes.append(f"{home} does not look like Clip It!'s own folder: left as it is")
    uv = None
    if p.program == "app":
        p.notes.append(f"the program itself: {APP_REMOVE.get(sys.platform, 'delete its folder')}")
    elif p.program == "uv":
        uv = find_uv()
        if not uv:
            p.program = "manual"
            p.notes.append("uv is not on PATH: run `uv tool uninstall smtv` yourself")
    else:
        p.notes.append(f"installed without uv tool: remove the program yourself with `{PIP_HINT}`")
    if uv or leftovers:
        log = Path(tempfile.gettempdir()) / "smtv-remove.log"
        spawn(later_script(uv, leftovers, os.getpid(), log))
        if uv:
            p.done.append(f"the program (uv tool uninstall smtv, right after Clip It! quits; what happened: {log})")
    return p
