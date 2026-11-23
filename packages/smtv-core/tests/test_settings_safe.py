"""В3, A8: settings that cannot be read, and two writers at once."""
import json
import subprocess
import sys
import threading

import pytest

from smtv_core import account, settings as settings_mod
from smtv_core.settings import Provider, Settings


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path))
    monkeypatch.setattr(settings_mod, "BROKEN", [])
    return tmp_path


@pytest.mark.parametrize("text", ["{", "[]", "", "\x00\xff", '"just a string"'])
def test_an_unreadable_settings_file_is_set_aside_and_smtv_starts_empty(home, text, capsys):
    (home / "settings.json").write_text(text, encoding="latin-1")
    s = Settings.load()
    assert s.providers == [] and s.tools == {}
    copies = list(home.glob("settings.broken-*.json"))
    assert len(copies) == 1 and copies[0].read_text(encoding="latin-1") == text
    assert not (home / "settings.json").exists()
    assert "kept as settings.broken-" in capsys.readouterr().err
    assert settings_mod.broken_notice() == copies[0].name
    # the next save works and the next load reads it
    with Settings.edit() as s:
        s.tools["smtv"] = {"update_check": False}
    assert Settings.load().tools == {"smtv": {"update_check": False}}


def test_no_notice_when_settings_are_fine(home):
    Settings().save()
    Settings.load()
    assert settings_mod.broken_notice() is None


def test_two_saves_at_once_never_fail(home):
    errors = []

    def save():
        try:
            for _ in range(30):
                Settings(tools={"smtv": {"x": 1}}).save()
        except Exception as e:  # noqa: BLE001
            errors.append(e)
    ts = [threading.Thread(target=save) for _ in range(4)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert errors == [] and json.loads((home / "settings.json").read_text(encoding="utf-8"))["tools"] == {"smtv": {"x": 1}}
    assert not list(home.glob("*.tmp"))


def test_two_edits_at_once_keep_both_changes(home):
    def switch():
        with Settings.edit() as s:
            s.tools.setdefault("vodcut", {})["recap"] = True

    def provider():
        with Settings.edit() as s:
            s.providers.append(Provider(id=s.new_id("openai"), kind="openai"))
    for _ in range(10):
        ts = [threading.Thread(target=switch), threading.Thread(target=provider)]
        [t.start() for t in ts]
        [t.join() for t in ts]
    s = Settings.load()
    assert s.tools["vodcut"]["recap"] is True and len(s.providers) == 10


def test_edits_from_two_processes_keep_every_change(home):
    """The window and `smtv model` are separate processes: the file lock keeps both."""
    code = ("import sys; from smtv_core.settings import Settings\n"
            "for i in range(40):\n"
            "    with Settings.edit() as s:\n"
            "        s.tools.setdefault('n', {})[sys.argv[1] + str(i)] = i\n")
    ps = [subprocess.Popen([sys.executable, "-c", code, tag]) for tag in ("a", "b")]
    assert [p.wait(60) for p in ps] == [0, 0]
    assert len(Settings.load().tools["n"]) == 80


def test_nothing_is_saved_when_an_edit_fails(home):
    Settings(tools={"smtv": {"a": 1}}).save()
    with pytest.raises(RuntimeError):
        with Settings.edit() as s:
            s.tools["smtv"]["a"] = 2
            raise RuntimeError("no")
    assert Settings.load().tools["smtv"]["a"] == 1


def test_the_account_server_is_set_under_the_lock(home, monkeypatch):
    monkeypatch.delenv("SMTV_ACCOUNT_URL", raising=False)
    monkeypatch.setattr(account, "delete_secret", lambda name: None)
    account.set_server("http://127.0.0.1:9000")
    assert Settings.load().tools["smtv"]["account_server"] == "http://127.0.0.1:9000"
