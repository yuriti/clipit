"""`smtv vodcut set` saves through Settings.edit (A8): a switch from the command line never loses a change made by the
window at the same moment."""
import argparse
import json

from smtv_core import paths
from smtv_core.settings import Settings
from vodcut import options, tool


def test_vodcut_set_keeps_what_else_is_in_the_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path))
    with Settings.edit() as s:
        s.tools["other"] = {"x": 1}
    name = next(iter(options.DEFAULTS))
    assert tool._cmd_set(argparse.Namespace(name=name, value="off"), None, None) == 0
    saved = json.loads(paths.settings_file().read_text(encoding="utf-8"))
    assert saved["tools"]["other"] == {"x": 1}
    assert options.load(Settings.load())[name] is False


def test_vodcut_set_edits_under_the_settings_lock(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path))
    used = []
    real = Settings.edit.__func__

    def spy(cls, path=None):
        used.append(True)
        return real(cls, path)

    monkeypatch.setattr(Settings, "edit", classmethod(spy))
    tool._cmd_set(argparse.Namespace(name=next(iter(options.DEFAULTS)), value="on"), None, None)
    assert used
