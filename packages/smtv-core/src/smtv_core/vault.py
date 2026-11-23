"""Keys in a file, encrypted, for computers without a system keychain (some Linux desktops, Docker) — stage 19.

Two files, each readable only by its owner:
- `secrets.json` in the SMTV folder — the keys, each encrypted on its own: {"v": 1, "keys": {name: {"n": nonce, "c":
  cipher text, "t": tag}}};
- `secrets.key` — 32 random bytes, the encryption key, made once (`paths.secrets_key_file`). On a Mac and Linux it is
  beside the keys with the rights 0600. Windows has no such rights: the files are in the person's profile, which other
  users of the computer cannot open, and the key is in %LOCALAPPDATA%, which a domain does not copy to its server
  (an older SMTV kept it beside the keys: it is moved there on first use).

What this protects from: the secrets file leaking alone — a backup, a synced folder, a file sent by mistake, a report.
What it does not protect from: a program running as the same user on this computer: it can read both files, as it could
read the system keychain of an unlocked session. The docs say so in these words.

Only the standard library: HMAC-SHA256 as a stream cipher in counter mode (keystream block i = HMAC(k_enc, nonce ‖ i))
and HMAC-SHA256 over name ‖ nonce ‖ cipher text as the tag (encrypt, then MAC), keys for both derived from the file key.
A changed byte, a key moved to another name or the wrong key file are refused, never decoded into garbage.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets as _random
import sys
import threading
from contextlib import contextmanager
from pathlib import Path

from .filelock import LockTimeout, ProcessLock

VERSION = 1
KEY_BYTES = 32
NONCE_BYTES = 16


# one read-change-write of the keys file at a time: the window's threads, and other SMTV processes (a job refreshing the
# account's token while the window saves a key, B20). The lock file is in `run` beside them (uninstall removes it with `run`).
_LOCKS: dict[Path, ProcessLock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock_of(file: Path) -> ProcessLock:
    with _LOCKS_GUARD:
        if file not in _LOCKS:
            _LOCKS[file] = ProcessLock(lambda: file.parent / "run" / f"{file.name}.lock", file.name, strict=True)
        return _LOCKS[file]


@contextmanager
def _locked(file: Path):
    """The keys file locked; held by another SMTV process for too long: VaultError («try again»), never a write without
    the lock that could lose the other's key."""
    try:
        lock = _lock_of(file).__enter__()
    except LockTimeout as e:
        raise VaultError(f"{file.name} is busy in another SMTV process: try again") from e
    try:
        yield
    finally:
        lock.__exit__(None, None, None)


class VaultError(Exception):
    """The file is damaged, or does not belong to this key file."""


def _b64(b: bytes) -> str:
    return base64.b64encode(b).decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.b64decode(s.encode("ascii"), validate=True)


def _write_private(path: Path, data: bytes) -> None:
    """Write a file only its owner can read, atomically: never a moment with wider access or half a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{_random.token_hex(4)}.tmp")   # two processes never share one
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


class Vault:
    def __init__(self, file: Path, key_file: Path, legacy_key_file: Path | None = None):
        self.file, self.key_file = file, key_file
        # where an older SMTV kept the key: beside the keys
        self.legacy_key_file = legacy_key_file or file.with_name(key_file.name)

    # --- the key -------------------------------------------------------------------------------------------

    def _move_legacy(self) -> None:
        """The key file of an older SMTV moved to `key_file`, never lost: copied first, the old one removed after."""
        old = self.legacy_key_file
        if old == self.key_file or self.key_file.exists() or not old.is_file():
            return
        raw = old.read_bytes()
        if len(raw) != KEY_BYTES:
            return                     # damaged: left where it is, `_master` names it below
        _write_private(self.key_file, raw)
        try:
            old.unlink()
        except OSError as e:
            print(f"smtv: the old key file stays at {old.parent} ({type(e).__name__}); the keys use the new one",
                  file=sys.stderr)

    def _master(self, create: bool) -> bytes | None:
        try:
            self._move_legacy()
        except OSError as e:
            raise VaultError(f"{self.key_file.name} could not be moved to {self.key_file.parent}: {type(e).__name__}") from e
        try:
            raw = self.key_file.read_bytes()
        except FileNotFoundError:
            raw = b""
        if len(raw) == KEY_BYTES:
            return raw
        if raw:
            raise VaultError(f"{self.key_file.name} is damaged")
        if not create:
            return None
        key = _random.token_bytes(KEY_BYTES)
        _write_private(self.key_file, key)
        return key

    @staticmethod
    def _sub(master: bytes, what: bytes) -> bytes:
        return hmac.new(master, b"smtv-vault-v1 " + what, hashlib.sha256).digest()

    @classmethod
    def _stream(cls, master: bytes, nonce: bytes, n: int) -> bytes:
        k = cls._sub(master, b"enc")
        out = bytearray()
        i = 0
        while len(out) < n:
            out += hmac.new(k, nonce + i.to_bytes(8, "big"), hashlib.sha256).digest()
            i += 1
        return bytes(out[:n])

    @classmethod
    def _tag(cls, master: bytes, name: str, nonce: bytes, cipher: bytes) -> bytes:
        k = cls._sub(master, b"mac")
        return hmac.new(k, name.encode("utf-8") + b"\0" + nonce + cipher, hashlib.sha256).digest()

    # --- the file ------------------------------------------------------------------------------------------

    def _load(self) -> tuple[dict, dict]:
        """(encrypted entries, plain entries left by SMTV before stage 19)."""
        try:
            raw = json.loads(self.file.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return {}, {}
        except ValueError as e:
            raise VaultError(f"{self.file.name} is not readable") from e
        if not isinstance(raw, dict):
            raise VaultError(f"{self.file.name} is not readable")
        if raw.get("v") == VERSION and isinstance(raw.get("keys"), dict):
            return dict(raw["keys"]), {}
        # an older SMTV kept {name: value} in plain text: read it once, the next write encrypts it
        return {}, {k: v for k, v in raw.items() if isinstance(k, str) and isinstance(v, str)}

    def _save(self, entries: dict) -> None:
        _write_private(self.file, json.dumps({"v": VERSION, "keys": entries}, indent=1).encode("utf-8"))

    def _seal(self, master: bytes, name: str, value: str) -> dict:
        nonce = _random.token_bytes(NONCE_BYTES)
        plain = value.encode("utf-8")
        cipher = bytes(a ^ b for a, b in zip(plain, self._stream(master, nonce, len(plain))))
        return {"n": _b64(nonce), "c": _b64(cipher), "t": _b64(self._tag(master, name, nonce, cipher))}

    def _open(self, master: bytes, name: str, entry: dict) -> str:
        try:
            nonce, cipher, tag = _unb64(entry["n"]), _unb64(entry["c"]), _unb64(entry["t"])
        except (KeyError, TypeError, ValueError) as e:
            raise VaultError(f"the saved key {name} is damaged") from e
        if not hmac.compare_digest(tag, self._tag(master, name, nonce, cipher)):
            raise VaultError(f"the saved key {name} does not match {self.key_file.name}")
        return bytes(a ^ b for a, b in zip(cipher, self._stream(master, nonce, len(cipher)))).decode("utf-8")

    # --- what the rest of SMTV uses ------------------------------------------------------------------------

    def get(self, name: str) -> str | None:
        with _locked(self.file):
            return self._get(name)

    def _get(self, name: str) -> str | None:
        entries, plain = self._load()
        if plain:
            self._upgrade(plain)
            return plain.get(name) or None
        entry = entries.get(name)
        if entry is None:
            return None
        master = self._master(create=False)
        if master is None:
            raise VaultError(f"{self.key_file.name} is missing: the saved keys cannot be read")
        return self._open(master, name, entry) or None

    def set(self, name: str, value: str) -> None:
        with _locked(self.file):
            self._set(name, value)

    def _set(self, name: str, value: str) -> None:
        entries, plain = self._load()
        master = self._master(create=True)
        for k, v in plain.items():
            entries[k] = self._seal(master, k, v)
        entries[name] = self._seal(master, name, value)
        self._save(entries)

    def delete(self, name: str) -> bool:
        """Remove a key. A file that cannot be written is an error: a key the window says is gone must be gone."""
        with _locked(self.file):
            entries, plain = self._load()
            if name not in entries and name not in plain:
                return False
            if plain:
                master = self._master(create=True)
                entries = {k: self._seal(master, k, v) for k, v in plain.items()}
            entries.pop(name, None)
            self._save(entries)
            return True

    def names(self) -> list[str]:
        entries, plain = self._load()
        return sorted(set(entries) | set(plain))

    def _upgrade(self, plain: dict) -> None:
        """Encrypt the plain keys an older SMTV left. If it cannot be written now, the key is still read, it is tried
        again on the next read, and the reason goes to the log (never the key)."""
        try:
            master = self._master(create=True)
            self._save({k: self._seal(master, k, v) for k, v in plain.items()})
        except OSError as e:
            print(f"smtv: the keys in {self.file.name} are still in plain text: it could not be encrypted ({type(e).__name__})",
                  file=sys.stderr)
