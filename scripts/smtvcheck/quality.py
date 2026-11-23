"""Code quality: ruff, types (mypy, not worse than the recorded count), dead code (vulture), copied blocks."""
from __future__ import annotations

import hashlib
import re
import shutil
import sys
from pathlib import PurePosixPath

from .common import Outcome, Repo, module_available, run


def source_dirs(repo: Repo) -> list[str]:
    return [d for d in repo.setting("source-dirs", ["packages/smtv-core/src", "packages/smtv/src", "packages/vodcut/src"])
            if (repo.root / d).exists()]


def ruff(repo: Repo) -> Outcome:
    out = Outcome("ruff")
    if not module_available("ruff"):
        out.skipped = "ruff is not installed (dev group)"
        return out
    # the folders that are never part of the repository (build/ holds a whole Python when the apps are built) stay out
    # even without git, whose ignore list ruff would otherwise follow
    from .common import SKIP_DIRS
    res = run([sys.executable, "-m", "ruff", "check", "--output-format", "concise", "--quiet",
               "--extend-exclude", ",".join(sorted(SKIP_DIRS)), "."], repo.root)
    for line in res.stdout.splitlines():
        m = re.match(r"(.+?):(\d+):\d+: (.+)", line)
        if m:
            out.add(m.group(1), int(m.group(2)), m.group(3))
    if res.returncode != 0 and not out.findings:
        out.add("-", 0, "ruff failed: " + (res.stderr.strip().splitlines() or ["?"])[-1])
    return out


def types(repo: Repo) -> Outcome:
    """mypy over the sources. The code was written without it, so the check is a ratchet: the number of errors may only
    go down ([tool.smtv-check] mypy-errors). Lower it in the same change that fixes some."""
    out = Outcome("types")
    dirs = source_dirs(repo)
    if not dirs:
        out.skipped = "no source folders"
        return out
    if not module_available("mypy"):
        out.skipped = "mypy is not installed (dev group)"
        return out
    res = run([sys.executable, "-m", "mypy", *dirs], repo.root)
    errors = [line for line in res.stdout.splitlines() if ": error:" in line]
    limit = int(repo.setting("mypy-errors", 0))
    if len(errors) > limit:
        out.add("-", 0, f"mypy: {len(errors)} errors, the recorded limit is {limit}; the first 40 below; fix new ones")
        for line in errors[:40]:
            m = re.match(r"(.+?):(\d+): error: (.+)", line)
            if m:
                out.add(m.group(1), int(m.group(2)), m.group(3))
    elif len(errors) < limit:
        out.notes.append(f"mypy: {len(errors)} errors, fewer than the limit {limit}: lower mypy-errors to {len(errors)}")
    if res.returncode not in (0, 1):
        out.add("-", 0, "mypy crashed: " + (res.stderr.strip().splitlines() or ["?"])[-1])
    return out


def dead(repo: Repo) -> Outcome:
    out = Outcome("dead-code")
    dirs = source_dirs(repo)
    if not dirs:
        out.skipped = "no source folders"
        return out
    if not module_available("vulture"):
        out.skipped = "vulture is not installed (dev group)"
        return out
    res = run([sys.executable, "-m", "vulture", *dirs, "--min-confidence", "100"], repo.root)
    for line in res.stdout.splitlines():
        m = re.match(r"(.+?):(\d+): (.+)", line)
        if m:
            out.add(m.group(1), int(m.group(2)), m.group(3))
    if res.returncode not in (0, 3) and not out.findings:      # 3: dead code found; anything else: vulture failed
        out.add("-", 0, "vulture failed: " + ((res.stderr.strip().splitlines() or ["?"])[-1]))
    return out


def duplicates(repo: Repo, window: int | None = None) -> Outcome:
    """The same block of code (comments and blank lines aside) in two places: one of them should call the other."""
    out = Outcome("duplicates")
    if not source_dirs(repo):
        out.skipped = "no source folders"
        return out
    window = window or int(repo.setting("duplicate-lines", 12))
    seen: dict[str, tuple[str, int]] = {}
    reported: set[tuple[str, str]] = set()
    for rel in repo.files():
        if PurePosixPath(rel).suffix not in (".py", ".js") or not any(rel.startswith(d + "/") for d in source_dirs(repo)):
            continue
        text = repo.text(rel)
        if text is None:
            continue
        lines = [(n, _norm(raw)) for n, raw in enumerate(text.splitlines(), 1)]
        lines = [(n, s) for n, s in lines if s and len(s) > 3]
        for i in range(len(lines) - window + 1):
            chunk = "\n".join(s for _, s in lines[i:i + window])
            key = hashlib.sha1(chunk.encode()).hexdigest()
            here = (rel, lines[i][0])
            first = seen.setdefault(key, here)
            if first != here and (first[0] != rel or here[1] - first[1] >= window):
                pair = (f"{first[0]}:{first[1] // 50}", f"{rel}:{here[1] // 50}")
                if pair not in reported:
                    reported.add(pair)
                    out.add(rel, here[1], f"{window}+ lines repeat {first[0]}:{first[1]}")
    return out


def _norm(line: str) -> str:
    s = line.strip()
    if s.startswith(("#", "//")) or s in ('"""', "'''", ")", "]", "}", "):", "},", "],", "else:", "try:"):
        return ""
    return re.sub(r"\s+", " ", s)


def web(repo: Repo) -> Outcome:
    """The window's JavaScript tests: Node's own runner (node --test) over packages/*/tests/web/*.test.mjs, on a small fake
    DOM kept beside them. No npm packages: Node alone is enough."""
    out = Outcome("web")
    files = sorted(str(p.relative_to(repo.root)) for p in repo.root.glob("packages/*/tests/web/*.test.mjs"))
    if not files:
        if any(repo.root.glob("packages/*/src/*/web/*.js")):
            out.skipped = "no tests"                       # a window without its tests: --ci fails on it
        else:
            out.notes.append("no window JavaScript here")  # e.g. the prompts repository: nothing to test
        return out
    node = shutil.which("node")
    if not node:
        out.skipped = "Node.js is not installed"
        return out
    res = run([node, "--test", "--test-reporter=tap", *files], repo.root, timeout=600)
    for line in res.stdout.splitlines():
        m = re.match(r"\s*not ok \d+ - (.+)", line)
        if m:
            out.add("packages/*/tests/web", 0, m.group(1))
    if res.returncode != 0 and not out.findings:
        out.add("-", 0, "node --test failed: " + ((res.stdout + res.stderr).strip().splitlines() or ["?"])[-1])
    elif res.returncode == 0:
        out.notes.append(next((x.strip("# ") for x in res.stdout.splitlines() if x.startswith("# pass")), "passed"))
    return out
