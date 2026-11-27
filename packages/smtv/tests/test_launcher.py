"""`smtv shortcut` on all three systems, without touching this computer: files go to a temporary home, helper commands
are recorded instead of run."""
from __future__ import annotations

import os
import shlex
import plistlib
import struct
from pathlib import Path

import pytest

import sys

from smtv import launcher
from smtv.launcher import System

# macOS and Linux files are made with POSIX permission bits, symlinks and `/` paths: checked where those exist
not_on_windows = pytest.mark.skipif(sys.platform == "win32", reason="macOS/Linux launcher files need POSIX modes and symlinks")


def system(tmp_path: Path, platform: str, **kw) -> tuple[System, list[list[str]]]:
    calls: list[list[str]] = []

    def run(argv):
        calls.append(argv)
        return 0

    home = tmp_path / "home folder"     # a space on purpose: paths are quoted everywhere
    home.mkdir(exist_ok=True)
    python = {"win32": r"C:\Users\someone\.local\share\uv\tools\smtv\Scripts\pythonw.exe"}.get(platform, "/opt/smtv venv/bin/python")
    env = {} if platform == "win32" else {"PATH": "/opt/homebrew/bin:/usr/bin:/bin"}
    s = System(platform, home, python, env, tmp_path / "smtv data", run=run, **kw)
    return s, calls


@pytest.fixture(autouse=True)
def no_xdg(monkeypatch):
    for var in ("XDG_DATA_HOME", "XDG_CONFIG_HOME"):
        monkeypatch.delenv(var, raising=False)


# --- macOS -----------------------------------------------------------------------------------------------------------

@not_on_windows
def test_mac_app_is_smtv_itself(tmp_path):
    s, calls = system(tmp_path, "darwin")
    s.env["SMTV_HOME"] = "/data/smtv home"
    launcher.install(s)
    app = s.home / "Applications" / "SMTV.app"
    info = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
    assert info["CFBundleIdentifier"] == launcher.BUNDLE_ID and info["CFBundleExecutable"] == "SMTV"
    assert "LSUIElement" not in info                       # a real app: in the Dock while its window is open
    assert "CFBundleURLTypes" not in info                  # no smtv:// link any more
    script = app / "Contents" / "MacOS" / info["CFBundleExecutable"]
    assert script.stat().st_mode & 0o111
    text = script.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/sh\n")
    assert "export PATH=/opt/homebrew/bin:/usr/bin:/bin" in text
    assert "export SMTV_HOME='/data/smtv home'" in text
    # exec: the process macOS started for SMTV.app becomes SMTV (a second click brings its window forward)
    assert "exec '/opt/smtv venv/bin/python' -m smtv app </dev/null >/dev/null 2>&1" in text
    assert "$@" not in text and "$1" not in text           # arguments are never passed on
    icon = (app / "Contents" / "Resources" / "smtv.icns").read_bytes()
    assert icon[:4] == b"icns" and struct.unpack(">I", icon[4:8])[0] == len(icon)
    assert icon[8:12] == b"ic09" and b"ic10" in icon
    # signed locally (ad-hoc), so macOS lets SMTV send notifications under its own name and icon
    assert calls == [["codesign", "--force", "--sign", "-", str(app)], [launcher.LSREGISTER, "-f", str(app)]]
    assert launcher.installed(s)


def test_mac_never_replaces_an_app_it_did_not_make(tmp_path):
    s, _ = system(tmp_path, "darwin")
    other = s.home / "Applications" / "SMTV.app" / "Contents"
    other.mkdir(parents=True)
    (other / "Info.plist").write_bytes(plistlib.dumps({"CFBundleIdentifier": "com.example.other"}))
    with pytest.raises(FileExistsError):
        launcher.install(s)
    assert not launcher.installed(s)
    launcher.remove(s)
    assert (other / "Info.plist").exists()


def test_mac_remove_unregisters_and_deletes(tmp_path):
    s, calls = system(tmp_path, "darwin")
    launcher.install(s)
    launcher.install(s)        # again: replaces its own app
    calls.clear()
    launcher.remove(s)
    assert not (s.home / "Applications" / "SMTV.app").exists()
    assert calls == [[launcher.LSREGISTER, "-u", str(s.home / "Applications" / "SMTV.app")]]


# --- Windows ---------------------------------------------------------------------------------------------------------

class FakeLinks:
    """winlink without Windows: shortcuts are files holding what was saved."""

    def __init__(self, root: Path):
        self.root, self.saved = root, []
        for name in ("Desktop", "Programs"):
            (root / name).mkdir(parents=True, exist_ok=True)

    def folders(self):
        return [str(self.root / "Desktop"), str(self.root / "Programs")]

    def save(self, path, target, arguments, workdir, icon, app_id, description):
        self.saved.append({"path": path, "target": target, "arguments": arguments, "workdir": workdir, "icon": icon,
                           "app_id": app_id, "description": description})
        Path(path).write_text(arguments, encoding="utf-8")

    def arguments(self, path):
        return Path(path).read_text(encoding="utf-8")


def win_system(tmp_path):
    s, calls = system(tmp_path, "win32")
    s.win = FakeLinks(tmp_path / "shell")
    return s, calls


def test_windows_makes_clip_it_lnk_on_desktop_and_start_menu_with_pythonw_and_the_taskbar_id(tmp_path):
    s, calls = win_system(tmp_path)
    # 0.1.0 made «SMTV» shortcuts: ours go, another program's of that name stays
    (s.win.root / "Desktop" / "SMTV.lnk").write_text("-m smtv app", encoding="utf-8")
    (s.win.root / "Programs" / "SMTV.lnk").write_text("--another-program", encoding="utf-8")
    launcher.install(s)
    assert calls == []                                    # no PowerShell: Smart App Control restricts it
    assert [Path(x["path"]).parent.name for x in s.win.saved] == ["Desktop", "Programs"]
    for x in s.win.saved:
        assert Path(x["path"]).name == "Clip It!.lnk" and x["description"] == "Clip It!"
        assert x["target"] == r"C:\Users\someone\.local\share\uv\tools\smtv\Scripts\pythonw.exe"
        assert x["arguments"] == "-m smtv app" and x["workdir"] == str(s.home)
        assert x["icon"] == str(s.data / "launcher" / "smtv.ico") and x["app_id"] == launcher.APP_ID == "ClipIt.ClipIt"
    assert not (s.win.root / "Desktop" / "SMTV.lnk").exists() and (s.win.root / "Programs" / "SMTV.lnk").exists()


def test_windows_failed_lnk_is_reported(tmp_path):
    s, _ = win_system(tmp_path)

    def refuse(*a):
        raise OSError("[WinError -2147024891] Access is denied")
    s.win.save = refuse
    with pytest.raises(RuntimeError, match="Clip It!.lnk.*Access is denied"):
        launcher.install(s)
    s.win.folders = lambda: ["", ""]
    with pytest.raises(RuntimeError, match="no desktop or Start menu folder"):
        launcher.install(s)


def test_windows_remove_takes_the_new_and_the_old_shortcuts_but_not_another_program_s(tmp_path):
    s, _ = win_system(tmp_path)
    launcher.install(s)
    icon = (s.data / "launcher" / "smtv.ico").read_bytes()
    assert launcher.installed(s) and icon[:4] == b"\x00\x00\x01\x00" and struct.unpack("<H", icon[4:6])[0] == 6
    (s.win.root / "Desktop" / "SMTV.lnk").write_text("-m smtv app", encoding="utf-8")          # left by 0.1.0
    (s.win.root / "Programs" / "Clip It!.lnk").write_text("--another-program", encoding="utf-8")
    launcher.remove(s)
    assert not (s.win.root / "Desktop" / "Clip It!.lnk").exists() and not (s.win.root / "Desktop" / "SMTV.lnk").exists()
    assert (s.win.root / "Programs" / "Clip It!.lnk").exists()
    assert not (s.data / "launcher" / "smtv.ico").exists() and not launcher.installed(s)

    def refuse(path):
        raise OSError("in use")
    (s.win.root / "Desktop" / "Clip It!.lnk").write_text("-m smtv app", encoding="utf-8")
    s.win.arguments = refuse
    with pytest.raises(RuntimeError, match="could not remove Clip It!.lnk"):
        launcher.remove(s)


def test_the_windows_icon_has_every_size_windows_asks_for():
    data = launcher.win_ico()
    count = struct.unpack("<HHH", data[:6])[2]
    entries = [struct.unpack("<BBBBHHII", data[6 + 16 * i:22 + 16 * i]) for i in range(count)]
    assert [e[0] or 256 for e in entries] == [16, 24, 32, 48, 64, 256]
    for (side, _, _, _, _, _, size, offset), want in zip(entries, (16, 24, 32, 48, 64, 256)):
        png = data[offset:offset + size]
        assert png[:8] == b"\x89PNG\r\n\x1a\n" and struct.unpack(">II", png[16:24]) == (want, want)
    assert data[entries[-1][7]:] == (launcher.ICONS / "icon-256.png").read_bytes()


def test_the_window_icon_is_the_app_s_own_else_one_made_in_smtv_s_folder(tmp_path):
    app = tmp_path / "SMTV"
    app.mkdir()
    (app / "smtv.ico").write_bytes(b"ico")
    assert launcher.window_icon(app, tmp_path / "data") == app / "smtv.ico"
    made = launcher.window_icon(tmp_path / "venv", tmp_path / "data")
    assert made == tmp_path / "data" / "launcher" / "window.ico" and made.read_bytes() == launcher.win_ico()
    assert not (tmp_path / "data" / "launcher" / "smtv.ico").exists()     # that one says the shortcut is made
    (tmp_path / "ro").write_text("a file, not a folder", encoding="utf-8")
    assert launcher.window_icon(tmp_path / "venv", tmp_path / "ro") is None


@pytest.mark.parametrize(("kind", "own"), [("uv", True), ("pip", True), ("zip", False), ("exe", False), ("dmg", False)])
def test_smtv_makes_its_own_icon_only_for_uv_and_pip(kind, own):
    # the Windows ZIP is portable: no shortcut, nothing outside its folder
    assert launcher.own_shortcut(kind) is own


# --- Linux -----------------------------------------------------------------------------------------------------------

def test_exec_arguments_follow_the_desktop_entry_spec():
    assert launcher.exec_arg("/usr/bin/python3") == "/usr/bin/python3"
    assert launcher.exec_arg("/opt/smtv venv/bin/python") == '"/opt/smtv venv/bin/python"'
    assert launcher.exec_arg("PATH=/a$b") == '"PATH=/a\\\\$b"'          # $ escaped, then the backslash escaped again
    assert launcher.exec_arg("50%") == "50%%"
    assert launcher.exec_arg('a"b') == '"a\\\\"b"'


@not_on_windows
def test_linux_menu_entry_and_desktop_icon(tmp_path):
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    s, calls = system(tmp_path, "linux", desktop=desktop)
    launcher.install(s)
    entry = s.home / ".local/share/applications/smtv.desktop"
    text = entry.read_text(encoding="utf-8")
    link = s.data / "launcher" / "SMTV"                    # not a venv here: the link lives in SMTV's own folder
    assert os.readlink(link) == "/opt/smtv venv/bin/python"
    assert f"Exec=env PATH=/opt/homebrew/bin:/usr/bin:/bin \"{link}\" -m smtv app\n" in text
    assert "Terminal=false" in text and "MimeType" not in text and "%u" not in text
    assert (s.home / ".local/share/icons/hicolor/256x256/apps/smtv.png").read_bytes()[:4] == b"\x89PNG"
    assert (desktop / "smtv.desktop").read_text(encoding="utf-8") == text and (desktop / "smtv.desktop").stat().st_mode & 0o111
    assert not any(c[0] == "xdg-mime" for c in calls)
    assert ["gio", "set", str(desktop / "smtv.desktop"), "metadata::trusted", "true"] in calls
    assert launcher.installed(s)


def test_linux_remove_only_its_own_files(tmp_path):
    desktop = tmp_path / "Desktop"
    desktop.mkdir()
    s, _ = system(tmp_path, "linux", desktop=desktop)
    launcher.install(s)
    (desktop / "smtv.desktop").write_text("[Desktop Entry]\nName=someone else's\n", encoding="utf-8")      # not ours any more
    launcher.remove(s)
    assert not (s.home / ".local/share/applications/smtv.desktop").exists()
    assert (desktop / "smtv.desktop").exists()
    assert not launcher.installed(s)


def test_unknown_system_says_what_to_do(tmp_path):
    s, _ = system(tmp_path, "aix")
    with pytest.raises(RuntimeError, match="smtv serve"):
        launcher.install(s)
    assert not launcher.installed(s)


def test_this_system_uses_pythonw_on_windows(tmp_path, monkeypatch):
    scripts = tmp_path / "Scripts"
    scripts.mkdir()
    (scripts / "python.exe").write_text("", encoding="utf-8")
    (scripts / "pythonw.exe").write_text("", encoding="utf-8")
    monkeypatch.setattr(launcher.sys, "platform", "win32")
    monkeypatch.setattr(launcher.sys, "executable", str(scripts / "python.exe"))
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "h"))
    s = launcher.this_system()
    assert s.python == str(scripts / "pythonw.exe") and "PATH" not in s.env
    assert s.env["SMTV_HOME"] == str((tmp_path / "h").resolve())
    (scripts / "SMTV.exe").write_text("", encoding="utf-8")      # the desktop app: its own SMTV.exe
    assert launcher.this_system().python == str(scripts / "SMTV.exe")


# --- the process name ------------------------------------------------------------------------------------------------

def framework_venv(tmp_path):
    """A venv on a macOS framework build (Homebrew): venv/bin/python3.14 -> opt/python/bin/python3.14, where the
    small bin/python3.14 runs Resources/Python.app/Contents/MacOS/Python."""
    version = tmp_path / "Cellar/Python.framework/Versions/3.14"
    (version / "bin").mkdir(parents=True)
    (version / "bin/python3.14").write_text("stub", encoding="utf-8")
    inner = version / "Resources/Python.app/Contents/MacOS"
    inner.mkdir(parents=True)
    (inner / "Python").write_text("python", encoding="utf-8")
    (tmp_path / "opt").mkdir()
    os.symlink(version, tmp_path / "opt/python")
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("home = x\n", encoding="utf-8")
    os.symlink(tmp_path / "opt/python/bin/python3.14", venv / "bin/python3.14")
    return venv


@not_on_windows
def test_mac_framework_python_runs_as_smtv_app_with_its_icon(tmp_path):
    venv = framework_venv(tmp_path)
    s, calls = system(tmp_path, "darwin")
    s.python = str(venv / "bin/python3.14")
    launcher.install(s)
    macos = s.home / "Applications/SMTV.app/Contents/MacOS"
    copy = macos / "smtv-python"                           # inside SMTV.app: macOS counts the process as SMTV's
    assert copy.read_text(encoding="utf-8") == "python" and not copy.is_symlink()
    assert ["codesign", "--force", "--sign", "-", "--identifier", launcher.BUNDLE_ID, str(copy)] in calls
    assert not (venv / "SMTV").exists()
    text = (macos / "SMTV").read_text(encoding="utf-8")
    assert f"export __PYVENV_LAUNCHER__={s.python}" in text
    q = shlex.quote(str(copy))
    assert f"if {q} -c '' >/dev/null 2>&1; then" in text   # tried first: the copy is tied to the Python version
    assert f"  exec {q} -m smtv app </dev/null" in text
    assert f"fi\nexec {s.python} -m smtv app </dev/null" in text      # a stale copy still starts SMTV
    launcher.remove(s)
    assert not macos.exists()


@not_on_windows
def test_framework_inner_program_is_found_by_a_path_that_survives_upgrades(tmp_path):
    venv = framework_venv(tmp_path)
    inner = launcher._framework_app_python(str(venv / "bin/python3.14"))
    assert inner == str(tmp_path / "opt/python/bin/../Resources/Python.app/Contents/MacOS/Python")
    assert launcher._framework_app_python(str(tmp_path / "nothing")) is None


@not_on_windows
def test_other_pythons_get_the_link_without_the_launcher_variable(tmp_path):
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "pyvenv.cfg").write_text("home = x\n", encoding="utf-8")
    (venv / "bin/python3").write_text("python", encoding="utf-8")
    s, _ = system(tmp_path, "darwin")
    s.python = str(venv / "bin/python3")
    assert launcher.named_python(s) == (str(venv / "SMTV"), {})
    assert os.readlink(venv / "SMTV") == s.python
    assert launcher.named_python(s)[0] == str(venv / "SMTV")      # again: replaced, not an error


def test_the_name_link_never_replaces_a_real_file(tmp_path):
    s, _ = system(tmp_path, "linux")
    place = s.data / "launcher" / "SMTV"
    place.parent.mkdir(parents=True)
    place.write_text("someone's file", encoding="utf-8")
    assert launcher.named_python(s) is None
    launcher.install(s)
    assert place.read_text(encoding="utf-8") == "someone's file"
    assert '"/opt/smtv venv/bin/python" -m smtv app' in (s.home / ".local/share/applications/smtv.desktop").read_text(encoding="utf-8")


def test_the_windows_zip_hides_only_what_a_person_never_opens(tmp_path):
    for name in ("SMTV.exe", "SMTV.exe.config", "python312.dll", "vcruntime140.dll", "python312._pth", "how.txt"):
        (tmp_path / name).write_bytes(b"x")
    (tmp_path / "app").mkdir()
    hidden = []

    def hide(path):
        if path.endswith("vcruntime140.dll"):
            raise OSError("in use")                      # a file it cannot mark stays as it is
        hidden.append(Path(path).name)
    assert launcher.hide_parts(tmp_path, hide) == ["python312._pth", "python312.dll"] == hidden


def test_the_mac_app_keeps_its_file_name_and_shows_clip_it(tmp_path):
    # SMTV.app stays SMTV.app (updates, the Dock's place, an older copy replaced in place); Finder, the Dock and the
    # menu show «Clip It!»: the localized display name, which Finder takes only when the plain one matches the file
    s = System("darwin", tmp_path, "/py", {}, tmp_path / "data")
    info = launcher.mac_info(s)
    assert launcher._mac_app(s).name == "SMTV.app"
    assert info["CFBundleName"] == "Clip It!" and info["CFBundleDisplayName"] == "SMTV" and info["LSHasLocalizedDisplayName"]
    launcher.mac_names(tmp_path / "Resources")
    for lang in ("en", "ru", "Base"):
        text = (tmp_path / "Resources" / f"{lang}.lproj" / "InfoPlist.strings").read_text(encoding="utf-8")
        assert '"CFBundleDisplayName" = "Clip It!";' in text and '"CFBundleName" = "Clip It!";' in text


def test_every_icon_is_made_from_the_clip_it_drawings_and_holds_only_its_image():
    import sys as _sys
    _sys.path.insert(0, str(launcher.ICONS.parents[5] / "scripts"))
    try:
        import make_icons
    finally:
        _sys.path.pop(0)
    assert make_icons.ICONS == launcher.ICONS
    assert set(make_icons.SMALL + make_icons.FULL) == set(launcher.WIN_ICON_SIZES)
    for name, size in [(f"icon-{n}.png", n) for n in launcher.WIN_ICON_SIZES] + [(f"icon-mac-{n}.png", n) for n in make_icons.MAC]:
        data = (launcher.ICONS / name).read_bytes()
        assert struct.unpack(">II", data[16:24]) == (size, size), name
        assert make_icons.plain_png(data) == data, name            # no EXIF or other chunks from the drawing tool
    for svg in ("clip-it.svg", "clip-it-small.svg", "clip-it-mac.svg"):
        text = (launcher.ICONS / svg).read_text(encoding="utf-8")
        assert "<path" in text and "<text" not in text and "font-family" not in text, svg   # outlines: no font ships
    assert not list(launcher.ICONS.glob("*sm*tv*")) and "Bitter" in (launcher.ICONS / "README.md").read_text(encoding="utf-8")
