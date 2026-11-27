# SMTV for advanced users

The [README](../README.en.md) is enough to install SMTV and make clips. This page is for the rest: Docker, every AI
service SMTV works with, speech models, where keys are kept, and the commands.

## Commands

SMTV's window does everything; the same is available in a terminal:

| Command | What it does |
|---|---|
| `smtv app` | SMTV in its own window (what the SMTV icon runs) |
| `smtv serve` | the same page in the browser, only on this computer |
| `smtv doctor` | check this computer and say what to fix |
| `smtv list` · `smtv add <tool>` | installed tools and the ones you can add |
| `smtv vodcut <link or file>` | clips and a recap without the window |
| `smtv model …` · `smtv speech …` | the AI and the speech models |
| `smtv report` | a problem report: an archive without keys and a new GitHub issue; nothing is sent by itself |
| `smtv shortcut [--remove]` | make or delete the SMTV icon |
| `smtv uninstall [--data]` | remove SMTV (clips and settings only with `--data`) |

On Windows with Smart App Control a terminal may refuse `smtv` the first time (uv's `smtv.exe` is not signed): run
`python -m smtv …` with the Python SMTV is installed on instead; the installer prints its full path. The icon is not
affected.

## Links and files

A video file of your own is read where it is, with no account; the recording itself is sent nowhere. A link (Twitch,
YouTube) needs **Download links myself** in VodCut's settings for now: the yt-dlp program downloads it on this computer
(`uv tool install "smtv[vodcut]" --with "vodcut[local]"`, or Settings → Computer check), at your own risk — platforms
change often, and YouTube may ask to sign in. Links through the StreamMoment account are built in and open together
with sign-in (coming soon): its server takes the recording from the platform in pieces and passes them straight to
SMTV, writing nothing to its disk; only the sound and the pieces the clips and the recap need are fetched.

## Without the installer

With uv: `uv tool install "smtv[vodcut]"` (on Windows add `--python ">=3.11,<3.14"`: SMTV's window is
tested up to Python 3.13 there), or `uvx "smtv[vodcut]" doctor` to try without installing.

## The downloaded apps

The `.dmg` and the Windows installer hold their own Python 3.12 ([python-build-standalone](https://github.com/astral-sh/python-build-standalone)),
SMTV with every dependency at the versions of `uv.lock`, and ffmpeg 9.1 with libass (macOS: Martin Riedl's static
build; Windows: Gyan's «essentials» build; both GPL, their license and source in the `ffmpeg` folder inside). Where:

- macOS: one `SMTV.app` for both processors: `Contents/Resources/python-arm64` and `python-x86_64` (each with its
  ffmpeg in `…/ffmpeg`; files the same in both are links to the arm64 copy). `Contents/MacOS/SMTV` (a small universal
  program, `install/app/launcher.c`) asks the hardware which processor this Mac has (`hw.optional.arm64`; under Rosetta
  `uname` would say x86_64) and starts `Contents/MacOS/smtv-python-<arch> -m smtv app` with `PYTHONHOME` set to that
  folder. Apple silicon on macOS 13 takes the Intel one under Rosetta. What fails before the window opens:
  `~/.smtv/logs/launch.log`.
- Windows: `%LOCALAPPDATA%\Programs\ClipIt` (installed by 0.1.0: `Programs\SMTV`, where updates stay; the ZIP:
  wherever it was unpacked). On top only `ClipIt.exe` (Python's
  `pythonw.exe` under the program's name, byte for byte, so Smart App Control lets it run), `ClipIt.exe.config`, the DLLs
  Windows loads before Python, `python312._pth` (Python's paths: everything else is in `app\`) and a how-to text. There
  is no `python.exe`: `ClipIt.exe` prints into a file or a pipe like it. A double click on `ClipIt.exe` opens the window
  (`app\Lib\site-packages\sitecustomize.py`); the Start menu icon runs `ClipIt.exe -m smtv app`.

Your own ffmpeg in SMTV's folder `bin/` still wins over the one inside. Commands work through the app's Python, for
example on a Mac with Apple silicon (Intel: `x86_64` instead of `arm64`):

```bash
PYTHONHOME=/Applications/SMTV.app/Contents/Resources/python-arm64 /Applications/SMTV.app/Contents/MacOS/smtv-python-arm64 -m smtv doctor
```

on Windows: `"%LOCALAPPDATA%\Programs\ClipIt\ClipIt.exe" -m smtv doctor | more` (the pipe shows its output). Updates: the window downloads the new
installer, checks it against the signed list of releases and opens it. Build them yourself: `install/app/build.py`
(see its first lines).

## Docker

For a home server, a NAS, Linux without a desktop, or when you would rather not install anything into the system:

```bash
docker compose up -d --build
```

```bash
docker compose logs smtv | grep token=
```

Open that link (`http://127.0.0.1:8642/?token=…`): the same page as in SMTV's window, and the browser remembers the key. Chrome and Edge then offer **Install SMTV** in the address bar — its own window, icon, notifications and the number of running jobs on the icon.

- **Only this computer** sees the page: the port is published on `127.0.0.1`. For a home server publish it wider on purpose (`"8642:8642"`) and list the names it is opened by in `SMTV_HOSTS`; every browser still needs the key. To cut off every browser that has the key: delete `access-key` in the data volume and restart.
- **Data** — settings, keys (encrypted, see below), speech models (~1 GB, downloaded when first needed) and clips — live in the volume `smtv-data`: a new container loses nothing. `docker compose down -v` deletes them.
- **Updates**: a new version is a new image (`docker compose up -d --build`); SMTV does not update itself in a container. Plugins come with the image; your own plugin is your own image on top of it.
- **Models**: API keys, OpenRouter, or Ollama and other model servers on the host (found at `host.docker.internal`). The Codex and Claude Code CLIs are not available in Docker.
- **Graphics card**: only Linux or Windows with WSL and an NVIDIA card (uncomment `deploy` in `compose.yaml`). On a Mac Docker runs without one and slower; install with `uv` there.
- **Phone**: set `SMTV_LAN_ADDRESS` to the host's address in the home network and publish the port on it; Settings → Phone shows the QR code.

## AI services and keys

Settings → **AI**: connect one or more — OpenAI, OpenRouter, Claude API, Gemini, a model server on this computer (Ollama, LM Studio, vLLM, llama.cpp: no key; **Find on this computer** looks at their usual addresses), another cloud service by your own key (DeepSeek, Groq, Mistral, xAI, Together, Fireworks, Qwen, Kimi, GLM, Cerebras), any OpenAI-compatible address, the Codex CLI or the Claude Code CLI; several of one kind under different keys and names are fine. Each preset knows how its server takes the answer's JSON schema; a server that refuses the schema is asked once more for a plain JSON object, and SMTV checks that answer against the schema itself.

**Ollama** is called through its own API, not the OpenAI-compatible one: there SMTV sets the context window by the length of each prompt (Ollama's own default is a few thousand tokens and it silently cuts a longer prompt — an hour of a stream would lose most of its words). Models are downloaded and removed right in its entry (Settings → AI → Ollama), with their size first. Recommended: `qwen3:14b` for text (16 GB of video memory) or `qwen3:8b`, `qwen3-vl:8b` or `gemma3:12b` for frames — local models are weaker than the cloud ones and these were not tested yet; models under 7B break the JSON. SMTV never installs Ollama or another server: you install it, SMTV finds it. Settings → **AI steps**: each step of each tool takes a provider and a model from dropdowns; by default the recommended ones (from the prompts bundled with SMTV, [`packages/smtv-core/src/smtv_core/prompts`](../packages/smtv-core/src/smtv_core/prompts/models.json), marked tested or not). Prices come from a built-in table or from OpenRouter; the CLIs are paid by your subscription.

## Speech to text

Settings → **Speech to text**: which model turns speech into text with the time of every word. By default Russian takes **GigaAM-v3**, Parakeet's 25 European languages take **Parakeet-TDT v3**, every other language **Whisper large-v3-turbo** on this computer (faster-whisper: an NVIDIA card or the processor; on a Mac only the processor, slower). Any language can take another model, also **Whisper in the cloud by your own key** — Groq (`whisper-large-v3-turbo`, about $0.04 an hour of sound) or OpenAI (`whisper-1`); the sound then leaves your computer, cut into pieces under 25 MB. Each model shows where it runs, its languages, licence, size and speed, with **Download** and **Remove**. Models live only in the `models` folder of SMTV; nothing needs administrator rights.

**The CLIs run on your personal subscription** (ChatGPT for Codex, Claude for Claude Code). Following the rules of OpenAI and Anthropic is up to you; StreamMoment is not responsible for the subscription. **We strongly advise against both CLIs:** the providers' rules may forbid other programs from using a subscription (Anthropic's Claude Code page says so outright), and the account may be restricted. SMTV only provides the technical option, at your own risk; use an API key instead. The rules in force: [OpenAI Terms of Use](https://openai.com/policies/terms-of-use/), [OpenAI Usage Policies](https://openai.com/policies/usage-policies/), [Claude Code: legal and compliance](https://code.claude.com/docs/en/legal-and-compliance), [Anthropic Consumer Terms](https://www.anthropic.com/legal/consumer-terms), [Anthropic Usage Policy](https://www.anthropic.com/legal/aup).

**Keys stay on your computer** and go only directly to the provider; StreamMoment never gets them, and they are never shown in the window, written to logs or put in a problem report.
- With a system keychain (macOS Keychain, Windows Credential Manager, Secret Service on Linux — install `smtv-core[keyring]`) the key is kept there.
- Without one (some Linux desktops, Docker) the key is encrypted in `secrets.json` in the SMTV folder; the encryption key is a separate file, `secrets.key`: on macOS and Linux beside it, readable only by you; on Windows in `%LOCALAPPDATA%\smtv` (it stays on this computer even when the profile is copied to a domain server), both inside your profile, which other users of the computer cannot open. This protects a key when the secrets file leaks on its own — a backup, a synced folder, a file sent by mistake. It does **not** protect from a program running under your own user on this computer: such a program can read both files, just as it can read an unlocked keychain.

## Problem reports

In SMTV: Settings → System → **Report a problem**, or the button under a failed request. Without the window (a server, Docker):

```bash
smtv report
```

SMTV shows what goes in, saves `smtv-report-<time>.zip` (versions, system, `smtv doctor`, settings, the failed request's journal and the end of the logs, crash files) and opens a new issue with the summary filled in; you drag the archive into it. Keys and tokens are cut out and your home folder shows as `~`; links to streams and file names stay out unless you tick the box (`--names`). SMTV sends nothing by itself.
