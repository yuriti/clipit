# smtv

One command for [StreamMoment](https://github.com/yuriti/clipit) tools: open-source clippers for long Twitch and YouTube streams that run on your own computer. Pick the tools you need; they plug into `smtv` on their own.

```bash
uv tool install "smtv[vodcut]"
```

```bash
smtv serve
```

The first run from a terminal also puts an SMTV icon on this computer (Applications on macOS, the desktop and Start menu on Windows, the applications menu on Linux): from then on start SMTV by double-clicking it. SMTV opens in its own window, like any program; closing the window quits it (while jobs run it asks whether to go on in the background). To remove SMTV: Settings → System → Remove SMTV, or `smtv uninstall` (your clips stay unless you add `--data`).

```bash
smtv doctor
```

| Command | What it does |
|---|---|
| `smtv list` | installed tools and the ones you can add |
| `smtv add vodcut` | add a tool |
| `smtv doctor` | check this computer and say what to fix |
| `smtv serve` | open the page (clips, jobs live, settings) |
| `smtv shortcut`, `smtv shortcut --remove` | the SMTV icon (made by itself on the first run) |
| `smtv app` | SMTV in its own window (what the icon runs) |
| `smtv uninstall [--data]` | remove SMTV from this computer |
| `smtv model set --provider … [--id …]`, `smtv model key [--id …]`, `smtv model show` | add a provider and its key (the window: Settings → Providers) |
| `smtv vodcut …` | a tool's own commands |

**Status: early development.** License: MIT

## Changelog

The SMTV window shows the entries newer than the installed version before an update: one `### <version>` per release,
one `- ` line per change, plain text.

### 0.1.0
- First build: SMTV in its own window with Home, Plugins, Settings and the phone by QR code.
- Settings → AI: connect the AI with your own key or for free on this computer (the StreamMoment account is coming soon); Settings → AI steps: pick which AI does each step.
- VodCut: a stream recording or a file in, vertical clips with captions and the streamer's webcam out, plus a recap.
- Requests wait in a queue; updates and plugins are installed from the window.
- Settings → About: what's new, the SMTV core, what is coming, and support for the project.
