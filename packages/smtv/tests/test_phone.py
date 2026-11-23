"""Phone access over home Wi-Fi (stage 9): off by default, the key from the QR code, Host and Origin of the home-network
address, what a phone may not do, the model key never reaching a phone, switching off cutting every phone."""
import http.client
import json
import socket
import sys
import threading
import time

import pytest

from smtv import jobs as jobs_module
from smtv import phone as phone_module
from smtv import qr, serve
from test_serve import CHILD, SECRET, Client, make_tool

ADDR, OTHER = "192.168.50.7", "10.0.0.9"


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)


class PhoneClient(Client):
    """Talks to the phone server (bound on 127.0.0.1 in tests) as a phone would: Host is the home-network address."""

    def __init__(self, bound, app):
        super().__init__(None, app.token)
        self.app, self.cookie, self._bound = app, None, bound

    @property
    def port(self):
        return self._bound.get("port")

    @port.setter
    def port(self, value):
        pass

    def request(self, method, path, body=None, headers=None, host=None, raw=False, cookie=True):
        h = {"Host": host or f"{self.app.phone.address or ADDR}:{self.app.port}"}
        if cookie and self.cookie:
            h["Cookie"] = f"{phone_module.COOKIE}={self.cookie}"
        h.update(headers or {})
        return super().request(method, path, body=body, headers=h, host=h["Host"], raw=raw)

    def scan(self, url):
        """What the phone's camera does with the QR code: opens the address; the key becomes a cookie."""
        path = url.split(str(self.app.port), 1)[1]
        res, _ = self.request("GET", path, raw=True, cookie=False)
        assert res.status == 303 and res.getheader("Location") == "/"
        cookie = res.getheader("Set-Cookie")
        assert "HttpOnly" in cookie and "SameSite=Strict" in cookie
        self.cookie = cookie.split(";")[0].split("=", 1)[1]
        return res


@pytest.fixture
def both(tmp_path):
    root = tmp_path / "jobs"
    root.mkdir()
    runner = jobs_module.Runner(lambda name, args: [sys.executable, "-c", CHILD, *args])
    app = serve.App([make_tool(root)], [], runner)
    srv = serve.make_server(app, port=0)
    threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    bound = {}

    def make(address):
        s = serve.make_phone_server(app, address, bind=("127.0.0.1", 0))
        bound["port"] = s.server_address[1]
        return s

    app.phone = phone_module.Phone(make, port=lambda: app.port, find=lambda: [ADDR, OTHER])
    local = Client(srv.server_address[1], app.token)
    yield app, local, lambda: PhoneClient(bound, app), root
    app.phone.disable()
    app.stopping.set()
    runner.stop_all()
    srv.shutdown()
    srv.server_close()


def switch_on(local, address=None):
    status, data = local.request("POST", "/api/phone", {"on": True, **({"address": address} if address else {})})
    assert status == 200 and data["on"], data
    return data


# --- the switch ----------------------------------------------------------------------------------------------

def test_off_by_default_and_only_loopback(both):
    app, local, _, _ = both
    status, data = local.request("GET", "/api/phone")
    assert status == 200 and data["on"] is False and data["url"] is None and data["qr"] is None
    assert data["addresses"] == [ADDR, OTHER]
    assert serve.App([], []).phone.on is False          # every start of SMTV: off


def test_switching_on_gives_a_qr_code_with_the_address_and_a_key(both):
    app, local, _, _ = both
    data = switch_on(local)
    assert data["address"] == ADDR and data["page"] == f"http://{ADDR}:{app.port}/"
    assert data["url"].startswith(f"http://{ADDR}:{app.port}/?k=") and len(data["url"].split("k=")[1]) >= 32
    assert data["qr"].startswith("<svg") and data["qr"] == qr.svg(data["url"])


def test_a_chosen_address_must_be_this_computers(both):
    app, local, _, _ = both
    assert switch_on(local, OTHER)["address"] == OTHER
    status, data = local.request("POST", "/api/phone", {"on": True, "address": "192.168.99.99"})
    assert status == 409 and data["error"] == "bad_address"
    status, data = local.request("POST", "/api/phone", {"on": "yes"})
    assert status == 400


def test_no_network_is_said_plainly(both):
    app, local, _, _ = both
    app.phone._find = lambda: []
    status, data = local.request("POST", "/api/phone", {"on": True})
    assert status == 409 and data["error"] == "no_network"


def test_only_private_addresses_are_offered():
    for ip in ("192.168.1.20", "10.1.2.3", "172.16.0.5", "172.31.255.1"):
        assert phone_module.private(ip), ip
    for ip in ("127.0.0.1", "198.18.0.2", "100.64.1.1", "169.254.1.1", "8.8.8.8", "172.32.0.1", "fe80::1", "nonsense"):
        assert not phone_module.private(ip), ip
    assert all(phone_module.private(ip) for ip in phone_module.addresses())
    with pytest.raises(OSError):
        serve.make_phone_server(serve.App([], []), "8.8.8.8")


# --- the key ---------------------------------------------------------------------------------------------------

def test_without_the_key_nothing_answers(both):
    app, local, phone_client, _ = both
    switch_on(local)
    phone = phone_client()
    status, body = phone.request("GET", "/")
    assert status == 403 and "QR" in body.decode()
    for path in ("/api/state", "/api/jobs", "/static/app.js", "/api/window/events", "/api/hello"):
        status, data = phone.request("GET", path)
        assert status == 403 and data["error"] == "no_phone_key", path
    status, body = phone.request("GET", "/?k=wrong-key")
    assert status == 403
    phone.cookie = "wrong-key"
    assert phone.request("GET", "/api/jobs")[0] == 403


def test_the_key_becomes_a_cookie_and_the_page_works(both):
    app, local, phone_client, _ = both
    data = switch_on(local)
    phone = phone_client()
    phone.scan(data["url"])
    status, page = phone.request("GET", "/")
    assert status == 200 and app.token.encode() in page
    status, state = phone.request("GET", "/api/state")
    assert status == 200 and state["phone"] is True
    assert local.request("GET", "/api/state")[1]["phone"] is False
    assert phone.request("GET", "/api/jobs")[0] == 200
    status, opts = phone.request("POST", "/api/tools/demo/options", {"name": "loud", "value": False},
                                 headers={"Origin": f"http://{ADDR}:{app.port}", "Sec-Fetch-Site": "same-origin"})
    assert status == 200 and opts[0]["value"] is False


def test_a_phone_starts_and_cancels_a_request(both):
    app, local, phone_client, root = both
    phone = phone_client()
    phone.scan(switch_on(local)["url"])
    status, job = phone.request("POST", "/api/tools/demo/jobs", {"source": "from-phone", "seconds": 30})
    assert status == 201 and job["id"] == "from-phone"
    status, job = phone.request("POST", "/api/jobs/demo/from-phone/cancel", {})
    assert status == 200


# --- Host and Origin -------------------------------------------------------------------------------------------

def test_host_and_origin_of_the_home_address(both):
    app, local, phone_client, _ = both
    phone = phone_client()
    phone.scan(switch_on(local)["url"])
    for host in (f"127.0.0.1:{app.port}", f"localhost:{app.port}", f"evil.example:{app.port}", f"{OTHER}:{app.port}", f"{ADDR}:1"):
        status, data = phone.request("GET", "/api/jobs", host=host)
        assert status == 403 and data["error"] == "bad_host", host
    # the computer's own server does not answer as the home address
    status, data = local.request("GET", "/api/jobs", host=f"{ADDR}:{app.port}")
    assert status == 403 and data["error"] == "bad_host"
    body = {"name": "loud", "value": True}
    for origin in ("http://evil.example", f"http://127.0.0.1:{app.port}", f"https://{ADDR}:{app.port}"):
        status, data = phone.request("POST", "/api/tools/demo/options", body, headers={"Origin": origin})
        assert status == 403 and data["error"] == "cross_origin", origin
    status, data = phone.request("POST", "/api/tools/demo/options", body, headers={"Sec-Fetch-Site": "cross-site"})
    assert status == 403
    status, data = phone.request("POST", "/api/tools/demo/options", body, headers={"X-SMTV-Token": "nope"})
    assert status == 403 and data["error"] == "stale_page"     # the session token of stage 5 stays


# --- what a phone may not do -----------------------------------------------------------------------------------

@pytest.mark.parametrize("method,path", [
    ("GET", "/api/settings"), ("POST", "/api/settings/providers"), ("POST", "/api/settings/providers/check"),
    ("POST", "/api/settings/providers/openai"), ("POST", "/api/settings/providers/openai/check"), ("POST", "/api/settings/providers/openai/delete"),
    ("POST", "/api/settings/providers/openai/recommend"), ("GET", "/api/settings/providers/openai/models"),
    ("POST", "/api/updates/update"), ("POST", "/api/updates/cancel"), ("POST", "/api/updates/settings"),
    ("POST", "/api/plugins/demo/install"), ("POST", "/api/plugins/demo/remove"), ("POST", "/api/plugins/livecut/install"),
    ("GET", "/api/uninstall"), ("POST", "/api/uninstall"), ("POST", "/api/quit"), ("POST", "/api/window/show"),
    ("GET", "/api/phone"), ("POST", "/api/phone"),
    ("POST", "/api/settings/providers/discover"), ("POST", "/api/settings/providers/ollama/ollama/pull"),
    ("GET", "/api/settings/providers/ollama/ollama"), ("POST", "/api/settings/speech/languages"),
    ("POST", "/api/settings/speech/models/whisper/download"), ("POST", "/api/settings/speech/models/gigaam/delete"),
    # B16: a phone only shows the StreamMoment account; the report archive is saved on the computer
    ("POST", "/api/account/login"), ("POST", "/api/account/logout"), ("POST", "/api/account/buy"), ("POST", "/api/account/check"),
    ("GET", "/api/report"), ("POST", "/api/report"), ("POST", "/api/report/reveal"),
])
def test_a_phone_may_not(both, method, path):
    app, local, phone_client, _ = both
    phone = phone_client()
    phone.scan(switch_on(local)["url"])
    status, data = phone.request(method, path, {"on": False, "confirm": "remove", "kind": "openai", "key": "x"} if method == "POST" else None)
    assert status == 403 and data["error"] == "not_from_phone", (method, path)
    assert app.phone.on        # still on: a phone cannot switch it off or read its key


def test_the_model_key_never_reaches_a_phone(both):
    app, local, phone_client, _ = both
    status, _ = local.request("POST", "/api/settings/providers", {"kind": "openai", "preset": "openai", "key": SECRET})
    assert status == 201
    phone = phone_client()
    phone.scan(switch_on(local)["url"])
    for path in ("/", "/api/state", "/api/jobs", "/api/doctor", "/api/usage", "/api/updates", "/api/activity",
                 "/api/tools/demo/options", "/api/hello", "/static/app.js", "/api/settings/agents", "/api/tools/demo/agents"):
        res, payload = phone.request("GET", path, raw=True)
        assert SECRET.encode() not in payload, path
        assert SECRET not in "".join(f"{k}{v}" for k, v in res.getheaders()), path


def test_a_phone_changes_an_agents_model_but_never_sees_the_key(both):
    app, local, phone_client, _ = both
    assert local.request("POST", "/api/settings/providers", {"kind": "openai", "preset": "openai", "key": SECRET})[0] == 201
    phone = phone_client()
    phone.scan(switch_on(local)["url"])
    origin = {"Origin": f"http://{ADDR}:{app.port}", "Sec-Fetch-Site": "same-origin"}
    for path in ("/api/tools/demo/agents", "/api/settings/agents"):
        res, payload = phone.request("GET", path, raw=True)
        assert res.status == 200 and SECRET.encode() not in payload, path
    status, data = phone.request("POST", "/api/settings/agents/demo/layout", {"provider": "openai", "model": "gpt-6-luna"}, headers=origin)
    assert status == 200 and SECRET not in json.dumps(data)
    assert [x for g in data["groups"] for x in g["agents"] if x["id"] == "layout"][0]["current"]["model"] == "gpt-6-luna"
    status, data = phone.request("POST", "/api/settings/agents/demo/layout", {"provider": "openai", "model": "gpt-6-luna"},
                                 headers={**origin, "X-SMTV-Token": "nope"})
    assert status == 403 and data["error"] == "stale_page"


# --- switching off ---------------------------------------------------------------------------------------------

def test_switching_off_closes_the_address_and_cuts_every_phone(both):
    app, local, phone_client, _ = both
    first = switch_on(local)
    phone = phone_client()
    port = phone.port
    phone.scan(first["url"])
    # an open stream of the window on the phone
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    conn.request("GET", "/api/window/events", headers={"Host": f"{ADDR}:{app.port}", "Cookie": f"{phone_module.COOKIE}={phone.cookie}"})
    res = conn.getresponse()
    assert res.status == 200 and res.fp.readline()
    status, data = local.request("POST", "/api/phone", {"on": False})
    assert status == 200 and data["on"] is False and data["url"] is None
    started = time.monotonic()
    while res.fp.readline():            # the stream ends at once, not at its next heartbeat
        assert time.monotonic() - started < 3
    with pytest.raises(OSError):
        socket.create_connection(("127.0.0.1", port), timeout=2).close()
    # on again: a new key; the old cookie no longer works
    second = switch_on(local)
    assert second["url"] != first["url"]
    phone2 = phone_client()
    phone2.cookie = phone.cookie
    assert phone2.request("GET", "/api/jobs")[0] == 403
    phone2.scan(second["url"])
    assert phone2.request("GET", "/api/jobs")[0] == 200


def test_another_address_keeps_the_key(both):
    app, local, _, _ = both
    a = switch_on(local, ADDR)
    b = switch_on(local, OTHER)
    assert b["address"] == OTHER and b["url"].split("k=")[1] == a["url"].split("k=")[1]
    assert switch_on(local, OTHER)["url"] == b["url"]     # the same address again: nothing changes


# --- remembered between starts (owner, 21.11) -----------------------------------------------------------------

class FakeServer:
    def __init__(self, address):
        self.address, self.closed = address, False

    def serve_forever(self, poll_interval=0.5):
        pass

    def shutdown(self):
        pass

    def server_close(self):
        self.closed = True

    def cut_all(self):
        pass


def start_smtv(find=lambda: [ADDR, OTHER]):
    """A start of SMTV as far as phone access goes: a new Phone with the saved switch, then restore."""
    p = phone_module.Phone(FakeServer, port=lambda: 8642, find=find, saved=phone_module.Saved())
    p.restore()
    return p


def test_the_switch_is_remembered_with_its_key_and_address():
    first = start_smtv()
    assert not first.on                              # never switched on: off
    first.enable(OTHER)
    key = first.key
    first.close()                                    # SMTV quits: closed now, but still «on» for the next start
    assert not first.on
    again = start_smtv()
    assert again.on and again.address == OTHER and again.key == key   # a phone's cookie keeps working
    again.disable()
    assert not start_smtv().on                       # switched off: stays off


def test_a_restore_without_the_saved_address_or_network():
    p = start_smtv()
    p.enable(OTHER)
    key = p.key
    p.close()
    moved = start_smtv(find=lambda: [ADDR])          # the computer got another address: the first one, same key
    assert moved.on and moved.address == ADDR and moved.key == key
    moved.close()
    offline = start_smtv(find=lambda: [])            # no network now: off this time, no error
    assert not offline.on
    assert start_smtv().on                           # and on again once there is a network


def test_a_lost_key_makes_a_new_one_and_remembers_it(monkeypatch):
    p = start_smtv()
    p.enable(ADDR)
    p.close()
    real = phone_module.Saved.load
    monkeypatch.setattr(phone_module.Saved, "load", lambda self: {"on": True, "address": ADDR, "key": None})
    fresh = start_smtv()
    assert fresh.on and fresh.key and len(fresh.key) >= 32
    monkeypatch.setattr(phone_module.Saved, "load", real)
    assert start_smtv().key == fresh.key


def test_the_key_is_not_in_the_settings_file(tmp_path):
    from smtv_core import paths
    p = start_smtv()
    p.enable(ADDR)
    text = paths.settings_file().read_text(encoding="utf-8")
    assert '"on": true' in text and ADDR in text and p.key not in text


def test_unreadable_settings_do_not_stop_smtv(monkeypatch):
    def broken(self):
        raise ValueError("bad json")
    monkeypatch.setattr(phone_module.Saved, "load", broken)
    assert not start_smtv().on


# --- the QR code -----------------------------------------------------------------------------------------------

def test_qr_sizes_and_limits():
    assert qr.QR("a").version == 1
    assert qr.QR("http://192.168.1.20:8642/?k=" + "x" * 32).version in (4, 5)
    with pytest.raises(ValueError):
        qr.QR("x" * 300)


@pytest.mark.skipif(sys.platform != "darwin", reason="reads the code back with macOS CoreImage")
@pytest.mark.parametrize("text", ["a", "http://192.168.1.20:8642/?k=Abc-_123", "http://10.0.0.9:8642/?k=" + "Z" * 32, "y" * 120, "q" * 200])
def test_qr_reads_back(text, tmp_path):
    Quartz = pytest.importorskip("Quartz")
    from Foundation import NSURL
    import struct
    import zlib
    code, scale, border = qr.QR(text), 6, 4
    n = (code.size + 2 * border) * scale
    rows = b"".join(bytes([0] + [0 if 0 <= (x := px // scale - border) < code.size and 0 <= (y := py // scale - border) < code.size and code.modules[y][x] else 255
                                 for px in range(n)]) for py in range(n))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    path = tmp_path / "qr.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", n, n, 8, 0, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))
    image = Quartz.CIImage.imageWithContentsOfURL_(NSURL.fileURLWithPath_(str(path)))
    detector = Quartz.CIDetector.detectorOfType_context_options_(Quartz.CIDetectorTypeQRCode, None, {Quartz.CIDetectorAccuracy: Quartz.CIDetectorAccuracyHigh})
    assert [f.messageString() for f in detector.featuresInImage_(image)] == [text]


# --- B28: a connection that says nothing, and a flood of them -----------------------------------------------------------

def test_a_silent_connection_to_the_phone_server_is_closed(both, monkeypatch):
    """Anyone on the home network reaches the phone server, even without the key: a connection that sends half a
    request and stops is closed after the timeout, never held for ever."""
    app, local, _, _ = both
    monkeypatch.setattr(serve, "PHONE_TIMEOUT_S", 0.5)
    switch_on(local)
    port = app.phone.server.server_address[1]
    s = socket.create_connection(("127.0.0.1", port), timeout=5)
    s.sendall(b"GET / HTTP/1.1\r\nHost: " + ADDR.encode())          # no end of the headers
    started = time.monotonic()
    assert s.recv(1024) == b""                                       # closed by the server
    assert time.monotonic() - started < 4
    s.close()


def test_the_phone_server_answers_at_most_so_many_connections_at_once(both, monkeypatch):
    app, local, _, _ = both
    monkeypatch.setattr(serve, "PHONE_MAX_CONNECTIONS", 3)
    switch_on(local)
    server = app.phone.server
    port = server.server_address[1]
    held = [socket.create_connection(("127.0.0.1", port), timeout=5) for _ in range(3)]
    deadline = time.monotonic() + 3
    while len(server.live) < 3 and time.monotonic() < deadline:
        time.sleep(0.02)
    extra = socket.create_connection(("127.0.0.1", port), timeout=5)
    assert extra.recv(1024) == b"" and server.refused >= 1          # closed at once
    for s in held + [extra]:
        s.close()
    deadline = time.monotonic() + 5
    while server.live and time.monotonic() < deadline:
        time.sleep(0.02)
    assert not server.live                                          # their places freed


def test_the_window_server_on_this_computer_has_no_cap():
    srv = serve.make_server(serve.App([], []), port=0)
    try:
        assert srv.max_live is None and srv.RequestHandlerClass.timeout is None
    finally:
        srv.server_close()


def test_live_streams_write_more_often_than_the_phone_server_waits():
    """An open stream on the phone (a request's progress) lives only because its heartbeat comes before the timeout."""
    from smtv import hub
    assert max(serve.HEARTBEAT_S, hub.HEARTBEAT_S) * 2 <= serve.PHONE_TIMEOUT_S
