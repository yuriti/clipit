"""В3, after the review of the fixes: a connection that drops after the request was sent is not paid for twice (B2,
decision 3); a settings file that cannot be opened for a moment is not taken for a broken one (A8)."""
import json
import socket
import threading

import pytest

from smtv_core import settings as settings_mod
from smtv_core.llm import providers
from smtv_core.settings import Settings


def _server_that_reads_and_hangs_up():
    """A real socket: reads the whole request, then closes without an answer (RemoteDisconnected in urllib)."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(5)
    accepted = []

    def serve():
        while True:
            try:
                conn, _ = srv.accept()
            except OSError:
                return
            accepted.append(1)
            conn.recv(65536)
            conn.close()

    threading.Thread(target=serve, daemon=True).start()
    return srv, accepted


def test_a_dropped_connection_after_sending_is_not_paid_again(monkeypatch):
    monkeypatch.setattr(providers.time, "sleep", lambda s: None)
    srv, accepted = _server_that_reads_and_hangs_up()
    try:
        with pytest.raises(providers.Overloaded, match="does not ask again"):
            providers._post(f"http://127.0.0.1:{srv.getsockname()[1]}/v1/x", {"a": 1}, {}, 10)
    finally:
        srv.close()
    assert len(accepted) == 1


def test_a_file_that_cannot_be_read_right_now_is_not_set_aside(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"tools": {"x": {"a": 1}}}), encoding="utf-8")
    monkeypatch.setattr(settings_mod.time, "sleep", lambda s: None)
    real = type(path).read_text

    def busy(self, *a, **k):
        if self == path:
            raise PermissionError(13, "in use by another program")
        return real(self, *a, **k)

    monkeypatch.setattr(type(path), "read_text", busy)
    before = list(settings_mod.BROKEN)
    with pytest.raises(PermissionError):
        Settings.load(path)
    assert path.exists() and settings_mod.BROKEN == before and not list(tmp_path.glob("*.broken-*"))


def test_a_moment_of_file_in_use_is_waited_out(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"tools": {"x": {"a": 1}}}), encoding="utf-8")
    monkeypatch.setattr(settings_mod.time, "sleep", lambda s: None)
    real, fails = type(path).read_text, [2]

    def flaky(self, *a, **k):
        if self == path and fails[0]:
            fails[0] -= 1
            raise PermissionError(13, "in use")
        return real(self, *a, **k)

    monkeypatch.setattr(type(path), "read_text", flaky)
    assert Settings.load(path).tools == {"x": {"a": 1}}


def test_a_broken_file_that_cannot_be_moved_is_still_copied_aside(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    path.write_text("{", encoding="utf-8")

    def no_move(a, b):
        raise PermissionError(13, "held open")

    monkeypatch.setattr(settings_mod.os, "replace", no_move)
    assert Settings.load(path).providers == []
    copies = list(tmp_path.glob("settings.broken-*.json"))
    assert len(copies) == 1 and copies[0].read_text(encoding="utf-8") == "{"
