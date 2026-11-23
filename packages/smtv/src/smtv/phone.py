"""Open SMTV on a phone over home Wi-Fi (stage 9).

Off by default. The switch is remembered between starts (owner, 21.11): SMTV started with it on opens the address
again with the same key, so a phone keeps working without a new scan. Switched on, the page's server also listens on this computer's
private address in the home network, and the window shows a QR code with that address and a random key. The phone's
camera opens it; the server swaps the key for a cookie and the phone works from then on. Without the key nothing on that
address answers. Switching off closes the address at once and forgets the key, so every phone is cut off; switching on
again makes a new key. The key is kept like the model key (the keychain, or a private file); the switch and the address
in the settings file.

Kept simple on purpose (owner, 20.11): no pairing codes, no device list. One key of 192 random bits cannot be guessed.

From a phone everything works except the model key (seeing or changing it) and changing the program (update, install,
remove plugins, remove SMTV, quit): those stay on the computer.
"""
from __future__ import annotations

import hmac
import ipaddress
import secrets
import socket
import threading

from . import qr

PRIVATE = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
COOKIE = "smtv_phone"
# Routes a phone never reaches: the providers and their keys, and changes to the program itself. «Settings → Agents»
# (which provider and model an agent takes) works from a phone: no key is ever in it.
DENIED = {
    ("GET", "/api/settings"), ("GET", "/api/uninstall"), ("GET", "/api/phone"),
    ("POST", "/api/window/show"), ("POST", "/api/quit"),
    ("POST", "/api/updates/update"), ("POST", "/api/updates/cancel"), ("POST", "/api/updates/settings"), ("POST", "/api/uninstall"),
    ("POST", "/api/phone"), ("POST", "/api/queue"),       # a command handed over from a terminal: only on the computer
    ("GET", "/api/report"), ("POST", "/api/report"), ("POST", "/api/report/reveal"),   # the archive is saved on the computer
}


def denied(method: str, path: str) -> bool:
    parts = [p for p in path.split("/") if p]
    if method == "POST" and parts[:2] == ["api", "plugins"]:
        return True
    if parts[:3] == ["api", "settings", "providers"]:
        return True
    if parts[:3] == ["api", "settings", "speech"] and method != "GET":    # downloads and removals change this computer
        return True
    if method == "POST" and parts[:2] == ["api", "account"]:
        return True                       # sign-in, sign-out and buying hours: on the computer; a phone only shows the account
    if method == "POST" and (parts[:2] == ["api", "fixes"] or parts[:2] == ["api", "cache"] or parts[:2] == ["api", "folder"]):
        return True                       # «Fix» runs programs on the computer, the cache and the folder are its own (stage 24)
    return (method, path.rstrip("/") or "/") in DENIED


def private(ip: str) -> bool:
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return a.version == 4 and any(a in n for n in PRIVATE)


def addresses() -> list[str]:
    """This computer's private IPv4 addresses in the local network; the one of the main route first. A UDP socket
    `connect` only picks the route, nothing is sent. VPN and proxy addresses (100.64/10, 198.18/15) are not private
    home addresses and are left out."""
    found: list[str] = []

    def add(ip: str) -> None:
        if private(ip) and ip not in found:
            found.append(ip)

    for target in ("8.8.8.8", "192.168.255.255", "10.255.255.255", "172.31.255.255"):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((target, 9))
            add(s.getsockname()[0])
        except OSError:
            pass
        finally:
            s.close()
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            add(str(info[4][0]))
    except OSError:
        pass
    return found


class PhoneError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


class Saved:
    """Where the switch lives between starts: on/off and the address in the settings, the key with the secrets."""
    KEY = "phone_key"

    def load(self) -> dict:
        from smtv_core.settings import Settings, get_secret
        saved = Settings.load().tools.get("smtv", {}).get("phone") or {}
        return {"on": saved.get("on") is True, "address": saved.get("address") if isinstance(saved.get("address"), str) else None,
                "key": get_secret(self.KEY) if saved.get("on") is True else None}

    def save(self, on: bool, address: str | None, key: str | None) -> None:
        from smtv_core.settings import Settings, set_secret
        if on and key:
            set_secret(self.KEY, key)
        with Settings.edit() as settings:
            settings.tools.setdefault("smtv", {})["phone"] = {"on": on, "address": address}


class Phone:
    """The switch, the second listening address and its key. `make_server(address)` makes the listening server."""

    def __init__(self, make_server, port, find=addresses, saved: Saved | None = None):
        self._make_server, self._port, self._find, self._saved = make_server, port, find, saved
        self._lock = threading.Lock()
        self.server = None
        self.address: str | None = None
        self.key: str | None = None

    @property
    def on(self) -> bool:
        return self.server is not None

    def url(self) -> str | None:
        return f"http://{self.address}:{self._port()}/?k={self.key}" if self.on else None

    def state(self) -> dict:
        addrs = self._find()
        if self.on and self.address not in addrs:
            addrs = [self.address, *addrs]
        url = self.url()
        return {"on": self.on, "address": self.address, "addresses": addrs, "port": self._port(),
                "page": f"http://{self.address}:{self._port()}/" if self.on else None, "url": url, "qr": qr.svg(url) if url else None}

    def restore(self) -> None:
        """At the start of SMTV: switched on last time — on again, with the same key and, if it is still there, the same
        address. No network now: stays off this time and tries again at the next start."""
        if not self._saved:
            return
        try:
            saved = self._saved.load()
        except Exception as e:  # noqa: BLE001 — unreadable settings must not stop SMTV from starting
            print(f"phone access: settings not read: {type(e).__name__}")
            return
        if not saved["on"]:
            return
        addrs = self._find()
        address = saved["address"] if saved["address"] in addrs else (addrs[0] if addrs else None)
        if not address:
            print("phone access: switched on, but this computer is not in a local network now")
            return
        try:
            self.enable(address, key=saved["key"], remember=False)
            if self.key != saved["key"] or self.address != saved["address"]:
                self._remember()      # a new key (the old one was lost) or another address: the next start uses these
        except PhoneError as e:
            print(f"phone access: not restored: {e.message}")

    def _remember(self) -> None:
        if not self._saved:
            return
        try:
            self._saved.save(self.on, self.address, self.key)
        except Exception as e:  # noqa: BLE001 — the switch works now; only the next start would not know it
            print(f"phone access: not saved: {type(e).__name__}")

    def enable(self, address: str | None = None, key: str | None = None, remember: bool = True) -> dict:
        with self._lock:
            addrs = self._find()
            address = address or (self.address if self.on else None) or (addrs[0] if addrs else None)
            if not address:
                raise PhoneError("no_network", "this computer has no private address in a local network: is Wi-Fi or Ethernet connected?")
            if address not in addrs and address != self.address:
                raise PhoneError("bad_address", "not an address of this computer in the local network")
            if self.on and address == self.address:
                return self.state()
            keep = self.key if self.on else None      # another address: the phones keep their key
            self._close()
            try:
                server = self._make_server(address)
            except OSError as e:
                raise PhoneError("cannot_listen", f"cannot listen on {address}:{self._port()}: {e.strerror or e}") from None
            self.key = key if key and len(key) >= 32 else keep or secrets.token_urlsafe(24)
            self.server, self.address = server, address
            threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.5}, name="smtv-phone", daemon=True).start()
            print(f"phone access: on, {address}:{self._port()}")
            if remember:
                self._remember()
        return self.state()

    def disable(self) -> dict:
        with self._lock:
            was = self.on
            self._close()
            if was:
                print("phone access: off")
            self._remember()
        return self.state()

    def close(self) -> None:
        """SMTV quits: the address closes, the switch stays as it was for the next start."""
        with self._lock:
            self._close()

    def _close(self) -> None:
        server, self.server, self.address, self.key = self.server, None, None, None
        if server:
            server.shutdown()
            server.server_close()
            server.cut_all()      # open streams of a phone end now, not at their next write

    def admits(self, address: str, key: str | None) -> bool:
        """A request on `address` with this key (from the QR code or the cookie) may go on."""
        current = self.key
        return bool(self.on and current and key and address == self.address and hmac.compare_digest(key, current))
