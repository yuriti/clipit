"""Stage 27: the update channel. latest.json is signed with Ed25519; SMTV believes only a manifest signed by the key in its
code, never goes back to an older one, and installs only files whose size and SHA-256 are the manifest's. A test key
pair is made here for each run: the real private key lives only in the release workflow's secrets."""
import base64
import hashlib
import io
import json
import os
import socket
import sys
import urllib.error
from pathlib import Path

import pytest

from smtv import channel, ed25519, updates

REPO = Path(__file__).resolve().parents[3]
ALLOWED = ("smtv", "smtv-core", "vodcut")
WHEEL = b"PK\x03\x04 a wheel's bytes"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("SMTV_UPDATE_URL", raising=False)


@pytest.fixture(scope="module")
def keys():
    secret = os.urandom(32)
    return secret, base64.b64encode(ed25519.public_key(secret)).decode()


def manifest(version="0.2.0", **over) -> dict:
    files = [{"package": "smtv", "name": f"smtv-{version}-py3-none-any.whl", "size": len(WHEEL),
              "sha256": hashlib.sha256(WHEEL).hexdigest(),
              "url": f"https://github.com/yuriti/clipit/releases/download/v{version}/smtv-{version}-py3-none-any.whl"}]
    return {"schema": 1, "version": version, "published": "2026-12-01T10:00:00Z",
            "packages": {"smtv": version, "smtv-core": version, "vodcut": version},
            "changes": [{"version": version, "notes": ["Faster clips"]}], "kinds": {"uv": {"files": files}, "pip": {"files": files}}, **over}


def signed(data: dict, secret: bytes) -> tuple[bytes, bytes]:
    raw = json.dumps(data).encode()
    return raw, base64.b64encode(ed25519.sign(secret, raw))


class Host:
    """urlopen in place of GitHub: url → bytes, or an exception to raise."""

    def __init__(self, pages: dict):
        self.pages, self.asked = pages, []

    def __call__(self, req, timeout=None):
        self.asked.append(req.full_url)
        page = self.pages.get(req.full_url)
        if page is None:
            raise urllib.error.HTTPError(req.full_url, 404, "Not Found", {}, None)
        if isinstance(page, BaseException):
            raise page
        return io.BytesIO(page)


def host_for(data: dict, secret: bytes, url=channel.URL, sig: bytes | None = None) -> Host:
    raw, signature = signed(data, secret)
    return Host({url: raw, url + ".sig": signature if sig is None else sig})


# --- the signature ----------------------------------------------------------------------------------------------------

def test_ed25519_matches_the_rfc_8032_test_vectors():
    secret = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
    assert ed25519.public_key(secret).hex() == "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    sig = ed25519.sign(secret, b"")
    assert sig.hex() == ("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd2"
                         "5bf5f0595bbe24655141438e7a100b")
    secret = bytes.fromhex("c5aa8df43f9f837bedb7442f31dcb7b166d38535076f094b85ce3a2e0b4458f7")
    assert ed25519.sign(secret, bytes.fromhex("af82")).hex().startswith("6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac")
    assert ed25519.verify(ed25519.public_key(secret), bytes.fromhex("af82"), ed25519.sign(secret, bytes.fromhex("af82")))


def test_a_manifest_signed_by_our_key_is_accepted(keys):
    secret, public = keys
    found = channel.load(ALLOWED, opener=host_for(manifest(), secret), key=public)
    assert found["version"] == "0.2.0" and found["packages"]["vodcut"] == "0.2.0"
    assert found["changes"] == [{"version": "0.2.0", "notes": ["Faster clips"]}]
    assert found["kinds"]["uv"]["files"][0]["package"] == "smtv"


@pytest.mark.parametrize("tamper", ["other_key", "changed_byte", "garbage", "empty", "missing"])
def test_a_wrong_or_missing_signature_is_refused(keys, tamper):
    secret, public = keys
    raw, sig = signed(manifest(), secret)
    pages = {channel.URL: raw, channel.URL + ".sig": sig}
    if tamper == "other_key":
        pages = dict(zip(pages, signed(manifest(), os.urandom(32))))
    elif tamper == "changed_byte":       # one version number changed after signing: the classic attack
        pages[channel.URL] = raw.replace(b'"0.2.0"', b'"9.2.0"', 1)
    elif tamper == "garbage":
        pages[channel.URL + ".sig"] = b"not base64 at all!"
    elif tamper == "empty":
        pages[channel.URL + ".sig"] = b""
    else:
        del pages[channel.URL + ".sig"]
    with pytest.raises(channel.ChannelError) as e:
        channel.load(ALLOWED, opener=Host(pages), key=public)
    assert e.value.code == ("no_signature" if tamper == "missing" else "bad_signature")


def test_the_public_key_in_the_code_is_a_real_key_and_not_a_test_one():
    raw = base64.b64decode(channel.PUBLIC_KEY, validate=True)
    assert len(raw) == 32 and ed25519._decompress(raw) is not None
    assert channel.URL.startswith("https://github.com/yuriti/clipit/releases/")


# --- going back ---------------------------------------------------------------------------------------------------------

def test_an_older_manifest_than_one_already_accepted_is_refused(keys):
    """A mirror that fell behind, or someone serving last month's manifest to hold back a security fix."""
    secret, public = keys
    with pytest.raises(channel.ChannelError) as e:
        channel.load(ALLOWED, floor="0.3.0", opener=host_for(manifest("0.2.0"), secret), key=public)
    assert e.value.code == "old_manifest"
    assert channel.load(ALLOWED, floor="0.2.0", opener=host_for(manifest("0.2.0"), secret), key=public)["version"] == "0.2.0"


def test_updates_remember_the_newest_manifest_and_never_offer_an_older_version(keys, monkeypatch):
    secret, public = keys
    names = {"smtv": "0.2.0", "smtv-core": "0.2.0", "vodcut": "0.2.0"}
    monkeypatch.setattr(updates, "version_of", lambda n: names.get(n))
    served = {"m": manifest("0.3.0")}
    u = updates.Updates(tools=lambda: ["vodcut"], running=lambda: 0, stop_jobs=lambda: None, port=lambda: 8650, kind="uv",
                        manifest=lambda floor: channel.load(ALLOWED, floor, opener=host_for(served["m"], secret), key=public),
                        spawn=lambda plan: 1)
    assert u.check()["available"]["version"] == "0.3.0"
    served["m"] = manifest("0.2.1")              # an old one served again
    s = u.check()
    assert "old_manifest" in s["error"] and s["available"]["version"] == "0.3.0"
    assert json.loads(updates.cache_file().read_text(encoding="utf-8"))[channel.VERSION_KEY] == "0.3.0"
    # a fresh start reads the floor from disk: the old manifest is still refused
    u2 = updates.Updates(tools=lambda: ["vodcut"], running=lambda: 0, stop_jobs=lambda: None, port=lambda: 8650, kind="uv",
                         manifest=u.manifest, spawn=lambda plan: 1)
    assert "old_manifest" in u2.check()["error"]
    # a manifest below the installed version is never an update
    names.update({"smtv": "0.4.0", "smtv-core": "0.4.0", "vodcut": "0.4.0"})
    served["m"] = manifest("0.3.0")
    assert u.check()["available"] is None


# --- no network ---------------------------------------------------------------------------------------------------------

def test_no_network_is_said_and_nothing_changes(keys, monkeypatch):
    secret, public = keys
    down = Host({channel.URL: urllib.error.URLError(socket.gaierror(8, "nodename nor servname provided"))})
    with pytest.raises(channel.ChannelError) as e:
        channel.load(ALLOWED, opener=down, key=public)
    assert e.value.code == "unreachable"
    slow = Host({channel.URL: TimeoutError("timed out")})
    with pytest.raises(channel.ChannelError) as e:
        channel.load(ALLOWED, opener=slow, key=public)
    assert e.value.code == "unreachable"
    nothing = Host({})                                           # no release yet: 404
    with pytest.raises(channel.ChannelError) as e:
        channel.load(ALLOWED, opener=nothing, key=public)
    assert e.value.code == "not_found"


def test_a_closed_port_is_unreachable_not_a_crash(keys, monkeypatch):
    secret, public = keys
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    monkeypatch.setenv("SMTV_UPDATE_URL", f"http://127.0.0.1:{port}/latest.json")
    with pytest.raises(channel.ChannelError) as e:
        channel.load(ALLOWED, key=public)
    assert e.value.code == "unreachable"


# --- the manifest's contents ------------------------------------------------------------------------------------------

@pytest.mark.parametrize("change, why", [
    ({"schema": 2}, "schema"),
    ({"version": "0.2.0; rm -rf ~"}, "version"),
    ({"packages": {"smtv": "0.2.0", "requests": "0.2.0"}}, "requests"),
    ({"packages": {"smtv": "0.2.0", "vodcut": "0.1.0"}}, "vodcut"),          # one number for all (decision 9)
    ({"kinds": {"brew": {"files": []}}}, "brew"),
    ({"kinds": {"uv": {"files": [{"package": "smtv", "name": "../../.bashrc", "url": "https://github.com/a", "size": 1, "sha256": "0" * 64}]}}}, "name"),
    ({"kinds": {"uv": {"files": [{"package": "smtv", "name": "a.whl", "url": "https://evil.example/a.whl", "size": 1, "sha256": "0" * 64}]}}}, "address"),
    ({"kinds": {"uv": {"files": [{"package": "smtv", "name": "a.whl", "url": "http://github.com/a.whl", "size": 1, "sha256": "0" * 64}]}}}, "address"),
    ({"kinds": {"uv": {"files": [{"package": "smtv", "name": "a.whl", "url": "https://github.com/a.whl", "size": 1, "sha256": "abc"}]}}}, "sha256"),
    ({"kinds": {"uv": {"files": [{"package": "smtv", "name": "a.whl", "url": "https://github.com/a.whl", "size": True, "sha256": "0" * 64}]}}}, "size"),
    ({"changes": [{"version": "9.9.9", "notes": ["from the future"]}]}, "changes"),
])
def test_a_malformed_manifest_is_refused_even_when_signed(keys, change, why):
    secret, public = keys
    with pytest.raises(channel.ChannelError) as e:
        channel.load(ALLOWED, opener=host_for(manifest(**change), secret), key=public)
    assert e.value.code == "malformed" and why in e.value.message


def test_the_test_channel_is_https_or_this_computer_only(monkeypatch):
    assert channel.manifest_url() == channel.URL
    for ok in ("https://mirror.example/latest.json", "http://127.0.0.1:9100/latest.json"):
        monkeypatch.setenv("SMTV_UPDATE_URL", ok)
        assert channel.manifest_url() == ok
    for bad in ("http://evil.example/latest.json", "file:///tmp/latest.json", "ftp://127.0.0.1/x"):
        monkeypatch.setenv("SMTV_UPDATE_URL", bad)
        with pytest.raises(ValueError):
            channel.manifest_url()


# --- the files ----------------------------------------------------------------------------------------------------------

def test_a_file_is_kept_only_when_it_is_the_manifests_file(tmp_path):
    f = channel.parse(json.dumps(manifest()).encode(), ALLOWED)["kinds"]["uv"]["files"][0]
    got = channel.download(f, tmp_path, opener=Host({f["url"]: WHEEL}))
    assert got.read_bytes() == WHEEL and got.name == f["name"]


@pytest.mark.parametrize("served", [WHEEL.replace(b"wheel", b"whEEl"), WHEEL + b"x", WHEEL[:-1], WHEEL * 1000])
def test_a_swapped_file_is_refused_and_deleted(tmp_path, served):
    f = channel.parse(json.dumps(manifest()).encode(), ALLOWED)["kinds"]["uv"]["files"][0]
    with pytest.raises(channel.ChannelError) as e:
        channel.download(f, tmp_path, opener=Host({f["url"]: served}))
    assert e.value.code == "bad_file" and list(tmp_path.iterdir()) == []


def test_a_swapped_wheel_stops_the_update_before_anything_is_installed(keys, monkeypatch):
    secret, public = keys
    names = {"smtv": "0.1.0", "smtv-core": "0.1.0", "vodcut": "0.1.0"}
    monkeypatch.setattr(updates, "version_of", lambda n: names.get(n))
    m = manifest()
    m["kinds"]["uv"]["files"] = [{**m["kinds"]["uv"]["files"][0], "package": n, "name": f"{n.replace('-', '_')}-0.2.0-py3-none-any.whl",
                                  "url": f"https://github.com/yuriti/clipit/releases/download/v0.2.0/{n}.whl"} for n in ALLOWED]
    pages = {f["url"]: WHEEL for f in m["kinds"]["uv"]["files"]}
    pages[m["kinds"]["uv"]["files"][2]["url"]] = b"someone else's vodcut"
    host = Host(pages)
    spawned = []
    u = updates.Updates(tools=lambda: ["vodcut"], running=lambda: 0, stop_jobs=lambda: None, port=lambda: 8650, kind="uv",
                        manifest=lambda floor: channel.load(ALLOWED, floor, opener=host_for(m, secret), key=public),
                        download=lambda files, folder: [channel.download(f, folder, opener=host) for f in files],
                        spawn=spawned.append)
    assert u.check()["available"]["version"] == "0.2.0"
    with pytest.raises(updates.UpdateError) as e:
        u.ask("update")
    assert "bad_file" in e.value.message or "SHA-256" in e.value.message
    assert spawned == [] and not u.leaving                                       # SMTV stays as it is
    # with the right files the updater gets a plan that installs exactly them
    pages[m["kinds"]["uv"]["files"][2]["url"]] = WHEEL
    u.ask("update")
    [plan] = spawned
    folder = updates.paths.home() / "run" / "update-files" / "0.2.0"
    assert f"smtv[vodcut] @ {(folder / 'smtv-0.2.0-py3-none-any.whl').resolve().as_uri()}" in plan.steps[0]
    assert all((folder / f["name"]).read_bytes() == WHEEL for f in m["kinds"]["uv"]["files"])


# --- each kind of install its own way -----------------------------------------------------------------------------------

def test_each_kind_of_install_takes_its_own_files():
    m = channel.parse(json.dumps(manifest(kinds={
        "uv": manifest()["kinds"]["uv"],
        "dmg": {"files": [{"name": "SMTV-0.2.0.dmg", "url": "https://github.com/a/SMTV-0.2.0.dmg", "size": 9, "sha256": "1" * 64}]},
        "exe": {"files": [{"name": "SMTV-0.2.0-setup.exe", "url": "https://github.com/a/s.exe", "size": 9, "sha256": "2" * 64}]},
    })).encode(), ALLOWED)
    assert [f["name"] for f in channel.files_for(m, "uv", ["smtv"])] == ["smtv-0.2.0-py3-none-any.whl"]
    assert [f["name"] for f in channel.files_for(m, "dmg")] == ["SMTV-0.2.0.dmg"]
    assert [f["name"] for f in channel.files_for(m, "exe")] == ["SMTV-0.2.0-setup.exe"]
    for kind, packages in (("uv", ["vodcut"]), ("pip", ["smtv"]), ("docker", None)):    # nothing for them in this manifest
        with pytest.raises(channel.ChannelError) as e:
            channel.files_for(m, kind, packages)
        assert e.value.code == "not_for_this_install"
    assert channel.METHOD == {"uv": "packages", "pip": "packages", "docker": "command", "dmg": "installer", "exe": "installer"}


def test_a_desktop_app_knows_its_kind_from_its_marker(tmp_path, monkeypatch):
    monkeypatch.setattr(updates.sys, "prefix", str(tmp_path))
    monkeypatch.delenv("SMTV_DOCKER", raising=False)
    (tmp_path / updates.KIND_MARKER).write_text("dmg\n", encoding="utf-8")
    assert updates.install_kind() == "dmg"
    (tmp_path / updates.KIND_MARKER).write_text("anything else", encoding="utf-8")
    assert updates.install_kind() != "anything else"
    monkeypatch.setenv("SMTV_DOCKER", "1")
    assert updates.install_kind() == "docker"


# --- the release side ---------------------------------------------------------------------------------------------------

def test_the_release_script_builds_a_manifest_that_smtv_accepts(tmp_path, keys, monkeypatch):
    secret, public = keys
    dist = tmp_path / "dist"
    dist.mkdir()
    for n in ("smtv", "smtv_core", "vodcut"):
        (dist / f"{n}-0.2.0-py3-none-any.whl").write_bytes(WHEEL + n.encode())
        (dist / f"{n}-0.2.0.tar.gz").write_bytes(b"sdist")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n## 0.2.0\n\n- Faster clips\n- A new step\n\n## 0.1.0\n\n- First\n", encoding="utf-8")
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import release_manifest
    finally:
        sys.path.remove(str(REPO / "scripts"))
    monkeypatch.setenv("SMTV_UPDATE_SIGNING_KEY", base64.b64encode(secret).decode())
    args = [str(dist), "--version", "0.2.0", "--changelog", str(changelog), "--public-key", public,
            "--base-url", "https://github.com/yuriti/clipit/releases/download/v0.2.0"]
    # a key that is not the one in SMTV's code: every SMTV would refuse it, so nothing is written
    assert release_manifest.main(args[:-4] + args[-2:]) != 0 and not (dist / "latest.json").exists()
    # a version the changelog does not describe: no release without its changes
    bare = tmp_path / "BARE.md"
    bare.write_text("# Changelog\n\n## 0.1.0\n\n- First\n", encoding="utf-8")
    assert release_manifest.main([*args[:4], str(bare), *args[5:]]) != 0 and not (dist / "latest.json").exists()
    assert release_manifest.main(args) == 0
    raw = (dist / "latest.json").read_bytes()
    channel.verify(raw, (dist / "latest.json.sig").read_bytes(), public)
    m = channel.parse(raw, ALLOWED)
    assert m["packages"] == {"smtv": "0.2.0", "smtv-core": "0.2.0", "vodcut": "0.2.0"}
    assert m["changes"] == [{"version": "0.2.0", "notes": ["Faster clips", "A new step"]}, {"version": "0.1.0", "notes": ["First"]}]
    wheels = channel.files_for(m, "uv", list(ALLOWED))
    assert [w["sha256"] for w in wheels] == [hashlib.sha256((dist / w["name"]).read_bytes()).hexdigest() for w in wheels]
    assert channel.files_for(m, "pip", ["vodcut"]) == [wheels[2]]
    # without the key nothing is written: an unsigned manifest never leaves the build machine
    monkeypatch.delenv("SMTV_UPDATE_SIGNING_KEY")
    (dist / "latest.json").unlink()
    assert release_manifest.main(args) != 0
    assert not (dist / "latest.json").exists()


def test_a_desktop_app_updates_by_its_checked_installer_and_docker_only_hears_of_it(keys, monkeypatch):
    secret, public = keys
    names = {"smtv": "0.1.0", "smtv-core": "0.1.0", "vodcut": "0.1.0"}
    monkeypatch.setattr(updates, "version_of", lambda n: names.get(n))
    dmg = b"a disk image"
    m = manifest(kinds={"dmg": {"files": [{"name": "SMTV-0.2.0.dmg", "url": "https://github.com/a/SMTV-0.2.0.dmg",
                                           "size": len(dmg), "sha256": hashlib.sha256(dmg).hexdigest()}]}})
    opened, spawned = [], []
    load = lambda floor: channel.load(ALLOWED, floor, opener=host_for(m, secret), key=public)  # noqa: E731
    u = updates.Updates(tools=lambda: ["vodcut"], running=lambda: 0, stop_jobs=lambda: None, port=lambda: 8650, kind="dmg",
                        manifest=load, open_file=opened.append, spawn=spawned.append,
                        download=lambda files, folder: [channel.download(f, folder, opener=Host({"https://github.com/a/SMTV-0.2.0.dmg": dmg})) for f in files])
    assert u.check()["available"]["version"] == "0.2.0"
    with pytest.raises(updates.UpdateError) as e:                     # plugins come inside the app, not one by one
        u.ask("install", "vodcut")
    assert e.value.code == "cannot_update"
    u.ask("update")
    assert spawned == [] and len(opened) == 1 and Path(opened[0]).read_bytes() == dmg and u.leaving
    # Docker: told about the new version, never changes itself
    d = updates.Updates(tools=lambda: ["vodcut"], running=lambda: 0, stop_jobs=lambda: None, port=lambda: 8650, kind="docker",
                        manifest=load, spawn=spawned.append)
    assert d.check()["available"]["version"] == "0.2.0"
    with pytest.raises(updates.UpdateError) as e:
        d.ask("update")
    assert e.value.code == "cannot_update" and spawned == []


def test_the_release_names_every_package_smtv_updates():
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import release_manifest
    finally:
        sys.path.remove(str(REPO / "scripts"))
    assert set(release_manifest.PACKAGES) == set(updates.allowed_packages())


def test_ed25519_refuses_odd_signatures_and_keys(keys):
    secret, public = keys
    pk, sig = base64.b64decode(public), ed25519.sign(secret, b"m")
    assert ed25519.verify(pk, b"m", sig)
    big_s = sig[:32] + int.to_bytes(int.from_bytes(sig[32:], "little") + ed25519._Q, 32, "little")   # the same point, S ≥ L
    assert not ed25519.verify(pk, b"m", big_s)
    assert not ed25519.verify(pk, b"m", sig[:63]) and not ed25519.verify(pk, b"m", sig + b"\0")
    assert not ed25519.verify(b"\xff" * 32, b"m", sig) and not ed25519.verify(pk[:31], b"m", sig)


def test_a_mirror_may_serve_its_own_files_but_no_other_hosts(keys):
    m = manifest()
    m["kinds"]["uv"]["files"][0]["url"] = "https://mirror.example/smtv.whl"
    raw = json.dumps(m).encode()
    assert channel.parse(raw, ALLOWED, "mirror.example")["kinds"]["uv"]["files"][0]["url"] == "https://mirror.example/smtv.whl"
    with pytest.raises(channel.ChannelError):
        channel.parse(raw, ALLOWED, "other.example")


def test_a_cut_connection_and_a_full_disk_are_told_apart(tmp_path, monkeypatch):
    import http.client
    f = channel.parse(json.dumps(manifest()).encode(), ALLOWED)["kinds"]["uv"]["files"][0]

    class Cut(io.BytesIO):
        def read(self, n=-1):
            raise http.client.IncompleteRead(b"x")
    with pytest.raises(channel.ChannelError) as e:
        channel.download(f, tmp_path, opener=lambda req, timeout=None: Cut())
    assert e.value.code == "unreachable" and list(tmp_path.iterdir()) == []
    with pytest.raises(channel.ChannelError) as e:
        channel.load(ALLOWED, opener=lambda req, timeout=None: Cut())
    assert e.value.code == "unreachable"
    real_open = open

    class Full:
        def __init__(self, *a, **k):
            self.f = real_open(*a, **k)
        def write(self, b):
            raise OSError(28, "No space left on device")
        def __enter__(self):
            return self
        def __exit__(self, *a):
            self.f.close()
    monkeypatch.setattr("builtins.open", Full)
    with pytest.raises(channel.ChannelError) as e:
        channel.download(f, tmp_path, opener=Host({f["url"]: WHEEL}))
    monkeypatch.undo()
    assert e.value.code == "disk" and not list(tmp_path.glob("*.part"))


def test_old_update_files_are_removed_and_the_current_kept(tmp_path):
    root = updates.paths.home() / "run" / "update-files"
    (root / "0.1.0").mkdir(parents=True)
    (root / "0.2.0").mkdir()
    (root / "0.2.0" / "a.whl").write_bytes(b"x")
    assert updates.update_files_folder("0.2.0") == root / "0.2.0"
    assert sorted(p.name for p in root.iterdir()) == ["0.2.0"] and (root / "0.2.0" / "a.whl").exists()


def test_an_installer_that_does_not_open_leaves_smtv_as_it_is_and_says_why(keys, monkeypatch):
    secret, public = keys
    names = {"smtv": "0.1.0", "smtv-core": "0.1.0"}
    monkeypatch.setattr(updates, "version_of", lambda n: names.get(n))
    dmg = b"img"
    m = manifest(kinds={"exe": {"files": [{"name": "s.exe", "url": "https://github.com/a/s.exe", "size": 3, "sha256": hashlib.sha256(dmg).hexdigest()}]}})

    def refuse(path):
        raise OSError("an installer opens only on macOS and Windows")
    u = updates.Updates(tools=lambda: [], running=lambda: 0, stop_jobs=lambda: None, port=lambda: 8650, kind="exe",
                        manifest=lambda floor: channel.load(ALLOWED, floor, opener=host_for(m, secret), key=public),
                        download=lambda files, folder: [channel.download(f, folder, opener=Host({"https://github.com/a/s.exe": dmg})) for f in files],
                        open_file=refuse)
    quits = []
    u.quit = lambda: quits.append(1)
    u.check()
    with pytest.raises(updates.UpdateError):
        u.ask("update")
    st = u.state()
    assert not u.leaving and quits == [] and "installer opens only" in st["error"]
    m["kinds"]["exe"]["files"][0]["sha256"] = "0" * 64           # a swapped installer: said in plain words' code
    u.check()
    with pytest.raises(updates.UpdateError):
        u.ask("update")
    assert u.state()["error"].startswith("bad_file:")


@pytest.mark.parametrize("kind, cpu, want", [("dmg", "x64", "SMTV-0.2.0-mac-x64.dmg"), ("dmg", "arm64", "SMTV-0.2.0-mac-arm64.dmg"),
                                             ("exe", "x64", "SMTV-0.2.0-windows-x64-setup.exe"),
                                             ("exe", "arm64", "SMTV-0.2.0-windows-x64-setup.exe")])   # Windows on ARM emulates x64
def test_a_desktop_app_update_opens_the_installer_of_this_processor(kind, cpu, want, keys, monkeypatch):
    """B11: two .dmg (Apple Silicon, Intel) in one manifest; the window's update, without being told, takes this computer's."""
    secret, public = keys
    monkeypatch.setattr(updates, "version_of", lambda n: {"smtv": "0.1.0", "smtv-core": "0.1.0", "vodcut": "0.1.0"}.get(n))
    monkeypatch.setattr(channel, "machine", lambda: cpu)
    names = {"dmg": [("SMTV-0.2.0-mac-arm64.dmg", "arm64"), ("SMTV-0.2.0-mac-x64.dmg", "x64")],
             "exe": [("SMTV-0.2.0-windows-x64-setup.exe", "x64")]}[kind]
    served = {f"https://github.com/a/{n}": n.encode() for n, _ in names}
    files = [{"name": n, "arch": a, "url": f"https://github.com/a/{n}", "size": len(n), "sha256": hashlib.sha256(n.encode()).hexdigest()}
             for n, a in names]
    m = manifest(kinds={kind: {"files": files}})
    opened = []
    u = updates.Updates(tools=lambda: ["vodcut"], running=lambda: 0, stop_jobs=lambda: None, port=lambda: 8650, kind=kind,
                        manifest=lambda floor: channel.load(ALLOWED, floor, opener=host_for(m, secret), key=public),
                        open_file=opened.append, spawn=lambda plan: None,
                        download=lambda fs, folder: [channel.download(f, folder, opener=Host(served)) for f in fs])
    assert u.check()["available"]["version"] == "0.2.0"
    u.ask("update")
    assert len(opened) == 1 and Path(opened[0]).name == want and Path(opened[0]).read_bytes() == want.encode()


def test_installers_without_a_processor_fit_every_computer(monkeypatch):
    monkeypatch.setattr(channel, "machine", lambda: "arm64")
    plain = {"name": "SMTV-0.2.0.dmg", "url": "https://github.com/a/x", "size": 1, "sha256": "0" * 64, "package": None, "arch": None}
    assert channel.files_for({"kinds": {"dmg": {"files": [plain]}}}, "dmg") == [plain]
    intel = {**plain, "name": "SMTV-0.2.0-mac-x64.dmg", "arch": "x64"}
    assert channel.files_for({"kinds": {"dmg": {"files": [intel, plain]}}}, "dmg") == [plain]


@pytest.mark.parametrize("junk", ["uv", "", "dmg-ish", "pip"])
def test_a_marker_with_anything_else_is_ignored_and_said(junk, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(updates.sys, "prefix", str(tmp_path))
    monkeypatch.delenv("SMTV_DOCKER", raising=False)
    (tmp_path / updates.KIND_MARKER).write_text(junk, encoding="utf-8")
    assert updates.install_kind() not in updates.APP_KINDS
    assert "ignored" in capsys.readouterr().err
