---
name: pre-pr-check
description: Check a change before opening a pull request to SMTV — run every check, the reviewer agents that fit the diff and the review by REVIEW.md, fix what they find, and fill in the PR template. Use before every `gh pr create` and when someone asks whether a change is ready.
---

# Before a pull request

The agent hook blocks `git push` and `gh pr create` until HEAD has passed every check. Do this, in order:

1. **Scope.** `git diff --stat main...HEAD`. One PR, one change; unrelated edits go to their own PR.
2. **Checks.** Commit, then `uv run python scripts/check.py`. Fix every red line and run it again until it is green
   (it then writes the stamp for HEAD). Never loosen a check or an allow-list to make it pass without saying why in
   the PR; a new host, dependency or license exception is a decision the PR explains.
3. **Reviewer agents** (`.claude/agents`, `.codex/agents`) on the diff against `main`, each given the task and the
   diff, not your explanation:
   - `test-gap-reviewer` — always for code;
   - `silent-failure-hunter` — errors, network, jobs, subprocesses, downloads, the account, keys;
   - `duplication-reviewer` — new functions, modules, settings, commands;
   - `leak-reviewer` — always;
   - `license-reviewer` — dependencies, copied code, models, fonts, images.
   Without subagents, read each agent's file and do its review yourself, one at a time.
4. **Review by `REVIEW.md`** — the pattern, point by point, on your own diff.
5. **Fix** what is blocking, add the missing tests, commit, and run step 2 again: the stamp must be for the last commit.
6. **The PR.** Fill `.github/pull_request_template.md`: what changes for a person, how it was checked (commands, what
   you looked at, what you could not check), new dependencies, hosts or exceptions and why. Tick «checks passed»
   only if step 2 is green for the last commit.
