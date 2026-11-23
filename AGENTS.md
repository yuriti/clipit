# Working on SMTV

This file is for everyone who changes SMTV: people, Claude Code, Codex, Cursor and other AI assistants. Claude Code
reads it through `CLAUDE.md`; Codex and Cursor read it directly. Each package has its own `AGENTS.md` with how it works
inside; read the one for the package you change.

One repository, several packages, published to PyPI together under one version number (a release raises all three):

| Folder | Package | What it is | Details |
|---|---|---|---|
| `packages/smtv` | `smtv` | The `smtv` command and the window: tools, `doctor`, models and keys, the page, updates, Docker | `packages/smtv/AGENTS.md` |
| `packages/smtv-core` | `smtv-core` | Shared code: settings, models and agents, prompts, speech, rendering, checks, job events, the account | `packages/smtv-core/AGENTS.md` |
| `packages/vodcut` | `vodcut` | Tool: clips and a recap from stream recordings | `packages/vodcut/AGENTS.md` |

Prompts live in their own repository, `prompts`, checked out next to this one (`../prompts`). Also here: `install/`
(the one-line installers `install.sh` and `install.ps1`, with tests in `tests/test_install_scripts.py`; `install/app/` —
the desktop apps: `build.py` makes SMTV.app in a `.dmg` and the Windows installer and ZIP from python-build-standalone,
the wheels of `uv.lock` and a pinned ffmpeg, `smoke.py` checks a built app without a window, `smtv.iss` is the Inno
Setup script; `.github/workflows/apps.yml` builds and checks them, `release.yml` puts them on the release; tests in
`tests/test_app_build.py`), `docs/`
(`advanced.md` for advanced users, `guide/` — step-by-step guides for newcomers, one page per task, translated in
`guide/<language>/`; `images/` — the pictures of the README and the guides), `README.md` with its translations `README.<language>.md`,
and `CHANGELOG.md`.

## Rules

- **SMTV is for ordinary people.** The people who use it are streamers and clippers, not developers: they do not know
  what a model, an LLM, an agent, a provider or an API key is. Every screen, message, check and README line says in
  plain words what this is and why; a term goes only on a second line or under «More». A change that adds a screen or
  a message is reviewed for this too.
- **Pictures** of the README and the guides live in `docs/images/`, in the repository: GitHub and the Codeberg mirror
  show them from there, and they change with the page in the same PR (release assets would tie them to a version and
  break the README until a release exists). A picture is at most 5 MB (a GIF: about 15 s, 800–1000 px wide, ~10 fps),
  a screenshot under 500 KB, all of `docs/images/` under 25 MB (`tests/test_docs.py`); a new GIF replaces the old one
  instead of adding to it. Only a made-up stream or one free to use is in a picture: no real person's face, no home
  path, network address, key or account.
- `README.md` is written in English for such a person; a change to it changes `README.ru.md` in the same PR (the other
  translations follow through the translators). Details for developers and advanced users go to `docs/advanced.md`.
- A tool imports shared code only from `smtv_core`, never from another tool.
- A tool plugs in through the entry point group `smtv.tools` (see `smtv_core/tool.py`); `smtv` must keep working when a tool fails to load.
- A new tool gets a line in `CATALOG` (`packages/smtv/src/smtv/tools.py`) and an extra in `packages/smtv/pyproject.toml` (skill `new-tool`).
- Settings are changed through `smtv` commands or the page, never by asking people to edit files. Keys go through `smtv_core.settings.set_secret` and are never printed or logged.
- Every check that can fail says how to fix it in one concrete step.
- Prompts come from the `prompts` repository at a pinned version: change and test them there, then copy the release in with `python scripts/sync_prompts.py ../prompts` (skill `new-agent`). Never edit `smtv_core/prompts/` by hand; a check fails when the bundled copy differs from `../prompts`.
- No personal data in code, commits or fixtures: no personal names, e-mails, home paths, machine or LAN addresses, account ids, private hosts. Commits are authored with a GitHub noreply address.
- The code talks only to the hosts listed in `[tool.smtv-check] hosts` (`pyproject.toml`); a new host is added there with its reason, in the same PR.
- Dependencies have permissive licenses (MIT, BSD, Apache, ISC, PSF); copyleft is a stop. Copied code carries a comment with its source link and license. A new dependency says in the PR why the existing ones did not fit.
- How changes are reviewed — reuse what exists, one task one way, retired code deleted, failures seen: `REVIEW.md`. It applies to your own changes too.

## Checks: one command, three places

`python scripts/check.py` checks everything; `--list` shows what, `--fast` runs the quick part. The same command runs:

1. **On your computer**: pre-commit runs `--fast` before every commit (`uv run pre-commit install` once); run the
   whole command before a pull request. AI assistants: the `pre-pr-check` skill before every PR; the agent hook
   (below) blocks `git commit` while the quick checks fail and `git push` / `gh pr create` until HEAD passed all of
   them.
2. **On GitHub, on every PR** (`.github/workflows/`): `checks` runs everything without secrets; `private-words`
   searches only the PR's text for the maintainers' private word list, never running its code; CodeQL, dependency
   review, Scorecard; Dependabot keeps dependencies and actions current. A PR merges only with green checks.
3. **When maintainers take a PR**: the `review-pr` skill (`python scripts/check_pr.py <number>`, the reviewer agents,
   the review by `REVIEW.md`); `gh pr merge` goes through the hook only with its approved report.

What the checks cover: personal traces and the private word list (`traces`; the list itself stays outside the
repository, format in `scripts/smtvcheck/private-words.example.txt`), keys and tokens (`secrets`, gitleaks), allowed
hosts (`hosts`), copied code (`sources`), licenses and font licenses (`licenses`), `uv.lock` hashes and no
install-time code (`supply`), known vulnerabilities (`audit`), GitHub workflows (`workflows`, zizmor), lint (`ruff`), types (`types`, mypy: the error count
in `pyproject.toml` may only go down), dead code, repeated blocks, prompts and agents in sync, the window's JavaScript (`web`: `node --test`, no npm packages), tests. A check that
cannot run here (a missing tool) is skipped with the reason; with `--ci` a skip fails.

Never loosen a check, an allow-list or a recorded limit to make a change pass without saying so in the PR.

## For AI assistants

- **Skills** (`SKILL.md`): one source in `.agents/skills/` (Codex and Cursor read it), linked for Claude Code from
  `.claude/skills/` (symlinks; the `sync` check keeps them in step):
  `new-tool`, `new-agent`, `pre-pr-check`, `review-pr`, `release-prep`.
- **Reviewer agents**: written once in `.claude/agents/` (Claude Code and Cursor read them), built for Codex into
  `.codex/agents/` by `python scripts/sync_agents.py`: `test-gap-reviewer`, `silent-failure-hunter`,
  `duplication-reviewer`, `leak-reviewer`, `license-reviewer`. `REVIEW.md` says which to run on which diff.
- **Hook** `scripts/hooks/agent_gate.py`, one script for all three: `.claude/settings.json`, `.codex/hooks.json`
  (Codex asks you to trust it once), `.cursor/hooks.json`.
- Read the package's own `AGENTS.md` before changing it. Run the tests you touch; run `python scripts/check.py`
  before saying a change is done.

## Code Review Rules

Review pull requests by `REVIEW.md` («The pattern»), blocking findings first.

## Run and test

```bash
uv sync --all-packages
uv run pytest -q
uv run python scripts/check.py
```

Without uv: `python3 -m venv .venv && .venv/bin/pip install -e packages/smtv-core -e packages/vodcut -e "packages/smtv[vodcut]"`
plus the dev tools listed in `[dependency-groups]` of `pyproject.toml`.

To try an install the way users get it, without touching your own tools: set `UV_TOOL_DIR`, `UV_TOOL_BIN_DIR` and `SMTV_HOME` to a temporary folder and run `uv tool install "./packages/smtv[vodcut]" --with ./packages/smtv-core --with ./packages/vodcut`.
