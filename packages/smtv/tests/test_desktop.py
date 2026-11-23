"""`smtv app`: SMTV's own window and the process around it — with a fake window, no real one."""
from __future__ import annotations

import json
import os
import stat
import threading
import time

import pytest

from smtv import desktop, i18n, serve, window


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(desktop.i18n, "system", lambda: "en")


def free_port() -> int:
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class FakeWindow:
    """Stands for SMTV's window: `run` blocks until it is closed, like pywebview's loop."""
    instances: list["FakeWindow"] = []

    def __init__(self, app, url, lang, can_open=True):
        self.app, self.url, self.lang, self.can_open = app, url, lang, can_open
        self.closed, self.shown = threading.Event(), 0
        FakeWindow.instances.append(self)

    def run(self):
        if not self.can_open:
            return False
        self.closed.wait(10)
        return True

    def show(self):
        self.shown += 1

    def close(self):
        self.closed.set()


def start_app(port, **kw):
    result = {}
    t = threading.Thread(target=lambda: result.setdefault("code", desktop.run_app([], [], port=port, log=False, **kw)), daemon=True)
    t.start()
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and not serve.probe(port, timeout=0.3):
        time.sleep(0.05)
    return t, result


def test_the_process_lives_as_long_as_its_window():
    FakeWindow.instances.clear()
    port = free_port()
    t, result = start_app(port, window_factory=FakeWindow)
    assert serve.probe(port)["app"] == "smtv"
    win = FakeWindow.instances[-1]
    assert win.url == f"http://127.0.0.1:{port}/?launch={serve.launch_key()}"     # decision 7: the key opens the page
    win.close()                                              # the person closed the window
    t.join(5)
    assert result["code"] == 0 and serve.probe(port, timeout=0.3) is None
    assert not desktop.session_file().exists()


def test_a_second_start_brings_the_window_forward_instead_of_a_second_smtv():
    FakeWindow.instances.clear()
    port = free_port()
    t, _ = start_app(port, window_factory=FakeWindow)
    first = FakeWindow.instances[-1]
    opened = []
    assert desktop.run_app([], [], port=port, log=False, window_factory=FakeWindow, opener=opened.append) == 0
    assert first.shown == 1 and opened == [] and len(FakeWindow.instances) == 1
    first.close()
    t.join(5)


def test_the_session_file_is_private_and_carries_the_token(tmp_path):
    desktop.write_session(8642, "secret-token")
    path = desktop.session_file()
    assert json.loads(path.read_text(encoding="utf-8"))["token"] == "secret-token"
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600          # only this user can read it
    desktop.remove_session("another token")                         # someone else's session is left alone
    assert path.exists()
    desktop.remove_session("secret-token")
    assert not path.exists()


def test_quit_from_the_page_closes_the_window():
    FakeWindow.instances.clear()
    port = free_port()
    t, result = start_app(port, window_factory=FakeWindow)
    session = json.loads(desktop.session_file().read_text(encoding="utf-8"))
    import http.client
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("POST", "/api/quit", body=b"{}", headers={"Host": f"127.0.0.1:{port}", "X-SMTV-Token": session["token"],
                                                            "Content-Type": "application/json"})
    assert conn.getresponse().status == 200
    t.join(5)
    assert FakeWindow.instances[-1].closed.is_set() and result["code"] == 0


def test_without_a_native_window_the_page_opens_in_the_browser(monkeypatch):
    port = free_port()
    opened = []
    monkeypatch.setattr(desktop, "IDLE_MINUTES", 0.0005)              # stops by itself when nobody looks
    t, result = start_app(port, window_factory=lambda *a: FakeWindow(*a, can_open=False), opener=opened.append)
    t.join(10)
    assert opened == [serve.launch_url(port)] and result["code"] == 0


def test_a_port_taken_by_another_program_is_shown_in_a_dialog(monkeypatch):
    import socket
    other = socket.socket()
    other.bind(("127.0.0.1", 0))
    other.listen()
    said = []
    monkeypatch.setattr(desktop, "notify_error", said.append)
    try:
        assert desktop.run_app([], [], port=other.getsockname()[1], log=False, window_factory=FakeWindow) == 2
    finally:
        other.close()
    assert len(said) == 1 and "taken by another program" in said[0]


def test_closing_the_window_asks_only_while_jobs_run():
    asked = []

    def ask(n):
        asked.append(n)
        return window.BACKGROUND_CHOICE

    assert window.closing_choice(0, ask) == window.STOP_CHOICE and asked == []      # nothing runs: just quit
    assert window.closing_choice(2, ask) == window.BACKGROUND_CHOICE and asked == [2]


def test_closing_with_jobs_keeps_them_running_in_the_background():
    class App:
        stopping = threading.Event()

        def __init__(self, running):
            self.running = running

        def activity(self):
            return {"running": self.running}

    minimized = []
    w = window.Window(App(1), "http://127.0.0.1:8642/", "en")
    w.window = type("W", (), {"minimize": lambda self: minimized.append(1),
                              "native": type("N", (), {"miniaturize_": lambda self, x: minimized.append(1)})()})()
    w.ask = lambda n: window.BACKGROUND_CHOICE
    assert w.on_closing() is False                                   # the window stays (in the Dock or taskbar)
    time.sleep(0.2)
    assert minimized
    w.ask = lambda n: window.CANCEL_CHOICE
    assert w.on_closing() is False
    w.ask = lambda n: window.STOP_CHOICE
    assert w.on_closing() is True                                    # closes: the process stops its jobs and quits
    w.app = App(0)
    assert w.on_closing() is True


def test_the_page_knows_which_window_it_is_in():
    assert window.shell() in {"mac", "win", "linux"}


def test_output_goes_to_the_log_file(monkeypatch):
    import sys
    monkeypatch.setattr(sys, "stdout", sys.stdout)
    monkeypatch.setattr(sys, "stderr", sys.stderr)
    desktop._log_to_file()
    print("hello log")
    sys.stdout.flush()
    assert "hello log" in desktop.log_file().read_text(encoding="utf-8")


def test_ui_language_from_the_environment(monkeypatch):
    monkeypatch.undo()
    monkeypatch.setattr(i18n.sys, "platform", "linux")
    for var in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        monkeypatch.delenv(var, raising=False)
    assert i18n.system() == "en"
    monkeypatch.setenv("LANG", "ru_RU.UTF-8")
    assert i18n.system() == "ru"
    monkeypatch.setenv("LANG", "xx_YY.UTF-8")                 # a language SMTV has no words for: English
    assert i18n.system() == "en"
    assert i18n.text("busy_bg", "ru") == "Продолжить в фоне" and i18n.text("busy_stop", "ru") == "Остановить и выйти"


def test_cli_has_the_commands():
    from smtv.cli import build_parser
    p = build_parser([])
    assert p.parse_args(["app", "--browser"]).browser
    assert p.parse_args(["shortcut", "--remove"]).remove
    with pytest.raises(SystemExit):
        p.parse_args(["autostart", "on"])                        # removed: SMTV does not run in the background on its own


# --- stage 7: the window's look -----------------------------------------------------------------------------------

def test_the_page_tells_the_window_its_theme_and_nothing_else_passes_for_one():
    from smtv import window
    assert window.theme_of("theme:dark") == "dark" and window.theme_of("theme:light") == "light" and window.theme_of("theme:auto") == "auto"
    for other in ("theme:", "theme:blue", "drag", "zoom", "theme:dark;rm -rf"):
        assert window.theme_of(other) is None


def test_windows_title_bar_takes_the_page_colours():
    from smtv import window
    assert window.colorref("#15151f") == 0x1F1515            # COLORREF is 0x00bbggrr
    assert window.colorref("#ffffff") == 0xFFFFFF and window.colorref("#000000") == 0
    attributes = dict(window.WIN_TITLE_ATTRIBUTES)
    assert attributes[20] == 1 and attributes[35] == window.colorref(window.CAPTION) and attributes[36] == window.colorref(window.CAPTION_TEXT)


def test_windows_title_bar_follows_the_page_theme():
    """V9: light, dark or the system's app mode, as the Mac window."""
    from smtv import window
    dark = dict(window.win_title_attributes("dark", True))
    light = dict(window.win_title_attributes("light", False))
    assert dark[20] == 1 and dark[35] == window.colorref(window.CAPTION) and dark[36] == window.colorref(window.CAPTION_TEXT)
    assert light[20] == 0 and light[35] == window.colorref(window.CAPTION_LIGHT) and light[36] == window.colorref(window.CAPTION_TEXT_LIGHT)
    assert dict(window.win_title_attributes("auto", True)) == light and dict(window.win_title_attributes("auto", False)) == dark
    # the light caption is the page's light background, its text the page's light text
    from smtv.serve import WEB
    css = (WEB / "app.css").read_text(encoding="utf-8")
    light_block = css.split(':root[data-theme="light"] {', 1)[1].split("}", 1)[0]
    assert f"--bg: {window.CAPTION_LIGHT};" in light_block and f"--text: {window.CAPTION_TEXT_LIGHT};" in light_block


def test_windows_window_paints_its_title_bar_for_each_theme_the_page_says(monkeypatch):
    from smtv import window
    painted = []
    monkeypatch.setattr(window, "_win_title", lambda hwnd, attributes: painted.append((hwnd, dict(attributes)[20])) or True)
    monkeypatch.setattr(window, "win_system_light", lambda: True)
    w = window.Window(app=None, url="http://x", lang="en")
    bridge = window.WinBridge(w.win_theme)
    w.win_theme("light")                                            # before the handle: remembered, nothing painted
    assert painted == [] and w.theme == "light"
    w.hwnd = 77
    assert bridge.message("theme:dark") and bridge.message("theme:light") and bridge.message("theme:auto")
    assert painted == [(77, 1), (77, 0), (77, 0)]                   # auto: the system is light here
    for other in ("focus:1:blur", "theme:blue", None, 5, {"theme": "dark"}):
        assert bridge.message(other) is False
    assert len(painted) == 3
    # only `message` is reachable from the page (pywebview publishes every public attribute)
    assert [k for k in dir(bridge) if not k.startswith("_")] == ["message"]


def test_windows_system_mode_unknown_is_dark(monkeypatch):
    import builtins
    from smtv import window
    real = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", lambda name, *a, **k: (_ for _ in ()).throw(ImportError(name)) if name == "winreg" else real(name, *a, **k))
    assert window.win_system_light() is False


def test_the_page_says_its_theme_to_the_windows_bridge_too():
    from smtv.serve import WEB
    js = (WEB / "app.js").read_text(encoding="utf-8")
    assert "window.pywebview?.api?.message?.(what)" in js
    assert 'addEventListener("pywebviewready", () => windowMessage("theme:" + theme))' in js
    assert 'if (theme === "auto") windowMessage("theme:auto")' in js
    src = (WEB.parent / "window.py").read_text(encoding="utf-8")
    assert 'js_api=WinBridge(self.win_theme) if sys.platform == "win32" else None' in src


def test_the_native_buttons_sit_in_the_middle_of_the_pages_top_bar():
    import re
    from smtv import window
    from smtv.serve import WEB
    css = (WEB / "app.css").read_text(encoding="utf-8")
    assert f"--top-h: {window.HEADER_PX}px" in css                      # the native buttons are centred in this height
    assert re.search(r"\.shell-mac \.top \{ padding-left: 88px;", css)    # and the page leaves room for them
    assert "classList.add('glass')" in window.GLASS_SCRIPT and ".glass" in css   # glass only when the window made it
    # with glass the frame lets it through and the work panel is see-through (a broken selector once made both opaque)
    assert re.search(r"^\.glass \{ --frame-bg: transparent;[^}]*--panel-bg: rgba\(", css, re.M)


def test_a_press_anywhere_in_the_top_bar_moves_the_window_but_not_on_its_buttons():
    from smtv import window
    height = 800.0                                   # window points, the origin at the bottom left (AppKit)
    top = height - window.HEADER_PX
    assert window.in_drag_strip(400, height - 1, height) and window.in_drag_strip(window.BUTTONS_PT, top, height)
    assert not window.in_drag_strip(400, top - 1, height)          # the page below the bar is the page's
    assert not window.in_drag_strip(40, height - 20, height)       # the close, minimise and zoom buttons stay theirs


def test_the_page_tells_the_window_its_focus_and_a_grey_page_in_front_is_marked():
    """Stage 16: the page says what document.hasFocus() gave; the log puts it beside the window's own state."""
    from smtv import window
    assert window.focus_of("focus:1:blur+500") == (True, "blur+500") and window.focus_of("focus:0:start") == (False, "start")
    for other in ("focus:2:x", "focus:1:", "theme:dark", "focus:1:" + "x" * 41, "focus"):
        assert window.focus_of(other) is None
    front = {"app": True, "key": True, "main": True, "visible": True, "mini": False, "responder": "page"}
    assert window.focus_line(False, "focus+500", front).endswith("MISMATCH")          # in front, yet grey: the bug
    assert not window.focus_line(True, "focus", front).endswith("MISMATCH")
    assert not window.focus_line(False, "blur", {**front, "app": False}).endswith("MISMATCH")   # another app in front: grey is right
    assert window.focus_line(False, "focus", {**front, "responder": "NSWindow"}) == \
        "focus: page=0 at=focus | app=1 key=1 main=1 visible=1 mini=0 responder=NSWindow"
