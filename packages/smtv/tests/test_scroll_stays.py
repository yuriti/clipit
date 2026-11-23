"""Scrolling stays where the person put it (owner, 22.11).

A running request changes its page every second. Since V6 the page never rebuilds what it already shows: every part
follows the state by key and changes only the node that changed (dom.js, tested with node --test in tests/web), so the
widgets column, the live feed and the page keep their scroll by themselves and need no saving and restoring. In the clip
viewer the transcript follows the word being said, but not while the person scrolls the side by hand: it waits a few
seconds after the last wheel, finger, scrollbar or key move, and a click on a line gives the following back at once.
"""
from __future__ import annotations

import re
from pathlib import Path

SECTION = (Path(__import__("vodcut").__file__).parent / "web" / "section.js").read_text(encoding="utf-8")


def test_redraw_changes_nodes_in_place():
    assert "scrollers" not in SECTION                                    # nothing to restore: nothing is rebuilt
    job = SECTION[SECTION.index("export function mountJob"):SECTION.index("// --- the viewer")]
    # the only full fills: the board, built once per request (or its error), and the recap viewer's side once loaded
    fills = set(re.findall(r"(\w+(?:\.\w+)*)\.replaceChildren\(", job))
    assert fills == {"root", "info"}, fills
    assert "dirty" not in SECTION and "function draw()" not in SECTION       # signals and effects, not a dirty set (V6)
    assert "clock = setInterval(() => { if (S?.running) now.value = Date.now() / 1000; }, 1000);" in SECTION


def test_transcript_follow_yields_to_the_hand():
    assert re.search(r'for \(const ev of \["wheel", "touchmove", "pointerdown", "keydown"\]\) side\.addEventListener\(ev, byHand', SECTION)
    assert 'if (performance.now() >= handsOff) reveal(side, litLine, "y")' in SECTION
    assert "onclick: () => { handsOff = 0; video.currentTime = l.start;" in SECTION
    # every other reveal of the side is the clip switch, which resets the pause too
    assert "side.scrollTop = 0; handsOff = 0;" in SECTION
