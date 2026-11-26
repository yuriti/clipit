# Translations

SMTV's window speaks the language of the system; Settings → Language and theme chooses another one. Every word of the
window lives in files, one per language, and is translated on [Weblate](https://hosted.weblate.org/projects/smtv/)
(free hosting for open projects). Translators work on the site; Weblate sends their work back as pull requests, which
pass the usual checks.

## The files

| Component | Files | Source (English) |
|---|---|---|
| `window` — the window, its dialogs and notifications, «Coming» in Settings → About, the core's shared AI steps | `packages/smtv/src/smtv/web/i18n/*.json` | `packages/smtv/src/smtv/web/i18n/en.json` |
| `vodcut` — VodCut's places in the window and its AI steps | `packages/vodcut/src/vodcut/web/i18n/*.json` | `packages/vodcut/src/vodcut/web/i18n/en.json` |

Each file is a flat JSON object `{"key": "text"}`. A file is named by its language code as Weblate writes it: `ru`,
`de`, `pt-BR`, `zh-Hans`. `{name}` in a text is a value SMTV fills in; a translation keeps the same ones (a test checks).
A key a language lacks, or an empty text, is shown in English, so a language can go out half translated.

What is not here: the README and the guides for newcomers. They are written in Russian — `README.md` and
`docs/guide/*.md` are the source — and every other language, English included, is translated from them as whole files:
`README.<language>.md` and `docs/guide/<language>/`, sent as ordinary pull requests. A change to the Russian source
changes the English translation in the same pull request; the other languages follow. The Russian `README.md` lists
every language, and a test (`tests/test_docs.py`) checks that each has its README and every guide, that each says it
was translated automatically from the Russian original with a link to it and to Weblate, and that every link leads to a
file and heading that exist. A new language adds both, and its name to `LANGS` in `scripts/doc_languages.py`, which
writes the language line at the top of every page. The window's words below keep English as their source.

The AI's steps and a tool's own places are in the same files: a step's name, its one sentence, what it does, the step
of the tool it serves, how much it reads and why — keys `agent.<id>.title`, `.short`, `.does`, `.stage`, `.needs`,
`.why` (the core's shared steps — layout, ad banner, critic — in the window's files, a tool's own steps in the tool's);
a tool's kind of request and its page under Plugins — `request.title`, `request.about`, `tool.about` in the tool's files.
In the code (`Agent`, `RequestKind`, `Page.about`) there are only keys; a key no file has is shown as it is.

## For developers

- A new text goes to `en.json` first, under a new key, and to `ru.json` in the same pull request; other languages
  follow through Weblate. Never write a text into `app.js`, `section.js`, `index.html` or a Python message: the tests
  in `packages/smtv/tests/test_i18n.py` fail on Russian or a capitalised phrase in the code, on a key the code asks for
  that `en.json` lacks, and on languages whose keys differ.
- Changing an English text that is already translated: change its key too when the meaning changes, so translators see
  it as new.
- The page loads `/static/i18n/en.json` and the chosen language at start (`app.js`, `loadWords`); a tool's words come
  from `/tools/<name>/i18n/`. Python reads the same files through `smtv.i18n.text(key, lang)`.
- «Coming» (`soon.json`) holds only what each item is; its words are keys `soon.<id>.title`, `soon.<id>.summary`,
  `soon.<id>.lead`, `soon.<id>.note`, `soon.<id>.points.1`, `.2`, … in the window's files.

## Weblate setup (maintainers, once)

Project `smtv` on hosted.weblate.org, «Libre» plan, license MIT, website `https://github.com/streammomenttv/smtv`.
For each component above:

| Setting | Value |
|---|---|
| Source code repository | `https://github.com/streammomenttv/smtv.git`, branch `main` |
| Repository push URL | the same; **Version control: GitHub pull request**, push on commit |
| File format | **JSON file** |
| File mask | the «Files» column above |
| Monolingual base language file | the «Source» column above |
| Template for new translations | the same `en.json` |
| Edit base file | off (developers change English in pull requests) |
| Source language | English |
| Language code style | BCP style (`pt-BR`) |
| Translation license | MIT |

Add-ons: **Cleanup translation files** (drops keys English no longer has, so every language keeps the same keys) and
**Customize JSON output** (indent 2, keys not sorted, Unicode kept). On GitHub: install the Weblate app on
`streammomenttv/smtv`. The `.weblate` file in the repository root points the Weblate command line client (`wlc`) at
the project.
