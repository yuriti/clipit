"""Outside sources: the code reaches only the hosts the maintainers allowed, and copied code names its source and license.

A new host is a decision, not a detail: it goes into [tool.smtv-check] `hosts` with the reason in a comment.
Tests are not scanned (they use made-up addresses on purpose); the code, scripts, the page, Docker files and CI are.
"""
from __future__ import annotations

import fnmatch
import re
from pathlib import PurePosixPath

from .common import Outcome, Repo

URL = re.compile(r"\b(?:https?|wss?)://(\[[0-9A-Fa-f:]+\]|[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?(?:\.[A-Za-z0-9-]+)*)")
CODE_SUFFIXES = {".py", ".js", ".mjs", ".ts", ".html", ".css", ".json", ".toml", ".yml", ".yaml", ".sh", ".ps1"}
CODE_NAMES = {"Dockerfile", "compose.yaml"}
DEFAULT_SKIP = ["tests/*", "*/tests/*", "*.md", "uv.lock"]
LOCAL = {"localhost", "127.0.0.1", "0.0.0.0", "[::1]", "host.docker.internal"}
COPIED = re.compile(r"\b(copied|adapted|ported|vendored|borrowed|taken)\s+from\b", re.IGNORECASE)
LICENSE_WORD = re.compile(r"\b(license|licence|SPDX|MIT|BSD|Apache|ISC)\b", re.IGNORECASE)
LINK = re.compile(r"https?://\S+")


def host_allowed(host: str, allowed: list[str]) -> bool:
    h = host.lower()
    if h in LOCAL or h.endswith((".example", ".test", ".invalid", ".localhost")) or h in ("example.com", "example.org"):
        return True
    for entry in allowed:
        e = entry.lower()
        if h == e or (e.startswith("*.") and (h.endswith(e[1:]) or h == e[2:])):
            return True
    return False


def code_files(repo: Repo) -> list[str]:
    skip = DEFAULT_SKIP + list(repo.setting("hosts-skip", []))
    found = []
    for rel in repo.files():
        p = PurePosixPath(rel)
        if (p.suffix in CODE_SUFFIXES or p.name in CODE_NAMES) and not any(fnmatch.fnmatch(rel, s) for s in skip):
            found.append(rel)
    return found


def check(repo: Repo) -> Outcome:
    out = Outcome("hosts")
    allowed = list(repo.setting("hosts", []))
    for rel in code_files(repo):
        text = repo.text(rel)
        if text is None:
            continue
        for n, line in enumerate(text.splitlines(), 1):
            for m in URL.finditer(line):
                host = m.group(1)
                if not host_allowed(host, allowed):
                    out.add(rel, n, f"{host} is not an allowed host: add it to [tool.smtv-check] hosts with the reason")
    return out


def sources(repo: Repo) -> Outcome:
    """A line saying code was copied, adapted or ported must name the source (a link) and its license nearby."""
    out = Outcome("sources")
    own = list(repo.setting("own-sources", []))     # our own repositories: no license line needed
    for rel in repo.files():
        if PurePosixPath(rel).suffix not in CODE_SUFFIXES or fnmatch.fnmatch(rel, "*tests/*"):
            continue
        text = repo.text(rel)
        if text is None:
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if COPIED.search(line) and _is_comment(line) and not any(o in line for o in own):
                near = "\n".join(lines[max(0, i - 2): i + 4])
                if not (LINK.search(near) and LICENSE_WORD.search(near)):
                    out.add(rel, i + 1, "copied code without a link to its source and its license within three lines")
    return out


def _is_comment(line: str) -> bool:
    s = line.strip()
    return s.startswith(("#", "//", "/*", "*", '"""', "'''", "<!--")) or " # " in line or " // " in line
