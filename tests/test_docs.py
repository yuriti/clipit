"""The README, its translations and the guides for newcomers (stage V7): every language listed at the top of README.md
has its README and every guide, each translation says it was translated automatically and links Weblate, every link
inside the repository leads to a file that exists (and to a heading that exists, when it names one), the window's link
to the guides is alive, and the pictures stay small enough for git."""
from __future__ import annotations

import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / "docs" / "guide"
IMAGES = ROOT / "docs" / "images"
WEBLATE = "https://hosted.weblate.org/engage/smtv/"
MARK = "<!-- languages -->"
LINK = re.compile(r"\]\(([^)\s]+)\)|\b(?:src|href)=\"([^\"]+)\"")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$")
MAX_IMAGE = 5 * 1024 * 1024          # one GIF or picture; GitHub shows the README's pictures from the repository
MAX_IMAGES = 25 * 1024 * 1024        # all of docs/images together (the rule and the reason: AGENTS.md, «Pictures»)


def languages() -> list[str]:
    """The language codes the English README's switcher links (README.<code>.md), in its order."""
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    line = text.split(MARK, 1)[1].strip().splitlines()[0]
    return re.findall(r"\(README\.([A-Za-z-]+)\.md\)", line)


def docs() -> list[Path]:
    return sorted([*ROOT.glob("README*.md"), *(ROOT / "docs").rglob("*.md")])


def slug(heading: str) -> str:
    """A heading's anchor as GitHub makes it: lower case, spaces to hyphens, punctuation and emoji dropped, letters of
    every script (with their combining marks) kept."""
    text = re.sub(r"[`*_]|\[([^\]]*)\]\([^)]*\)", lambda m: m.group(1) or "", heading).strip().lower()
    kept = "".join(c for c in text if c in " -_" or unicodedata.category(c)[0] in "LNM")
    return kept.replace(" ", "-")


def anchors(path: Path) -> set[str]:
    found, seen = set(), {}
    fenced = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        m = None if fenced else HEADING.match(line)
        if m:
            base = slug(m.group(1))
            n = seen.get(base, 0)
            seen[base] = n + 1
            found.add(base if n == 0 else f"{base}-{n}")
    return found


def links(path: Path) -> list[str]:
    text = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
    return [a or b for a, b in LINK.findall(text)]


def test_every_language_has_its_readme_and_every_guide():
    langs = languages()
    assert len(langs) >= 10, langs
    pages = sorted(p.name for p in GUIDE.glob("*.md"))
    assert {"README.md", "install.md", "first-clip.md", "connect-ai.md", "free-ai-on-your-computer.md", "get-a-key.md",
            "troubleshooting.md"} <= set(pages)
    missing = [f"README.{code}.md" for code in langs if not (ROOT / f"README.{code}.md").is_file()]
    missing += [f"docs/guide/{code}/{page}" for code in langs for page in pages if not (GUIDE / code / page).is_file()]
    assert not missing, missing


def test_no_translation_outside_the_list():
    langs = set(languages())
    readmes = {p.name[len("README."):-len(".md")] for p in ROOT.glob("README.*.md")}
    folders = {p.name for p in GUIDE.iterdir() if p.is_dir()}
    assert readmes <= langs, readmes - langs
    assert folders <= langs, folders - langs


@pytest.mark.parametrize("code", languages())
def test_a_translation_says_it_is_automatic_and_links_weblate(code):
    for path in [ROOT / f"README.{code}.md", *sorted((GUIDE / code).glob("*.md"))]:
        text = path.read_text(encoding="utf-8")
        assert MARK in text, f"{path.relative_to(ROOT)}: no language switcher"
        assert WEBLATE in text, f"{path.relative_to(ROOT)}: no «translated automatically» line with the Weblate link"


def test_every_page_with_a_switcher_links_every_language():
    langs = languages()
    for path in docs():
        text = path.read_text(encoding="utf-8")
        if MARK not in text:
            continue
        line = text.split(MARK, 1)[1].strip().splitlines()[0]
        assert line.count(" · ") == len(langs), f"{path.relative_to(ROOT)}: the switcher lists {line.count(' · ') + 1} languages"


def test_language_lines_are_written_by_the_script():
    res = subprocess.run([sys.executable, str(ROOT / "scripts" / "doc_languages.py"), "--check"], capture_output=True, text=True)
    assert res.returncode == 0, f"run: python scripts/doc_languages.py\n{res.stdout}"


def test_links_inside_the_repository_lead_somewhere():
    broken = []
    for path in docs():
        for target in links(path):
            if re.match(r"^[a-z]+:", target) or target.startswith("//"):
                continue                      # http(s), mailto: outside the repository
            file, _, anchor = target.partition("#")
            dest = (path.parent / file).resolve() if file else path
            where = f"{path.relative_to(ROOT)} → {target}"
            if not dest.exists():
                broken.append(f"{where}: no such file")
            elif anchor and dest.suffix == ".md" and anchor not in anchors(dest):
                broken.append(f"{where}: no such heading")
    assert not broken, "\n".join(broken)


def test_the_window_links_guides_that_exist():
    app = (ROOT / "packages/smtv/src/smtv/web/app.js").read_text(encoding="utf-8")
    base = re.search(r'const GUIDE = "([^"]+)"', app)
    assert base and base.group(1).endswith("/docs/guide/"), "app.js: GUIDE should point at docs/guide/ on GitHub"
    pages = re.findall(r'GUIDE \+ "([^"]+)"', app)
    assert pages, "app.js links no guide"
    for page in pages:
        assert (GUIDE / page).is_file(), f"app.js links docs/guide/{page}, which does not exist"


def test_pictures_stay_small():
    files = [p for p in IMAGES.rglob("*") if p.is_file()]
    big = [f"{p.name}: {p.stat().st_size // 1024} KB" for p in files if p.stat().st_size > MAX_IMAGE]
    assert not big, big
    assert sum(p.stat().st_size for p in files) <= MAX_IMAGES


def test_slug_matches_github():
    assert slug("Install in one line") == "install-in-one-line"
    assert slug("If the system warns you") == "if-the-system-warns-you"
    assert slug("How SMTV compares") == "how-smtv-compares"
    assert slug("1. Computer check → Fix") == "1-computer-check--fix"
    assert slug("Установка одной строкой") == "установка-одной-строкой"
    assert slug("एक लाइन में इंस्टॉल") == "एक-लाइन-में-इंस्टॉल"


def test_anchors_follow_github_for_the_uzbek_letter():
    """V9: GitHub keeps «ʻ» (U+02BB, a letter, Lm) in an anchor and drops «’» (U+2019, punctuation): github-slugger's
    regex.js has no range over U+02BB, html-pipeline's toc filter keeps \\p{Word}. So `#bir-qatorda-oʻrnatish` works."""
    assert slug("Bir qatorda oʻrnatish") == "bir-qatorda-oʻrnatish"
    assert slug("SMTV’ni oʻrnatish") == "smtvni-oʻrnatish"
    assert slug("SMTV boshqalar bilan taqqoslaganda") == "smtv-boshqalar-bilan-taqqoslaganda"
