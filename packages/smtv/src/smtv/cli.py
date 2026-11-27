"""smtv: list and add tools, check this computer, set up the model, and run the tools' own commands."""
from __future__ import annotations

import argparse
import getpass
import os
import subprocess
import sys
from pathlib import Path

from smtv_core import checks as core, paths
from smtv_core.settings import KINDS, PRESETS, Provider, Settings, default_name, secrets_backend, set_secret

from . import __version__
from .tools import CATALOG, discover, doctor_rows

MARK = {core.OK: "ok  ", core.WARN: "warn", core.FAIL: "FAIL"}


def cmd_list(_args, tools, broken):
    installed = {t.name for t in tools}
    for t in tools:
        print(f"  {t.name:<10} {t.version:<12} {t.summary}")
    for b in broken:
        print(f"  {b.name:<10} {'broken':<12} {b.error}")
    missing = [n for n in CATALOG if n not in installed and n not in {b.name for b in broken}]
    if not tools and not broken:
        print("  No tools installed yet.")
    for name in missing:
        print(f"  {name:<10} {'not added':<12} {CATALOG[name]}   →  smtv add {name}")
    return 0


def cmd_doctor(_args, tools, broken):
    rows = doctor_rows(tools, broken)
    width = max(len(r.name) for r in rows)
    for r in rows:
        print(f"  {MARK[r.status]}  {r.name:<{width}}  {r.detail}")
        if r.status != core.OK and (r.recipe or r.fix):
            line = r.recipe.line() if r.recipe else r.fix
            print(f"        {'':<{width}}  fix: {line}" + ("   (administrator rights: run it yourself)" if r.recipe and r.recipe.admin else ""))
    failed = [r for r in rows if r.status == core.FAIL]
    print("\nReady." if not failed else f"\n{len(failed)} thing(s) to fix before the tools can run.")
    return 1 if failed else 0


def cmd_speech_download(args, _tools, _broken):
    """A speech model into SMTV's models folder, with progress lines (what «Fix» runs from the window, stage 24)."""
    from smtv_core.asr import catalog
    model = catalog.MODELS.get(args.model)
    if model is None or model.where != "local":
        print(f"No speech model {args.model} to download. Local models: {', '.join(m.id for m in catalog.MODELS.values() if m.where == 'local')}")
        return 2
    if catalog.is_installed(model):
        print(f"{model.title} is on this computer already: {catalog.folder(model)}")
        return 0
    if not catalog.package_available(model):
        print(f"{model.title} needs the {model.package} package: reinstall Clip It! with vodcut")
        return 1
    print(f"Downloading {model.title} (about {model.size_mb} MB) into {catalog.folder(model)}")
    last = [-1]

    def progress(done, total):
        step = int(done * 10 / total) if total else 0
        if step != last[0]:
            last[0] = step
            print(f"  {done} of {total} MB")

    if model.id in catalog.ONNX:
        from smtv_core.asr.engines import load_watched
        load_watched(catalog.ONNX[model.id], progress)
    else:
        from smtv_core.asr import whisper
        extra = catalog.package_mb(model)
        if extra:
            print(f"First Whisper's engine, which the app downloads on first use (about {extra} MB)")
            catalog.ensure_package(model, progress)
        whisper.download(progress=progress)
    if not catalog.is_installed(model):
        print("The download ended, but the model is not complete: try again")
        return 1
    print(f"Done: {model.title} is on this computer")
    return 0


def cmd_add(args, tools, _broken):
    """Installs tools the same way the window does (`updates.make_plan`): the same pinned versions, everything added
    with `--with` kept, and smtv, smtv-core and the tools at one number."""
    from . import updates
    unknown = [n for n in args.names if n not in CATALOG]
    if unknown:
        print(f"Unknown tool: {', '.join(unknown)}. Available: {', '.join(CATALOG)}.")
        return 2
    now = updates.installed_tools(t.name for t in tools)
    after = sorted(set(now) | set(args.names))
    if after == now:
        print("Already installed: " + ", ".join(args.names))
        return 0
    kind = updates.install_kind()
    if kind not in ("uv", "pip"):
        print("This Clip It! was not installed with uv or pip (from source, Docker or without uv on this computer): "
              "add the tool where it was installed.")
        return 2
    current = {n: v for n in (*updates.CORE, *now) if (v := updates.version_of(n))}
    target = {**current, **{n: current["smtv"] for n in args.names}}   # tools come out with smtv, under its number
    plan = updates.make_plan("install", kind, now, current, target, after, port=0, relaunch=["smtv"])
    if args.dry_run:
        for step in plan.steps:
            print("Would run: " + " ".join(step))
        return 0
    if kind == "uv" and not updates.find_uv():
        print("smtv was installed with uv, but uv is not on PATH. Run this yourself:\n  " + "\n  ".join(" ".join(s) for s in plan.steps))
        return 2
    print("Close the Clip It! window first if it is open: on Windows its files cannot be replaced while it runs.")
    for step in plan.steps:
        print("Running: " + " ".join(step))
        code = subprocess.call(step)
        if code != 0:
            return code
    return 0


def _cli_provider(settings, args):
    """The provider `smtv model` works on: --id, else the first of the kind given, else the first of the list."""
    if getattr(args, "id", None):
        return settings.provider(args.id)
    kind = getattr(args, "provider", None)
    return next((p for p in settings.providers if kind in (None, p.kind)), None)


def cmd_model_set(args, _tools, _broken):
    """Adds or changes one provider of the list (the window's «Settings → Providers» does the same)."""
    with Settings.edit() as settings:
        p = _cli_provider(settings, args)
        if p is None:
            if not args.provider:
                print("Name the provider: smtv model set --provider <" + "|".join(KINDS) + ">")
                return 2
            p = Provider(id=args.id or settings.new_id(args.provider), kind=args.provider)
            if p.kind == "openai":
                p.base_url = args.base_url or PRESETS["openai"]
                p.preset = "openai" if "api.openai.com" in p.base_url else "openrouter" if "openrouter.ai" in p.base_url else "custom"
            p.name = default_name(p.kind, p.preset)
            settings.providers.append(p)
        if args.model is not None:
            p.default_model = args.model
        if args.base_url and p.kind == "openai":
            p.base_url = args.base_url
        if args.json_mode:
            p.json_mode = args.json_mode
    path = paths.settings_file()
    print(f"Saved to {path}: {p.id} ({p.name}) / {p.default_model or '(recommended per agent)'}")
    if p.key_name():
        print(f"Now add the key: smtv model key --id {p.id}")
    return 0


def cmd_model_key(args, _tools, _broken):
    settings = Settings.load()
    p = _cli_provider(settings, args)
    if p is None:
        print("Add a provider first: smtv model set --provider <" + "|".join(KINDS) + ">")
        return 2
    if not p.key_name():
        print(f"{p.name} uses its own sign-in with your subscription. No key is needed.")
        return 0
    value = getpass.getpass(f"{p.name} API key (input hidden): ").strip()
    if not value:
        print("Nothing entered, nothing saved.")
        return 2
    where = set_secret(p.key_name(), value)
    print("Key saved in the system keychain." if where == "keychain" else
          "Key saved encrypted in the Clip It! folder. Install smtv-core[keyring] to keep keys in the system keychain instead.")
    return 0


def cmd_account_server(args, _tools, _broken):
    from smtv_core import account
    if args.url:
        try:
            now = account.set_server(None if args.url == "default" else args.url)
        except account.AccountError as e:
            print(f"smtv: {e}", file=sys.stderr)
            return 2
        print(f"StreamMoment server: {now}")
        print("Restart Clip It! for the window to use it. Signing in again is needed: tokens of another server do not work here.")
        return 0
    print(account.server())
    return 0


def cmd_model_show(_args, _tools, _broken):
    settings = Settings.load()
    if not settings.providers:
        print("No providers yet: smtv model set --provider <" + "|".join(KINDS) + ">")
    for p in settings.providers:
        line = f"{p.id:<14} {p.name:<22} {p.kind:<12} {'on ' if p.enabled else 'off'}"
        if p.kind == "openai":
            line += f"  {p.base_url}"
        if p.default_model:
            line += f"  default model: {p.default_model}"
        print(line)
    print(f"keys in:  the {'system keychain' if secrets_backend() == 'keychain' else 'encrypted file in the Clip It! folder'}")
    return 0


def cmd_serve(args, tools, broken):
    from .serve import serve
    return serve(tools, broken, port=args.port, open_browser=not args.no_browser)


def cmd_app(args, tools, broken):
    from .desktop import run_app
    return run_app(tools, broken, port=args.port, browser=args.browser)


SHORTCUT_MARK = "shortcut"   # Settings.tools["smtv"]["shortcut"]: "made" or "removed" (then never made again by itself)


def _mark_shortcut(value: str) -> None:
    with Settings.edit() as settings:
        settings.tools.setdefault("smtv", {})[SHORTCUT_MARK] = value


def at_terminal() -> bool:
    """A person typing in a terminal: not a job the page started, a script, a pipe or a test."""
    try:
        return bool(sys.stdin and sys.stdin.isatty() and sys.stdout and sys.stdout.isatty())
    except (AttributeError, ValueError):
        return False


def first_run_shortcut(command: str | None) -> None:
    """The SMTV icon on the first run of any smtv command by a person at a terminal (not jobs started by the page, not
    scripts or tests), so nobody needs to know about `smtv shortcut`. Once: after `smtv shortcut --remove`, or a deleted
    shortcut, it is never made again by itself. SMTV_NO_SHORTCUT=1 turns it off. Never for the desktop apps."""
    if command in (None, "shortcut", "uninstall") or os.environ.get("SMTV_NO_SHORTCUT"):
        return
    from . import launcher
    from .updates import install_kind
    if not launcher.own_shortcut(install_kind()):    # the desktop apps: their own icon, or none at all (the ZIP)
        return
    if command == "app" or not at_terminal():
        return
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return   # a server without a desktop: nothing to click
    try:
        if (Settings.load().tools.get("smtv") or {}).get(SHORTCUT_MARK):
            return
        system = launcher.this_system()
        if not launcher.installed(system):
            launcher.install(system)
            print("Made the Clip It! icon: from now on start Clip It! by double-clicking it (remove it: smtv shortcut --remove).")
        _mark_shortcut("made")
    except Exception as e:  # noqa: BLE001 — the icon is a convenience; the command itself must still run
        print(f"Could not make the Clip It! icon ({type(e).__name__}: {e}); try: smtv shortcut")
        try:
            _mark_shortcut("failed")
        except OSError:
            pass


def cmd_shortcut(args, _tools, _broken):
    from . import launcher
    from .updates import install_kind
    if not launcher.own_shortcut(install_kind()):
        print("This Clip It! is the desktop app: its icon is in Applications (macOS) or the Start menu (Windows) already.")
        return 0
    system = launcher.this_system()
    try:
        made = launcher.remove(system) if args.remove else launcher.install(system)
    except (OSError, RuntimeError) as e:
        print(f"Could not {'remove' if args.remove else 'make'} the shortcut: {e}")
        return 2
    _mark_shortcut("removed" if args.remove else "made")
    if args.remove:
        print("Removed:" if made else "Nothing to remove.")
        for m in made:
            print(f"  {m}")
        return 0
    print("Clip It! can now start without a terminal:")
    for m in made:
        print(f"  {m}")
    print("Double-click Clip It! to open it in its own window.")
    return 0


def cmd_uninstall(args, _tools, _broken):
    from . import instance, serve, uninstall
    # any SMTV on this data folder: a window on any port (`--port 9000`), or a job in another terminal
    if serve.probe(serve.DEFAULT_PORT) or instance.holder(wait=0.5):
        print("Clip It! is running. Close its window first (or Settings → Quit), or remove it from its window: "
              "Settings → System → Remove Clip It!")
        return 2
    p = uninstall.plan()
    gb = p.data_bytes / 1e9
    if p.program == "app":
        print("This removes Clip It!'s data from this computer; the program itself you remove the system's way: "
              + uninstall.APP_REMOVE.get(sys.platform, "delete its folder") + ".")
    else:
        print("This removes Clip It! from this computer: the icon"
              + (" and the program (uv tool uninstall smtv)." if p.program == "uv" else "."))
    print(f"Clips, jobs, settings and keys in {p.data_folder} ({gb:.1f} GB): "
          + ("removed too (--data)." if args.data else "kept (add --data to remove them too)."))
    if not args.yes:
        try:
            answer = input("Type yes to remove Clip It!: ").strip().lower()
        except EOFError:
            answer = ""
        if answer != "yes":
            print("Nothing removed.")
            return 1
    done = uninstall.run(args.data)
    for d in done.done:
        print(f"  removed: {d}")
    for n in done.notes:
        print(f"  note: {n}")
    return 0


def cmd_report(args, tools, broken):
    """«Report a problem» without the window (a terminal, a server, Docker): shows what goes in, saves the archive and
    gives the address of a new GitHub issue. Nothing is sent."""
    from . import report
    try:
        job = report.find_job(tools, args.job)
    except LookupError as e:
        print(f"{e}. Requests: smtv report --list")
        return 2
    if args.list:
        from .jobs import status
        for tool, folder in sorted(report.job_folders(tools), key=lambda x: x[1].name):
            print(f"  {tool}/{folder.name:<40} {status(folder, None)}")
        return 0
    r = report.collect(tools, broken, job=job, names=args.names)
    print("The report will hold these files:")
    width = max(len(p.name) for p in r.parts)
    for p in r.parts:
        print(f"  {p.name:<{width}}  {len(p.text.encode('utf-8')) / 1024:6.1f} KB  {p.about}")
    print("\nKeys and tokens are cut out; your home folder shows as ~. "
          + ("Links to streams and file names are kept (--names)." if args.names
             else "Links to streams and file names are hidden (add --names to keep them)."))
    print(f"About: {report.issue_title(r)}")
    if args.show:
        for p in r.parts:
            print(f"\n===== {p.name} =====\n{p.text}")
    if not args.yes and at_terminal():
        try:
            answer = input("Save the report? [Y/n] ").strip().lower()
        except EOFError:
            answer = ""
        if answer not in ("", "y", "yes", "д", "да"):
            print("Nothing saved.")
            return 1
    try:
        path = r.save(Path(args.out).expanduser() if args.out else None)
    except OSError as e:
        print(f"Could not save the report: {e}")
        return 2
    url = report.issue_url(r)
    print(f"\nSaved: {path}")
    print(f"New issue: {url}")
    print("Nothing was sent. Open the address, check the text and drag the archive into the issue.")
    if not args.no_open and report.can_open():
        report.reveal(path)
        report.open_issue(url)
    elif report.in_docker():
        print(f"In Docker, copy it out first: docker cp <container>:{path} .")
    return 0


def build_parser(tools) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="smtv", description="StreamMoment tools: clip long streams on your own computer.")
    parser.add_argument("--version", action="version", version=f"smtv {__version__}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    sub.add_parser("list", help="installed tools and the ones you can add").set_defaults(func=cmd_list)
    sub.add_parser("doctor", help="check this computer and say what to fix").set_defaults(func=cmd_doctor)
    add = sub.add_parser("add", help="add a tool, e.g. smtv add vodcut")
    add.add_argument("names", nargs="+", metavar="tool")
    add.add_argument("--dry-run", action="store_true", help="print the install command without running it")
    add.set_defaults(func=cmd_add)
    model = sub.add_parser("model", help="choose the AI model the tools use")
    msub = model.add_subparsers(dest="model_command", metavar="<action>", required=True)
    ms = msub.add_parser("set", help="provider and model id")
    ms.add_argument("--provider", choices=KINDS, help="the kind of provider")
    ms.add_argument("--id", help="which provider of the list (see `smtv model show`); a new one with this id if none")
    ms.add_argument("--model", help="its default model: for agents the table has no model for (empty for a CLI's own default)")
    ms.add_argument("--base-url", help="openai only: an OpenAI-compatible server, e.g. http://127.0.0.1:11434/v1 for Ollama")
    ms.add_argument("--json-mode", choices=("schema", "object", "none"), help="openai only: how the answer format is requested")
    ms.set_defaults(func=cmd_model_set)
    mk = msub.add_parser("key", help="add or replace a provider's API key (asked without echo)")
    mk.add_argument("--id", help="which provider of the list (default: the first)")
    mk.set_defaults(func=cmd_model_key)
    msub.add_parser("show", help="the providers").set_defaults(func=cmd_model_show)
    sp = sub.add_parser("speech", help="speech recognition models")
    spsub = sp.add_subparsers(dest="speech_command", metavar="<action>", required=True)
    spd = spsub.add_parser("download", help="download a speech model now (otherwise the first request does)")
    spd.add_argument("model", help="gigaam, parakeet or whisper")
    spd.set_defaults(func=cmd_speech_download)
    acc = sub.add_parser("account", help="the StreamMoment account on this computer")
    asub = acc.add_subparsers(dest="account_command", metavar="<action>", required=True)
    asrv = asub.add_parser("server", help="which StreamMoment server to sign in to: an address of a local test stand, or «default»")
    asrv.add_argument("url", nargs="?", help="https://…, http://localhost:<port>, or default; without it: show the current one")
    asrv.set_defaults(func=cmd_account_server)
    srv = sub.add_parser("serve", help="open the page: jobs live, clips, settings (only on this computer)")
    srv.add_argument("--port", type=int, default=8642, help="port on 127.0.0.1 (default 8642, the installed app's port)")
    srv.add_argument("--no-browser", action="store_true", help="do not open the browser")
    srv.set_defaults(func=cmd_serve)
    app = sub.add_parser("app", help="Clip It! in its own window, like any program (what the Clip It! icon runs)")
    app.add_argument("--browser", action="store_true", help="open the page in the browser instead of Clip It!'s window")
    app.add_argument("--port", type=int, default=8642, help="port on 127.0.0.1 (default 8642; another one only for tests)")
    app.set_defaults(func=cmd_app)
    sc = sub.add_parser("shortcut", help="the Clip It! icon (Applications, desktop, Start menu, applications menu)")
    sc.add_argument("--remove", action="store_true", help="delete the icon")
    sc.set_defaults(func=cmd_shortcut)
    un = sub.add_parser("uninstall", help="remove Clip It! from this computer (clips and settings only with --data)")
    un.add_argument("--data", action="store_true", help="also remove clips, jobs, settings and keys")
    un.add_argument("--yes", action="store_true", help="do not ask")
    un.set_defaults(func=cmd_uninstall)
    rp = sub.add_parser("report", help="report a problem: an archive with logs (no keys) and a new GitHub issue; nothing is sent")
    rp.add_argument("job", nargs="?", help="the request: <tool>/<id>, its id or its folder (default: the newest failed one)")
    rp.add_argument("--names", action="store_true", help="keep links to streams and file names (hidden by default)")
    rp.add_argument("--out", help="folder for the archive (default: Downloads, or Clip It!'s own reports folder)")
    rp.add_argument("--show", action="store_true", help="print every file of the report in full before saving")
    rp.add_argument("--yes", action="store_true", help="do not ask before saving")
    rp.add_argument("--no-open", action="store_true", help="do not open the browser and the folder")
    rp.add_argument("--list", action="store_true", help="list the requests that can be reported")
    rp.set_defaults(func=cmd_report)
    for tool in tools:
        tp = sub.add_parser(tool.name, help=tool.summary)
        tool.add_commands(tp)
    return parser


def _line_buffered() -> None:
    """Progress lines show up at once even when the output goes to a file or a pipe (a long run under nohup or a task).
    And a character the output's code page lacks becomes «?» instead of a crash: on Windows, `smtv doctor > file.txt` or
    a pipe writes in cp1252 or cp1251, which have no «→» (a console window itself takes any character). The encoding a
    job is started with (PYTHONIOENCODING, jobs.py) is set here too: the Windows ZIP's Python ignores PYTHON* variables
    (its ._pth file puts it in isolated mode), and its job logs would come out in the system's code page."""
    wanted = os.environ.get("PYTHONIOENCODING", "").split(":")[0].strip()
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(line_buffering=True, errors="replace", **({"encoding": wanted} if wanted else {}))


def main(argv=None) -> int:
    _line_buffered()
    tools, broken = discover()
    parser = build_parser(tools)
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    first_run_shortcut(args.command)
    try:                   # the ffmpeg with captions first on PATH, for this process and every job it starts (stage 24)
        core.use_ffmpeg()
    except Exception as e:  # noqa: BLE001 — never stops a command: the check says what is wrong with ffmpeg
        print(f"ffmpeg lookup: {type(e).__name__}: {e}", file=sys.stderr)
    from smtv_core import crash
    from .jobs import UNDER_SMTV, as_job
    where = "server" if args.command in ("serve", "app") else "job" if os.environ.get(UNDER_SMTV) else "cli"
    crash.install_hooks(where)
    if where == "job":     # «Остановить» stops ffmpeg and yt-dlp under the job too; the job ends when its SMTV is gone (A3)
        as_job()
    try:
        job = _job_command(args, tools)
        if job:
            from .handoff import run_command
            tool, spec = job
            return run_command(tool, spec, args, tools, broken)
        return args.func(args, tools, broken) or 0
    except (KeyboardInterrupt, SystemExit):
        raise
    except Exception as e:
        crash.record(e, where=where, stage=args.command, tool=args.command if any(t.name == args.command for t in tools) else None)
        raise


def _job_command(args, tools):
    """(tool, JobStart) for a tool's job command typed here: it runs under the data folder's lock or goes to the running
    SMTV (stage 16). None for everything else, and for the jobs SMTV starts itself (they run under SMTV's lock)."""
    from . import instance
    from .jobs import UNDER_SMTV
    owner = os.environ.get(UNDER_SMTV, "")
    if owner.isdigit() and instance.alive(int(owner)):
        return None                       # started by that SMTV, under its lock (a value left in a shell is not enough)
    tool = next((t for t in tools if t.name == args.command), None)
    if not tool or not tool.page or not tool.page.command_job:
        return None
    spec = tool.page.command_job(args)
    return (tool, spec) if spec else None


if __name__ == "__main__":
    sys.exit(main())
