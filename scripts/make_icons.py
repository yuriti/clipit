"""Every icon of Clip It! from its two drawings in packages/smtv/src/smtv/web/icons (run on a Mac: sips draws SVG):

    python scripts/make_icons.py

- clip-it.svg        the logo: «Clip / It!» on the purple square (Bitter Black Italic, outlined; SIL OFL 1.1), drawn
                     at each size straight from the drawing (16 px included), never a smaller copy of a large PNG;
- clip-it-mac.svg    the logo on Apple's icon grid: an 824 px rounded square, 185 px corners, a soft shadow.
The PNGs are committed (Windows' .ico, the .icns, the page's manifest and notifications use them); make them again
after a drawing changes. Only the image itself is kept in each PNG: nothing the drawing tool adds (EXIF and the like).
"""
from __future__ import annotations

import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

ICONS = Path(__file__).resolve().parents[1] / "packages" / "smtv" / "src" / "smtv" / "web" / "icons"
FULL = (16, 24, 32, 48, 64, 256)   # clip-it.svg
MAC = (512, 1024)               # clip-it-mac.svg → icon-mac-<size>.png
KEEP = (b"IHDR", b"PLTE", b"tRNS", b"sRGB", b"IDAT", b"IEND")


def plain_png(data: bytes) -> bytes:
    """The PNG with only the chunks that draw it."""
    out, i = data[:8], 8
    while i < len(data):
        n = struct.unpack(">I", data[i:i + 4])[0]
        if data[i + 4:i + 8] in KEEP:
            out += data[i:i + 12 + n]
        i += 12 + n
    return out


def render(svg: Path, size: int, dest: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out.png"
        subprocess.run(["sips", "-s", "format", "png", "-z", str(size), str(size), str(svg), "--out", str(out)],
                       check=True, capture_output=True)
        dest.write_bytes(plain_png(out.read_bytes()))


def main() -> int:
    if not shutil.which("sips"):
        print("sips is macOS's own tool: make the icons on a Mac")
        return 1
    for size in FULL:
        render(ICONS / "clip-it.svg", size, ICONS / f"icon-{size}.png")
    for size in MAC:
        render(ICONS / "clip-it-mac.svg", size, ICONS / f"icon-mac-{size}.png")
    print(f"icons made in {ICONS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
