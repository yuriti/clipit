# Contributing to SMTV

Thank you for helping. You do not need to write code for it.

## Without code

- **Report a problem**: in SMTV, Settings → **Report a problem**, or the button under a failed request. SMTV prepares
  the report without your keys; you only press the button on GitHub. Or open a
  [problem report](https://github.com/streammomenttv/smtv/issues/new?template=bug.yml) by hand.
- **Suggest an idea**: [a new idea](https://github.com/streammomenttv/smtv/issues/new?template=feature.yml) — what you
  wanted to do and what got in the way.
- **Tell us which clips were bad and why.** A link to the recording and the clip numbers help the most: the choice of
  moments gets better from such examples.
- **Translate**: SMTV's window and README are being prepared for translation; once the project is on Weblate, you can
  translate right in the browser, with nothing to install.

## With code

Everything a contributor needs — how the repository is laid out, the rules, and the one command that checks a change
(`python scripts/check.py`) — is in [AGENTS.md](AGENTS.md); it is written for people and AI assistants alike. Reviews
follow [REVIEW.md](REVIEW.md). Two rules are worth knowing up front:

- SMTV is for ordinary people, not developers: every screen and message says in plain words what it is and why.
- Commit with your GitHub noreply address (`git config user.email <id>+<login>@users.noreply.github.com`): the checks
  refuse any other.

By sending a pull request you agree that it is published under the MIT license, like the rest of SMTV.
