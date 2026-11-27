"""The update channel (stage 27): one signed manifest, `latest.json`, beside every release on GitHub.

The manifest says which version is the latest, what changed, and which files each kind of install takes, with their
sizes and SHA-256 sums. Its detached signature, `latest.json.sig` (Ed25519, base64), is made on the build machine with
the maintainers' private key, which lives only in the release workflow's secrets; SMTV checks it with the public key
written below. A manifest that is not signed by that key, is malformed, or is older than one SMTV already accepted, is
refused; a file whose size or sum differs from the manifest is refused and deleted.

How each kind of install takes an update (`updates.install_kind`):
- uv, pip: the wheels of smtv, smtv-core and the installed tools, downloaded and checked here, then installed by the
  updater from those files (their dependencies come from PyPI as usual);
- docker: a new image is built from the repository (the window shows the command);
- dmg, exe (the desktop apps of stage 30): the installer file, downloaded and checked here, then opened.

Format (schema 1):
    {"schema": 1, "version": "0.2.0", "published": "2026-12-01T10:00:00Z",
     "packages": {"smtv": "0.2.0", "smtv-core": "0.2.0", "vodcut": "0.2.0"},
     "changes": [{"version": "0.2.0", "notes": ["…"]}, …],
     "kinds": {"uv": {"files": [{"package": "smtv", "name": "smtv-0.2.0-py3-none-any.whl", "url": "https://…",
                                 "size": 123, "sha256": "…"}, …]},
               "pip": {"files": […]},
               "dmg": {"files": [{"name": "SMTV-0.2.0-mac.dmg", …}]},      # both processors inside: no "arch"
               "exe": {"files": [{"name": "SMTV-0.2.0-windows-x64-setup.exe", "arch": "x64", …}]}}}
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import http.client
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import ed25519

URL = "https://github.com/yuriti/clipit/releases/latest/download/latest.json"
# The maintainers' public key. Its private half is the release workflow's secret SMTV_UPDATE_SIGNING_KEY.
PUBLIC_KEY = "QLD7R3qn3faw5V2wG7qyIxdlFpzPfljZINV0QHS5gsw="
SCHEMA = 1
TIMEOUT_S = 15.0
MAX_MANIFEST = 1_000_000
MAX_FILE = 2_000_000_000
KINDS = ("uv", "pip", "docker", "dmg", "exe")
METHOD = {"uv": "packages", "pip": "packages", "docker": "command", "dmg": "installer", "exe": "installer",
          "zip": "archive"}
# The Windows ZIP's file is listed under "exe": 0.1.0 refuses a list with a kind it does not know, so a "zip" kind would
# hide every update from it. Since 0.1.1 there is no installer: 0.1.0's installed copies get the ZIP, opened in
# Explorer, and the notes of the version say what to do; the ZIP updates itself in place from the same file.
LISTED_AS = {"zip": "exe"}
FILE_HOSTS = ("github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com")
LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
FILE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,150}$")
ARCHES = ("arm64", "x64")           # the processor an installer is for (a file without one fits every processor; an
                                    # arm64 computer without its own installer takes the x64 one, which it emulates)
VERSION_KEY = "manifest_version"     # in updates.json: the newest manifest SMTV accepted (no going back below it)


VERSION = re.compile(r"^(\d{1,6}(?:\.\d{1,6}){0,4})(?:(a|b|rc)(\d{1,6}))?(?:\.post(\d{1,6}))?(?:\.dev(\d{1,6}))?$")


def machine() -> str:
    """This computer's processor in the manifest's words: arm64 (Apple Silicon, Windows on ARM) or x64."""
    import platform
    return "arm64" if platform.machine().lower() in ("arm64", "aarch64") else "x64"


# --- version numbers (plain PEP 440 releases) ---------------------------------------------------------------------------------------------------

def parse_version(v: str):
    """A sortable key for a plain PEP 440 release number (1.2.3, 1.2.3rc1, 1.2.3.post1, 1.2.3.dev4), or None."""
    m = VERSION.match(str(v or "").strip())
    if not m:
        return None
    rel, phase, pre_n, post, dev = m.groups()
    nums = [int(x) for x in rel.split(".")]
    while len(nums) > 1 and nums[-1] == 0:
        nums.pop()
    inf = 10 ** 9
    if phase:
        pre = ({"a": 0, "b": 1, "rc": 2}[phase], int(pre_n))
    elif dev is not None and post is None:
        pre = (-1, 0)                   # 1.0.dev1 comes before 1.0a1
    else:
        pre = (3, 0)
    return (tuple(nums), pre, int(post) if post is not None else -1, int(dev) if dev is not None else inf)


def is_pre(v: str) -> bool:
    m = VERSION.match(str(v or "").strip())
    return bool(m and (m.group(2) or m.group(5) is not None))


def newer(a: str, b: str) -> bool:
    """a is a later version than b (unknown numbers are never newer)."""
    ka, kb = parse_version(a), parse_version(b)
    return bool(ka and kb and ka > kb)


class ChannelError(Exception):
    """Something about the channel that the window shows: `code` is one of not_found (no release yet), no_signature,
    bad_signature, malformed, old_manifest, not_for_this_install, bad_file, disk, unreachable."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


def manifest_url() -> str:
    """Our releases on GitHub, or SMTV_UPDATE_URL (a person's own setting for tests and mirrors: https, or http on this
    computer only). The signature is still checked with the same key."""
    raw = os.environ.get("SMTV_UPDATE_URL", "").strip()
    if not raw:
        return URL
    u = urllib.parse.urlsplit(raw)
    if u.scheme == "https" and u.hostname or (u.scheme == "http" and (u.hostname or "") in LOCAL_HOSTS):
        return raw
    raise ValueError("SMTV_UPDATE_URL: an https address, or http://127.0.0.1:<port>/latest.json")


def _read(url: str, limit: int, opener=None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "smtv-update-check"})
    try:
        with (opener or urllib.request.urlopen)(req, timeout=TIMEOUT_S) as r:
            raw = r.read(limit + 1)
    except urllib.error.HTTPError as e:     # the host answered: 404 is «not there», anything else is trouble on its side
        raise ChannelError("not_found" if e.code == 404 else "unreachable", f"{url}: HTTP {e.code}") from None
    except (OSError, http.client.HTTPException) as e:   # no network, the host is down, a connection cut mid-answer
        raise ChannelError("unreachable", f"{url}: {type(e).__name__}: {e}") from None
    if len(raw) > limit:
        raise ChannelError("malformed", f"{url}: the answer is too large")
    return raw


def verify(raw: bytes, signature: bytes, key: str = PUBLIC_KEY) -> None:
    """Raises ChannelError unless `signature` (base64 text) is the key's Ed25519 signature of exactly these bytes."""
    try:
        sig = base64.b64decode(signature.strip(), validate=True)
        public = base64.b64decode(key, validate=True)
    except (binascii.Error, ValueError):
        raise ChannelError("bad_signature", "the signature of latest.json is not base64") from None
    if not ed25519.verify(public, raw, sig):
        raise ChannelError("bad_signature", "latest.json is not signed by Clip It!'s maintainers")


def _file_ok(url: str, manifest_host: str | None) -> bool:
    u = urllib.parse.urlsplit(url)
    host = (u.hostname or "").lower()
    if u.scheme == "https" and (host in FILE_HOSTS or host == manifest_host):
        return True
    return u.scheme == "http" and host in LOCAL_HOSTS and host == manifest_host     # a test channel on this computer


def parse(raw: bytes, allowed: tuple[str, ...], manifest_host: str | None = None) -> dict:
    """The manifest, checked field by field; anything off raises ChannelError("malformed"). Only our packages
    (`allowed`), plain version numbers, file names without paths, https addresses on GitHub (or on the manifest's own
    host when SMTV_UPDATE_URL points elsewhere), SHA-256 sums and sizes pass."""
    def bad(why: str):
        return ChannelError("malformed", f"latest.json: {why}")

    try:
        data = json.loads(raw)
    except ValueError:
        raise bad("not JSON") from None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise bad(f"schema {SCHEMA} expected")
    version = data.get("version")
    if not isinstance(version, str) or not parse_version(version):
        raise bad("no plain version")
    packages = data.get("packages")
    if not isinstance(packages, dict) or packages.get("smtv") != version:
        raise bad("packages must name smtv at the manifest's version")
    for name, v in packages.items():
        if name not in allowed or v != version:   # all of SMTV's packages come out together, under one number
            raise bad(f"package {name!r} at {v!r}")
    changes = []
    for e in data.get("changes") or []:
        if not isinstance(e, dict) or not isinstance(e.get("version"), str) or not parse_version(e["version"]) \
                or newer(e["version"], version) or not isinstance(e.get("notes"), list):
            raise bad("a changes entry")
        changes.append({"version": e["version"], "notes": [str(n)[:400] for n in e["notes"][:50] if isinstance(n, str)]})
    kinds = {}
    for kind, spec in (data.get("kinds") or {}).items():
        if kind not in KINDS or not isinstance(spec, dict):
            raise bad(f"kind {kind!r}")
        files = []
        for f in spec.get("files") or []:
            if not isinstance(f, dict):
                raise bad(f"a file of {kind}")
            name, url, size, sha = f.get("name"), f.get("url"), f.get("size"), f.get("sha256")
            package, arch = f.get("package"), f.get("arch")
            if not isinstance(name, str) or not FILE_NAME.match(name) or ".." in name:
                raise bad(f"file name {name!r}")
            if not isinstance(url, str) or not _file_ok(url, manifest_host):
                raise bad(f"address of {name}")
            if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= MAX_FILE:
                raise bad(f"size of {name}")
            if not isinstance(sha, str) or not SHA256.match(sha):
                raise bad(f"sha256 of {name}")
            if package is not None and package not in packages:
                raise bad(f"package of {name}")
            if arch is not None and arch not in ARCHES:
                raise bad(f"arch of {name}")
            files.append({"name": name, "url": url, "size": size, "sha256": sha, "package": package, "arch": arch})
        kinds[kind] = {"files": files}
    return {"version": version, "published": str(data.get("published") or "")[:40], "packages": dict(packages),
            "changes": changes, "kinds": kinds}


def load(allowed: tuple[str, ...], floor: str | None = None, url: str | None = None, opener=None, key: str = PUBLIC_KEY) -> dict:
    """The latest manifest, fetched, verified and checked. `floor` is the newest version SMTV accepted before: a
    manifest below it is an old one served again (a mirror that fell behind, or someone holding updates back) and is
    refused, so SMTV never goes back."""
    url = url or manifest_url()
    raw = _read(url, MAX_MANIFEST, opener)
    try:
        signature = _read(url + ".sig", 4096, opener)
    except ChannelError as e:
        if e.code == "not_found":
            raise ChannelError("no_signature", "latest.json has no signature beside it") from None
        raise
    verify(raw, signature, key)
    found = parse(raw, allowed, (urllib.parse.urlsplit(url).hostname or "").lower())
    if floor and newer(floor, found["version"]):
        raise ChannelError("old_manifest", f"latest.json says {found['version']}, but {floor} was already announced")
    return found


def files_for(manifest: dict, kind: str, packages: list[str] | None = None, arch: str | None = None) -> list[dict]:
    """The files this kind of install takes from the manifest: for uv and pip, one wheel of each of `packages`; for the
    desktop apps, the one installer of this processor (`arch`, else this computer's)."""
    if kind not in METHOD or METHOD[kind] == "command":
        raise ChannelError("not_for_this_install", f"{kind}: nothing to download")
    files = (manifest.get("kinds") or {}).get(LISTED_AS.get(kind, kind), {}).get("files") or []
    if kind == "zip":
        files = [f for f in files if f["name"].endswith(".zip")]
    if METHOD[kind] in ("installer", "archive"):
        if any(f.get("arch") for f in files):     # an installer per processor, where there is one per processor
            mine = arch or machine()
            fits = [f for f in files if f.get("arch") in (mine, None)]
            if not fits and mine == "arm64":         # Windows on ARM runs x64 programs (an x64 app updates to x64)
                fits = [f for f in files if f.get("arch") == "x64"]
            files = fits
        if len(files) != 1:
            raise ChannelError("not_for_this_install", f"latest.json has no single installer for {kind}")
        return files
    out = []
    for name in packages or []:
        wheels = [f for f in files if f.get("package") == name and f["name"].endswith(".whl")]
        if len(wheels) != 1:
            raise ChannelError("not_for_this_install", f"latest.json has no single wheel of {name} for {kind}")
        out.append(wheels[0])
    return out


def download(file: dict, folder: Path, opener=None) -> Path:
    """One file of the manifest into `folder`, kept only when its size and SHA-256 are the manifest's."""
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / file["name"]
    part = folder / (file["name"] + ".part")
    digest, size = hashlib.sha256(), 0
    req = urllib.request.Request(file["url"], headers={"User-Agent": "smtv-update"})
    try:
        out = open(part, "wb")  # noqa: SIM115 — closed below on every path
    except OSError as e:
        raise ChannelError("disk", f"{part}: {type(e).__name__}: {e}") from None
    try:
        with out, (opener or urllib.request.urlopen)(req, timeout=TIMEOUT_S) as r:
            while True:
                try:
                    chunk = r.read(1 << 20)
                except (OSError, http.client.HTTPException) as e:
                    raise ChannelError("unreachable", f"{file['name']}: {type(e).__name__}: {e}") from None
                if not chunk:
                    break
                size += len(chunk)
                if size > file["size"]:
                    break
                digest.update(chunk)
                try:
                    out.write(chunk)
                except OSError as e:          # a full disk, no rights: not «no network»
                    raise ChannelError("disk", f"{part}: {type(e).__name__}: {e}") from None
    except ChannelError:
        part.unlink(missing_ok=True)
        raise
    except (OSError, http.client.HTTPException) as e:
        part.unlink(missing_ok=True)
        raise ChannelError("unreachable", f"{file['name']}: {type(e).__name__}: {e}") from None
    if size != file["size"] or digest.hexdigest() != file["sha256"]:
        part.unlink(missing_ok=True)
        raise ChannelError("bad_file", f"{file['name']} is not the file the manifest names (size or SHA-256 differs)")
    os.replace(part, target)
    return target
