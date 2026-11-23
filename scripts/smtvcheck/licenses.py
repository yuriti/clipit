"""Licenses: every dependency our packages pull in has an allowed license; fonts come with theirs; the third-party
notices file is built from what is installed, never written by hand."""
from __future__ import annotations

import re
from importlib import metadata
from pathlib import Path

from .common import Outcome, Repo

# Permissive licenses: code under them may ship inside or next to SMTV. Anything else needs a reasoned exception in
# [tool.smtv-check.license-exceptions]; copyleft (GPL and the like) never gets one.
ALLOWED = {"MIT", "MIT-CMU", "BSD-2-Clause", "BSD-3-Clause", "0BSD", "Apache-2.0", "ISC", "PSF-2.0", "Python-2.0",
           "Unlicense", "Zlib", "CC0-1.0", "HPND"}
COPYLEFT = re.compile(r"(?<![A-Za-z])(A?GPL|LGPL|GNU|SSPL|EUPL|CDDL|EPL|OSL|BUSL|CC-BY-NC|CC-BY-SA|Commons.Clause)",
                      re.IGNORECASE)

# Trove classifiers and the free-text «License:» field, as SPDX ids.
NAMES = {
    "mit license": "MIT", "mit": "MIT",
    "bsd license": "BSD-3-Clause", "3-clause bsd license": "BSD-3-Clause", "bsd-3-clause": "BSD-3-Clause",
    "bsd 3-clause": "BSD-3-Clause", "new bsd license": "BSD-3-Clause", "bsd-2-clause": "BSD-2-Clause",
    "apache software license": "Apache-2.0", "apache 2.0": "Apache-2.0", "apache-2.0": "Apache-2.0",
    "apache license 2.0": "Apache-2.0", "apache license, version 2.0": "Apache-2.0",
    "isc license (iscl)": "ISC", "isc": "ISC",
    "python software foundation license": "PSF-2.0", "psf": "PSF-2.0",
    "mozilla public license 2.0 (mpl 2.0)": "MPL-2.0",
    "the unlicense (unlicense)": "Unlicense", "unlicense": "Unlicense",
    "zlib/libpng license": "Zlib", "historical permission notice and disclaimer (hpnd)": "HPND",
}
FONT_SUFFIXES = {".ttf", ".otf", ".woff", ".woff2"}
MODEL_SUFFIXES = {".onnx"}            # a model shipped inside a package (B12: the YuNet face detector)
NOTICES = "THIRD_PARTY_LICENSES.md"


def normal(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def identify(meta) -> str:
    """The distribution's license as an SPDX expression, «UNKNOWN» when it does not say."""
    expr = (meta.get("License-Expression") or "").strip()
    if expr:
        return expr
    found = []
    for c in meta.get_all("Classifier") or []:
        if c.startswith("License ::"):
            last = c.split("::")[-1].strip()
            if last != "OSI Approved":
                found.append(NAMES.get(last.lower(), last))
    if found:
        return " OR ".join(dict.fromkeys(found))     # several classifiers: the author offers a choice
    text = (meta.get("License") or "").strip()
    if text and len(text) < 60 and "\n" not in text:
        return NAMES.get(text.lower(), text)
    return "UNKNOWN"


def allowed(expr: str, allow: set[str]) -> bool:
    """An SPDX expression is fine when one of its OR choices is made only of allowed licenses."""
    if COPYLEFT.search(expr) and not any(_choice_ok(c, allow) for c in _choices(expr)):
        return False
    return any(_choice_ok(c, allow) for c in _choices(expr))


def _choices(expr: str) -> list[str]:
    return [c for c in re.split(r"\s+OR\s+", expr.replace("(", " ").replace(")", " ")) if c.strip()]


def _choice_ok(choice: str, allow: set[str]) -> bool:
    ids = [t.strip() for t in re.split(r"\s+AND\s+", choice) if t.strip()]
    return bool(ids) and all(i.split(" WITH ")[0].strip() in allow for i in ids)


def our_packages(repo: Repo) -> dict[str, list[str]]:
    """{our distribution: extras} — the workspace members, or the root project of a single-package repository."""
    import tomllib
    found = {}
    for p in sorted(repo.root.glob("packages/*/pyproject.toml")) + [repo.root / "pyproject.toml"]:
        if p.exists():
            project = tomllib.loads(p.read_text(encoding="utf-8")).get("project")
            if project and project.get("name"):
                found[normal(project["name"])] = sorted(project.get("optional-dependencies", {}))
    return found


def closure(roots: dict[str, list[str]], lookup=metadata.distribution) -> tuple[dict[str, object], set[str]]:
    """Every installed distribution our packages need (with all their extras), and the names not installed here."""
    from packaging.requirements import Requirement
    seen: dict[str, object] = {}
    missing: set[str] = set()
    done: set[tuple[str, tuple]] = set()
    todo = [(name, tuple(extras)) for name, extras in roots.items()]
    while todo:
        name, extras = todo.pop()
        key = normal(name)
        if (key, extras) in done:
            continue
        done.add((key, extras))
        try:
            dist = seen.get(key) or lookup(name)
        except metadata.PackageNotFoundError:
            missing.add(key)
            continue
        seen[key] = dist
        envs = [{"extra": ""}] + [{"extra": e} for e in extras]
        for raw in dist.requires or []:
            req = Requirement(raw)
            if req.marker is None or any(req.marker.evaluate(env) for env in envs):
                todo.append((req.name, tuple(sorted(req.extras))))
    return seen, missing


def check(repo: Repo, lookup=metadata.distribution) -> Outcome:
    out = Outcome("licenses")
    allow = ALLOWED | set(repo.setting("allowed-licenses", []))
    exceptions = {normal(k): v for k, v in repo.setting("license-exceptions", {}).items()}
    roots = our_packages(repo)
    if not roots:
        out.skipped = "no [project] in pyproject.toml"
        return out
    try:
        dists, missing = closure(roots, lookup)
    except ImportError:
        out.skipped = "the packaging module is missing: install the dev group"
        return out
    for key, dist in sorted(dists.items()):
        expr = identify(dist.metadata)
        exc = exceptions.get(key)
        if exc is not None:
            if not isinstance(exc, dict) or not exc.get("why") or exc.get("license") != expr:
                out.add("pyproject.toml", 0, f"{key}: exception must say {{license = \"{expr}\", why = \"…\"}}")
            elif COPYLEFT.search(expr):
                out.add("pyproject.toml", 0, f"{key}: {expr} is copyleft; no exception allowed")
            continue
        if not allowed(expr, allow):
            out.add("dependencies", 0, f"{key} {dist.version}: license «{expr}» is not allowed "
                                       "(MIT, BSD, Apache, ISC, PSF…); drop it or ask the maintainers for an exception")
    for key in sorted(exceptions):
        if key not in dists and key not in missing:
            out.notes.append(f"exception for {key} is unused here")
    if missing:
        out.notes.append("not installed here, so not checked: " + ", ".join(sorted(missing)))
    for rel in repo.files():
        if Path(rel).suffix.lower() in FONT_SUFFIXES:
            folder = (repo.root / rel).parent
            if not any(re.match(r"(OFL|LICEN[CS]E)", f.name, re.I) for f in folder.iterdir()):
                out.add(rel, 0, "font without its license file (OFL-*.txt or LICENSE) in the same folder")
        if Path(rel).suffix.lower() in MODEL_SUFFIXES:
            folder = (repo.root / rel).parent
            if not any(re.match(r"LICEN[CS]E", f.name, re.I) for f in folder.iterdir()):
                out.add(rel, 0, "bundled model without its license file (LICENSE-<name>.txt) in the same folder")
    return out


def notices(repo: Repo, lookup=metadata.distribution) -> str:
    """THIRD_PARTY_LICENSES.md for a release: the dependencies installed here, bundled fonts, speech models."""
    roots = our_packages(repo)
    dists, _ = closure(roots, lookup)
    lines = ["# Third-party licenses", "", "Built by `python scripts/check.py licenses --write`; do not edit by hand.", "",
             "## Python packages", "", "| Package | Version | License | Home page |", "|---|---|---|---|"]
    for key, dist in sorted(dists.items()):
        if key in roots:
            continue
        meta = dist.metadata
        home = meta.get("Home-page") or next((u.split(",", 1)[1].strip() for u in meta.get_all("Project-URL") or []
                                              if u.lower().startswith(("homepage", "source", "repository"))), "")
        lines.append(f"| {meta['Name']} | {dist.version} | {identify(meta)} | {home} |")
    fonts = sorted({str(Path(r).parent) for r in repo.files() if Path(r).suffix.lower() in FONT_SUFFIXES})
    if fonts:
        lines += ["", "## Fonts", ""]
        for folder in fonts:
            for lic in sorted((repo.root / folder).glob("OFL*")):
                lines.append(f"- `{folder}`: SIL Open Font License 1.1, see `{folder}/{lic.name}`")
    bundled = sorted(r for r in repo.files() if Path(r).suffix.lower() in MODEL_SUFFIXES)
    if bundled:
        lines += ["", "## Bundled models", ""]
        for rel in bundled:
            for lic in sorted((repo.root / rel).parent.glob("LICEN[CS]E*")):
                lines.append(f"- `{rel}`: see `{Path(rel).parent.as_posix()}/{lic.name}`")
    try:
        from smtv_core.asr.catalog import MODELS
    except ImportError:
        MODELS = {}
    local = [m for m in MODELS.values() if m.where == "local"]
    if local:
        lines += ["", "## Speech models (downloaded on first use, not shipped)", ""]
        for m in local:
            lines.append(f"- {m.title}: {m.license}, {m.links.get('model', '')}")
    return "\n".join(lines) + "\n"
