"""Copy a released version of the prompts repository into smtv-core.

    python scripts/sync_prompts.py ../prompts            copy and report what changed
    python scripts/sync_prompts.py ../prompts --check    only report; exit 1 if the bundled copy differs
    python scripts/sync_prompts.py --intact              without ../prompts: the bundled copy is whole and readable

The prompts are changed and tested in the prompts repository (its harness, a private checkout next to this one),
released as a version (its VERSION file and a git tag) and only then copied here. The bundled copy in smtv-core is
what is published: anyone without ../prompts (CI, a contributor) checks only that it is whole (--intact). Never edit
the bundled copy by hand.
What is copied: vod/*.txt, fit/*.txt, schemas/*.json, models.json (the model for each agent and provider, and what was
tested), prices.json (dollars per million tokens of each known model) and VERSION.
"""
from __future__ import annotations

import argparse
import filecmp
import json
import re
import shutil
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parent.parent / "packages" / "smtv-core" / "src" / "smtv_core" / "prompts"
PARTS = (("vod", "*.txt"), ("fit", "*.txt"), ("schemas", "*.json"), (".", "models.json"), (".", "prices.json"))


def plan(source: Path) -> list[tuple[str, Path, Path]]:
    """[(change, source file or None, target file)] with change in added | changed | removed."""
    filecmp.clear_cache()   # filecmp remembers by size and time: a copy made in the same clock tick looked unchanged (Windows)
    out = []
    for folder, pattern in PARTS:
        src_files = {p.name: p for p in (source / folder).glob(pattern)}
        dst_files = {p.name: p for p in (TARGET / folder).glob(pattern)}
        for name, src in sorted(src_files.items()):
            dst = TARGET / folder / name
            if name not in dst_files:
                out.append(("added", src, dst))
            elif not filecmp.cmp(src, dst, shallow=False):
                out.append(("changed", src, dst))
        for name, dst in sorted(dst_files.items()):
            if name not in src_files:
                out.append(("removed", None, dst))
    if not filecmp.cmp(source / "VERSION", TARGET / "VERSION", shallow=False):
        out.append(("changed", source / "VERSION", TARGET / "VERSION"))
    return out


def broken(target: Path | None = None) -> list[str]:
    """What is wrong with the bundled copy on its own: a release VERSION, every part present, every file readable and
    every JSON file valid. Used where ../prompts is not next to this repository (CI, a contributor's checkout)."""
    target = target or TARGET
    problems = []
    version = (target / "VERSION").read_text(encoding="utf-8").strip() if (target / "VERSION").is_file() else ""
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        problems.append(f"VERSION: {version or 'missing'} is not a release number like 1.2.3")
    for folder, pattern in PARTS:
        files = sorted((target / folder).glob(pattern))
        if not files:
            problems.append(f"{folder}/{pattern}: nothing there")
        for f in files:
            try:
                text = f.read_text(encoding="utf-8")
                if f.suffix == ".json":
                    json.loads(text)
                elif not text.strip():
                    problems.append(f"{f.relative_to(target)}: empty")
            except (OSError, ValueError) as e:
                problems.append(f"{f.relative_to(target)}: {type(e).__name__}: {e}"[:200])
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, nargs="?", help="the prompts repository folder")
    parser.add_argument("--check", action="store_true", help="only compare")
    parser.add_argument("--intact", action="store_true", help="without the prompts repository: check the bundled copy")
    args = parser.parse_args(argv)
    if args.intact:
        problems = broken()
        for p in problems:
            print(f"  {p}")
        version = (TARGET / "VERSION").read_text(encoding="utf-8").strip() if not problems else ""
        print(f"Bundled prompts are whole (version {version})." if not problems else "Bundled prompts are broken.")
        return 1 if problems else 0
    if args.source is None:
        parser.error("the prompts repository folder, or --intact")
    source = args.source.expanduser().resolve()
    if not (source / "VERSION").exists() or not (source / "vod").is_dir():
        print(f"{source} does not look like the prompts repository (no VERSION or vod/)")
        return 2
    changes = plan(source)
    version = (source / "VERSION").read_text(encoding="utf-8").strip()
    if not changes:
        print(f"Bundled prompts are the same as {source} (version {version}).")
        return 0
    for change, _src, dst in changes:
        print(f"  {change:<8} {dst.relative_to(TARGET)}")
    if args.check:
        print(f"Bundled prompts differ from {source}. Run without --check to copy version {version}.")
        return 1
    for change, src, dst in changes:
        if change == "removed":
            dst.unlink()
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    print(f"Copied prompts version {version}. Now run the tests: python -m pytest -q")
    return 0


if __name__ == "__main__":
    sys.exit(main())
