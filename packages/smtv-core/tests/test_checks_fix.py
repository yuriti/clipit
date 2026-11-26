"""Stage 24: the checks of this computer and their built-in recipes («Fix»)."""
import os
import sys
from collections import namedtuple
from pathlib import Path

import pytest

from smtv_core import checks
from smtv_core.checks import FAIL, OK, WARN, Check, Recipe
from smtv_core.settings import Provider, Settings, set_secret


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)
    monkeypatch.delenv("SMTV_DOCKER", raising=False)
    monkeypatch.setattr(checks, "LANGUAGE_HINT", None)


def fake_ffmpeg(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("ffmpeg", "ffprobe"):
        (folder / checks._exe(name)).write_text("", encoding="utf-8")
    return folder


def test_a_check_shows_its_recipe_as_text_and_only_while_not_ok():
    r = Recipe("x", ["/usr/bin/tool", "install", "a b"], links=("https://example.org",))
    bad = Check("Thing", FAIL, "missing", "do it", id="thing", recipe=r, actions=(checks.OPEN_FOLDER,))
    pub = bad.public()
    assert pub["recipe"] == {"id": "x", "kind": "command", "command": r.line(), "links": ["https://example.org"], "consent": None}
    assert "a b" in pub["recipe"]["command"] and pub["actions"] == ["open_folder"] and pub["id"] == "thing"
    good = Check("Thing", OK, "here", id="thing", recipe=r, actions=(checks.OPEN_FOLDER,)).public()
    assert good["recipe"] is None and good["actions"] == []
    assert Recipe("y", ["sudo", "x"], admin=True).public()["kind"] == "terminal"
    assert Recipe("z", ["a"], shown="what runs").line() == "what runs"


def test_the_libass_check_waits_for_a_slow_first_start(tmp_path, monkeypatch):
    # the Intel ffmpeg of SMTV.app under Rosetta took more than 15 s to start the first time: «no libass», doctor then ok
    asked = []
    monkeypatch.setattr(checks, "_run", lambda argv, timeout=15: asked.append(timeout) or " .. ass  V->V  Render ASS\n")
    assert checks.has_libass(str(tmp_path)) and asked == [checks.LIBASS_WAIT_S] and checks.LIBASS_WAIT_S >= 60


def test_ffmpeg_with_captions_is_preferred_and_put_first_on_path(tmp_path, monkeypatch):
    plain = fake_ffmpeg(tmp_path / "plain")
    full = fake_ffmpeg(tmp_path / "full")
    monkeypatch.setattr(checks, "_ffmpeg_dirs", lambda: ([plain], [full]))
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    monkeypatch.setattr(checks, "has_libass", lambda folder: folder == str(full))
    assert checks.find_ffmpeg() == (str(full), True)
    monkeypatch.setenv("PATH", os.pathsep.join(["/usr/bin", str(full)]))
    assert checks.use_ffmpeg() == str(full)
    parts = os.environ["PATH"].split(os.pathsep)
    assert parts[0] == str(full) and parts.count(str(full)) == 1 and "/usr/bin" in parts
    # none has libass: the first one, and the libass row fails with the recipe
    monkeypatch.setattr(checks, "has_libass", lambda folder: False)
    assert checks.find_ffmpeg() == (str(plain), False)
    monkeypatch.setattr(checks, "_run", lambda argv, timeout=15: "ffmpeg version 7")
    monkeypatch.setattr(checks, "ffmpeg_recipe", lambda: Recipe("ffmpeg", ["brew", "install", "ffmpeg-full"]))
    rows = checks.check_ffmpeg()
    assert [r.status for r in rows] == [OK, FAIL] and rows[1].id == "libass" and rows[1].recipe.id == "ffmpeg"


def test_no_ffmpeg_fails_with_the_recipe_and_use_ffmpeg_leaves_path(monkeypatch):
    monkeypatch.setattr(checks, "_ffmpeg_dirs", lambda: ([], []))
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    monkeypatch.setattr(checks, "ffmpeg_recipe", lambda: Recipe("ffmpeg", ["winget", "install"]))
    [row] = checks.check_ffmpeg()
    assert row.status == FAIL and row.id == "ffmpeg" and row.recipe.argv == ["winget", "install"]
    before = os.environ.get("PATH")
    assert checks.use_ffmpeg() is None and os.environ.get("PATH") == before


def test_ffmpeg_recipes_per_system(monkeypatch):
    monkeypatch.setattr(checks.sys, "platform", "darwin")
    monkeypatch.setattr(checks, "find_brew", lambda: "/opt/homebrew/bin/brew")
    r = checks.ffmpeg_recipe()
    assert r.argv == ["/opt/homebrew/bin/brew", "install", "ffmpeg-full"] and not r.admin and "formulae.brew.sh" in r.links[0]
    monkeypatch.setattr(checks, "find_brew", lambda: None)
    r = checks.ffmpeg_recipe()                       # no Homebrew: its official installer, only in a terminal
    assert r.id == "homebrew" and r.admin and r.line() == checks.HOMEBREW_INSTALL and r.links == ("https://brew.sh",)
    monkeypatch.setattr(checks.sys, "platform", "win32")
    monkeypatch.setattr(checks, "find_winget", lambda: r"C:\winget.exe")
    r = checks.ffmpeg_recipe()
    assert r.argv[:4] == [r"C:\winget.exe", "install", "--id", "Gyan.FFmpeg"] and not r.admin and "--disable-interactivity" in r.argv
    monkeypatch.setattr(checks, "find_winget", lambda: None)
    assert checks.ffmpeg_recipe() is None and "Microsoft Store" in checks.ffmpeg_install_hint()
    monkeypatch.setattr(checks.sys, "platform", "linux")
    monkeypatch.setattr(checks.shutil, "which", lambda name: "/usr/bin/apt-get" if name == "apt-get" else None)
    r = checks.ffmpeg_recipe()
    assert r.argv == ["sudo", "apt-get", "install", "-y", "ffmpeg"] and r.admin
    monkeypatch.setenv("SMTV_DOCKER", "1")
    assert checks.ffmpeg_recipe() is None             # the image has its own ffmpeg


DU = namedtuple("DU", "total used free")


@pytest.mark.parametrize("free_gb,status", [(300, OK), (12, WARN), (2, FAIL)])
def test_free_space_blocks_only_when_a_request_cannot_fit(monkeypatch, free_gb, status):
    monkeypatch.setattr(checks.shutil, "disk_usage", lambda p: DU(0, 0, free_gb * 1e9))
    row = checks.check_disk()
    assert row.status == status and row.id == "disk" and row.recipe is None
    assert row.actions == (checks.OPEN_FOLDER, checks.CLEAR_CACHE)
    assert bool(row.fix) == (status != OK)


def test_system_version(monkeypatch):
    monkeypatch.setattr(checks.sys, "platform", "darwin")
    monkeypatch.setattr(checks.platform, "mac_ver", lambda: ("12.7.1", ("", "", ""), "arm64"))
    old = checks.check_system()
    assert old.status == FAIL and "13" in old.fix and old.recipe is None
    monkeypatch.setattr(checks.platform, "mac_ver", lambda: ("15.1", ("", "", ""), "arm64"))
    assert checks.check_system().status == OK
    monkeypatch.setattr(checks.sys, "platform", "win32")
    monkeypatch.setattr(checks.sys, "getwindowsversion", lambda: type("V", (), {"build": 17134})(), raising=False)
    assert checks.check_system().status == FAIL
    monkeypatch.setattr(checks.sys, "getwindowsversion", lambda: type("V", (), {"build": 22631})(), raising=False)
    assert checks.check_system().status == OK


def test_gpu_is_only_information(monkeypatch):
    monkeypatch.setattr(checks.shutil, "which", lambda name: None)
    assert checks.check_gpu().status == OK


def test_the_model_check_counts_a_refused_key_as_not_ready(monkeypatch):
    p = Provider(id="oa", kind="openai", name="OpenAI", preset="openai", base_url="https://api.openai.com/v1")
    set_secret(p.key_name(), "sk-xxxxxxxxxxxx")
    s = Settings(providers=[p])
    assert checks.check_model(s).status == OK
    row = checks.check_model(s, verify=lambda prov: (False, "HTTP 401"))
    assert row.status == FAIL and "not accepted" in row.detail and "HTTP 401" in row.detail and row.actions == (checks.PROVIDERS,)
    assert checks.check_model(s, verify=lambda prov: (None, "")).status == OK     # no network: not held against it
    assert checks.check_model(s, verify=lambda prov: (True, "")).status == OK


def test_streammoment_unreachable_blocks_only_when_it_is_the_one_provider(monkeypatch):
    from smtv_core import account
    monkeypatch.setattr(account, "check", lambda: {"ok": False, "detail": "no answer", "hint": "a VPN?"})
    assert checks.check_streammoment(others_ready=False).status == FAIL
    assert checks.check_streammoment(others_ready=True).status == WARN


def test_the_speech_model_check(monkeypatch):
    from smtv_core.asr import catalog
    s = Settings()
    monkeypatch.setattr(catalog, "is_installed", lambda m, d=None: False)
    row = checks.check_speech(s, "ru")
    assert row.status == WARN and row.id == "speech" and "GigaAM" in row.detail
    assert row.recipe.argv == [sys.executable, "-m", "smtv", "speech", "download", "gigaam"] and not row.recipe.admin
    assert row.recipe.links and row.actions == (checks.SPEECH,)
    monkeypatch.setattr(catalog, "is_installed", lambda m, d=None: True)
    assert checks.check_speech(s, "ru").status == OK
    monkeypatch.setattr(checks, "LANGUAGE_HINT", "en")
    assert "Parakeet" in checks.check_speech(s).detail          # the window's language by default
    catalog.set_choice(s, "ru", "groq")                          # a cloud model without a key: a warning, no recipe
    row = checks.check_speech(s, "ru")
    assert row.status == WARN and row.recipe is None and row.actions == (checks.SPEECH,)


def test_python_is_not_checked_any_more():
    assert not hasattr(checks, "check_python")                   # the installer brings Python (uv), stage 24


@pytest.mark.parametrize("value, code", [("ru_RU.UTF-8", "ru"), ("ru-RU", "ru"), ("Russian_Russia", "ru"), ("English_United States", "en"),
                                         ("German_Germany", "de"), ("C", None), ("", None), ("Klingon_Space", None)])
def test_the_speech_check_reads_the_language_as_windows_names_it(value, code):
    # Windows 11 (22.11): locale.getlocale() gives ('Russian_Russia', '1251'), and the check took English
    assert checks._language_code(value) == code


def test_a_russian_windows_checks_the_russian_speech_model(monkeypatch):
    import locale
    monkeypatch.setattr(checks, "LANGUAGE_HINT", None)
    for var in ("LC_ALL", "LANG"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(checks, "_windows_language", lambda: None)
    monkeypatch.setattr(locale, "getlocale", lambda *a: ("Russian_Russia", "1251"))
    assert checks.default_language() == "ru"
    monkeypatch.setattr(checks, "_windows_language", lambda: "ru_RU")
    monkeypatch.setattr(locale, "getlocale", lambda *a: (None, None))
    assert checks.default_language() == "ru"
