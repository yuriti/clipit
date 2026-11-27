"""Finding installed tools and installing new ones."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from importlib.metadata import entry_points

from smtv_core import checks as core
from smtv_core.settings import Settings
from smtv_core.tool import ENTRY_POINT_GROUP, Tool

from . import i18n
from .about import soon_item, soon_plugins

# Tools that exist and can be added with `smtv add <name>`. A new tool gets a line here and an extra in pyproject.toml.
CATALOG = {
    "vodcut": "Clips and a recap from stream recordings (Twitch, YouTube, a file)",
}

# Tools that are announced but cannot be added yet: shown under Plugins as «soon», never installed. They come from the one
# list of what is coming, soon.json (about.py).
SOON = soon_plugins()


@dataclass
class Broken:
    name: str
    error: str


def discover() -> tuple[list[Tool], list[Broken]]:
    """Installed tools, and tools that are installed but failed to load (they must not break smtv itself)."""
    tools, broken = [], []
    for ep in entry_points(group=ENTRY_POINT_GROUP):
        try:
            tool = ep.load()
            if not isinstance(tool, Tool):
                raise TypeError(f"{ep.value} is not a smtv_core.tool.Tool")
            tools.append(tool)
        except Exception as e:  # noqa: BLE001 — a broken tool is reported, never fatal
            broken.append(Broken(ep.name, f"{type(e).__name__}: {e}"))
    return sorted(tools, key=lambda t: t.name), broken


def running_as_uv_tool() -> bool:
    """True when smtv was installed with `uv tool install`: uv leaves a receipt in the tool's environment."""
    return os.path.exists(os.path.join(sys.prefix, "uv-receipt.toml"))


def doctor_groups(tools: list[Tool], broken: list[Broken], settings: Settings | None = None,
                  verify: core.Verify | None = None) -> list[tuple[str, list[core.Check]]]:
    """Every check of this computer, grouped: "smtv" (the shared ones and the window), then each tool's own, and tools that
    are installed but do not load under their own name. A tool whose checks crash gets one failed row, never breaks the rest.
    `verify`: how the model check tries a saved key (the window's «Check again»)."""
    settings = settings or Settings.load()
    try:
        own = core.core_checks(settings, verify)
    except Exception as e:  # noqa: BLE001 — the window still shows every other row, and the crash itself as one
        own = [core.Check("Clip It! checks", core.WARN, f"the checks crashed: {type(e).__name__}: {e}"[:300], id="smtv-checks")]
    groups: list[tuple[str, list[core.Check]]] = [("smtv", [*own, window_check()])]
    for t in tools:
        try:
            rows = list(t.checks(settings))
        except Exception as e:  # noqa: BLE001
            rows = [core.Check(f"{t.name}", core.FAIL, f"its checks crashed: {type(e).__name__}: {e}", id=f"{t.name}-checks")]
        if rows:
            groups.append((t.name, rows))
    groups += [(b.name, [core.Check(b.name, core.FAIL, f"installed but does not load: {b.error}", f"smtv add {b.name}", id=f"{b.name}-broken")]) for b in broken]
    return groups


def doctor_rows(tools: list[Tool], broken: list[Broken], settings: Settings | None = None) -> list[core.Check]:
    """Every check of this computer in one list (`smtv doctor`)."""
    return [row for _, rows in doctor_groups(tools, broken, settings) for row in rows]


def plugins(tools: list[Tool], broken: list[Broken]) -> list[dict]:
    """The cards under Plugins: installed tools (working or broken), then the ones that can be added, then the announced
    ones. A broken tool is shown only here, so the rest of the window never depends on it."""
    out, seen = [], set()
    for t in tools:
        page = t.page
        out.append({"name": t.name, "status": "installed", "version": t.version, "summary": t.summary,
                    "about": i18n.texts(page.about, page.folder / "i18n") if page else {}, "icon": page.icon if page else "", "title": page.title if page else t.name})
        seen.add(t.name)
    for b in broken:
        out.append({"name": b.name, "status": "broken", "error": b.error, "summary": CATALOG.get(b.name, ""), "title": b.name})
        seen.add(b.name)
    out += [{"name": n, "status": "available", "summary": s, "add": f"smtv add {n}", "title": n} for n, s in CATALOG.items() if n not in seen]
    out += [{"name": n, "status": "soon", "summary": s, "title": n, "soon": soon_item(n)} for n, s in SOON.items() if n not in seen]
    return out


def window_check() -> core.Check:
    """SMTV's own window (pywebview); without it the page opens in the browser, which works too."""
    from . import container
    if container.active():
        return core.Check("Clip It! window", core.OK, "in Docker the page opens in the browser; Chrome or Edge install it as an app with its own window", id="window")
    from .window import available
    why = available()
    if why is None:
        return core.Check("Clip It! window", core.OK, "Clip It! opens in its own window", id="window")
    fix = ('uv tool install --reinstall "smtv[vodcut]" --with "pywebview[qt]"' if sys.platform.startswith("linux")
           else 'uv tool install --reinstall "smtv[vodcut]"')
    return core.Check("Clip It! window", core.WARN, f"no window here, the page opens in the browser ({why})", fix, id="window")
