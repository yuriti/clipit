#!/usr/bin/env python3
"""The hook AI assistants run before a shell command: Claude Code and Codex (PreToolUse on Bash), Cursor
(beforeShellExecution). One script for all three: it reads the command from stdin and blocks with exit code 2.

- `git commit`             → the quick checks (`scripts/check.py --fast`) must pass.
- `git push`, `gh pr create` → HEAD must have passed every check (`scripts/check.py` leaves a stamp in .git/smtv-check/).
- `gh pr merge <n>`        → `.check/pr-<n>.md` from `scripts/check_pr.py <n>` must be for the PR's current head, show
                             the checks passed and carry the review (the review-pr skill fills «Review:»).

Anything that keeps the hook from deciding on one of these commands blocks it; other commands always pass.
People are not stopped by this hook: GitHub's required checks are the final gate for everyone.
"""
from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
START = r"(?:^|[\s;&|(`'\"])"
# git and gh by name or by path, quoted or not; global options before the subcommand.
GIT = START + r"(?:\S*/)?[\"']?git[\"']?(?:\s+-[cC]\s+\S+|\s+--?[\w-]+(?:=\S+)?)*\s+"
GH = START + r"(?:\S*/)?[\"']?gh[\"']?(?:\s+-R\s+\S+|\s+--repo[=\s]\S+)*\s+"
COMMIT = re.compile(GIT + r"commit\b")
PUSH = re.compile(GIT + r"push\b")
PR_CREATE = re.compile(GH + r"pr\s+create\b")
PR_MERGE = re.compile(GH + r"pr\s+merge\b([^;&|`]*)")
API_MERGE = re.compile(GH + r"api\b[^;&|]*pulls/\d+/merge\b")
# `gh pr merge` options that take a value: the value is not the PR.
MERGE_VALUE_FLAGS = {"-t", "--subject", "-b", "--body", "-F", "--body-file", "--match-head-commit", "-A",
                     "--author-email", "-R", "--repo"}
GUARDED = (COMMIT, PUSH, PR_CREATE, PR_MERGE, API_MERGE)


def command_of(payload: dict) -> str | None:
    """Claude Code and Codex put it in tool_input.command, Cursor in command."""
    cmd = (payload.get("tool_input") or {}).get("command", payload.get("command"))
    return cmd if isinstance(cmd, str) else None


def git(*args: str, cwd: Path = ROOT) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=20, check=True).stdout.strip()


def decide(command: str, cwd: Path = ROOT, run_fast=None, pr_head=None) -> str | None:
    """None to let the command run, or why it is blocked. Every guarded command in the line is judged: a chain like
    `git commit && git push` needs both the quick checks and the stamp."""
    reasons = []
    if COMMIT.search(command):
        ok, output = (run_fast or fast_checks)(cwd)
        if not ok:
            reasons.append("The quick checks failed; fix them before committing:\n" + output)
    if PUSH.search(command) or PR_CREATE.search(command):
        head = git("rev-parse", "HEAD", cwd=cwd)
        stamp = Path(git("rev-parse", "--path-format=absolute", "--git-dir", cwd=cwd)) / "smtv-check" / head
        if not stamp.is_file():
            reasons.append(f"HEAD {head[:9]} has not passed every check. Run `python scripts/check.py` on a clean tree "
                           "(commit first); it leaves a stamp for this commit. Before a PR also follow the pre-pr-check skill.")
    if API_MERGE.search(command):
        reasons.append("Merge with gh pr merge <number> after python scripts/check_pr.py <number>, not through gh api.")
    for merge in PR_MERGE.finditer(command):
        number = merge_number(merge.group(1))
        if number is None:
            reasons.append("Name the pull request by number: gh pr merge <number>, after python scripts/check_pr.py <number>.")
            continue
        reason = merge_ready(cwd, number, (pr_head or current_pr_head)(cwd, number))
        if reason:
            reasons.append(reason)
    return "\n".join(reasons) or None


def merge_number(rest: str) -> str | None:
    """The PR `gh pr merge` acts on: the one positional argument, when it is a number (a URL or branch: None)."""
    try:
        args = shlex.split(rest)
    except ValueError:
        return None
    positional, skip = [], False
    for a in args:
        if skip:
            skip = False
        elif a in MERGE_VALUE_FLAGS:
            skip = True
        elif not a.startswith("-"):
            positional.append(a)
    return positional[0] if len(positional) == 1 and positional[0].isdigit() else None


def merge_ready(cwd: Path, number: str, head: str) -> str | None:
    report = cwd / ".check" / f"pr-{number}.md"
    if not report.is_file():
        return f"No report for PR {number}: run the review-pr skill (python scripts/check_pr.py {number}, then the review)."
    # Only the header the script wrote: the checks' output further down comes from the PR and could print anything.
    text = report.read_text(encoding="utf-8").split("\n## ", 1)[0]
    if not re.search(rf"^Head: {re.escape(head)}\s*$", text, re.M):
        return f"The report for PR {number} is for another commit; the PR has new commits. Check it again."
    if not re.search(r"^Result: passed\s*$", text, re.M):
        return f"The checks did not pass for PR {number} (see {report.relative_to(cwd)})."
    if not re.search(r"^Review: approve\s*$", text, re.M):
        return f"The report for PR {number} is not approved: the review-pr skill writes «Review: approve» when it is."
    return None


def current_pr_head(cwd: Path, number: str) -> str:
    out = subprocess.run(["gh", "pr", "view", number, "--json", "headRefOid", "-q", ".headRefOid"], cwd=cwd,
                         capture_output=True, text=True, timeout=30, check=True)
    return out.stdout.strip()


def fast_checks(cwd: Path) -> tuple[bool, str]:
    """The hook itself needs only the standard library; the checks run in the project's environment (uv)."""
    python = ["uv", "run", "--frozen", "--quiet", "python"] if shutil.which("uv") else [sys.executable]
    res = subprocess.run([*python, str(cwd / "scripts" / "check.py"), "--fast"], cwd=cwd, capture_output=True,
                         text=True, timeout=600)
    return res.returncode == 0, (res.stdout + res.stderr)[-4000:]


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw or "{}")
    except json.JSONDecodeError as exc:
        if any(p.search(raw) for p in GUARDED):       # cannot read it, and it looks like a guarded command: block
            print(f"agent_gate could not read the hook input ({exc}); blocked", file=sys.stderr)
            return 2
        return 0
    command = command_of(payload)
    if not command:
        return 0
    cwd = Path(payload.get("cwd") or ROOT)
    try:
        reason = decide(command, cwd if (cwd / "scripts" / "check.py").exists() else ROOT)
    except Exception as exc:                    # cannot decide on a guarded command: block, never pass silently
        if any(p.search(command) for p in GUARDED):
            print(f"agent_gate failed ({type(exc).__name__}: {exc}); the command is blocked. Fix the cause or run the "
                  "checks by hand.", file=sys.stderr)
            return 2
        return 0
    if reason:
        print(reason, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
