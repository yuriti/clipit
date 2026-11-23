"""Personal traces: home folders, e-mail addresses, commit authors, and the maintainers' private word list.

The private list is never in the repository (it would be the leak itself): a person keeps it in
~/.config/smtv/private-words.txt (or SMTV_PRIVATE_WORDS_FILE), GitHub passes it as the secret SMTV_PRIVATE_WORDS.
Format: `scripts/smtvcheck/private-words.example.txt`. In CI a match is named by its line in the list, never by the
word, so the public log does not print it.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from .common import Outcome, Repo, run

NAME = r"([A-Za-z0-9][^/\\\s\"'`)<>{}$*|…]*)"
HOME = re.compile(r"(?:/Users/|/home/)" + NAME + r"|[A-Za-z]:\\+Users\\+" + NAME)
EMAIL = re.compile(r"(?<![\w.+-])[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})(?![\w-])")
# Names that only stand for «some person» in examples and tests.
PLACEHOLDER_USERS = {"someone", "me", "you", "user", "username", "name", "runner", "smtv", "example", "person",
                     "admin", "test", "shared", "public", "default"}
SAFE_DOMAINS = ("example.com", "example.org", "example.net", "users.noreply.github.com", "noreply.github.com")
SAFE_SUFFIXES = (".example", ".test", ".invalid", ".localhost")
FILE_SUFFIXES = {"png", "jpg", "jpeg", "svg", "webp", "gif", "js", "css", "json", "py", "mp4", "wav", "woff", "woff2",
                 "ico", "html", "txt", "md", "toml"}
DEFAULT_LIST = Path.home() / ".config" / "smtv" / "private-words.txt"
# Any GitHub noreply address passes here; an old or private account is stopped by the private word list, which every
# author and committer name and address is also checked against (authors()).
AUTHORS = [r"^(\d+\+)?[A-Za-z0-9-]+@users\.noreply\.github\.com$",
           r"^noreply@github\.com$", r"^[A-Za-z0-9-]+\[bot\]@users\.noreply\.github\.com$"]


def private_words(env: dict | None = None) -> tuple[list[tuple[int, re.Pattern, str]], str]:
    """[(line in the list, pattern, the word as written)] and where the list came from («» when there is none)."""
    env = os.environ if env is None else env
    text, source = env.get("SMTV_PRIVATE_WORDS", ""), "SMTV_PRIVATE_WORDS"
    if not text.strip():
        path = Path(env.get("SMTV_PRIVATE_WORDS_FILE") or DEFAULT_LIST)
        text, source = (path.read_text(encoding="utf-8"), str(path)) if path.is_file() else ("", "")
    words = []
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("re:"):
            words.append((n, re.compile(line[3:].strip(), re.IGNORECASE), line))
        else:
            words.append((n, re.compile(r"(?<![\w])" + re.escape(line) + r"(?![\w])", re.IGNORECASE), line))
    return words, source


def safe_email(addr: str, domain: str, allowed: set[str]) -> bool:
    d = domain.lower()
    return (addr.lower() in allowed or d in SAFE_DOMAINS or d.endswith(SAFE_SUFFIXES)
            or d.rsplit(".", 1)[-1] in FILE_SUFFIXES or d.endswith(".users.noreply.github.com"))


def scan_text(rel: str, text: str, out: Outcome, words, ci: bool, users: set[str], emails: set[str],
              patterns: bool = True) -> None:
    """`patterns=False`: only the private words (files with made-up paths and addresses on purpose)."""
    for n, line in enumerate(text.splitlines(), 1):
        for m in HOME.finditer(line) if patterns else ():
            who = (m.group(1) or m.group(2) or "").strip()
            if len(who) > 2 and who.lower() not in users:
                out.add(rel, n, f"home folder of a real person ({m.group(0)[:40]}); use ~ or a placeholder like someone")
        for m in EMAIL.finditer(line) if patterns else ():
            if not safe_email(m.group(0), m.group(1), emails):
                out.add(rel, n, f"e-mail address {m.group(0)}; use a noreply or example.com address")
        for i, pattern, word in words:
            if pattern.search(line):
                out.add(rel, n, f"private word #{i} from the list" if ci else f"private word «{word}»")


def mask(out: Outcome, words) -> Outcome:
    """In CI the log is public: a private word must not appear anywhere in it, also not inside a file name, a home
    folder or an e-mail address a finding quotes. Each is replaced by its line number in the list."""
    for f in out.findings:
        for i, pattern, _ in words:
            f.path = pattern.sub(f"[private #{i}]", f.path)
            f.message = pattern.sub(f"[private #{i}]", f.message)
    return out


def diff(repo: Repo, patch: str, log: str | None = None, env: dict | None = None) -> Outcome:
    """Only the lines a pull request adds, and its commit authors: for CI with the private list, where the PR's code is
    never checked out (workflow private-words)."""
    out = Outcome("traces")
    words, source = private_words(env)
    if not words:
        out.add("-", 0, "no private word list given (SMTV_PRIVATE_WORDS), or it holds no words")
    users = PLACEHOLDER_USERS | {u.lower() for u in repo.setting("placeholder-users", [])}
    emails = {e.lower() for e in repo.setting("allowed-emails", [])}
    path, n = "?", 0
    for line in patch.splitlines():
        if line.startswith("+++ "):
            path = line[4:].removeprefix("b/")
            scan_text("(file name)", path, out, words, repo.ci, users, emails)
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            n = int(m.group(1)) - 1 if m else 0
        elif line.startswith("+"):
            n += 1
            sub = Outcome("line")
            scan_text(path, line[1:], sub, words, repo.ci, users, emails)
            out.findings += [type(f)(f.path, n, f.message) for f in sub.findings]
        elif not line.startswith(("-", "\\")):
            n += 1
    if log is not None:
        if patch.strip() and not log.strip():
            out.add("-", 0, "no commit authors given for a non-empty pull request")
        authors(repo, out, words, log)
    return mask(out, words) if repo.ci else out


def check(repo: Repo, env: dict | None = None) -> Outcome:
    out = Outcome("traces")
    words, source = private_words(env)
    if not words:
        msg = "no private word list (~/.config/smtv/private-words.txt or SMTV_PRIVATE_WORDS): names were not searched"
        if repo.ci and (env if env is not None else os.environ).get("SMTV_REQUIRE_PRIVATE_WORDS") == "1":
            out.add("-", 0, msg)
        else:
            out.notes.append(msg)
    users = PLACEHOLDER_USERS | {u.lower() for u in repo.setting("placeholder-users", [])}
    emails = {e.lower() for e in repo.setting("allowed-emails", [])}
    skip = set(repo.setting("traces-skip", []))
    for rel in repo.files():
        text = repo.text(rel)
        if text is not None:
            scan_text(rel, text, out, words, repo.ci, users, emails, patterns=rel not in skip)
        scan_text("(file name)", rel, out, words, repo.ci, users, emails)
    for rel in repo.unread:
        out.notes.append(f"not searched (larger than 2 MB): {rel}")
    if repo.git:
        authors(repo, out, words)
    return mask(out, words) if repo.ci else out


def authors(repo: Repo, out: Outcome, words, log: str | None = None) -> None:
    """Every author and committer in history (or in SMTV_CHECK_RANGE, e.g. origin/main..HEAD) is a noreply address."""
    if log is None:
        cmd = ["git", "log", "--format=%H%x00%an%x00%ae%x00%cn%x00%ce"]
        if os.environ.get("SMTV_CHECK_RANGE"):
            cmd.append(os.environ["SMTV_CHECK_RANGE"])
        res = run(cmd, repo.root)
        if res.returncode != 0:
            msg = "git log failed: commit authors not checked"
            out.add("-", 0, msg) if repo.ci else out.notes.append(msg)
            return
        log = res.stdout
    rules = [re.compile(r) for r in repo.setting("author-emails", AUTHORS)]
    for row in log.splitlines():
        parts = row.split("\0")
        if len(parts) != 5:
            if row.strip():
                out.add("commit authors", 0, "a line of the author list could not be read: the check cannot vouch for it")
            continue
        sha, an, ae, cn, ce = parts
        for name, mail in ((an, ae), (cn, ce)):
            if not any(r.match(mail) for r in rules):
                out.add(f"commit {sha[:9]}", 0, f"{mail} is not a GitHub noreply address "
                                                "(git config user.email <id>+<login>@users.noreply.github.com)")
            for i, pattern, word in words:
                if pattern.search(name) or pattern.search(mail):
                    out.add(f"commit {sha[:9]}", 0, f"private word #{i} in the author" if repo.ci
                            else f"private word «{word}» in the author")


def secrets(repo: Repo) -> Outcome:
    """Keys and tokens, by gitleaks: the history when there is git, the files otherwise."""
    import shutil
    out = Outcome("secrets")
    exe = shutil.which("gitleaks")
    if exe is None:
        out.skipped = "gitleaks is not installed (macOS: brew install gitleaks; CI installs it)"
        return out
    cmd = [exe, "git" if repo.git else "dir", "--no-banner", "--redact", "--exit-code", "1"]
    config = None
    if not repo.git:
        # without git, the folders that are never part of the repository (build/ with the apps' Python, .venv) stay out:
        # gitleaks' own rules plus an allow-list of those paths
        import tempfile
        from .common import SKIP_DIRS
        skip = "|".join(re.escape(d) for d in sorted(SKIP_DIRS))
        config = tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False, encoding="utf-8")
        config.write('[extend]\nuseDefault = true\n\n[allowlist]\npaths = ["""(^|/)(' + skip.replace("\\", "\\\\") + ')/"""]\n')
        config.close()
        cmd += ["--config", config.name, str(repo.root)]
    try:
        res = run(cmd, repo.root)
    finally:
        if config:
            os.unlink(config.name)
    if res.returncode == 0 and repo.git:       # also what is staged for the next commit (pre-commit, the hook)
        res = run([exe, "git", "--staged", "--no-banner", "--redact", "--exit-code", "1"], repo.root)
    if res.returncode == 1:
        for line in (res.stdout + res.stderr).splitlines():
            if line.strip().startswith(("Finding:", "File:", "Line:", "RuleID:", "Commit:")):
                out.add("gitleaks", 0, line.strip())
        if not out.findings:
            out.add("gitleaks", 0, "leaks found: run gitleaks yourself to see them")
    elif res.returncode != 0:
        out.add("gitleaks", 0, "gitleaks failed: " + ((res.stderr.strip().splitlines() or ["?"])[-1]))
    return out
