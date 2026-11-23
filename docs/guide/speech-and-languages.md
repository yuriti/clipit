<!-- languages -->
**English** · [Русский](ru/speech-and-languages.md) · [Қазақша](kk/speech-and-languages.md) · [Oʻzbekcha](uz/speech-and-languages.md) · [Azərbaycanca](az/speech-and-languages.md) · [Кыргызча](ky/speech-and-languages.md) · [简体中文](zh-CN/speech-and-languages.md) · [日本語](ja/speech-and-languages.md) · [한국어](ko/speech-and-languages.md) · [Tiếng Việt](vi/speech-and-languages.md) · [Bahasa Indonesia](id/speech-and-languages.md) · [हिन्दी](hi/speech-and-languages.md) · [বাংলা](bn/speech-and-languages.md) · [Español](es/speech-and-languages.md) · [Português](pt-BR/speech-and-languages.md) · [Deutsch](de/speech-and-languages.md)

# Speech and languages

First SMTV turns the stream's speech into text, with the time of every word — that is how the AI understands what
happened. This runs **on your computer, for free**. SMTV finds the language of the stream by itself.

| Language | Model | Download (once) | Speed on a 12-core processor |
|---|---|---|---|
| Russian | GigaAM-v3, made for Russian | 0.9 GB | 54× faster than real time |
| 25 European languages: English, Spanish, German, French, Italian, Portuguese, Polish, Ukrainian and others | Parakeet-TDT v3 | 2.4 GB | 33× faster than real time |
| Every other language: Chinese, Japanese, Korean, Hindi, Bengali, Kazakh, Uzbek, Azerbaijani, Vietnamese, Indonesian and dozens more | Whisper large-v3-turbo | 1.6 GB | Not measured yet |

A model downloads by itself the first time a stream in its language comes. A graphics card is not needed; an NVIDIA
card makes it faster. On a Mac, Whisper runs on the processor and is slower.

**Settings → Speech to text** shows every model: where it runs, its languages, size and speed, with **Download** and
**Remove**. There each language can take another model, also **Whisper in the cloud** by your own key (Groq or
OpenAI) — faster on a weak computer, but then the sound leaves your computer.

<img src="../images/speech.png" alt="Settings → Speech to text: the models and the languages they take" width="820">

**The window's language** is separate: SMTV speaks the language of your computer; **Settings → Language and theme**
chooses another. Is your language missing or half translated? [Help translate it](../translations.md) — no
programming needed.
