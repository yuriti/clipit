"""install/install.sh and install/install.ps1: the one-line installers (stage 27).

They run on people's computers before SMTV exists there, so the tests check what can be checked without installing:
the syntax, the linters when present, and a dry run that prints every step and changes nothing.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SH = REPO / "install" / "install.sh"
PS1 = REPO / "install" / "install.ps1"
ISSUE = "https://github.com/streammomenttv/smtv/issues/new?template=bug.yml"
RAW = "https://raw.githubusercontent.com/streammomenttv/smtv/main/install/"

posix = pytest.mark.skipif(sys.platform == "win32", reason="install.sh is for macOS and Linux")


def dry_run(tmp_path: Path, *args: str, lang: str = "en_US.UTF-8", **env: str) -> subprocess.CompletedProcess:
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    clean = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "HOME": str(home), "LANG": lang, "SMTV_DRY_RUN": "1", **env}
    return subprocess.run(["sh", str(SH), *args], env=clean, capture_output=True, text=True, timeout=60)


@posix
def test_install_sh_is_valid_posix_sh():
    assert subprocess.run(["sh", "-n", str(SH)], capture_output=True).returncode == 0


@posix
@pytest.mark.skipif(not shutil.which("shellcheck"), reason="shellcheck is not installed (brew install shellcheck)")
def test_install_sh_passes_shellcheck():
    res = subprocess.run(["shellcheck", "-s", "sh", str(SH)], capture_output=True, text=True)
    assert res.returncode == 0, res.stdout


@posix
def test_dry_run_prints_every_step_and_changes_nothing(tmp_path):
    res = dry_run(tmp_path)
    assert res.returncode == 0, res.stderr
    out = res.stdout
    assert "https://astral.sh/uv/install.sh" in out                       # uv is missing here: its official installer
    assert re.search(r"uv tool install --upgrade .*smtv\[vodcut\]", out)
    assert re.search(r"/smtv shortcut$", out, re.M)
    assert "SMTV is installed." in out
    assert list((tmp_path / "home").iterdir()) == []                      # nothing written


@posix
def test_dry_run_speaks_russian_on_a_russian_system(tmp_path):
    out = dry_run(tmp_path, lang="ru_RU.UTF-8").stdout
    assert "Устанавливаю SMTV" in out and "SMTV установлен." in out
    assert "Installing SMTV" not in out


@posix
def test_tools_can_be_chosen_and_are_checked(tmp_path):
    assert "smtv[vodcut,livecut]" in dry_run(tmp_path, "--tools", "vodcut,livecut").stdout
    bad = dry_run(tmp_path, "--tools", "vodcut;rm")
    assert bad.returncode == 2 and "--tools" in bad.stderr


@posix
def test_no_start_skips_opening(tmp_path):
    res = dry_run(tmp_path, "--no-start", DISPLAY=":0")
    after = res.stdout.split("SMTV is installed.")[1]
    assert res.returncode == 0 and not any(line.startswith("  $ ") for line in after.splitlines())


def test_install_sh_never_asks_for_sudo():
    commands = [line.strip() for line in SH.read_text(encoding="utf-8").splitlines() if not line.strip().startswith("#")]
    assert not any(re.match(r"(run\s+)?sudo\b", c) for c in commands)


def test_install_ps1_never_starts_smtv_exe():
    """Smart App Control blocks the unsigned smtv.exe uv makes: SMTV runs as `python -m smtv` (stage 27, check 2)."""
    text = PS1.read_text(encoding="utf-8-sig")
    code = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    assert "smtv.exe" not in code
    assert '@("-m", "smtv", "shortcut")' in code and '@("-m", "smtv", "app")' in code
    assert "--no-managed-python" in code and "VerifiedAndReputablePolicyState" in code


def test_install_ps1_is_utf8_with_bom():
    """Windows PowerShell 5.1 reads a file without BOM in the ANSI code page: the Russian messages would break."""
    assert PS1.read_bytes().startswith(b"\xef\xbb\xbf")


def test_install_ps1_stops_with_throw_not_exit():
    """`irm | iex` runs in the person's own window: `exit` would close it before they read why."""
    code = "\n".join(line for line in PS1.read_text(encoding="utf-8-sig").splitlines() if not line.lstrip().startswith("#"))
    assert not re.search(r"^\s*exit\b", code, re.M | re.I)


@pytest.mark.skipif(not shutil.which("pwsh"), reason="PowerShell is not installed")
def test_install_ps1_parses_and_dry_runs(tmp_path):
    parse = ("$e=$null; [System.Management.Automation.Language.Parser]::ParseFile('%s',[ref]$null,[ref]$e) | Out-Null; "
             "if ($e.Count) { $e; exit 1 }" % PS1)
    assert subprocess.run(["pwsh", "-NoProfile", "-Command", parse], capture_output=True).returncode == 0
    if sys.platform == "win32":
        env = {**os.environ, "SMTV_DRY_RUN": "1", "SMTV_LANG": "en"}
        res = subprocess.run(["pwsh", "-NoProfile", "-File", str(PS1)], env=env, capture_output=True, text=True, timeout=60)
        assert res.returncode == 0 and "SMTV is installed." in res.stdout


def test_both_installers_agree():
    sh, ps1 = SH.read_text(encoding="utf-8"), PS1.read_text(encoding="utf-8-sig")
    for text in (sh, ps1):
        assert ISSUE in text
        assert "https://astral.sh/uv/install." in text
        assert re.search(r'tool"?,? "?install', text) and "--upgrade" in text
    assert 'TOOLS="${SMTV_TOOLS:-vodcut}"' in sh and '{ "vodcut" }' in ps1


def test_readmes_point_at_the_installers():
    names = sorted(p.name for p in REPO.glob("README*.md"))
    assert {"README.md", "README.ru.md"} <= set(names)
    for name in names:
        text = (REPO / name).read_text(encoding="utf-8")
        assert f"curl -LsSf {RAW}install.sh | sh" in text, name
        assert f"irm {RAW}install.ps1 | iex" in text, name
        for other in names:                                               # every translation links every other one
            assert other == name or f"]({other})" in text, (name, other)
