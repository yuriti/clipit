"""The update channel's manifest for a release (stage 27), run by `.github/workflows/release.yml`:

    python scripts/release_manifest.py dist --version 0.2.0 --base-url https://github.com/<org>/smtv/releases/download/v0.2.0

Reads the wheels in `dist` (and, with --apps, the installers of the desktop apps, install/app/build.py), writes `dist/latest.json` (version, changes from CHANGELOG.md, the files of each kind of
install with their sizes and SHA-256 sums) and `dist/latest.json.sig`, its Ed25519 signature made with the private key
in the environment variable SMTV_UPDATE_SIGNING_KEY (base64 of the 32-byte seed; the release workflow's secret). SMTV
checks the signature with `channel.PUBLIC_KEY`. Without the key nothing is written: an unsigned manifest never leaves
the build machine. Make a new key pair (only when the old private key is lost or leaked; every SMTV out there then
needs a release with the new public key, signed with the old key while it is still trusted):

    python scripts/release_manifest.py --new-key
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "packages" / "smtv" / "src"))
from smtv import channel, ed25519  # noqa: E402 — from the source, so the release does not need SMTV installed

PACKAGES = ("smtv", "smtv-core", "vodcut")
KEY_ENV = "SMTV_UPDATE_SIGNING_KEY"


def changes(text: str, up_to: str) -> list[dict]:
    """`## <version>` sections of CHANGELOG.md, newest first, from `up_to` down: their `- ` lines as plain text."""
    out: list[dict] = []
    cur: dict | None = None
    started = False
    for line in text.splitlines():
        m = re.match(r"^## +v?(\d[\w.]*)", line)
        if m:
            started = started or m.group(1) == up_to
            cur = {"version": m.group(1), "notes": []} if started else None
            if cur:
                out.append(cur)
            continue
        if cur is None:
            continue
        s = line.strip()
        if s.startswith(("- ", "* ")):
            cur["notes"].append(_plain(s[2:]))
        elif s and not s.startswith("#") and cur["notes"] and line.startswith("  "):
            cur["notes"][-1] = f"{cur['notes'][-1]} {_plain(s)}"
    return out[:20]


def _plain(s: str) -> str:
    return re.sub(r"\*\*|`", "", s).strip()[:400]


# The desktop apps (install/app/build.py): kind, processor and file name of each installer in `dist`.
# One .dmg for every Mac (both processors inside: no `arch`), one installer for x64 Windows.
APPS = (("dmg", None, "SMTV-{v}-mac.dmg"), ("exe", "x64", "SMTV-{v}-windows-x64-setup.exe"))


def _file(path: Path, base_url: str, **extra) -> dict:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return {**extra, "name": path.name, "url": f"{base_url.rstrip('/')}/{path.name}", "size": path.stat().st_size,
            "sha256": h.hexdigest()}


def apps(dist: Path, version: str, base_url: str, required: bool) -> dict:
    """The installers of the desktop apps found in `dist`, by kind; with `required` every one of APPS must be there
    (a release never goes out with an app missing from the update channel while its file is on the page)."""
    kinds: dict = {}
    for kind, arch, pattern in APPS:
        path = dist / pattern.format(v=version)
        if not path.is_file():
            if required:
                raise SystemExit(f"{dist}: {path.name} is missing")
            continue
        kinds.setdefault(kind, {"files": []})["files"].append(_file(path, base_url, **({"arch": arch} if arch else {})))
    return kinds


def manifest(dist: Path, version: str, base_url: str, changelog: Path, with_apps: bool = False) -> dict:
    wheels = []
    for name in PACKAGES:
        found = sorted(dist.glob(f"{name.replace('-', '_')}-{version}-*.whl"))
        if len(found) != 1:
            raise SystemExit(f"{dist}: expected one wheel of {name} {version}, found {len(found)}")
        wheels.append(_file(found[0], base_url, package=name))
    return {
        "schema": 1, "version": version, "published": os.environ.get("SMTV_RELEASE_TIME", ""),
        "packages": {n: version for n in PACKAGES},
        "changes": changes(changelog.read_text(encoding="utf-8"), version),
        # uv and pip install the same wheels; the desktop apps (dmg, exe) open their installer
        "kinds": {"uv": {"files": wheels}, "pip": {"files": wheels}, **apps(dist, version, base_url, with_apps)},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("dist", nargs="?", type=Path)
    ap.add_argument("--version")
    ap.add_argument("--base-url", help="where the release's files are downloaded from")
    ap.add_argument("--changelog", type=Path, default=REPO / "CHANGELOG.md")
    ap.add_argument("--apps", action="store_true", help="the installers of the desktop apps must be in dist too")
    ap.add_argument("--new-key", action="store_true", help="print a new key pair and exit")
    ap.add_argument("--public-key", default=channel.PUBLIC_KEY, help=argparse.SUPPRESS)   # tests sign with their own pair
    a = ap.parse_args(argv)
    if a.new_key:
        seed = os.urandom(32)
        print(f"private (the secret {KEY_ENV}, nowhere else): {base64.b64encode(seed).decode()}")
        print(f"public (channel.PUBLIC_KEY): {base64.b64encode(ed25519.public_key(seed)).decode()}")
        return 0
    if not (a.dist and a.version and a.base_url):
        ap.error("dist, --version and --base-url are needed")
    raw_key = os.environ.get(KEY_ENV, "").strip()
    try:
        seed = base64.b64decode(raw_key, validate=True)
    except ValueError:
        seed = b""
    if len(seed) != 32:
        print(f"{KEY_ENV} is missing or is not base64 of 32 bytes: no manifest is written", file=sys.stderr)
        return 2
    if base64.b64encode(ed25519.public_key(seed)).decode() != a.public_key:
        print(f"{KEY_ENV} is not the key whose public half is in channel.PUBLIC_KEY: every SMTV would refuse this "
              "manifest. No manifest is written.", file=sys.stderr)
        return 2
    m = manifest(a.dist, a.version, a.base_url, a.changelog, a.apps)
    if not m["changes"] or not m["changes"][0]["notes"]:
        print(f"{a.changelog} has no «## {a.version}» section with «- » lines: no manifest is written", file=sys.stderr)
        return 2
    data = json.dumps(m, ensure_ascii=False, indent=1).encode("utf-8") + b"\n"
    signature = base64.b64encode(ed25519.sign(seed, data)) + b"\n"
    try:     # exactly what every SMTV will do with it: a manifest they would refuse never leaves the build machine
        channel.verify(data, signature, a.public_key)
        channel.parse(data, PACKAGES)
    except channel.ChannelError as e:
        print(f"the manifest would be refused by SMTV: {e}", file=sys.stderr)
        return 2
    (a.dist / "latest.json").write_bytes(data)
    (a.dist / "latest.json.sig").write_bytes(signature)
    print(f"{a.dist / 'latest.json'}: {a.version}, signed by {base64.b64encode(ed25519.public_key(seed)).decode()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
