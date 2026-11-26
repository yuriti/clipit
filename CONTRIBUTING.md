# Contributing to SMTV

Thank you for helping. You do not need to write code for it.

## Without code

- **Report a problem**: in SMTV, Settings → **Report a problem**, or the button under a failed request. SMTV prepares
  the report without your keys; you only press the button on GitHub. Or open a
  [problem report](https://github.com/yuriti/clipit/issues/new?template=bug.yml) by hand.
- **Suggest an idea**: [a new idea](https://github.com/yuriti/clipit/issues/new?template=feature.yml) — what you
  wanted to do and what got in the way.
- **Tell us which clips were bad and why.** A link to the recording and the clip numbers help the most: the choice of
  moments gets better from such examples.
- **Translate**: SMTV's window is translated on [Weblate](https://hosted.weblate.org/engage/smtv/), right in the
  browser, with nothing to install. The README and the guides are written in Russian; their translations are the files
  `README.<language>.md` and `docs/guide/<language>/` — send fixes as a pull request.

## With code

Everything a contributor needs — how the repository is laid out, the rules, and the one command that checks a change
(`python scripts/check.py`) — is in [AGENTS.md](AGENTS.md); it is written for people and AI assistants alike. Reviews
follow [REVIEW.md](REVIEW.md). Two rules are worth knowing up front:

- SMTV is for ordinary people, not developers: every screen and message says in plain words what it is and why.
- Commit with your GitHub noreply address (`git config user.email <id>+<login>@users.noreply.github.com`): the checks
  refuse any other.

By sending a pull request you agree that it is published under the MIT license, like the rest of SMTV.

---

**По-русски, коротко.** О проблемах и идеях — через шаблоны выше или прямо из SMTV («Настройки → Сообщить о
проблеме»). Окно переводится на Weblate; README и инструкции написаны по-русски, их переводы — целые файлы
(`README.<язык>.md`, `docs/guide/<язык>/`). Для кода прочитайте [AGENTS.md](AGENTS.md) и [REVIEW.md](REVIEW.md) и
запустите `python scripts/check.py`. Pull request'ы публикуются под лицензией MIT.
