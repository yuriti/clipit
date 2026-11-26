"""The desktop apps (work В11): install/app/build.py, smoke.py, smtv.iss, the release workflow, and what SMTV does
differently when it runs as the app (dmg, exe, zip). Nothing here downloads or builds a whole app: the downloads are
local files, the Python is a tiny fake archive. The real build and its check run in .github/workflows/apps.yml."""
import base64
import hashlib
import json
import os
import plistlib
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

from smtv import channel, cli, ed25519, launcher, uninstall, updates
from smtv_core import checks

REPO = Path(__file__).resolve().parents[1]
APP = REPO / "install" / "app"


def load(name: str, folder: Path):
    sys.path.insert(0, str(folder))
    try:
        return __import__(name)
    finally:
        sys.path.remove(str(folder))


build = load("build", APP)
smoke = load("smoke", APP)
release_manifest = load("release_manifest", REPO / "scripts")


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("SMTV_DOCKER", raising=False)


def marked(monkeypatch, tmp_path, kind: str) -> Path:
    prefix = tmp_path / "prefix"
    prefix.mkdir(exist_ok=True)
    (prefix / updates.KIND_MARKER).write_text(kind + "\n", encoding="utf-8")
    monkeypatch.setattr(updates.sys, "prefix", str(prefix))
    return prefix


# --- what is downloaded ---------------------------------------------------------------------------------------------

def test_every_download_is_pinned_by_https_and_sha256_and_versions_agree():
    for t in build.TARGETS.values():
        for d in (t.python, *t.ffmpeg):
            assert d.url.startswith("https://") and re.fullmatch(r"[0-9a-f]{64}", d.sha256), d
        assert "cpython-3.12." in t.python.url and t.python.url.split("/")[-1].startswith("cpython-")
        names = {name for d in t.ffmpeg for _, name in d.members}
        exe = ".exe" if t.system == "win" else ""
        assert {f"ffmpeg{exe}", f"ffprobe{exe}"} <= names        # SMTV needs both, or it finds no ffmpeg at all
        assert all("9.1" in d.url for d in t.ffmpeg)            # the version FFMPEG_NOTE names
    assert {t.min_os for t in build.TARGETS.values() if t.system == "mac"} == {"13.0", "14.0"}


def serve_file(tmp_path, data: bytes) -> str:
    f = tmp_path / "served.bin"
    f.write_bytes(data)
    return f.as_uri()


def test_a_download_is_kept_only_with_its_pinned_sum_and_is_not_fetched_twice(tmp_path, monkeypatch):
    data = b"python archive"
    url = serve_file(tmp_path, data)
    cache = tmp_path / "cache"
    with pytest.raises(SystemExit, match="SHA-256"):
        build.fetch(build.Download(url, "0" * 64), cache)
    assert not list(cache.glob("*"))                        # neither the file nor its .part stays
    good = build.Download(url, hashlib.sha256(data).hexdigest())
    path = build.fetch(good, cache)
    assert path.read_bytes() == data
    (tmp_path / "served.bin").unlink()                      # the source is gone: the cached copy is used
    assert build.fetch(good, cache) == path


def fake_python(tmp_path, system: str) -> Path:
    """A python-build-standalone archive in miniature: python/ with the folders the build trims and keeps."""
    root = tmp_path / "src" / "python"
    lib = root / ("Lib" if system == "win" else "lib/python3.12")
    for keep in ("os.py", "site-packages/pip/__init__.py"):
        (lib / keep).parent.mkdir(parents=True, exist_ok=True)
        (lib / keep).write_text("x", encoding="utf-8")
    for gone in ("tkinter/__init__.py", "idlelib/x.py", "ensurepip/__init__.py", "__pycache__/os.cpython-312.pyc"):
        (lib / gone).parent.mkdir(parents=True, exist_ok=True)
        (lib / gone).write_text("x", encoding="utf-8")
    (root / "include").mkdir()
    (root / "include" / "Python.h").write_text("x", encoding="utf-8")
    if system == "win":
        for f in ("python.exe", "pythonw.exe", "python312.dll", "python312.pdb"):
            (root / f).write_bytes(b"MZ")
    archive = tmp_path / "python.tar.gz"
    with tarfile.open(archive, "w:gz") as tar:
        tar.add(root, arcname="python")
    return archive


@pytest.mark.parametrize("system", ["mac", "win"])
def test_python_is_unpacked_and_trimmed_of_what_nobody_runs(tmp_path, system):
    t = build.TARGETS["win-x64" if system == "win" else "mac-arm64"]
    py = build.unpack_python(fake_python(tmp_path, system), tmp_path / "out" / "python")
    site = build.site_packages(py, t)
    assert (site / "pip" / "__init__.py").is_file()
    assert build.trim(py, site) > 0
    lib = py / ("Lib" if system == "win" else "lib/python3.12")
    assert (lib / "os.py").is_file() and (site / "pip").is_dir()          # pip stays: yt-dlp is installed with it
    for gone in ("tkinter", "idlelib", "ensurepip", "__pycache__"):
        assert not (lib / gone).exists()
    assert not (py / "include").exists() and not list(py.rglob("*.pdb"))
    # unpacking again replaces the folder instead of mixing two builds
    build.unpack_python(fake_python(tmp_path / "again", system), tmp_path / "out" / "python")
    assert (lib / "tkinter").exists()


def test_the_requirements_come_from_the_lock_with_hashes_for_every_package(tmp_path):
    lock = (REPO / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "onnxruntime", version = "1.23.2"' in lock and "platform_machine == 'x86_64' and sys_platform == 'darwin'" in lock
    if not build.shutil.which("uv") and not build.shutil.which("uv", path=str(Path(sys.executable).parent)):
        pytest.skip("uv is not installed here")
    text = build.requirements(tmp_path / "req.txt").read_text(encoding="utf-8")
    pins = [line for line in text.splitlines() if re.match(r"^[A-Za-z0-9]", line)]
    assert pins and all("==" in p for p in pins)
    assert text.count("--hash=sha256:") >= len(pins)
    names = {p.split("==")[0].lower() for p in pins}
    assert {"pywebview", "onnxruntime", "faster-whisper", "numpy"} <= names
    assert not names & {"smtv", "smtv-core", "vodcut", "torch", "yt-dlp"}    # own wheels apart; no torch, no yt-dlp


# --- macOS -----------------------------------------------------------------------------------------------------------

def test_the_mac_launcher_picks_the_python_by_the_hardware_and_sets_only_what_it_needs():
    c = (APP / "launcher.c").read_text(encoding="utf-8")
    assert 'sysctlbyname("hw.optional.arm64"' in c and "uname" not in c.split("*/", 1)[1]   # under Rosetta uname lies
    assert 'macos_major() >= 14 ? "arm64" : "x86_64"' in c          # Apple silicon on macOS 13: the Intel one, under Rosetta
    assert '"%s/Resources/python-%s"' in c and '"%s/MacOS/smtv-python-%s"' in c
    assert 'setenv("PYTHONHOME"' in c and 'unsetenv("PYTHONPATH")' in c and 'setenv("PYTHONNOUSERSITE", "1", 1)' in c
    assert '{python, "-m", "smtv", "app", NULL}' in c and "argv" not in c.split("int main", 1)[1]   # Finder's args never passed on
    assert "/opt/homebrew/bin" in c and 'launch.log' in c


def test_the_mac_app_is_marked_so_smtv_shortcut_never_touches_it(tmp_path):
    info = build.mac_info("0.2.0", "14.0")
    assert info["CFBundleIdentifier"] == launcher.BUNDLE_ID and info["CFBundleExecutable"] == "SMTV"
    assert info[build.INFO_KIND] == "dmg" == info[launcher.APP_KIND] and info["LSMinimumSystemVersion"] == "14.0"
    for name, plist, ours in (("App.app", info, False), ("Shortcut.app", {"CFBundleIdentifier": launcher.BUNDLE_ID}, True),
                              ("Other.app", {"CFBundleIdentifier": "com.example"}, False)):
        app = tmp_path / name
        (app / "Contents").mkdir(parents=True)
        (app / "Contents" / "Info.plist").write_bytes(plistlib.dumps(plist))
        assert launcher._is_ours(app) is ours, name


def test_the_mac_app_holds_both_pythons_where_the_launcher_looks_and_keeps_shared_files_once(tmp_path, monkeypatch):
    pythons = {}
    for arch in ("arm64", "x86_64"):
        py = tmp_path / arch / "python"
        (py / "bin").mkdir(parents=True)
        (py / "bin" / "python3.12").write_bytes(f"mach-o {arch}".encode())
        (py / "lib").mkdir()
        (py / "lib" / "same.py").write_text("print('the same in both')", encoding="utf-8")
        (py / "lib" / "native.so").write_bytes(f"native {arch}".encode())
        pythons[arch] = py
    made = []
    monkeypatch.setattr(build, "compile_launcher", lambda dest: made.append(dest) or dest.write_bytes(b"universal") or dest)
    app = build.make_mac_app(pythons, tmp_path, "0.2.0")
    c = app / "Contents"
    for arch in ("arm64", "x86_64"):
        assert (c / "MacOS" / f"smtv-python-{arch}").read_bytes() == f"mach-o {arch}".encode()
        assert (c / "Resources" / f"python-{arch}" / "lib" / "native.so").read_bytes() == f"native {arch}".encode()
    assert made == [c / "MacOS" / "SMTV"]
    shared = c / "Resources" / "python-x86_64" / "lib" / "same.py"
    assert shared.is_symlink() and not os.path.isabs(os.readlink(shared))            # relative: the app can move
    assert shared.read_text(encoding="utf-8") == "print('the same in both')"
    assert not (c / "Resources" / "python-x86_64" / "lib" / "native.so").is_symlink()
    assert (c / "Resources" / "smtv.icns").read_bytes()[:4] == b"icns"
    info = plistlib.loads((c / "Info.plist").read_bytes())
    assert info["LSArchitecturePriority"] == ["arm64", "x86_64"] and info["LSMinimumSystemVersion"] == "13.0"


def test_the_dmg_readme_explains_the_warning_honestly_in_both_languages():
    text = (APP / "dmg-readme.txt").read_text(encoding="utf-8")
    for must in ("Конфиденциальность и безопасность", "Всё равно открыть", "Privacy & Security", "Open Anyway",
                 "Подпись появится при первой возможности", "It will get one as soon as possible", "Исправить", "Fix",
                 "Один SMTV для любого Mac", "One SMTV for every Mac"):
        assert must in text, must


# --- Windows ---------------------------------------------------------------------------------------------------------

def test_the_windows_folder_has_smtv_exe_the_icon_and_the_zip_is_marked_zip(tmp_path):
    py = tmp_path / "python"
    py.mkdir()
    (py / "pythonw.exe").write_bytes(b"MZ windowless")
    (py / build.KIND_MARKER).write_text("exe\n", encoding="utf-8")
    folder = build.make_win_folder(py, tmp_path)
    assert (folder / "SMTV.exe").read_bytes() == b"MZ windowless"
    assert (folder / "smtv.ico").read_bytes()[:4] == b"\x00\x00\x01\x00"
    assert "-m smtv app" in (folder / "Start SMTV.cmd").read_text(encoding="utf-8")
    z = build.zip_folder(folder, tmp_path / "SMTV.zip", "zip")
    with zipfile.ZipFile(z) as f:
        names = f.namelist()
        assert f.read(f"SMTV/{build.KIND_MARKER}").decode().strip() == "zip"
    assert "SMTV/SMTV.exe" in names and all(n.startswith("SMTV/") and "\\" not in n for n in names)
    assert (folder / build.KIND_MARKER).read_text(encoding="utf-8").strip() == "exe"   # the installer's copy stays exe


def test_the_installer_is_per_user_keeps_its_id_and_names_its_file_as_the_release_expects():
    iss = (APP / "smtv.iss").read_text(encoding="utf-8")
    assert "PrivilegesRequired=lowest" in iss and r"DefaultDirName={localappdata}\Programs\SMTV" in iss
    assert "AppId={{6F0B7E52-6C1D-4E57-9C4B-3B7D2B1E5A10}" in iss          # never change: Windows finds SMTV by it
    assert "OutputBaseFilename=SMTV-{#AppVersion}-windows-x64-setup" in iss
    assert ("exe", "x64", "SMTV-{v}-windows-x64-setup.exe") in release_manifest.APPS
    assert r'Name: "{autoprograms}\SMTV"; Filename: "{app}\SMTV.exe"; Parameters: "-m smtv app"' in iss
    assert 'Excludes: "Start SMTV.cmd"' in iss and "[UninstallDelete]" in iss
    # ISCC is 32-bit: the compressor runs apart, in 64 bits, with few threads (4 threads ran out of memory, v0.1.0)
    assert "LZMAUseSeparateProcess=yes" in iss and int(re.search(r"LZMANumBlockThreads=(\d+)", iss)[1]) <= 2
    # the file build.py looks for after ISCC is the one smtv.iss writes
    assert "SMTV-{v}-windows-x64-setup.exe" in (APP / "build.py").read_text(encoding="utf-8")


# --- the release ---------------------------------------------------------------------------------------------------

def test_the_release_puts_every_app_in_the_signed_manifest_with_its_processor(tmp_path, monkeypatch):
    secret = os.urandom(32)
    public = base64.b64encode(ed25519.public_key(secret)).decode()
    dist = tmp_path / "dist"
    dist.mkdir()
    for n in ("smtv", "smtv_core", "vodcut"):
        (dist / f"{n}-0.2.0-py3-none-any.whl").write_bytes(b"PK" + n.encode())
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n## 0.2.0\n\n- Apps\n", encoding="utf-8")
    monkeypatch.setenv("SMTV_UPDATE_SIGNING_KEY", base64.b64encode(secret).decode())
    args = [str(dist), "--apps", "--version", "0.2.0", "--changelog", str(changelog), "--public-key", public,
            "--base-url", "https://github.com/yuriti/clipit/releases/download/v0.2.0"]
    with pytest.raises(SystemExit, match="missing"):           # --apps: no release with an app missing
        release_manifest.main(args)
    for _, _, pattern in release_manifest.APPS:
        (dist / pattern.format(v="0.2.0")).write_bytes(pattern.encode())
    assert release_manifest.main(args) == 0
    raw = (dist / "latest.json").read_bytes()
    channel.verify(raw, (dist / "latest.json.sig").read_bytes(), public)
    m = channel.parse(raw, ("smtv", "smtv-core", "vodcut"))
    assert [(f["name"], f["arch"]) for f in m["kinds"]["dmg"]["files"]] == [("SMTV-0.2.0-mac.dmg", None)]
    for cpu in ("arm64", "x64"):                                # one .dmg for every Mac
        assert channel.files_for(m, "dmg", arch=cpu)[0]["name"] == "SMTV-0.2.0-mac.dmg"
    exe = channel.files_for(m, "exe", arch="x64")[0]
    assert exe["sha256"] == hashlib.sha256(b"SMTV-{v}-windows-x64-setup.exe").hexdigest()
    assert channel.files_for(m, "exe", arch="arm64") == [exe]  # Windows on ARM: the x64 installer, which it emulates
    assert "zip" not in m["kinds"]                            # the ZIP does not update itself


def test_a_manifest_with_an_unknown_processor_is_refused():
    with pytest.raises(channel.ChannelError):
        f = {"name": "SMTV-0.2.0-mac.dmg", "url": "https://github.com/x", "size": 1, "sha256": "0" * 64, "arch": "riscv"}
        channel.parse(json.dumps({"schema": 1, "version": "0.2.0", "packages": {"smtv": "0.2.0"}, "changes": [],
                                  "kinds": {"dmg": {"files": [f]}}}).encode(), ("smtv",), "github.com")


def test_this_computers_processor_in_the_manifests_words(monkeypatch):
    import platform
    for machine, word in (("arm64", "arm64"), ("aarch64", "arm64"), ("ARM64", "arm64"), ("x86_64", "x64"), ("AMD64", "x64")):
        monkeypatch.setattr(platform, "machine", lambda m=machine: m)
        assert channel.machine() == word


def test_the_release_workflow_publishes_nothing_before_every_app_passed_its_check():
    release = (REPO / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
    apps = (REPO / ".github" / "workflows" / "apps.yml").read_text(encoding="utf-8")
    assert "uses: ./.github/workflows/apps.yml" in release and "needs: apps" in release
    assert "release_manifest.py dist --apps" in release and "SHA256SUMS.txt" in release
    assert "workflow_call:" in apps
    for target in ("mac", "win-x64"):
        assert f"build.py {target}" in apps
    assert apps.count("smoke.py") >= 3 and "unins000.exe" in apps and "/VERYSILENT" in apps
    assert "|| true" not in apps and "not started" not in apps          # the Intel app is never released unchecked
    assert apps.count("--release") == 2 and "hdiutil attach" in apps and "Expand-Archive" in apps
    assert "--arch arm64" in apps and "--arch x86_64" in apps                 # both Pythons of the one app
    assert "SMTV-$v-mac.dmg" in release and "mac-arm64" not in release + apps and "mac-x64" not in release + apps
    assert release.index("uv publish") < release.index("dist/latest.json.sig dist/latest.json")   # the manifest last
    for line in re.findall(r"uses: (\S+)", apps):
        assert line.startswith("./") or re.search(r"@[0-9a-f]{40}$", line), line   # actions pinned by commit


# --- SMTV as the app --------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["dmg", "exe", "zip"])
def test_the_app_knows_its_kind_and_takes_no_icon_of_its_own(kind, tmp_path, monkeypatch, capsys):
    marked(monkeypatch, tmp_path, kind)
    assert updates.install_kind() == kind
    made = []
    monkeypatch.setattr(launcher, "install", lambda s: made.append(s) or ["icon"])
    monkeypatch.setattr(cli, "at_terminal", lambda: True)
    cli.first_run_shortcut("doctor")
    assert made == []
    assert cli.cmd_shortcut(type("A", (), {"remove": False})(), [], []) == 0 and made == []
    assert "desktop app" in capsys.readouterr().out


@pytest.mark.parametrize("kind", ["dmg", "exe", "zip"])
def test_removing_the_app_from_its_window_keeps_its_icon_and_says_how_to_remove_the_program(kind, tmp_path, monkeypatch):
    marked(monkeypatch, tmp_path, kind)
    p = uninstall.plan()
    assert p.program == "app" and p.program_command == []
    spawned, removed = [], []
    monkeypatch.setattr(launcher, "remove", lambda s: removed.append(s) or ["icon"])
    done = uninstall.run(False, spawn=spawned.append, system=object())
    assert removed == [] and spawned == []                     # no uv, no script: the app goes the system's way
    assert any("the program itself" in n for n in done.notes)


def test_smtv_uninstall_in_a_terminal_says_how_to_remove_the_app(tmp_path, monkeypatch, capsys):
    marked(monkeypatch, tmp_path, "dmg")
    from smtv import instance, serve
    monkeypatch.setattr(serve, "probe", lambda port: None)
    monkeypatch.setattr(instance, "holder", lambda *a, **k: None)
    monkeypatch.setattr(uninstall, "run", lambda data: uninstall.Plan("x", 0, "app", []))
    assert cli.cmd_uninstall(type("A", (), {"data": False, "yes": True})(), [], []) == 0
    out = capsys.readouterr().out
    assert "the system's way" in out and "uv tool" not in out


@pytest.mark.skipif(sys.platform != "darwin" or not build.shutil.which("clang"), reason="builds the launcher with clang on a Mac")
def test_the_launcher_is_one_program_for_both_processors_and_picks_this_macs_python(tmp_path):
    import subprocess
    (tmp_path / "SMTV.app" / "Contents" / "MacOS").mkdir(parents=True)
    main = build.compile_launcher(tmp_path / "SMTV.app" / "Contents" / "MacOS" / "SMTV")
    assert sorted(subprocess.run(["lipo", "-archs", str(main)], capture_output=True, text=True).stdout.split()) == ["arm64", "x86_64"]
    want = smoke.native_arch()
    env = {"SMTV_LAUNCHER_DRY": "1", "HOME": str(tmp_path)}
    runs = [[str(main)]] + ([["/usr/bin/arch", "-x86_64", str(main)]] if want == "arm64" and
                            subprocess.run(["/usr/bin/arch", "-x86_64", "/usr/bin/true"]).returncode == 0 else [])
    for cmd in runs:          # under Rosetta too: the hardware decides, not the launcher's own processor
        arch, python = subprocess.run(cmd, env=env, capture_output=True, text=True, check=True).stdout.split()
        assert arch == want and python == str(tmp_path / "SMTV.app" / "Contents" / "MacOS" / f"smtv-python-{want}")


def test_a_zip_without_its_marker_is_not_made(tmp_path):
    (tmp_path / "SMTV").mkdir()
    with pytest.raises(SystemExit, match="missing"):
        build.zip_folder(tmp_path / "SMTV", tmp_path / "x.zip", "zip")


def test_the_window_says_how_the_app_updates_and_is_removed():
    js = (REPO / "packages" / "smtv" / "src" / "smtv" / "web" / "app.js").read_text(encoding="utf-8")
    assert 'isApp(u) ? h("p.hint", t("p_app"))' in js and 'u.kind === "zip"' in js
    assert 'r.program === "app"' in js and 'p.program === "app"' in js
    assert 'r.id === "speech" && r.status === "warn" && r.recipe' in js          # the first run offers the speech model
    for lang in ("en", "ru"):
        words = json.loads((REPO / "packages" / "smtv" / "src" / "smtv" / "web" / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
        for key in ("remove_app_mac", "remove_app_win", "upd_zip", "upd_zip_link", "p_app", "ob_speech"):
            assert words.get(key), (lang, key)


def test_the_apps_ffmpeg_comes_after_a_persons_own_and_before_anything_else(tmp_path, monkeypatch):
    prefix = marked(monkeypatch, tmp_path, "dmg")
    monkeypatch.setattr(checks.sys, "prefix", str(prefix))
    before, _ = checks._ffmpeg_dirs()
    assert before[:2] == [checks.paths.home() / "bin", prefix / checks.APP_FFMPEG]
    for d in before[:2]:
        d.mkdir(parents=True, exist_ok=True)
        for n in ("ffmpeg", "ffprobe"):
            (d / checks._exe(n)).write_text("", encoding="utf-8")
    monkeypatch.setattr(checks, "has_libass", lambda folder: folder == str(prefix / checks.APP_FFMPEG))
    assert checks.find_ffmpeg() == (str(prefix / checks.APP_FFMPEG), True)   # a person's bin without captions loses


# --- the check of a built app --------------------------------------------------------------------------------------

def test_the_smoke_check_runs_the_apps_python_with_a_clean_environment(tmp_path, monkeypatch):
    cmd, env = smoke.app_python(tmp_path / "SMTV.app", "arm64")
    assert cmd == ["/usr/bin/arch", "-arm64", str(tmp_path / "SMTV.app" / "Contents" / "MacOS" / "smtv-python-arm64")]
    assert env["PYTHONHOME"].endswith(os.path.join("Contents", "Resources", "python-arm64"))
    intel, ienv = smoke.app_python(tmp_path / "SMTV.app", "x86_64")
    assert intel[:2] == ["/usr/bin/arch", "-x86_64"] and ienv["PYTHONHOME"].endswith("python-x86_64")
    assert smoke.app_python(tmp_path / "SMTV")[0] == [str(tmp_path / "SMTV" / "python.exe")]
    monkeypatch.setenv("PYTHONPATH", "/somewhere")
    monkeypatch.setenv("PATH", "/opt/homebrew/bin:/usr/bin")
    clean = smoke.clean_env(tmp_path / "home", {"PYTHONHOME": "x"})
    assert "PYTHONPATH" not in clean and "homebrew" not in clean["PATH"]   # the app must find its own ffmpeg
    assert clean["SMTV_HOME"] == str(tmp_path / "home") and clean["SMTV_NO_SHORTCUT"] == "1" and clean["PYTHONHOME"] == "x"


def test_the_smoke_check_fails_when_the_app_does_not_start(tmp_path, capsys):
    app = tmp_path / "SMTV"
    app.mkdir()
    assert smoke.main([str(app)]) == 1
    out = capsys.readouterr()
    # the cause sits in this run's own output, right above its summary (not on stderr, next to the other run's)
    lines = out.out.splitlines()
    assert lines[-2].startswith("FAILED: the app's Python did not start") and lines[-1] == "smoke (windows): 1 failed"
    assert out.err == ""


def test_the_build_scripts_print_any_character_on_a_console_without_it(tmp_path):
    # a Windows runner's console is cp1252: smoke printed smtv doctor's «→» and died with UnicodeEncodeError
    env = {**os.environ, "PYTHONIOENCODING": "ascii"}           # stricter than cp1252: no «, no →
    app = tmp_path / "SMTV →"                                    # smoke's failure names the folder
    app.mkdir()
    r = subprocess.run([sys.executable, str(APP / "smoke.py"), str(app)], env=env, capture_output=True, timeout=60)
    assert r.returncode == 1 and "SMTV →".encode() in r.stdout and b"Traceback" not in r.stderr, r.stderr
    r = subprocess.run([sys.executable, str(APP / "build.py"), "--help"], env=env, capture_output=True, timeout=60)
    assert r.returncode == 0 and "«".encode() in r.stdout, r.stderr


def test_the_build_sources_are_ascii_named_and_have_their_callers():
    for f in APP.iterdir():
        assert re.fullmatch(r"[a-z0-9._-]+", f.name), f.name
    apps = (REPO / ".github" / "workflows" / "apps.yml").read_text(encoding="utf-8")
    for name in ("build.py", "smoke.py"):
        assert f"install/app/{name}" in apps
    sac = (REPO / ".github" / "workflows" / "smart-app-control.yml").read_text(encoding="utf-8")
    assert "install/app/sac_check.py" in sac
    built = (APP / "build.py").read_text(encoding="utf-8")
    for name in ("smtv.iss", "dmg-readme.txt", "start-smtv.cmd", "launcher.c"):
        assert name in built
