"""The caption font (Montserrat Black, SIL OFL 1.1) and text width in ASS units.

libass sizes text by winAscent + winDescent, so a width measured in em at `size` is divided by that ratio (1.562 for
Montserrat): the same rule the captions are laid out by in production.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

FONTS_DIR = Path(__file__).resolve().parent / "fonts"
FACE = "Montserrat Black"


@lru_cache(maxsize=1)
def _fonts():
    from fontTools.ttLib import TTFont
    out = []
    for path in sorted(FONTS_DIR.glob("*.woff")):
        font = TTFont(str(path))
        cmap, hmtx = font.getBestCmap(), font["hmtx"].metrics
        os2, upem = font["OS/2"], font["head"].unitsPerEm
        out.append((cmap, hmtx, upem, (os2.usWinAscent + os2.usWinDescent) / upem))
    if not out:
        raise FileNotFoundError(f"caption fonts missing in {FONTS_DIR}")
    return out


def text_width(text: str, size: float) -> float:
    """Width in output pixels of `text` drawn with \\fs{size}."""
    fonts = _fonts()
    total = 0.0
    for ch in text:
        for cmap, hmtx, upem, scale in fonts:
            glyph = cmap.get(ord(ch))
            if glyph:
                total += hmtx[glyph][0] / upem * size / scale
                break
        else:  # not in Montserrat: libass falls back to another font; count it like an average letter
            total += 0.62 * size / fonts[0][3]
    return total
