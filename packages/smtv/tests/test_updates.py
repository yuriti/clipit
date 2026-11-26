"""Stage 8: updates and plugins from the window. The update channel (the signed manifest, stage 27: test_channel.py) is
faked; the updater runs real processes with fake commands, and a fake SMTV that answers /api/hello with the version it
was "installed" with."""
import ast
import json
import os
import socket
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

import pytest

from smtv import hub, updater, updates
from smtv.updates import UpdateError, Updates


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("SMTV_INDEX", raising=False)
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)


# --- versions and the index -------------------------------------------------------------------------------------

def test_version_order():
    order = ["0.0.1", "0.1.0.dev0", "0.1.0.dev1", "0.1.0a1", "0.1.0rc2", "0.1.0", "0.1.0.post1", "0.1.1", "0.2", "1.0.0"]
    keys = [updates.parse(v) for v in order]
    assert all(keys) and keys == sorted(keys)
    assert updates.parse("1.0") == updates.parse("1.0.0")
    for bad in ("", "latest", "1.0; rm -rf /", "1.0 --index-url http://x", "v1.0", "1.0+local", "../1.0"):
        assert updates.parse(bad) is None
    assert updates.newer("0.1.1", "0.1.0") and not updates.newer("0.1.0", "0.1.0") and not updates.newer("evil", "0.1.0")


def test_changelog_from_the_package_description():
    text = textwrap.dedent("""\
        # smtv
        Some text.
        ## Changelog
        ### 0.2.0
        - Updates from the window
          with a second line
        - Plugins install themselves
        ### 0.1.1 (2026-11-20)
        * A fix
        ### not-a-version
        - ignored
        ## License
        - not a change
    """)
    entries = updates.changelog(text)
    assert entries == [{"version": "0.2.0", "notes": ["Updates from the window with a second line", "Plugins install themselves"]},
                       {"version": "0.1.1", "notes": ["A fix"]}]


def test_index_is_pypi_or_a_safe_override(monkeypatch):
    assert updates.index_base() == "https://pypi.org"
    for ok in ("https://mirror.example/", "http://127.0.0.1:9100", "http://localhost:9100"):
        monkeypatch.setenv("SMTV_INDEX", ok)
        assert updates.index_base() == ok.rstrip("/")
    for bad in ("http://evil.example", "ftp://127.0.0.1", "file:///tmp/x", "http://127.0.0.1.evil.example"):
        monkeypatch.setenv("SMTV_INDEX", bad)
        with pytest.raises(ValueError):
            updates.index_base()


# --- commands and plans ---------------------------------------------------------------------------------------------

def test_uv_and_pip_commands(tmp_path):
    v = {"smtv": "0.2.0", "smtv-core": "0.2.0", "vodcut": "0.2.0"}
    [uv] = updates.install_steps("uv", ["vodcut"], v, "https://pypi.org", uv="/bin/uv")
    assert uv == ["/bin/uv", "tool", "install", "--reinstall", "smtv[vodcut]==0.2.0", "--with", "smtv-core==0.2.0",
                  "--with", "vodcut==0.2.0", "--default-index", "https://pypi.org/simple"]
    [pip] = updates.install_steps("pip", ["vodcut"], v, "https://pypi.org", python="/py")
    assert pip[:5] == ["/py", "-m", "pip", "install", "--upgrade"] and "smtv[vodcut]==0.2.0" in pip and pip[-2:] == ["--index-url", "https://pypi.org/simple"]
    # a local index for tests goes first, PyPI stays for everything else
    [uv] = updates.install_steps("uv", [], {"smtv": "0.2.0", "smtv-core": "0.2.0"}, "http://127.0.0.1:9", uv="uv")
    assert "smtv==0.2.0" in uv and uv[-2:] == ["--index", "http://127.0.0.1:9/simple"]
    # names outside the catalog never reach a command; a bad version stops everything
    # the wheels from the signed manifest, checked and saved here, are installed from their files
    files = {"smtv": str(tmp_path / "smtv-0.2.0-py3-none-any.whl"), "smtv-core": str(tmp_path / "smtv_core-0.2.0-py3-none-any.whl")}
    [uv] = updates.install_steps("uv", ["vodcut"], v, "https://pypi.org", uv="uv", files=files, extras_of={"smtv-core": ["keyring"]})
    assert uv[4] == f"smtv[vodcut] @ {(tmp_path / 'smtv-0.2.0-py3-none-any.whl').as_uri()}"
    assert f"smtv-core[keyring] @ {(tmp_path / 'smtv_core-0.2.0-py3-none-any.whl').as_uri()}" in uv and "vodcut==0.2.0" in uv
    [pip] = updates.install_steps("pip", [], {"smtv": "0.2.0", "smtv-core": "0.2.0"}, "https://pypi.org", python="/py", files=files)
    assert f"smtv @ {(tmp_path / 'smtv-0.2.0-py3-none-any.whl').as_uri()}" in pip
    [uv] = updates.install_steps("uv", ["vodcut", "evil"], v, "https://pypi.org", uv="uv")
    assert not any("evil" in a for a in uv)
    with pytest.raises(ValueError):
        updates.install_steps("uv", [], {"smtv": "0.2.0; rm -rf ~"}, "https://pypi.org", uv="uv")
    with pytest.raises(ValueError):
        updates.install_steps("dev", [], v, "https://pypi.org")


def test_plan_remembers_the_versions_before(tmp_path):
    cur = {"smtv": "0.1.0", "smtv-core": "0.1.0", "vodcut": "0.1.0"}
    plan = updates.make_plan("update", "uv", ["vodcut"], cur, {**cur, "smtv": "0.2.0", "smtv-core": "0.2.0", "vodcut": "0.2.0"},
                             ["vodcut"], 8642, uv="uv", relaunch=["smtv", "app"])
    assert "smtv[vodcut]==0.2.0" in plan.steps[0] and "smtv[vodcut]==0.1.0" in plan.rollback[0]
    known = list(updates.CATALOG)
    assert plan.expect == {"version": "0.2.0", "tools": ["vodcut"], "known": known}
    assert plan.previous == {"version": "0.1.0", "tools": ["vodcut"], "known": known}
    assert plan.wait_pid == os.getpid() and plan.relaunch == ["smtv", "app"]
    # pip: a removed tool is uninstalled; rolling back an install uninstalls the new tool
    rm = updates.make_plan("remove", "pip", ["vodcut"], cur, {"smtv": "0.1.0", "smtv-core": "0.1.0"}, [], 8642, python="/py", relaunch=["x"])
    assert rm.steps[-1][-4:] == ["uninstall", "-y", "--disable-pip-version-check", "vodcut"] and rm.expect["tools"] == []
    cur2 = {"smtv": "0.1.0", "smtv-core": "0.1.0"}
    add = updates.make_plan("install", "pip", [], cur2, {**cur2, "vodcut": "0.1.0"}, ["vodcut"], 8642, python="/py", relaunch=["x"])
    assert "smtv[vodcut]==0.1.0" in add.steps[0] and add.rollback[-1][-1] == "vodcut"


# --- Updates: asking, waiting for jobs, starting the updater -----------------------------------------------------------

class Box:
    def __init__(self, tools=("vodcut",), running=0, kind="uv", packages=None):
        self.tools, self.running, self.spawned, self.stopped, self.quits = list(tools), running, [], 0, 0
        self.downloaded, self.opened, self.floors = [], [], []
        self.u = Updates(tools=lambda: self.tools, running=lambda: self.running, stop_jobs=self.stop, port=lambda: 8650,
                         manifest=self.fetch, download=self.download, open_file=self.opened.append, spawn=self.spawn, kind=kind)
        self.u.quit = self.quit
        self.packages = packages or {}

    def fetch(self, floor):
        """The verified manifest (channel.load) for the packages given as {name: {"latest", "changes"}}: smtv, smtv-core
        and the tools come out together under one number (decision 9 of the В2 review)."""
        self.floors.append(floor)
        version = (self.packages.get("smtv") or {}).get("latest") or "0.1.0"
        names = [n for n in ("smtv", "smtv-core", "vodcut") if n in self.packages or "smtv" in self.packages]
        files = [{"package": n, "name": f"{n.replace('-', '_')}-{version}-py3-none-any.whl", "url": f"https://github.com/x/{n}.whl",
                  "size": 1, "sha256": "0" * 64} for n in names]
        return {"version": version, "published": "", "packages": {n: version for n in names},
                "changes": [c for p in self.packages.values() for c in p.get("changes") or []],
                "kinds": {"uv": {"files": files}, "pip": {"files": files},
                          "dmg": {"files": [{"package": None, "name": f"SMTV-{version}.dmg", "url": "https://github.com/x/a.dmg",
                                             "size": 1, "sha256": "0" * 64}]}}}

    def download(self, files, folder):
        self.downloaded.append([f["name"] for f in files])
        return [folder / f["name"] for f in files]

    def spawn(self, plan):
        self.spawned.append(plan)
        return 1

    def stop(self):
        self.stopped += 1
        self.running = 0

    def quit(self):
        self.quits += 1


def versions(monkeypatch, **v):
    names = {"smtv": "0.1.0", "smtv-core": "0.1.0", "vodcut": "0.1.0", **{k.replace("_", "-"): x for k, x in v.items()}}
    monkeypatch.setattr(updates, "version_of", lambda n: names.get(n))


def test_check_finds_an_update_and_the_update_waits_for_jobs(monkeypatch):
    versions(monkeypatch)
    box = Box(running=1, packages={"smtv": {"latest": "0.2.0", "changes": [{"version": "0.2.0", "notes": ["new"]}]},
                                   "smtv-core": {"latest": "0.2.0", "changes": []}, "vodcut": {"latest": "0.2.0", "changes": []}})
    s = box.u.check()
    assert s["available"] == {"version": "0.2.0", "versions": {"smtv": "0.2.0", "smtv-core": "0.2.0", "vodcut": "0.2.0"}}
    assert s["packages"]["smtv"]["changes"][0]["notes"] == ["new"]
    assert json.loads(updates.cache_file().read_text(encoding="utf-8"))["packages"]["smtv"]["latest"] == "0.2.0"   # kept for the next start

    s = box.u.ask("update")
    assert s["pending"] == {"action": "update", "tool": None} and box.spawned == []     # a job runs: it waits
    box.u.go()
    assert box.spawned == []
    box.running = 0
    box.u.go()                                                                           # the window's thread, a second later
    assert len(box.spawned) == 1 and box.u.leaving and box.u.pending is None
    plan = box.spawned[0]
    assert plan.expect["version"] == "0.2.0" and plan.expect["tools"] == ["vodcut"] and "smtv[vodcut]==0.1.0" in plan.rollback[0]
    with pytest.raises(UpdateError) as e:                                               # one update at a time
        box.u.ask("update")
    assert e.value.code == "updating"


def test_update_now_stops_the_jobs_first(monkeypatch):
    versions(monkeypatch)
    box = Box(running=2, packages={"smtv": {"latest": "0.2.0", "changes": []}})
    box.u.check()
    box.u.ask("update", now=True)
    assert box.stopped == 1 and len(box.spawned) == 1


def test_waiting_update_can_be_cancelled(monkeypatch):
    versions(monkeypatch)
    box = Box(running=1, packages={"smtv": {"latest": "0.2.0", "changes": []}})
    box.u.check()
    box.u.ask("update")
    box.u.cancel()
    box.running = 0
    box.u.go()
    assert box.spawned == [] and box.u.state()["pending"] is None


def test_nothing_newer_and_dev_installs(monkeypatch):
    versions(monkeypatch)
    box = Box()
    box.u.check()
    with pytest.raises(UpdateError) as e:
        box.u.ask("update")
    assert e.value.code == "up_to_date"
    dev = Box(kind="dev")
    with pytest.raises(UpdateError) as e:
        dev.u.ask("install", "vodcut")
    assert e.value.code == "cannot_update"


@pytest.mark.parametrize("name", ["evil", "livecut", "mcp", "autopublish", "tiktok-hashtags", "tiktok-music", "smtv", "smtv-core", "../vodcut", "vodcut ", "VODCUT", "", None])
def test_plugin_names_outside_the_catalog_are_refused(monkeypatch, name):
    versions(monkeypatch)
    for kind in ("uv", "dev"):
        box = Box(tools=[], kind=kind)
        for action in ("install", "remove"):
            with pytest.raises(UpdateError) as e:
                box.u.ask(action, name)
            assert e.value.code == "not_in_catalog"
        assert box.spawned == []


def test_no_announced_plugin_can_be_installed(monkeypatch):
    """Every «soon» card, including ones added later, is refused by the updater itself, not only by the page."""
    from smtv.tools import SOON
    versions(monkeypatch)
    box = Box(tools=[], kind="uv")
    for name in SOON:
        with pytest.raises(UpdateError) as e:
            box.u.ask("install", name)
        assert e.value.code == "not_in_catalog", name
    assert box.spawned == []


def test_install_and_remove_a_plugin(monkeypatch):
    versions(monkeypatch, vodcut=None)
    box = Box(tools=[])
    box.u.ask("install", "vodcut")
    [plan] = box.spawned
    assert plan.action == "install" and "smtv[vodcut]==0.1.0" in plan.steps[0] and "vodcut==0.1.0" in plan.steps[0]
    assert (plan.expect["version"], plan.expect["tools"]) == ("0.1.0", ["vodcut"]) and plan.previous["tools"] == []

    versions(monkeypatch)
    box = Box(tools=["vodcut"])
    with pytest.raises(UpdateError) as e:
        box.u.ask("install", "vodcut")
    assert e.value.code == "installed"
    box.u.ask("remove", "vodcut")
    [plan] = box.spawned
    assert plan.steps[0][4] == "smtv==0.1.0" and plan.expect["tools"] == [] and "smtv[vodcut]==0.1.0" in plan.rollback[0]

    box = Box(tools=[])
    with pytest.raises(UpdateError) as e:
        box.u.ask("remove", "vodcut")
    assert e.value.code == "not_installed"


def test_a_failed_spawn_leaves_smtv_as_it_is(monkeypatch):
    versions(monkeypatch)
    box = Box(packages={"smtv": {"latest": "0.2.0", "changes": []}})
    box.u.check()
    box.u.spawn = lambda plan: (_ for _ in ()).throw(OSError("no python"))
    with pytest.raises(UpdateError) as e:
        box.u.ask("update")
    assert e.value.code == "not_started" and not box.u.leaving and "no python" in box.u.state()["error"]


def test_daily_check_can_be_turned_off(monkeypatch):
    versions(monkeypatch)
    from smtv_core.settings import Settings
    box = Box()
    assert box.u.due()
    s = Settings.load()
    s.tools["smtv"] = {"update_check": False}
    s.save()
    assert not box.u.due() and box.u.state()["check"] is False


# --- the updater ------------------------------------------------------------------------------------------------------

def test_updater_uses_only_the_standard_library():
    tree = ast.parse(Path(updater.__file__).read_text(encoding="utf-8"))
    names = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    names |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module and n.level == 0}
    assert names <= set(sys.stdlib_module_names) | {"__future__"}, names - set(sys.stdlib_module_names)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# A fake SMTV: answers /api/hello with the version written in "installed.json" when it started; "broken" ones never answer.
FAKE_SMTV = """
import http.server, json, sys
port, state = int(sys.argv[1]), json.load(open(sys.argv[2]))
if state.get("broken"):
    sys.exit(3)
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"app": "smtv", "version": state["version"], "tools": state["tools"]}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_POST(self):
        self.send_response(200); self.send_header("Content-Length", "2"); self.end_headers(); self.wfile.write(b"{}")
        raise SystemExit
    def log_message(self, *a): pass
srv = http.server.HTTPServer(("127.0.0.1", port), H)
srv.timeout = 1
import time
end = time.time() + 30
while time.time() < end:
    srv.handle_request()
"""

# A fake installer: writes what it "installed" (or fails when asked to install a version listed as bad).
FAKE_INSTALL = """
import json, sys
spec, out, bad = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
version = spec.split("==")[1]
tools = spec.split("[")[1].split("]")[0].split(",") if "[" in spec else []
if version in bad:
    sys.exit(1)
json.dump({"version": version, "tools": tools, "broken": version.endswith("broken")}, open(out, "w"))
"""


def make_updater_plan(tmp_path, port, target, previous, bad="") -> dict:
    (tmp_path / "smtv.py").write_text(FAKE_SMTV, encoding="utf-8")
    (tmp_path / "install.py").write_text(FAKE_INSTALL, encoding="utf-8")
    state = tmp_path / "installed.json"
    state.write_text(json.dumps(previous), encoding="utf-8")
    (tmp_path / "run").mkdir(exist_ok=True)
    (tmp_path / "run" / "session.json").write_text(json.dumps({"token": "t", "pid": 0}), encoding="utf-8")
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    spec = lambda v: f"smtv[{','.join(v['tools'])}]=={v['version']}" if v["tools"] else f"smtv=={v['version']}"
    return {"action": "update", "steps": [[sys.executable, str(tmp_path / "install.py"), spec(target), str(state), bad]],
            "rollback": [[sys.executable, str(tmp_path / "install.py"), spec(previous), str(state), ""]],
            "relaunch": [sys.executable, str(tmp_path / "smtv.py"), str(port), str(state)],
            "expect": {k: target[k] for k in ("version", "tools")}, "previous": {k: previous[k] for k in ("version", "tools")},
            "wait_pid": dead.pid, "port": port, "home": str(tmp_path), "status": str(tmp_path / "status.json"),
            "log": str(tmp_path / "update.log"), "timeout_s": 8}


def run_updater(tmp_path, plan) -> tuple[int, dict]:
    (tmp_path / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    p = subprocess.run([sys.executable, "-I", updater.__file__, str(tmp_path / "plan.json")], capture_output=True, text=True, timeout=120,
                       env={**os.environ, "PATH": os.environ.get("PATH", "")})
    status = json.loads(Path(plan["status"]).read_text(encoding="utf-8"))
    port = plan["port"]
    try:   # the fake SMTV the updater started: ask it to quit
        import http.client
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
        c.request("POST", "/api/quit", body=b"{}")
        c.getresponse().read()
    except OSError:
        pass
    return p.returncode, status


def test_updater_updates_and_starts_smtv_again(tmp_path):
    port = free_port()
    plan = make_updater_plan(tmp_path, port, {"version": "0.2.0", "tools": ["vodcut"]}, {"version": "0.1.0", "tools": ["vodcut"]})
    code, status = run_updater(tmp_path, plan)
    assert code == 0 and status["state"] == "done", Path(plan["log"]).read_text(encoding="utf-8") if Path(plan["log"]).exists() else status
    assert json.loads((tmp_path / "installed.json").read_text(encoding="utf-8"))["version"] == "0.2.0"


def test_updater_rolls_back_when_the_install_fails(tmp_path):
    port = free_port()
    plan = make_updater_plan(tmp_path, port, {"version": "0.2.0", "tools": ["vodcut"]}, {"version": "0.1.0", "tools": ["vodcut"]}, bad="0.2.0")
    code, status = run_updater(tmp_path, plan)
    assert code == 1 and status["state"] == "rolled_back"
    assert json.loads((tmp_path / "installed.json").read_text(encoding="utf-8"))["version"] == "0.1.0"


def test_updater_rolls_back_when_the_new_version_does_not_start(tmp_path):
    port = free_port()
    plan = make_updater_plan(tmp_path, port, {"version": "0.2.0", "tools": ["vodcut"]},
                             {"version": "0.1.0", "tools": ["vodcut"]})
    # the "installed" new version exits at once: no answer on the port
    plan["steps"][0][3:] = [str(tmp_path / "installed.json"), ""]
    install = (tmp_path / "install.py").read_text(encoding="utf-8").replace('"broken": version.endswith("broken")', '"broken": version == "0.2.0"')
    (tmp_path / "install.py").write_text(install, encoding="utf-8")
    plan["timeout_s"] = 60
    t0 = time.monotonic()
    code, status = run_updater(tmp_path, plan)
    assert code == 1 and status["state"] == "rolled_back"
    assert time.monotonic() - t0 < 30            # the dead start is seen at once, not after the whole wait
    assert json.loads((tmp_path / "installed.json").read_text(encoding="utf-8")) == {"version": "0.1.0", "tools": ["vodcut"], "broken": False}


def test_updater_rolls_back_a_plugin_install_that_comes_up_without_it(tmp_path):
    port = free_port()
    plan = make_updater_plan(tmp_path, port, {"version": "0.1.0", "tools": ["vodcut"]}, {"version": "0.1.0", "tools": []})
    plan["action"] = "install"
    plan["steps"][0][2] = "smtv==0.1.0"         # the installer "forgot" the plugin: SMTV answers without it
    code, status = run_updater(tmp_path, plan)
    assert code == 1 and status["state"] == "rolled_back" and status["action"] == "install"


def test_updater_waits_for_smtv_to_quit(monkeypatch):
    alive = iter([True, True, True, False])
    monkeypatch.setattr(updater, "pid_alive", lambda pid: next(alive))
    sleeps = []
    assert updater.wait_gone(123, 60, sleep=sleeps.append) and len(sleeps) == 3
    monkeypatch.setattr(updater, "pid_alive", lambda pid: True)
    assert not updater.wait_gone(123, 0.05, sleep=lambda s: time.sleep(0.01))


def test_updater_fails_loudly_when_even_the_old_version_does_not_start(tmp_path, monkeypatch):
    said = []
    monkeypatch.setattr(updater, "alert", said.append)
    monkeypatch.setattr(updater, "hello", lambda port: None)
    monkeypatch.setattr(updater, "wait_gone", lambda pid, timeout, sleep=None: True)
    monkeypatch.setattr(updater, "wait_hello", lambda port, expect, timeout, sleep=None, proc=None: None)
    plan = {"action": "update", "steps": [["true"]], "rollback": [["true"]], "relaunch": ["true"], "expect": {"version": "2"},
            "previous": {"version": "1"}, "wait_pid": 1, "port": 1, "home": str(tmp_path), "status": str(tmp_path / "s.json"), "log": "update.log"}
    ran = []
    assert updater.update(plan, runner=lambda argv, **k: ran.append(argv) or subprocess.CompletedProcess(argv, 0),
                          popen=lambda argv, **k: ran.append(argv)) == "failed"
    assert said and "update.log" in said[0] and json.loads((tmp_path / "s.json").read_text(encoding="utf-8"))["state"] == "failed"


# --- the window's one stream ----------------------------------------------------------------------------------------

def test_hub_diff():
    a = {"jobs": {"t/1": {"tool": "t", "id": "1", "status": "running"}, "t/2": {"tool": "t", "id": "2"}}, "activity": {"running": 1}, "usage": {}, "update": {}}
    b = {"jobs": {"t/1": {"tool": "t", "id": "1", "status": "done"}, "t/3": {"tool": "t", "id": "3"}}, "activity": {"running": 0}, "usage": {}, "update": {}}
    chunks = b"".join(hub.diff(a, b)).decode()
    assert '"status": "done"' in chunks and '"id": "3"' in chunks and "event: job_gone" in chunks and '"id": "2"' in chunks
    assert "event: activity" in chunks and "event: usage" not in chunks
    assert hub.diff(a, a) == []


def test_hub_stream_sends_a_snapshot_then_changes():
    stopping = threading.Event()
    state = {"jobs": {}, "activity": {"running": 0}, "usage": {}, "update": {}}
    looks = []

    def look():
        looks.append(1)
        return json.loads(json.dumps(state))

    h = hub.Hub(look, stopping, every=0.05)
    out = []
    got = threading.Event()

    def write(b):
        out.append(b)
        if b"event: job\n" in b:
            got.set()

    t = threading.Thread(target=h.stream, args=(write,), daemon=True)
    t.start()
    time.sleep(0.2)
    state["jobs"] = {"t/1": {"tool": "t", "id": "1"}}
    assert got.wait(3)
    stopping.set()
    h.poke()
    t.join(3)
    text = b"".join(out).decode()
    assert text.index("event: snapshot") < text.index("event: job\n")
    assert not t.is_alive() and h.listeners == 0


def test_smtv_starts_again_with_the_same_command_and_options():
    assert updates.same_options(["app", "--browser", "--port", "8650"]) == ["app", "--browser", "--port", "8650"]
    assert updates.same_options(["serve", "--no-browser", "--port=9000"]) == ["serve", "--no-browser", "--port", "9000"]
    assert updates.same_options([]) == ["app"]
    assert updates.same_options(["vodcut", "run", "x", "--port", "1; rm"]) == ["app"]


def test_a_new_stream_never_gets_an_old_picture():
    stopping = threading.Event()
    state = {"jobs": {}, "activity": {"running": 0}, "usage": {}, "update": {"checking": True}}
    h = hub.Hub(lambda: json.loads(json.dumps(state)), stopping, every=0.05)
    h.refresh()                                    # looked while a check ran; then nobody listened
    state["update"] = {"checking": False}
    out = []
    t = threading.Thread(target=h.stream, args=(out.append,), daemon=True)
    t.start()
    deadline = time.time() + 3
    while not any(b"snapshot" in b for b in out) and time.time() < deadline:
        time.sleep(0.02)
    stopping.set()
    h.poke()
    t.join(3)
    snap = next(b for b in out if b.startswith(b"event: snapshot"))
    assert b'"checking": false' in snap


def test_a_waiting_update_starts_without_any_window(monkeypatch):
    versions(monkeypatch)
    box = Box(running=1, packages={"smtv": {"latest": "0.2.0", "changes": []}})
    box.u.check()
    box.u.ask("update")
    stopping = threading.Event()
    t = threading.Thread(target=box.u.daily, args=(stopping,), kwargs={"first": 999, "tick": 0.02}, daemon=True)
    t.start()
    time.sleep(0.1)
    assert box.spawned == []
    box.running = 0                                   # the job ended; nobody has the window open
    deadline = time.time() + 3
    while not box.spawned and time.time() < deadline:
        time.sleep(0.02)
    stopping.set()
    t.join(2)
    assert len(box.spawned) == 1


def test_the_daily_check_runs_after_the_start_and_then_once_a_day(monkeypatch):
    versions(monkeypatch)
    box = Box()
    calls = []
    box.u.check = lambda: calls.append(1)
    stopping = threading.Event()
    t = threading.Thread(target=box.u.daily, args=(stopping,), kwargs={"first": 0.05, "tick": 0.01, "every": 0.05}, daemon=True)
    t.start()
    time.sleep(0.3)
    stopping.set()
    t.join(2)
    assert calls                       # due: never checked before
    box.u.cache = {"checked": time.time()}
    calls.clear()
    stopping = threading.Event()
    t = threading.Thread(target=box.u.daily, args=(stopping,), kwargs={"first": 0.0, "tick": 0.01, "every": 0.01}, daemon=True)
    t.start()
    time.sleep(0.2)
    stopping.set()
    t.join(2)
    assert calls == []                 # checked less than a day ago


# --- after the independent review ----------------------------------------------------------------------------------

def test_start_updater_runs_outside_the_environment_and_waits_for_it(monkeypatch, tmp_path):
    cur = {"smtv": "0.1.0", "smtv-core": "0.1.0"}
    plan = updates.make_plan("update", "uv", [], cur, {"smtv": "0.2.0", "smtv-core": "0.2.0"}, [], 8650, uv="uv", relaunch=["x"])
    seen = {}

    class FakePopen:
        pid = 4242

        def __init__(self, argv, env=None, **kw):
            seen.update(argv=argv, env=env, kw=kw)
            Path(plan.status).write_text(json.dumps({"state": "waiting", "pid": 4243, "started": time.time()}), encoding="utf-8")

        def poll(self):
            return None

    monkeypatch.setattr(updates.subprocess, "Popen", FakePopen)
    monkeypatch.setenv("PYTHONPATH", "/somewhere")
    assert updates.start_updater(plan) == 4242
    run = Path(plan.home) / "run"
    assert seen["argv"] == [updates.base_python(), "-I", "-X", "utf8", str(run / "updater.py"), str(run / "update-plan.json")]
    assert not any(k.startswith("PYTHON") for k in seen["env"])
    if sys.platform == "win32":     # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP: outlives SMTV, no console window
        assert seen["kw"].get("creationflags", 0) & 0x00000008 and seen["kw"]["creationflags"] & 0x00000200
    else:
        assert seen["kw"].get("start_new_session") is True
    assert json.loads((run / "update-plan.json").read_text(encoding="utf-8")) == plan.as_dict()
    assert (run / "updater.py").read_text(encoding="utf-8") == Path(updater.__file__).read_text(encoding="utf-8")


def test_smtv_does_not_quit_when_the_updater_never_starts(monkeypatch):
    cur = {"smtv": "0.1.0", "smtv-core": "0.1.0"}
    plan = updates.make_plan("update", "uv", [], cur, {"smtv": "0.2.0", "smtv-core": "0.2.0"}, [], 8650, uv="uv", relaunch=["x"])

    class Dead:
        pid = 1

        def __init__(self, *a, **k):
            pass

        def poll(self):
            return 1

    monkeypatch.setattr(updates.subprocess, "Popen", Dead)
    with pytest.raises(OSError):
        updates.start_updater(plan, confirm_s=1)
    # and through Updates: no quit, not «leaving», the error is shown
    versions(monkeypatch)
    box = Box(packages={"smtv": {"latest": "0.2.0", "changes": []}})
    box.u.spawn = lambda p: updates.start_updater(p, confirm_s=0.5)
    box.u.check()
    with pytest.raises(UpdateError):
        box.u.ask("update")
    time.sleep(1.2)
    assert box.quits == 0 and not box.u.leaving and box.u.state()["error"]


def test_a_plan_from_make_plan_is_what_the_updater_reads(tmp_path, monkeypatch):
    cur = {"smtv": "0.1.0", "smtv-core": "0.1.0", "vodcut": "0.1.0"}
    plan = updates.make_plan("update", "uv", ["vodcut"], cur, {**cur, "smtv": "0.2.0"}, ["vodcut"], 8650, uv="uv", relaunch=["smtv", "app"])
    d = json.loads(json.dumps(plan.as_dict()))
    monkeypatch.setattr(updater, "wait_gone", lambda pid, timeout, sleep=None: True)
    monkeypatch.setattr(updater, "wait_hello", lambda port, expect, timeout, sleep=None, proc=None: expect)
    ran = []
    Path(d["status"]).parent.mkdir(parents=True, exist_ok=True)
    assert updater.update(d, runner=lambda argv, **k: ran.append(argv) or subprocess.CompletedProcess(argv, 0),
                          popen=lambda argv, **k: ran.append(argv)) == "done"
    assert ran[0] == plan.steps[0] and ran[1] == ["smtv", "app"]


def test_nothing_is_installed_while_the_old_smtv_still_runs(tmp_path, monkeypatch):
    gone = iter([False, True])
    monkeypatch.setattr(updater, "wait_gone", lambda pid, timeout, sleep=None: next(gone))
    monkeypatch.setattr(updater, "hello", lambda port: None)
    ran = []
    plan = {"action": "update", "steps": [["install"]], "rollback": [["back"]], "relaunch": ["smtv", "app"], "expect": {"version": "2"},
            "previous": {"version": "1"}, "wait_pid": 1, "port": 1, "home": str(tmp_path), "status": str(tmp_path / "s.json"), "log": "l"}
    assert updater.update(plan, runner=lambda argv, **k: ran.append(argv), popen=lambda argv, **k: ran.append(argv)) == "failed"
    assert ran == [["smtv", "app"]]          # no install; started again, unchanged, once it was gone
    assert json.loads((tmp_path / "s.json").read_text(encoding="utf-8"))["why"] == "SMTV did not quit"


def test_a_crash_inside_the_updater_still_brings_smtv_back(tmp_path, monkeypatch):
    plan = {"action": "update", "steps": [], "rollback": [], "relaunch": ["smtv", "app"], "expect": {}, "previous": {},
            "wait_pid": 1, "port": 1, "home": str(tmp_path), "status": str(tmp_path / "s.json"), "log": "l"}
    (tmp_path / "p.json").write_text(json.dumps(plan), encoding="utf-8")
    monkeypatch.setattr(updater, "update", lambda p: 1 / 0)
    monkeypatch.setattr(updater, "hello", lambda port: None)
    started, said = [], []
    monkeypatch.setattr(updater, "launch", lambda argv, popen=None: started.append(argv))
    monkeypatch.setattr(updater, "alert", said.append)
    assert updater.main([str(tmp_path / "p.json")]) == 1
    assert started == [["smtv", "app"]] and said and json.loads((tmp_path / "s.json").read_text(encoding="utf-8"))["state"] == "failed"


def test_a_failed_check_keeps_the_known_update_and_never_sticks(monkeypatch):
    versions(monkeypatch)
    box = Box(packages={"smtv": {"latest": "0.2.0", "changes": []}})
    box.u.check()
    checked = box.u.cache["checked"]

    def broken(floor):
        raise updates.channel.ChannelError("unreachable", "github.com: RemoteDisconnected: hung up")

    box.u.manifest = broken
    s = box.u.check()
    assert s["available"]["version"] == "0.2.0" and "unreachable" in s["error"] and not s["checking"]
    assert box.u.cache["checked"] == checked      # tried again within the hour, not a day later


def test_a_half_finished_update_shows_as_failed_and_does_not_block(monkeypatch):
    versions(monkeypatch)
    updates._write_json(updates.status_file(), {"state": "installing", "action": "update", "pid": 999999, "started": 1.0,
                                                "from": {"version": "0.1.0"}, "to": {"version": "0.2.0"}})
    box = Box(packages={"smtv": {"latest": "0.2.0", "changes": []}})
    box.u.check()
    assert box.u.state()["last"]["state"] == "failed"
    box.u.ask("update")
    assert len(box.spawned) == 1


def test_the_last_result_is_shown_until_seen(monkeypatch):
    versions(monkeypatch)
    updates._write_json(updates.status_file(), {"state": "rolled_back", "action": "update", "from": {"version": "0.1.0"},
                                                "to": {"version": "0.2.0"}, "log": "x"})
    box = Box()
    assert box.u.state()["last"]["state"] == "rolled_back" and not box.u.state()["last"]["seen"]
    assert box.u.seen()["last"]["seen"] is True


def test_editable_install_is_never_updated_from_the_window(monkeypatch):
    class Dist:
        def __init__(self, direct):
            self.direct = direct

        def read_text(self, name):
            return self.direct

    monkeypatch.setattr(updates.metadata, "distribution", lambda n: Dist('{"url": "file:///x", "dir_info": {"editable": true}}'))
    assert updates.install_kind() == "dev"
    monkeypatch.setattr(updates.metadata, "distribution", lambda n: Dist(None))
    monkeypatch.setattr(updates.os.path, "exists", lambda p: p.endswith("uv-receipt.toml"))
    monkeypatch.setattr(updates, "find_uv", lambda: None)
    assert updates.install_kind() == "none"
    monkeypatch.setattr(updates, "find_uv", lambda: "/bin/uv")
    assert updates.install_kind() == "uv"


def test_two_clicks_at_once_start_one_updater(monkeypatch):
    versions(monkeypatch)
    box = Box(packages={"smtv": {"latest": "0.2.0", "changes": []}})
    box.u.check()
    results = []

    def click():
        try:
            box.u.ask("update")
            results.append("ok")
        except UpdateError as e:
            results.append(e.code)

    ts = [threading.Thread(target=click) for _ in range(5)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert len(box.spawned) == 1 and results.count("ok") >= 1


# --- В3: what the review of 22.11 found -------------------------------------------------------------------------------

RECEIPT = '''[tool]
requirements = [
    { name = "smtv", extras = ["vodcut"] },
    { name = "smtv-core", extras = ["keyring"] },
    { name = "yt-dlp" },
    { name = "pywebview", extras = ["qt"], specifier = ">=5" },
    { name = "myplugin", directory = "/plugins/myplugin" },
]
entrypoints = [{ name = "smtv", install-path = "/x/bin/smtv" }]
'''


def test_an_update_keeps_what_was_added_with_uv_with(tmp_path, monkeypatch):
    """A14: `uv tool install --reinstall` keeps only what its command names: yt-dlp, pywebview[qt], smtv-core[keyring]
    and a plugin go into the new command and into the rollback."""
    (tmp_path / "uv-receipt.toml").write_text(RECEIPT, encoding="utf-8")
    monkeypatch.setattr(updates.sys, "prefix", str(tmp_path))
    cur = {"smtv": "0.1.0", "smtv-core": "0.1.0", "vodcut": "0.1.0"}
    plan = updates.make_plan("update", "uv", ["vodcut"], cur, {n: "0.2.0" for n in cur}, ["vodcut"], 8642, uv="uv",
                             relaunch=["smtv", "app"])
    for steps in (plan.steps, plan.rollback, plan.rollback_offline):
        cmd = steps[0]
        withs = [cmd[i + 1] for i, a in enumerate(cmd) if a == "--with"]
        assert "yt-dlp" in withs and "pywebview[qt]>=5" in withs
        assert any(w.startswith("myplugin @ file:") for w in withs)
        assert any(w.startswith("smtv-core[keyring]==") for w in withs)
    assert plan.rollback_offline[0][-1] == "--offline" and "--offline" not in plan.rollback[0]


def test_a_third_party_plugin_does_not_fail_an_update():
    """A15: /api/hello lists every plugin found; only SMTV's own tools are compared."""
    expect = {"version": "0.2.0", "tools": ["vodcut"], "known": ["vodcut"]}
    assert updater.matches({"version": "0.2.0", "tools": ["myplugin", "vodcut"]}, expect)
    assert not updater.matches({"version": "0.2.0", "tools": ["myplugin"]}, expect)
    assert not updater.matches({"version": "0.1.0", "tools": ["vodcut"]}, expect)


def test_a_rollback_that_could_not_run_but_left_the_old_smtv_is_not_failed(tmp_path, monkeypatch):
    """A16: no network — the install and the rollback both fail, the old SMTV still starts: no alarm."""
    said = []
    monkeypatch.setattr(updater, "alert", said.append)
    monkeypatch.setattr(updater, "hello", lambda port: None)
    monkeypatch.setattr(updater, "wait_gone", lambda pid, timeout, sleep=None: True)
    asked = []
    monkeypatch.setattr(updater, "wait_hello", lambda port, expect, timeout, sleep=None, proc=None:
                        asked.append(expect["version"]) or ({"version": "1"} if expect["version"] == "1" else None))
    plan = {"action": "update", "steps": [["uv", "x"]], "rollback": [["uv", "y"]], "rollback_offline": [["uv", "y", "--offline"]],
            "relaunch": ["true"], "expect": {"version": "2"}, "previous": {"version": "1"}, "wait_pid": 1, "port": 1,
            "home": str(tmp_path), "status": str(tmp_path / "s.json"), "log": "update.log"}
    ran = []
    state = updater.update(plan, runner=lambda argv, **k: ran.append(argv) or subprocess.CompletedProcess(argv, 1),
                           popen=lambda argv, **k: None)
    assert state == "rolled_back" and not said and asked == ["1"]
    assert ran == [["uv", "x"], ["uv", "y", "--offline"], ["uv", "y"]]    # the offline rollback is tried first
    assert "previous version stayed" in json.loads((tmp_path / "s.json").read_text(encoding="utf-8"))["why"]


def test_an_update_needs_every_package_at_the_same_new_number(monkeypatch):
    """B21: smtv, smtv-core and vodcut come out together; a manifest without one of the installed ones holds it back."""
    versions(monkeypatch)
    box = Box(packages={"smtv": {"latest": "0.2.0", "changes": []}})
    box.fetch = lambda floor: {**Box.fetch(box, floor), "packages": {"smtv": "0.2.0", "smtv-core": "0.2.0"}}
    box.u.manifest = box.fetch
    box.u.check()
    assert box.u.available() is None
    box.u.manifest = lambda floor: Box.fetch(box, floor)
    box.u.check()
    assert box.u.available() == {"version": "0.2.0", "versions": {"smtv": "0.2.0", "smtv-core": "0.2.0", "vodcut": "0.2.0"}}


def test_the_updates_thread_lives_through_a_broken_count_of_jobs(monkeypatch):
    """C11: an error in the loop is kept as the window's error; the thread goes on."""
    versions(monkeypatch)
    box = Box()
    calls = []

    def running():
        calls.append(1)
        raise RuntimeError("journal gone")
    box.u.running = running
    box.u.pending = {"action": "update", "tool": None}
    stop = threading.Event()
    t = threading.Thread(target=box.u.daily, args=(stop,), kwargs={"first": 0, "tick": 0.01}, daemon=True)
    t.start()
    time.sleep(0.2)
    stop.set()
    t.join(2)
    assert len(calls) > 1 and "journal gone" in box.u.error


def test_the_update_log_is_trimmed(tmp_path):
    """C22: update.log keeps only its last part."""
    log = tmp_path / "update.log"
    log.write_bytes(b"old line\n" * 300_000)
    updates.trim_log(log, limit=1000, keep=100)
    assert 0 < log.stat().st_size <= 100 and log.read_bytes().startswith(b"old line")
