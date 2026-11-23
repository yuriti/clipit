"""SMTV in Docker (stage 21): the same page as in the window, opened in a browser on the host.

The image sets SMTV_DOCKER=1. Then `smtv serve`:
- listens on every address inside the container (a published port reaches it only that way); compose publishes it on
  the host's 127.0.0.1 only, so other computers do not see it unless the owner publishes it wider on purpose;
- asks for an access key on every request, like Jupyter: inside the container every connection comes from Docker's own
  network, so the address of the caller says nothing, and the Host header is the caller's to choose. The key is made once,
  kept in the data volume (`access-key`, readable only by its owner) and printed in the log as a link
  `http://127.0.0.1:<port>/?token=<key>`. The link swaps the key for a cookie and leaves the address bar; the installed
  app (Chrome or Edge, «Install SMTV») keeps the cookie, so a new container with the same volume needs no new link.
  Delete the file and restart to cut off every browser that has the old key;
- keeps the checks of the window's page on top of the key: Host must be one of ours, changes need the session token in
  X-SMTV-Token and our own Origin, no CORS;
- does not update itself: a new version is a new image.

Settings, keys, speech models and clips live in SMTV_HOME (the volume). Local model servers (Ollama, LM Studio, …) are
on the host: SMTV_LOCAL_HOST=host.docker.internal. The Codex and Claude Code CLIs are not offered in the container —
signing in to a subscription inside a container is awkward and both are discouraged anyway; an API key works.

Environment:
- SMTV_PUBLIC_PORT — the host port the page is published on, if not the container's own (`9000:8642` → 9000);
- SMTV_HOSTS — more names the page is opened by, for a home server: `nas.local,192.168.1.20` (port: SMTV_PUBLIC_PORT
  unless given). Each still needs the key;
- SMTV_LAN_ADDRESS — the host's address in the home network, for «Phone»: the QR code then opens the page on the phone
  with its own phone key (the port must be published on that address too).
"""
from __future__ import annotations

import hmac
import ipaddress
import os
import re
import secrets
import threading
from dataclasses import dataclass, field
from pathlib import Path

ENV = "SMTV_DOCKER"
COOKIE = "smtv_access"
KEY_FILE = "access-key"
_HOST_NAME = re.compile(r"^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$")


def active() -> bool:
    return os.environ.get(ENV, "").strip() == "1"


def key_file() -> Path:
    from smtv_core import paths
    return paths.home() / KEY_FILE


def access_key(path: Path | None = None) -> str:
    """The key in the data volume; made the first time (192 random bits), readable only by its owner."""
    path = path or key_file()
    try:
        key = path.read_text(encoding="utf-8").strip()
        if len(key) >= 32:
            return key
    except FileNotFoundError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    key = secrets.token_urlsafe(24)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(key + "\n")
    os.replace(tmp, path)
    return key


def _port_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    if not raw.isdigit() or not 0 < int(raw) < 65536:
        raise ValueError(f"{name}={raw!r}: a port number, 1–65535")
    return int(raw)


def _host(entry: str, port: int) -> str:
    entry = entry.strip().lower()
    name, _, p = entry.rpartition(":") if entry.count(":") == 1 else (entry, "", "")
    if not p:
        name = entry
    elif not p.isdigit() or not 0 < int(p) < 65536:
        raise ValueError(f"SMTV_HOSTS: {entry!r} has a bad port")
    if not _HOST_NAME.match(name):
        raise ValueError(f"SMTV_HOSTS: {entry!r} is not a host name or an IPv4 address")
    return f"{name}:{p or port}"


def lan_address(raw: str | None) -> str | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    from .phone import private
    if not private(raw):
        raise ValueError(f"SMTV_LAN_ADDRESS={raw!r}: a private IPv4 address of the host in the home network (192.168…, 10…, 172.16–31…)")
    return str(ipaddress.ip_address(raw))


@dataclass
class Docker:
    """What `smtv serve` needs to know in a container."""
    port: int                         # the port inside the container
    public_port: int                  # the port on the host, as the browser sees it
    key: str
    lan: str | None = None            # the host's home-network address, for «Phone»
    extra: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls, port: int, key: str | None = None) -> "Docker":
        public = _port_env("SMTV_PUBLIC_PORT", port)
        extra = [_host(e, public) for e in os.environ.get("SMTV_HOSTS", "").split(",") if e.strip()]
        return cls(port=port, public_port=public, key=key or access_key(), lan=lan_address(os.environ.get("SMTV_LAN_ADDRESS")),
                   extra=extra)

    @property
    def hosts(self) -> set[str]:
        """Every Host the page answers: the host's loopback on the published port, the container's own port (health
        check, a command handed over from `docker exec`), the home-network address and the names given."""
        out = {f"{h}:{p}" for h in ("127.0.0.1", "localhost") for p in {self.port, self.public_port}}
        if self.lan:
            out.add(f"{self.lan}:{self.public_port}")
        out.update(self.extra)
        return out

    def phone_host(self) -> str | None:
        return f"{self.lan}:{self.public_port}" if self.lan else None

    def admits(self, value: str | None) -> bool:
        return bool(value) and hmac.compare_digest(value.encode(), self.key.encode())

    def links(self) -> list[str]:
        """The links printed in the log: loopback first, then the home-server names."""
        hosts = [f"127.0.0.1:{self.public_port}", *sorted(h for h in self.extra), *([self.phone_host()] if self.lan else [])]
        seen: list[str] = []
        for h in hosts:
            if h not in seen:
                seen.append(h)
        return [f"http://{h}/?token={self.key}" for h in seen]

    def cookie(self) -> str:
        return f"{COOKIE}={self.key}; Path=/; HttpOnly; SameSite=Strict; Max-Age=31536000"


def auth_headers() -> dict[str, str]:
    """For a command inside the container that talks to the running page (`docker exec … smtv vodcut run`): the key
    as the browser would send it. Empty outside Docker."""
    if not active():
        return {}
    try:
        key = key_file().read_text(encoding="utf-8").strip()
    except OSError:
        return {}
    return {"Cookie": f"{COOKIE}={key}"} if key else {}


class NoServer:
    """«Phone» in a container: the page already listens on every address, so switching it on starts no second
    server; this stands in for one (the phone's key and the QR code work as on a computer)."""

    def __init__(self):
        self._stop = threading.Event()

    def serve_forever(self, poll_interval: float = 0.5) -> None:
        self._stop.wait()

    def shutdown(self) -> None:
        self._stop.set()

    def server_close(self) -> None:
        pass

    def cut_all(self) -> None:
        pass
