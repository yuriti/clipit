# Clip It!'s icons

- `clip-it.svg` — the logo: «Clip / It!» on the purple square. The letters are the font Bitter (Black Italic), turned
  into outlines, so no font file ships; Bitter is © The Bitter Project Authors, SIL Open Font License 1.1
  (https://github.com/solmatas/BitterPro).
- `clip-it-small.svg` — the same art as «C!» for 32 px and less (the tab's icon, Windows' small sizes).
- `clip-it-mac.svg` — the logo on Apple's icon grid (an 824 px rounded square on 1024, 185 px corners, a soft shadow).

The PNGs are made from them by `python scripts/make_icons.py` (on a Mac) and committed: `icon-<size>.png` for Windows'
.ico, the page's manifest and notifications, `icon-mac-<size>.png` for the .icns.
