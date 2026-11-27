<!-- languages -->
[Русский](../free-ai-on-your-computer.md) · **English** · [Қазақша](../kk/free-ai-on-your-computer.md) · [Oʻzbekcha](../uz/free-ai-on-your-computer.md) · [Azərbaycanca](../az/free-ai-on-your-computer.md) · [Кыргызча](../ky/free-ai-on-your-computer.md) · [简体中文](../zh-CN/free-ai-on-your-computer.md) · [日本語](../ja/free-ai-on-your-computer.md) · [한국어](../ko/free-ai-on-your-computer.md) · [Tiếng Việt](../vi/free-ai-on-your-computer.md) · [Bahasa Indonesia](../id/free-ai-on-your-computer.md) · [हिन्दी](../hi/free-ai-on-your-computer.md) · [বাংলা](../bn/free-ai-on-your-computer.md) · [Español](../es/free-ai-on-your-computer.md) · [Português](../pt-BR/free-ai-on-your-computer.md) · [Deutsch](../de/free-ai-on-your-computer.md)

> 🌐 This page was translated automatically from the [Russian original](../free-ai-on-your-computer.md). Help improve it: [Weblate](https://hosted.weblate.org/engage/smtv/) · [pull request](https://github.com/yuriti/clipit/pulls).

# A free AI on your computer

The AI can run right on your computer, for free: nothing leaves it, and there is nothing to pay. You need a program
that runs AI models — **Ollama** or **LM Studio** — and a model, for example **Qwen**. Clip It! finds the program by itself.

**Honestly:** models that fit on a home computer are weaker than the cloud ones, so the clips come out worse, and none
of the recommended models was tested with Clip It! yet. If the result disappoints you, try the [account](account.md) or
[a key](get-a-key.md).

## 1. Which model fits your computer

What matters is the **video memory** of your graphics card (on a Mac with Apple silicon: the whole memory).

| Video memory | Model | Download | Notes |
|---|---|---|---|
| less than 8 GB | — | — | Too little: use the account or a key |
| 8 GB | `qwen3:8b` | 5.2 GB | The lightest that works well enough |
| 10–12 GB | `qwen3-vl:8b` or `gemma3:12b` | 6.1 / 8.1 GB | These also look at frames of the video |
| 16 GB and more | `qwen3:14b` | 9.3 GB | The best of the four |

Models smaller than 7B («7 billion») are not recommended: they break the answers Clip It! needs.

**How to find your video memory:**
- **Windows:** press Ctrl+Shift+Esc → **Performance** → **GPU** → **Dedicated GPU memory**.
- **Mac:** Apple menu → **About This Mac** → **Memory**. A Mac shares memory with the AI: with 16 GB take `qwen3:8b`,
  with 32 GB or more `qwen3:14b`.

## 2a. Ollama (simplest)

1. Download Ollama from [ollama.com/download](https://ollama.com/download) and install it like any program. It starts
   by itself and lives near the clock.
2. In Clip It!: **Settings → AI → Free, on this computer → Find on this computer**. Clip It! finds Ollama.
3. Open **Ollama** in the list: Clip It! shows the recommended models with their size. Press **Download** next to the one
   from the table above and wait (5–10 GB).
4. Done. Clip It! picks that model for its steps by itself.

Clip It! sets Ollama's memory for each request so that the whole stream text fits; you do not need to change Ollama's
settings.

## 2b. LM Studio

1. Download LM Studio from [lmstudio.ai/download](https://lmstudio.ai/download) and install it.
2. In LM Studio open **Discover**, search for **Qwen3 8B** (or 14B, by the table) and press **Download**.
3. Open the **Developer** tab and turn on **Start server** (it listens on port 1234). Load the model there.
4. In Clip It!: **Settings → AI → Free, on this computer → Find on this computer**. Clip It! finds LM Studio.

## 3. Make a clip

Give Clip It! a [video file](first-clip.md). A link to Twitch or YouTube needs the [account](account.md) even with a free
AI: the account fetches the recording.

The free AI works slower than a cloud one; a long stream can take a few hours. Leave the computer on.
