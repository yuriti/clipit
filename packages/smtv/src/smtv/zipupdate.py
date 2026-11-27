"""The Windows ZIP updates in place: only the program's own files are replaced; data, Clips and anything else a person
put into the folder are never touched.

The window downloads the new ZIP (checked against the signed list of releases, `updates.py`), unpacks it into
data\\run\\update-app and starts the new copy's own ClipIt.exe from there (python.org's own program, byte for byte, signed
by the Python Software Foundation: Smart App Control lets it run, and no script is needed). That process, `python -m smtv.zipupdate swap`, waits for this one
to end, moves the old program's files aside into data\\run\\update-old, copies the new ones in and starts the new
ClipIt.exe. A failure at any step removes only what the copy made and moves the old files back.

data\\run\\update.json says where an update stands (staged, swapping, swapped, confirmed, failed, rollback_failed,
restored). The old program in update-old is deleted only after the new one started once and settled (`settle`, called
by the window under its instance lock); until then `python -m smtv.zipupdate restore` puts it back.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path, PurePosixPath

from smtv_core import paths

STAGING = "update-app"
OLD = "update-old"
STATE = "update.json"
LAUNCHER = "ClipIt.exe"
WAIT_S = 120
# The program's own names at the top of its folder (build.make_win_folder); the new ZIP's own top names count too
OWN = ("ClipIt.exe", "ClipIt.exe.config", "python312.dll", "python3.dll", "vcruntime140.dll", "vcruntime140_1.dll",
       "python312._pth", paths.APP_FOLDER)
HOW_TO_STARTS = ("как запустить", "how to start")       # the how-to text, by the start of its name


def run_dir(top: Path) -> Path:
    return top / paths.PORTABLE_DATA / "run"


def read_state(top: Path) -> dict:
    try:
        found = json.loads((run_dir(top) / STATE).read_text(encoding="utf-8"))
        return found if isinstance(found, dict) else {}
    except (OSError, ValueError):
        return {}


def write_state(top: Path, **state) -> None:
    run_dir(top).mkdir(parents=True, exist_ok=True)
    (run_dir(top) / STATE).write_text(json.dumps(state), encoding="utf-8")


def ours(name: str, also: set[str] | None = None) -> bool:
    """A top-level name of the program: its own files, the how-to text, or a name the new ZIP brings (`also`)."""
    low = name.lower()
    if low in (paths.PORTABLE_DATA.lower(), paths.PORTABLE_CLIPS.lower()):
        return False
    return low in {n.lower() for n in OWN} or name in (also or set()) or \
        (low.endswith(".txt") and low.startswith(HOW_TO_STARTS))


def unpack(archive: Path, staging: Path) -> Path:
    """The ZIP into `staging`; returns its one top folder (the new program). A path outside it stops everything."""
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    with zipfile.ZipFile(archive) as z:
        tops = set()
        for info in z.infolist():
            parts = PurePosixPath(info.filename).parts
            if not parts or info.filename.startswith("/") or ".." in parts or ":" in info.filename:
                raise ValueError(f"the ZIP has a path outside its folder: {info.filename[:80]}")
            tops.add(parts[0])
        if len(tops) != 1:
            raise ValueError(f"the ZIP holds {len(tops)} folders at its top, not one")
        z.extractall(staging)
    new = staging / tops.pop()
    if not (new / LAUNCHER).is_file() or not (new / paths.APP_FOLDER).is_dir():
        raise ValueError(f"the ZIP has no {LAUNCHER} and {paths.APP_FOLDER} folder: not this program")
    return new


def start(archive: Path, top: Path, pid: int, spawn=None) -> list[str]:
    """Unpacks the new program and starts its swap; the caller quits right after. Returns the started command."""
    if read_state(top).get("state") in ("swapped", "rollback_failed"):
        raise RuntimeError("the previous update is not settled yet: start Clip It! once more, then update")
    new = unpack(archive, run_dir(top) / STAGING)
    argv = [str(new / LAUNCHER), "-m", "smtv.zipupdate", "swap", "--new", str(new), "--top", str(top), "--pid", str(pid)]
    swapper = (spawn or _detached)(argv)
    write_state(top, state="staged", pid=swapper if isinstance(swapper, int) else 0)
    return argv


def _detached(argv: list[str]) -> int:
    flags = 0x00000008 | 0x08000000 if sys.platform == "win32" else 0     # DETACHED_PROCESS | CREATE_NO_WINDOW
    return subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                            close_fds=True, creationflags=flags, cwd=str(Path(argv[0]).parent)).pid


def _remove(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def swap(new: Path, top: Path, alive, wait_s: float = WAIT_S, start_new=None) -> None:
    """Replaces the program's own files in `top` by `new` once process `alive()` is gone. On a failure: what the copy
    made goes, the old files come back; nothing else is ever deleted."""
    deadline = time.monotonic() + wait_s
    while alive():
        if time.monotonic() > deadline:
            raise TimeoutError("the old Clip It! did not quit: nothing was replaced")
        time.sleep(0.5)
    old = run_dir(top) / OLD
    if old.exists() and any(old.iterdir()):
        raise RuntimeError(f"{old} still holds an earlier program: nothing was replaced")
    old.mkdir(parents=True, exist_ok=True)
    write_state(top, state="swapping", pid=os.getpid())
    new_names = {f.name for f in new.iterdir() if ours(f.name, {f.name})}
    moved: list[str] = []
    created: list[str] = []
    try:
        for f in sorted(top.iterdir()):
            if ours(f.name, new_names):
                f.replace(old / f.name)
                moved.append(f.name)
        for name in sorted(new_names):
            src = new / name
            created.append(name)          # before the copy: a half-made copy goes too
            if src.is_dir():
                shutil.copytree(src, top / name)
            else:
                shutil.copy2(src, top / name)
    except BaseException as failure:
        why = f"{type(failure).__name__}: {failure}"[:300]
        try:
            for name in created:
                if (top / name).exists() or (top / name).is_symlink():
                    _remove(top / name)
            for name in moved:
                (old / name).replace(top / name)
            write_state(top, state="failed", error=why)
        except BaseException:
            write_state(top, state="rollback_failed", error=why)
        raise
    write_state(top, state="swapped")
    (start_new or _detached)([str(top / LAUNCHER), "-m", "smtv", "app"])


def restore(top: Path) -> list[str]:
    """Puts the program in update-old back (the newer one goes aside into update-app\\undone): the way back."""
    old = run_dir(top) / OLD
    if not old.is_dir() or not any(old.iterdir()):
        raise RuntimeError("no earlier program to put back")
    undone = run_dir(top) / STAGING / "undone"
    undone.mkdir(parents=True, exist_ok=True)
    back = sorted(f.name for f in old.iterdir())
    for name in back:
        if (top / name).exists():
            (top / name).replace(undone / name)
        (old / name).replace(top / name)
    write_state(top, state="restored")
    return back


def settle(top: Path, alive) -> str:
    """Called by the window once it runs, under its instance lock: a new program that started is confirmed, and only
    then the old one goes; the helper folders go once no swap runs. Returns the state it leaves."""
    state = read_state(top)
    status = str(state.get("state", ""))
    if status in ("staged", "swapping") and state.get("pid") and alive(int(state["pid"])):
        return status                     # a swap runs right now: touch nothing
    if status == "swapped":
        write_state(top, state="confirmed")
        status = "confirmed"
    if status == "rollback_failed":
        return status                     # update-old may hold the only copy: kept for `restore`
    run = run_dir(top)
    shutil.rmtree(run / STAGING, ignore_errors=True)
    old = run / OLD
    if status in ("confirmed", "restored") or (old.is_dir() and not any(old.iterdir())):
        shutil.rmtree(old, ignore_errors=True)
    return status


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m smtv.zipupdate")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sw = sub.add_parser("swap")
    sw.add_argument("--new", type=Path, required=True)
    sw.add_argument("--top", type=Path, required=True)
    sw.add_argument("--pid", type=int, required=True)
    rs = sub.add_parser("restore", help="put back the program the last update replaced")
    rs.add_argument("--top", type=Path, default=None)
    args = ap.parse_args(argv)
    if args.cmd == "restore":
        top = args.top or paths.portable_top()
        if top is None:
            print("this is not the Windows ZIP: nothing to put back")
            return 2
        print("put back: " + ", ".join(restore(top)))
        return 0
    from .updates import pid_alive
    log = args.top / paths.PORTABLE_DATA / "logs" / "update.log"
    try:
        swap(args.new, args.top, lambda: pid_alive(args.pid))
        return 0
    except Exception as e:  # noqa: BLE001 — written down: there is no window to say it in
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} the update in place failed: {type(e).__name__}: {e}; the "
                    f"earlier program stays (if it does not start: {LAUNCHER} -m smtv.zipupdate restore)\n")
        if (args.top / LAUNCHER).is_file():
            _detached([str(args.top / LAUNCHER), "-m", "smtv", "app"])     # the old program, as it was
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
