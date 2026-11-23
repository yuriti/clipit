---
name: review-pr
description: Maintainers taking a pull request into SMTV — «check PR <number>» — fetch it into its own folder, run every check with our own scripts, the reviewer agents and the review by REVIEW.md, and write the report that allows the merge. Use when a maintainer asks to check, review or merge a PR.
---

# Check PR <number>

Needs `git`, `gh` (signed in) and `uv`. The merge goes through only with a report for the PR's current head that
passed and carries a review: the agent hook checks it before `gh pr merge`; GitHub's required checks guard it too.

1. **Look before running.** `gh pr view <n>` and `gh pr diff <n>`. A first-time author: read the whole diff before
   step 2 — step 2 runs the PR's tests on this computer. Anything that touches CI, hooks, `scripts/` or install steps
   from an unknown author: stop and ask the maintainer.
2. **Checks.** `python scripts/check_pr.py <n>`: the PR in `.check/pr-<n>/`, installed from its `uv.lock`, checked by
   *this* checkout's `scripts/check.py`. Report: `.check/pr-<n>.md`.
3. **Read the guarded files** the report lists (rules, checks, allow-lists) line by line, and its section «What the
   checks allow»: the checks ran with the PR's own `[tool.smtv-check]`. A loosened check without a reason is blocking.
4. **Reviewer agents**, from `.check/pr-<n>/` on `git diff origin/<base>...HEAD`: the ones `REVIEW.md` names for this
   diff; for a large PR, all five. Give each the PR's description and the diff.
5. **Review by `REVIEW.md`.**
6. **Write the verdict** into the report: replace the line `Review: ` with `Review: approve` or `Review: changes
   needed`, and add a section «## Review» with blocking findings, other findings, and what was not checked. Keep the
   `Head:` line as the script wrote it.
7. **Changes needed:** post the findings on the PR (`gh pr review <n> --request-changes --body-file …`) only after
   the maintainer has read them. **Approve:** the maintainer merges (`gh pr merge <n> --squash`); new commits on the
   PR mean a new run from step 2.
8. Clean up: `git worktree remove .check/pr-<n>`.
