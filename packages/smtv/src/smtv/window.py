"""SMTV's own window: the page in a native window (pywebview), not a browser tab.

pywebview draws the page with the system's own engine (WebKit on macOS, WebView2 on Windows, WebKitGTK or Qt on Linux),
so SMTV is one program with one icon: the process lives as long as its window, and nothing runs in the background on
its own. Closing the window while jobs run asks whether to go on in the background (the window then goes to the Dock or
the taskbar) or to stop them.

The window is built hidden and shown only when the page has loaded, so its first frame is already right. On macOS it has
no title bar: the native buttons sit in the page's top bar, a press anywhere in that bar moves the window (caught by
the window itself before the page sees it: asking from the page arrived too late, after the press was gone), a double
press zooms it, and the corners are rounder (24 pt, where macOS allows it). Behind the page is glass: the
window is not opaque, WebKit draws no background of its own, and a vibrancy view (NSVisualEffectView, always Active —
following the window's active state made it blink on redraws) sits inside the WebKit view below the page. The page then
gets the class `glass` from the first frame and keeps its header and rail see-through and its cards dense. The page says
which theme it shows (`theme:dark|light|auto`) and the glass follows. Without glass the window stays opaque in the page's colour.

Windows keeps its own frame: a frameless pywebview window there cannot be resized from its edges or snapped, so the
title bar is only painted in the page's colours (Windows 11; a dark or light title bar on Windows 10) and follows the
page's theme as the Mac window does (V9): the page says `theme:…` through pywebview's bridge (`js_api`, the Mac uses
its own message handler), and «auto» reads the system's app mode (and is said again when the system changes it).
"""
from __future__ import annotations

import sys
import threading
from pathlib import Path

from . import i18n

HEADER_PX = 46          # the page's top bar height on macOS: the native buttons sit in its middle, the bar moves the window
BUTTONS_PT = 84         # the native buttons' corner of the top bar: presses there are theirs
CORNER_PT = 24.0
WIDTH, HEIGHT, MIN_SIZE = 1280, 820, (720, 520)
BACKGROUND = "#181818"
CAPTION = "#181818"      # the page's top bar on Windows 11, so the system title bar continues it
CAPTION_TEXT = "#ececec"
CAPTION_LIGHT = "#f9f9f9"   # the same in the light theme (app.css: --bg, --text)
CAPTION_TEXT_LIGHT = "#0d0d0d"
GLASS_SCRIPT = "document.documentElement.classList.add('glass');"

BACKGROUND_CHOICE, STOP_CHOICE, CANCEL_CHOICE = "background", "stop", "cancel"


def shell() -> str:
    """Which window the page is in: it lays out its header for it (`?window=mac`)."""
    if sys.platform == "darwin":
        return "mac"
    return "win" if sys.platform == "win32" else "linux"


def available() -> str | None:
    """None when a native window can open here; otherwise why not (the page then opens in the browser)."""
    try:
        import webview  # noqa: F401
    except Exception as e:  # noqa: BLE001 — on Linux GTK or Qt bindings may be missing
        return f"{type(e).__name__}: {e}"
    return None


def closing_choice(running: int, ask) -> str:
    """What closing the window does: quit when nothing runs, otherwise what the person picks."""
    if running <= 0:
        return STOP_CHOICE
    return ask(running)


# --- macOS: no title bar, native buttons in the header, dragging, corners ------------------------------------------

def _mac_dress(window, on_message) -> None:
    import AppKit
    import objc
    from Foundation import NSObject
    from webview.platforms.cocoa import BrowserView

    ns = window.native
    ns.setStyleMask_(ns.styleMask() | AppKit.NSWindowStyleMaskFullSizeContentView)
    ns.setTitlebarAppearsTransparent_(True)
    ns.setTitleVisibility_(AppKit.NSWindowTitleHidden)
    ns.setBackgroundColor_(AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(24 / 255, 24 / 255, 24 / 255, 1.0))
    ns.setAppearance_(AppKit.NSAppearance.appearanceNamed_(AppKit.NSAppearanceNameDarkAqua))   # the page starts dark
    if ns.respondsToSelector_("_setCornerRadius:"):     # a private method: without it the corners stay as macOS draws them
        ns._setCornerRadius_(CORNER_PT)
    titlebar = ns.contentView().superview().subviews().lastObject()   # pywebview paints it grey on purpose
    if titlebar.respondsToSelector_("setBackgroundColor:"):
        titlebar.setBackgroundColor_(AppKit.NSColor.clearColor())
    view = BrowserView.instances[window.uid].webview
    for selector, value in (("_setAutomaticallyAdjustsContentInsets:", False), ("_setTopContentInset:", 0.0)):
        if view.respondsToSelector_(selector):            # WebKit would leave room for the title bar on its own
            getattr(view, selector.replace(":", "_"))(value)
    window._smtv_glass = _mac_glass(ns, view)

    class SMTVWindowMessages(NSObject):
        def userContentController_didReceiveScriptMessage_(self, controller, message):
            on_message(str(message.body()))

        def windowDidResize_(self, note):
            _mac_place_buttons(ns)

        def nativeFocus_(self, note):          # key, main, active: into the log beside what the page saw
            name = str(note.name()).replace("Notification", "")
            try:
                state = _mac_native_focus(ns, view)
                print(f"window: {name} | " + " ".join(f"{k}={int(v) if isinstance(v, bool) else v}" for k, v in state.items()))
            except Exception as e:  # noqa: BLE001
                print(f"window: {type(e).__name__}: {e}")
            if "Become" in name:
                # The page reads its focus only on its own focus, blur and visibility events; a change of the window that
                # comes without one of them (or before WebKit has taken it) would leave it grey. The window tells it to look.
                from PyObjCTools import AppHelper
                AppHelper.callLater(0.3, lambda: view.evaluateJavaScript_completionHandler_(
                    f"window.smtvFocusCheck && window.smtvFocusCheck('{name}')", None))

    def pressed(event):
        """A press in the top bar moves the window (a double press zooms it); any other press goes on to the page."""
        if event.window() != ns:
            return event
        point = event.locationInWindow()
        if not in_drag_strip(point.x, point.y, ns.contentView().frame().size.height):
            return event
        if event.clickCount() >= 2:
            ns.zoom_(None)
        else:
            ns.performWindowDragWithEvent_(event)
        return None

    try:
        handler_class = objc.lookUpClass("SMTVWindowMessages")
    except objc.nosuchclass_error:
        handler_class = SMTVWindowMessages
    handler = handler_class.alloc().init()
    window._smtv_handler = handler                        # keep it alive as long as the window
    window._smtv_drag = AppKit.NSEvent.addLocalMonitorForEventsMatchingMask_handler_(AppKit.NSEventMaskLeftMouseDown, pressed)
    view.configuration().userContentController().addScriptMessageHandler_name_(handler, "smtvWindow")
    center = AppKit.NSNotificationCenter.defaultCenter()
    center.addObserver_selector_name_object_(handler, "windowDidResize:", AppKit.NSWindowDidResizeNotification, ns)
    for name in (AppKit.NSWindowDidBecomeKeyNotification, AppKit.NSWindowDidResignKeyNotification,
                 AppKit.NSWindowDidBecomeMainNotification, AppKit.NSWindowDidResignMainNotification):
        center.addObserver_selector_name_object_(handler, "nativeFocus:", name, ns)
    for name in (AppKit.NSApplicationDidBecomeActiveNotification, AppKit.NSApplicationDidResignActiveNotification):
        center.addObserver_selector_name_object_(handler, "nativeFocus:", name, None)
    _mac_place_buttons(ns)


def _mac_glass(ns, view) -> bool:
    """Glass behind the page (recipe tried with the owner 20.11). False, and the window stays opaque, when any part fails."""
    import AppKit
    try:
        import WebKit
        effect = AppKit.NSVisualEffectView.alloc().initWithFrame_(view.bounds())
        effect.setAutoresizingMask_(AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable)
        effect.setMaterial_(AppKit.NSVisualEffectMaterialUnderWindowBackground)
        effect.setBlendingMode_(AppKit.NSVisualEffectBlendingModeBehindWindow)
        effect.setState_(AppKit.NSVisualEffectStateActive)   # following the active state blinked on every redraw
        effect.setWantsLayer_(True)
        script = WebKit.WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
            GLASS_SCRIPT, WebKit.WKUserScriptInjectionTimeAtDocumentStart, True)
        view.setValue_forKey_(False, "drawsBackground")
        view.addSubview_positioned_relativeTo_(effect, AppKit.NSWindowBelow, None)
        view.configuration().userContentController().addUserScript_(script)
        ns.setOpaque_(False)
        ns.setBackgroundColor_(AppKit.NSColor.clearColor())
        return True
    except Exception as e:  # noqa: BLE001 — glass is a look; the window works without it
        print(f"window: no glass: {type(e).__name__}: {e}")
        try:
            view.setValue_forKey_(True, "drawsBackground")
        except Exception:  # noqa: BLE001
            pass
        return False


def _mac_place_buttons(ns) -> None:
    import AppKit
    close = ns.standardWindowButton_(AppKit.NSWindowCloseButton)
    if close is None or close.superview() is None:
        return
    container = close.superview().superview()             # NSTitlebarContainerView
    frame = container.frame()
    container.setFrame_(((frame.origin.x, ns.frame().size.height - HEADER_PX), (frame.size.width, HEADER_PX)))
    for i, kind in enumerate((AppKit.NSWindowCloseButton, AppKit.NSWindowMiniaturizeButton, AppKit.NSWindowZoomButton)):
        button = ns.standardWindowButton_(kind)
        button.setFrameOrigin_((20 + i * 20, (HEADER_PX - button.frame().size.height) / 2))


def in_drag_strip(x: float, y: float, height: float) -> bool:
    """Whether a press at (x, y) in window points (origin bottom left) is in the top bar, off the native buttons."""
    return y >= height - HEADER_PX and x >= BUTTONS_PT


def theme_of(body: str) -> str | None:
    """The theme a page message asks for: `theme:dark`, `theme:light` or `theme:auto` (follow the system); anything else
    is not a theme."""
    return body.split(":", 1)[1] if body in ("theme:dark", "theme:light", "theme:auto") else None


def focus_of(body: str) -> tuple[bool, str] | None:
    """What the page saw of its focus: `focus:1:blur+500` → (True, "blur+500"); anything else is not that."""
    parts = body.split(":", 2)
    if len(parts) != 3 or parts[0] != "focus" or parts[1] not in ("0", "1") or not parts[2] or len(parts[2]) > 40:
        return None
    return parts[1] == "1", parts[2]


def focus_line(page: bool, why: str, native: dict) -> str:
    """One log line: what the page saw and what the window is. `MISMATCH`: the window is the key window of the active app
    with the page as its first responder, yet the page thinks it has no focus (it draws itself grey) — or the reverse."""
    expected = bool(native.get("app") and native.get("key") and native.get("responder") == "page")
    flags = " ".join(f"{k}={int(v) if isinstance(v, bool) else v}" for k, v in native.items())
    return f"focus: page={int(page)} at={why} | {flags}" + ("  MISMATCH" if expected != page else "")


def _mac_native_focus(ns, view) -> dict:
    import AppKit
    responder = ns.firstResponder()
    if responder is not None and responder.isKindOfClass_(AppKit.NSView) and (responder == view or responder.isDescendantOf_(view)):
        name = "page"
    else:
        name = type(responder).__name__ if responder is not None else "none"
    return {"app": bool(AppKit.NSApp.isActive()), "key": bool(ns.isKeyWindow()), "main": bool(ns.isMainWindow()),
            "visible": bool(ns.isVisible()), "mini": bool(ns.isMiniaturized()), "responder": name}


def _mac_message(window, body: str) -> None:
    import AppKit
    ns = window.native
    focus = focus_of(body)
    if focus:
        try:
            from webview.platforms.cocoa import BrowserView
            print(focus_line(focus[0], focus[1], _mac_native_focus(ns, BrowserView.instances[window.uid].webview)))
        except Exception as e:  # noqa: BLE001 — a look for the log only
            print(f"focus: page={int(focus[0])} at={focus[1]} | native state unknown: {type(e).__name__}: {e}")
        return
    theme = theme_of(body)
    if theme:      # the glass and the native buttons follow the page's theme
        # auto: no appearance of our own, so the window (and the page's prefers-color-scheme) follow the system again
        names = {"dark": AppKit.NSAppearanceNameDarkAqua, "light": AppKit.NSAppearanceNameAqua}
        ns.setAppearance_(AppKit.NSAppearance.appearanceNamed_(names[theme]) if theme in names else None)
        if not getattr(window, "_smtv_glass", False):
            light = theme == "light" or (theme == "auto" and "Dark" not in str(ns.effectiveAppearance().name()))
            rgb = (249 / 255, 249 / 255, 249 / 255) if light else (24 / 255, 24 / 255, 24 / 255)
            ns.setBackgroundColor_(AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(*rgb, 1.0))
        _mac_place_buttons(ns)      # a new appearance lays the title bar out again: the buttons go back to the corner


def _mac_ask(running: int, lang: str) -> str:
    import AppKit
    alert = AppKit.NSAlert.alloc().init()
    alert.setMessageText_(i18n.text("busy_title", lang))
    alert.setInformativeText_(i18n.text("busy_body", lang, n=running, where=i18n.text("busy_dock", lang)))
    for key in ("busy_bg", "busy_stop", "busy_cancel"):
        alert.addButtonWithTitle_(i18n.text(key, lang))
    answer = alert.runModal()
    return {AppKit.NSAlertFirstButtonReturn: BACKGROUND_CHOICE,
            AppKit.NSAlertSecondButtonReturn: STOP_CHOICE}.get(answer, CANCEL_CHOICE)


# Notifications under SMTV's own name and icon (UserNotifications). macOS allows them only to a signed app, so
# `smtv shortcut` signs SMTV.app locally (ad-hoc); the first start asks the person once. Not allowed or not available:
# False, and the caller falls back to osascript.
_notifications = {"granted": False}


def mac_notifications_setup() -> None:
    try:
        import UserNotifications as UN
    except ImportError:
        return

    def answered(granted, error):
        _notifications["granted"] = bool(granted)
        if error is not None:
            print(f"notifications: {error.localizedDescription()}")

    try:
        UN.UNUserNotificationCenter.currentNotificationCenter().requestAuthorizationWithOptions_completionHandler_(
            UN.UNAuthorizationOptionAlert | UN.UNAuthorizationOptionSound, answered)
    except Exception as e:  # noqa: BLE001 — not SMTV.app's process (started from a terminal): osascript then
        print(f"notifications: {type(e).__name__}: {e}")


def mac_notify(title: str, text: str) -> bool:
    if not _notifications["granted"]:
        return False
    try:
        import uuid

        import UserNotifications as UN
        content = UN.UNMutableNotificationContent.alloc().init()
        content.setTitle_(title)
        content.setBody_(text)
        content.setSound_(UN.UNNotificationSound.defaultSound())
        request = UN.UNNotificationRequest.requestWithIdentifier_content_trigger_(str(uuid.uuid4()), content, None)

        def added(error):
            if error is not None:
                print(f"notification: {error.localizedDescription()}")

        UN.UNUserNotificationCenter.currentNotificationCenter().addNotificationRequest_withCompletionHandler_(request, added)
        return True
    except Exception as e:  # noqa: BLE001
        print(f"notification: {type(e).__name__}: {e}")
        return False


def mac_badge(count: int) -> None:
    """The number of running jobs on SMTV's Dock icon (none at zero)."""
    try:
        import AppKit
        from PyObjCTools import AppHelper
        AppHelper.callAfter(lambda: AppKit.NSApp.dockTile().setBadgeLabel_(str(count) if count else ""))
    except Exception:  # noqa: BLE001 — a badge is decoration
        pass


# --- Windows -------------------------------------------------------------------------------------------------------

def colorref(color: str) -> int:
    """#rrggbb as Windows' COLORREF (0x00bbggrr)."""
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
    return r | (g << 8) | (b << 16)


# DwmSetWindowAttribute: DWMWA_USE_IMMERSIVE_DARK_MODE (Windows 10 2004+), then DWMWA_CAPTION_COLOR and
# DWMWA_TEXT_COLOR (Windows 11; ignored before)
DWM_DARK_MODE, DWM_CAPTION_COLOR, DWM_TEXT_COLOR = 20, 35, 36
PERSONALIZE_KEY = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"


def win_title_attributes(theme: str, system_light: bool) -> tuple[tuple[int, int], ...]:
    """The title bar for the page's theme: dark, light, or auto (the system's app mode)."""
    light = theme == "light" or (theme == "auto" and system_light)
    caption, text = (CAPTION_LIGHT, CAPTION_TEXT_LIGHT) if light else (CAPTION, CAPTION_TEXT)
    return ((DWM_DARK_MODE, 0 if light else 1), (DWM_CAPTION_COLOR, colorref(caption)), (DWM_TEXT_COLOR, colorref(text)))


WIN_TITLE_ATTRIBUTES = win_title_attributes("dark", False)     # the page starts dark, as on the Mac


def win_system_light() -> bool:
    """Whether Windows shows apps light (Settings → Personalization → Colours → app mode). Unknown: dark, the page's own
    first theme."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, PERSONALIZE_KEY) as key:
            return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 1
    except (ImportError, OSError):
        return False


def _win_title(hwnd: int, attributes=WIN_TITLE_ATTRIBUTES) -> bool:
    """A title bar in the page's colours, so the system frame reads as the page's top bar. False: not even dark or light
    mode took (before Windows 10 2004); the colours alone fail on Windows 10 and that is fine."""
    try:
        import ctypes
        results = []
        for attribute, raw in attributes:
            value = ctypes.c_int(raw)
            results.append(ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attribute, ctypes.byref(value), ctypes.sizeof(value)))  # type: ignore[attr-defined]
        if results[0] != 0:
            print(f"window: DwmSetWindowAttribute(dark mode) answered {results[0] & 0xFFFFFFFF:#010x}")
        return results[0] == 0
    except Exception as e:  # noqa: BLE001 — no dwmapi: the system colours stay
        print(f"window: no title bar colours ({type(e).__name__}: {e})")
        return False


class WinBridge:
    """What the page reaches on Windows as `window.pywebview.api`: only `message`, the same words the Mac window gets
    through its message handler. Nothing else is exposed (pywebview publishes every public attribute)."""

    def __init__(self, apply):
        self._apply = apply

    def message(self, body) -> bool:
        theme = theme_of(body) if isinstance(body, str) else None
        if not theme:
            return False
        try:
            self._apply(theme)
        except Exception as e:  # noqa: BLE001 — said here: the page's side of the bridge swallows errors
            print(f"window: the title bar did not take theme {theme} ({type(e).__name__}: {e})")
            return False
        return True


def _win_ask(running: int, lang: str) -> str:
    import ctypes
    text = i18n.text("busy_body", lang, n=running, where=i18n.text("busy_taskbar", lang)) + "\n\n" + i18n.text("busy_yes_no", lang)
    answer = ctypes.windll.user32.MessageBoxW(None, text, i18n.text("busy_title", lang), 0x03 | 0x20 | 0x40000)  # type: ignore[attr-defined]
    return {6: BACKGROUND_CHOICE, 7: STOP_CHOICE}.get(answer, CANCEL_CHOICE)


# --- the window ----------------------------------------------------------------------------------------------------

VIDEO_TYPES = ("Video (*.mp4;*.mkv;*.mov;*.webm;*.flv;*.ts;*.m4v;*.avi;*.mp3;*.m4a;*.wav;*.aac)", "All files (*.*)")


def browser_profile() -> str | None:
    """The Windows ZIP keeps the window's browser profile (WebView2) in its own data folder, not in %LOCALAPPDATA%."""
    from smtv_core import paths
    return str(paths.home() / "webview") if paths.portable_top() is not None else None


def win_taskbar(app: Path | None = None, set_id=None):
    """Windows: SMTV's taskbar id for this process (the window is one button with SMTV's shortcuts and the installer's
    icons, not Python's) and the icon file for the window. ClipIt.exe stays python.org's signed program byte for byte
    (Smart App Control), so its icon is Python's: the window's comes from here. Neither failing stops the window."""
    from . import launcher
    try:
        if set_id is None and sys.platform == "win32":
            from .winlink import set_app_id
            set_id = set_app_id
        if set_id is not None:
            set_id(launcher.APP_ID)
    except Exception as e:  # noqa: BLE001 — the window groups under Python then
        print(f"window: no taskbar id ({type(e).__name__}: {e})")
    from smtv_core import paths
    icon = launcher.window_icon(app or paths.app_folder(), paths.home())
    if icon is None:
        print("window: no icon file, Python's icon stays")
    return icon


class Window:
    """The one window of this SMTV process."""

    def __init__(self, app, url: str, lang: str):
        self.app, self.url, self.lang = app, url, lang
        self.window = None
        self.loaded = threading.Event()
        self.hwnd = 0               # Windows: the window's handle, kept from the setup (the bridge runs on its own thread)
        self.theme = "dark"

    def ask(self, running: int) -> str:
        if sys.platform == "darwin":
            return _mac_ask(running, self.lang)
        if sys.platform == "win32":
            return _win_ask(running, self.lang)
        return BACKGROUND_CHOICE        # no dialog here: the safe choice keeps the work

    def on_closing(self):
        """False keeps the window: it goes to the Dock or taskbar instead (jobs go on) or stays (cancel)."""
        if self.app.stopping.is_set():
            return True
        choice = closing_choice(self.app.activity().get("running", 0), self.ask)
        if choice == STOP_CHOICE:
            return True
        if choice == BACKGROUND_CHOICE:
            if sys.platform == "darwin":
                self.window.native.miniaturize_(None)
            else:
                threading.Thread(target=self.window.minimize, daemon=True).start()
        return False

    def show(self) -> None:
        """Bring the window forward (a second double-click on the SMTV icon)."""
        if not self.window:
            return
        if sys.platform == "darwin":
            import AppKit
            from PyObjCTools import AppHelper

            def front():
                ns = self.window.native
                if ns.isMiniaturized():
                    ns.deminiaturize_(None)
                ns.makeKeyAndOrderFront_(None)
                AppKit.NSApp.activateIgnoringOtherApps_(True)
            AppHelper.callAfter(front)
        else:
            self.window.restore()
            self.window.show()

    def pick_file(self) -> str | None:
        """The system's «open file» dialog over this window: the path of the chosen video, or None (cancelled)."""
        if not self.window:
            return None
        import webview
        kind = getattr(getattr(webview, "FileDialog", None), "OPEN", None) or webview.OPEN_DIALOG
        chosen = self.window.create_file_dialog(kind, allow_multiple=False, file_types=VIDEO_TYPES)
        if not chosen:
            return None
        return str(chosen[0] if isinstance(chosen, (list, tuple)) else chosen)

    def close(self) -> None:
        if self.window:
            try:
                self.window.destroy()
            except Exception:  # noqa: BLE001 — already closed
                pass

    def _setup(self, window) -> None:
        """Runs once the GUI loop is up: dress the hidden window, load the page, show it when it has loaded."""
        if sys.platform == "darwin":
            from PyObjCTools import AppHelper
            mac_notifications_setup()
            dressed = threading.Event()

            def dress():
                try:
                    _mac_dress(window, lambda body: _mac_message(window, body))
                finally:
                    dressed.set()
            AppHelper.callAfter(dress)
            dressed.wait(5)
        elif sys.platform == "win32":
            try:
                self.hwnd = int(str(window.native.Handle))
            except Exception as e:  # noqa: BLE001 — no handle: the system's title bar stays
                print(f"window: no handle for the title bar ({type(e).__name__}: {e})")
            self.win_theme(self.theme)
        self.loaded.clear()
        window.load_url(f"{self.url}{'&' if '?' in self.url else '?'}window={shell()}")
        self.loaded.wait(15)
        if sys.platform == "darwin":
            from PyObjCTools import AppHelper
            placed = threading.Event()
            AppHelper.callAfter(lambda: (_mac_place_buttons(window.native), placed.set()))
            placed.wait(5)
        window.show()

    def win_theme(self, theme: str) -> None:
        """Windows: the title bar follows the page's theme (`auto`: the system's app mode at this moment)."""
        self.theme = theme
        if self.hwnd and not _win_title(self.hwnd, win_title_attributes(theme, theme == "auto" and win_system_light())):
            print(f"window: the title bar keeps the system's colours (theme {theme})")

    def run(self) -> bool:
        """Blocks until the window closes. False when no native window can open here."""
        try:
            import webview
        except Exception as e:  # noqa: BLE001
            print(f"no window: {type(e).__name__}: {e}")
            return False
        webview.settings["ALLOW_DOWNLOADS"] = True                 # «Download» on a clip: a save dialog
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = True  # «Where to get a key» opens in the browser
        icon = win_taskbar() if sys.platform == "win32" else None
        window = webview.create_window("Clip It!", "about:blank", width=WIDTH, height=HEIGHT, min_size=MIN_SIZE,
                                       background_color=BACKGROUND, hidden=True, text_select=True,
                                       js_api=WinBridge(self.win_theme) if sys.platform == "win32" else None)
        self.window = window
        self.app.pick_file = self.pick_file
        window.events.loaded += lambda: self.loaded.set()
        window.events.closing += self.on_closing
        try:
            webview.start(self._setup, window, private_mode=False, icon=str(icon) if icon else None,
                          storage_path=browser_profile())
        except Exception as e:  # noqa: BLE001 — no GUI here (Linux without WebKitGTK or Qt)
            print(f"no window: {type(e).__name__}: {e}")
            return False
        return True
