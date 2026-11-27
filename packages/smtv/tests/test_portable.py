"""The Windows ZIP is portable (0.1.1): its data, clips, temporary files and caches stay in its folder; its update
replaces only the program; 0.1.0's settings are offered once; a folder it cannot write into is said plainly."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from smtv import i18n, portable, uninstall, zipupdate
from smtv_core import paths


def zip_folder(top: Path, kind: str = "zip") -> Path:
    (top / "app" / "Lib" / "site-packages").mkdir(parents=True)
    (top / "app" / paths.KIND_MARKER).write_text(kind + "\n", encoding="utf-8")
    (top / "ClipIt.exe").write_bytes(b"MZ")
    (top / "python312.dll").write_bytes(b"MZ dll")
    return top


@pytest.fixture(autouse=True)
def restored():
    """apply_portable writes os.environ, sys.path and tempfile's folder itself: every test gets them back as they were."""
    import tempfile
    env, path = dict(os.environ), list(sys.path)
    yield
    os.environ.clear()
    os.environ.update(env)
    sys.path[:] = path
    tempfile.tempdir = None


@pytest.fixture
def clean_env(monkeypatch):
    for key in ("SMTV_HOME", "SMTV_OUTER_TEMP", "HF_HOME", "PIP_CACHE_DIR", "WEBVIEW2_USER_DATA_FOLDER"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("TEMP", "/the/system/temp")
    monkeypatch.setenv("TMP", "/the/system/temp")
    monkeypatch.setenv("TMPDIR", os.environ.get("TMPDIR", "/tmp"))


# --- where the data goes, by kind of install ----------------------------------------------------------------------

@pytest.mark.parametrize(("platform", "kind", "portable_"), [
    ("win32", "zip", True), ("win32", "exe", False), ("darwin", "zip", False), ("win32", None, False)])
def test_only_the_windows_zip_is_portable(tmp_path, platform, kind, portable_):
    if kind:
        zip_folder(tmp_path, kind)
    assert (paths.portable_top(str(tmp_path), platform) == tmp_path) is portable_


def test_the_zip_keeps_its_data_and_clips_beside_clipit_exe(tmp_path, monkeypatch, clean_env):
    top = zip_folder(tmp_path / "ClipIt")
    monkeypatch.setattr(paths, "portable_top", lambda prefix=None, platform=None: top)
    assert paths.home() == top / "data" and paths.data_dir() == top / "Clips"
    assert paths.models_dir() == top / "data" / "models" and paths.secrets_key_file() == top / "data" / "secrets.key"
    assert paths.apply_portable() == top
    for key in ("SMTV_HOME", "TEMP", "TMP", "TMPDIR", "HF_HOME", "PIP_CACHE_DIR", "WEBVIEW2_USER_DATA_FOLDER"):
        assert Path(os.environ[key]).is_relative_to(top / "data"), key
    assert os.environ["SMTV_OUTER_TEMP"] == "/the/system/temp"       # kept for removing the folder itself
    assert (top / "data" / "tmp").is_dir()
    import tempfile
    assert Path(tempfile.gettempdir()).is_relative_to(top)


def test_a_persons_own_smtv_home_still_wins(tmp_path, monkeypatch, clean_env):
    top = zip_folder(tmp_path / "ClipIt")
    monkeypatch.setattr(paths, "portable_top", lambda prefix=None, platform=None: top)
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "mine"))
    paths.apply_portable()
    assert paths.home() == tmp_path / "mine" and paths.data_dir() == tmp_path / "mine" / "data"
    for key in ("TEMP", "TMP", "TMPDIR", "HF_HOME", "PIP_CACHE_DIR", "WEBVIEW2_USER_DATA_FOLDER"):
        assert Path(os.environ[key]).is_relative_to(tmp_path / "mine"), key
    assert not (top / "data").exists()                         # smoke.py sets SMTV_HOME: the top stays as built


def test_every_other_install_keeps_the_standard_places(monkeypatch, clean_env):
    monkeypatch.setattr(paths, "portable_top", lambda prefix=None, platform=None: None)
    assert paths.apply_portable() is None and "HF_HOME" not in os.environ
    assert paths.home() == paths.standard_home() and paths.data_dir() == paths.home() / "data"


def test_nothing_lands_outside_the_folder_when_the_checks_run(tmp_path):
    # the person's home, %APPDATA%, %LOCALAPPDATA% and %TEMP% are a sentinel folder: it must stay empty
    top = zip_folder(tmp_path / "ClipIt")
    sentinel = tmp_path / "outside"
    sentinel.mkdir()
    code = (f"import sys; from pathlib import Path; from smtv_core import paths; top = Path({str(top)!r});"
            "paths.portable_top = lambda prefix=None, platform=None: top; paths.apply_portable();"
            "from smtv.cli import main; sys.argv = ['smtv', 'doctor']; main()")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("SMTV_", "HF_", "XDG_"))}
    env.update({"HOME": str(sentinel), "USERPROFILE": str(sentinel), "APPDATA": str(sentinel / "Roaming"),
                "LOCALAPPDATA": str(sentinel / "Local"), "TEMP": str(sentinel / "Temp"), "TMP": str(sentinel / "Temp"),
                "TMPDIR": str(sentinel / "Temp"), "SMTV_NO_SHORTCUT": "1"})
    subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=300, cwd=tmp_path)
    assert list(sentinel.rglob("*")) == []
    assert (top / "data").is_dir()


# --- a folder it cannot write into --------------------------------------------------------------------------------

def test_a_folder_that_cannot_be_written_is_said_plainly_and_no_window_opens(tmp_path, monkeypatch):
    top = zip_folder(tmp_path / "ClipIt")
    monkeypatch.setattr(paths, "portable_problem", lambda t: "PermissionError: [WinError 5] Access is denied")
    said = []
    assert portable.start("ru", top, ask=lambda t: pytest.fail("asked"), say=said.append, hide=lambda p: None) is False
    (text,) = said
    assert str(top) in text and "Документы" in text and "Program Files" in text and "Access is denied" in text
    assert "Documents" in i18n.text("portable_readonly", "en", folder="x", error="e")
    assert not (top / "data").exists()                         # nothing quietly put into %APPDATA% either


def test_a_writable_folder_is_checked_for_real(tmp_path):
    top = zip_folder(tmp_path / "ClipIt")
    assert paths.portable_problem(top) is None and (top / "Clips").is_dir() and (top / "data").is_dir()


def test_the_start_hides_what_a_person_never_opens_but_not_the_clips(tmp_path, monkeypatch):
    top = zip_folder(tmp_path / "ClipIt")
    (top / "data" / "run" / "update-old").mkdir(parents=True)        # an update in place may still need it
    hidden = []
    assert portable.start("en", top, ask=lambda t: False, say=pytest.fail, hide=hidden.append)
    assert sorted(Path(h).name for h in hidden) == ["data", "python312.dll"]
    assert (top / "data" / "run" / "update-old").exists()             # only settle, under the lock, removes it


# --- 0.1.0's settings, offered once -------------------------------------------------------------------------------

def old_install(tmp_path) -> tuple[Path, Path]:
    old = tmp_path / "Roaming" / "smtv"
    (old / "models" / "gigaam").mkdir(parents=True)
    (old / "models" / "gigaam" / "model.onnx").write_bytes(b"x" * 1000)
    (old / "settings.json").write_text('{"providers": []}', encoding="utf-8")
    (old / "secrets.json").write_text("{}", encoding="utf-8")
    key = tmp_path / "Local" / "smtv" / "secrets.key"
    key.parent.mkdir(parents=True)
    key.write_bytes(b"k" * 32)
    return old, key


def test_0_1_0_s_settings_and_keys_are_offered_once_and_copied_not_moved(tmp_path):
    top = zip_folder(tmp_path / "ClipIt")
    old, key = old_install(tmp_path)
    asked = []
    answer = portable.offer_migration(top, "ru", lambda t: asked.append(t) or True, old, key)
    assert answer == "copied" and len(asked) == 1 and str(old) in asked[0] and "ГБ" in asked[0]
    data = top / "data"
    assert {f.name for f in data.iterdir()} >= {"settings.json", "secrets.json", "secrets.key"}
    assert (old / "settings.json").exists() and key.exists()             # a copy: the old ones stay
    assert not (data / "models").exists()                               # models download again
    (data / "settings.json").unlink()
    assert portable.offer_migration(top, "ru", lambda t: pytest.fail("asked twice"), old, key) is None


def test_a_no_is_remembered_and_a_folder_with_settings_is_never_asked(tmp_path):
    top = zip_folder(tmp_path / "ClipIt")
    old, key = old_install(tmp_path)
    assert portable.offer_migration(top, "en", lambda t: False, old, key) == "declined"
    assert not (top / "data" / "settings.json").exists()
    assert json.loads((top / "data" / "run" / portable.MIGRATION_MARK).read_text(encoding="utf-8"))["answer"] == "declined"
    other = zip_folder(tmp_path / "Other")
    (other / "data").mkdir()
    (other / "data" / "settings.json").write_text("{}", encoding="utf-8")
    assert portable.offer_migration(other, "en", lambda t: pytest.fail("asked"), old, key) is None
    assert portable.offer_migration(zip_folder(tmp_path / "Fresh"), "en", pytest.fail, tmp_path / "none", key) is None


# --- the update in place ------------------------------------------------------------------------------------------

def release_zip(tmp_path, version: str) -> Path:
    archive = tmp_path / f"SMTV-{version}-windows-x64.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("ClipIt/ClipIt.exe", f"MZ {version}")
        z.writestr("ClipIt/ClipIt.exe.config", f"<config {version}/>")
        z.writestr("ClipIt/app/Lib/site-packages/smtv/__init__.py", f"__version__ = {version!r}\n")
        z.writestr("ClipIt/python312.dll", f"MZ dll {version}")
        z.writestr("ClipIt/python312._pth", "app\r\nimport site\r\n")
        z.writestr("ClipIt/How to start Clip It!.txt", version)
        z.writestr("ClipIt/data/should-not-land.txt", "x")
    return archive


def installed(tmp_path) -> Path:
    """A ZIP copy in use: the program, its data and clips, and a file of the person's own."""
    top = zip_folder(tmp_path / "ClipIt")
    (top / "app" / "Lib" / "site-packages" / "gone_in_new.py").write_text("old", encoding="utf-8")
    (top / "ClipIt.exe.config").write_text("<config old/>", encoding="utf-8")
    (top / "python312._pth").write_text("app\r\nimport site\r\n", encoding="utf-8")
    (top / "How to start Clip It!.txt").write_text("old", encoding="utf-8")
    (top / "data").mkdir()
    (top / "data" / "settings.json").write_text('{"mine": 1}', encoding="utf-8")
    (top / "Clips" / "job").mkdir(parents=True)
    (top / "Clips" / "job" / "clip01.mp4").write_bytes(b"clip")
    (top / "my notes.docx").write_bytes(b"mine")
    return top


def snapshot(top: Path) -> dict:
    return {str(f.relative_to(top)): f.read_bytes() for f in sorted(top.rglob("*"))
            if f.is_file() and not f.relative_to(top).parts[0] == "data"}


def staged(tmp_path, top: Path) -> Path:
    zipupdate.start(release_zip(tmp_path, "0.1.2"), top, 4242, spawn=lambda argv: 999)
    return top / "data" / "run" / zipupdate.STAGING / "ClipIt"


def test_an_update_replaces_only_the_program_and_never_touches_data_clips_or_a_persons_file(tmp_path):
    top = installed(tmp_path)
    started = []
    argv = zipupdate.start(release_zip(tmp_path, "0.1.2"), top, 4242, spawn=lambda argv: started.append(argv) or 777)
    new = top / "data" / "run" / zipupdate.STAGING / "ClipIt"
    assert argv[0] == str(new / "ClipIt.exe") and argv[1:4] == ["-m", "smtv.zipupdate", "swap"] and "4242" in argv
    assert zipupdate.read_state(top) == {"state": "staged", "pid": 777}
    zipupdate.swap(new, top, alive=lambda: False, start_new=started.append)
    assert (top / "ClipIt.exe").read_bytes() == b"MZ 0.1.2" and (top / "python312.dll").read_bytes() == b"MZ dll 0.1.2"
    assert not (top / "app" / "Lib" / "site-packages" / "gone_in_new.py").exists()    # no stale file of the old one
    assert (top / "data" / "settings.json").read_text(encoding="utf-8") == '{"mine": 1}'
    assert (top / "Clips" / "job" / "clip01.mp4").read_bytes() == b"clip"
    assert (top / "my notes.docx").read_bytes() == b"mine"
    assert not (top / "data" / "should-not-land.txt").exists()
    assert started[-1] == [str(top / "ClipIt.exe"), "-m", "smtv", "app"]
    assert zipupdate.read_state(top)["state"] == "swapped"
    assert (top / "data" / "run" / zipupdate.OLD / "ClipIt.exe").read_bytes() == b"MZ"     # kept until the new one ran


def failing_at(monkeypatch, what: str, n: int):
    """The n-th move (Path.replace) or copy (copy2/copytree) of the swap fails, as a file held by another program."""
    count = {"n": 0}
    if what == "move":
        real = Path.replace

        def replace(self, target):
            if "update-old" in str(target) and not str(self).startswith(str(target)):
                count["n"] += 1
                if count["n"] == n:
                    raise PermissionError(13, "The process cannot access the file", str(self))
            return real(self, target)
        monkeypatch.setattr(Path, "replace", replace)
    else:
        real_file, real_tree = zipupdate.shutil.copy2, zipupdate.shutil.copytree

        def once(real):
            def copy(src, dst, *a, **k):
                count["n"] += 1
                if count["n"] == n:
                    if real is real_tree:              # half a folder made, then the failure
                        Path(dst).mkdir(parents=True)
                        (Path(dst) / "half.py").write_text("x", encoding="utf-8")
                    raise OSError(28, "No space left on device")
                return real(src, dst, *a, **k)
            return copy
        monkeypatch.setattr(zipupdate.shutil, "copy2", once(real_file))
        monkeypatch.setattr(zipupdate.shutil, "copytree", once(real_tree))


@pytest.mark.parametrize(("what", "n"), [("move", 1), ("move", 2), ("move", 4), ("move", 6),
                                         ("copy", 1), ("copy", 2), ("copy", 4), ("copy", 5)])
def test_a_failure_at_any_step_leaves_the_old_program_whole(tmp_path, monkeypatch, what, n):
    # review #1: a file held open at the 2nd move must not cost the old app\, its DLLs or its ._pth
    top = installed(tmp_path)
    before = snapshot(top)
    new = staged(tmp_path, top)
    failing_at(monkeypatch, what, n)
    with pytest.raises(OSError):
        zipupdate.swap(new, top, alive=lambda: False, start_new=pytest.fail)
    monkeypatch.undo()
    assert snapshot(top) == before
    assert zipupdate.read_state(top)["state"] == "failed"
    assert not any((top / "data" / "run" / zipupdate.OLD).iterdir())    # everything moved back


def test_a_rollback_that_fails_keeps_the_old_program_and_restore_brings_it_back(tmp_path, monkeypatch):
    top = installed(tmp_path)
    before = snapshot(top)
    new = staged(tmp_path, top)
    real = Path.replace
    calls = {"n": 0}

    def replace(self, target):
        calls["n"] += 1
        if calls["n"] == 3 or (calls["n"] > 3 and "update-old" in str(self)):   # the 3rd move fails, and so does going back
            raise PermissionError(13, "held", str(self))
        return real(self, target)
    monkeypatch.setattr(Path, "replace", replace)
    with pytest.raises(PermissionError):
        zipupdate.swap(new, top, alive=lambda: False, start_new=pytest.fail)
    monkeypatch.undo()
    assert zipupdate.read_state(top)["state"] == "rollback_failed"
    assert zipupdate.settle(top, alive=lambda pid: False) == "rollback_failed"   # update-old holds the only copy: kept
    assert any((top / "data" / "run" / zipupdate.OLD).iterdir())
    zipupdate.restore(top)
    assert snapshot(top) == before


def test_the_old_program_goes_only_after_the_new_one_started_and_never_during_a_swap(tmp_path):
    # review #3 and #11: a double click during the swap removes nothing; the old copy stays until the new one ran
    top = installed(tmp_path)
    new = staged(tmp_path, top)
    assert zipupdate.settle(top, alive=lambda pid: pid == 999) == "staged"   # the swapper is alive: touch nothing
    assert new.is_dir()
    zipupdate.swap(new, top, alive=lambda: False, start_new=lambda argv: None)
    old = top / "data" / "run" / zipupdate.OLD
    zipupdate.write_state(top, state="swapping", pid=1234)
    assert zipupdate.settle(top, alive=lambda pid: pid == 1234) == "swapping" and old.is_dir() and new.is_dir()
    zipupdate.write_state(top, state="swapped")
    with pytest.raises(RuntimeError, match="not settled"):         # no second update over an unconfirmed one
        zipupdate.start(release_zip(tmp_path, "0.1.3"), top, 1, spawn=lambda argv: 1)
    assert zipupdate.settle(top, alive=lambda pid: False) == "confirmed"    # the new program runs: now they go
    assert not old.exists() and not (top / "data" / "run" / zipupdate.STAGING).exists()


def test_the_window_settles_an_update_only_once_it_runs(tmp_path, monkeypatch):
    top = installed(tmp_path)
    staged(tmp_path, top)
    seen = []
    monkeypatch.setattr(zipupdate, "settle", lambda t, alive: seen.append(t) or "staged")
    assert portable.start("en", top, ask=lambda t: False, say=pytest.fail, hide=lambda p: None)
    assert seen == []                                                 # the start (before the lock) settles nothing
    assert portable.settle(top) == "staged" and seen == [top]
    src = Path(portable.__file__).with_name("desktop.py").read_text(encoding="utf-8")
    assert src.index("lock.update(port=app.port)") < src.index("portable.settle()")   # under the instance lock


def test_an_update_waits_for_the_old_program_and_a_zip_of_something_else_is_refused(tmp_path):
    top = zip_folder(tmp_path / "ClipIt")
    with pytest.raises(TimeoutError):
        zipupdate.swap(top, top, alive=lambda: True, wait_s=0.1, start_new=pytest.fail)
    evil = tmp_path / "evil.zip"
    with zipfile.ZipFile(evil, "w") as z:
        z.writestr("../outside.txt", "x")
    with pytest.raises(ValueError, match="outside"):
        zipupdate.unpack(evil, tmp_path / "staging")
    other = tmp_path / "other.zip"
    with zipfile.ZipFile(other, "w") as z:
        z.writestr("Something/readme.txt", "x")
    with pytest.raises(ValueError, match="not this program"):
        zipupdate.unpack(other, tmp_path / "staging")


def test_the_zip_looks_for_updates_every_day_like_the_other_apps(monkeypatch):
    # review #5: the daily check ran only for the kinds in the list of releases; the ZIP is listed as «exe»
    from smtv import updates
    checked = []
    u = updates.Updates(tools=lambda: [], running=lambda: 0, stop_jobs=lambda: None, port=lambda: 1, kind="zip",
                        manifest=lambda floor: pytest.fail("no network here"))
    monkeypatch.setattr(u, "due", lambda: True)
    stopping = __import__("threading").Event()
    monkeypatch.setattr(u, "check", lambda: checked.append(1) or stopping.set())
    u.daily(stopping, first=0, tick=0.01, every=0)
    assert checked == [1]


# --- yt-dlp in the ZIP ----------------------------------------------------------------------------------------------

def test_the_zip_installs_yt_dlp_into_its_data_folder_where_python_finds_it(tmp_path, monkeypatch):
    # review #2: pip into sys.prefix put it at the top (Lib, Scripts), where the ._pth never looks
    from vodcut import local_download
    top = zip_folder(tmp_path / "ClipIt")
    monkeypatch.setattr(paths, "portable_top", lambda prefix=None, platform=None: top)
    monkeypatch.setenv("SMTV_HOME", str(top / "data"))
    monkeypatch.setattr("smtv.updates.find_uv", lambda: None)
    argv = local_download.install_argv()
    assert argv[argv.index("--target") + 1] == str(top / "data" / paths.PORTABLE_SITE)
    assert str(top / "data" / paths.PORTABLE_SITE) in local_download.install_hint()
    site = top / "data" / paths.PORTABLE_SITE / "yt_dlp"
    site.mkdir(parents=True)
    (site / "__init__.py").write_text("", encoding="utf-8")
    assert local_download.available()                       # found without a new start
    monkeypatch.setattr(paths, "portable_top", lambda prefix=None, platform=None: None)
    other = local_download.install_argv()
    assert other is None or "--target" not in other           # every other install: its own environment, as before


def test_a_job_writes_its_log_in_utf8_even_where_python_ignores_pythonioencoding(monkeypatch):
    # review #7: the ._pth puts the ZIP's Python in isolated mode; the job sets its own encoding
    from smtv import cli
    import io
    out = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", out)
    monkeypatch.setattr(sys, "stderr", io.TextIOWrapper(io.BytesIO(), encoding="cp1252"))
    monkeypatch.setenv("PYTHONIOENCODING", "utf-8")
    cli._line_buffered()
    assert sys.stdout.encoding == "utf-8" and sys.stdout.line_buffering


# --- removing it ----------------------------------------------------------------------------------------------------

def test_removing_the_zip_takes_only_its_own_files_and_the_folder_only_when_empty(tmp_path, monkeypatch):
    # review #4, #8, #9: a person's file stays (and so does the folder then); hidden files go; the script runs outside
    top = installed(tmp_path)
    monkeypatch.setattr(paths, "portable_top", lambda prefix=None, platform=None: top)
    monkeypatch.setenv("SMTV_HOME", str(top / "data"))
    p = uninstall.plan()
    assert p.program == "folder" and p.data_folder == str(top)
    keep = [f.name for f in uninstall.folder_leftovers(top, data=False)]
    assert keep == ["ClipIt.exe", "ClipIt.exe.config", "How to start Clip It!.txt", "app", "python312._pth", "python312.dll"]
    every = [f.name for f in uninstall.folder_leftovers(top, data=True)]
    assert "Clips" in every and "data" in every and "my notes.docx" not in every
    monkeypatch.setenv("SMTV_OUTER_TEMP", str(tmp_path / "systemp"))
    (tmp_path / "systemp").mkdir()
    spawned = []
    done = uninstall.run(True, spawn=spawned.append)
    (argv,) = spawned
    assert Path(argv[-1]).is_relative_to(tmp_path / "systemp")
    script = Path(argv[-1]).read_text(encoding="utf-8")
    assert "my notes.docx" not in script and str(top / "Clips") in script
    if sys.platform == "win32":
        assert "del /f /q /a" in script and f'rd "{top}"' in script and f'rd /s /q "{top}"' not in script
    else:
        assert f"rmdir {top}" in script.replace("'", "")
    assert any("nothing of yours" in d for d in done.done)
    assert uninstall.outer_temp() == str(tmp_path / "systemp")
    src = Path(uninstall.__file__).read_text(encoding="utf-8")
    assert "cwd=outer_temp()" in src


