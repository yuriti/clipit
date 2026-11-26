#!/usr/bin/env python3
"""Check everything: the one command for people, AI assistants, pre-commit, the agent hooks and GitHub Actions.

    python scripts/check.py                 every check (what CI runs on a pull request)
    python scripts/check.py --fast          the quick ones, for pre-commit and before `git commit`
    python scripts/check.py hosts traces    only these
    python scripts/check.py --root ../prompts
    python scripts/check.py licenses --write   rebuild THIRD_PARTY_LICENSES.md (for a release)
    python scripts/check.py --list

A check that cannot run here (a tool is missing) is skipped with the reason; with --ci a skip is a failure.
When everything passed on a clean git tree, the command leaves a stamp for HEAD in .git/smtv-check/: the agent
hooks let `git push` and `gh pr create` through only with it.
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from smtvcheck import hosts, licenses, quality, supply, sync, traces  # noqa: E402
from smtvcheck.common import Outcome, Repo, run  # noqa: E402

# name: (function, fast, what it guards)
CHECKS = {
    "traces": (traces.check, True, "personal paths, e-mails, private words, commit authors"),
    "secrets": (traces.secrets, True, "keys and tokens (gitleaks)"),
    "hosts": (hosts.check, True, "the code reaches only allowed hosts"),
    "sources": (hosts.sources, True, "copied code names its source and license"),
    "sync": (sync.check, True, "prompts, agents and skills match their source"),
    "ruff": (quality.ruff, True, "lint"),
    "supply": (supply.check, True, "lock file with hashes, no install-time code"),
    "licenses": (licenses.check, False, "dependency and font licenses"),
    "types": (quality.types, False, "mypy, not worse than recorded"),
    "dead-code": (quality.dead, False, "unused code (vulture)"),
    "duplicates": (quality.duplicates, False, "repeated blocks"),
    "audit": (supply.audit, False, "known vulnerabilities (pip-audit)"),
    "workflows": (supply.workflows, False, "GitHub workflows (zizmor)"),
    "web": (quality.web, True, "the window's JavaScript (node --test)"),
    "tests": (sync.tests, False, "the test suite"),
}
ROOT = Path(__file__).resolve().parent.parent


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Check everything before a commit or a pull request.")
    ap.add_argument("names", nargs="*", help="only these checks")
    ap.add_argument("--root", type=Path, default=ROOT, help="the repository to check (default: this one)")
    ap.add_argument("--fast", action="store_true", help="only the quick checks")
    ap.add_argument("--ci", action="store_true", help="a skipped check is a failure")
    ap.add_argument("--skip", action="append", default=[], help="leave this check out (CI runs some separately)")
    ap.add_argument("--write", action="store_true", help="with licenses: rebuild THIRD_PARTY_LICENSES.md")
    ap.add_argument("--list", action="store_true", help="list the checks")
    ap.add_argument("--diff", type=Path, help="only personal traces in the lines this patch adds (CI, private list)")
    ap.add_argument("--authors", type=Path, help="with --diff: commit authors, one «sha NUL name NUL email NUL …» per line")
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):        # a Windows console is cp1252: «», … and → came out as «�»
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    if args.list:
        for name, (_, fast, what) in CHECKS.items():
            print(f"{name:11} {'fast' if fast else '    '}  {what}")
        return 0
    unknown = [n for n in args.names + args.skip if n not in CHECKS]
    if unknown:
        print("unknown check: " + ", ".join(unknown) + " (see --list)", file=sys.stderr)
        return 2
    repo = Repo(args.root, ci=args.ci)
    if args.diff:
        log = args.authors.read_text(encoding="utf-8") if args.authors else None
        outcome = traces.diff(repo, args.diff.read_text(encoding="utf-8", errors="replace"), log)
        report(outcome, 0, args.ci)
        return 0 if outcome.ok else 1
    if args.write:
        target = repo.root / licenses.NOTICES
        target.write_text(licenses.notices(repo), encoding="utf-8")
        print(f"wrote {target.name}")
        return 0
    names = args.names or [n for n, (_, fast, _) in CHECKS.items() if fast or not args.fast]
    names = [n for n in names if n not in args.skip]
    results: list[Outcome] = []
    for name in names:
        started = time.monotonic()
        try:
            outcome = CHECKS[name][0](repo)
        except Exception as exc:          # a broken check fails loudly, it never passes
            outcome = Outcome(name)
            outcome.add("-", 0, f"the check itself failed: {type(exc).__name__}: {exc}")
        results.append(outcome)
        report(outcome, time.monotonic() - started, args.ci)
    failed = [o.name for o in results if not o.ok or (args.ci and o.skipped)]
    skipped = [o.name for o in results if o.skipped]
    print()
    if failed:
        print("FAILED: " + ", ".join(failed))
        return 1
    print("all checks passed" + (f" (skipped here: {', '.join(skipped)})" if skipped else ""))
    if not args.names and not args.fast and not args.skip and not skipped:
        stamp(repo)
    return 0


def report(o: Outcome, seconds: float, ci: bool) -> None:
    state = "ok" if o.ok and not o.skipped else ("skip" if o.ok and not ci else "FAIL")
    print(f"[{state:4}] {o.name} ({seconds:.1f} s)" + (f": {o.skipped}" if o.skipped else ""))
    for f in o.findings[:200]:
        print(f"       {f}")
    if len(o.findings) > 200:
        print(f"       … and {len(o.findings) - 200} more")
    for note in o.notes:
        print(f"       note: {note}")


def stamp(repo: Repo) -> None:
    """Remember that HEAD passed every check on a clean tree (what the agent hooks ask for before a push or a PR)."""
    if not repo.git:
        return
    head = run(["git", "rev-parse", "HEAD"], repo.root)
    dirty = run(["git", "status", "--porcelain", "--untracked-files=no"], repo.root)
    git_dir = run(["git", "rev-parse", "--git-dir"], repo.root)
    if head.returncode or dirty.returncode or git_dir.returncode or dirty.stdout.strip():
        print("(no stamp: uncommitted changes; commit and run again before a push)")
        return
    folder = (repo.root / git_dir.stdout.strip() / "smtv-check")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / head.stdout.strip()).write_text(time.strftime("%Y-%m-%dT%H:%M:%S") + " all checks passed\n")
    print(f"stamp for {head.stdout.strip()[:9]} written")


if __name__ == "__main__":
    sys.exit(main())
