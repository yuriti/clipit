"""YouTube asks some computers to sign in before it gives a video («confirm you're not a bot»). VodCut never reads the
person's browser or its cookies (that looks like breaking into the person's computer). It says that YouTube
wants an authorised download and offers the way: a video file (links through StreamMoment are Twitch only for now).
"""
from __future__ import annotations

import re

BOT_CHECK = re.compile(r"confirm you.{0,3}re not a bot|sign in to confirm", re.I)
SIGN_IN = "youtube_sign_in"            # in the error text: the window shows its own explanation


def sign_in_hint() -> str:
    return ("YouTube does not give this video without signing in. Fix: download the recording and choose the file "
            f"(smtv vodcut run <file>) [{SIGN_IN}]")
