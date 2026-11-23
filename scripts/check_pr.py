#!/usr/bin/env python3
"""Check a pull request the way the maintainers take it: `python scripts/check_pr.py <number>`.

Fetches the PR into its own folder (.check/pr-<n>/, a git worktree), installs it there with uv, runs every check with
THIS checkout's scripts/check.py (so a PR cannot weaken the checks it is judged by), and writes .check/pr-<n>.md:
the PR's head commit, the result, the changed files, changes to the allow-lists, and an empty «Review:» line. The
review-pr skill then runs the reviewer agents and the review by REVIEW.md and fills that line. The agent hook lets
`gh pr merge <n>` through only with a report for the PR's current head that passed and has a review.

This runs the PR's code (its tests) on this computer: read the diff first when the author is new.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from smtvcheck.common import load_config  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GUARDED = ["pyproject.toml", ".gitleaks.toml", ".pre-commit-config.yaml", ".github/", "scripts/", ".claude/", ".codex/",
           ".cursor/", ".agents/", "AGENTS.md", "REVIEW.md"]


def sh(cmd: list[str], cwd: Path = ROOT, timeout: float = 600) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def setting_changes(before: dict, after: dict) -> list[str]:
    """One line per [tool.smtv-check] key the PR adds, removes or changes (hosts, exceptions, limits, test command)."""
    lines = []
    for key in sorted(set(before) | set(after)):
        old, new = before.get(key), after.get(key)
        if old == new:
            continue
        if isinstance(old, list) and isinstance(new, list):
            added = [x for x in new if x not in old]
            gone = [x for x in old if x not in new]
            lines.append(f"- {key}: added {added or '—'}, removed {gone or '—'}")
        else:
            lines.append(f"- {key}: {old!r} → {new!r}")
    return lines


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or not argv[0].isdigit():
        print(__doc__)
        return 2
    n = argv[0]
    for tool in ("git", "gh", "uv"):
        if shutil.which(tool) is None:
            print(f"{tool} is needed", file=sys.stderr)
            return 2
    info = sh(["gh", "pr", "view", n, "--json", "headRefOid,baseRefName,title,author,url"])
    if info.returncode:
        print(info.stderr.strip(), file=sys.stderr)
        return 1
    pr = json.loads(info.stdout)
    head, base = pr["headRefOid"], pr["baseRefName"]
    folder = ROOT / ".check" / f"pr-{n}"
    for step in (["git", "fetch", "--quiet", "origin", f"pull/{n}/head", base],
                 ["git", "worktree", "remove", "--force", str(folder)] if folder.exists() else None,
                 ["git", "worktree", "add", "--detach", "--quiet", str(folder), head]):
        if step is None:
            continue
        res = sh(step)
        if res.returncode:
            print(f"{' '.join(step)}: {res.stderr.strip()}", file=sys.stderr)
            return 1
    sync = sh(["uv", "sync", "--frozen", "--all-packages", "--all-extras", "--quiet"], folder, timeout=1800)
    python = folder / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if sync.returncode:
        checks = subprocess.CompletedProcess([], 1, "uv sync failed:\n" + sync.stderr, "")
    else:
        checks = subprocess.run([str(python), str(ROOT / "scripts" / "check.py"), "--root", str(folder), "--ci"],
                                cwd=folder, capture_output=True, text=True, timeout=3600,
                                env={**os.environ, "SMTV_PROMPTS_DIR": str(ROOT.parent / "prompts")})
    listed = sh(["git", "diff", "-z", "--name-only", f"origin/{base}...{head}"])
    if listed.returncode:
        print("git diff failed: " + listed.stderr.strip(), file=sys.stderr)
        return 1
    files = [f for f in listed.stdout.split("\0") if f]
    guarded = [f for f in files if any(f == g or (g.endswith("/") and f.startswith(g)) for g in GUARDED)]
    base_toml = sh(["git", "show", f"origin/{base}:pyproject.toml"]).stdout
    settings = setting_changes(tomllib.loads(base_toml).get("tool", {}).get("smtv-check", {}) if base_toml else {},
                               load_config(folder))
    passed = checks.returncode == 0
    report = ROOT / ".check" / f"pr-{n}.md"
    report.write_text("\n".join([
        f"# PR {n}: {pr['title']}", "",
        f"URL: {pr['url']}",
        f"Author: {pr['author'].get('login', '?')}",
        f"Head: {head}",
        f"Base: {base}",
        f"Checked: {time.strftime('%Y-%m-%d %H:%M')}",
        f"Result: {'passed' if passed else 'failed'}",
        "Review: ",
        "", "## Files", "", *[f"- {f}" for f in files],
        "", "## Rules, checks and allow-lists this PR changes (read them line by line)", "",
        *([f"- {f}" for f in guarded] or ["- none"]),
        "", "## What the checks allow: [tool.smtv-check] before → in this PR", "",
        "The checks above ran with the PR's own settings; every change here needs a reason in the PR.", "",
        *(settings or ["- unchanged"]),
        "", "## Checks", "", "```", (checks.stdout + checks.stderr).strip(), "```", "",
    ]), encoding="utf-8")
    print(f"{'passed' if passed else 'FAILED'}: report in {report.relative_to(ROOT)}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
