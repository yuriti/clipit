"""Stage 24: VodCut's own checks — links (the account, or a fresh yt-dlp here with its recipe) and the speech model."""
import datetime as dt
import sys

import pytest

from smtv_core.checks import FAIL, OK, SIGN_IN, WARN
from smtv_core.settings import Settings
from vodcut import local_download, options, tool


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path))
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)
    from smtv_core import account
    monkeypatch.setattr(account, "signed_in", lambda: None)


def links(s):
    return next(r for r in tool.checks(s) if r.id.startswith("vodcut-"))


def test_without_an_account_links_warn_and_offer_to_sign_in():
    row = links(Settings.load())
    assert row.status == WARN and row.actions == (SIGN_IN,) and row.recipe is None


def test_yt_dlp_missing_fails_with_a_recipe_into_smtvs_own_environment(monkeypatch):
    s = Settings.load()
    options.set_option(s, "local_download", True)
    monkeypatch.setattr(local_download, "available", lambda: False)
    monkeypatch.setattr("smtv.updates.find_uv", lambda: "/home/u/.local/bin/uv")
    row = links(s)
    assert row.status == FAIL and row.id == "vodcut-yt-dlp"
    assert row.recipe.argv == ["/home/u/.local/bin/uv", "pip", "install", "--python", sys.executable, "--upgrade", "yt-dlp"]
    assert not row.recipe.admin and row.recipe.links == ("https://github.com/yt-dlp/yt-dlp",)
    monkeypatch.setattr("smtv.updates.find_uv", lambda: None)
    monkeypatch.setattr("importlib.util.find_spec", lambda name: object() if name == "pip" else None)
    assert links(s).recipe.argv == [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp"]
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None)
    assert links(s).recipe is None and links(s).fix                        # no way here: the command to run by hand


def test_an_old_yt_dlp_is_a_warning_with_the_update(monkeypatch):
    s = Settings.load()
    options.set_option(s, "local_download", True)
    monkeypatch.setattr(local_download, "available", lambda: True)
    monkeypatch.setattr("smtv.updates.find_uv", lambda: "uv")
    old = (dt.date.today() - dt.timedelta(days=120)).strftime("%Y.%m.%d")
    monkeypatch.setattr(local_download, "version", lambda: old)
    row = links(s)
    assert row.status == WARN and "120 days" in row.detail and "--upgrade" in row.recipe.argv
    monkeypatch.setattr(local_download, "version", lambda: dt.date.today().strftime("%Y.%m.%d"))
    row = links(s)
    assert row.status == OK and row.recipe is None


def test_age_of_a_version():
    assert local_download.age_days("2026.11.02", dt.date(2026, 11, 22)) == 20
    assert local_download.age_days("2026.11.02.233000", dt.date(2026, 11, 2)) == 0
    assert local_download.age_days("nightly", dt.date(2026, 11, 2)) is None
    assert local_download.age_days(None) is None


def test_vodcut_checks_the_speech_model():
    row = next(r for r in tool.checks(Settings.load()) if r.id == "speech")
    assert row.status in (OK, WARN)
