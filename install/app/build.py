"""The desktop apps (stage 30, part «build»; work В11): SMTV.app in a .dmg for macOS, a folder for the Windows installer.

    python install/app/build.py mac          # SMTV.app and SMTV-<version>-mac.dmg, one for every Mac (on a Mac)
    python install/app/build.py win-x64      # the folder SMTV/ and SMTV-<version>-windows-x64.zip (on any system);
                                             # on Windows with Inno Setup also SMTV-<version>-windows-x64-setup.exe

One SMTV.app for Apple silicon and Intel: it holds two Pythons (python-arm64, python-x86_64, each with its own ffmpeg
and libraries) and a small universal program (launcher.c) that starts the one native to the Mac. Files that are the same
in both (Python code, fonts, the window's page) are kept once: the Intel copy is a link to the Apple silicon one.

What goes in: Python 3.12 (python-build-standalone: a relocatable build of CPython, the one uv itself installs), SMTV
with every dependency at the versions of uv.lock (hashes checked), ffmpeg and ffprobe 9.1 with libass and libx264 (the
captions and clips need both), the caption fonts (inside smtv-core). What stays out: the speech models (downloaded on
the first run, only for the person's language: «Check this computer → Fix»), a local AI model and yt-dlp (optional,
as in every other install).

Why not PyInstaller or Briefcase: SMTV starts its jobs as `python -m smtv …`, installs yt-dlp into its own Python and
updates itself through it; a frozen program has no `python -m` and no pip. A real Python inside the app keeps every
one of those paths the same as in a uv install. Nothing new is installed for the build: it needs uv (already the
project's tool) and, for the Windows installer, Inno Setup (free; preinstalled on GitHub's Windows machines).

Every download is pinned with its SHA-256 below; a file that differs stops the build. Run from the repository root:
the files land in build/app/ (git ignores build/).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
ICONS = REPO / "packages" / "smtv" / "src" / "smtv" / "web" / "icons"
sys.path[:0] = [str(REPO / "packages" / "smtv" / "src"), str(REPO / "packages" / "smtv-core" / "src")]
from smtv import launcher  # noqa: E402 — the icon files and Info.plist of `smtv shortcut`, from the source

PY = "3.12"
PBS = "https://github.com/astral-sh/python-build-standalone/releases/download/20261110/"
RIEDL = "https://ffmpeg.martin-riedl.de/download/macos/"
KIND_MARKER = "smtv-install-kind"    # updates.KIND_MARKER: beside the app's Python, says how this SMTV takes updates
INFO_KIND = "SMTVInstallKind"        # in SMTV.app's Info.plist: `smtv shortcut` never touches an app with it


@dataclass(frozen=True)
class Download:
    url: str
    sha256: str
    members: tuple[tuple[str, str], ...] = ()     # (name inside a zip, name in the app's ffmpeg folder)


@dataclass(frozen=True)
class Target:
    name: str
    system: str                    # "mac" or "win"
    platform: str                  # uv's --python-platform
    python: Download
    ffmpeg: tuple[Download, ...]
    can_run: tuple[str, ...]       # (sys.platform, machine) pairs where this build's Python runs here (for .pyc)
    min_os: str = ""               # macOS: the oldest system the wheels of uv.lock run on (onnxruntime, av)


# ffmpeg: macOS — Martin Riedl's static builds (GPL, release 9.1, libass 0.17.5, x264); Windows — Gyan's «essentials»
# build 9.1 (GPL, libass, x264, NVENC), the one `winget install Gyan.FFmpeg` gives too. Both are separate programs SMTV
# runs; their license and source go into the app's ffmpeg folder (FFMPEG_NOTE).
TARGETS = {
    "mac-arm64": Target(
        "mac-arm64", "mac", "aarch64-apple-darwin",
        Download(PBS + "cpython-3.12.16%2B20261110-aarch64-apple-darwin-install_only.tar.gz",
                 "e956e60bc9465d577ef8062059aa05cd3a2665b4b8678a2ed24e432368330b8f"),
        (Download(RIEDL + "arm64/1795207104_9.1/ffmpeg.zip", "1f66e9a690a7f1c9e60b012379f8869c11818d1797f45b21dbb2f2564ba61ae1",
                  (("ffmpeg", "ffmpeg"),)),
         Download(RIEDL + "arm64/1795207104_9.1/ffprobe.zip", "6ef2df5f575042923a28537ab37adf936f28bf3e7b85de23a1447ed447ec1dbd",
                  (("ffprobe", "ffprobe"),))),
        (("darwin", "arm64"),), "14.0"),
    "mac-x64": Target(
        "mac-x64", "mac", "x86_64-apple-darwin",
        Download(PBS + "cpython-3.12.16%2B20261110-x86_64-apple-darwin-install_only.tar.gz",
                 "83f2922437e6d546d0fcdb8c11f150a8e52787e8d9ea8651b1974e20908eb1bc"),
        (Download(RIEDL + "amd64/1795212433_9.1/ffmpeg.zip", "35b3d82cccc2c1d644d49d15f5e57eb913a08ef68f798042c90eecec62c51f1e",
                  (("ffmpeg", "ffmpeg"),)),
         Download(RIEDL + "amd64/1795212433_9.1/ffprobe.zip", "41ca7b7cba7992e33f1da3f1bf54db8ec103a4d387b1bfac3162062e8b1074ad",
                  (("ffprobe", "ffprobe"),))),
        (("darwin", "x86_64"),), "13.0"),
    "win-x64": Target(
        "win-x64", "win", "x86_64-pc-windows-msvc",
        Download(PBS + "cpython-3.12.16%2B20261110-x86_64-pc-windows-msvc-install_only.tar.gz",
                 "e23fe5b16926de1d81661b1a97352e89fb167549c55a6825796ccd0f32ec7f1b"),
        (Download("https://github.com/GyanD/codexffmpeg/releases/download/9.1/ffmpeg-9.1-essentials_build.zip",
                  "b9bbbb3acece000cbeec994f856649354e52c773807841e78908374b24d658fd",
                  (("ffmpeg-9.1-essentials_build/bin/ffmpeg.exe", "ffmpeg.exe"),
                   ("ffmpeg-9.1-essentials_build/bin/ffprobe.exe", "ffprobe.exe"),
                   ("ffmpeg-9.1-essentials_build/LICENSE", "LICENSE.txt"))),),
        (("win32", "AMD64"),)),
}

FFMPEG_NOTE = """ffmpeg and ffprobe {version} in this folder are separate programs that SMTV runs; they are not part of SMTV's
own code. They are built by {builder} under the GNU General Public License (GPL) version 3: you may share and change
them under its terms. The source code of this version: https://ffmpeg.org/releases/ffmpeg-{version}.tar.xz
How it was built: {config}
License text: https://www.gnu.org/licenses/gpl-3.0.html
SMTV uses the first ffmpeg with captions it finds: put your own build into SMTV's folder bin/ to use it instead.
"""

# What a person never needs from Python here: the Tk window toolkit and its libraries, IDLE, the C headers, the
# turtle demos, the old 2to3, the bundled pip installer, manual pages. The window is pywebview; pip itself stays (yt-dlp
# and the optional parts are installed with it).
TRIM_PYTHON = ("lib/python3.12/tkinter", "lib/python3.12/idlelib", "lib/python3.12/turtledemo", "lib/python3.12/lib2to3",
               "lib/python3.12/ensurepip", "lib/python3.12/turtle.py", "include", "share", "lib/pkgconfig",
               "lib/itcl4.3.8", "lib/thread3.0.6", "lib/tcl9", "lib/tcl9.0", "lib/tk9.0", "lib/libtcl9.0.dylib",
               "lib/libtcl9tk9.0.dylib", "lib/libpython3.12.dylib", "bin/idle3", "bin/idle3.12", "bin/pydoc3",
               "bin/pydoc3.12", "bin/python3-config", "bin/python3.12-config",
               # Windows layout (python-build-standalone keeps the standard library in Lib/)
               "Lib/tkinter", "Lib/idlelib", "Lib/turtledemo", "Lib/lib2to3", "Lib/ensurepip", "Lib/turtle.py", "tcl",
               "DLLs/_tkinter.pyd", "DLLs/tcl86t.dll", "DLLs/tk86t.dll", "DLLs/tcl90.dll", "DLLs/tk90.dll", "libs",
               "include")
# Tests that wheels carry along; nothing imports them at run time.
TRIM_SITE = ("PyObjCTest", "numpy/_core/tests", "numpy/tests", "numpy/f2py", "numpy/typing/tests", "numpy/random/tests",
             "numpy/linalg/tests", "numpy/fft/tests", "numpy/lib/tests", "numpy/ma/tests", "numpy/polynomial/tests",
             "numpy/testing/tests", "onnxruntime/tools", "onnxruntime/transformers", "onnxruntime/quantization",
             "onnxruntime/datasets", "fontTools/misc/plistlib/tests", "av/include", "ctranslate2/converters", "bin")


def log(text: str) -> None:
    print(f"[build] {text}", flush=True)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def fetch(d: Download, cache: Path) -> Path:
    """The file of `d` in `cache`, downloaded once; a file whose SHA-256 differs from the pinned one stops the build."""
    cache.mkdir(parents=True, exist_ok=True)
    name = re.sub(r"[^A-Za-z0-9._+-]", "_", d.url.split("://", 1)[1])
    path = cache / name
    if path.is_file() and sha256(path) == d.sha256:
        return path
    log(f"download {d.url}")
    part = path.with_suffix(path.suffix + ".part")
    req = urllib.request.Request(d.url, headers={"User-Agent": "smtv-build"})   # some hosts refuse Python's default one
    with urllib.request.urlopen(req, timeout=120) as r, open(part, "wb") as f:   # noqa: S310 — pinned https URL
        shutil.copyfileobj(r, f, 1 << 20)
    got = sha256(part)
    if got != d.sha256:
        part.unlink()
        raise SystemExit(f"{d.url}: SHA-256 {got}, expected {d.sha256}. Nothing is built from a file that changed.")
    part.replace(path)
    return path


def version() -> str:
    text = (REPO / "packages" / "smtv" / "pyproject.toml").read_text(encoding="utf-8")
    m = re.search(r'^version = "([^"]+)"', text, re.M)
    if not m:
        raise SystemExit("packages/smtv/pyproject.toml has no version")
    return m.group(1)


def site_packages(python: Path, t: Target) -> Path:
    return python / ("Lib" if t.system == "win" else f"lib/python{PY}") / "site-packages"


def unpack_python(archive: Path, dest: Path) -> Path:
    """python-build-standalone's install_only archive holds one folder, python/; it becomes `dest`."""
    if dest.exists():
        shutil.rmtree(dest)
    tmp = dest.parent / (dest.name + ".unpack")
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    with tarfile.open(archive) as tar:
        tar.extractall(tmp, filter="data")
    (tmp / "python").replace(dest)
    tmp.rmdir()
    return dest


def uv() -> str:
    found = shutil.which("uv") or shutil.which("uv", path=str(Path(sys.executable).parent))
    if not found:
        raise SystemExit("uv is needed for the build (https://astral.sh/uv, or pip install uv)")
    return found


def run(argv: list, **kw) -> None:
    log(" ".join(str(a) for a in argv))
    subprocess.run([str(a) for a in argv], check=True, **kw)


def wheels(out: Path, given: Path | None) -> list[Path]:
    """SMTV's three wheels: from `given` (the release workflow built them already), else built here."""
    v = version()
    if given is None:
        out.mkdir(parents=True, exist_ok=True)
        for old in out.glob("*.whl"):
            old.unlink()
        run([uv(), "build", "--all-packages", "--wheel", "--out-dir", out], cwd=REPO)
        given = out
    found = []
    for name in ("smtv", "smtv_core", "vodcut"):
        w = sorted(given.glob(f"{name}-{v}-*.whl"))
        if len(w) != 1:
            raise SystemExit(f"{given}: expected one wheel of {name} {v}, found {len(w)}")
        found.append(w[0])
    return found


def requirements(out: Path) -> Path:
    """Every dependency of smtv[vodcut] at the versions and hashes of uv.lock; SMTV's own packages are added as wheels.
    --locked: a lock that no longer matches pyproject.toml stops the build (a new dependency would be missing)."""
    run([uv(), "export", "--locked", "--no-dev", "--no-emit-workspace", "--package", "smtv", "--extra", "vodcut",
         "--format", "requirements-txt", "--no-header", "--output-file", out], cwd=REPO, stdout=subprocess.DEVNULL)
    return out


def install(site: Path, t: Target, reqs: Path, own: list[Path]) -> None:
    common = ["--target", site, "--python-platform", t.platform, "--python-version", PY, "--no-cache", "--link-mode", "copy"]
    env = {**os.environ, "MACOSX_DEPLOYMENT_TARGET": t.min_os} if t.system == "mac" else None
    run([uv(), "pip", "install", "--require-hashes", "--no-deps", "-r", reqs, *common], env=env)
    run([uv(), "pip", "install", "--no-deps", *own, *common], env=env)


def remove(paths) -> int:
    """Deletes what exists of `paths`; returns the bytes freed."""
    freed = 0
    for p in paths:
        if p.is_symlink() or p.is_file():
            freed += p.lstat().st_size
            p.unlink()
        elif p.is_dir():
            freed += sum(f.lstat().st_size for f in p.rglob("*") if f.is_file() or f.is_symlink())
            shutil.rmtree(p)
    return freed


def trim(python: Path, site: Path) -> int:
    freed = remove(python / p for p in TRIM_PYTHON)
    freed += remove(site / p for p in TRIM_SITE)
    freed += remove(p for p in python.rglob("__pycache__"))
    freed += remove(list(python.rglob("*.pdb")))      # Windows debug symbols: 80 MB nobody but a debugger reads
    return freed


def add_ffmpeg(python: Path, t: Target, cache: Path) -> Path:
    folder = python / "ffmpeg"
    folder.mkdir(exist_ok=True)
    for d in t.ffmpeg:
        archive = fetch(d, cache)
        with zipfile.ZipFile(archive) as z:
            for inside, name in d.members:
                with z.open(inside) as src, open(folder / name, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                if not name.endswith(".txt"):
                    (folder / name).chmod(0o755)
    builder = "Gyan Doshi (gyan.dev)" if t.system == "win" else "Martin Riedl (ffmpeg.martin-riedl.de)"
    config = t.ffmpeg[0].url.rsplit("/", 1)[0] + ("/versions.txt" if t.system == "mac" else "")
    (folder / "README.txt").write_text(FFMPEG_NOTE.format(version="9.1", builder=builder, config=config), encoding="utf-8")
    return folder


def compile_pyc(python: Path, t: Target) -> bool:
    """.pyc files made at build time: the app's folder may be read-only (macOS runs a downloaded app from a hidden copy
    until it is moved) and SMTV starts faster. Only when this build's Python runs here; otherwise Python makes them on
    the first start."""
    import platform
    here = (sys.platform, platform.machine())
    prefix: list = []
    if here == ("darwin", "arm64") and ("darwin", "x86_64") in t.can_run and Path("/usr/bin/arch").exists() \
            and subprocess.run(["/usr/bin/arch", "-x86_64", "/usr/bin/true"], capture_output=True).returncode == 0:
        prefix = ["/usr/bin/arch", "-x86_64"]        # the Intel build's Python under Rosetta
    elif here not in t.can_run:
        log(f"no .pyc: the {t.name} Python does not run on this computer")
        return False
    exe = python / ("python.exe" if t.system == "win" else f"bin/python{PY}")
    run([*prefix, exe, "-I", "-m", "compileall", "-q", "-j", "0", "--invalidation-mode", "checked-hash", "-x", r"[/\\](tests?|test_[^/\\]*)[/\\]", python], stdout=subprocess.DEVNULL)
    return True


MAC_SLICES = {"arm64": "mac-arm64", "x86_64": "mac-x64"}   # the processor → the Python built for it (TARGETS)
MAC_MIN_OS = "13.0"     # the oldest macOS the app opens on: Intel from 13; Apple silicon's own Python needs 14 (on 13 it
                        # takes the Intel one under Rosetta, launcher.c)


def compile_launcher(dest: Path) -> Path:
    """Contents/MacOS/SMTV from launcher.c, for arm64 and x86_64 in one file."""
    if not shutil.which("clang"):
        raise SystemExit("clang is missing: install Xcode's command line tools (xcode-select --install)")
    run(["clang", "-Wall", "-Wextra", "-Werror", "-O2", "-arch", "arm64", "-arch", "x86_64", "-mmacosx-version-min=11.0",
         "-o", dest, HERE / "launcher.c"])
    return dest


def share_identical(primary: Path, other: Path) -> int:
    """Every file of `other` that is byte for byte the same file in `primary` (Python code, fonts, the window's page)
    becomes a relative link to it: the .dmg carries it once. Returns the bytes saved."""
    saved = 0
    for f in sorted(other.rglob("*")):
        if f.is_symlink() or not f.is_file():
            continue
        twin = primary / f.relative_to(other)
        if twin.is_symlink() or not twin.is_file() or twin.stat().st_size != f.stat().st_size:
            continue
        if sha256(twin) != sha256(f):
            continue
        saved += f.stat().st_size
        f.unlink()
        f.symlink_to(os.path.relpath(twin, f.parent))
    return saved


def mac_info(v: str, min_os: str = MAC_MIN_OS) -> dict:
    system = launcher.System("darwin", Path.home(), "", {}, Path.home())
    info = launcher.mac_info(system)
    info["CFBundleShortVersionString"] = v.split(".dev")[0]
    info["CFBundleVersion"] = v
    info["LSMinimumSystemVersion"] = min_os
    info["LSArchitecturePriority"] = ["arm64", "x86_64"]     # native on both: never offered «Open using Rosetta»
    info[INFO_KIND] = "dmg"
    return info


def make_mac_app(pythons: dict[str, Path], out: Path, v: str) -> Path:
    """SMTV.app with one Python per processor: Resources/python-<arch>, MacOS/smtv-python-<arch> (a copy of that
    Python, so macOS counts the process as SMTV.app's, with its name and icon) and MacOS/SMTV, the universal launcher."""
    app = out / "SMTV.app"
    if app.exists():
        shutil.rmtree(app)
    (app / "Contents" / "MacOS").mkdir(parents=True)
    (app / "Contents" / "Resources").mkdir()
    for arch, python in pythons.items():
        py = app / "Contents" / "Resources" / f"python-{arch}"
        python.replace(py)
        shutil.copy2(py / "bin" / f"python{PY}", app / "Contents" / "MacOS" / f"smtv-python-{arch}")
    compile_launcher(app / "Contents" / "MacOS" / "SMTV")
    (app / "Contents" / "Info.plist").write_bytes(plistlib.dumps(mac_info(v)))
    (app / "Contents" / "Resources" / "smtv.icns").write_bytes(launcher.icns({
        "ic09": (ICONS / "icon-mac-512.png").read_bytes(), "ic10": (ICONS / "icon-mac-1024.png").read_bytes()}))
    if "arm64" in pythons and "x86_64" in pythons:
        res = app / "Contents" / "Resources"
        log(f"shared between the two Pythons: {share_identical(res / 'python-arm64', res / 'python-x86_64') / 1e6:.0f} MB")
    return app


def sign_adhoc(app: Path) -> None:
    """A local signature without a certificate (ad-hoc): Apple Silicon runs only signed code, and notifications need
    the app's identifier. It does not stop the «unidentified developer» warning: that goes with stage 30."""
    if not shutil.which("codesign"):
        raise SystemExit("codesign is missing: an unsigned app does not start on Apple Silicon (install Xcode's command line tools)")
    for python in sorted((app / "Contents" / "MacOS").glob("smtv-python-*")):
        run(["codesign", "--force", "--sign", "-", "--identifier", launcher.BUNDLE_ID, python])
    run(["codesign", "--force", "--sign", "-", app])


def make_dmg(app: Path, out: Path, name: str) -> Path:
    stage = out / "dmg"
    if stage.exists():
        shutil.rmtree(stage)
    stage.mkdir()
    shutil.copytree(app, stage / app.name, symlinks=True)
    (stage / "Applications").symlink_to("/Applications")
    shutil.copy2(HERE / "dmg-readme.txt", stage / "Как открыть — How to open.txt")
    dmg = out / name
    dmg.unlink(missing_ok=True)
    # ULMO: LZMA, the smallest image format (macOS 10.15 and newer)
    run(["hdiutil", "create", "-volname", "SMTV", "-srcfolder", stage, "-fs", "HFS+", "-format", "ULMO", "-ov", dmg],
        stdout=subprocess.DEVNULL)
    shutil.rmtree(stage)
    return dmg


def make_win_folder(python: Path, out: Path) -> Path:
    """SMTV/: the Python with everything inside, SMTV.exe (Python's windowless program under SMTV's name, so Task
    Manager shows SMTV; a double click on it opens the window: double_click.py) and the icon. The installer copies this
    folder. No script to start it: Smart App Control blocks a downloaded .cmd, and any program of our own."""
    folder = out / "SMTV"
    if folder.exists():
        shutil.rmtree(folder)
    python.replace(folder)
    shutil.copy2(folder / "pythonw.exe", folder / "SMTV.exe")
    (folder / "smtv.ico").write_bytes(launcher.ico((ICONS / "icon-256.png").read_bytes()))
    shutil.copy2(HERE / "double_click.py", folder / "Lib" / "site-packages" / "sitecustomize.py")
    return folder


def zip_folder(folder: Path, dest: Path, kind: str) -> Path:
    """The ZIP without installation: the same folder, marked "zip" (it does not update from the window)."""
    dest.unlink(missing_ok=True)
    if not (folder / KIND_MARKER).is_file():
        raise SystemExit(f"{folder / KIND_MARKER} is missing: the ZIP would not know it is the ZIP")
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(folder.rglob("*")):
            if f.is_file():
                arc = Path("SMTV") / f.relative_to(folder)
                if f.name == KIND_MARKER and f.parent == folder:
                    z.writestr(str(arc).replace("\\", "/"), kind + "\n")
                else:
                    z.write(f, str(arc).replace("\\", "/"))
    return dest


def inno_setup(folder: Path, out: Path, v: str) -> Path | None:
    iscc = shutil.which("iscc") or next((str(p) for p in (Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Inno Setup 6" / "ISCC.exe",
                                                          Path(os.environ.get("LOCALAPPDATA", "C:/")) / "Programs" / "Inno Setup 6" / "ISCC.exe")
                                          if p.is_file()), None)
    if not iscc:
        log("no Inno Setup here: the .exe installer is made on Windows (GitHub Actions or `winget install JRSoftware.InnoSetup`)")
        return None
    run([iscc, "/Qp", f"/DAppVersion={v}", f"/DSourceDir={folder}", f"/DOutputDir={out}", HERE / "smtv.iss"])
    return out / f"SMTV-{v}-windows-x64-setup.exe"


def prepare(t: Target, work: Path, cache: Path, own: list[Path], require_pyc: bool) -> Path:
    """One Python with SMTV, its dependencies and ffmpeg inside, trimmed and compiled: work/python."""
    work.mkdir(parents=True, exist_ok=True)
    python = unpack_python(fetch(t.python, cache), work / "python")
    site = site_packages(python, t)
    install(site, t, requirements(work / "requirements.txt"), own)
    log(f"{t.name}: trimmed {trim(python, site) / 1e6:.0f} MB")
    add_ffmpeg(python, t, cache)
    (python / KIND_MARKER).write_text(("dmg" if t.system == "mac" else "exe") + "\n", encoding="utf-8")
    if not compile_pyc(python, t) and require_pyc:
        raise SystemExit(f"the {t.name} Python does not run here, so no .pyc and no check: build it where it runs")
    return python


def build(target: str, out: Path, cache: Path, given_wheels: Path | None = None, require_pyc: bool = False) -> list[Path]:
    v = version()
    made: list[Path] = []
    if target == "mac":
        work = out / "mac"
        own = wheels(work / "wheels", given_wheels)
        pythons = {arch: prepare(TARGETS[name], work / name, cache, own, require_pyc) for arch, name in MAC_SLICES.items()}
        app = make_mac_app(pythons, work, v)
        sign_adhoc(app)
        made.append(make_dmg(app, out, f"SMTV-{v}-mac.dmg"))
    else:
        t = TARGETS[target]
        work = out / t.name
        python = prepare(t, work, cache, wheels(work / "wheels", given_wheels), require_pyc)
        folder = make_win_folder(python, work)
        made.append(zip_folder(folder, out / f"SMTV-{v}-windows-x64.zip", "zip"))
        setup = inno_setup(folder, out, v)
        if setup:
            made.append(setup)
    for f in made:
        log(f"{f}  {f.stat().st_size / 1e6:.0f} MB  sha256 {sha256(f)}")
    return made


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):   # a Windows runner's console is cp1252: no «→», and print would fail
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("target", choices=("mac", "win-x64"))
    ap.add_argument("--out", type=Path, default=REPO / "build" / "app")
    ap.add_argument("--cache", type=Path, default=REPO / "build" / "app-cache", help="downloads, kept between builds")
    ap.add_argument("--wheels", type=Path, help="a folder with SMTV's wheels already built (the release workflow)")
    ap.add_argument("--release", action="store_true", help="for a release: the .pyc must be made and, on Windows, the installer too")
    a = ap.parse_args(argv)
    if a.target == "mac" and sys.platform != "darwin":
        raise SystemExit("SMTV.app and the .dmg are made on a Mac (hdiutil, codesign)")
    made = build(a.target, a.out.resolve(), a.cache.resolve(), a.wheels.resolve() if a.wheels else None, require_pyc=a.release)
    if a.release and a.target == "win-x64" and not any(f.suffix == ".exe" for f in made):
        raise SystemExit("--release: no Inno Setup here, so no installer was made")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
