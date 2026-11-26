"""Things kept in two forms must match: the bundled prompts and ../prompts (without it, the bundled copy must be whole),
reviewer agents for Claude Code and Codex,
skills for Claude Code (symlinks) and for Codex and Cursor (the real folder)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from .common import Outcome, Repo, run

SKILLS = ".agents/skills"          # the one source: Codex and Cursor read it
CLAUDE_SKILLS = ".claude/skills"   # Claude Code reads only this: one symlink per skill
CLAUDE_AGENTS = ".claude/agents"   # the one source of reviewer agents; Cursor reads it too
CODEX_AGENTS = ".codex/agents"     # built from it by scripts/sync_agents.py


def check(repo: Repo) -> Outcome:
    out = Outcome("sync")
    root = repo.root
    script = root / "scripts" / "sync_prompts.py"
    prompts = Path(os.environ.get("SMTV_PROMPTS_DIR") or root.parent / "prompts")
    if script.exists():
        if prompts.is_dir():
            res = run([sys.executable, str(script), str(prompts), "--check"], root, timeout=120)
            if res.returncode != 0:
                out.add("packages/smtv-core/src/smtv_core/prompts", 0,
                        "differs from ../prompts: run python scripts/sync_prompts.py ../prompts")
        else:   # CI and contributors have no ../prompts: the published copy is checked on its own
            res = run([sys.executable, str(script), "--intact"], root, timeout=120)
            if res.returncode != 0:
                out.add("packages/smtv-core/src/smtv_core/prompts", 0,
                        "the bundled prompts are broken: " + " ".join(res.stdout.split())[:300])
            else:
                out.notes.append("../prompts is not next to this repository: the bundled copy checked on its own")
    skills = root / SKILLS
    if skills.is_dir():
        for folder in sorted(p for p in skills.iterdir() if p.is_dir()):
            skill_file = folder / "SKILL.md"
            if not skill_file.exists():
                out.add(f"{SKILLS}/{folder.name}", 0, "a skill folder without SKILL.md")
                continue
            meta = frontmatter(skill_file.read_text(encoding="utf-8"))
            if meta.get("name") != folder.name or not meta.get("description"):
                out.add(f"{SKILLS}/{folder.name}/SKILL.md", 1, "needs name (= folder name) and description")
            link = root / CLAUDE_SKILLS / folder.name
            want = "/".join(("..", "..", SKILLS, folder.name))
            if not link.is_symlink() or os.readlink(link).replace("\\", "/") != want:
                out.add(f"{CLAUDE_SKILLS}/{folder.name}", 0, f"must be a symlink to {want} (ln -s {want} {link.name})")
        extra = root / CLAUDE_SKILLS
        if extra.is_dir():
            for p in extra.iterdir():
                if not (skills / p.name).is_dir():
                    out.add(f"{CLAUDE_SKILLS}/{p.name}", 0, f"skills live in {SKILLS}; here only symlinks to them")
    if (root / CLAUDE_AGENTS).is_dir() or (root / CODEX_AGENTS).is_dir():
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # our own script, never the checked repo's
        try:
            import sync_agents
        finally:
            sys.path.pop(0)
        for rel in sync_agents.stale(root):
            out.add(rel, 0, "differs from .claude/agents: run python scripts/sync_agents.py")
    return out


def frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        return {}
    meta = {}
    for line in text[4:].split("\n---", 1)[0].splitlines():
        if ":" in line and not line.startswith(" "):
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta


def tests(repo: Repo) -> Outcome:
    out = Outcome("tests")
    args = repo.setting("test-command", ["-m", "pytest", "-q", "-p", "no:cacheprovider"])
    res = run([sys.executable, *args], repo.root, timeout=3600)
    text = res.stdout + res.stderr
    tail = (text.strip().splitlines() or ["?"])[-1]
    if res.returncode != 0:
        for line in text.splitlines():
            if line.startswith(("FAILED", "ERROR", "FAIL:")):
                out.add("tests", 0, line)
        if not out.findings:
            out.add("tests", 0, tail)
    else:
        out.notes.append(tail)
    return out

