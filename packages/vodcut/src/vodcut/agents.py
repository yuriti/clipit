"""VodCut's agents (stage 10): its own, and the shared ones of the core it uses while editing and checking. Their words
are in `web/i18n/<language>.json` under `agent.<id>.*` (the core's in the window's files)."""
from __future__ import annotations

from smtv_core.agents import Agent, Needs, core

SCAN = Agent(id="scan", purposes=("scan", "scan_repair"), prompt="vod/pass1-prompt.txt", schema="pass1", needs=Needs(level="strong"))

RATING = Agent(id="rating", prompt="vod/pass2-prompt.txt", schema="pass2", needs=Needs(level="medium"))

FIT = Agent(id="fit", purposes=("fit", "fit_repair"), prompt="fit/prompt-policy.txt", schema="fit", needs=Needs(level="medium"))

RECAP = Agent(id="recap", prompt="vod/recap-prompt.txt", schema="recap", needs=Needs(level="strong"))

AGENTS = [SCAN, RATING, FIT, RECAP, *core("layout", "banner", "critic")]
