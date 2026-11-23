"""`smtv shortcut`: the SMTV icon, so SMTV starts like any other program, without a terminal.

What it makes, for the person who is signed in (no administrator rights anywhere):
- macOS: `~/Applications/SMTV.app`, whose script hands over to `smtv app` (SMTV's own window, `window.py`): the process
  is SMTV.app's, with its name and icon in the Dock, and a second click brings the running window forward.
- Windows: `SMTV.lnk` on the desktop and in the Start menu, running `pythonw` (no console window).
- Linux: `smtv.desktop` in the applications menu and on the desktop.

Everything that touches the system goes through `System` (files under `home`, helper commands), so the tests check what
would be written without writing it.
"""
from __future__ import annotations

import base64
import os
import plistlib
import shlex
import shutil
import struct
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from smtv_core import paths, proc

NAME = "SMTV"
ENTRY = "smtv"
BUNDLE_ID = "tv.streammoment.smtv"
ICONS = Path(__file__).parent / "web" / "icons"
LSREGISTER = "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
MAC_EXEC = NAME
MARK = "Made by `smtv shortcut`; `smtv shortcut --remove` deletes it."


def _run(argv: list[str]) -> int:
    """A helper command; a missing one is not an error (the shortcut still works)."""
    try:
        return subprocess.run(argv, stdin=subprocess.DEVNULL, capture_output=True, timeout=60, **proc.hidden()).returncode
    except (OSError, subprocess.TimeoutExpired):
        return -1


@dataclass
class System:
    platform: str                    # sys.platform: darwin, win32, linux
    home: Path                       # the person's home folder
    python: str                      # the interpreter that runs smtv, windowless on Windows (pythonw)
    env: dict[str, str]              # carried into the started server: PATH (ffmpeg, yt-dlp, codex) and SMTV_HOME if set
    data: Path                       # SMTV's own folder (icons for Windows and Linux live here)
    run: Callable[[list[str]], int] = _run
    desktop: Path | None = None      # Linux: the desktop folder, if there is one
    made: list[str] = field(default_factory=list)


def this_system() -> System:
    platform = sys.platform
    python = sys.executable
    if platform == "win32":
        windowless = Path(sys.executable).with_name("pythonw.exe")
        python = str(windowless if windowless.exists() else Path(sys.executable))
    env = {}
    if platform != "win32":
        env["PATH"] = os.environ.get("PATH", "/usr/bin:/bin")
    if os.environ.get("SMTV_HOME", "").strip():
        env["SMTV_HOME"] = str(Path(os.environ["SMTV_HOME"]).expanduser().resolve())
    system = System(platform, Path.home(), python, env, paths.home())
    if platform.startswith("linux"):
        system.desktop = _linux_desktop(system.home)
    return system


def _linux_desktop(home: Path) -> Path | None:
    try:
        out = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        out = ""
    folder = Path(out) if out else home / "Desktop"
    return folder if folder.is_dir() and folder != home else None


def launch_args(system: System, python: str | None = None) -> list[str]:
    return [python or system.python, "-m", "smtv", "app"]


# --- the process name: "SMTV" in Activity Monitor and ps, not "Python" ---------------------------------------------
# The system names a process after the file it started from. So the icon starts Python through a symlink named SMTV.
# It lives in the environment's own folder, next to pyvenv.cfg, where Python still finds its packages (not in bin/,
# where `smtv` already is: on macOS SMTV and smtv are one name).
# macOS framework builds (python.org, Homebrew) start through a small bin/python3.x that runs Resources/Python.app again,
# so the process would be Python.app's, named Python with Python's icon. There SMTV.app gets its own copy of that inner
# program (about 50 KB): macOS then counts the process as SMTV.app's, with its name and icon. __PYVENV_LAUNCHER__ tells it
# which environment it belongs to (what the small one does). The copy is tied to the installed Python version: the
# script tries it first and falls back to plain Python, and `smtv shortcut` after a Python upgrade makes it again.

def _framework_app_python(python: str) -> str | None:
    """macOS: the program inside Python.app behind a framework build's bin/python3.x, by a path that survives
    upgrades (Homebrew's opt/ link, not the Cellar version), or None for other builds."""
    p = python
    for _ in range(12):
        inner = os.path.join(os.path.dirname(p), "..", "Resources", "Python.app", "Contents", "MacOS", "Python")
        if os.path.exists(inner):
            return inner
        if not os.path.islink(p):
            return None
        p = os.path.join(os.path.dirname(p), os.readlink(p))
    return None


def _named_python_place(s: System) -> Path:
    venv = Path(s.python).parent.parent
    return (venv if (venv / "pyvenv.cfg").exists() else s.data / "launcher") / NAME


def named_python(s: System) -> tuple[str, dict[str, str]] | None:
    """The symlink named SMTV and the environment it needs; None if something else is in its place."""
    link = _named_python_place(s)
    framework = _framework_app_python(s.python) if s.platform == "darwin" else None
    if link.exists() and not link.is_symlink():
        return None
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink():
        link.unlink()
    os.symlink(framework or s.python, link)
    return str(link), ({"__PYVENV_LAUNCHER__": s.python} if framework else {})


MAC_PYTHON = "smtv-python"


def mac_python(s: System, app: Path) -> tuple[str, dict[str, str]] | None:
    """macOS: the copy of a framework build's inner program inside SMTV.app; otherwise the symlink named SMTV."""
    inner = _framework_app_python(s.python)
    if not inner:
        return named_python(s)
    copy = app / "Contents" / "MacOS" / MAC_PYTHON
    shutil.copy2(inner, copy)
    return str(copy), {"__PYVENV_LAUNCHER__": s.python}


def _remove_named_python(s: System) -> None:
    link = _named_python_place(s)
    if link.is_symlink():
        link.unlink()


# --- icon files, from the PNGs the page uses ---------------------------------------------------------------------

def icns(pngs: dict[str, bytes]) -> bytes:
    """A macOS .icns made of PNG entries (ic09 = 512 px, ic10 = 1024 px)."""
    body = b"".join(kind.encode("ascii") + struct.pack(">I", len(data) + 8) + data for kind, data in pngs.items())
    return b"icns" + struct.pack(">I", len(body) + 8) + body


def ico(png: bytes, size: int = 256) -> bytes:
    """A Windows .ico with one PNG entry (Windows Vista and later read PNG inside .ico)."""
    side = 0 if size >= 256 else size
    return struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(png), 22) + png


# --- macOS ---------------------------------------------------------------------------------------------------------

def _mac_app(s: System) -> Path:
    return s.home / "Applications" / f"{NAME}.app"


APP_KIND = "SMTVInstallKind"    # in the Info.plist of SMTV.app from the .dmg (install/app/build.py)


def _is_ours(app: Path) -> bool:
    """SMTV.app made by `smtv shortcut`. The app from the .dmg carries the same identifier but is a whole program, not
    an icon: it is never replaced or removed from here."""
    try:
        info = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
    except (OSError, ValueError, plistlib.InvalidFileException):
        return False
    return info.get("CFBundleIdentifier") == BUNDLE_ID and APP_KIND not in info


def mac_script(s: System, named: tuple[str, dict[str, str]] | None = None) -> str:
    lines = ["#!/bin/sh", f"# {MARK}"]
    lines += [f"export {k}={shlex.quote(v)}" for k, v in sorted(s.env.items())]
    # `exec`: the process macOS started for SMTV.app becomes SMTV itself, so the Dock shows it while its window is open
    # and a second click brings that window forward. Arguments (from Finder or elsewhere) are never passed on.
    lines += ['cd "$HOME" || exit 1']
    plain = "exec " + " ".join(shlex.quote(a) for a in launch_args(s)) + " </dev/null >/dev/null 2>&1"
    if named:
        link, env = named
        # Python under SMTV's name; if it no longer starts (Python was upgraded or removed), plain Python still starts SMTV.
        lines += [*(f"export {k}={shlex.quote(v)}" for k, v in sorted(env.items())),
                  f"if {shlex.quote(link)} -c '' >/dev/null 2>&1; then",
                  "  exec " + " ".join(shlex.quote(a) for a in launch_args(s, python=link)) + " </dev/null >/dev/null 2>&1",
                  "fi", plain]
    else:
        lines.append(plain)
    return "\n".join(lines + [""])


def mac_info(s: System) -> dict:
    from . import __version__
    return {
        "CFBundleIdentifier": BUNDLE_ID, "CFBundleName": NAME, "CFBundleDisplayName": NAME, "CFBundleExecutable": MAC_EXEC,
        "CFBundleIconFile": "smtv", "CFBundlePackageType": "APPL", "CFBundleShortVersionString": __version__.split(".dev")[0],
        "CFBundleInfoDictionaryVersion": "6.0", "LSMinimumSystemVersion": "11.0", "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.video",
    }


def _mac_install(s: System) -> None:
    app = _mac_app(s)
    if app.exists() and not _is_ours(app):
        raise FileExistsError(f"{app} exists and is not made by smtv: move it away, then run smtv shortcut again")
    if app.exists():
        shutil.rmtree(app)
    (app / "Contents" / "MacOS").mkdir(parents=True)
    (app / "Contents" / "Resources").mkdir()
    (app / "Contents" / "Info.plist").write_bytes(plistlib.dumps(mac_info(s)))
    script = app / "Contents" / "MacOS" / MAC_EXEC
    script.write_text(mac_script(s, mac_python(s, app)), encoding="utf-8")
    script.chmod(0o755)
    icon = app / "Contents" / "Resources" / "smtv.icns"
    icon.write_bytes(icns({"ic09": (ICONS / "icon-mac-512.png").read_bytes(), "ic10": (ICONS / "icon-mac-1024.png").read_bytes()}))
    # A local signature (ad-hoc: no certificate, nothing paid), with SMTV's identifier on the Python copy too: macOS lets
    # only a signed app send notifications under its own name and icon. Without codesign, notifications fall back to
    # osascript (Script Editor's icon).
    copy = app / "Contents" / "MacOS" / MAC_PYTHON
    if copy.exists():
        s.run(["codesign", "--force", "--sign", "-", "--identifier", BUNDLE_ID, str(copy)])
    s.run(["codesign", "--force", "--sign", "-", str(app)])
    s.run([LSREGISTER, "-f", str(app)])     # Launchpad and Spotlight know it at once, not after the next login
    s.made.append(str(app))


def _mac_remove(s: System) -> None:
    app = _mac_app(s)
    if _is_ours(app):
        s.run([LSREGISTER, "-u", str(app)])
        shutil.rmtree(app)
        s.made.append(str(app))
    _remove_named_python(s)


# --- Windows -------------------------------------------------------------------------------------------------------

def _win_icon(s: System) -> Path:
    return s.data / "launcher" / "smtv.ico"


def _ps(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def lnk_script(s: System, remove: bool = False) -> str:
    """PowerShell that makes (or deletes) SMTV.lnk on the desktop and in the Start menu, in the person's own folders
    (wherever Windows keeps them, OneDrive included)."""
    folders = "@([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))"
    if remove:   # only a shortcut SMTV made (it starts `-m smtv`): another program's SMTV.lnk stays
        return "\n".join([
            "$ErrorActionPreference = 'Stop'",
            "$w = New-Object -ComObject WScript.Shell",
            f"foreach ($d in {folders}) {{",
            f"  $p = Join-Path $d '{NAME}.lnk'",
            "  if (Test-Path -LiteralPath $p) {",
            "    $l = $w.CreateShortcut($p)",
            "    if ($l.Arguments -like '*-m smtv*') { Remove-Item -LiteralPath $p -Force }",
            "  }",
            "}",
        ])
    args = subprocess.list2cmdline(launch_args(s)[1:])
    return "\n".join([
        "$ErrorActionPreference = 'Stop'",
        "$w = New-Object -ComObject WScript.Shell",
        f"foreach ($d in {folders}) {{",
        f"  $l = $w.CreateShortcut((Join-Path $d '{NAME}.lnk'))",
        f"  $l.TargetPath = {_ps(s.python)}",
        f"  $l.Arguments = {_ps(args)}",
        "  $l.WorkingDirectory = $env:USERPROFILE",
        f"  $l.IconLocation = {_ps(str(_win_icon(s)) + ',0')}",
        f"  $l.Description = {_ps(NAME)}",
        "  $l.Save()",
        "}",
    ])


def powershell(script: str) -> list[str]:
    return ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
            "-EncodedCommand", base64.b64encode(script.encode("utf-16-le")).decode("ascii")]


def _win_install(s: System) -> None:
    icon = _win_icon(s)
    icon.parent.mkdir(parents=True, exist_ok=True)
    icon.write_bytes(ico((ICONS / "icon-256.png").read_bytes()))
    if s.run(powershell(lnk_script(s))) != 0:
        raise RuntimeError("could not make SMTV.lnk (PowerShell failed)")
    s.made.append("SMTV.lnk on the desktop and in the Start menu")


def _win_remove(s: System) -> None:
    if s.run(powershell(lnk_script(s, remove=True))) != 0:
        raise RuntimeError("could not remove SMTV.lnk (PowerShell failed)")
    _win_icon(s).unlink(missing_ok=True)
    s.made.append("SMTV.lnk")


# --- Linux ---------------------------------------------------------------------------------------------------------

_RESERVED = set(" \t\n\"'\\><~|&;$*?#()`")


def exec_arg(arg: str) -> str:
    """One argument of a .desktop Exec line (Desktop Entry spec: quoting, then the string escape of backslashes)."""
    arg = arg.replace("%", "%%")
    if arg and not (_RESERVED & set(arg)):
        return arg
    quoted = '"' + "".join("\\" + c if c in '"`$\\' else c for c in arg) + '"'
    return quoted.replace("\\", "\\\\")


def _xdg(s: System, var: str, default: str) -> Path:
    value = os.environ.get(var, "").strip()
    return Path(value) if value else s.home / default


def _linux_entry_path(s: System) -> Path:
    return _xdg(s, "XDG_DATA_HOME", ".local/share") / "applications" / f"{ENTRY}.desktop"


def _linux_icon(s: System) -> Path:
    return _xdg(s, "XDG_DATA_HOME", ".local/share") / "icons" / "hicolor" / "256x256" / "apps" / f"{ENTRY}.png"


def linux_entry(s: System, python: str | None = None) -> str:
    argv = launch_args(s, python)
    if s.env:
        argv = ["env", *(f"{k}={v}" for k, v in sorted(s.env.items())), *argv]
    lines = ["[Desktop Entry]", f"# {MARK}", "Type=Application", f"Name={NAME}", "Comment=Stream clips on this computer",
             "Exec=" + " ".join(exec_arg(a) for a in argv), f"Icon={_linux_icon(s)}", "Terminal=false",
             "StartupNotify=true", "StartupWMClass=SMTV", "Categories=AudioVideo;Video;"]
    return "\n".join(lines) + "\n"


def _linux_install(s: System) -> None:
    icon = _linux_icon(s)
    icon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ICONS / "icon-256.png", icon)
    entry = _linux_entry_path(s)
    entry.parent.mkdir(parents=True, exist_ok=True)
    named = named_python(s)
    python = named[0] if named else None
    entry.write_text(linux_entry(s, python=python), encoding="utf-8")
    entry.chmod(0o755)
    s.made.append(str(entry))
    s.run(["update-desktop-database", str(entry.parent)])
    if s.desktop:
        copy = s.desktop / entry.name
        copy.write_text(linux_entry(s, python=python), encoding="utf-8")
        copy.chmod(0o755)
        s.run(["gio", "set", str(copy), "metadata::trusted", "true"])   # GNOME: start on double-click without asking
        s.made.append(str(copy))


def _linux_remove(s: System) -> None:
    files = [_linux_entry_path(s), _linux_icon(s)] + ([s.desktop / f"{ENTRY}.desktop"] if s.desktop else [])
    for f in files:
        if f.exists() and (f.suffix != ".desktop" or MARK in f.read_text(encoding="utf-8", errors="replace")):
            f.unlink()
            s.made.append(str(f))
    s.run(["update-desktop-database", str(_linux_entry_path(s).parent)])
    _remove_named_python(s)


# --- the commands --------------------------------------------------------------------------------------------------

def _kind(s: System) -> str:
    if s.platform == "darwin":
        return "mac"
    if s.platform == "win32":
        return "win"
    if s.platform.startswith("linux") or "bsd" in s.platform:
        return "linux"
    raise RuntimeError(f"no shortcuts for {s.platform}: start the page with `smtv serve`")


def install(s: System) -> list[str]:
    {"mac": _mac_install, "win": _win_install, "linux": _linux_install}[_kind(s)](s)
    return s.made


def remove(s: System) -> list[str]:
    {"mac": _mac_remove, "win": _win_remove, "linux": _linux_remove}[_kind(s)](s)
    return s.made


def installed(s: System) -> bool:
    """Whether the SMTV icon is on this computer (made by `smtv shortcut`)."""
    try:
        kind = _kind(s)
    except RuntimeError:
        return False
    if kind == "mac":
        return _is_ours(_mac_app(s))
    if kind == "win":
        return _win_icon(s).exists()
    return _linux_entry_path(s).exists()
