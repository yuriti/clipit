"""System checks shared by every tool: what is missing on this computer, and how to fix it (stage 24).

A check that fails blocks new requests (the window and the API refuse to start one); a warning does not. A check that can
be fixed carries a `Recipe`: a program SMTV itself knows for this system, run without a shell, never a command from the
network or from settings. What needs administrator rights is never run silently: SMTV opens a terminal with the command
and the person runs it there. The window shows the whole command and a link to its official page before anything runs.
"""
from __future__ import annotations

import os
import platform
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from . import paths
from .settings import Settings, get_secret, secrets_backend

OK, WARN, FAIL = "ok", "warn", "fail"

# What the window can do for a check besides a recipe: open a place of its own, or act on SMTV's folder
SIGN_IN, PROVIDERS, SPEECH, OPEN_FOLDER, CLEAR_CACHE = "sign_in", "providers", "speech", "open_folder", "clear_cache"
ACTIONS = (SIGN_IN, PROVIDERS, SPEECH, OPEN_FOLDER, CLEAR_CACHE)


WINGET_CONSENT = "Запуская установку, вы принимаете условия Microsoft и автора пакета (winget)."


@dataclass
class Recipe:
    """One fix built into SMTV: a program and its arguments, run as is (no shell, no substitutions); its output goes to
    the window line by line, and «Stop» stops it. `admin`: needs administrator rights, so SMTV only opens a terminal with
    the command. `links`: the official pages of what runs («What is this?»)."""
    id: str
    argv: list[str] = field(default_factory=list)
    shown: str = ""               # what the window shows as what will run; default: the command line
    links: tuple[str, ...] = ()
    admin: bool = False

    def line(self) -> str:
        if self.shown:
            return self.shown
        return subprocess.list2cmdline(self.argv) if sys.platform == "win32" else shlex.join(self.argv)

    def consent(self) -> str | None:
        """What the person agrees to by pressing «Исправить»: winget runs with --accept-*-agreements (decision 11)."""
        argv = [a.lower() for a in self.argv]
        if any(a.endswith(("winget", "winget.exe")) for a in argv[:1]) or "--accept-package-agreements" in argv:
            return WINGET_CONSENT
        return None

    def public(self) -> dict:
        return {"id": self.id, "kind": "terminal" if self.admin else "command", "command": self.line(), "links": list(self.links),
                "consent": self.consent()}


@dataclass
class Check:
    name: str
    status: str          # ok | warn | fail
    detail: str
    fix: str = ""        # one concrete step, shown when status is not ok
    id: str = ""         # stable: the window and the API name a check by it
    recipe: Recipe | None = None
    actions: tuple[str, ...] = ()

    def public(self) -> dict:
        """The check for the window: the recipe as text, never its code."""
        bad = self.status != OK
        return {"id": self.id or self.name, "name": self.name, "status": self.status, "detail": self.detail, "fix": self.fix,
                "recipe": self.recipe.public() if self.recipe and bad else None, "actions": list(self.actions) if bad else []}


def _run(argv: list[str], timeout: float = 15) -> str | None:
    """A program's output, or None when it is missing, fails or hangs. `proc.run`: UTF-8, no console window on Windows,
    the whole tree stopped at the limit."""
    from . import proc
    try:
        done = proc.run(argv, timeout, what=Path(argv[0]).name)
    except (OSError, proc.TimedOut):
        return None
    return (done.stdout or "") + (done.stderr or "") if done.returncode == 0 else None


def in_docker() -> bool:
    return os.environ.get("SMTV_DOCKER", "").strip() == "1"


# --- ffmpeg -------------------------------------------------------------------------------------------------------

def _exe(name: str) -> str:
    return name + ".exe" if sys.platform == "win32" else name


APP_FFMPEG = "ffmpeg"   # the desktop apps (install/app/build.py) carry their ffmpeg in this folder beside their Python


def _ffmpeg_dirs() -> tuple[list[Path], list[Path]]:
    """Folders with an ffmpeg besides PATH: (looked at before PATH, after it). Before: SMTV's own `bin` (a person's own
    build wins), the ffmpeg inside the desktop app, Homebrew's ffmpeg-full (keg-only: brew leaves it off PATH when plain
    ffmpeg is there) and winget's links (a running SMTV does not see a PATH changed after it started). After: Homebrew's
    own folders (an SMTV started from an icon has a short PATH)."""
    before, after = [paths.home() / "bin", Path(sys.prefix) / APP_FFMPEG], []
    if sys.platform == "darwin":
        before += [Path("/opt/homebrew/opt/ffmpeg-full/bin"), Path("/usr/local/opt/ffmpeg-full/bin")]
        after += [Path("/opt/homebrew/bin"), Path("/usr/local/bin")]
    elif sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        before.append(Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "WinGet" / "Links")
    return before, after


def _ffmpeg_candidates() -> list[str]:
    """Folders that hold both ffmpeg and ffprobe, the preferred first."""
    before, after = _ffmpeg_dirs()
    found = shutil.which("ffmpeg")
    on_path = [Path(found).parent] if found and shutil.which("ffprobe") else []
    out: list[str] = []
    for d in [*before, *on_path, *after]:
        if (d / _exe("ffmpeg")).is_file() and (d / _exe("ffprobe")).is_file() and str(d) not in out:
            out.append(str(d))
    return out


def has_libass(folder: str) -> bool:
    filters = _run([str(Path(folder) / _exe("ffmpeg")), "-hide_banner", "-filters"]) or ""
    return any(line.split()[1:2] == ["ass"] for line in filters.splitlines() if line.strip())


def find_ffmpeg() -> tuple[str | None, bool]:
    """(the folder of the ffmpeg SMTV uses, whether it burns captions): the first that has libass, else the first."""
    folders = _ffmpeg_candidates()
    for folder in folders:
        if has_libass(folder):
            return folder, True
    return (folders[0], False) if folders else (None, False)


def use_ffmpeg() -> str | None:
    """Puts the chosen ffmpeg's folder first on PATH: this process and every job it starts run that one."""
    folder, _ = find_ffmpeg()
    if folder:
        parts = [p for p in os.environ.get("PATH", "").split(os.pathsep) if p]
        if not parts or parts[0] != folder:
            os.environ["PATH"] = os.pathsep.join([folder, *[p for p in parts if p != folder]])
    return folder


def find_brew() -> str | None:
    found = shutil.which("brew")
    if found:
        return found
    return next((str(p) for p in (Path("/opt/homebrew/bin/brew"), Path("/usr/local/bin/brew")) if p.is_file()), None)


def find_winget() -> str | None:
    found = shutil.which("winget")
    if found:
        return found
    local = os.environ.get("LOCALAPPDATA")
    path = Path(local) / "Microsoft" / "WindowsApps" / "winget.exe" if local else None
    return str(path) if path and path.is_file() else None


HOMEBREW_PAGE = "https://brew.sh"
HOMEBREW_INSTALL = '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
WINGET_PAGE = "https://learn.microsoft.com/windows/package-manager/winget/"
APP_INSTALLER = "https://apps.microsoft.com/detail/9NBLGGH4NNS1"
FFMPEG_PAGE = "https://ffmpeg.org/download.html"


def ffmpeg_recipe() -> Recipe | None:
    """ffmpeg with libass for this system, without administrator rights where it can be: Homebrew's ffmpeg-full on a Mac,
    the full Gyan build through winget on Windows (both into the person's own folders); a Linux package manager needs
    sudo, so it goes to a terminal. A Mac without Homebrew: Homebrew's own installer (brew.sh), in a terminal. None in
    Docker (the image has its ffmpeg) or when this system has no known way."""
    if in_docker():
        return None
    if sys.platform == "darwin":
        brew = find_brew()
        if brew:
            return Recipe("ffmpeg", [brew, "install", "ffmpeg-full"], links=("https://formulae.brew.sh/formula/ffmpeg-full", FFMPEG_PAGE))
        return Recipe("homebrew", ["/bin/bash", "-c", HOMEBREW_INSTALL], shown=HOMEBREW_INSTALL, links=(HOMEBREW_PAGE,), admin=True)
    if sys.platform == "win32":
        winget = find_winget()
        if not winget:
            return None
        return Recipe("ffmpeg", [winget, "install", "--id", "Gyan.FFmpeg", "--exact", "--source", "winget",
                                 "--accept-package-agreements", "--accept-source-agreements", "--disable-interactivity"],
                      links=(WINGET_PAGE, "https://www.gyan.dev/ffmpeg/builds/", FFMPEG_PAGE))
    for manager, argv in (("apt-get", ["sudo", "apt-get", "install", "-y", "ffmpeg"]), ("dnf", ["sudo", "dnf", "install", "-y", "ffmpeg"]),
                          ("pacman", ["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"])):
        if shutil.which(manager):
            return Recipe("ffmpeg", argv, links=(FFMPEG_PAGE,), admin=True)
    return None


def ffmpeg_install_hint() -> str:
    recipe = ffmpeg_recipe()
    if recipe and recipe.id == "ffmpeg":
        return recipe.line()
    if sys.platform == "win32":
        return f"install App Installer (winget) from the Microsoft Store: {APP_INSTALLER}, then: winget install Gyan.FFmpeg"
    if sys.platform == "darwin":
        return f"install Homebrew ({HOMEBREW_PAGE}), then: brew install ffmpeg-full"
    return f"install ffmpeg with your system's package manager: {FFMPEG_PAGE}"


def check_ffmpeg() -> list[Check]:
    folder, has_ass = find_ffmpeg()
    if not folder:
        return [Check("ffmpeg", FAIL, "ffmpeg or ffprobe not found", ffmpeg_install_hint(), id="ffmpeg", recipe=ffmpeg_recipe())]
    version = (_run([str(Path(folder) / _exe("ffmpeg")), "-hide_banner", "-version"]) or "").splitlines()
    out = [Check("ffmpeg", OK, version[0] if version else "found", id="ffmpeg")]
    if has_ass:
        out.append(Check("Captions (libass)", OK, "ffmpeg can burn captions", id="libass"))
    else:
        out.append(Check("Captions (libass)", FAIL, "this ffmpeg build cannot burn captions", ffmpeg_install_hint(), id="libass",
                         recipe=ffmpeg_recipe()))
    return out


# --- this computer ------------------------------------------------------------------------------------------------

MIN_FREE_GB = 5          # below this a request does not fit at all: blocks
ROOMY_GB = 20            # a 6-hour stream: its sound and pieces of video, the speech models, the clips and the recap


def check_disk(minimum_gb: float = MIN_FREE_GB, roomy_gb: float = ROOMY_GB) -> Check:
    target = paths.home()
    probe = target if target.exists() else next((p for p in target.parents if p.exists()), target.anchor)
    free_gb = shutil.disk_usage(probe).free / 1e9
    status = OK if free_gb >= roomy_gb else WARN if free_gb >= minimum_gb else FAIL
    fix = "" if status == OK else (f"A 6-hour stream needs about {roomy_gb:.0f} GB while it is processed (its sound, video pieces, "
                                    "speech models, clips): free up space, clear SMTV's cache, or set SMTV_HOME to another drive")
    return Check("Free space", status, f"{free_gb:.0f} GB free for {target}", fix, id="disk", actions=(OPEN_FOLDER, CLEAR_CACHE))


def check_gpu() -> Check:
    """Only for information: everything runs on the processor too."""
    out = _run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"]) if shutil.which("nvidia-smi") else None
    if out:
        return Check("Graphics card", OK, out.strip().splitlines()[0] + " (used to speed things up)", id="gpu")
    return Check("Graphics card", OK, "none found: everything runs on the processor, just slower", id="gpu")


MIN_MACOS = (13, 0)        # the scientific wheels SMTV installs (onnxruntime, numpy) are built for macOS 13 and newer
MIN_WINDOWS_BUILD = 17763  # Windows 10 1809: the first with winget


def _version(text: str) -> tuple[int, ...]:
    out = []
    for part in text.split("."):
        if not part.isdigit():
            break
        out.append(int(part))
    return tuple(out)


def check_system() -> Check:
    """The system's version. An older one cannot be fixed from SMTV: the row says what is needed."""
    if sys.platform == "darwin":
        version = platform.mac_ver()[0]
        if version and _version(version) < MIN_MACOS:
            need = ".".join(map(str, MIN_MACOS))
            return Check("System", FAIL, f"macOS {version}", f"SMTV needs macOS {need} or newer: update macOS in System Settings", id="os")
        return Check("System", OK, f"macOS {version or '(version unknown)'}", id="os")
    if sys.platform == "win32":
        try:
            build = sys.getwindowsversion().build
        except AttributeError:
            build = 0
        name = f"Windows {platform.release()} (build {build})"
        if build and build < MIN_WINDOWS_BUILD:
            return Check("System", FAIL, name, "SMTV needs Windows 10 version 1809 or newer: update Windows", id="os")
        return Check("System", OK, name, id="os")
    try:
        name = platform.freedesktop_os_release().get("PRETTY_NAME", "Linux")
    except OSError:
        name = "Linux"
    return Check("System", OK, f"{name} ({platform.machine()})", id="os")


# --- the model ----------------------------------------------------------------------------------------------------

# verify(provider) -> True: the key works; False: refused; None: not known now (no network, a CLI, no key to check)
Verify = Callable[[object], tuple[bool | None, str]]


def _usable(p) -> tuple[bool, str]:
    """Can this provider answer: its CLI is installed, or its key is saved (a custom server may need none)."""
    if p.kind == "codex":
        return (bool(shutil.which(p.bin or "codex")), "Codex CLI not found")
    if p.kind == "claude_code":
        return (bool(shutil.which(p.bin or "claude")), "Claude Code not found")
    if p.kind == "streammoment":
        from .account import signed_in
        return (signed_in() is not None, "not signed in")
    if not p.needs_key():          # a local server or an own address: no key needed (stage 20)
        return True, ""
    try:
        env = p.table_key() == p.kind and bool(os.environ.get(f"SMTV_{p.kind.upper()}_API_KEY", "").strip())
        saved = bool(get_secret(p.key_name() or "")) or env
    except Exception as e:  # noqa: BLE001 — a damaged key file or a locked keychain: say so, the check does not crash
        return False, f"its key cannot be read ({type(e).__name__})"
    return saved, "no key"


def check_model(settings: Settings, verify: Verify | None = None) -> Check:
    """A provider is set up and can answer. With `verify` (the window's «Check again»), a saved key is also tried with a
    free request: a key the provider refuses does not count."""
    providers = settings.enabled()
    if not providers:
        return Check("Model", FAIL, "no provider set up", "Connect an AI in «Settings → AI»: your own key, or a free AI on this computer (Ollama, LM Studio). "
                     "Or: smtv model set --provider openai --model <model id>",
                     id="model", actions=(PROVIDERS,))
    ok, problems = [], []
    for p in providers:
        usable, why = _usable(p)
        if usable and verify is not None and p.kind not in ("codex", "claude_code", "streammoment"):
            good, said = verify(p)
            if good is False:
                usable, why = False, f"the key was not accepted ({said})" if said else "the key was not accepted"
        if usable:
            ok.append(p.name or p.id)
        else:
            problems.append(f"{p.name or p.id}: {why}")
    if not ok:
        return Check("Model", FAIL, "; ".join(problems), "Open «Settings → Providers» and press «Check» on each", id="model", actions=(PROVIDERS,))
    where = "keychain" if secrets_backend() == "keychain" else "encrypted file"
    return Check("Model", OK, f"{', '.join(ok)} (keys in the {where})" + (f"; not ready: {'; '.join(problems)}" if problems else ""), id="model")


def check_streammoment(others_ready: bool = False) -> Check:
    """Our own server answers at streammoment.tv (with a timeout); a VPN is the usual reason it does not (stage 22). It
    blocks only when StreamMoment is the one provider that could answer."""
    from . import account
    found = account.check()
    if found["ok"]:
        return Check("StreamMoment", OK, f"streammoment.tv {found['detail']}", id="streammoment")
    status = FAIL if found.get("hint") and not others_ready else WARN
    return Check("StreamMoment", status, found["detail"], found.get("hint") or "", id="streammoment")


def core_checks(settings: Settings, verify: Verify | None = None) -> list[Check]:
    model = check_model(settings, verify)
    out = [check_system(), *check_ffmpeg(), check_disk(), check_gpu(), model]
    enabled = settings.enabled()
    if any(p.kind == "streammoment" for p in enabled):   # only then: a check is a request to our server
        others = any(_usable(p)[0] for p in enabled if p.kind != "streammoment")
        out.append(check_streammoment(others))
    return out


# --- speech -------------------------------------------------------------------------------------------------------

LANGUAGE_HINT: str | None = None     # the window's language, set by the server once a page says it


def default_language() -> str:
    """The language whose speech model is checked: the window's, else the system's, else English."""
    if LANGUAGE_HINT:
        return LANGUAGE_HINT
    import locale
    for value in (os.environ.get("LC_ALL"), os.environ.get("LANG"), _windows_language(), (locale.getlocale()[0] or "")):
        code = _language_code(value or "")
        if code:
            return code
    return "en"


def _language_code(value: str) -> str | None:
    """«ru_RU.UTF-8», «ru-RU» → ru. Windows names its locales in words («Russian_Russia», checked on Windows 11 22.11):
    Python's own table of locale names turns «russian» into ru_RU."""
    import locale
    code = value.split(".")[0].replace("_", "-").split("-")[0].lower()
    if code.isalpha() and len(code) > 3:
        code = locale.normalize(code).split(".")[0].split("_")[0].lower()
    return code if code.isalpha() and len(code) in (2, 3) and code != "c" else None


def _windows_language() -> str | None:
    """The language of Windows itself (ru_RU), as the window takes it (desktop.ui_lang)."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes
        import locale
        return locale.windows_locale.get(ctypes.windll.kernel32.GetUserDefaultUILanguage())  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        return None


def speech_recipe(model) -> Recipe:
    """The speech model downloaded by SMTV itself into its models folder (no administrator rights)."""
    return Recipe(f"speech-{model.id}", [sys.executable, "-m", "smtv", "speech", "download", model.id],
                  links=tuple(u for u in (model.links.get("model"), model.links.get("engine")) if u))


def check_speech(settings: Settings, language: str | None = None) -> Check:
    """The speech model the stream's language takes is ready. Not downloaded yet is a warning: the first request downloads
    it by itself; «Fix» downloads it now."""
    from .asr import catalog
    language = catalog.code(language or default_language())
    model, _ = catalog.model_for(language, settings)
    name = f"Speech model ({language})"
    if model.where == "cloud":
        try:
            catalog.cloud_key(model, settings)
        except Exception as e:  # noqa: BLE001 — no key or a locked keychain: the words are in the error
            return Check(name, WARN, str(e)[:300], "Open «Settings → Speech» and choose a model, or add the key", id="speech", actions=(SPEECH,))
        return Check(name, OK, f"{model.title}, by your key", id="speech")
    if catalog.is_installed(model):
        return Check(name, OK, f"{model.title} is on this computer", id="speech")
    if not catalog.package_ready(model):
        return Check(name, WARN, f"{model.title} needs the {model.package} package, which is not installed",
                     "Choose another model in «Settings → Speech», or reinstall SMTV with vodcut", id="speech", actions=(SPEECH,))
    return Check(name, WARN, f"{model.title} is not downloaded yet: the first request downloads it (about {model.size_mb} MB)",
                 f"smtv speech download {model.id}", id="speech", recipe=speech_recipe(model), actions=(SPEECH,))
