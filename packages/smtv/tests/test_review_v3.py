"""В3: what the code review of 22.11 found in settings, the report, «Fix», the icon and downloads."""
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from smtv import desktop, fixes, launcher, models_api, phone, report, serve, updater
from smtv_core import proc
from smtv_core import settings as settings_mod
from smtv_core.checks import Check, Recipe
from smtv_core.settings import Settings, set_secret


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("SMTV_NO_KEYCHAIN", "1")
    monkeypatch.setattr(settings_mod, "BROKEN", [])
    return tmp_path / "home"


# --- A8: the window's settings -----------------------------------------------------------------------------------------

def test_the_window_says_when_settings_were_set_aside(home):
    home.mkdir(parents=True)
    (home / "settings.json").write_text("{", encoding="utf-8")
    app = serve.App([], [])
    got = app.settings()
    assert got["providers"] == [] and got["broken"].startswith("settings.broken-")   # the kept copy; the window words it
    words = {lang: json.loads((serve.WEB / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))["set_broken"] for lang in ("en", "ru")}
    assert all("{file}" in w for w in words.values())
    assert app.update_settings({"check": False})["check"] is False      # saving works again


def test_a_switch_and_the_update_setting_at_once_keep_both(home):
    app = serve.App([], [])
    barrier = threading.Barrier(2)
    real_load = Settings.load.__func__

    def slow_load(cls, path=None):          # both read before either writes: without the lock one change is lost
        s = real_load(cls, path)
        try:
            barrier.wait(timeout=0.3)
        except threading.BrokenBarrierError:
            pass
        return s
    with pytest.MonkeyPatch.context() as m:
        m.setattr(Settings, "load", classmethod(slow_load))
        ts = [threading.Thread(target=app.update_settings, args=({"check": False},)),
              threading.Thread(target=lambda: phone.Saved().save(True, None, None))]
        [t.start() for t in ts]
        [t.join() for t in ts]
    s = Settings.load().tools["smtv"]
    assert s["update_check"] is False and s["phone"]["on"] is True


# --- A19, B24: the report ----------------------------------------------------------------------------------------------

def test_account_tokens_are_cut_by_value(home, monkeypatch):
    from smtv_core import account
    set_secret(account.SECRET_NAME, json.dumps({"access_token": "opaque-access-1234567890", "refresh_token": "opaque-refresh-abcdefghij",
                                                "expires_at": 1}))
    values = report.secret_values()
    assert "opaque-refresh-abcdefghij" in values and "opaque-access-1234567890" in values
    cut = report.Scrubber(values)("refreshing with opaque-refresh-abcdefghij failed")
    assert "opaque-refresh" not in cut and "[key]" in cut


def test_the_docker_access_key_is_cut_by_value(home):
    from smtv import container
    home.mkdir(parents=True, exist_ok=True)
    container.key_file().write_text("docker-key-0123456789abcdef\n", encoding="utf-8")
    assert "docker-key-0123456789abcdef" in report.secret_values()


def test_the_home_folder_is_cut_in_any_case():
    s = report.Scrubber([], homes=["C:\\Users\\Someone"])
    assert s("c:\\users\\someone\\AppData\\x and C:\\USERS\\SOMEONE\\y") == "~\\AppData\\x and ~\\y"


def test_explorer_gets_the_path_quoted_on_its_own():
    """C20: the whole `/select,…` quoted makes Explorer open «Documents»."""
    assert report.explorer_select(Path("C:/Users/someone/My Videos/Downloads/r.zip")) == \
        f'explorer /select,"{Path("C:/Users/someone/My Videos/Downloads/r.zip")}"'


# --- A10, C23, decision 11: «Fix» ----------------------------------------------------------------------------------------

WINGET = Recipe("ffmpeg", ["C:\\winget.exe", "install", "--id", "Gyan.FFmpeg", "--accept-package-agreements",
                           "--accept-source-agreements"])


def test_winget_says_what_the_person_accepts():
    assert fixes.consent(WINGET) == fixes.WINGET_CONSENT and "Microsoft" in fixes.WINGET_CONSENT
    assert fixes.consent(Recipe("ffmpeg", ["brew", "install", "ffmpeg"])) is None


def test_the_window_sees_the_winget_consent_before_the_press():
    # the check's recipe (what the dialog shows before «Исправить») carries the sentence, not only the console
    assert WINGET.public()["consent"] == fixes.WINGET_CONSENT
    assert Recipe("ffmpeg", ["brew", "install", "ffmpeg"]).public()["consent"] is None


def test_the_winget_consent_is_the_first_console_line_and_in_the_recipe(monkeypatch):
    class P:
        stdout = iter([b"ok\n", b""]).__next__
        returncode = 0

        def __init__(self):
            self.stdout = type("S", (), {"readline": iter([b"done\n", b""]).__next__})()

        def wait(self, timeout=None):
            return 0

        def poll(self):
            return 0
    seen = {}
    f = fixes.Fixes(popen=lambda argv, **k: seen.update(k) or P())
    state = f.start(Check("ffmpeg", "fail", "no ffmpeg", recipe=WINGET, id="ffmpeg"))
    assert state["lines"][0]["text"] == fixes.WINGET_CONSENT and state["recipe"]["consent"] == fixes.WINGET_CONSENT
    assert "text" not in seen and "encoding" not in seen           # bytes: decoded per line
    assert seen.get("creationflags") == proc.group().get("creationflags")


def test_winget_output_in_the_console_code_page_is_read(monkeypatch):
    monkeypatch.setattr(fixes.sys, "platform", "win32")
    monkeypatch.setattr(fixes, "_oem", lambda: "cp866")
    assert fixes.decode("Найден пакет".encode("cp866")) == "Найден пакет"
    assert fixes.decode("Готово ✓".encode("utf-8")) == "Готово ✓"


def test_the_terminal_script_for_winget_names_the_consent(tmp_path, monkeypatch):
    monkeypatch.setattr(fixes.sys, "platform", "win32")
    script = fixes._script(WINGET, tmp_path).read_text(encoding="utf-8")
    assert "chcp 65001" in script and fixes.WINGET_CONSENT in script


def test_helper_programs_open_no_console_window(monkeypatch):
    """A10: the icon's PowerShell and uv in the updater run with CREATE_NO_WINDOW on Windows."""
    seen = []
    monkeypatch.setattr(proc, "hidden", lambda: {"creationflags": 0x08000000})
    monkeypatch.setattr(launcher.subprocess, "run", lambda argv, **k: seen.append(k) or subprocess.CompletedProcess(argv, 0))
    launcher._run(["powershell.exe"])
    assert seen[-1]["creationflags"] == 0x08000000
    monkeypatch.setattr(updater.sys, "platform", "win32")
    updater.run_steps([["uv", "tool"]], runner=lambda argv, **k: seen.append(k) or subprocess.CompletedProcess(argv, 0))
    assert seen[-1]["creationflags"] == updater.NO_WINDOW


# --- C25: the session file ----------------------------------------------------------------------------------------------

@pytest.mark.skipif(sys.platform == "win32", reason="POSIX rights")
def test_an_old_session_file_is_made_private(home):
    path = desktop.session_file()
    path.parent.mkdir(parents=True)
    path.write_text("{}", encoding="utf-8")
    os.chmod(path, 0o644)
    desktop.write_session(8642, "tok")
    assert (path.stat().st_mode & 0o777) == 0o600


# --- C12, C22: model downloads ------------------------------------------------------------------------------------------

def test_a_failing_hook_does_not_leave_the_download_running():
    d = models_api.Downloads(on_change=lambda: (_ for _ in ()).throw(RuntimeError("window gone")))
    d.start("speech:x", lambda progress, stop: None, done_hook=lambda: (_ for _ in ()).throw(OSError("disk")))
    for _ in range(100):
        if not d.running("speech:x"):
            break
        time.sleep(0.01)
    assert d.state("speech:x")["status"] == "done"


def test_old_finished_downloads_are_forgotten_without_being_read():
    d = models_api.Downloads()
    d.items["old"] = {"status": "done", "at": time.time() - 10_000}
    d.start("new", lambda progress, stop: None)
    time.sleep(0.1)
    assert "old" not in d.items
