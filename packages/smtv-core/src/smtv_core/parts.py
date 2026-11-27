"""Parts of the desktop app that come on first use: Whisper's engine (faster-whisper, CTranslate2, PyAV, tokenizers;
about 140 MB unpacked) is needed only for the ~70 languages GigaAM and Parakeet do not know, so the Windows app does
not carry it.

The app lists each part in `parts.json` in its own folder (`paths.app_folder()`, written by install/app/build.py):
the wheels at the versions of uv.lock with their size and SHA-256. The first use downloads them from PyPI's file host,
checks every size and hash, unpacks them into SMTV's folder (`parts/<name>-<hash of the list>`) and adds that folder to
`sys.path`; afterwards they work without the internet. A new app with other versions gets a new folder; the old one
goes once the new one is in. These are PyPI's own files, byte for byte: Smart App Control judges them as it judges the
same wheels installed by pip. An install from PyPI (pip, uv) has no `parts.json`: its extras decide, as before.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Callable

from . import paths

WHISPER = "whisper"
MANIFEST = "parts.json"
HOST = "files.pythonhosted.org"     # PyPI's file host: the only place a part is fetched from
DONE = ".complete"
TIMEOUT_S = 60
CHUNK = 1 << 20


def manifest(name: str, app: Path | None = None) -> dict | None:
    """The app's list for a part, or None (no list: not a desktop app, or the part is inside it)."""
    try:
        found = json.loads(((app or paths.app_folder()) / MANIFEST).read_text(encoding="utf-8")).get(name)
    except (OSError, ValueError, AttributeError):
        return None
    if not isinstance(found, dict) or not isinstance(found.get("wheels"), list) or not found["wheels"]:
        return None
    return found


def folder(name: str, spec: dict, home: Path | None = None) -> Path:
    key = hashlib.sha256(json.dumps(spec, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return (home or paths.home()) / "parts" / f"{name}-{key}"


def size_mb(spec: dict) -> int:
    return max(1, round(sum(int(w.get("size") or 0) for w in spec["wheels"]) / 1e6))


def ready(name: str, app: Path | None = None, home: Path | None = None) -> bool:
    spec = manifest(name, app)
    return spec is not None and (folder(name, spec, home) / DONE).is_file()


def needed(name: str, app: Path | None = None, home: Path | None = None) -> bool:
    """The app lists the part and it is not downloaded yet."""
    return manifest(name, app) is not None and not ready(name, app, home)


def activate(name: str, app: Path | None = None, home: Path | None = None) -> bool:
    """Puts a downloaded part on `sys.path` (once). False when it is not here."""
    spec = manifest(name, app)
    if spec is None:
        return False
    where = folder(name, spec, home)
    if not (where / DONE).is_file():
        return False
    if str(where) not in sys.path:
        sys.path.append(str(where))
    return True


def _check_url(url: str) -> None:
    u = urllib.parse.urlsplit(url)
    if u.scheme != "https" or u.hostname != HOST:
        raise ValueError(f"a part is fetched from https://{HOST} only, not {url[:120]}")


def _fetch(url: str, dest: Path, size: int, sha256: str, progress: Callable[[int], None], opener) -> None:
    _check_url(url)
    digest, got = hashlib.sha256(), 0
    with (opener or urllib.request.urlopen)(url, timeout=TIMEOUT_S) as r, open(dest, "wb") as out:
        while True:
            chunk = r.read(CHUNK)
            if not chunk:
                break
            got += len(chunk)
            if got > size:
                raise ValueError(f"{dest.name}: more than the {size} bytes the app lists")
            digest.update(chunk)
            out.write(chunk)
            progress(len(chunk))
    if got != size or digest.hexdigest() != sha256:
        raise ValueError(f"{dest.name}: not the file the app lists (size or SHA-256 differ): the download was "
                         "changed or cut short; try again")


def _unpack(wheel: Path, into: Path) -> None:
    """A wheel is a zip of the package as it sits in site-packages; `<dist>.data/purelib|platlib` go there too."""
    with zipfile.ZipFile(wheel) as z:
        for info in z.infolist():
            parts = PurePosixPath(info.filename).parts
            if not parts or info.filename.startswith("/") or ".." in parts or ":" in info.filename:
                raise ValueError(f"{wheel.name}: a path outside the folder ({info.filename[:80]})")
            if parts[0].endswith(".data"):
                if len(parts) < 3 or parts[1] not in ("purelib", "platlib"):
                    continue                     # scripts, headers, data: nothing SMTV runs
                parts = parts[2:]
            target = into.joinpath(*parts)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with z.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)


def install(name: str, progress: Callable[[int, int], None] | None = None, app: Path | None = None,
            home: Path | None = None, opener=None) -> Path:
    """Downloads, checks and unpacks a part; `progress(mb_done, mb_total)`. Two processes at once: the first to finish
    wins, the other's copy is dropped. Raises ValueError (a wrong file) or OSError (the network, the disk)."""
    spec = manifest(name, app)
    if spec is None:
        raise ValueError(f"this Clip It! lists no part {name!r}")
    where = folder(name, spec, home)
    if (where / DONE).is_file():
        return where
    total = sum(int(w["size"]) for w in spec["wheels"])
    done = [0]

    def step(n: int) -> None:
        done[0] += n
        if progress:
            progress(round(done[0] / 1e6), round(total / 1e6))

    where.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{name}-", dir=where.parent))
    try:
        for w in spec["wheels"]:
            wheel = staging / PurePosixPath(urllib.parse.urlsplit(w["url"]).path).name
            _fetch(w["url"], wheel, int(w["size"]), str(w["sha256"]), step, opener)
            _unpack(wheel, staging / "site")
            wheel.unlink()
        (staging / "site" / DONE).write_text(json.dumps(spec, sort_keys=True), encoding="utf-8")
        try:
            (staging / "site").replace(where)
        except OSError:
            if not (where / DONE).is_file():     # not another process's finished copy: a real failure
                raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    for old in where.parent.glob(f"{name}-*"):   # an older app's versions
        if old != where and old.is_dir():
            shutil.rmtree(old, ignore_errors=True)
    return where
