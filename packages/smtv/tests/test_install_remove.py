"""The icon on the first run, and removing SMTV from the computer — without touching this computer."""
from __future__ import annotations

import http.client
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from smtv import cli, serve, uninstall
from smtv_core.settings import Settings


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("SMTV_NO_SHORTCUT", raising=False)
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)


class Out:
    def __init__(self):
        self.out = ""


@pytest.fixture
def made(monkeypatch):
    """A terminal, and a launcher that only records."""
    from smtv import launcher
    calls = []
    out = Out()
    monkeypatch.setattr(cli, "at_terminal", lambda: True)
    monkeypatch.setattr("builtins.print", lambda *a, **k: setattr(out, "out", out.out + " ".join(map(str, a)) + "\n"))
    monkeypatch.setattr(cli.sys, "platform", "darwin")
    monkeypatch.setattr(launcher, "this_system", lambda: "system")
    monkeypatch.setattr(launcher, "installed", lambda s: bool(calls))
    monkeypatch.setattr(launcher, "install", lambda s: calls.append("install") or ["SMTV.app"])
    return calls, out


def mark():
    return (Settings.load().tools.get("smtv") or {}).get("shortcut")


# --- the icon on the first run -----------------------------------------------------------------------------------------

def test_the_first_run_from_a_terminal_makes_the_icon_once(made):
    calls, out = made
    cli.first_run_shortcut("serve")
    assert calls == ["install"] and mark() == "made" and "Made the SMTV icon" in out.out
    cli.first_run_shortcut("doctor")
    assert calls == ["install"]


def test_an_icon_removed_by_hand_is_never_made_again(made, monkeypatch):
    calls, _ = made
    from smtv import launcher
    monkeypatch.setattr(launcher, "remove", lambda s: ["SMTV.app"])
    cli.cmd_shortcut(type("A", (), {"remove": True})(), [], [])
    assert mark() == "removed"
    cli.first_run_shortcut("serve")
    assert calls == []


@pytest.mark.parametrize("command", [None, "shortcut", "uninstall", "app"])
def test_no_icon_for_these_commands(made, command):
    cli.first_run_shortcut(command)
    assert made[0] == [] and mark() is None


def test_no_icon_without_a_terminal_or_when_turned_off(made, monkeypatch):
    monkeypatch.setenv("SMTV_NO_SHORTCUT", "1")
    cli.first_run_shortcut("serve")
    monkeypatch.delenv("SMTV_NO_SHORTCUT")
    monkeypatch.setattr(cli, "at_terminal", lambda: False)        # a job started by the page, a script, a pipe
    cli.first_run_shortcut("vodcut")
    assert made[0] == [] and mark() is None


def test_a_pipe_is_not_a_terminal():
    assert cli.at_terminal() is False                 # under pytest output is captured


def test_no_icon_on_a_linux_server_without_a_desktop(made, monkeypatch):
    monkeypatch.setattr(cli.sys, "platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)
    cli.first_run_shortcut("serve")
    assert made[0] == []


def test_a_failed_icon_never_stops_the_command(made, monkeypatch):
    from smtv import launcher
    monkeypatch.setattr(launcher, "install", lambda s: (_ for _ in ()).throw(OSError("read-only")))
    cli.first_run_shortcut("serve")
    assert mark() == "failed" and "try: smtv shortcut" in made[1].out


# --- removing SMTV -----------------------------------------------------------------------------------------------------

def home_with_data(tmp_path) -> Path:
    home = tmp_path / "home"
    (home / "data" / "vodcut" / "job").mkdir(parents=True)
    (home / "data" / "vodcut" / "job" / "clip01.mp4").write_bytes(b"x" * 1000)
    (home / "settings.json").write_text("{}", encoding="utf-8")
    return home


@pytest.fixture
def no_launcher(monkeypatch):
    from smtv import launcher
    monkeypatch.setattr(launcher, "this_system", lambda: "system")
    monkeypatch.setattr(launcher, "remove", lambda s: ["SMTV.app"])


def test_remove_keeps_the_data_unless_asked(tmp_path, no_launcher, monkeypatch):
    home = home_with_data(tmp_path)
    monkeypatch.setattr(uninstall, "running_as_uv_tool", lambda: True)
    monkeypatch.setattr("smtv.updates.find_uv", lambda: "/usr/local/bin/uv")
    spawned = []
    p = uninstall.run(False, spawn=spawned.append)
    assert (home / "data" / "vodcut" / "job" / "clip01.mp4").exists()
    assert "SMTV.app" in p.done and p.program == "uv"
    (cmd,) = spawned
    script = Path(cmd[-1]).read_text(encoding="utf-8")
    assert "/usr/local/bin/uv" in script and "tool uninstall smtv" in script
    if sys.platform != "win32":
        assert f"while kill -0 {os.getpid()}" in script        # after this process quits, not after a fixed delay
    uninstall.run(True, spawn=spawned.append)
    assert not home.exists()


def test_remove_data_takes_only_what_smtv_made(tmp_path, no_launcher, monkeypatch):
    """A17: SMTV_HOME with the person's own recordings: SMTV's files go, the recordings and the folder stay."""
    home = home_with_data(tmp_path)
    (home / "my-video.mp4").write_bytes(b"mine")
    (home / "logs").mkdir()
    (home / "settings.broken-20261122-101010.json").write_text("{", encoding="utf-8")
    monkeypatch.setattr(uninstall, "running_as_uv_tool", lambda: False)
    p = uninstall.run(True, spawn=lambda a: None)
    assert (home / "my-video.mp4").read_bytes() == b"mine"
    assert sorted(x.name for x in home.iterdir()) == ["my-video.mp4"]
    assert str(home) not in p.done and any("остались ваши файлы" in n for n in p.notes)


def test_remove_data_takes_the_key_kept_outside_the_folder(tmp_path, no_launcher, monkeypatch):
    """Windows keeps secrets.key in %LOCALAPPDATA%\\smtv: it goes too, and that folder when it is empty."""
    home = home_with_data(tmp_path)
    key = tmp_path / "local" / "smtv" / "secrets.key"
    key.parent.mkdir(parents=True)
    key.write_bytes(b"k" * 32)
    monkeypatch.setattr(uninstall.paths, "secrets_key_file", lambda: key)
    monkeypatch.setattr(uninstall, "running_as_uv_tool", lambda: False)
    p = uninstall.run(True, spawn=lambda a: None)
    assert not key.exists() and not key.parent.exists() and str(key) in p.done and not home.exists()


def test_what_could_not_be_removed_is_not_called_removed(tmp_path, no_launcher, monkeypatch):
    """A17: a file Windows keeps open: not in `done`, named in `notes`, removed by the script after SMTV quits."""
    home = home_with_data(tmp_path)
    monkeypatch.setattr(uninstall, "running_as_uv_tool", lambda: False)
    real = uninstall._remove
    monkeypatch.setattr(uninstall, "_remove", lambda path: [f"{path}: PermissionError"] if path.name == "data" else real(path))
    spawned = []
    p = uninstall.run(True, spawn=spawned.append)
    assert str(home / "data") not in p.done and any("PermissionError" in n for n in p.notes)
    assert spawned and str(home / "data") in Path(spawned[0][-1]).read_text(encoding="utf-8")


def test_remove_data_waits_for_another_smtv(tmp_path, no_launcher, monkeypatch):
    """A17: a job in another terminal holds the folder's lock: nothing of the data is removed."""
    from smtv import instance
    home = home_with_data(tmp_path)
    monkeypatch.setattr(uninstall, "running_as_uv_tool", lambda: False)
    other = subprocess.Popen([sys.executable, "-c", "import fcntl,sys,time; f=open(sys.argv[1],'a+b'); "
                              "fcntl.flock(f.fileno(), fcntl.LOCK_EX); print('ok', flush=True); time.sleep(30)",
                              str(instance.lock_file(home))], stdout=subprocess.PIPE, text=True) if sys.platform != "win32" else None
    if other is None:
        pytest.skip("flock from a second process: POSIX")
    try:
        (home / "run").mkdir(exist_ok=True)
        assert other.stdout.readline().strip() == "ok"
        p = uninstall.run(True, spawn=lambda a: None)
        assert (home / "data" / "vodcut" / "job" / "clip01.mp4").exists() and any("SMTV is running" in n for n in p.notes)
    finally:
        other.kill()


def test_the_plan_says_what_and_how_much(tmp_path, monkeypatch):
    home_with_data(tmp_path)
    monkeypatch.setattr(uninstall, "running_as_uv_tool", lambda: False)
    p = uninstall.plan()
    assert p.data_bytes >= 1000 and p.program == "manual" and "pip uninstall smtv" in " ".join(p.program_command)


def test_an_install_without_uv_is_left_alone_and_explained(tmp_path, no_launcher, monkeypatch):
    monkeypatch.setattr(uninstall, "running_as_uv_tool", lambda: False)
    spawned = []
    p = uninstall.run(False, spawn=spawned.append)
    assert spawned == [] and any("pip uninstall" in n for n in p.notes)


def test_never_deletes_a_folder_that_is_not_smtvs(tmp_path, no_launcher, monkeypatch):
    other = tmp_path / "my documents"
    other.mkdir()
    (other / "thesis.docx").write_text("important", encoding="utf-8")
    monkeypatch.setenv("SMTV_HOME", str(other))
    monkeypatch.setattr(uninstall, "running_as_uv_tool", lambda: False)
    p = uninstall.run(True, spawn=lambda a: None)
    assert (other / "thesis.docx").exists() and any("does not look like" in n for n in p.notes)
    assert not uninstall.smtv_folder(Path.home())


def test_windows_removes_after_the_program_quits_with_paths_that_have_spaces(monkeypatch, tmp_path):
    """B23: a script file (no `cmd /c "…"` quoting), waiting for the process id, with a log."""
    monkeypatch.setattr(uninstall.sys, "platform", "win32")
    cmd = uninstall.later_script("C:\\Program Files\\uv\\uv.exe", [Path("C:\\Users\\O'Brien Smith\\smtv\\run")], 4242,
                                 tmp_path / "remove.log")
    assert cmd[:2] == ["cmd.exe", "/c"] and cmd[2].endswith("remove.cmd")
    script = Path(cmd[2]).read_text(encoding="utf-8")
    assert 'tasklist /FI "PID eq 4242"' in script and "timeout" not in script
    assert '"C:\\Program Files\\uv\\uv.exe" tool uninstall smtv' in script
    assert 'rd /s /q "C:\\Users\\O\'Brien Smith\\smtv\\run"' in script and str(tmp_path / "remove.log") in script


def test_cli_refuses_while_smtv_runs_and_asks_before_removing(monkeypatch, capsys, no_launcher):
    monkeypatch.setattr(serve, "probe", lambda port: {"app": "smtv"})
    args = type("A", (), {"data": False, "yes": False})()
    assert cli.cmd_uninstall(args, [], []) == 2 and "Close its window first" in capsys.readouterr().out
    monkeypatch.setattr(serve, "probe", lambda port: None)
    from smtv import instance
    monkeypatch.setattr(instance, "holder", lambda home=None, wait=2.0: {"pid": 1, "kind": "server", "port": 9000})
    assert cli.cmd_uninstall(args, [], []) == 2           # an SMTV on another port, or a job in a terminal
    capsys.readouterr()
    monkeypatch.setattr(instance, "holder", lambda home=None, wait=2.0: None)
    monkeypatch.setattr("builtins.input", lambda prompt: "no")
    ran = []
    monkeypatch.setattr(uninstall, "run", lambda data: ran.append(data))
    assert cli.cmd_uninstall(args, [], []) == 1 and ran == [] and "Nothing removed" in capsys.readouterr().out


# --- the page --------------------------------------------------------------------------------------------------------

@pytest.fixture
def server():
    app = serve.App([], [])
    srv = serve.make_server(app, port=0)
    threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    yield srv.server_address[1], app
    app.stopping.set()
    srv.shutdown()
    srv.server_close()


def req(port, method, path, body=None, token=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    headers = {"Host": f"127.0.0.1:{port}"}
    if token:
        headers["X-SMTV-Token"] = token
    data = json.dumps(body).encode() if body is not None else None
    if data:
        headers["Content-Type"] = "application/json"
    conn.request(method, path, body=data, headers=headers)
    res = conn.getresponse()
    out = res.status, json.loads(res.read() or b"{}")
    conn.close()
    return out


def test_the_page_removes_smtv_only_with_the_token_and_a_confirmation(server, monkeypatch):
    port, app = server
    ran, quit_ = [], threading.Event()
    app.quit = quit_.set
    monkeypatch.setattr(uninstall, "run", lambda data: ran.append(data) or uninstall.Plan("/x", 0, "uv", ["uv"], ["SMTV.app"]))
    assert req(port, "GET", "/api/uninstall")[0] == 403                                  # B15: not from the page
    assert req(port, "GET", "/api/uninstall", token=app.token)[0] == 200
    assert req(port, "POST", "/api/uninstall", {"confirm": "remove"})[0] == 403          # not from the page
    assert req(port, "POST", "/api/uninstall", {}, token=app.token)[0] == 400             # not confirmed
    assert ran == []
    assert headers_of(port, "/api/uninstall", {}, app.token).get("Clear-Site-Data") is None      # refused: forget nothing
    h = headers_of(port, "/api/uninstall", {"confirm": "remove", "data": True}, app.token)
    assert h["status"] == 200 and ran == [True]
    # the browser forgets the site: no saved "not running" page keeps waiting for an SMTV that is gone
    assert h["Clear-Site-Data"] == '"cache", "storage"'
    assert quit_.wait(5)                                                                  # then the server quits


def headers_of(port, path, body, token):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request("POST", path, body=json.dumps(body).encode(),
                 headers={"Host": f"127.0.0.1:{port}", "X-SMTV-Token": token, "Content-Type": "application/json"})
    res = conn.getresponse()
    res.read()
    out = {"status": res.status, **{k: v for k, v in res.getheaders()}}
    conn.close()
    return out


def test_quit_from_the_page(server):
    port, app = server
    assert req(port, "POST", "/api/quit", {})[0] == 403
    assert req(port, "POST", "/api/quit", {}, token=app.token)[0] == 409       # nothing to stop it with
    quit_ = threading.Event()
    app.quit = quit_.set
    assert req(port, "POST", "/api/quit", {}, token=app.token) == (200, {"quitting": True})
    assert quit_.wait(5)
