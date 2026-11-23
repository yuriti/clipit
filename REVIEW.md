# How SMTV changes are reviewed

One page, read by people and by every AI reviewer: Claude Code review reads this file itself, `AGENTS.md` points
Codex and Cursor here, `.github/copilot-instructions.md` points Copilot here, and the `pre-pr-check` and `review-pr`
skills follow it. Change the rules here and nowhere else.

## The pattern

1. **Reuse what exists.** Before writing a helper, a request, a parser, a retry loop or a setting, look for the one
   SMTV already has — shared code lives in `smtv_core`. A tool never copies what the core offers.
2. **One task, one way.** If the change adds a second way of doing something SMTV already does, it is a mistake: the
   first way is changed or replaced, not given a neighbour. «The new one is better» means the old one goes in the
   same change, with its callers moved.
3. **Retired code is deleted, not switched off.** No flag, setting or `if False` keeps dead code around «just in case».
4. **Failures are seen.** A failure reaches the job's journal and the page in plain words; nothing is swallowed,
   nothing waits for a human who will never look. Every outside call has a timeout; retries stop and never repeat
   something irreversible.
5. **Tests prove the behaviour.** New behaviour has a test that fails without it; a bug fix has a test that failed
   before the fix. Tests use made-up data, never real people, streams or keys.
6. **Nothing personal, nothing secret.** No names, home paths, e-mail addresses, machine or LAN addresses, private
   hosts, keys or tokens — in code, tests, commits or screenshots.
7. **Every new outside thing has a reason.** A new dependency (and why the existing ones did not fit), a new host the
   code talks to, a new license exception: the PR says why; the allow-lists in `pyproject.toml` change in the same PR.
8. **Contracts stay compatible.** Job events, the page's API, settings files and the tool entry point follow their
   rules in `AGENTS.md`: new fields are optional, a rename is a new major version.

## What a reviewer does

1. Read the PR's description and its diff; rebuild what it should do.
2. Run `python scripts/check.py` (maintainers: `python scripts/check_pr.py <number>`). Red is a stop.
3. Read every change to the rules, checks and allow-lists (`pyproject.toml` `[tool.smtv-check]`, `scripts/`,
   `.github/`, `.claude/`, `.codex/`, `.cursor/`, `.agents/`, `AGENTS.md`, this file) line by line: a PR must not
   loosen the checks it is judged by without saying so.
4. Run the reviewer agents that fit the diff (all of them for a large change):
   - `test-gap-reviewer` — always for code changes;
   - `silent-failure-hunter` — errors, network, jobs, subprocesses, downloads, the account, keys;
   - `duplication-reviewer` — any new function, module, setting or command;
   - `leak-reviewer` — always before it becomes public;
   - `license-reviewer` — dependencies, copied code, models, fonts, images.
5. Check the change against the pattern above.
6. Write the verdict: what must change (blocking), what could be better (not blocking), what was not checked.

A finding is blocking when it breaks the pattern, loses a failure, leaks, or lacks a test for changed behaviour.
Style that the checks do not enforce is never blocking.
