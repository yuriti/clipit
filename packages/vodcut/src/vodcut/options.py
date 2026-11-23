"""VodCut's switches, kept in the settings file under tools["vodcut"] and changed with `smtv vodcut set`.

loudness    bring every clip to −14 LUFS, the level platforms play shorts at
bleep       cover slurs against groups of people with a tone (ordinary swearing stays); the captions star them
peak_lines  end the clip on its last phrase in big letters
ad_blur     blur sponsor banners and promo codes; one more model request per clip
precise     Fit: cut each clip exactly by words in the 70 s around it (no idle lead-in); one model request per 4 clips
critic      look at every finished clip like an editor and make at most one edit (another layout, captions higher or lower,
            no hook); one model request per clip, two more and a render when it edits
local_download  «Download on this computer»: links through yt-dlp here instead of the StreamMoment account (stage 23);
            off, at the person's own risk (platforms change, YouTube may ask to sign in); yt-dlp is installed separately
recap       a 20–30 minute 16:9 recap of the whole stream after the clips (recap/): one strong model request for the story and
            two per five parts for the webcam and the ads; the parts are encoded on this computer
"""
from __future__ import annotations

from smtv_core.settings import Settings

TOOL = "vodcut"
# On (stage 12, 21.11.2026): on a 2 h 21 min Twitch VOD on an M-series Mac without a graphics card the recap took 389 s —
# about a third of the whole request (~20 min) — for a 10.7 min video; it runs after the clips, so they come no later.
RECAP_DEFAULT = True
# On (stage 14, 21.11.2026): on the same 2 h 21 min Twitch VOD, Mac without a graphics card, Codex, a check took 7–11 s
# per clip (about 10 s, one request with six small frames; ~20 000 input and ~75 output tokens through Codex, which bills
# nothing beyond the ChatGPT plan) against ~50 s for the rest of the clip; an edit adds a render and a second check,
# 33–39 s in all. It passed all six real clips and caught both clips rendered with the whole frame over a visible webcam
# (65–68 → 81–82 after one edit to a split).
CRITIC_DEFAULT = True
DEFAULTS = {"loudness": True, "bleep": True, "peak_lines": False, "ad_blur": True, "precise": True, "critic": CRITIC_DEFAULT,
            "recap": RECAP_DEFAULT, "local_download": False}
ABOUT = {"loudness": "loudness −14 LUFS", "bleep": "tone over slurs", "peak_lines": "last phrase in big letters",
         "ad_blur": "blur ads (one more model request per clip)",
         "precise": "exact cut by words (one more model request per 4 clips)",
         "critic": "check every clip like an editor, at most one edit (one more model request per clip)",
         "recap": "a 20–30 minute recap of the whole stream after the clips (encoded on this computer)",
         "local_download": "download links on this computer with yt-dlp instead of StreamMoment (at your own risk)"}


def load(settings: Settings) -> dict:
    """The switches with defaults for the ones never set; anything that is not true/false is ignored."""
    saved = settings.tools.get(TOOL) or {}
    return {k: saved[k] if isinstance(saved.get(k), bool) else v for k, v in DEFAULTS.items()}


def set_option(settings: Settings, name: str, value: bool) -> None:
    if name not in DEFAULTS:
        raise KeyError(name)
    settings.tools[TOOL] = {**(settings.tools.get(TOOL) or {}), name: value}


def local_download() -> bool:
    """«Download on this computer» is on (read now: the switch may change between two steps of a job)."""
    try:
        return bool(load(Settings.load())["local_download"])
    except Exception:  # noqa: BLE001 — unreadable settings: links go through StreamMoment, as by default
        return False
