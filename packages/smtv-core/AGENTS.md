# smtv-core

Shared code of every SMTV tool: settings and keys, model providers and agents, prompts (a pinned copy), speech
recognition, rendering, system checks, job events, the StreamMoment account and downloads through it. Rules of the
whole repository: the root `AGENTS.md`. Tests: `packages/smtv-core/tests`.

- Nothing here imports `smtv` or a tool: the core is below both.
- A change to a public contract here (job events, the tool contract in `tool.py`, settings) is a change for every
  tool: follow the versioning rules below and keep older readers working.

## Job events (public contract)

A job reports what it does only through its event journal (`smtv_core.events.Journal`, `events.jsonl` in the job folder), never with `print`. The command line, the page, subscribers, and later the cloud and MCP all read the same events; the command line turns them into text with the tool's own formatter (`vodcut/console.py`).

- Envelope: `n` (1, 2, 3… continuing across reruns), `t` (unix time), `type`, `v` (contract version), `job` (job folder name), `tool`, `data`.
- The contract is `smtv_core/events/schema.json`: the envelope and the data of every type. A new field or type raises the minor version; renaming or removing one, or changing its meaning, raises the major version. Readers ignore fields they do not know. Every field a tool writes is declared there; a test checks every event the pipeline writes against it.
- Events are facts in the past tense. The pipeline calls its steps itself, in order; an event never starts a step.
- Events carry short data and paths of job files relative to the job folder, never whole transcripts or frames.
- Commands (cancel, run again) are a separate API, not events (the page: `POST /api/jobs/<tool>/<job>/cancel`). No outside bus (Redis, Kafka): the journal file and in-process subscribers.
- «Run again (a new request)» on a finished request never overwrites it: `POST /api/jobs/<tool>/<job>/again` asks the tool's `Page.again(folder, args)` for a new job in a new folder (VodCut: `<name>-2`, `-3`…, the audio already fetched taken over by a hard link) and starts it; the old request stays. «Continue» (`restart`) is for a paused, stopped or failed one.
- Pause (`smtv_core.pause`): the page asks a running job to stop at its next safe point (`POST /api/jobs/<tool>/<job>/pause` writes `pause.request` into the job folder; only for a tool with `Page.pause`). The job checks it between its steps and between clips (`checkpoint`), writes `cancelled` with `graceful: true` and exits cleanly; nothing done is lost. «Stop now» is `cancel` (the process is killed; the step it was in runs again). A new run removes the request first.
- Contract 1.4 added `recap_ready` (VodCut's recap, the `recap` switch: `file`, `cover`, `chapters_file`, `description_file` as job files under `recap/`, `title`, `duration_s`, `source_s`, `parts`, `chapters` with their start in the video, `shots`, `ads_blurred`, `music_risk`, `encoder`, `fps`, `encoded`/`kept` parts, `seconds`, `existing`), `recap_failed` (`error`; the clips stay) and `done` with `stage: recap` carrying `skipped` (the model found nothing worth a recap) or `failed` with a `reason`; the `recap` stage (`progress` with `stage: recap` and `step` story | video | look | encode, `done`/`total`). Nothing is published: tools that process never publish.
- Contract 1.3 added `clip_fitted` (VodCut's Fit, the `precise` switch: one per clip — `before` and `after` bounds, `cut_start_s`, `cut_end_s`, `cut_s`, `title` and `title_before` (Fit's title replaces pass 2's when Fit cut away more than a third of the clip), `by` model|kept, `status`, `fit_score`, `repaired`, `reason`), the `fit` stage (`stage` name `fit`, `progress` with `stage: fit`) and `start_s`/`end_s` in the render report rows.
- Contract 1.2 added `source_ready` and `cancelled.graceful`. `source_ready`: what the request is about (kind, title, channel, platform, length, link or file, language, the channel's picture as a job file), written right after the audio is in, on every run. Readers take a job's title and channel from it, never by asking again.
- Contract 1.1 added the `cancelled` type (written by the page after it stopped the job's process), `model_call.cost_usd` (from the prices in the model settings), `layout_chosen.frames` and `error.exit_code`.
- Subscribers plug in through the entry point group `smtv.subscribers` (a callable taking one event). Each runs in its own thread: a slow or failing subscriber never slows or stops the job (its first failure is logged and written as an `error` event with `stage: subscriber`). A subscriber that missed events reads the journal after the last number it saw (`events.read(job, after=n)` or `Journal.subscribe(fn, after=n)`).

## The StreamMoment account and our key (stage 22)

- The provider `streammoment` needs no key of the person: the window signs in to a StreamMoment account (`smtv_core/account.py`) and calls the model through our server, paid from the account's balance. Our server picks the model; it accepts only SMTV's own agents, and only a prompt holding its agent's anchor (`tests/test_account.py::ANCHORS` mirrors the server's list: change both with the prompts).
- Sign-in starts from the profile menu («Sign in») or Settings → Account; a finished sign-in adds StreamMoment to the providers once, last (removed later, it stays removed).
- Sign-in: loopback + PKCE on `127.0.0.1` (the browser comes back with a one-time code), or a device code typed on our page. The tokens are one secret in the keychain (`streammoment.session`); a refresh happens under a file lock (the page and a job are two processes). «Sign out on this computer» deletes them here even when the server cannot be reached.
- Every call has one idempotency key for all its retries: a lost answer is asked again and never charged twice. 402 (no balance) stops the run as a quota error.
- `streammoment.tv` is asked only by a button, before a sign-in, while the account panel is open and for ten minutes after a purchase; never in the background. Every failure to reach it says so and suggests a VPN.
- `SMTV_ACCOUNT_URL` points to a local test server (https, or http on this computer only).

## Links through StreamMoment (stage 23)

- VodCut does not depend on yt-dlp. A file of one's own always works, without an account or the internet. A link goes through the StreamMoment account (`smtv_core.media`): `Ticket(url)` opens a place in our server's queue (`POST /api/smtv/media/open`; the window shows «StreamMoment queue: place N»), `fetch("audio", dest)` writes the whole audio track, `fetch("video", dest, start, end)` only the segments over a clip or a recap part and returns where they start. Our server streams the platform's HLS segments as they come: nothing is stored there, nothing transcoded. Segments are fetched 16 at a time and written in order; a passing failure is tried again, a ticket the server forgot (SMTV slept) is opened again, a half-written file never stays.
- Only Twitch for now (`twitch.tv/videos/<id>`); YouTube and other sites get a plain «not yet: choose the file, or turn on Download on this computer». The server refuses with codes the window turns into words (`media.MESSAGES`): not signed in, daily hours used up, too long, subscribers only.
- A clip's piece: whole segments joined into one MP4 starting at 0 (`ffmpeg -c copy`), its offset in the recording kept next to it as `pieces/<clip>.mp4.offset`. One ticket per link for a whole render and for the recap's pieces (`render.close_tickets()` gives the slot back).
- «Download on this computer» (`local_download`, off by default, at the person's own risk): yt-dlp here, as before stage 23 (`vodcut/local_download.py`); yt-dlp is installed separately (the extra `vodcut[local]`, the command in `smtv doctor`). The check in `smtv doctor` is about links: signed in to StreamMoment (a warning when not: files work), or yt-dlp present when the switch is on.
