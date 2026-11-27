"""The desktop apps (work В11): install/app/build.py, smoke.py, the release workflow, and what SMTV does
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
from smtv_core import checks, paths

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
double_click = load("double_click", APP)
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
        if t.system == "win":    # python.org's own CPython, signed by the PSF (Smart App Control), from its NuGet package
            assert t.python.url.startswith(build.NUGET + "python/3.12.") and t.python.url.endswith(".nupkg")
        else:
            assert "cpython-3.12." in t.python.url and t.python.url.split("/")[-1].startswith("cpython-")
        names = {name for d in t.ffmpeg for _, name in d.members}
        exe = ".exe" if t.system == "win" else ""
        assert f"ffmpeg{exe}" in names and not any("ffprobe" in n for n in names)   # proc.probe asks ffmpeg itself
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
                 "Один Clip It! для любого Mac", "One Clip It! for every Mac"):
        assert must in text, must


# --- Windows ---------------------------------------------------------------------------------------------------------

REAL_COMPILE = build.compile_win_launcher
LAUNCHER = b"MZ launcher " + "SMTV_LAUNCH_CHECK".encode("utf-16-le")


@pytest.fixture(autouse=True)
def fake_win_launcher(monkeypatch):
    """MinGW is not on every computer: the folder tests get a stand-in for what compile_win_launcher makes."""
    monkeypatch.setattr(build, "compile_win_launcher", lambda dest, v: dest.write_bytes(LAUNCHER) or dest)


def win_python(tmp_path):
    """python-build-standalone's Windows folder, in small."""
    py = tmp_path / "python"
    (py / "Lib" / "site-packages").mkdir(parents=True)
    (py / "DLLs").mkdir()
    (py / "DLLs" / "_ssl.pyd").write_bytes(b"MZ ssl")
    (py / "pythonw.exe").write_bytes(b"MZ windowless")
    (py / "python.exe").write_bytes(b"MZ console")
    for dll in ("python312.dll", "python3.dll", "vcruntime140.dll", "vcruntime140_1.dll"):
        (py / dll).write_bytes(b"MZ " + dll.encode())
    (py / "LICENSE.txt").write_text("PSF", encoding="utf-8")
    (py / build.KIND_MARKER).write_text("exe\n", encoding="utf-8")
    return py


def test_python_org_s_nuget_package_unpacks_into_the_same_layout(tmp_path):
    nupkg = tmp_path / "python.3.12.10.nupkg"
    with zipfile.ZipFile(nupkg, "w") as z:
        z.writestr("python.nuspec", "<package/>")
        z.writestr("tools/pythonw.exe", "MZ signed")
        z.writestr("tools/python312.dll", "MZ dll")
        z.writestr("tools/DLLs/_ssl.pyd", "MZ ssl")
        z.writestr("tools/Lib/os.py", "")
        z.writestr("build/native/python.props", "")
    py = build.unpack_python(nupkg, tmp_path / "python")
    assert sorted(str(f.relative_to(py)).replace("\\", "/") for f in py.rglob("*") if f.is_file()) == \
        ["DLLs/_ssl.pyd", "Lib/os.py", "python312.dll", "pythonw.exe"]
    evil = tmp_path / "evil.nupkg"
    with zipfile.ZipFile(evil, "w") as z:
        z.writestr("tools/../../escaped.txt", "x")
    with pytest.raises(SystemExit, match="outside"):
        build.unpack_python(evil, tmp_path / "python2")
    apps = (REPO / ".github" / "workflows" / "apps.yml").read_text(encoding="utf-8")
    assert "Get-AuthenticodeSignature" in apps and "O=Python Software Foundation" in apps   # checked on Windows, per build
    assert "'app\\pythonw.exe'" in apps and "launcher built here" in apps and "ProductName -ne 'Clip It!'" in apps


def test_the_windows_folder_shows_one_program_a_how_to_and_app_with_the_rest(tmp_path):
    folder = build.make_win_folder(win_python(tmp_path), tmp_path)
    how_to = build.how_to_name()
    assert how_to.endswith(" Clip It!.txt")         # its first line: «how to start Clip It!» in Russian
    assert sorted(f.name for f in folder.iterdir()) == sorted([
        "ClipIt.exe", "ClipIt.exe.config", "app", how_to, "python312._pth",
        "python312.dll", "python3.dll", "vcruntime140.dll", "vcruntime140_1.dll"])
    app = folder / "app"
    assert sorted(f.name for f in app.iterdir()) == sorted([
        "DLLs", "LICENSE.txt", "Lib", build.KIND_MARKER, "pythonw.exe", "smtv.ico"])
    # ClipIt.exe is our launcher (launcher_win.c), not a copy of Python's program; pythonw.exe stays in app\ exactly as
    # python.org publishes it, python.exe is gone, and no script is added
    assert (folder / "ClipIt.exe").read_bytes() == LAUNCHER and (app / "pythonw.exe").read_bytes() == b"MZ windowless"
    assert sorted(f.name for f in folder.rglob("*") if f.suffix.lower() in (".exe", ".cmd", ".bat")) == \
        ["ClipIt.exe", "pythonw.exe"]
    # Python finds everything in app\ through the ._pth beside python312.dll (ASCII, as Python reads it)
    assert (folder / "python312._pth").read_bytes() == \
        b"app\r\napp\\DLLs\r\napp\\Lib\r\napp\\Lib\\site-packages\r\nimport site\r\n"
    # the text a person reads: Russian first, then English; with a BOM, so Notepad shows it right on any Windows
    text = (folder / how_to).read_bytes()
    assert text.startswith(b"\xef\xbb\xbf") and b"\r\n" in text
    body = text.decode("utf-8-sig")
    assert body.index("ClipIt.exe") < body.index("How to start Clip It!") and "app" in body
    assert (app / "smtv.ico").read_bytes()[:4] == b"\x00\x00\x01\x00"
    assert paths.app_folder(str(folder)) == app                   # where SMTV looks for ffmpeg, its kind and icon
    # the double click on ClipIt.exe opens the window: Python reads this on every start
    site = app / "Lib" / "site-packages" / "sitecustomize.py"
    assert site.read_text(encoding="utf-8") == (APP / "double_click.py").read_text(encoding="utf-8")
    # .NET loads pythonnet's files even when Explorer marked them as downloaded (Extract All)
    config = (folder / "ClipIt.exe.config").read_text(encoding="utf-8")
    assert '<loadFromRemoteSources enabled="true"/>' in config and config.startswith("<?xml")
    assert smoke.win_layout(folder) == []
    z = build.zip_folder(folder, tmp_path / "SMTV.zip", "zip")
    with zipfile.ZipFile(z) as f:
        names = f.namelist()
        assert f.read(f"ClipIt/app/{build.KIND_MARKER}").decode().strip() == "zip"
        assert f.getinfo(f"ClipIt/{how_to}").flag_bits & 0x800       # its Russian name is marked UTF-8 for Explorer
    assert folder.name == "ClipIt" and "ClipIt/ClipIt.exe" in names
    assert all(n.startswith("ClipIt/") and "\\" not in n for n in names)
    assert (app / build.KIND_MARKER).read_text(encoding="utf-8").strip() == "exe"   # the installer's copy stays exe


def test_smoke_names_what_does_not_belong_at_the_top(tmp_path):
    folder = build.make_win_folder(win_python(tmp_path), tmp_path)
    (folder / "python.exe").write_bytes(b"MZ")
    (folder / "unins000.exe").write_bytes(b"MZ")          # the installer's own uninstaller belongs there
    (folder / "ClipIt.exe.config").write_text("<configuration/>", encoding="utf-8")
    failed = smoke.win_layout(folder)
    assert len(failed) == 2 and "python.exe" in failed[0] and "loadFromRemoteSources" in failed[1]


def test_smoke_tells_a_copy_of_pythonw_from_the_launcher(tmp_path):
    folder = build.make_win_folder(win_python(tmp_path), tmp_path)
    assert smoke.win_layout(folder) == []
    (folder / "ClipIt.exe").write_bytes((folder / "app" / "pythonw.exe").read_bytes())    # the build before the launcher
    assert "not the launcher" in smoke.win_layout(folder)[0]
    (folder / "ClipIt.exe").write_bytes(LAUNCHER)
    (folder / "app" / "pythonw.exe").unlink()
    assert "pythonw.exe is missing" in smoke.win_layout(folder)[0]


def test_the_launcher_has_the_clip_it_icon_and_the_apps_version_in_its_resources():
    rc = build.win_launcher_rc("0.2.0")
    assert "FILEVERSION 0,2,0,0" in rc and 'VALUE "FileVersion", "0.2.0"' in rc and '1 ICON "smtv.ico"' in rc
    assert 'VALUE "ProductName", "Clip It!"' in rc and 'VALUE "CompanyName", "yuriti"' in rc
    assert "FILEVERSION 1,2,3,0" in build.win_launcher_rc("1.2.3rc1")


def test_the_launcher_source_starts_pythonw_in_app_and_says_what_is_wrong_in_a_box():
    c = (APP / "launcher_win.c").read_text(encoding="utf-8")
    assert r'L"\\app\\pythonw.exe"' in c and "-m smtv app" in c and "MessageBoxW" in c and "SMTV_LAUNCH_CHECK" in c
    assert sorted(set(re.findall(r"[^\x00-\x7f]", c))) == []        # English and ASCII, as the other service files


def test_compile_win_launcher_says_what_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(build.shutil, "which", lambda tool: None)
    with pytest.raises(SystemExit, match="MinGW-w64"):
        REAL_COMPILE(tmp_path / "ClipIt.exe", "0.2.0")


def test_paths_app_folder_is_the_prefix_everywhere_but_the_windows_app(tmp_path):
    assert paths.app_folder(str(tmp_path)) == tmp_path            # a uv tool, a Mac app, a venv
    (tmp_path / "app").mkdir()                                     # a folder of that name alone is not the layout
    assert paths.app_folder(str(tmp_path)) == tmp_path
    (tmp_path / "app" / "Lib" / "site-packages").mkdir(parents=True)
    assert paths.app_folder(str(tmp_path)) == tmp_path / "app"


def test_there_is_no_windows_installer_any_more():
    # Smart App Control blocks Inno Setup's unsigned is-*.tmp; the ZIP is portable and updates itself
    assert not (APP / "smtv.iss").exists()
    built = (APP / "build.py").read_text(encoding="utf-8")
    assert "iscc" not in built.lower() and "setup.exe" not in built
    for wf in ("apps.yml", "release.yml", "smart-app-control.yml"):
        assert "setup.exe" not in (REPO / ".github" / "workflows" / wf).read_text(encoding="utf-8"), wf
    assert ("exe", "x64", "SMTV-{v}-windows-x64.zip") in release_manifest.APPS


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
    # the Windows ZIP is listed as "exe": 0.1.0 refuses a list with a kind it does not know. Its installed copies get
    # the ZIP; the ZIP takes the same file to replace itself in place
    exe = channel.files_for(m, "exe", arch="x64")[0]
    assert exe["name"] == "SMTV-0.2.0-windows-x64.zip"
    assert exe["sha256"] == hashlib.sha256(b"SMTV-{v}-windows-x64.zip").hexdigest()
    assert channel.files_for(m, "exe", arch="arm64") == [exe]  # Windows on ARM: the x64 build, which it emulates
    assert channel.files_for(m, "zip", arch="x64") == [exe]
    assert set(m["kinds"]) <= {"uv", "pip", "dmg", "exe"}      # 0.1.0's own list of kinds


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
    assert apps.count("smoke.py") >= 2 and "setup.exe" not in apps and "/VERYSILENT" not in apps   # no installer
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
    assert 'isApp(u) ? h("p.hint", t("p_app"))' in js and '["dmg", "exe", "zip"].includes(u.kind)' in js   # it updates
    assert 'r.program === "app"' in js and 'p.program === "app"' in js and 'p.program === "folder"' in js
    assert 'r.id === "speech" && r.status === "warn" && r.recipe' in js          # the first run offers the speech model
    for lang in ("en", "ru"):
        words = json.loads((REPO / "packages" / "smtv" / "src" / "smtv" / "web" / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))
        for key in ("remove_app_mac", "remove_app_win", "remove_folder", "portable_readonly", "portable_migrate", "p_app",
                    "ob_speech"):
            assert words.get(key), (lang, key)


def test_the_apps_ffmpeg_comes_after_a_persons_own_and_before_anything_else(tmp_path, monkeypatch):
    prefix = marked(monkeypatch, tmp_path, "dmg")
    monkeypatch.setattr(checks.sys, "prefix", str(prefix))
    before, _ = checks._ffmpeg_dirs()
    assert before[:2] == [checks.paths.home() / "bin", prefix / checks.APP_FFMPEG]
    for d in before[:2]:
        d.mkdir(parents=True, exist_ok=True)
        (d / checks._exe("ffmpeg")).write_text("", encoding="utf-8")
    monkeypatch.setattr(checks, "has_libass", lambda folder: folder == str(prefix / checks.APP_FFMPEG))
    assert checks.find_ffmpeg() == (str(prefix / checks.APP_FFMPEG), True)   # a person's bin without captions loses


# --- the check of a built app --------------------------------------------------------------------------------------

def test_the_smoke_check_runs_the_apps_python_with_a_clean_environment(tmp_path, monkeypatch):
    cmd, env = smoke.app_python(tmp_path / "SMTV.app", "arm64")
    assert cmd == ["/usr/bin/arch", "-arm64", str(tmp_path / "SMTV.app" / "Contents" / "MacOS" / "smtv-python-arm64")]
    assert env["PYTHONHOME"].endswith(os.path.join("Contents", "Resources", "python-arm64"))
    intel, ienv = smoke.app_python(tmp_path / "SMTV.app", "x86_64")
    assert intel[:2] == ["/usr/bin/arch", "-x86_64"] and ienv["PYTHONHOME"].endswith("python-x86_64")
    assert smoke.app_python(tmp_path / "SMTV")[0] == [str(tmp_path / "SMTV" / "ClipIt.exe")]   # no python.exe in it
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
    for name in ("dmg-readme.txt", "double_click.py", "launcher.c", "launcher_win.c", "how-to-start.txt"):
        assert name in built


# --- the size of the Windows app (0.1.1: 549 MB → about 290) -----------------------------------------------------------

def test_the_windows_app_leaves_whisper_s_engine_to_first_use_with_pinned_pypi_wheels():
    win = build.TARGETS["win-x64"]
    assert win.on_demand == build.WHISPER_PART == ("av", "ctranslate2", "faster-whisper", "tokenizers")
    assert all(not t.on_demand for t in build.TARGETS.values() if t.system == "mac")     # its signature seals what it loads
    spec = build.part_spec(win.on_demand, win)
    assert [w["name"] for w in spec["wheels"]] == list(win.on_demand)
    lock = (REPO / "uv.lock").read_text(encoding="utf-8")
    for w in spec["wheels"]:
        assert w["url"].startswith("https://files.pythonhosted.org/") and w["url"].endswith(".whl")
        assert re.fullmatch(r"[0-9a-f]{64}", w["sha256"]) and f"sha256:{w['sha256']}" in lock and w["size"] > 0
        name = w["url"].rsplit("/", 1)[-1]
        assert "win_amd64" in name or name.endswith("-none-any.whl"), name
    assert 30 < sum(w["size"] for w in spec["wheels"]) / 1e6 < 200        # the download, compressed
    # smoke and pip check know what is left out on purpose
    assert set(smoke.LEFT_OUT) == set(build.WHISPER_PART + build.NOT_IN_APPS)


@pytest.mark.parametrize(("name", "fits"), [
    ("av-16.0.1-cp312-cp312-win_amd64.whl", True), ("tokenizers-0.23.3-cp310-abi3-win_amd64.whl", True),
    ("faster_whisper-1.2.1-py3-none-any.whl", True), ("av-16.0.1-cp313-cp313-win_amd64.whl", False),
    ("av-16.0.1-cp312-cp312-macosx_11_0_arm64.whl", False), ("x-1-cp313-abi3-win_amd64.whl", False),
    ("ctranslate2-4.6.0-cp312-cp312-win32.whl", False)])
def test_a_part_takes_the_wheel_uv_would_install_for_the_target(name, fits):
    assert build.wheel_fits(name, build.TARGETS["win-x64"]) is fits


def test_the_build_leaves_out_packages_through_uv_export(monkeypatch, tmp_path):
    ran = []
    monkeypatch.setattr(build, "run", lambda argv, **k: ran.append([str(a) for a in argv]))
    build.requirements(tmp_path / "r.txt", ("hf-xet", "av"))
    (argv,) = ran
    assert argv[argv.index("hf-xet") - 1] == "--no-emit-package" and argv[argv.index("av") - 1] == "--no-emit-package"


def test_sources_headers_and_tests_of_packages_go_but_licenses_stay(tmp_path):
    site = tmp_path / "site-packages"
    for f in ("numpy/_core/include/numpy/x.h", "av/_core.pyx", "av/x.pxd", "lib/tests/test_a.py", "lib/tests/data/t.bin",
              "lib/test/b.py", "lib/LICENSE.txt", "lib/core.py", "lib/latest.py", "lib.libs/x.dll", "src/x.c"):
        (site / f).parent.mkdir(parents=True, exist_ok=True)
        (site / f).write_text("x", encoding="utf-8")
    build.remove(build.leftovers(site))
    left = sorted(str(f.relative_to(site)).replace("\\", "/") for f in site.rglob("*") if f.is_file())
    assert left == ["lib.libs/x.dll", "lib/LICENSE.txt", "lib/core.py", "lib/latest.py"]


def test_the_build_says_where_the_size_is_and_smoke_holds_the_limit(tmp_path, capsys):
    (tmp_path / "app" / "Lib" / "site-packages" / "big").mkdir(parents=True)
    (tmp_path / "app" / "Lib" / "site-packages" / "big" / "x.bin").write_bytes(b"x" * 3_000_000)
    (tmp_path / "ClipIt.exe").write_bytes(b"x" * 1_000)
    sizes = dict(build.folder_sizes(tmp_path))
    assert sizes == {"app/Lib/site-packages/big": 3_000_000, "(top files)": 1_000}
    assert smoke.win_size(tmp_path, limit_mb=5) == []
    (failed,) = smoke.win_size(tmp_path, limit_mb=2)
    assert "over its limit of 2 MB" in failed and "WIN_LIMIT_MB" in failed
    assert smoke.WIN_LIMIT_MB == 320


def test_pip_check_complains_only_about_what_was_not_left_out_on_purpose():
    out = ("vodcut 0.1.1 requires faster-whisper, which is not installed.\n"
           "huggingface-hub 1.2.0 requires hf-xet, which is not installed.\n"
           "onnx-asr 0.12 requires numpy, which is not installed.\n")
    assert smoke.unexpected_pip_check(out) == ["onnx-asr 0.12 requires numpy, which is not installed."]
