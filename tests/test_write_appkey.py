"""scripts/write_appkey.py: the key is written from the environment, and a build without it fails the release."""
import importlib.util
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("write_appkey", ROOT / "scripts" / "write_appkey.py")
write_appkey = importlib.util.module_from_spec(spec)
spec.loader.exec_module(write_appkey)


def wheel(folder: Path, key: str | None) -> None:
    with zipfile.ZipFile(folder / "smtv_core-0.2.0-py3-none-any.whl", "w") as z:
        z.writestr("smtv_core/__init__.py", "")
        if key is not None:
            z.writestr("smtv_core/_appkey.py", f'KEY = "{key}"\n')


def test_a_wheel_with_the_key_passes_and_one_without_fails(tmp_path, capsys):
    wheel(tmp_path, "abc123")
    assert write_appkey.verify(tmp_path) == 0
    wheel(tmp_path, None)
    assert write_appkey.verify(tmp_path) == 1 and "without the app key" in capsys.readouterr().err
    wheel(tmp_path, "")
    assert write_appkey.verify(tmp_path) == 1, "an empty key is no key"


def test_an_sdist_without_the_key_fails(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "x.py").write_text("")
    with tarfile.open(tmp_path / "smtv_core-0.2.0.tar.gz", "w:gz") as t:
        t.add(src / "x.py", "smtv_core-0.2.0/src/smtv_core/__init__.py")
    assert write_appkey.verify(tmp_path) == 1


def test_nothing_to_check_fails(tmp_path):
    assert write_appkey.verify(tmp_path) == 1


def test_no_key_stops_the_build_unless_optional(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("SMTV_APP_KEY", raising=False)
    monkeypatch.setattr(write_appkey, "TARGET", tmp_path / "_appkey.py")
    assert write_appkey.main([]) == 1 and not (tmp_path / "_appkey.py").exists()
    assert write_appkey.main(["--optional"]) == 0 and "WARNING" in capsys.readouterr().err
    monkeypatch.setenv("SMTV_APP_KEY", "k-1")
    assert write_appkey.main([]) == 0
    assert (tmp_path / "_appkey.py").read_text().endswith('KEY = "k-1"\n')
