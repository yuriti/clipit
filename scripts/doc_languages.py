"""Write the language line at the top of the README, its translations and the guides for newcomers.

    python scripts/doc_languages.py            rewrite every language line
    python scripts/doc_languages.py --check    only report; exit 1 if a line differs

The line comes right after `<!-- languages -->` and links every language of LANGS: `README.<code>.md` in the root,
`docs/guide/<code>/<page>.md` for a guide. A new language: add it to LANGS, add its README and guides, run this.
`tests/test_docs.py` checks the result (every language has every page, every link leads somewhere).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARK = "<!-- languages -->"
LANGS = [("en", "English"), ("ru", "Русский"), ("kk", "Қазақша"), ("uz", "Oʻzbekcha"), ("az", "Azərbaycanca"),
         ("ky", "Кыргызча"), ("zh-CN", "简体中文"), ("ja", "日本語"), ("ko", "한국어"), ("vi", "Tiếng Việt"),
         ("id", "Bahasa Indonesia"), ("hi", "हिन्दी"), ("bn", "বাংলা"), ("es", "Español"), ("pt-BR", "Português"),
         ("de", "Deutsch")]


def target(page: str | None, current: str, lang: str) -> str:
    """Where the link to `lang` goes from a page in `current` (page None: the README)."""
    if page is None:
        return "README.md" if lang == "en" else f"README.{lang}.md"
    if current == "en":
        return page if lang == "en" else f"{lang}/{page}"
    return f"../{page}" if lang == "en" else f"../{lang}/{page}"


def line(page: str | None, current: str) -> str:
    return " · ".join(f"**{name}**" if code == current else f"[{name}]({target(page, current, code)})" for code, name in LANGS)


def rewrite(text: str, page: str | None, current: str) -> str:
    lines, out, i = text.split("\n"), [], 0
    while i < len(lines):
        out.append(lines[i])
        if lines[i].strip() == MARK:
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            if " · " in nxt and nxt.startswith(("**", "[")):
                i += 1                      # the old line is replaced, not kept
            out.append(line(page, current))
        i += 1
    return "\n".join(out)


def pages() -> list[tuple[Path, str | None, str]]:
    found: list[tuple[Path, str | None, str]] = []
    for p in ROOT.glob("README*.md"):
        m = re.fullmatch(r"README(?:\.(.+))?\.md", p.name)
        if m:
            found.append((p, None, m.group(1) or "en"))
    guide = ROOT / "docs" / "guide"
    found += [(p, p.name, "en") for p in guide.glob("*.md")]
    for code, _ in LANGS[1:]:
        found += [(p, p.name, code) for p in (guide / code).glob("*.md")]
    return sorted(found)


def main(argv: list[str]) -> int:
    check = "--check" in argv
    differ = []
    for path, page, current in pages():
        old = path.read_text(encoding="utf-8")
        new = rewrite(old, page, current)
        if new != old:
            differ.append(str(path.relative_to(ROOT)))
            if not check:
                path.write_text(new, encoding="utf-8")
    if differ:
        print(("differ: " if check else "rewritten: ") + ", ".join(differ))
    return 1 if check and differ else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
