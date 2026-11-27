"""Checks a built desktop app without opening its window (install/app/build.py; the release workflow runs it too):

    python install/app/smoke.py /Volumes/SMTV/SMTV.app                  # this Mac's own Python (arm64 on Apple silicon)
    python install/app/smoke.py /Volumes/SMTV/SMTV.app --arch x86_64    # the Intel Python (under Rosetta on Apple silicon)
    python install/app/smoke.py "%LOCALAPPDATA%\\Programs\\SMTV"          # after the installer, on Windows

Runs the app's own Python with a clean environment and an empty SMTV folder, and checks that:
- the heavy libraries load (speech, sound, the window's bridge) and the kind of install is the app's (dmg, exe, zip);
- the ffmpeg inside the app is the one SMTV picks, and it burns captions (libass) with SMTV's caption font;
- the Windows app's Whisper engine (left out of it: smtv_core.parts) downloads from PyPI, matches its hashes and loads;
- `smtv doctor` runs: nothing but the AI connection and the speech model is missing on a fresh computer, and the
  speech model is offered for download, not bundled;
- `smtv serve` answers /api/hello with its version and keeps the page closed without the launch key;
- on Windows, ClipIt.exe (the launcher built from install/app/launcher_win.c) opened with nothing after it (a double
  click) starts `app\\pythonw.exe -m smtv app` (checked without opening the window: SMTV_LAUNCH_CHECK), and the page's
  server runs through it;
- on Windows, .NET loads (pythonnet); the folder's top holds only ClipIt.exe with its .config (which lets .NET load files
  Explorer marked as downloaded: a ZIP opened with "Extract All"), the DLLs, the ._pth, a how-to text and app/.
Exits 1 with the failed checks listed. Prints nothing secret: the folder is a fresh temporary one.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

PROBE = r"""
import json, sys
import onnxruntime, numpy, onnx_asr, webview, fontTools, jsonschema, huggingface_hub
from smtv_core import parts
if not parts.manifest(parts.WHISPER):          # inside the app (the Mac); the Windows app downloads it (PART below)
    import av, ctranslate2, faster_whisper
if sys.platform == "win32":
    import clr  # noqa: F401 — pythonnet: .NET, the bridge to the window; fails on files marked as downloaded
from smtv import updates
from smtv_core import checks, paths
from smtv_core.render.fonts import FONTS_DIR
if not list(FONTS_DIR.glob("*.woff")):
    raise SystemExit(f"no caption font in {FONTS_DIR}")
import platform, subprocess, time
started = time.monotonic()
folder, captions = checks.find_ffmpeg()
took = time.monotonic() - started
again = checks.has_libass(folder) if folder and not captions else None   # a slow first start, or no libass at all
translated = subprocess.run(["sysctl", "-n", "sysctl.proc_translated"], capture_output=True, text=True).stdout.strip() \
    if sys.platform == "darwin" else ""
print(json.dumps({"machine": platform.machine(), "rosetta": translated == "1", "prefix": sys.prefix, "app": str(paths.app_folder()), "version": sys.version.split()[0], "kind": updates.install_kind(),
                  "ffmpeg": folder, "libass": captions, "libass_s": round(took, 1), "libass_again": again, "fonts": str(FONTS_DIR)}))
"""

PART = r"""
import json
from smtv_core import parts
from smtv_core.asr import catalog
spec = parts.manifest(parts.WHISPER)
where = parts.install(parts.WHISPER)
assert catalog.package_ready(catalog.WHISPER_M), "faster-whisper is not importable after the download"
import av, ctranslate2, faster_whisper, tokenizers
print(json.dumps({"mb": parts.size_mb(spec), "folder": str(where), "versions": [ctranslate2.__version__, av.__version__]}))
"""

ASS = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Montserrat Black,90,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,4,0,2,10,10,200,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,ПРИВЕТ SMTV
"""


def native_arch() -> str:
    """This Mac's processor from the hardware (under Rosetta `uname` says x86_64 even on Apple silicon)."""
    r = subprocess.run(["sysctl", "-n", "hw.optional.arm64"], capture_output=True, text=True)
    return "arm64" if r.stdout.strip() == "1" else "x86_64"


def app_python(app: Path, arch: str = "arm64") -> tuple[list[str], dict[str, str]]:
    """The command that starts one of the app's Pythons and what it needs in its environment (what the launcher sets).
    The Intel one runs under Rosetta on Apple silicon: `arch -x86_64` makes sure of it."""
    if app.suffix == ".app":
        contents = app / "Contents"
        return [*(["/usr/bin/arch", "-x86_64"] if arch == "x86_64" else ["/usr/bin/arch", "-arm64"]),
                str(contents / "MacOS" / f"smtv-python-{arch}")], \
            {"PYTHONHOME": str(contents / "Resources" / f"python-{arch}"), "PYTHONNOUSERSITE": "1"}
    return [str(app / "ClipIt.exe")], {"PYTHONNOUSERSITE": "1"}   # the launcher hands arguments to pythonw.exe and waits; prints into a pipe


def mac_bundle(app: Path) -> list[str]:
    """SMTV.app as macOS sees it: the signature seals everything (Apple Silicon kills broken code without a word); the
    launcher Finder starts is one program for both processors, and it picks this Mac's own Python by the hardware even
    when it is itself run under Rosetta."""
    out = []
    v = subprocess.run(["codesign", "--verify", "--deep", "--strict", str(app)], capture_output=True, text=True)
    if v.returncode != 0:
        out.append(f"codesign --verify: {v.stderr.strip()[-500:]}")
    main = app / "Contents" / "MacOS" / "SMTV"
    archs = subprocess.run(["lipo", "-archs", str(main)], capture_output=True, text=True).stdout.split()
    if sorted(archs) != ["arm64", "x86_64"]:
        out.append(f"the launcher is built for {archs}, not for arm64 and x86_64")
    want = native_arch()
    for how in ([], ["/usr/bin/arch", "-x86_64"]):
        r = subprocess.run([*how, str(main)], env={"SMTV_LAUNCHER_DRY": "1", "HOME": os.environ.get("HOME", "/tmp")},
                           capture_output=True, text=True)
        picked = r.stdout.split()[:1]
        if picked != [want]:
            out.append(f"the launcher{' under Rosetta' if how else ''} picks {picked}, this Mac is {want}: {r.stderr.strip()}")
    return out





def clean_env(home: Path, extra: dict[str, str]) -> dict[str, str]:
    """Only what a program needs: no PYTHON* or PATH of the build machine (the app must find its own ffmpeg)."""
    keep = ("SYSTEMROOT", "SystemRoot", "WINDIR", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA", "APPDATA", "HOME",
            "HOMEDRIVE", "HOMEPATH", "USERNAME", "LANG", "COMSPEC", "PROGRAMDATA")
    env = {k: v for k, v in os.environ.items() if k in keep}
    env["PATH"] = os.pathsep.join([os.environ.get("SYSTEMROOT", r"C:\Windows") + r"\System32"]) if os.name == "nt" \
        else "/usr/bin:/bin:/usr/sbin:/sbin"
    env.update(extra)
    env.update({"SMTV_HOME": str(home), "SMTV_NO_SHORTCUT": "1", "PYTHONIOENCODING": "utf-8"})
    return env


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def hello(port: int, timeout_s: float) -> dict | None:
    end = time.monotonic() + timeout_s
    while time.monotonic() < end:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/hello", timeout=3) as r:   # noqa: S310 — local
                return json.loads(r.read())
        except (OSError, ValueError):
            time.sleep(1)
    return None


def page_status(port: int) -> int:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5) as r:   # noqa: S310 — local
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except OSError:
        return 0


WIN_LIMIT_MB = 320      # the Windows app unpacked: 549 MB in 0.1.0, about 290 since 0.1.1; it must not creep back


LEFT_OUT = ("av", "ctranslate2", "faster-whisper", "tokenizers", "hf-xet")   # build.WHISPER_PART + build.NOT_IN_APPS


def unexpected_pip_check(out: str) -> list[str]:
    """pip check's complaints but the packages the build leaves out on purpose (downloaded on first use, or not needed)."""
    return [line for line in out.strip().splitlines()
            if line.strip() and not any(f"requires {name}," in line.lower() for name in LEFT_OUT)]


def win_size(app: Path, limit_mb: int = WIN_LIMIT_MB) -> list[str]:
    total = sum(f.stat().st_size for f in app.rglob("*") if f.is_file()) / 1e6
    print(f"the app unpacked: {total:.0f} MB (the limit {limit_mb} MB)")
    if total > limit_mb:
        return [f"the Windows app is {total:.0f} MB unpacked, over its limit of {limit_mb} MB: find what grew in "
                "build.py's size list, or raise WIN_LIMIT_MB in smoke.py and say why in the pull request"]
    return []


LAUNCHER_MARK = "SMTV_LAUNCH_CHECK".encode("utf-16-le")     # a string only launcher_win.c has, as Windows text
WIN_TOP = {"ClipIt.exe", "ClipIt.exe.config", "app"}     # and the DLLs, the ._pth and the how-to text (build.make_win_folder)


def win_layout(app: Path) -> list[str]:
    """The Windows folder as a person sees it: one program to start, a text that says how, app/ with the rest; the
    .config that lets .NET load files Explorer marked as downloaded (without it the window does not start)."""
    failed = []
    names = {f.name for f in app.iterdir() if not f.name.lower().startswith("unins")}   # the installer's uninstaller
    other = sorted(n for n in names - WIN_TOP if not n.lower().endswith((".dll", "._pth", ".txt")))
    if not WIN_TOP <= names or other or sum(n.lower().endswith("._pth") for n in names) != 1 \
            or sum(n.endswith(".txt") for n in names) != 1:
        failed.append(f"the top of {app} is not ClipIt.exe, its .config, the DLLs, one ._pth, one text and app: "
                      f"{sorted(names)} (build the app again with build.py)")
    exe, python = app / "ClipIt.exe", app / "app" / "pythonw.exe"
    if exe.is_file():
        body = exe.read_bytes()
        if not python.is_file():
            failed.append(f"{python} is missing: ClipIt.exe starts it")
        elif body == python.read_bytes() or LAUNCHER_MARK not in body:
            failed.append(f"{exe} is not the launcher built from install/app/launcher_win.c (a copy of pythonw.exe?): "
                          "build the app again with build.py")
    config = app / "ClipIt.exe.config"
    if config.is_file() and 'loadFromRemoteSources enabled="true"' not in config.read_text(encoding="utf-8", errors="replace"):
        failed.append(f"{config} does not allow loadFromRemoteSources: build the app again with build.py")
    return failed


def double_click(smtv_exe: Path, env: dict[str, str], tmp: Path) -> list[str]:
    """ClipIt.exe with nothing after it, as Explorer starts it: it must ask for app\\pythonw.exe -m smtv app and end at
    once (launcher_win.c writes the command into SMTV_LAUNCH_CHECK instead of opening the window)."""
    check = tmp / "double-click.txt"
    try:
        r = subprocess.run([str(smtv_exe)], env={**env, "SMTV_LAUNCH_CHECK": str(check)}, capture_output=True,
                           timeout=60, cwd=tmp, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        return ["a double click on ClipIt.exe did not end within 60 s"]
    except OSError as e:
        return [f"ClipIt.exe did not start: {e}"]
    if not check.is_file():
        return [f"a double click on ClipIt.exe starts nothing (exit {r.returncode}): is it launcher_win.c's program?"]
    started = check.read_text(encoding="utf-8").strip()
    want = f'"{smtv_exe.parent / "app" / "pythonw.exe"}" -m smtv app'
    if started.lower() != want.lower():
        return [f"a double click on ClipIt.exe would start {started}, not {want}"]
    print(f"double click on ClipIt.exe: starts {started}")
    return []


def stop(server: subprocess.Popen) -> None:
    """End the page's server. On Windows ClipIt.exe waits for pythonw.exe, which is the one that has to end: the whole
    tree, or the port stays taken."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(server.pid)], capture_output=True)
    else:
        server.terminate()


def smoke(app: Path, kinds: tuple[str, ...], arch: str = "arm64") -> list[str]:
    failed: list[str] = []
    cmd, extra = app_python(app, arch)
    with tempfile.TemporaryDirectory(prefix="smtv-smoke-") as tmp:
        home = Path(tmp) / "home"
        home.mkdir()
        env = clean_env(home, extra)

        def py(*args: str, timeout: float = 300) -> subprocess.CompletedProcess:
            return subprocess.run([*cmd, *args], env=env, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=timeout, cwd=tmp)

        try:
            p = py("-c", PROBE)
        except (OSError, subprocess.TimeoutExpired) as e:
            return [f"the app's Python did not start: {type(e).__name__}: {e}"]
        if p.returncode != 0:
            return [f"the app's Python did not load SMTV and its libraries:\n{p.stderr[-2000:]}"]
        info = json.loads(p.stdout.strip().splitlines()[-1])
        if app.suffix == ".app":
            failed += mac_bundle(app)
        deps = py("-m", "pip", "check")
        wrong = unexpected_pip_check(deps.stdout)
        if deps.returncode != 0 and wrong:   # a dependency missing or at a version another one cannot use
            failed.append("pip check: " + "\n".join(wrong)[-1500:])
        print(f"Python {info['version']} as {info['machine']}{' under Rosetta' if info['rosetta'] else ''}, "
              f"kind {info['kind']}, ffmpeg {info['ffmpeg']}")
        if app.suffix == ".app":
            if info["machine"] != arch:
                failed.append(f"the {arch} Python runs as {info['machine']}")
            if arch == "arm64" and info["rosetta"]:
                failed.append("the Apple silicon Python runs under Rosetta")
        if info["kind"] not in kinds:
            failed.append(f"kind of install {info['kind']!r}, expected one of {kinds}")
        if not info["ffmpeg"] or Path(info["ffmpeg"]).resolve() != (Path(info["app"]) / "ffmpeg").resolve():
            failed.append(f"SMTV picked ffmpeg in {info['ffmpeg']}, not the one inside the app")
        if not info["libass"]:
            failed.append(f"the ffmpeg SMTV picked cannot burn captions (no libass): finding it took {info['libass_s']} s, "
                          f"asked once more it {'has' if info['libass_again'] else 'still has no'} libass")

        if info["ffmpeg"]:
            ffmpeg = str(Path(info["ffmpeg"]) / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg"))
            ass = Path(tmp) / "t.ass"
            ass.write_text(ASS, encoding="utf-8")
            out = Path(tmp) / "t.mp4"
            fonts = info["fonts"].replace("\\", "/").replace(":", "\\:")
            r = subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                                "color=c=blue:s=1080x1920:d=1", "-vf", f"ass=t.ass:fontsdir='{fonts}'", "-c:v", "libx264",
                                str(out)], env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=120, cwd=tmp)
            if r.returncode != 0 or not out.is_file() or out.stat().st_size < 1000:
                failed.append(f"ffmpeg did not burn a caption with libx264: {r.stderr[-800:]}")

        part = py("-c", "from smtv_core import parts; print(bool(parts.manifest(parts.WHISPER)))")
        if part.stdout.strip() == "True":     # the Windows app: Whisper's engine on first use, from PyPI, checked
            got = py("-c", PART, timeout=900)
            if got.returncode != 0:
                failed.append(f"Whisper's engine did not download or load:\n{got.stderr[-1500:]}")
            else:
                print(f"Whisper's engine on first use: {got.stdout.strip().splitlines()[-1]}")

        d = py("-m", "smtv", "doctor")
        print(d.stdout)
        if not any(line.split()[:2] == ["ok", "ffmpeg"] for line in d.stdout.splitlines()):
            failed.append("smtv doctor printed no «ok ffmpeg» row: its output changed or ffmpeg is not found")
        rows = [line for line in d.stdout.splitlines() if line.startswith("  FAIL")]
        unexpected = [r for r in rows if not r.split()[1:2] == ["Model"]]
        if unexpected:
            failed.append("smtv doctor fails on a fresh computer: " + "; ".join(unexpected))
        if "Speech model" not in d.stdout or "not downloaded" not in d.stdout:
            failed.append("smtv doctor does not offer the speech model for download")

        smtv_exe = app / "ClipIt.exe" if app.suffix != ".app" else None
        if smtv_exe and smtv_exe.is_file():
            failed += double_click(smtv_exe, env, Path(tmp))
            failed += win_layout(app)
            failed += win_size(app)
        port = free_port()
        serving = [str(smtv_exe)] if smtv_exe and smtv_exe.is_file() else cmd     # what a double click runs
        server = subprocess.Popen([*serving, "-m", "smtv", "serve", "--no-browser", "--port", str(port)], env=env, cwd=tmp,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                  errors="replace")
        try:
            h = hello(port, 90)

            if not h or h.get("app") != "smtv" or "vodcut" not in (h.get("tools") or []):
                failed.append(f"smtv serve: /api/hello answered {h}")
            else:
                print(f"/api/hello: {h}")
            status = page_status(port)
            if status != 403:
                failed.append(f"the page without the launch key answered {status}, expected 403")
        finally:
            stop(server)
            try:
                out, _ = server.communicate(timeout=20)
            except subprocess.TimeoutExpired:
                server.kill()
                out, _ = server.communicate()
            if failed:
                print("smtv serve printed:\n" + "\n".join("    " + line for line in out[-3000:].splitlines()))
    return failed


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):   # a Windows runner's console is cp1252: no «→», and print would fail
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("app", type=Path, help="SMTV.app, or the folder of the Windows app")
    ap.add_argument("--arch", choices=("arm64", "x86_64"), help="SMTV.app: which of its Pythons (default: this Mac's own)")
    ap.add_argument("--kind", action="append", help="the expected kind of install (default: dmg for SMTV.app, exe or zip)")
    a = ap.parse_args(argv)
    kinds = tuple(a.kind or (("dmg",) if a.app.suffix == ".app" else ("exe", "zip")))
    arch = a.arch or (native_arch() if a.app.suffix == ".app" else "x86_64")
    failed = smoke(a.app.resolve(), kinds, arch)
    # on stdout, right under this run's own output: on stderr they landed next to the other Python's run in CI logs
    for f in failed:
        print(f"FAILED: {f}")
    print(f"smoke ({arch if a.app.suffix == '.app' else 'windows'}): " + ("ok" if not failed else f"{len(failed)} failed"),
          flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
