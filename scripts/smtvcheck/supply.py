"""Supply chain: a lock file with hashes, nothing that runs code at install time, known vulnerabilities."""
from __future__ import annotations

import shutil
import sys
import tempfile
import tomllib
from pathlib import Path, PurePosixPath

from .common import Outcome, Repo, module_available, run

BACKENDS = {"hatchling.build"}
INSTALL_SCRIPTS = {"setup.py", "setup.cfg"}


def check(repo: Repo) -> Outcome:
    out = Outcome("supply")
    lock = repo.root / "uv.lock"
    if not lock.exists():
        out.add("uv.lock", 0, "no lock file: run `uv lock` and commit uv.lock")
    else:
        lock_hashes(tomllib.loads(lock.read_text(encoding="utf-8")), out)
    for rel in repo.files():
        p = PurePosixPath(rel)
        if p.name in INSTALL_SCRIPTS:
            out.add(rel, 0, "install-time script: packages are built by hatchling from pyproject.toml only")
        if p.name == "pyproject.toml":
            build(rel, tomllib.loads((repo.root / rel).read_text(encoding="utf-8")), out)
    return out


def lock_hashes(lock: dict, out: Outcome) -> None:
    for pkg in lock.get("package", []):
        source = pkg.get("source", {})
        if any(k in source for k in ("editable", "virtual", "directory", "path")):
            continue                       # our own workspace packages (and the prompts' local smtv-core)
        if "registry" not in source:
            out.add("uv.lock", 0, f"{pkg.get('name')}: comes from {', '.join(source) or '?'}, not from PyPI: no hash pins it")
            continue
        files = ([pkg["sdist"]] if "sdist" in pkg else []) + pkg.get("wheels", [])
        if not files or any(not str(f.get("hash", "")).startswith("sha256:") for f in files):
            out.add("uv.lock", 0, f"{pkg.get('name')}: a file without a sha256 hash")


def build(rel: str, data: dict, out: Outcome) -> None:
    backend = data.get("build-system", {}).get("build-backend")
    if "project" in data and backend not in BACKENDS:
        out.add(rel, 0, f"build backend {backend!r}: only {', '.join(sorted(BACKENDS))}")
    hatch_all = data.get("tool", {}).get("hatch", {})
    hatch = hatch_all.get("build", {})
    targets = hatch.get("targets", {})
    if ("hooks" in hatch or "hooks" in hatch_all.get("metadata", {})
            or any("hooks" in t for t in targets.values() if isinstance(t, dict))):
        out.add(rel, 0, "build hooks run code at install time: not allowed")


def audit(repo: Repo) -> Outcome:
    """Known vulnerabilities in every package uv.lock pins for users (all platforms and extras, without the dev tools):
    `uv export` writes them out, pip-audit asks the PyPI advisory database (needs the internet)."""
    out = Outcome("audit")
    uv = shutil.which("uv") or shutil.which("uv", path=str(Path(sys.executable).parent))
    if not module_available("pip_audit"):
        out.skipped = "pip-audit is not installed (dev group)"
        return out
    if uv is None or not (repo.root / "uv.lock").exists():
        out.skipped = "needs uv and uv.lock"
        return out
    with tempfile.TemporaryDirectory() as tmp:
        req = Path(tmp) / "requirements.txt"
        res = run([uv, "export", "--frozen", "--no-dev", "--all-extras", "--all-packages", "--no-emit-workspace",
                   "--format", "requirements-txt", "-o", str(req)], repo.root, timeout=300)
        if res.returncode != 0:
            out.add("uv.lock", 0, "uv export failed: " + (res.stderr.strip().splitlines() or ["?"])[-1])
            return out
        # Packages from a local checkout (the prompts repository's smtv-core) are ours, not from PyPI: nothing to look up.
        req.write_text("".join(line for line in req.read_text(encoding="utf-8").splitlines(keepends=True)
                               if not line.startswith(("-e ", "--editable"))), encoding="utf-8")
        ignore = []
        for vuln_id in repo.setting("audit-ignore", []):
            ignore += ["--ignore-vuln", vuln_id]
        res = run([sys.executable, "-m", "pip_audit", "-r", str(req), "--no-deps", "--disable-pip",
                   "--strict", "--progress-spinner", "off", *ignore], repo.root)
    if res.returncode == 0:
        return out
    rows = [r for r in res.stdout.splitlines() if r and not r.startswith(("Name", "----"))]
    if rows:
        for row in rows:
            out.add("dependencies", 0, "vulnerable: " + " ".join(row.split()))
    else:
        out.skipped = "pip-audit could not run: " + ((res.stdout + res.stderr).strip().splitlines() or ["?"])[-1][:200]
    return out


def workflows(repo: Repo) -> Outcome:
    """The GitHub workflows: each parses as YAML, then zizmor (offline): template injection, credentials left in checkouts, risky triggers."""
    out = Outcome("workflows")
    folder = repo.root / ".github" / "workflows"
    if not folder.is_dir():
        out.skipped = "no .github/workflows"
        return out
    # zizmor silently passes over a file it cannot read, and GitHub then rejects it on push: parse each one first.
    try:
        import yaml
    except ImportError:
        out.skipped = "PyYAML is not installed (dev group)"
        return out
    for path in sorted(folder.glob("*.y*ml")):
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None)
            line = mark.line + 1 if mark else 0
            out.add(str(path.relative_to(repo.root)), line, f"not valid YAML, GitHub will reject it: {getattr(e, 'problem', None) or e}"
                    " (quote a value that holds «: » or « #»)")
    exe = shutil.which("zizmor") or shutil.which("zizmor", path=str(Path(sys.executable).parent))
    if exe is None:
        if not out.findings:
            out.skipped = "zizmor is not installed (dev group)"
        return out
    res = run([exe, "--offline", "--format", "plain", "--min-severity", "medium", str(folder)], repo.root, timeout=300)
    if res.returncode not in (0,):
        for line in res.stdout.splitlines():
            if line.startswith(("error[", "warning[")) or line.lstrip().startswith("-->"):
                out.add(".github/workflows", 0, line.strip())
        if not out.findings:
            out.add(".github/workflows", 0, "zizmor failed: " + ((res.stderr.strip().splitlines() or ["?"])[-1]))
    return out
