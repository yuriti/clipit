"""How VodCut plugs into smtv: its commands and its checks."""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from smtv_core import agents
from smtv_core.checks import FAIL, OK, SIGN_IN, WARN, Check, Recipe, check_ffmpeg, check_model, check_speech
from smtv_core.events import Journal
from smtv_core.settings import Settings
from smtv_core.tool import Tool
from smtv_core.pause import Paused

from . import __version__, local_download, options
from .agents import AGENTS
from .page import page


def _yt_dlp_recipe() -> Recipe | None:
    argv = local_download.install_argv()
    return Recipe("yt-dlp", argv, links=("https://github.com/yt-dlp/yt-dlp",)) if argv else None


def checks(settings: Settings) -> list[Check]:
    """Links: through the StreamMoment account (stage 23), or yt-dlp here when «Download on this computer» is on (then it
    must be there and fresh). A file of one's own needs neither, so a missing account is a warning, not a failure. And the
    speech model the stream's language takes (stage 24)."""
    try:
        speech = check_speech(settings)
    except Exception as e:  # noqa: BLE001 — the links row stays; a broken speech check is a warning (the run says more)
        speech = Check("Speech model", WARN, f"the check crashed: {type(e).__name__}: {e}"[:300], id="speech")
    return [_links_check(settings), speech]


def _links_check(settings: Settings) -> Check:
    if options.load(settings)["local_download"]:
        name = "vodcut: links (yt-dlp here, at your own risk)"
        if not local_download.available():
            return Check(name, FAIL, "yt-dlp not found", local_download.install_hint(), id="vodcut-yt-dlp", recipe=_yt_dlp_recipe())
        found = local_download.version()
        age = local_download.age_days(found)
        if age is not None and age > local_download.STALE_DAYS:
            return Check(name, WARN, f"yt-dlp {found} is {age} days old: links may no longer open",
                         local_download.install_hint(), id="vodcut-yt-dlp", recipe=_yt_dlp_recipe())
        return Check(name, OK, f"yt-dlp {found or 'found'}", id="vodcut-yt-dlp")
    from smtv_core import account
    who = account.signed_in()
    name = "vodcut: links (through StreamMoment)"
    if who:
        return Check(name, OK, f"signed in as {who.get('name') or who.get('provider') or 'an account'}", id="vodcut-links")
    return Check(name, WARN, "not signed in: links need a StreamMoment account, files work without it",
                 "profile menu → Sign in", id="vodcut-links", actions=(SIGN_IN,))


def _cmd_check(_args, _tools, _broken) -> int:
    rows = checks(Settings.load())
    for r in rows:
        print(f"  {r.status:<4}  {r.name}  {r.detail}" + (f"\n        fix: {r.fix}" if r.status != OK and r.fix else ""))
    return 1 if any(r.status == FAIL for r in rows) else 0


def _asker(settings: Settings):
    """The provider and model for each agent: the person's choice in «Settings → Agents», else the recommended one of the
    first suitable provider (stage 19)."""
    from .model import Asker
    return Asker(agents.default_connection(settings), models=agents.models_for(settings, "vodcut", AGENTS))


def _crash(error: Exception, job: Path, journal: Journal, stage: str | None = None) -> None:
    """An error nobody expected leaves a crash file for «Report a problem» (`smtv_core.crash`). A RunError is an expected
    stop with its own words (a link that does not open, a missing model): it is in the journal, not a crash."""
    from smtv_core import crash
    from .pipeline import RunError
    if isinstance(error, RunError):
        return
    if stage is None:
        try:
            stage = next((e["data"].get("name") for e in reversed(journal.read()) if e["type"] == "stage"), None)
        except Exception:  # noqa: BLE001 — the step is a nicety
            stage = None
    crash.record(error, where="job", tool="vodcut", job=job.name, stage=stage)


def _ready_to_render() -> str | None:
    """Why clips cannot be rendered on this computer, or None."""
    for row in check_ffmpeg():
        if row.status == FAIL:
            return f"{row.detail}. fix: {row.fix}"
    return None


def _render(job: Path, settings: Settings, only: set[str] | None) -> int:
    from .render import render_all

    problem = _ready_to_render()
    if problem:
        print(f"\nClips are not rendered: {problem}\nThe list of clips is saved; after the fix run: smtv vodcut render {job}")
        return 1
    asker = _asker(settings) if check_model(settings).status == OK else None
    from . import console, options
    with Journal(job, tool="vodcut", echo=console.printer(job)) as journal:
        try:
            report = render_all(job, asker, only=only, options=options.load(settings), journal=journal)
        except Paused:
            return 0                  # paused between two clips: the clips made so far stay; «Continue» goes on
        except Exception as e:
            _crash(e, job, journal, "render")
            raise
    return 0 if all(r["status"] == "done" for r in report) else 1


def _recap(job: Path, settings: Settings) -> int:
    """The recap after the clips (the «recap» switch). Its failure is reported in the journal and leaves the clips."""
    from . import console, options
    from .recap import make

    if not (shutil.which("ffmpeg") and shutil.which("ffprobe")):     # no captions are burned in: any ffmpeg will do
        print(f"\nThe recap is not made: ffmpeg is not installed.\nAfter the fix run: smtv vodcut recap {job}")
        return 1
    asker = _asker(settings) if check_model(settings).status == OK else None
    with Journal(job, tool="vodcut", echo=console.printer(job)) as journal:
        try:
            made = make(job, asker, journal, ad_blur=options.load(settings)["ad_blur"])
        except Paused:
            return 0
        except Exception as e:
            _crash(e, job, journal, "recap")
            raise
    return 0 if made or _recap_skipped(job) else 1


def _recap_skipped(job: Path) -> bool:
    """The model found nothing worth a recap: a result, not a failure. A story with a failed encode is a failure (exit 1)."""
    try:
        return json.loads((job / "recap" / "story.json").read_text(encoding="utf-8")).get("status") == "skipped"
    except (OSError, ValueError, AttributeError):
        return False


def _cmd_run(args, _tools, _broken) -> int:
    from . import console, options
    from .pipeline import job_dir, run

    settings = Settings.load()
    model_check = check_model(settings)
    if model_check.status == FAIL:
        print(f"The model is not set up: {model_check.detail}.\n  fix: {model_check.fix}")
        return 2
    job = Path(args.out) if args.out else job_dir(args.source)
    with Journal(job, tool="vodcut", echo=console.printer(job)) as journal:  # every step is printed from the job's journal
        before = journal.last
        try:
            result = run(args.source, _asker(settings), job=job, language=args.language, channel=args.channel or "",
                         workers=args.workers, max_clips=args.max_clips, journal=journal,
                         precise=options.load(settings)["precise"])
        except Paused:
            return 0                  # paused between two steps, as asked: a clean stop, not a failure
        except Exception as e:  # noqa: BLE001 — download, ffmpeg and model errors carry their own message
            _crash(e, job, journal)
            if not any(ev["type"] == "error" for ev in journal.read(after=before)):  # the journal itself could not be written
                print(f"Stopped: {type(e).__name__}: {e}")
            return 1
    clips = result["clips"]
    if args.no_render or not clips:
        return 0
    code = _render(job, settings, None)
    from smtv_core.events import read
    paused = any(e["type"] == "cancelled" for e in read(job)[-1:])     # a pause between two clips stops the recap too
    if options.load(settings)["recap"] and not paused:
        _recap(job, settings)       # extra: a failed recap is in the journal, the clips are what the run is judged by
    return code


def _cmd_recap(args, _tools, _broken) -> int:
    from .pipeline import job_dir

    candidate = Path(args.job).expanduser().resolve()
    job = candidate if (candidate / "clips.json").exists() else job_dir(args.job)
    if not (job / "clips.json").exists():
        print(f"No clips.json in {job}: run `smtv vodcut run {args.job}` first.")
        return 2
    return _recap(job, Settings.load())


def _cmd_render(args, _tools, _broken) -> int:
    from .pipeline import job_dir

    candidate = Path(args.job).expanduser().resolve()
    job = candidate if (candidate / "clips.json").exists() else job_dir(args.job)
    if not (job / "clips.json").exists():
        print(f"No clips.json in {job}: run `smtv vodcut run {args.job}` first.")
        return 2
    only = set(args.clips.split(",")) if args.clips else None
    return _render(job, Settings.load(), only)


def _cmd_set(args, _tools, _broken) -> int:
    from . import options

    if args.name:
        if args.name not in options.DEFAULTS or args.value not in ("on", "off"):
            print(f"Usage: smtv vodcut set <{'|'.join(options.DEFAULTS)}> <on|off>")
            return 2
        with Settings.edit() as s:          # one edit at a time with the window and other commands (A8)
            options.set_option(s, args.name, args.value == "on")
    settings = Settings.load()
    for name, value in options.load(settings).items():
        print(f"  {name:<14} {'on ' if value else 'off'}  {options.ABOUT[name]}")
    return 0


def add_commands(parser: argparse.ArgumentParser) -> None:
    parser.description = "Clips and a recap from stream recordings: a Twitch or YouTube link, or a video file."
    sub = parser.add_subparsers(dest="vodcut_command", metavar="<action>")
    run = sub.add_parser("run", help="find the clips in a recording and render them: smtv vodcut run <link or file>")
    run.add_argument("source", help="a Twitch link (through your StreamMoment account) or a path to a video file")
    run.add_argument("--language", default="auto", help="language of the speech: auto (default), ru, en, de, es, …")
    run.add_argument("--channel", help="streamer's name, if the link does not tell it")
    run.add_argument("--max-clips", type=int, help="at most this many clips (default: every strong and good moment, up to 30)")
    run.add_argument("--workers", type=int, default=4, help="model requests at once (default 4)")
    run.add_argument("--no-render", action="store_true", help="only find the clips, do not render them")
    run.add_argument("--out", help="job folder (default: one folder per recording in the smtv data folder)")
    run.set_defaults(func=_cmd_run)
    render = sub.add_parser("render", help="render the clips found earlier: smtv vodcut render <link, file or job folder>")
    render.add_argument("job", help="the same link or file as for run, or its job folder")
    render.add_argument("--clips", help="only these clips, e.g. clip01,clip03")
    render.set_defaults(func=_cmd_render)
    recap = sub.add_parser("recap", help="make the 20–30 minute recap of a recording analysed earlier: smtv vodcut recap <link, file or job folder>")
    recap.add_argument("job", help="the same link or file as for run, or its job folder")
    recap.set_defaults(func=_cmd_recap)
    switches = sub.add_parser("set", help="turn a detail of the clips on or off: smtv vodcut set bleep off; without arguments shows them")
    switches.add_argument("name", nargs="?", help="loudness, bleep, peak_lines, ad_blur, precise, critic or recap")
    switches.add_argument("value", nargs="?", choices=("on", "off"))
    switches.set_defaults(func=_cmd_set)
    check = sub.add_parser("check", help="VodCut's own checks (part of smtv doctor)")
    check.set_defaults(func=_cmd_check)
    parser.set_defaults(func=lambda args, tools, broken: (parser.print_help(), 0)[1])


tool = Tool(name="vodcut", summary="Clips and a recap from stream recordings (Twitch, YouTube, a file)", version=__version__,
            add_commands=add_commands, checks=checks, page=page, agents=AGENTS)
