# VodCut

The reference tool: clips and a recap from a stream recording. Rules of the whole repository: the root `AGENTS.md`;
shared code (events, models, speech, rendering, links through StreamMoment): `packages/smtv-core/AGENTS.md`.
Tests: `packages/vodcut/tests`.

- The pipeline (`pipeline.py`) runs its steps itself, in order, and continues after an interruption: sound
  (`ingest.py`: a file, or a link through StreamMoment; `local_download.py` with yt-dlp only when the person turned
  on «Download on this computer»), speech, `pass1.py` (scan the transcript in windows), `pass2.py` (rate episodes),
  `pick.py` (choose clips), `fit/` (exact trims), `render.py` (clips through `smtv_core.render`), `recap/`.
- Every step writes its result into the job folder and its facts into the journal; a step that already has its
  result is skipped on a rerun.
- Its agents and their prompts: `agents.py` (prompts in the `prompts` repository, the `new-agent` skill).
- Its page section and settings: `page.py`, `options.py`, `web/`; its command line: `tool.py`, `console.py`.
