"""What our server learns about this copy of Clip It! when a link is downloaded (see PRIVACY.md).

The device: sha256 hex of 'smtv-device-v1:' + the machine id (macOS IOPlatformUUID, Windows MachineGuid, Linux
/etc/machine-id). The machine id itself is never sent or stored. When it cannot be read, a random 32-byte id is made
once and kept in the app's settings (`tools.smtv.device_id`).
"""
from __future__ import annotations

import hashlib
import platform
import re
import secrets
import subprocess
import sys
from pathlib import Path

PREFIX = "smtv-device-v1:"


def machine_id() -> str:
    """The operating system's own id of this computer, or an empty string when it cannot be read."""
    try:
        if sys.platform == "darwin":
            out = subprocess.run(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], capture_output=True, text=True, timeout=10).stdout
            found = re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', out)
            return found.group(1).strip() if found else ""
        if sys.platform.startswith("win"):
            import winreg      # type: ignore[import-not-found]
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
                return str(winreg.QueryValueEx(key, "MachineGuid")[0]).strip()
        return Path("/etc/machine-id").read_text(encoding="ascii").strip()
    except Exception:  # noqa: BLE001 — any failure: the random id below
        return ""


def _random_id() -> str:
    from .settings import Settings
    with Settings.edit() as s:
        own = s.tools.setdefault("smtv", {})
        stored = str(own.get("device_id") or "")
        if not re.fullmatch(r"[0-9a-f]{64}", stored):
            stored = own["device_id"] = secrets.token_hex(32)
    return stored


def device_id() -> str:
    raw = machine_id()
    if raw:
        return hashlib.sha256((PREFIX + raw).encode("utf-8")).hexdigest()
    return _random_id()


def os_tag() -> str:
    """macos-15.1-arm64, windows-11-x64, linux-x64."""
    machine = platform.machine().lower()
    arch = {"x86_64": "x64", "amd64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(machine, machine or "unknown")
    if sys.platform == "darwin":
        return f"macos-{platform.mac_ver()[0] or 'unknown'}-{arch}"
    if sys.platform.startswith("win"):
        build = sys.getwindowsversion().build if hasattr(sys, "getwindowsversion") else 0       # type: ignore[attr-defined]
        return f"windows-{'11' if build >= 22000 else platform.release() or 'unknown'}-{arch}"
    return f"linux-{arch}"


def headers(app_key: str) -> dict[str, str]:
    from . import __version__
    return {"X-SMTV-App-Key": app_key, "X-SMTV-Device": device_id(), "X-SMTV-Version": __version__, "X-SMTV-OS": os_tag()}
