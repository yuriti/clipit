"""Keys without a system keychain (stage 19): encrypted in a file, the encryption key in another file, both only for the
owner; read back after a restart; a changed byte or a wrong key file is refused; an older plain file is encrypted."""
import json
import os
import stat
import subprocess
import sys

import pytest

from smtv_core import paths, settings
from smtv_core.vault import Vault, VaultError

KEY = "sk-proj-THIS-IS-A-REAL-LOOKING-KEY-1234567890"


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    for key in list(os.environ):
        if key.startswith("SMTV_") and key != "SMTV_HOME":
            monkeypatch.delenv(key)
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)
    return tmp_path / "home"


def mode(path):
    return stat.S_IMODE(os.stat(path).st_mode)


def test_a_key_is_encrypted_in_its_file_and_the_encryption_key_is_apart():
    assert settings.set_secret("provider.openai", KEY) == "file"
    assert settings.secrets_backend() == "file"
    raw = paths.secrets_file().read_bytes()
    assert KEY.encode() not in raw and b"REAL-LOOKING" not in raw
    data = json.loads(raw)
    assert data["v"] == 1 and set(data["keys"]["provider.openai"]) == {"n", "c", "t"}
    assert paths.secrets_key_file().exists() and paths.secrets_key_file() != paths.secrets_file()
    assert len(paths.secrets_key_file().read_bytes()) == 32
    assert sys.platform == "win32" or mode(paths.secrets_file()) == mode(paths.secrets_key_file()) == 0o600   # no POSIX bits on Windows
    assert settings.get_secret("provider.openai") == KEY


def test_the_key_is_read_after_a_restart(isolated_home):
    settings.set_secret("provider.anthropic", KEY)
    # another process, as after closing and opening SMTV again
    code = ("import os; from smtv_core import settings; settings._keyring = lambda: None; "
            "print(settings.get_secret('provider.anthropic'))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env={**os.environ, "SMTV_HOME": str(isolated_home)}, check=True)
    assert out.stdout.strip() == KEY


def test_two_keys_one_encryption_key_and_each_nonce_fresh():
    settings.set_secret("a", KEY)
    settings.set_secret("b", KEY)
    entries = json.loads(paths.secrets_file().read_text(encoding="utf-8"))["keys"]
    assert entries["a"]["c"] != entries["b"]["c"] and entries["a"]["n"] != entries["b"]["n"]
    assert settings.get_secret("a") == settings.get_secret("b") == KEY


def test_a_changed_byte_a_moved_key_or_another_key_file_is_refused():
    settings.set_secret("a", KEY)
    settings.set_secret("b", "another-key-0000000")
    data = json.loads(paths.secrets_file().read_text(encoding="utf-8"))
    # one key's encrypted value put under another name: the tag binds the name
    data["keys"]["b"] = data["keys"]["a"]
    paths.secrets_file().write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(VaultError):
        settings.get_secret("b")
    # a changed byte
    c = bytearray(__import__("base64").b64decode(data["keys"]["a"]["c"]))
    c[0] ^= 1
    data["keys"]["a"]["c"] = __import__("base64").b64encode(bytes(c)).decode()
    paths.secrets_file().write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(VaultError):
        settings.get_secret("a")
    # the encryption key of another computer
    settings.set_secret("c", KEY)
    paths.secrets_key_file().write_bytes(os.urandom(32))
    with pytest.raises(VaultError):
        settings.get_secret("c")
    # no key file at all
    paths.secrets_key_file().unlink()
    with pytest.raises(VaultError, match="missing"):
        settings.get_secret("c")


def test_an_older_plain_file_is_encrypted_on_the_first_read():
    paths.home().mkdir(parents=True)
    paths.secrets_file().write_text(json.dumps({"openai_api_key": KEY, "phone_key": "phone-key-123456"}), encoding="utf-8")
    assert settings.get_secret("openai_api_key") == KEY
    raw = paths.secrets_file().read_text(encoding="utf-8")
    assert KEY not in raw and "phone-key-123456" not in raw
    assert settings.get_secret("phone_key") == "phone-key-123456"
    assert sys.platform == "win32" or mode(paths.secrets_file()) == 0o600


def test_delete_and_names():
    settings.set_secret("provider.x", KEY)
    settings.set_secret("provider.y", KEY)
    assert {"provider.x", "provider.y"} <= set(settings.secret_names())
    settings.delete_secret("provider.x")
    assert settings.get_secret("provider.x") is None and settings.get_secret("provider.y") == KEY
    settings.delete_secret("provider.never-saved")          # not an error


def test_nothing_is_written_until_a_key_is_saved(isolated_home):
    assert settings.get_secret("anything") is None
    assert not paths.secrets_key_file().exists() and not paths.secrets_file().exists()


def test_vault_round_trip_with_unicode(tmp_path):
    v = Vault(tmp_path / "s.json", tmp_path / "s.key")
    v.set("x", "ключ-🙂-" + KEY)
    assert Vault(tmp_path / "s.json", tmp_path / "s.key").get("x") == "ключ-🙂-" + KEY


def test_deleting_from_an_older_plain_file_really_deletes():
    paths.home().mkdir(parents=True)
    paths.secrets_file().write_text(json.dumps({"openai_api_key": KEY, "phone_key": "phone-key-123456"}), encoding="utf-8")
    settings.delete_secret("openai_api_key")
    assert settings.get_secret("openai_api_key") is None and settings.get_secret("phone_key") == "phone-key-123456"
    assert KEY not in paths.secrets_file().read_text(encoding="utf-8")


def test_keys_saved_from_many_threads_at_once_are_all_kept():
    import threading
    threads = [threading.Thread(target=settings.set_secret, args=(f"provider.p{i}", f"key-number-{i:04d}")) for i in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert [settings.get_secret(f"provider.p{i}") for i in range(12)] == [f"key-number-{i:04d}" for i in range(12)]


def test_keys_saved_from_two_processes_at_once_are_all_kept(tmp_path):
    """B20: a job refreshing the account's token while the window saves a key are two processes; a lock between threads
    alone lost one side's keys. Two processes, 50 saves each, start together: every name is there."""
    file, key_file, go = tmp_path / "secrets.json", tmp_path / "secrets.key", tmp_path / "go"
    code = ("import sys, time, pathlib\n"
            "from smtv_core.vault import Vault\n"
            "file, key_file, go, tag = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), pathlib.Path(sys.argv[3]), sys.argv[4]\n"
            "v = Vault(file, key_file)\n"
            "while not go.exists(): time.sleep(0.005)\n"
            "for i in range(50): v.set(f'{tag}{i}', f'value-{tag}-{i}')\n")
    ps = [subprocess.Popen([sys.executable, "-c", code, str(file), str(key_file), str(go), tag]) for tag in ("a", "b")]
    go.write_text("go", encoding="utf-8")
    assert [p.wait(60) for p in ps] == [0, 0]
    v = Vault(file, key_file)
    assert v.names() == sorted(f"{t}{i}" for t in "ab" for i in range(50))
    assert v.get("a7") == "value-a-7" and v.get("b49") == "value-b-49"      # one encryption key: made once, never raced
    assert (tmp_path / "run" / "secrets.json.lock").exists() and not list(tmp_path.glob("*.tmp"))


def test_a_keys_file_held_too_long_by_another_process_is_an_error_not_a_lost_key(tmp_path, monkeypatch):
    """A save never goes on without the lock: «try again» beats losing the other process's key."""
    from smtv_core import filelock
    file, key_file = tmp_path / "secrets.json", tmp_path / "secrets.key"
    held = filelock.file_lock(tmp_path / "run" / "secrets.json.lock")
    try:
        code = ("import sys, pathlib\nfrom smtv_core import vault\nvault._lock_of(pathlib.Path(sys.argv[1])).timeout = 0.3\n"
                "try:\n    vault.Vault(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])).set('a', 'b')\n"
                "except vault.VaultError as e:\n    print('refused:', e)\n")
        out = subprocess.run([sys.executable, "-c", code, str(file), str(key_file)], capture_output=True, text=True, timeout=30)
        assert "refused: secrets.json is busy in another Clip It! process" in out.stdout and not file.exists()
    finally:
        filelock.file_unlock(held)


def test_a_lock_that_cannot_work_here_is_said_at_once_not_waited_for(tmp_path, monkeypatch, capsys):
    import errno
    import fcntl
    from smtv_core import filelock
    monkeypatch.setattr(fcntl, "flock", lambda *a: (_ for _ in ()).throw(OSError(errno.ENOLCK, "no locks on this disk")))
    f = filelock.file_lock(tmp_path / "x.lock", "settings", timeout=30)
    f.close()
    assert "cannot be locked here" in capsys.readouterr().err
