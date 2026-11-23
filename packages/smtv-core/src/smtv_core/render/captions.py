"""Burned-in captions and the hook card, as an ASS file for libass. Style kinetic_pop_v1, as in production:

- words appear in groups of up to 5 (a new group after a pause > 600 ms, a sentence end or a new segment);
- the active word pops in coloured and settles white; the rest of the group waits dimmed;
- the hook is a dark rounded card for the first seconds: at the top of a full-frame clip, on the seam between the
  webcam and the scene in a split one, so it never covers the streamer's face;
- with a peak (render/peak.py) the clip's last phrase slams in big letters and the ordinary captions give way to it.

Text is upper-cased with str.upper(), which works for any language.
"""
from __future__ import annotations

from . import peak as peaks
from .fonts import FACE, text_width
from .layout import SLOTS, H, W

CAPTION_Y = {"lower": 1400, "center": 1000, "upper": 600}
CAPTION_SIZE, CAPTION_MAX_W, CAPTION_LINE_H = 96, 940, 104
PALETTES = {"yellow_lime": ("FFE14D", "C8FF3D"), "white_cyan": ("5CE1FF", "FFE14D"), "pink_violet": ("FF5CAA", "B98CFF"),
            "orange_white": ("FF9F1C", "FFFFFF")}
INK, WHITE = "111111", "FFFFFF"
LAYER_DIM, LAYER_WORD, LAYER_HOOK = 60, 61, 75
SENTENCE_END = (".", "?", "!", "…")


def bgr(hex_rgb: str) -> str:
    return f"&H{hex_rgb[4:6]}{hex_rgb[2:4]}{hex_rgb[0:2]}&".upper()


def esc(text: str) -> str:
    """Text for an ASS line. libass has no escape for a backslash: `a\\Nb` from a transcript would break the line, so a
    word joiner (invisible) goes after every backslash and no override tag can form."""
    return text.replace("\\", "\\\u2060").replace("{", "\\{").replace("}", "\\}").replace("\r", " ").replace("\n", " ").replace("\0", "")


def ts(ms: float) -> str:
    cs = round(max(0, ms) / 10)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def rounded_rect(w: float, h: float, radius: float) -> str:
    w, h, radius = round(w), round(h), round(radius)
    return (f"m {radius} 0 l {w - radius} 0 b {w} 0 {w} 0 {w} {radius} l {w} {h - radius} b {w} {h} {w} {h} {w - radius} {h} "
            f"l {radius} {h} b 0 {h} 0 {h} 0 {h - radius} l 0 {radius} b 0 0 0 0 {radius} 0")


HOOK_Y_TOP = 300        # card centre in a full-frame clip
HOOK_SEAM_REACH = 80    # in a split clip the card reaches this far up into the webcam, below the face


def seam_y(mode: str) -> int | None:
    """The y of the webcam/scene seam for a split layout mode, None for a full-frame one."""
    return SLOTS[mode][0] if mode in SLOTS else None


def groups_of(words: list[dict]) -> list[list[dict]]:
    """words: {'text', 's', 'e' (ms), 'seg'} in clip time."""
    groups, cur = [], []
    for w in words:
        prev = cur[-1] if cur else None
        if prev and (w["s"] - prev["e"] > 600 or len(cur) >= 5 or prev["text"].strip().endswith(SENTENCE_END) or w["seg"] != prev["seg"]):
            groups.append(cur)
            cur = []
        cur.append(w)
    if cur:
        groups.append(cur)
    return groups


def build_ass(words: list[dict], duration_ms: float, hook: str = "", hook_end_ms: float = 3000, position: str = "lower",
              palette: str = "yellow_lime", peak: "peaks.Peak | None" = None, seam: int | None = None) -> str:
    events: list[tuple[int, float, float, str]] = []

    def add(layer, start, end, text):
        end = min(end, duration_ms)
        if end > start:
            events.append((layer, start, end, text))

    active_hex, _ = PALETTES[palette]
    ACTIVE, WHITE_C, INK_C = bgr(active_hex), bgr(WHITE), bgr(INK)
    space = text_width(" ", CAPTION_SIZE) + 10
    base_y = CAPTION_Y[position]
    in_peak = (lambda w: w["s"] >= peak.start_ms - 10) if peak else (lambda w: False)
    groups = groups_of([w for w in words if w["text"].strip() and not in_peak(w)])
    for gi, group in enumerate(groups):
        g_end = group[-1]["e"] + 350
        if gi + 1 < len(groups):
            g_end = min(g_end, groups[gi + 1][0]["s"] - 20)
        if peak:
            g_end = min(g_end, peak.start_ms)
        lines = [{"items": [], "width": 0.0}]
        for w in group:
            shown = esc(w["text"].strip().upper())
            width = text_width(shown, CAPTION_SIZE)
            line = lines[-1]
            if line["items"] and line["width"] + space + width > CAPTION_MAX_W:
                lines.append(line := {"items": [], "width": 0.0})
            line["width"] += (space if line["items"] else 0) + width
            line["items"].append((w, width, shown))
        top = base_y - (len(lines) - 1) * CAPTION_LINE_H / 2
        flat = [w for line in lines for w, _, _ in line["items"]]
        for li, line in enumerate(lines):
            x = W / 2 - line["width"] / 2
            y = round(top + li * CAPTION_LINE_H)
            for w, width, shown in line["items"]:
                cx = round(x + width / 2)
                x += width + space
                k = flat.index(w)
                nxt = flat[k + 1] if k + 1 < len(flat) else None
                active_ms = round((nxt["s"] if nxt else g_end) - w["s"])
                tags = (f"\\an5\\fs{CAPTION_SIZE}\\bord7\\shad0\\3c{INK_C}\\1c{ACTIVE}\\move({cx},{y + 22},{cx},{y},0,110)\\fad(60,0)"
                        f"\\fscx62\\fscy62\\t(0,90,\\fscx114\\fscy114)\\t(90,170,\\fscx100\\fscy100)\\t({active_ms},{active_ms + 80},\\1c{WHITE_C})")
                group_start = max(0, group[0]["s"] - 50)
                if w["s"] - group_start > 40:
                    add(LAYER_DIM, group_start, w["s"], f"{{\\an5\\pos({cx},{y})\\fs{CAPTION_SIZE}\\bord5\\shad0\\3c{INK_C}\\1c{WHITE_C}\\alpha&HB0&\\fad(80,0)}}{shown}")
                add(LAYER_WORD, w["s"], g_end, f"{{{tags}}}{shown}")

    if hook.strip():
        text, size = hook.strip().upper(), 72
        rows = [text]
        if text_width(text, size) > 880 and " " in text:
            spaces = [i for i, c in enumerate(text) if c == " "]
            cut = min(spaces, key=lambda i: abs(i - len(text) / 2))
            rows = [text[:cut], text[cut + 1:]]
        card_w = max(text_width(r, size) for r in rows) + 72
        card_h = len(rows) * size * 1.08 + 56
        life = round(min(hook_end_ms, duration_ms))
        hook_center_y = HOOK_Y_TOP if seam is None else round(seam - HOOK_SEAM_REACH + card_h / 2)
        pop = (f"\\an5\\pos(540,{hook_center_y})\\org(540,{hook_center_y})\\fscx40\\fscy40\\frz-4\\t(0,180,\\fscx106\\fscy106\\frz-2)"
               f"\\t(180,300,\\fscx100\\fscy100)\\t({life - 160},{life},\\alpha&HFF&\\fscx90\\fscy90)")
        add(LAYER_HOOK, 0, life, f"{{\\p1\\bord0\\shad0\\1c{INK_C}\\1a&H18&{pop}}}{rounded_rect(card_w, card_h, 26)}{{\\p0}}")
        add(LAYER_HOOK + 1, 0, life, f"{{\\fs{size}\\bord0\\shad0\\1c{WHITE_C}{pop}}}" + "\\N".join(esc(r) for r in rows))

    if peak:
        for event in peaks.events(peak, ACTIVE, INK_C, WHITE_C):
            add(*event)

    head = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 2", "ScaledBorderAndShadow: yes", "YCbCr Matrix: TV.709", "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
            "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            f"Style: Motion,{FACE},64,&H00FFFFFF,&H00FFFFFF,&H00111111,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,0,0,0,1", "",
            "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    body = [f"Dialogue: {layer},{ts(s)},{ts(e)},Motion,,0,0,0,,{text}" for layer, s, e, text in sorted(events, key=lambda e: (e[1], e[0]))]
    return "\n".join(head + body) + "\n"


def clip_words(segments: list[dict], start_s: float, end_s: float) -> list[dict]:
    """Transcript words inside [start_s, end_s] in clip time (ms), with their segment index."""
    out = []
    for si, s in enumerate(segments):
        if s["end"] < start_s or s["start"] > end_s:
            continue
        for w in s.get("words", ()):
            if start_s - 0.05 <= w["start"] and w["end"] <= end_s + 0.05:
                out.append({"text": w["word"].strip(), "s": round((w["start"] - start_s) * 1000), "e": round((w["end"] - start_s) * 1000), "seg": si})
    return out
