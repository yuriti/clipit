"""Glass only in SMTV's own window on macOS (owner, 21.11).

Chrome painted bits of tiles and captions over the clip viewer: many blurred layers (`backdrop-filter`) over a grid of
videos. So: a browser tab (Chrome, Safari, a phone, Docker) and the Windows window are solid; CSS blur lives only under
`.glass`, which only the macOS window adds; «reduce transparency» makes the glass solid too; under an open viewer the
grid is paused and has no blurred layer at all.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from smtv import window
from smtv.serve import WEB

SECTION = Path(__import__("vodcut").__file__).parent / "web"


def rules(css: str) -> list[tuple[list[str], str, str]]:
    """(at-rule stack, selector, body) for every plain rule, comments dropped."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    out, stack, i, buf = [], [], 0, ""
    while i < len(css):
        ch = css[i]
        if ch == "{":
            head = buf.strip(); buf = ""
            if head.startswith("@"):
                stack.append(head)
            else:
                end = css.index("}", i)
                out.append((list(stack), head, css[i + 1:end]))
                i = end
        elif ch == "}":
            if stack:
                stack.pop()
            buf = ""
        else:
            buf += ch
        i += 1
    return out


def blurred(css: str) -> list[tuple[list[str], str]]:
    return [(at, sel) for at, sel, body in rules(css) if re.search(r"backdrop-filter:\s*blur", body)]


@pytest.mark.parametrize("path", [WEB / "app.css", SECTION / "section.css"])
def test_blur_is_only_under_the_glass_of_the_mac_window(path):
    for at, selector in blurred(path.read_text(encoding="utf-8")):
        for one in selector.split(","):
            assert one.strip().startswith(".glass "), f"{path.name}: blur outside .glass: {one.strip()}"
        assert not any("reduced-transparency" in a for a in at), f"{path.name}: blur under reduce transparency"


def test_only_the_mac_window_turns_the_glass_on():
    assert "classList.add('glass')" in window.GLASS_SCRIPT
    # nobody else adds the class: not the page, not the server's HTML, not a plugin's section
    for path in (WEB / "app.js", WEB / "index.html", SECTION / "section.js"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"""add\(\s*['"]glass['"]|toggle\(\s*['"]glass['"]|class="[^"]*\bglass\b""", text), path.name
    src = Path(window.__file__).read_text(encoding="utf-8")
    assert src.count("GLASS_SCRIPT") == 2 and "def _mac_glass" in src        # defined once, used only by _mac_glass
    assert src.index("GLASS_SCRIPT,") > src.index("def _mac_glass")


def test_reduce_transparency_makes_the_glass_solid_in_both_themes():
    css = re.sub(r"/\*.*?\*/", "", (WEB / "app.css").read_text(encoding="utf-8"), flags=re.S)
    solid = {}
    for at, selector, body in rules(css):
        if any("prefers-reduced-transparency: reduce" in a for a in at) and selector.startswith(".glass"):
            for name in ("--frame-bg", "--panel-bg", "--list-bg", "--panel"):
                m = re.search(rf"{name}:\s*([^;]+);", body)
                if m:
                    solid.setdefault(selector, {})[name] = m.group(1).strip()
    assert ".glass" in solid and '.glass[data-theme="light"]' in solid and '.glass:not([data-theme="dark"])' in solid
    for selector, values in solid.items():
        assert set(values) == {"--frame-bg", "--panel-bg", "--list-bg", "--panel"}, selector
        for value in values.values():
            assert re.fullmatch(r"#[0-9a-f]{6}", value), f"{selector}: not solid: {value}"
    assert solid['.glass[data-theme="light"]']["--frame-bg"] == "#f9f9f9"      # a light window stays light


def test_the_grid_under_an_open_viewer_is_paused_and_flat():
    js = (SECTION / "section.js").read_text(encoding="utf-8")
    css = (SECTION / "section.css").read_text(encoding="utf-8")
    hold = js[js.index("function holdPage("):]
    hold = hold[:hold.index("\n  }\n") + 4]
    assert "v.pause()" in hold and 'classList.add("vc-viewing")' in hold
    assert "!viewer.contains(v)" in hold                     # the viewer's own video keeps playing
    assert 'classList.remove("vc-viewing")' in hold and "play()" in hold     # closing plays again what was playing
    # both viewers (a clip and the recap) hold the page and let it go when closed
    assert js.count("release = holdPage(back);") == 2 and js.count("back.remove(); release();") == 2
    # under the viewer no blurred layer is left on the cards
    assert re.search(r"\.vc-viewing \.vc-play, \.vc-viewing \.vc-heart \{ backdrop-filter: none;", css)
    # and the viewer itself has none of its own
    for at, selector in blurred(css):
        assert ".vc-v" not in selector, selector
