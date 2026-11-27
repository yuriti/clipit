"""`smtv app`: SMTV as a program — what the SMTV icon runs. One process: the local server and SMTV's own window.

- SMTV already runs: its window comes forward and this process quits (a second double-click never starts a second one).
- The port is taken by another program: say so in a system dialog (there is no terminal to print to) and quit.
- Otherwise: start the server and open the window (`window.py`). The process ends with the window. Closing it while
  jobs run asks whether to go on in the background (the window goes to the Dock or taskbar, a notification says when a
  job is done or failed) or to stop them.
- No native window here (Linux without WebKitGTK or Qt): the page opens in the browser instead, and with no open page
  and no running job for a few minutes SMTV stops by itself.

Output goes to `<SMTV home>/logs/app.log`: under pythonw (Windows) or a Finder launch there is nowhere else for it.
"""
from __future__ import annotations

import http.client
import json
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

from smtv_core import paths

from . import i18n, instance, serve
from .activity import IDLE_MINUTES, IdleWatch, finished_text
from .window import Window, mac_badge, mac_notify

WATCH_S = 2.0
LOG_LIMIT = 2_000_000


def log_file() -> Path:
    return paths.home() / "logs" / "app.log"


def _log_to_file() -> None:
    path = log_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size > LOG_LIMIT:
            path.replace(path.with_suffix(".log.1"))
        f = open(path, "a", encoding="utf-8", buffering=1)  # noqa: SIM115 — lives as long as the program
    except OSError:
        f = open(os.devnull, "w")  # noqa: SIM115
    f.write(f"\n--- smtv app {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    sys.stdout = sys.stderr = f


def notify_error(text: str) -> None:
    """A message the person sees without a terminal; best effort, and always in the log."""
    print(f"smtv app: {text}")
    try:
        if sys.__stderr__ is not None and sys.__stderr__.isatty():
            sys.__stderr__.write(text + "\n")
    except (OSError, ValueError):
        pass
    try:
        if sys.platform == "darwin":
            script = ['-e', 'on run argv', '-e', 'display alert "Clip It!" message (item 1 of argv) as critical', '-e', 'end run']
            subprocess.run(["osascript", *script, text], capture_output=True, timeout=300)
        elif sys.platform == "win32":
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, text, "Clip It!", 0x10)  # type: ignore[attr-defined]
        else:
            for argv in (["zenity", "--error", "--title=Clip It!", f"--text={text}"], ["notify-send", "Clip It!", text]):
                try:
                    if subprocess.run(argv, capture_output=True, timeout=300).returncode == 0:
                        break
                except OSError:
                    continue
    except (OSError, subprocess.TimeoutExpired):
        pass


def system_notify(title: str, text: str) -> bool:
    """A system notification (macOS Notification Center, Linux notify-send); False where there is none."""
    try:
        if sys.platform == "darwin":
            script = ['-e', 'on run argv', '-e', 'display notification (item 2 of argv) with title (item 1 of argv)', '-e', 'end run']
            return subprocess.run(["osascript", *script, title, text], capture_output=True, timeout=30).returncode == 0
        if sys.platform.startswith("linux"):
            return subprocess.run(["notify-send", "-a", "Clip It!", title, text], capture_output=True, timeout=30).returncode == 0
        if sys.platform == "win32":
            return subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", WIN_TOAST, title, text],
                                  capture_output=True, timeout=30, creationflags=0x08000000).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        pass
    return False


# A Windows toast without extra modules (Windows 10 and later), shown under PowerShell's name.
WIN_TOAST = (
    "param($t, $m); "
    "[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null; "
    "$x = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
    "$n = $x.GetElementsByTagName('text'); $n.Item(0).AppendChild($x.CreateTextNode($t)) > $null; "
    "$n.Item(1).AppendChild($x.CreateTextNode($m)) > $null; "
    "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('SMTV').Show([Windows.UI.Notifications.ToastNotification]::new($x))"
)


class Watcher:
    """Every few seconds: notifications for jobs that ended, the job count on the Dock icon, and — only when the page is
    in a browser instead of SMTV's window — the idle shutdown. Separate from any window, so it is tested on its own."""

    def __init__(self, app: serve.App, stop, lang: str = "en", idle_s: float | None = None, notify=system_notify,
                 badge=None, clock=time.monotonic):
        self.app, self.stop, self.lang, self.notify, self.badge = app, stop, lang, notify, badge
        self.running: dict[tuple[str, str], dict] = {}
        self.count: int | None = None
        self.idle = IdleWatch(idle_s, busy=self._busy, keep=lambda: False, clock=clock) if idle_s is not None else None
        self._act: dict = {"running": 0}

    def _busy(self) -> bool:
        return bool(self._act.get("running") or self._act.get("viewers"))

    def tick(self) -> bool:
        """One look. True when SMTV should stop now (browser mode, idle)."""
        act = self._act = self.app.activity()
        if self.badge and act["running"] != self.count:
            self.badge(act["running"])
        self.count = act["running"]
        now = {(j["tool"], j["job"]): j for j in act["jobs"]}
        for key in [k for k in self.running if k not in now]:
            self._ended(*key)
        self.running = now
        return bool(self.idle and self.idle.should_stop())

    def _ended(self, tool: str, job: str) -> None:
        try:
            info = self.app.job(tool, job)
        except Exception:  # noqa: BLE001 — the folder went away: nothing to tell
            return
        lang = getattr(self.app, "lang", None) or self.lang          # the language the person chose on the page
        message = finished_text(info["status"], info.get("title") or job, int(info.get("clips") or 0), lang)
        if message:
            print(f"{info['status']}: {tool}/{job}")
            self.notify(*message)

    def run(self) -> None:
        while not self.app.stopping.is_set():
            try:
                if self.tick():
                    print(f"quit: no open page and no job for {self.idle.idle_s / 60:g} min")
                    self.stop()
                    return
            except Exception as e:  # noqa: BLE001 — the watcher must never take the server down
                print(f"watch: {type(e).__name__}: {e}")
            self.app.stopping.wait(WATCH_S)


# --- one SMTV at a time: a second start brings the running one's window forward --------------------------------------

def session_file() -> Path:
    return paths.home() / "run" / "session.json"


def write_session(port: int, token: str) -> None:
    """The running SMTV's port and session token, readable only by this user: a second start uses it to bring the
    window forward (a change like any other, so it needs the token)."""
    path = session_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.chmod(path, 0o600)          # O_CREAT's mode is only for a new file: an old one keeps wider rights (C25)
    except OSError:
        pass
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"port": port, "token": token, "pid": os.getpid()}, f)


def remove_session(token: str) -> None:
    try:
        if json.loads(session_file().read_text(encoding="utf-8")).get("token") == token:
            session_file().unlink()
    except (OSError, ValueError):
        pass


def show_running(port: int) -> bool:
    """Ask the SMTV that already runs on this port to bring its window forward."""
    try:
        session = json.loads(session_file().read_text(encoding="utf-8"))
        if session.get("port") != port:
            return False
        conn = http.client.HTTPConnection(serve.HOST, port, timeout=5)
        conn.request("POST", "/api/window/show", body=b"{}", headers={
            "Host": f"{serve.HOST}:{port}", "X-SMTV-Token": session["token"], "Content-Type": "application/json"})
        ok = conn.getresponse().status == 200
        conn.close()
        return ok
    except (OSError, ValueError, KeyError, http.client.HTTPException):
        return False


def job_holds_text(other: dict, lang: str) -> str:
    """Why SMTV does not open: a job command in a terminal works on the same data folder right now."""
    return i18n.text("app_job_holds", lang, job=other.get("job") or "?", pid=other.get("pid") or "?")


def other_folder_text(port: int, lang: str) -> str:
    return i18n.text("app_other_folder", lang, port=port, next=port + 1)


def claim(port: int, lock: instance.Lock, show=None, opener=webbrowser.open, say=print, lang: str = "en") -> int | None:
    """Takes the data folder's lock for a server. None: taken, go on. A number: the exit code — another SMTV on this
    folder was brought forward (0), or a terminal job holds the folder (2)."""
    try:
        for _ in range(5):
            if lock.take(instance.SERVER, port=port):
                return None
            other = instance.holder()
            if other is not None:
                break
            time.sleep(0.05)               # free a moment ago: someone only looked at it
        else:
            other = {}
    except OSError as e:                   # a folder where the system cannot lock files (some network drives)
        say(i18n.text("app_lock_failed", lang, folder=instance.lock_file(), error=e))
        return 2
    other = other or {}
    if other.get("kind") == instance.SERVER:
        theirs = int(other.get("port") or port)
        print(f"already running on this data folder: {serve.page_url(theirs)} (process {other.get('pid')})")
        if not (show or show_running)(theirs):
            opener(serve.launch_url(theirs))
        return 0
    say(job_holds_text(other, lang))
    return 2


def run_app(tools, broken, port: int = serve.DEFAULT_PORT, browser: bool = False, log: bool = True,
            window_factory=None, opener=webbrowser.open) -> int:
    lang = i18n.system()
    from . import portable
    if not portable.start(lang):           # the Windows ZIP in a folder it cannot write into: said, no window
        return 2
    if log:
        _log_to_file()
    try:
        url = serve.launch_url(port)
    except OSError as e:                   # the data folder cannot be written: said, never a silent exit
        notify_error(i18n.text("app_launch_failed", lang, error=e))
        return 2
    lock = instance.Lock()
    code = claim(port, lock, opener=opener, say=notify_error, lang=lang)
    if code is not None:
        return code
    try:
        return _run_app(tools, broken, port, browser, window_factory, opener, url, lang, lock)
    finally:
        lock.release()


def _run_app(tools, broken, port, browser, window_factory, opener, url, lang, lock) -> int:
    app = serve.App(tools, broken)
    app.instance = lock
    try:
        server = serve.make_server(app, port)
        lock.update(port=app.port)
    except serve.PortBusy as e:
        if e.smtv:
            if show_running(port):     # an SMTV from before the lock, on this same folder (its session is ours)
                return 0
            notify_error(other_folder_text(port, lang))
            return 2
        notify_error(serve.busy_message(e))
        return 2
    print(f"serving {serve.page_url(port)}")      # the launch key never goes to the log
    write_session(port, app.token)
    app.phone.restore()
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.5}, name="smtv-serve", daemon=True)
    thread.start()
    from . import portable
    portable.settle()                       # the Windows ZIP: an update in place is confirmed now that this one runs

    win = None if browser else (window_factory or Window)(app, url, lang)
    stopped = threading.Event()

    def stop() -> None:
        if stopped.is_set():
            return
        stopped.set()
        app.stopping.set()
        app.phone.close()
        app.runner.stop_all()
        server.shutdown()
        if win:
            win.close()

    app.quit = stop
    threading.Thread(target=app.updates.daily, args=(app.stopping,), name="smtv-updates", daemon=True).start()
    if win:
        app.show_window = win.show
    on_mac = bool(win) and sys.platform == "darwin"
    notify = (lambda title, text: mac_notify(title, text) or system_notify(title, text)) if on_mac else system_notify
    watcher = Watcher(app, stop, lang, notify=notify, badge=mac_badge if on_mac else None)
    threading.Thread(target=watcher.run, name="smtv-watch", daemon=True).start()
    try:
        app.queue_next()                   # requests that waited when SMTV last quit go on (inside: stop() ends them)
        shown = win.run() if win else False
        if not shown:                      # no native window here: the page in the browser, until idle or Ctrl+C
            app.show_window = lambda: opener(url)
            watcher.idle = IdleWatch(IDLE_MINUTES * 60, busy=watcher._busy, keep=lambda: False)
            opener(url)
            while thread.is_alive():
                thread.join(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        stop()
        server.server_close()
        remove_session(app.token)
    return 0
