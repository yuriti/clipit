"""Stage 23: recordings by link through StreamMoment (smtv_core.media) against a fake of our server's /api/smtv/media."""
from __future__ import annotations

import http.server
import hashlib
import json
import threading
import time

import pytest

from smtv_core import appkey, device, media

LINK = "https://www.twitch.tv/videos/2934906889"
SEGMENTS = [{"name": f"{i}.mp4", "start": i * 10.0, "duration": 10.0} for i in range(40)]


class Fake:
    """Our server's media API in a thread: a queue place, then segments (bytes = their name), with chosen failures."""

    def __init__(self):
        self.waits = 2                  # GET /media/<ticket> answers «waiting» this many times
        self.tickets: list[str] = []
        self.closed: list[str] = []
        self.fail: dict[str, list[int]] = {}      # segment name -> statuses to answer before the bytes
        self.forget_once = False         # the server forgot the ticket (SMTV slept): 404 media_ticket_expired once
        self.open_error: tuple[int, dict] | None = None
        self.headers: list[dict] = []
        self.seen: list[str] = []
        self.in_flight = 0
        self.max_in_flight = 0
        self.lock = threading.Lock()
        fake = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def send(self, status, body, kind="application/json"):
                data = body if isinstance(body, bytes) else json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_POST(self):  # noqa: N802
                fake.headers.append({k.lower(): v for k, v in self.headers.items()})
                self.rfile.read(int(self.headers.get("Content-Length") or 0))
                if fake.open_error:
                    return self.send(*fake.open_error)
                ticket = f"t{len(fake.tickets) + 1}"
                fake.tickets.append(ticket)
                self.send(200, {"ticket": ticket, "state": "waiting" if fake.waits else "ready", "position": 3,
                                "source": {"platform": "twitch", "title": "Стрим", "duration_s": 400, "url": LINK}})

            def do_DELETE(self):  # noqa: N802
                fake.headers.append({k.lower(): v for k, v in self.headers.items()})
                fake.closed.append(self.path.rsplit("/", 1)[-1])
                self.send(200, {"closed": True})

            def do_GET(self):  # noqa: N802
                fake.headers.append({k.lower(): v for k, v in self.headers.items()})
                parts = self.path.split("/")[4:]        # /api/smtv/media/<ticket>[/<track>[/<file>]]
                ticket = parts[0]
                fake.seen.append("/".join(parts))
                if fake.forget_once and len(parts) == 3 and ticket == "t1":
                    fake.forget_once = False
                    return self.send(404, {"error": "media_ticket_expired"})
                if len(parts) == 1:
                    fake.waits -= 1
                    return self.send(200, {"state": "waiting" if fake.waits > 0 else "ready", "position": max(fake.waits, 0)})
                if len(parts) == 2:
                    return self.send(200, {"track": parts[1], "init": "init-0.mp4", "segments": SEGMENTS})
                name = parts[2]
                with fake.lock:
                    fake.in_flight += 1
                    fake.max_in_flight = max(fake.max_in_flight, fake.in_flight)
                try:
                    statuses = fake.fail.get(name)
                    if statuses:
                        status = statuses.pop(0)
                        return self.send(status, {"error": {403: "media_segment_gone", 401: "app_key"}.get(status, "media_upstream_unavailable")})
                    time.sleep(0.02 if name.startswith("1") else 0.001)     # out of order on purpose
                    self.send(200, f"[{name}]".encode(), "video/mp4")
                finally:
                    with fake.lock:
                        fake.in_flight -= 1

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"


@pytest.fixture
def fake(monkeypatch, tmp_path):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    f = Fake()
    monkeypatch.setenv("SMTV_ACCOUNT_URL", f.url)
    monkeypatch.setenv("SMTV_APP_KEY", "test-app-key")
    monkeypatch.setattr(device, "machine_id", lambda: "MACHINE-1")
    yield f
    f.server.shutdown()


def no_sleep(_s):
    pass


def test_waits_its_turn_then_fetches_all_audio_in_order(fake, tmp_path):
    places = []
    with media.Ticket(LINK, on_wait=places.append, sleep=no_sleep) as t:
        assert t.source["title"] == "Стрим"
        progress = []
        start = t.fetch("audio", tmp_path / "a.mp4", on_progress=lambda d, n: progress.append((d, n)))
    assert places == [3, 1, 0], "the window sees its place in our queue, then its turn"
    assert start == 0.0
    want = b"[init-0.mp4]" + b"".join(f"[{s['name']}]".encode() for s in SEGMENTS)
    assert (tmp_path / "a.mp4").read_bytes() == want, "segments are written in the order of the recording"
    assert progress[-1] == (41, 41)
    assert 1 < fake.max_in_flight <= media.FRAGMENTS_AT_ONCE
    assert fake.closed == ["t1"], "the slot is given back"
    assert fake.headers and all("authorization" not in h and h["x-smtv-app-key"] == "test-app-key" for h in fake.headers)
    want_device = hashlib.sha256(b"smtv-device-v1:MACHINE-1").hexdigest()
    assert all(h["x-smtv-device"] == want_device and h["x-smtv-version"] == __import__("smtv_core").__version__
               and h["x-smtv-os"] == device.os_tag() for h in fake.headers)
    assert "MACHINE-1" not in json.dumps(fake.headers)


def test_a_piece_takes_only_its_segments_and_says_where_it_starts(fake, tmp_path):
    fake.waits = 0
    with media.Ticket(LINK, sleep=no_sleep) as t:
        start = t.fetch("video", tmp_path / "p.mp4", 95.0, 121.0)
    assert start == 90.0
    assert (tmp_path / "p.mp4").read_bytes() == b"[init-0.mp4][9.mp4][10.mp4][11.mp4][12.mp4]"


def test_a_passing_failure_is_tried_again_a_lasting_one_leaves_no_half_file(fake, tmp_path):
    fake.waits = 0
    fake.fail = {"3.mp4": [503, 502], "5.mp4": [429]}
    with media.Ticket(LINK, sleep=no_sleep) as t:
        t.fetch("audio", tmp_path / "a.mp4")
        assert b"[3.mp4]" in (tmp_path / "a.mp4").read_bytes()
        fake.fail = {"7.mp4": [403]}
        with pytest.raises(media.MediaError, match="no longer gives a part"):
            t.fetch("audio", tmp_path / "b.mp4")
    assert not (tmp_path / "b.mp4").exists() and not (tmp_path / "b.mp4.part").exists()
    fake.fail = {"7.mp4": [503] * 10}
    with media.Ticket(LINK, sleep=no_sleep) as t, pytest.raises(media.MediaError):
        t.fetch("audio", tmp_path / "c.mp4")
    assert not list(tmp_path.glob("c.mp4*"))


def test_a_ticket_the_server_forgot_is_opened_again(fake, tmp_path):
    fake.waits = 0
    fake.forget_once = True
    with media.Ticket(LINK, sleep=no_sleep) as t:
        t.fetch("video", tmp_path / "p.mp4", 0, 15)
        assert t.id == "t2"
    assert (tmp_path / "p.mp4").read_bytes() == b"[init-0.mp4][0.mp4][1.mp4]"


def test_refusals_are_plain_words(fake, monkeypatch):
    fake.open_error = (429, {"error": "media_daily_limit"})
    with pytest.raises(media.MediaError, match="hours of links .* used up") as e:
        media.Ticket(LINK, sleep=no_sleep)
    assert not e.value.retryable
    fake.open_error = (404, {"message": "Route POST:/api/smtv/media/open not found", "error": "Not Found"})
    with pytest.raises(media.MediaError, match="not available in this copy.*Download links myself"):
        media.Ticket(LINK, sleep=no_sleep)
    with pytest.raises(media.MediaError, match="Twitch and YouTube only"):
        media.Ticket("https://kick.com/video/1")
    assert len(fake.tickets) == 0
    fake.open_error = None
    assert media.Ticket("https://www.youtube.com/watch?v=jNQXAC9IVRw", sleep=no_sleep).id == "t1"      # YouTube goes to the server


def test_no_key_turns_links_off_with_a_clear_message_and_asks_nothing(fake, monkeypatch, tmp_path):
    monkeypatch.delenv("SMTV_APP_KEY")
    monkeypatch.chdir(tmp_path)                                   # no .env here
    monkeypatch.setattr(appkey, "_built_in", lambda: "")
    with pytest.raises(media.MediaError, match="not available in this copy.*choose the recording file.*Download links myself") as e:
        media.Ticket(LINK, sleep=no_sleep)
    assert e.value.code == "no_app_key" and media.SIGN_IN in str(e.value) and not e.value.retryable
    assert fake.headers == [] and fake.tickets == [], "nothing is sent without a key"


def test_the_key_comes_from_the_environment_then_dotenv_then_the_built_module(monkeypatch, tmp_path):
    monkeypatch.delenv("SMTV_APP_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(appkey, "_built_in", lambda: "built")
    assert appkey.get() == "built"
    (tmp_path / ".env").write_text('OTHER=1\nSMTV_APP_KEY="from-dotenv"\n', encoding="utf-8")
    assert appkey.get() == "from-dotenv"
    monkeypatch.setenv("SMTV_APP_KEY", "from-env")
    assert appkey.get() == "from-env"


def test_401_app_key_says_to_update_or_use_a_file(fake):
    fake.open_error = (401, {"error": "app_key"})
    with pytest.raises(media.MediaError, match="too old or not genuine.*choose the recording file") as e:
        media.Ticket(LINK, sleep=no_sleep)
    assert e.value.code == "app_key" and not e.value.retryable


def test_429_limit_says_when_to_come_back_and_is_not_retried(fake):
    fake.open_error = (429, {"error": "limit", "limit": 5, "retry_after": 5400})
    with pytest.raises(media.MediaError, match="limit.*in 90 minutes") as e:
        media.Ticket(LINK, sleep=no_sleep)
    assert e.value.code == "limit" and e.value.retry_after == 5400 and not e.value.retryable
    assert len(fake.headers) == 1, "asked once"
    assert str(media._error(429, {"error": "limit", "retry_after": 30})).count("in a minute") == 1
    assert "later" in str(media._error(429, {"error": "limit"}))


def test_503_is_still_retryable(fake):
    assert media._error(503, {"error": "media_upstream_unavailable"}).retryable


def test_a_segment_401_is_the_same_clear_message(fake, tmp_path):
    fake.waits = 0
    fake.fail["3.mp4"] = [401] * 9
    with media.Ticket(LINK, sleep=no_sleep) as t:
        with pytest.raises(media.MediaError) as e:
            t.fetch("video", tmp_path / "p.mp4", 0, 45)
    assert e.value.code == "app_key"


def test_the_device_is_a_hash_and_the_raw_id_is_never_used(monkeypatch):
    monkeypatch.setattr(device, "machine_id", lambda: "ABC-123")
    assert device.device_id() == hashlib.sha256(b"smtv-device-v1:ABC-123").hexdigest()
    assert "ABC-123" not in "".join(device.headers("k").values())


def test_when_the_machine_id_cannot_be_read_a_random_one_is_made_once_and_kept(monkeypatch, tmp_path):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path))
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)
    monkeypatch.setattr(device, "machine_id", lambda: "")
    first = device.device_id()
    assert len(first) == 64 and int(first, 16) >= 0
    assert device.device_id() == first, "the same one next time"
    from smtv_core.settings import Settings
    assert Settings.load().tools["smtv"]["device_id"] == first
    (tmp_path / "x").write_text("")      # a settings file that was hand-damaged: a new valid id
    with Settings.edit() as s:
        s.tools["smtv"]["device_id"] = "not-hex"
    assert device.device_id() != "not-hex"


def test_os_tag_shapes(monkeypatch):
    monkeypatch.setattr(device.sys, "platform", "darwin")
    monkeypatch.setattr(device.platform, "mac_ver", lambda: ("15.1", ("", "", ""), ""))
    monkeypatch.setattr(device.platform, "machine", lambda: "arm64")
    assert device.os_tag() == "macos-15.1-arm64"
    monkeypatch.setattr(device.sys, "platform", "linux")
    monkeypatch.setattr(device.platform, "machine", lambda: "x86_64")
    assert device.os_tag() == "linux-x64"
    monkeypatch.setattr(device.sys, "platform", "win32")
    monkeypatch.setattr(device.sys, "getwindowsversion", lambda: type("V", (), {"build": 26100})(), raising=False)
    assert device.os_tag() == "windows-11-x64"


def test_an_expired_ticket_is_opened_again_once_for_all_segments_in_flight(fake, tmp_path, monkeypatch):
    """The server forgot the ticket (SMTV slept, a deploy): 16 segments in flight all hear «expired» — one new ticket."""
    fake.waits = 0
    with media.Ticket(LINK, sleep=no_sleep) as t:
        t.playlist("audio")
        real = media._bytes

        def forgetful(path, timeout=media.SEGMENT_TIMEOUT_S):
            if "/t1/" in path:
                time.sleep(0.01)
                raise media.MediaError("media_ticket_expired")
            return real(path, timeout)

        monkeypatch.setattr(media, "_bytes", forgetful)
        t.fetch("audio", tmp_path / "a.mp4")
        assert t.id == "t2"
    assert fake.tickets == ["t1", "t2"], "exactly one new ticket"
    assert (tmp_path / "a.mp4").read_bytes().startswith(b"[init-0.mp4][0.mp4][1.mp4]")


def test_a_segment_cut_short_is_tried_again(fake, tmp_path, monkeypatch):
    import http.client
    fake.waits = 0
    real, cut = media._bytes, {"n": 0}

    def breaks_once(path, timeout=media.SEGMENT_TIMEOUT_S):
        if path.endswith("/4.mp4") and not cut["n"]:
            cut["n"] += 1
            try:
                raise http.client.IncompleteRead(b"half", 100)
            except http.client.HTTPException as e:       # as _bytes turns it into a retryable error
                raise media.MediaError("segment_short", str(e), retryable=True) from e
        return real(path, timeout)

    monkeypatch.setattr(media, "_bytes", breaks_once)
    with media.Ticket(LINK, sleep=no_sleep) as t:
        t.fetch("audio", tmp_path / "a.mp4")
    assert cut["n"] == 1 and b"[4.mp4]" in (tmp_path / "a.mp4").read_bytes()


def test_incomplete_read_is_retryable_in_bytes(monkeypatch):
    import http.client
    import urllib.request

    class Broken:
        headers = {"Content-Length": "100"}

        def read(self):
            raise http.client.IncompleteRead(b"half", 96)

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setenv("SMTV_APP_KEY", "k")
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: Broken())
    with pytest.raises(media.MediaError) as e:
        media._bytes("/api/smtv/media/t1/audio/0.mp4")
    assert e.value.code == "segment_short" and e.value.retryable


def test_the_estimate_asks_info_not_a_ticket(fake):
    fake.open_error = None
    # the fake answers POST with a ticket; info reads only its «source»
    assert media.info(LINK)["title"] == "Стрим"


def test_a_passing_network_failure_keeps_the_place_in_the_queue(fake, monkeypatch, tmp_path):
    """B4: Wi-Fi dropped for a moment while waiting: the ticket is kept, the wait goes on, the recording comes."""
    real, failures = media._json, iter([media.MediaError("unreachable", "no Wi-Fi", retryable=True)] * 3)

    def flaky(method, path, body=None, **kw):
        if method == "GET" and path.count("/") == 4:      # /api/smtv/media/<ticket>: the place in the queue
            failure = next(failures, None)
            if failure:
                raise failure
        return real(method, path, body, **kw) if body is not None else real(method, path, **kw)
    monkeypatch.setattr(media, "_json", flaky)
    places = []
    with media.Ticket(LINK, on_wait=places.append, sleep=no_sleep) as t:
        assert t.fetch("audio", tmp_path / "a.mp4") == 0.0
    assert fake.tickets == ["t1"] and places[-1] == 0                 # the same ticket: the place was never given up


def test_a_lasting_network_failure_or_a_refusal_still_gives_up(fake, monkeypatch):
    clock = iter(range(0, 10_000, 100))
    monkeypatch.setattr(media.time, "monotonic", lambda: float(next(clock)))
    real, asked = media._json, []

    def down(method, path, body=None, **kw):
        if method == "GET":
            asked.append(path)
            raise media.MediaError("unreachable", "no network", retryable=True)
        return real(method, path, body, **kw)
    monkeypatch.setattr(media, "_json", down)
    with pytest.raises(media.MediaError) as e:
        media.Ticket(LINK, sleep=no_sleep)
    assert e.value.code == "unreachable" and 3 <= len(asked) <= 9    # after WAIT_NET_TOLERANCE_S (600 s, the clock moves 100 s a call), not on the first

    def refused(method, path, body=None, **kw):
        if method == "GET":
            raise media.MediaError("media_ticket_expired", "gone")
        return real(method, path, body, **kw)
    monkeypatch.setattr(media, "_json", refused)
    with pytest.raises(media.MediaError) as e:
        media.Ticket(LINK, sleep=no_sleep)
    assert e.value.code == "media_ticket_expired"


def test_a_ticket_the_queue_forgot_while_waiting_takes_a_new_place_once(fake, monkeypatch, tmp_path):
    """Our server restarted while SMTV waited: one new ticket, not an error after an hour in the queue."""
    real, forgot = media._json, [media.MediaError("media_ticket_expired", "gone")]

    def forgetful(method, path, body=None, **kw):
        if method == "GET" and path == "/api/smtv/media/t1" and forgot:
            raise forgot.pop()
        return real(method, path, body, **kw) if body is not None else real(method, path, **kw)
    monkeypatch.setattr(media, "_json", forgetful)
    fake.waits = 5
    with media.Ticket(LINK, sleep=no_sleep) as t:
        assert t.id == "t2" and t.fetch("audio", tmp_path / "a.mp4") == 0.0
    assert fake.tickets == ["t1", "t2"]


def test_network_failures_apart_never_add_up_to_giving_up(fake, monkeypatch):
    """«In a row»: a failure now and then over hours of waiting keeps the place; only a lasting one gives it up."""
    clock = iter(range(0, 1_000_000, 100))
    monkeypatch.setattr(media.time, "monotonic", lambda: float(next(clock)))
    real, n = media._json, [0]

    def now_and_then(method, path, body=None, **kw):
        if method == "GET" and path == "/api/smtv/media/t1":
            n[0] += 1
            if n[0] % 2:
                raise media.MediaError("unreachable", "Wi-Fi", retryable=True)
        return real(method, path, body, **kw) if body is not None else real(method, path, **kw)
    monkeypatch.setattr(media, "_json", now_and_then)
    fake.waits = 20
    t = media.Ticket(LINK, sleep=no_sleep)
    assert t.id == "t1" and fake.tickets == ["t1"] and n[0] >= 30
