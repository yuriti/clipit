"""Peak lines: the clip's last spoken phrase slammed onto the frame in big letters (the "clean slam" look).

The phrase is taken literally from the transcript: up to 3 lines of up to 16 characters; a phrase too long for three
lines keeps its ending, the punchline. Each line slams in as its first word is spoken and stays to the end of the clip;
the last line is larger and coloured. Ordinary captions give way for the peak's time.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .fonts import text_width

LINE_MAX_CHARS, MAX_LINES = 16, 3
PEAK_Y = 1250
LAYER_SLAM = 83
TEXT_MAX_W = 860            # room for the 4° tilt and the 108 % drift
PAUSE_MS = 600              # a longer pause ends the phrase
MAX_TAIL_GAP_MS = 2500      # a phrase that ended longer before the clip's end is no punchline
SENTENCE_END = (".", "?", "!", "…")


@dataclass(frozen=True)
class Peak:
    lines: tuple[str, ...]
    starts_ms: tuple[int, ...]   # when each line slams in, clip time
    end_ms: int                  # the clip's end

    @property
    def start_ms(self) -> int:
        return self.starts_ms[0]


def _letters(text: str) -> str:
    return re.sub(r"[^\w]|_", "", text.upper())


def split_words(words: list[str], count: int) -> list[str] | None:
    """`words` in `count` lines of at most 16 characters with the shortest longest line, or None."""
    if count == 1:
        line = " ".join(words)
        return [line] if len(line) <= LINE_MAX_CHARS else None
    best = None
    for cut in range(1, len(words) - count + 2):
        head = " ".join(words[:cut])
        if len(head) > LINE_MAX_CHARS:
            break
        rest = split_words(words[cut:], count - 1)
        if rest and (best is None or max(len(head), *map(len, rest)) < max(map(len, best))):
            best = [head, *rest]
    return best


def last_phrase(words: list[dict]) -> list[dict]:
    """The clip's last phrase: back from the last word until a pause or the end of the previous sentence."""
    words = [w for w in words if w["text"].strip()]
    if not words:
        return []
    start = len(words) - 1
    while start > 0:
        prev, cur = words[start - 1], words[start]
        if cur["s"] - prev["e"] > PAUSE_MS or prev["text"].strip().endswith(SENTENCE_END):
            break
        start -= 1
    return words[start:]


def choose(words: list[dict], duration_ms: float) -> Peak | None:
    """The peak for clip words {'text', 's', 'e'} (ms, clip time), or None when the clip has no punchline at its end."""
    phrase = last_phrase(words)
    if not phrase or duration_ms - phrase[-1]["e"] > MAX_TAIL_GAP_MS:
        return None
    spoken = [w["text"].strip() for w in phrase]
    for first in range(len(spoken)):
        tail = spoken[first:]
        # Two lines when there are two words or more: the slam builds up to the coloured last line.
        split = next((s for n in (2, 3, 1) if n <= len(tail) and (s := split_words(tail, n))), None)
        if split:
            used = phrase[first:]
            # Each line starts at the word that holds its first letter.
            offsets, acc = [], 0
            for w in used:
                offsets.append(acc)
                acc += len(_letters(w["text"]))
            starts, acc = [], 0
            for line in split:
                i = max(k for k, o in enumerate(offsets) if o <= acc)
                starts.append(round(used[i]["s"]))
                acc += len(_letters(line))
            return Peak(tuple(split), tuple(starts), round(duration_ms))
    return None


def _esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def events(peak: Peak, active: str, ink: str, white: str) -> list[tuple[int, float, float, str]]:
    """ASS events (layer, start ms, end ms, text) of the clean slam. Colours are ASS &HBBGGRR& strings."""
    n = len(peak.lines)
    ys = [PEAK_Y + 40] if n == 1 else [PEAK_Y - 60, PEAK_Y + 100] if n == 2 else [PEAK_Y - 150, PEAK_Y - 25, PEAK_Y + 120]
    out = []
    for i, (raw, start, y) in enumerate(zip(peak.lines, peak.starts_ms, ys)):
        last = i == n - 1
        text = raw.upper()
        size = 176 if last else 120
        size = min(size, int(size * TEXT_MAX_W / max(text_width(text, size), 1)))
        life = round(peak.end_ms - start)
        slam = (f"\\an5\\fs{size}\\org(540,{PEAK_Y})\\frz4\\shad0\\fscx240\\fscy240\\alpha&HFF&\\blur6"
                f"\\t(0,110,0.6,\\fscx100\\fscy100\\alpha&H00&\\blur0)\\t(110,170,\\fscx93\\fscy93)\\t(170,240,\\fscx100\\fscy100)"
                f"\\t(600,{max(life, 700)},\\fscx108\\fscy108)")
        out.append((LAYER_SLAM, start, peak.end_ms, f"{{{slam}\\pos(540,{y})\\bord9\\3c{ink}\\1c{active if last else white}}}{_esc(text)}"))
    return out
