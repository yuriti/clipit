"""What every check shares: the repository's files, its settings, and what a check found."""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

# Folders that are never part of the repository, with or without git.
SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules",
             "dist", "build", ".check", ".runs"}
SKIP_FILES = {".DS_Store", ".env"}
TEXT_LIMIT = 2_000_000


@dataclass
class Finding:
    path: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.message}" if self.line else f"{self.path}: {self.message}"


@dataclass
class Outcome:
    name: str
    findings: list[Finding] = field(default_factory=list)
    skipped: str = ""           # why the check could not run here; a failure with --ci
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.findings

    def add(self, path: str, line: int, message: str) -> None:
        self.findings.append(Finding(path, line, message))


class Repo:
    """One repository root: smtv (packages/…) or prompts. Settings come from `[tool.smtv-check]` in its pyproject.toml."""

    def __init__(self, root: Path, config: dict | None = None, ci: bool = False):
        self.root = root.resolve()
        self.config = load_config(self.root) if config is None else config
        self.ci = ci
        self._files: list[str] | None = None
        self.unread: set[str] = set()      # text files too large to search: traces names them

    @property
    def git(self) -> bool:
        return (self.root / ".git").exists() and shutil.which("git") is not None

    def files(self) -> list[str]:
        """Every file of the repository, relative, with `/`: tracked and new ones git does not ignore."""
        if self._files is None:
            if self.git:
                res = run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], self.root)
                if res.returncode != 0:
                    raise RuntimeError("git ls-files failed: " + (res.stderr.strip().splitlines() or ["?"])[-1])
                out = res.stdout
                names = [p for p in out.split("\0") if p and (self.root / p).is_file() and not (self.root / p).is_symlink()]
            else:
                names = []
                for top, dirs, files in os.walk(self.root):
                    dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.endswith(".egg-info"))
                    for f in files:
                        p = Path(top) / f
                        if f not in SKIP_FILES and not p.is_symlink():
                            names.append(p.relative_to(self.root).as_posix())
            if not names:
                raise RuntimeError(f"no files found in {self.root}: nothing would be checked")
            self._files = sorted(names)
        return self._files

    def text(self, rel: str) -> str | None:
        """The file as text, or None for a binary or a huge file."""
        p = self.root / rel
        try:
            if p.stat().st_size > TEXT_LIMIT:
                with p.open("rb") as f:
                    if b"\0" not in f.read(8000):
                        self.unread.add(rel)
                return None
            data = p.read_bytes()
        except OSError:
            self.unread.add(rel)
            return None
        if b"\0" in data[:8000]:
            return None
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("latin-1")      # text in another encoding is still searched

    def setting(self, key: str, default):
        return self.config.get(key, default)


def load_config(root: Path) -> dict:
    p = root / "pyproject.toml"
    if not p.exists():
        return {}
    return tomllib.loads(p.read_text(encoding="utf-8")).get("tool", {}).get("smtv-check", {})


def run(cmd: list[str], cwd: Path, timeout: float = 900, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                          env=None if env is None else {**os.environ, **env})


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None
