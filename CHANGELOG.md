# Changes

What changes for the people who use SMTV, newest first. `smtv`, `smtv-core` and `vodcut` always come out together
under one version number.

## 0.1.0 — first release (date: the day it is published)

The first public version: SMTV turns a long stream recording into vertical clips and a recap on your own computer.

### Making clips

- **VodCut**: a link to a Twitch or YouTube recording, or a video file, in — 6–30 vertical clips out, for streams of
  6–12 hours too. Clips appear one by one while the rest are still being made.
- The streamer's webcam goes into the vertical frame next to the game; captions word by word; a short hook line at
  the start of each clip.
- **Precise trimming**: the start and end of every clip are moved to where the thought begins and ends.
- **A second look**: each finished clip is checked like an editor would, and fixed once when something is off
  (the layout, where the captions sit).
- **Recap**: a 20–30 minute horizontal video that retells the whole stream.
- Even loudness, the level platforms play shorts at; sponsor banners and promo codes blurred; slurs against groups of
  people covered with a tone (ordinary swearing stays). Each can be switched off.
- Before a request starts, SMTV says how long it should take; an interrupted request carries on from where it stopped.
- Requests wait in a queue and run one after another.
- A link is downloaded through the StreamMoment account, which stores nothing; a video file of your own needs no
  account. «Download links myself» does it on this computer instead (yt-dlp, at your own risk).

### Choosing the AI

- Three simple ways: through the StreamMoment account, with your own key from an AI service, or a free AI on your
  computer (Ollama, LM Studio and similar).
- Many services by your own key: OpenAI, Claude, Gemini, OpenRouter, DeepSeek, Groq, Mistral and more.
- Each step of the work already has a suitable model; changing it is one button.

### Speech to text, on your computer

- Russian with GigaAM-v3, 25 European languages with Parakeet v3, every other language with Whisper; the language of
  the stream is found by itself or chosen by hand.
- Models are downloaded once, when first needed, and can be removed in Settings.

### The program

- Its own window and icon on macOS, Windows and Linux. **A download for Windows and Mac**: an installer for Windows
  (and a ZIP without installation), one `.dmg` for every Mac, Apple silicon and Intel (SMTV starts the one made for the
  Mac's processor) — Python, ffmpeg with captions and the caption font inside, 130–270 MB; speech recognition is downloaded on the first start, only for your
  language. Not signed yet: the system warns the first time, and the guide says what to press. Or one command in a
  terminal (also Linux and Windows with Smart App Control). No administrator password either way. The window's title
  bar follows the light, dark or system theme on macOS and Windows.
- **Computer check** finds what is missing and fixes it with one button (for example, installs ffmpeg).
- **Phone**: open SMTV on a phone in the same Wi-Fi by a QR code and watch the clips there. Connections that send
  nothing are closed after 30 seconds, and at most 64 are answered at once.
- **Report a problem**: an archive with what went wrong, without keys, and a ready GitHub issue; nothing is sent by
  itself.
- Updates and new tools from inside the window; updates come from a list of releases signed by the authors.
- English and Russian; the window speaks the system's language, and more languages can be added through Weblate.
- **Docker** image for a home server or Linux without a desktop.
- `smtv uninstall` and Settings → Remove SMTV; clips stay unless you ask otherwise.
- **Step-by-step guides** for newcomers (`docs/guide/`): install, the first clip, a free AI on your computer, where
  to get a key, the account, the phone, languages, updates, what to do when something goes wrong; the README and the
  guides in 16 languages (the first translations made automatically). Settings → AI links them.

### Not yet

- A signature for the apps (so the system no longer warns): for Windows a little later, for macOS as soon as
  possible.
- LiveCut, clips while a stream is still live: after this release.
