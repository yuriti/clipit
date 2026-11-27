"""smtv_core.parts: the desktop app's Whisper engine, downloaded on first use from PyPI, checked, then offline."""
from __future__ import annotations

import hashlib
import io
import json
import sys
import zipfile

import pytest

from smtv_core import parts
from smtv_core.asr import catalog

HOST = "https://files.pythonhosted.org/packages/aa/bb/"


def wheel(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, body in files.items():
            z.writestr(name, body)
    return buf.getvalue()


class Net:
    """PyPI's file host in a dict; counts what was asked."""

    def __init__(self, files: dict[str, bytes]):
        self.files, self.asked = files, []

    def __call__(self, url, timeout):
        self.asked.append(url)
        return io.BytesIO(self.files[url])


def app_with(tmp_path, files: dict[str, bytes], wrong: dict | None = None):
    app = tmp_path / "app"
    app.mkdir(parents=True)
    wheels = []
    for i, (name, body) in enumerate(files.items()):
        url = HOST + name
        wheels.append({"name": f"p{i}", "version": "1.0", "url": url, "sha256": hashlib.sha256(body).hexdigest(),
                       "size": len(body), **(wrong or {})})
    (app / parts.MANIFEST).write_text(json.dumps({parts.WHISPER: {"wheels": wheels}}), encoding="utf-8")
    return app, Net({HOST + n: b for n, b in files.items()})


@pytest.fixture
def clean_path():
    before = list(sys.path)
    yield
    sys.path[:] = before


def test_a_part_is_downloaded_checked_unpacked_once_and_then_works_offline(tmp_path, clean_path):
    files = {"fakewhisper-1.0-py3-none-any.whl": wheel({"fakewhisper_x/__init__.py": b"VALUE = 42\n",
                                                        "fakewhisper-1.0.dist-info/METADATA": b"Name: fakewhisper\n"}),
             "fakeengine-2.0-cp312-cp312-win_amd64.whl": wheel({"fakeengine-2.0.data/platlib/fakeengine_x.py": b"N = 7\n",
                                                                "fakeengine-2.0.data/scripts/tool": b"#!/bin/sh\n"})}
    app, net = app_with(tmp_path, files)
    home = tmp_path / "home"
    assert parts.needed(parts.WHISPER, app, home) and not parts.activate(parts.WHISPER, app, home)
    seen = []
    where = parts.install(parts.WHISPER, lambda done, total: seen.append((done, total)), app, home, opener=net)
    assert parts.ready(parts.WHISPER, app, home) and not parts.needed(parts.WHISPER, app, home)
    assert (where / "fakewhisper_x" / "__init__.py").is_file() and (where / "fakeengine_x.py").is_file()
    assert not (where / "tool").exists() and not any(where.parent.glob(".whisper-*"))     # no scripts, no staging left
    assert seen[-1][0] == seen[-1][1]
    assert parts.activate(parts.WHISPER, app, home) and str(where) in sys.path
    import fakewhisper_x
    assert fakewhisper_x.VALUE == 42
    parts.install(parts.WHISPER, None, app, home, opener=net)          # already here: nothing fetched again
    assert len(net.asked) == 2


def test_a_wrong_file_never_becomes_a_part(tmp_path):
    files = {"x-1.0-py3-none-any.whl": wheel({"x_mod.py": b"1"})}
    app, net = app_with(tmp_path, files, wrong={"sha256": "0" * 64})
    with pytest.raises(ValueError, match="SHA-256"):
        parts.install(parts.WHISPER, None, app, tmp_path / "home", opener=net)
    assert not parts.ready(parts.WHISPER, app, tmp_path / "home")
    assert not [p for p in (tmp_path / "home" / "parts").iterdir()]        # nothing half-made stays
    app, net = app_with(tmp_path / "b", files, wrong={"size": 3})
    with pytest.raises(ValueError, match="more than the 3 bytes"):
        parts.install(parts.WHISPER, None, app, tmp_path / "home", opener=net)


def test_a_part_comes_only_from_pypis_file_host_and_never_writes_outside_its_folder(tmp_path):
    files = {"x-1.0-py3-none-any.whl": wheel({"x.py": b"1"})}
    app, net = app_with(tmp_path, files, wrong={"url": "https://example.org/x-1.0-py3-none-any.whl"})
    with pytest.raises(ValueError, match="files.pythonhosted.org only"):
        parts.install(parts.WHISPER, None, app, tmp_path / "home", opener=net)
    evil = {"e-1.0-py3-none-any.whl": wheel({"../../escaped.py": b"bad"})}
    app, net = app_with(tmp_path / "e", evil)
    with pytest.raises(ValueError, match="outside the folder"):
        parts.install(parts.WHISPER, None, app, tmp_path / "home", opener=net)
    assert not list(tmp_path.rglob("escaped.py"))


def test_a_new_app_with_other_versions_gets_a_new_folder_and_the_old_one_goes(tmp_path):
    home = tmp_path / "home"
    old_app, old_net = app_with(tmp_path / "old", {"x-1.0-py3-none-any.whl": wheel({"x.py": b"1"})})
    old = parts.install(parts.WHISPER, None, old_app, home, opener=old_net)
    new_app, new_net = app_with(tmp_path / "new", {"x-2.0-py3-none-any.whl": wheel({"x.py": b"2"})})
    new = parts.install(parts.WHISPER, None, new_app, home, opener=new_net)
    assert new != old and new.is_dir() and not old.exists()


def test_no_list_means_no_part_and_a_broken_list_is_no_list(tmp_path):
    assert parts.manifest(parts.WHISPER, tmp_path) is None and not parts.needed(parts.WHISPER, tmp_path)
    (tmp_path / parts.MANIFEST).write_text("{not json", encoding="utf-8")
    assert parts.manifest(parts.WHISPER, tmp_path) is None
    (tmp_path / parts.MANIFEST).write_text(json.dumps({parts.WHISPER: {"wheels": []}}), encoding="utf-8")
    assert parts.manifest(parts.WHISPER, tmp_path) is None
    with pytest.raises(ValueError, match="lists no part"):
        parts.install(parts.WHISPER, None, tmp_path, tmp_path / "home")


def test_whisper_says_how_much_more_comes_and_gets_it_before_use(tmp_path, monkeypatch, clean_path):
    files = {"fw-1.0-py3-none-any.whl": wheel({"fake_fw_pkg/__init__.py": b""})}
    app, net = app_with(tmp_path, files)
    monkeypatch.setattr(catalog.parts.paths, "app_folder", lambda prefix=None: app)
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(catalog.parts.urllib.request, "urlopen", net)
    model = catalog.SpeechModel(**{**catalog.WHISPER_M.__dict__, "package": "fake_fw_pkg"})
    assert not catalog.package_ready(model) and catalog.package_mb(model) == 1 and catalog.package_available(model)
    catalog.ensure_package(model)
    assert catalog.package_ready(model) and catalog.package_mb(model) == 0
    # an install from PyPI lists no part: its extras decide, as before
    monkeypatch.setattr(catalog.parts.paths, "app_folder", lambda prefix=None: tmp_path / "nowhere")
    missing = catalog.SpeechModel(**{**catalog.WHISPER_M.__dict__, "package": "no_such_pkg_here"})
    assert catalog.package_mb(missing) == 0 and not catalog.package_available(missing)
    with pytest.raises(RuntimeError, match="reinstall Clip It! with vodcut"):
        catalog.ensure_package(missing)
