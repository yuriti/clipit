
import pytest

from smtv import cli, tools
from smtv_core.checks import OK, Check
from smtv_core.tool import Tool


class FakeEntryPoint:
    def __init__(self, name, obj=None, error=None):
        self.name, self.value, self._obj, self._error = name, f"fake:{name}", obj, error

    def load(self):
        if self._error:
            raise self._error
        return self._obj


def make_tool(name="demo"):
    def add_commands(parser):
        sub = parser.add_subparsers(dest="demo_command")
        hello = sub.add_parser("hello")
        hello.set_defaults(func=lambda args, t, b: 7)

    return Tool(name=name, summary="a demo tool", version="1.0", add_commands=add_commands,
                checks=lambda s, v=None: [Check(f"{name}: thing", OK, "fine")])


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)


def test_discover_keeps_good_tools_and_reports_broken_ones(monkeypatch):
    eps = [FakeEntryPoint("demo", make_tool()), FakeEntryPoint("bad", error=ImportError("no module x")),
           FakeEntryPoint("wrong", obj=object())]
    monkeypatch.setattr(tools, "entry_points", lambda group: eps)
    found, broken = tools.discover()
    assert [t.name for t in found] == ["demo"]
    assert {b.name for b in broken} == {"bad", "wrong"}


def test_tool_commands_are_mounted_under_smtv(monkeypatch):
    monkeypatch.setattr(tools, "entry_points", lambda group: [FakeEntryPoint("demo", make_tool())])
    monkeypatch.setattr(cli, "discover", tools.discover)
    assert cli.main(["demo", "hello"]) == 7


def _versions(monkeypatch, kind, uv="/bin/uv"):
    from smtv import updates
    monkeypatch.setattr(updates, "install_kind", lambda: kind)
    monkeypatch.setattr(updates, "find_uv", lambda: uv)
    monkeypatch.setattr(updates, "version_of", lambda n: {"smtv": "0.3.0", "smtv-core": "0.3.0", "vodcut": "0.3.0"}.get(n))
    monkeypatch.setattr(updates, "carried", lambda prefix=None: (["yt-dlp"], {}))


def test_add_installs_with_the_window_s_plan(monkeypatch, capsys):
    """B22: `smtv add` makes the same pinned plan as the window, and keeps what was added with --with."""
    monkeypatch.setattr(cli, "discover", lambda: ([], []))
    _versions(monkeypatch, "uv")
    assert cli.main(["add", "vodcut", "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "Would run: /bin/uv tool install --reinstall smtv[vodcut]==0.3.0 --with smtv-core==0.3.0 --with vodcut==0.3.0 --with yt-dlp" in out
    assert cli.main(["add", "nonsense"]) == 2


def test_add_of_an_installed_tool_does_nothing(monkeypatch, capsys):
    monkeypatch.setattr(cli, "discover", lambda: ([make_tool("vodcut")], []))
    monkeypatch.setattr(cli.subprocess, "call", lambda argv: pytest.fail("nothing to install"))
    assert cli.main(["add", "vodcut"]) == 0 and "Already installed" in capsys.readouterr().out


def test_add_without_uv_on_path_prints_the_command(monkeypatch, capsys):
    monkeypatch.setattr(cli, "discover", lambda: ([], []))
    _versions(monkeypatch, "uv", uv=None)
    monkeypatch.setattr(cli.subprocess, "call", lambda argv: pytest.fail("must not run without uv"))
    assert cli.main(["add", "vodcut"]) == 2
    assert "uv tool install --reinstall smtv[vodcut]==0.3.0" in capsys.readouterr().out


def test_add_with_pip_pins_every_package(monkeypatch, capsys):
    monkeypatch.setattr(cli, "discover", lambda: ([], []))
    _versions(monkeypatch, "pip")
    ran = []
    monkeypatch.setattr(cli.subprocess, "call", lambda argv: ran.append(argv) or 0)
    assert cli.main(["add", "vodcut"]) == 0
    assert ran and ran[0][1:4] == ["-m", "pip", "install"] and "smtv[vodcut]==0.3.0" in ran[0] and "vodcut==0.3.0" in ran[0]


def test_add_from_source_says_where_to_add(monkeypatch, capsys):
    monkeypatch.setattr(cli, "discover", lambda: ([], []))
    _versions(monkeypatch, "dev")
    assert cli.main(["add", "vodcut"]) == 2


def test_doctor_fails_until_a_model_is_set(monkeypatch, capsys):
    monkeypatch.setattr(cli, "discover", lambda: ([make_tool()], []))
    monkeypatch.setattr(cli.core, "core_checks", lambda s, v=None: [Check("Model", "fail", "no model set up", "smtv model set …")])
    assert cli.main(["doctor"]) == 1
    out = capsys.readouterr().out
    assert "demo: thing" in out and "fix: smtv model set" in out
    monkeypatch.setattr(cli.core, "core_checks", lambda s, v=None: [Check("Model", OK, "set")])
    assert cli.main(["doctor"]) == 0


def test_doctor_prints_the_recipe_and_says_when_it_needs_an_administrator(monkeypatch, capsys):
    from smtv_core.checks import Recipe
    monkeypatch.setattr(cli, "discover", lambda: ([], []))
    monkeypatch.setattr(cli.core, "core_checks", lambda s, v=None: [
        Check("ffmpeg", "fail", "not found", "brew install ffmpeg-full", id="ffmpeg", recipe=Recipe("ffmpeg", ["brew", "install", "ffmpeg-full"])),
        Check("Thing", "fail", "x", id="t", recipe=Recipe("t", ["sudo", "apt-get", "install", "-y", "ffmpeg"], admin=True))])
    assert cli.main(["doctor"]) == 1
    out = capsys.readouterr().out
    assert "fix: brew install ffmpeg-full\n" in out and "fix: sudo apt-get install -y ffmpeg   (administrator rights" in out


def test_speech_download_from_the_command_line(monkeypatch, capsys):
    from smtv_core.asr import catalog
    assert cli.main(["speech", "download", "groq"]) == 2                      # a cloud model is not downloaded
    monkeypatch.setattr(catalog, "is_installed", lambda m, d=None: True)
    assert cli.main(["speech", "download", "gigaam"]) == 0 and "already" in capsys.readouterr().out
    state = {"done": False}
    monkeypatch.setattr(catalog, "is_installed", lambda m, d=None: state["done"])

    def load_watched(engine, progress):
        for mb in (0, 400, 852):
            progress(mb, 852)
        state["done"] = True

    monkeypatch.setattr("smtv_core.asr.engines.load_watched", load_watched)
    assert cli.main(["speech", "download", "gigaam"]) == 0
    out = capsys.readouterr().out
    assert "852 of 852 MB" in out and "Done" in out
    state["done"] = False
    monkeypatch.setattr("smtv_core.asr.engines.load_watched", lambda engine, progress: None)    # ended but not complete
    assert cli.main(["speech", "download", "gigaam"]) == 1


def test_model_set_and_key(monkeypatch, capsys):
    from smtv_core.settings import Settings, get_secret
    assert cli.main(["model", "set", "--provider", "openai", "--model", "m1"]) == 0
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: "sk-secret")
    assert cli.main(["model", "key"]) == 0
    out = capsys.readouterr().out
    assert "sk-secret" not in out
    p = Settings.load().providers[0]
    assert (p.id, p.kind, p.default_model) == ("openai", "openai", "m1") and get_secret(p.key_name()) == "sk-secret"
    # a second provider of the same kind, with its own key
    assert cli.main(["model", "set", "--provider", "openai", "--id", "openai-work"]) == 0
    monkeypatch.setattr(cli.getpass, "getpass", lambda prompt: "sk-work")
    assert cli.main(["model", "key", "--id", "openai-work"]) == 0
    s = Settings.load()
    assert [p.id for p in s.providers] == ["openai", "openai-work"]
    assert get_secret(s.provider("openai-work").key_name()) == "sk-work" and get_secret(s.provider("openai").key_name()) == "sk-secret"
    assert cli.main(["model", "show"]) == 0 and "sk-" not in capsys.readouterr().out


def test_progress_reaches_a_file_before_the_run_ends(tmp_path):
    """A long run with its output in a file (nohup, a scheduled task) must show progress lines as they happen."""
    import subprocess
    import sys
    script = ("import sys, time\n"
              "from smtv import cli\n"
              "cli._line_buffered()\n"
              "print('step 1', flush=False)\n"
              "time.sleep(30)\n")
    log = tmp_path / "run.log"
    with log.open("w") as out:
        proc = subprocess.Popen([sys.executable, "-c", script], stdout=out, stderr=subprocess.STDOUT)
        try:
            import time
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and "step 1" not in log.read_text(encoding="utf-8"):
                time.sleep(0.1)
            assert "step 1" in log.read_text(encoding="utf-8")
        finally:
            proc.kill()
            proc.wait()
