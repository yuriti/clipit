"""The repository checks (scripts/check.py, stage 25) on made-up repositories: licenses, hosts, copied code, personal
traces and the private word list, the supply chain, duplicates, agents and skills in sync, and the agent hook."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from email.message import Message
from importlib import metadata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "hooks"))

import agent_gate  # noqa: E402
import check  # noqa: E402
import sync_agents  # noqa: E402
from smtvcheck import hosts, licenses, quality, supply, sync, traces  # noqa: E402
from smtvcheck.common import Repo  # noqa: E402

NO_WORDS = {"SMTV_PRIVATE_WORDS_FILE": "/nonexistent/list"}


def tree(base: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        p = base / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return base


def repo(tmp_path: Path, files: dict[str, str], config: dict | None = None, ci: bool = False) -> Repo:
    return Repo(tree(tmp_path, files), config=config or {}, ci=ci)


def messages(outcome) -> list[str]:
    return [str(f) for f in outcome.findings]


# --- licenses -----------------------------------------------------------------------------------------------------

class FakeDist:
    def __init__(self, name, requires=(), expression="", classifiers=(), text="", version="1.0"):
        self.metadata = Message()
        self.metadata["Name"] = name
        if expression:
            self.metadata["License-Expression"] = expression
        for c in classifiers:
            self.metadata["Classifier"] = c
        if text:
            self.metadata["License"] = text
        self.requires = list(requires)
        self.version = version


def lookup_from(dists: dict[str, FakeDist]):
    def lookup(name):
        key = licenses.normal(name)
        if key not in dists:
            raise metadata.PackageNotFoundError(name)
        return dists[key]
    return lookup


PROJECT = '[project]\nname = "ourtool"\nversion = "1"\n[project.optional-dependencies]\nextra1 = ["only-extra"]\n'


def test_license_is_read_from_expression_then_classifiers_then_the_free_text_field():
    assert licenses.identify(FakeDist("a", expression="Apache-2.0 OR BSD-2-Clause").metadata) == "Apache-2.0 OR BSD-2-Clause"
    assert licenses.identify(FakeDist("a", classifiers=["License :: OSI Approved :: MIT License"]).metadata) == "MIT"
    assert licenses.identify(FakeDist("a", text="3-Clause BSD License").metadata) == "BSD-3-Clause"
    assert licenses.identify(FakeDist("a", text="x" * 200).metadata) == "UNKNOWN"
    assert licenses.identify(FakeDist("a").metadata) == "UNKNOWN"


@pytest.mark.parametrize("expr, ok", [
    ("MIT", True), ("MIT-0", True), ("Apache-2.0 OR BSD-2-Clause", True), ("BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0", True),
    ("GPL-3.0-only", False), ("LGPL-2.1-or-later", False), ("MIT AND GPL-2.0", False), ("GPL-2.0 OR MIT", True),
    ("MPL-2.0", False), ("UNKNOWN", False), ("AGPL-3.0", False),
])
def test_allowed_licenses(expr, ok):
    assert licenses.allowed(expr, licenses.ALLOWED) is ok


def test_dependency_tree_with_a_gpl_package_fails_and_names_it(tmp_path):
    r = repo(tmp_path, {"pyproject.toml": PROJECT})
    dists = {
        "ourtool": FakeDist("ourtool", ["good>=1", "bad", 'only-extra; extra == "extra1"', 'winonly; sys_platform == "nope"'],
                            expression="MIT"),
        "good": FakeDist("good", ["deep"], expression="BSD-3-Clause"),
        "deep": FakeDist("deep", classifiers=["License :: OSI Approved :: GNU General Public License v3 (GPLv3)"]),
        "bad": FakeDist("bad", expression="GPL-3.0-or-later"),
        "only-extra": FakeDist("only-extra", expression="MIT"),
    }
    out = licenses.check(r, lookup_from(dists))
    text = "\n".join(messages(out))
    assert "deep 1.0" in text and "bad 1.0" in text and "good" not in text
    assert out.notes == []                       # winonly's marker is false here; only-extra comes with our extra


def test_a_missing_dependency_is_noted_not_failed(tmp_path):
    r = repo(tmp_path, {"pyproject.toml": PROJECT})
    out = licenses.check(r, lookup_from({"ourtool": FakeDist("ourtool", ["ghost"], expression="MIT")}))
    assert out.ok and "ghost" in out.notes[0]


def test_an_exception_needs_the_exact_license_and_a_reason_and_never_covers_copyleft(tmp_path):
    dists = {"ourtool": FakeDist("ourtool", ["mpl", "gpl"], expression="MIT"),
             "mpl": FakeDist("mpl", expression="MPL-2.0"), "gpl": FakeDist("gpl", expression="GPL-3.0")}
    good = {"license-exceptions": {"mpl": {"license": "MPL-2.0", "why": "used unchanged"},
                                   "gpl": {"license": "GPL-3.0", "why": "please"}}}
    out = licenses.check(repo(tmp_path, {"pyproject.toml": PROJECT}, good), lookup_from(dists))
    assert messages(out) == ["pyproject.toml: gpl: GPL-3.0 is copyleft; no exception allowed"]
    stale = {"license-exceptions": {"mpl": {"license": "MPL-1.1", "why": "old"}}}
    out = licenses.check(repo(tmp_path, {"pyproject.toml": PROJECT}, stale), lookup_from(dists))
    assert any("mpl: exception must say" in m for m in messages(out))
    silent = {"ourtool": FakeDist("ourtool", ["quiet"], expression="MIT"), "quiet": FakeDist("quiet")}   # clr-loader
    assert licenses.check(repo(tmp_path, {"pyproject.toml": PROJECT}), lookup_from(silent)).findings
    known = {"license-exceptions": {"quiet": {"license": "UNKNOWN", "why": "the LICENSE file in the wheel is MIT"}}}
    assert not licenses.check(repo(tmp_path, {"pyproject.toml": PROJECT}, known), lookup_from(silent)).findings


def test_a_font_needs_its_license_next_to_it(tmp_path):
    lookup = lookup_from({"ourtool": FakeDist("ourtool", expression="MIT")})
    r = repo(tmp_path, {"pyproject.toml": PROJECT, "fonts/a.woff": "x"})
    assert "font without its license" in messages(licenses.check(r, lookup))[0]
    tree(tmp_path, {"fonts/OFL-A.txt": "SIL"})
    assert licenses.check(Repo(tmp_path, config={}), lookup).ok


def test_a_bundled_model_needs_its_license_next_to_it_and_is_listed_in_the_notices(tmp_path):
    lookup = lookup_from({"ourtool": FakeDist("ourtool", expression="MIT")})
    r = repo(tmp_path, {"pyproject.toml": PROJECT, "models/face.onnx": "x"})
    assert "bundled model without its license" in messages(licenses.check(r, lookup))[0]
    tree(tmp_path, {"models/LICENSE-Face.txt": "MIT License"})
    r = Repo(tmp_path, config={})
    assert licenses.check(r, lookup).ok
    assert "`models/face.onnx`: see `models/LICENSE-Face.txt`" in licenses.notices(r, lookup)


def test_the_notices_file_lists_dependencies_and_fonts_but_not_our_packages(tmp_path):
    r = repo(tmp_path, {"pyproject.toml": PROJECT, "fonts/a.woff": "x", "fonts/OFL-A.txt": "SIL"})
    text = licenses.notices(r, lookup_from({"ourtool": FakeDist("ourtool", ["good"], expression="MIT"),
                                            "good": FakeDist("good", expression="ISC")}))
    assert "| good | 1.0 | ISC |" in text and "| ourtool" not in text and "fonts/OFL-A.txt" in text


# --- hosts and copied code ----------------------------------------------------------------------------------------

def test_only_allowed_hosts_in_code_and_tests_are_not_scanned(tmp_path):
    r = repo(tmp_path, {
        "packages/x/src/x/net.py": 'A = "https://api.allowed.com/v1"\nB = "https://evil.example.net/x"\n'
                                   'C = "http://127.0.0.1:8642/"\nD = "https://cdn.wild.org/a"\nE = f"https://{host}/x"\n',
        "packages/x/src/x/page.js": 'fetch("https://tracker.io/p")\n',
        "packages/x/tests/test_net.py": 'X = "https://anything.test.com"\n',
        "README.md": "[link](https://docs.somewhere.com)\n",
    }, {"hosts": ["api.allowed.com", "*.wild.org"]})
    found = messages(hosts.check(r))
    assert found == ["packages/x/src/x/net.py:2: evil.example.net is not an allowed host: add it to [tool.smtv-check] hosts with the reason",
                     "packages/x/src/x/page.js:1: tracker.io is not an allowed host: add it to [tool.smtv-check] hosts with the reason"]


def test_wildcard_host_covers_subdomains_and_the_domain_itself():
    assert hosts.host_allowed("a.b.wild.org", ["*.wild.org"]) and hosts.host_allowed("wild.org", ["*.wild.org"])
    assert not hosts.host_allowed("notwild.org", ["*.wild.org"])
    assert hosts.host_allowed("localhost", []) and hosts.host_allowed("nas.test", [])


def test_copied_code_must_name_its_source_and_license(tmp_path):
    r = repo(tmp_path, {
        "src/a.py": "# Adapted from some blog post\ndef f(): pass\n",
        "src/b.py": "# Ported from https://github.com/x/y (MIT license)\ndef g(): pass\n",
        "src/c.py": '"""Copied from the prompts repository at a pinned version."""\n',
        "src/d.py": 'msg = "copied from the clipboard"\n',
    }, {"own-sources": ["prompts repository"]})
    assert messages(hosts.sources(r)) == ["src/a.py:1: copied code without a link to its source and its license within three lines"]


# --- personal traces ----------------------------------------------------------------------------------------------

def test_home_folders_and_emails_of_real_people_are_found_placeholders_are_not(tmp_path):
    r = repo(tmp_path, {"src/a.py": "\n".join([
        'P = "/Users/janedoe/Sites/smtv"',
        r'W = r"C:\Users\JohnSmith\AppData"',
        r'OK = "/Users/someone/x", "/home/u/x", "~/x", r"C:\Users\someone\x"',
        'MAIL = "jane.doe@gmail.com"',
        'OK2 = "yuriti@users.noreply.github.com", "a@example.com", "x@host.test", "icon@2x.png"',
    ])})
    found = messages(traces.check(r, env=NO_WORDS))
    assert [f.split(":")[1] for f in found] == ["1", "2", "4"]


def test_private_words_come_from_outside_and_ci_never_prints_them(tmp_path):
    words = tmp_path / "words.txt"
    words.write_text("# comment\nJanePrivate\nre:\\bsecret-host-\\d+\\b\n", encoding="utf-8")
    files = {"src/a.py": "# decided by janeprivate\nURL = 'secret-host-12'\nJanePrivateer = 1\n"}
    local = traces.check(repo(tmp_path / "r", files), env={"SMTV_PRIVATE_WORDS_FILE": str(words)})
    assert messages(local) == ["src/a.py:1: private word «JanePrivate»", "src/a.py:2: private word «re:\\bsecret-host-\\d+\\b»"]
    ci = traces.check(repo(tmp_path / "r", files, ci=True), env={"SMTV_PRIVATE_WORDS": "JanePrivate\n"})
    assert messages(ci) == ["src/a.py:1: private word #1 from the list"]
    assert all("JanePrivate" not in m for m in messages(ci))


def test_without_a_list_traces_only_notes_it_unless_ci_requires_it(tmp_path):
    assert traces.check(repo(tmp_path, {"a.py": "x = 1\n"}), env=NO_WORDS).notes
    strict = traces.check(repo(tmp_path, {}, ci=True), env={**NO_WORDS, "SMTV_REQUIRE_PRIVATE_WORDS": "1"})
    assert not strict.ok


def test_commit_authors_must_be_noreply_and_free_of_private_words(tmp_path):
    r = repo(tmp_path, {})
    out = traces.Outcome("traces")
    words = [(1, __import__("re").compile("JanePrivate", 2), "JanePrivate")]
    log = "\n".join([
        "a" * 40 + "\0Yuri\0" + "11354356+yuriti@users.noreply.github.com\0GitHub\0noreply@github.com",
        "b" * 40 + "\0Jane\0jane@gmail.com\0Jane\0jane@gmail.com",
        "c" * 40 + "\0JanePrivate\0" + "9+jp@users.noreply.github.com\0GitHub\0noreply@github.com",
    ])
    traces.authors(r, out, words, log)
    found = messages(out)
    assert len(found) == 3 and all(m.startswith(("commit bbbbbbbbb", "commit ccccccccc")) for m in found)


def test_an_old_account_is_stopped_by_the_private_list_even_with_a_noreply_address(tmp_path):
    # A maintainer's old or private GitHub account has a valid noreply address too: only the private list, checked
    # against the address and not just the name, keeps it out of the history.
    words = [(1, __import__("re").compile(r"(?<![\w])jprivate-old(?![\w])", 2), "jprivate-old")]
    old = "d" * 40 + "\0Yuri\0" + "204+jprivate-old@users.noreply.github.com\0Yuri\0" + "204+jprivate-old@users.noreply.github.com"
    new = "e" * 40 + "\0Yuri\0" + "11354356+yuriti@users.noreply.github.com\0Yuri\0" + "11354356+yuriti@users.noreply.github.com"
    out = traces.Outcome("traces")
    traces.authors(repo(tmp_path, {}), out, words, old + "\n" + new)
    found = messages(out)
    assert len(found) == 2 and all(m.startswith("commit ddddddddd") and "private word" in m for m in found)


def test_diff_mode_reads_only_added_lines_with_their_numbers(tmp_path):
    patch = "\n".join([
        "diff --git a/src/a.py b/src/a.py", "--- a/src/a.py", "+++ b/src/a.py", "@@ -10,3 +10,4 @@",
        " keep = 1", "-old = 'JanePrivate'", "+new = 'JanePrivate'", "+path = '/Users/janedoe/x'", " tail = 2",
    ])
    out = traces.diff(repo(tmp_path, {}, ci=True), patch, env={"SMTV_PRIVATE_WORDS": "JanePrivate"})
    assert messages(out) == ["src/a.py:11: private word #1 from the list",
                             "src/a.py:12: home folder of a real person (/Users/janedoe); use ~ or a placeholder like someone"]
    assert not traces.diff(repo(tmp_path, {}, ci=True), patch, env={}).ok        # no list in CI: fail, never pass quietly


# --- supply chain -------------------------------------------------------------------------------------------------

LOCK = """version = 1
[[package]]
name = "good"
source = { registry = "https://pypi.org/simple" }
sdist = { url = "u", hash = "sha256:aa" }
wheels = [{ url = "w", hash = "sha256:bb" }]
[[package]]
name = "nohash"
source = { registry = "https://pypi.org/simple" }
wheels = [{ url = "w" }]
[[package]]
name = "ours"
source = { editable = "packages/ours" }
"""


def test_a_workflow_github_cannot_read_fails_before_the_push(tmp_path, monkeypatch):
    # zizmor passes over a file it cannot parse, so the YAML is read first: «: » in an unquoted step name broke apps.yml.
    monkeypatch.setattr(supply.shutil, "which", lambda *a, **k: None)
    good = "on: push\njobs:\n  a:\n    runs-on: ubuntu-latest\n    steps:\n      - name: \"one: two\"\n        run: true\n"
    bad = good.replace('"one: two"', "Rosetta (without it: the job stops)")
    found = supply.workflows(repo(tmp_path, {".github/workflows/bad.yml": bad, ".github/workflows/good.yml": good}))
    assert [(f.path, f.line) for f in found.findings] == [(".github/workflows/bad.yml", 6)]
    assert "not valid YAML" in messages(found)[0] and not found.skipped
    assert supply.workflows(repo(tmp_path / "ok", {".github/workflows/good.yml": good})).skipped   # no zizmor here


def test_every_workflow_of_this_repository_is_valid_yaml():
    import yaml
    for path in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        assert isinstance(yaml.safe_load(path.read_text(encoding="utf-8")), dict), path.name


def test_supply_chain_lock_hashes_install_scripts_and_build_hooks(tmp_path):
    r = repo(tmp_path, {
        "uv.lock": LOCK,
        "packages/a/pyproject.toml": '[project]\nname="a"\n[build-system]\nbuild-backend = "setuptools.build_meta"\n',
        "packages/b/pyproject.toml": '[project]\nname="b"\n[build-system]\nbuild-backend = "hatchling.build"\n'
                                     '[tool.hatch.build.targets.wheel.hooks.custom]\n',
        "packages/c/setup.py": "import os\n",
    })
    found = "\n".join(messages(supply.check(r)))
    assert "nohash: a file without a sha256 hash" in found and "good" not in found and "ours" not in found
    assert "build backend 'setuptools.build_meta'" in found and "build hooks" in found and "setup.py" in found
    assert "no lock file" in messages(supply.check(repo(tmp_path / "empty", {"a.py": "x = 1\n"})))[0]


# --- quality ------------------------------------------------------------------------------------------------------

def test_a_repeated_block_is_found_once(tmp_path):
    block = "\n".join(f"    value_{i} = compute({i}) + other_{i}" for i in range(14))
    r = repo(tmp_path, {"src/a.py": "def f():\n" + block + "\n", "src/b.py": "def g():\n" + block + "\n",
                        "src/c.py": "def h():\n    return 1\n"}, {"source-dirs": ["src"]})
    found = messages(quality.duplicates(r, window=12))
    assert len(found) == 1 and "src/b.py" in found[0] and "repeat src/a.py" in found[0]


# --- agents and skills in sync ------------------------------------------------------------------------------------

AGENT = "---\nname: demo-reviewer\ndescription: Reviews \"demo\" things.\ntools: Read\n---\n\nBody line.\n"


def test_codex_agents_are_built_from_the_claude_agents_and_drift_is_found(tmp_path):
    tree(tmp_path, {".claude/agents/demo-reviewer.md": AGENT})
    assert sync_agents.stale(tmp_path) == [".codex/agents/demo-reviewer.toml"]
    assert sync_agents.main([], root=tmp_path) == 0 and sync_agents.stale(tmp_path) == []
    import tomllib
    data = tomllib.loads((tmp_path / ".codex/agents/demo-reviewer.toml").read_text())
    assert data == {"name": "demo-reviewer", "description": 'Reviews "demo" things.', "developer_instructions": "Body line.\n"}
    (tmp_path / ".codex/agents/left-over.toml").write_text("x")
    assert sync_agents.stale(tmp_path) == [".codex/agents/left-over.toml"]


def test_skills_live_in_one_folder_and_claude_code_gets_symlinks(tmp_path):
    tree(tmp_path, {".agents/skills/demo/SKILL.md": "---\nname: demo\ndescription: d\n---\nx\n",
                    ".agents/skills/bad/SKILL.md": "---\nname: other\n---\n"})
    (tmp_path / ".claude/skills").mkdir(parents=True)
    os.symlink("../../.agents/skills/demo", tmp_path / ".claude/skills/demo")
    found = messages(sync.check(Repo(tmp_path, config={})))
    assert found == [".agents/skills/bad/SKILL.md:1: needs name (= folder name) and description",
                     ".claude/skills/bad: must be a symlink to ../../.agents/skills/bad (ln -s ../../.agents/skills/bad bad)"]


@pytest.mark.skipif(sys.platform == "win32" and not all(p.is_symlink() for p in (ROOT / ".claude" / "skills").glob("*")),
                    reason="this checkout has no symlinks (Windows without Developer Mode or git core.symlinks)")
def test_this_repository_keeps_its_agents_and_skills_in_sync():
    assert sync.check(Repo(ROOT, config={})).ok


# --- the agent hook -----------------------------------------------------------------------------------------------

def test_hook_reads_the_command_of_claude_codex_and_cursor():
    assert agent_gate.command_of({"tool_input": {"command": "git push"}}) == "git push"
    assert agent_gate.command_of({"command": "git push", "cwd": "/x"}) == "git push"
    assert agent_gate.command_of({"tool_input": {}}) is None


def git_repo(path: Path) -> Path:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.com"}
    for cmd in (["git", "init", "-q"], ["git", "commit", "-q", "--allow-empty", "-m", "x"]):
        subprocess.run(cmd, cwd=path, check=True, env=env)
    return path


needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")


@needs_git
@pytest.mark.parametrize("command, kind", [
    ("git commit -m x", "commit"), ("cd a && git -C b commit", "commit"), ("git push origin main", "push"),
    ("gh pr create --fill", "push"), ("/usr/bin/git push", "push"), ('"git" push', "push"),
    ("sh -c 'git push'", "push"), ("echo `git push`", "push"), ("git push; echo --help", "push"),
    ("gh -R o/r pr merge 12 --squash", "merge"), ("gh api -X PUT repos/o/r/pulls/9/merge", "merge"),
    ("git status", None), ("git log --oneline", None), ("gh pr view 3", None), ("echo pushing to git", None),
])
def test_hook_knows_which_commands_it_guards(tmp_path, command, kind):
    git_repo(tmp_path)
    seen = []

    def fast(cwd):
        seen.append("fast")
        return False, "red"
    reason = agent_gate.decide(command, tmp_path, run_fast=fast, pr_head=lambda cwd, n: "f" * 40)
    if kind is None:
        assert reason is None and not seen
    elif kind == "commit":
        assert seen and "quick checks failed" in reason
    elif kind == "push":
        assert "has not passed every check" in reason
    else:
        assert "No report for PR 12" in reason or "not through gh api" in reason


@needs_git
def test_hook_judges_every_guarded_command_of_a_chain(tmp_path):
    git_repo(tmp_path)
    green = lambda cwd: (True, "")  # noqa: E731
    assert "has not passed every check" in agent_gate.decide("git commit -m x && git push", tmp_path, run_fast=green)
    both = agent_gate.decide("git push && gh pr merge 9", tmp_path, run_fast=green, pr_head=lambda cwd, n: "f" * 40)
    assert "has not passed every check" in both and "No report for PR 9" in both


def test_merge_number_is_the_pr_being_merged():
    assert agent_gate.merge_number(" --subject 5 9 --squash") == "9"
    assert agent_gate.merge_number(" 9 -t 'fix 5' -b 3") == "9"
    assert agent_gate.merge_number(" --squash") is None
    assert agent_gate.merge_number(" feature-branch") is None
    assert agent_gate.merge_number(" 5 9") is None              # two positionals: refuse to guess


@needs_git
def test_push_needs_the_stamp_check_py_leaves_for_head(tmp_path):
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@example.com"}
    git_repo(tmp_path)
    assert "has not passed every check" in agent_gate.decide("git push", tmp_path)
    check.stamp(Repo(tmp_path, config={}))
    assert agent_gate.decide("git push", tmp_path) is None
    (tmp_path / "f.txt").write_text("x")
    subprocess.run(["git", "add", "f.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "y"], cwd=tmp_path, check=True, env=env)
    assert agent_gate.decide("gh pr create", tmp_path) is not None        # a new commit needs a new stamp


def test_merge_needs_an_approved_report_for_the_current_head(tmp_path):
    head = "a" * 40
    report = tmp_path / ".check" / "pr-7.md"
    decide = lambda: agent_gate.decide("gh pr merge 7 --squash", tmp_path, pr_head=lambda cwd, n: head)  # noqa: E731
    assert "No report" in decide()
    report.parent.mkdir()
    report.write_text(f"Head: {'b' * 40}\nResult: passed\nReview: approve\n")
    assert "another commit" in decide()
    report.write_text(f"Head: {head}\nResult: failed\nReview: approve\n")
    assert "did not pass" in decide()
    report.write_text(f"Head: {head}\nResult: passed\nReview: changes needed\n")
    assert "not approved" in decide()
    report.write_text(f"Head: {head}\nResult: passed\nReview: approve\n")
    assert decide() is None
    assert "Name the pull request" in agent_gate.decide("gh pr merge --squash", tmp_path)
    assert "is for another commit" in agent_gate.decide("gh pr merge --subject 7 8", tmp_path, pr_head=lambda c, n: head) \
        or "No report for PR 8" in agent_gate.decide("gh pr merge --subject 7 8", tmp_path, pr_head=lambda c, n: head)


def test_hook_blocks_with_exit_code_2_and_lets_other_commands_through(tmp_path, monkeypatch):
    script = ROOT / "scripts" / "hooks" / "agent_gate.py"
    run = lambda payload: subprocess.run([sys.executable, str(script)], input=json.dumps(payload), text=True,  # noqa: E731
                                         capture_output=True, timeout=60)
    assert run({"tool_input": {"command": "ls -la"}, "cwd": str(tmp_path)}).returncode == 0
    blocked = run({"command": "gh pr merge 3", "cwd": str(tmp_path)})          # Cursor's shape; not a repository
    assert blocked.returncode == 2 and blocked.stderr


# --- the command --------------------------------------------------------------------------------------------------

def test_check_command_lists_rejects_unknown_and_fails_on_findings(tmp_path, capsys):
    assert check.main(["--list"]) == 0 and "traces" in capsys.readouterr().out
    assert check.main(["nope"]) == 2
    tree(tmp_path, {"src/a.py": 'U = "https://unlisted.example.org/x"\n', "pyproject.toml": "[tool.smtv-check]\nhosts = []\n"})
    assert check.main(["hosts", "--root", str(tmp_path)]) == 1
    assert "unlisted.example.org" in capsys.readouterr().out
    (tmp_path / "pyproject.toml").write_text('[tool.smtv-check]\nhosts = ["unlisted.example.org"]\n')
    assert check.main(["hosts", "--root", str(tmp_path)]) == 0


def test_a_check_that_crashes_fails_instead_of_passing(tmp_path, monkeypatch, capsys):
    def broken(repo):
        raise RuntimeError("boom")
    monkeypatch.setitem(check.CHECKS, "hosts", (broken, True, "x"))
    assert check.main(["hosts", "--root", str(tmp_path)]) == 1
    assert "the check itself failed: RuntimeError: boom" in capsys.readouterr().out


def test_ci_turns_a_skipped_check_into_a_failure(tmp_path, monkeypatch, capsys):
    def skipped(repo):
        o = supply.Outcome("secrets")
        o.skipped = "tool missing"
        return o
    monkeypatch.setitem(check.CHECKS, "secrets", (skipped, True, "x"))
    assert check.main(["secrets", "--root", str(tmp_path)]) == 0
    assert check.main(["secrets", "--root", str(tmp_path), "--ci"]) == 1


def test_traces_skip_keeps_searching_private_words(tmp_path):
    r = repo(tmp_path, {"tests/fake.py": 'P = "/Users/janedoe/x"  # JanePrivate\n'}, {"traces-skip": ["tests/fake.py"]})
    found = messages(traces.check(r, env={"SMTV_PRIVATE_WORDS_FILE": "/nonexistent", "SMTV_PRIVATE_WORDS": "JanePrivate"}))
    assert found == ["tests/fake.py:1: private word «JanePrivate»"]


def test_ci_output_never_contains_a_private_word(tmp_path, capsys):
    patch = "\n".join(["+++ b/docs/zorkin-notes.py", "@@ -0,0 +1,2 @@", "+p = '/Users/zorkin/x'", "+m = 'ivan.zorkin@gmail.com'"])
    (tmp_path / "pr.diff").write_text(patch)
    (tmp_path / "authors.txt").write_text("a" * 40 + "\0Ivan\0ivan.zorkin@mail.ru\0Ivan\0ivan.zorkin@mail.ru\n")
    os.environ["SMTV_PRIVATE_WORDS"] = "Zorkin"
    try:
        code = check.main(["--root", str(tmp_path), "--ci", "--diff", str(tmp_path / "pr.diff"),
                           "--authors", str(tmp_path / "authors.txt")])
    finally:
        del os.environ["SMTV_PRIVATE_WORDS"]
    out = capsys.readouterr().out
    assert code == 1 and "[private #1]" in out and "zorkin" not in out.lower()


def test_unreadable_author_lines_and_missing_authors_fail(tmp_path):
    patch = "+++ b/a.py\n@@ -0,0 +1 @@\n+x = 1\n"
    env = {"SMTV_PRIVATE_WORDS": "Zorkin"}
    assert not traces.diff(repo(tmp_path, {}, ci=True), patch, "garbage without separators\n", env=env).ok
    assert not traces.diff(repo(tmp_path, {}, ci=True), patch, "", env=env).ok


def test_text_in_another_encoding_is_still_searched_and_huge_files_are_named(tmp_path):
    (tmp_path / "a.txt").write_bytes("café /Users/janedoe/x\n".encode("latin-1"))
    (tmp_path / "big.txt").write_text("x" * 2_100_000)
    out = traces.check(Repo(tmp_path, config={}), env=NO_WORDS)
    assert [f.path for f in out.findings] == ["a.txt"] and any("big.txt" in n for n in out.notes)


def test_lock_entries_from_git_or_a_url_and_metadata_hooks_fail(tmp_path):
    lock = 'version = 1\n[[package]]\nname = "fromgit"\nsource = { git = "https://github.com/x/y" }\n'
    meta = '[project]\nname="m"\n[build-system]\nbuild-backend = "hatchling.build"\n[tool.hatch.metadata.hooks.custom]\n'
    found = "\n".join(messages(supply.check(repo(tmp_path, {"uv.lock": lock, "pyproject.toml": meta}))))
    assert "fromgit: comes from git" in found and "build hooks" in found


def test_sync_without_the_prompts_repository_checks_the_bundled_copy(tmp_path):
    """The prompts repository is not published: CI and contributors check that the bundled copy is whole instead."""
    tree(tmp_path / "smtv", {"scripts/sync_prompts.py": "import sys; sys.exit(0 if sys.argv[1:] == ['--intact'] else 3)\n"})
    for ci in (False, True):
        assert sync.check(Repo(tmp_path / "smtv", config={}, ci=ci)).ok
    tree(tmp_path / "bad", {"scripts/sync_prompts.py": "import sys; print('VERSION: missing'); sys.exit(1)\n"})
    found = sync.check(Repo(tmp_path / "bad", config={}, ci=True))
    assert not found.ok and "VERSION: missing" in "\n".join(messages(found))


@needs_git
def test_stamp_only_after_a_full_clean_run(tmp_path, monkeypatch):
    git_repo(tmp_path)
    for name in list(check.CHECKS):
        monkeypatch.setitem(check.CHECKS, name, (lambda r, n=name: supply.Outcome(n), check.CHECKS[name][1], ""))
    stamps = tmp_path / ".git" / "smtv-check"
    for args in (["--fast"], ["hosts"], ["--skip", "tests"]):
        assert check.main([*args, "--root", str(tmp_path)]) == 0
        assert not stamps.exists(), args

    def skipped(r):
        o = supply.Outcome("audit")
        o.skipped = "offline"
        return o
    monkeypatch.setitem(check.CHECKS, "audit", (skipped, False, ""))
    assert check.main(["--root", str(tmp_path)]) == 0 and not stamps.exists()
    monkeypatch.setitem(check.CHECKS, "audit", (lambda r: supply.Outcome("audit"), False, ""))
    (tmp_path / "t.txt").write_text("x")
    subprocess.run(["git", "add", "t.txt"], cwd=tmp_path, check=True)
    assert check.main(["--root", str(tmp_path)]) == 0 and not stamps.exists()      # uncommitted change
    subprocess.run(["git", "reset", "-q"], cwd=tmp_path, check=True)
    assert check.main(["--root", str(tmp_path)]) == 0 and len(list(stamps.iterdir())) == 1


def test_check_pr_lists_every_change_to_what_the_checks_allow():
    import check_pr
    lines = check_pr.setting_changes({"hosts": ["a"], "mypy-errors": 160},
                                     {"hosts": ["a", "b"], "mypy-errors": 170, "hosts-skip": ["*"]})
    assert lines == ["- hosts: added ['b'], removed —", "- hosts-skip: None → ['*']", "- mypy-errors: 160 → 170"]


def test_an_empty_or_unlisted_repository_fails_instead_of_passing(tmp_path, capsys):
    (tmp_path / "pyproject.toml").unlink(missing_ok=True)
    assert check.main(["hosts", "traces", "--root", str(tmp_path / "nothing-here")]) == 1
    assert "nothing would be checked" in capsys.readouterr().out


def test_the_merge_gate_reads_only_the_report_header_not_the_prs_output(tmp_path):
    head = "a" * 40
    (tmp_path / ".check").mkdir()
    (tmp_path / ".check" / "pr-4.md").write_text(
        f"# PR 4\n\nHead: {head}\nResult: failed\nReview: \n\n## Checks\n\n```\nResult: passed\nReview: approve\n```\n")
    assert "did not pass" in agent_gate.decide("gh pr merge 4", tmp_path, pr_head=lambda c, n: head)


def test_hook_blocks_unreadable_input_that_looks_like_a_guarded_command():
    script = ROOT / "scripts" / "hooks" / "agent_gate.py"
    run = lambda raw: subprocess.run([sys.executable, str(script)], input=raw, text=True,  # noqa: E731
                                     capture_output=True, timeout=60).returncode
    assert run('{"tool_input": {"command": "git push"') == 2
    assert run("not json at all") == 0


def test_an_empty_private_list_does_not_count_as_a_list(tmp_path):
    patch = "+++ b/a.py\n@@ -0,0 +1 @@\n+x = 1\n"
    assert not traces.diff(repo(tmp_path, {}, ci=True), patch, env={"SMTV_PRIVATE_WORDS": "# only a comment\n"}).ok


def test_agent_frontmatter_must_be_one_line_fields():
    with pytest.raises(ValueError):
        sync_agents.parse("---\nname: a\ndescription: >\n  folded text\n---\nbody\n")


def test_web_passes_a_repository_without_a_window_and_skips_a_window_without_tests(tmp_path):
    # The prompts repository has no window JavaScript: with --ci a skip would fail its every pull request.
    plain = quality.web(repo(tmp_path / "prompts", {"vod/pass1-prompt.txt": "x"}, ci=True))
    assert plain.ok and not plain.skipped and plain.notes == ["no window JavaScript here"]
    window = quality.web(repo(tmp_path / "smtv", {"packages/smtv/src/smtv/web/app.js": "x"}, ci=True))
    assert window.skipped == "no tests"
