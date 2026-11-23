#!/usr/bin/env python3
"""Reviewer agents are written once, in .claude/agents/*.md (Claude Code and Cursor read them). Codex wants TOML in
.codex/agents/; this script builds those files. `python scripts/check.py sync` fails while they differ.

    python scripts/sync_agents.py           rebuild .codex/agents
    python scripts/sync_agents.py --check   only say whether they are current
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path(".claude/agents")
TARGET = Path(".codex/agents")
HEADER = "# Built by scripts/sync_agents.py from .claude/agents/{name}.md; edit that file, not this one.\n"


def parse(text: str) -> tuple[dict, str]:
    """Frontmatter fields and the body of an agent file."""
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ValueError("no frontmatter")
    head, body = text[4:].split("\n---\n", 1)
    meta = {}
    for line in head.splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
        elif line.strip():
            raise ValueError(f"only one-line fields in the frontmatter: {line.strip()[:40]}")
    if any(v in (">", "|", ">-", "|-") for v in meta.values()):
        raise ValueError("only one-line fields in the frontmatter")
    if not meta.get("name") or not meta.get("description"):
        raise ValueError("needs name and description")
    return meta, body.strip() + "\n"


def toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render(meta: dict, body: str) -> str:
    if "'''" in body:
        raise ValueError("the body may not contain '''")
    # Codex has no per-agent tool list: «read-only» is carried by the instructions themselves (each says so).
    return (HEADER.format(name=meta["name"]) + f"name = {toml_string(meta['name'])}\n"
            f"description = {toml_string(meta['description'])}\n"
            f"developer_instructions = '''\n{body}'''\n")


def wanted(root: Path) -> dict[Path, str]:
    return {TARGET / f"{p.stem}.toml": render(*parse(p.read_text(encoding="utf-8")))
            for p in sorted((root / SOURCE).glob("*.md"))}


def stale(root: Path) -> list[str]:
    """Files under .codex/agents that are missing, different or left over."""
    want = wanted(root)
    found = []
    for rel, text in want.items():
        p = root / rel
        if not p.exists() or p.read_text(encoding="utf-8") != text:
            found.append(rel.as_posix())
    target = root / TARGET
    if target.is_dir():
        found += [(TARGET / p.name).as_posix() for p in sorted(target.glob("*.toml")) if TARGET / p.name not in want]
    return found


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--check" in argv:
        bad = stale(root)
        for rel in bad:
            print(f"out of date: {rel}")
        return 1 if bad else 0
    want = wanted(root)
    (root / TARGET).mkdir(parents=True, exist_ok=True)
    for p in (root / TARGET).glob("*.toml"):
        if TARGET / p.name not in want:
            p.unlink()
    for rel, text in want.items():
        (root / rel).write_text(text, encoding="utf-8")
    print(f"{len(want)} agents written to {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
