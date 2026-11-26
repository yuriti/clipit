# smtv-core

Shared core of [StreamMoment](https://github.com/yuriti/clipit) tools: settings, model access (OpenAI-compatible servers including OpenRouter, Claude, Gemini, the Codex CLI and the Claude Code CLI), keys in the system keychain or encrypted in a file, system checks and the contract tools use to plug into `smtv`. Speech recognition and 9:16 rendering come next.

You normally do not install it directly: it comes with `smtv` and every tool.

License: MIT

## Changelog

The SMTV window shows the entries newer than the installed version before an update: one `### <version>` per release,
one `- ` line per change, plain text.

### 0.1.1
- The captions check waits for a slow first start of ffmpeg; Python 3.11 or newer.

### 0.1.0
- First build.
