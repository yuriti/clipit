"""The contract between `smtv` and a tool (vodcut, livecut, …).

A tool is a separate package that declares an entry point in the group "smtv.tools":

    [project.entry-points."smtv.tools"]
    vodcut = "vodcut.tool:tool"

`smtv` finds every installed tool through that group: it gets a command (`smtv vodcut …`), its own checks in
`smtv doctor`, and, if it has a `Page`, its own places in SMTV's window. A tool imports shared code only from smtv_core,
never from another tool.

The window is the gateway's; a tool only plugs into it (stage 7). Its places, each one optional:
- a kind of request under «New request» on Home (`Page.request`); its jobs join the one list of requests there;
- its own view of an open request (`mountJob` in `section.js`);
- its own item in the window's side rail (`Page.nav` and `mountNav`);
- its own block in Settings (`Page.options` switches, and/or `mountSettings`) and its checks under System (`Tool.checks`);
- its card and page under Plugins (`Tool.summary`, `Page.about`, `Page.icon`), with the tab «Agents» listing
  `Tool.agents` (stage 10): its own agents and the shared ones of the core it uses (`smtv_core.agents.core`).
A tool that is not installed leaves no trace; one that fails to load is listed under Plugins as broken and nowhere else.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .agents import Agent
from .checks import Check
from .settings import Settings

ENTRY_POINT_GROUP = "smtv.tools"


@dataclass
class JobStart:
    """A new job from the page: its folder, and the arguments after `smtv <tool>` that run it in its own process.
    `echo` (a job typed in a terminal and handed over to the running SMTV) prints its events there as they come."""
    folder: Path
    args: list[str]
    echo: Callable[[dict], None] | None = None


# Text the window shows: a key of the tool's words (`Page.folder/i18n/<language>.json`, the window's when the tool's
# lack it); a key no file has is shown as it is, so plain English works too.
Text = str


@dataclass
class RequestKind:
    """A kind of request this tool takes under «New request» on Home (a recording, a live stream, …)."""
    title: Text
    about: Text = ""
    icon: str = ""          # SVG path data on a 24×24 grid, drawn as a stroke; empty: the tool's own icon


@dataclass
class NavItem:
    """The tool's own item in the window's side rail (for example LiveCut's «Live streams»). `section.js` draws it with
    `mountNav(element, api, path)`, where path is the rest of the address after the item."""
    id: str                 # [a-z0-9-]+, part of the address: #/x/<tool>/<id>
    title: Text
    icon: str = ""


@dataclass
class Page:
    """A tool's places in SMTV's window. The window runs every job as `smtv <tool> <args>` in its own process
    (cancel stops that process) and shows it from the job's event journal.

    `folder` holds the tool's static files: `section.js`, an ES module exporting any of
    `mountNew(element, api)` (the form of a new request), `mountJob(element, api, job)` (an open request; may return
    {close}), `mountNav(element, api, path)` (its rail item; may return {route(path), close}), `mountSettings(element, api)`
    (its block in Settings); `section.css`, loaded with it; and `i18n/<language>.json`, its own words ({key: text},
    `i18n/en.json` the source; apart from the window's and other tools'; a key a language lacks is shown in English).
    `start` turns the form's fields into a job; it raises ValueError with a message for the person when they do not fit.
    `estimate` (optional) says how long a job would take before it starts: {"seconds": ..., "steps": [{"name", "seconds"}], ...}.
    `describe` (optional) gives a job folder's short summary for the list of jobs: {"title", "source", "duration_s", ...}.
    `options` (optional) lists the tool's switches as [{"name", "value", "about"}]; `set_option` changes one.
    """
    title: str
    folder: Path
    jobs: Callable[[], Path]
    start: Callable[[dict], JobStart]
    estimate: Callable[[dict], dict] | None = None
    describe: Callable[[Path], dict] | None = None
    options: Callable[[Settings], list[dict]] | None = None
    set_option: Callable[[Settings, str, bool], None] | None = None
    request: RequestKind | None = None          # None: no «New request» entry; its jobs are still listed and open
    nav: NavItem | None = None
    about: Text = ""                            # a few sentences for its page under Plugins: what it does, how
    icon: str = ""                              # SVG path data on a 24×24 grid: its card, its requests in the list
    pause: bool = False                         # its jobs stop at a safe point when asked (smtv_core.pause); else only at once
    # «Run again (a new request)»: from a finished job's folder and the arguments it ran with, a new job in a new folder;
    # the old request stays as it is. None: no such button.
    again: Callable[[Path, list], JobStart] | None = None
    # A job command typed in a terminal (`smtv vodcut run …`), as the window would run it: its job folder (inside `jobs()`)
    # and arguments. While SMTV runs, the gateway hands such a command over to it, into its queue (stage 16); without SMTV
    # the command runs itself under the data folder's lock. None for commands that are not jobs (set, check).
    command_job: Callable[[argparse.Namespace], JobStart | None] | None = None


@dataclass
class Tool:
    name: str                                   # command and extra name: smtv <name>, smtv[<name>]
    summary: str                                # one line for `smtv list`
    version: str
    add_commands: Callable[[argparse.ArgumentParser], None]   # fills the tool's own subcommands
    checks: Callable[[Settings], list[Check]] = field(default=lambda settings: [])
    page: Page | None = None                    # its section on the `smtv serve` page, if it has one
    agents: list[Agent] = field(default_factory=list)   # the prompts it asks a model with, and what each needs
