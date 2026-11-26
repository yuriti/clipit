"""Stage 23: a link goes through the StreamMoment account; yt-dlp here only with «Download on this computer» on."""
import sys
import types

import pytest

from smtv_core import media

from vodcut import ingest, local_download, options


@pytest.fixture(autouse=True)
def ffmpeg_here(monkeypatch):
    monkeypatch.setattr(ingest, "_has_ffmpeg", lambda: True)


def local_on(monkeypatch, on=True):
    monkeypatch.setattr(options, "local_download", lambda: on)


def test_vodcut_does_not_need_yt_dlp():
    import tomllib
    from pathlib import Path
    project = tomllib.loads((Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert not any("yt-dlp" in d for d in project["dependencies"])
    assert any("yt-dlp" in d for d in project["optional-dependencies"]["local"])


def test_a_link_goes_through_streammoment_audio_only(tmp_path, monkeypatch):
    local_on(monkeypatch, False)
    seen = {}

    class FakeTicket:
        def __init__(self, url, on_wait=None):
            seen["url"] = url
            on_wait and on_wait(2)
            on_wait and on_wait(0)
            self.source = {"url": "https://www.twitch.tv/videos/2934906889", "title": "Стрим", "platform": "twitch", "channel": "Vika",
                           "channel_id": "vika_karter", "id": "2934906889", "duration_s": 20349, "language": "ru", "date": "2026-11-20"}

        def fetch(self, track, dest, start_s=None, end_s=None, on_progress=None):
            seen["track"], seen["range"] = track, (start_s, end_s)
            dest.write_bytes(b"fmp4")
            on_progress and on_progress(1, 1)
            return 0.0

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            seen["closed"] = True

    monkeypatch.setattr(media, "Ticket", FakeTicket)
    monkeypatch.setattr(ingest, "_ffmpeg_to_wav", lambda src, wav: wav.write_bytes(b"RIFF"))
    places, ticks = [], []
    info = ingest.ingest("https://www.twitch.tv/videos/2934906889", tmp_path, on_wait=places.append, on_progress=lambda d, t: ticks.append(d))
    assert seen == {"url": "https://www.twitch.tv/videos/2934906889", "track": "audio", "range": (None, None), "closed": True}
    assert places == [2, 0] and ticks == [1]
    assert info["via"] == "streammoment" and info["platform"] == "twitch" and info["channel_id"] == "vika_karter"
    assert info["date"] == "2026-11-20" and info["duration_s"] == 20349
    assert (tmp_path / "audio.wav").exists() and not (tmp_path / "source_audio.mp4").exists()
    assert (tmp_path / "source.json").exists()


def test_a_refused_link_says_what_to_do(tmp_path, monkeypatch):
    local_on(monkeypatch, False)

    def refuses(url, on_wait=None):
        raise media.MediaError("not_signed_in")

    monkeypatch.setattr(media, "Ticket", refuses)
    with pytest.raises(ingest.IngestError, match="coming soon.*choose the recording file.*Download links myself.*streammoment_sign_in"):
        ingest.from_link("https://www.twitch.tv/videos/2934906889", tmp_path)


def test_youtube_is_not_downloaded_here_without_the_switch(tmp_path, monkeypatch):
    local_on(monkeypatch, False)
    monkeypatch.setitem(sys.modules, "yt_dlp", None)        # even when yt-dlp is installed it is not used
    with pytest.raises(ingest.IngestError, match="YouTube links do not open through StreamMoment yet.*Download links myself"):
        ingest.from_link("https://www.youtube.com/watch?v=x", tmp_path)


def test_the_local_switch_uses_yt_dlp_many_fragments_at_once(tmp_path, monkeypatch):
    """One fragment at a time a 2.3 h Twitch audio took 9.5 minutes; the download must ask yt-dlp for parallel fragments."""
    local_on(monkeypatch)
    seen = {}

    class FakeYDL:
        def __init__(self, opts):
            seen.update(opts)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def extract_info(self, url, download):
            assert download is False                 # first only what the link is: a live stream is refused before anything is written
            return {"id": "v1", "title": "t", "extractor_key": "TwitchVod", "uploader": "ch", "duration": 60, "ext": "mp4"}

        def process_ie_result(self, meta, download):
            (tmp_path / "source_audio.mp4").write_bytes(b"x")
            return meta

        def prepare_filename(self, meta):
            return str(tmp_path / "source_audio.mp4")

    monkeypatch.setitem(sys.modules, "yt_dlp", types.SimpleNamespace(YoutubeDL=FakeYDL))
    monkeypatch.setattr(ingest, "_ffmpeg_to_wav", lambda src, wav: wav.write_bytes(b"RIFF"))
    info = ingest.from_link("https://www.twitch.tv/videos/1", tmp_path)
    assert seen["concurrent_fragment_downloads"] >= 8
    assert seen["format"].startswith("bestaudio")
    assert info["platform"] == "twitchvod" and info["channel"] == "ch" and info["via"] == "local"
    assert not (tmp_path / "source_audio.mp4").exists()


def test_the_local_switch_without_yt_dlp_names_the_command(tmp_path, monkeypatch):
    local_on(monkeypatch)
    monkeypatch.setitem(sys.modules, "yt_dlp", None)
    with pytest.raises(ingest.IngestError, match="yt-dlp is not installed: .*yt-dlp"):
        ingest.from_link("https://www.youtube.com/watch?v=x", tmp_path)


class Refuses:
    def __init__(self, opts):
        assert not any("cookie" in k for k in opts)          # never the person's browser

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def extract_info(self, url, download=True):
        raise RuntimeError("ERROR: [youtube] x: Sign in to confirm you’re not a bot. Use --cookies-from-browser")


def test_youtube_bot_check_says_what_to_do(tmp_path, monkeypatch):
    local_on(monkeypatch)
    monkeypatch.setitem(sys.modules, "yt_dlp", types.SimpleNamespace(YoutubeDL=Refuses))
    with pytest.raises(ingest.IngestError, match="without signing in.*choose the file.*youtube_sign_in"):
        ingest.from_link("https://www.youtube.com/watch?v=x", tmp_path)


def test_the_window_explains_youtube_sign_in_and_reads_no_browser(monkeypatch):
    from vodcut import page
    local_on(monkeypatch)
    monkeypatch.setitem(sys.modules, "yt_dlp", types.SimpleNamespace(YoutubeDL=Refuses))
    with pytest.raises(ValueError, match="without signing in.*youtube_sign_in"):
        page._probe("https://www.youtube.com/watch?v=x")


def test_the_estimate_of_a_link_asks_streammoment_without_queue_or_download(monkeypatch):
    from vodcut import page
    local_on(monkeypatch, False)
    monkeypatch.setattr(media, "Ticket", lambda *a, **kw: (_ for _ in ()).throw(AssertionError("no place in the queue for an estimate")))
    monkeypatch.setattr(media, "info", lambda url: {"duration_s": 7200, "title": "t", "channel": "c", "live": False})
    assert page._probe("https://www.twitch.tv/videos/2934906889") == {"duration_s": 7200.0, "title": "t", "channel": "c", "kind": "link", "live": False}


def test_doctor_checks_links_not_yt_dlp(monkeypatch, tmp_path):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path))
    from smtv_core import account
    from smtv_core.checks import FAIL, OK, WARN
    from smtv_core.settings import Settings
    from vodcut import tool
    s = Settings.load()
    monkeypatch.setattr(account, "signed_in", lambda: None)
    row = tool.checks(s)[0]
    assert row.status == WARN and "StreamMoment" in row.name and "video file works" in row.detail
    monkeypatch.setattr(account, "signed_in", lambda: {"name": "Аня"})
    assert tool.checks(s)[0].status == OK
    options.set_option(s, "local_download", True)
    monkeypatch.setattr(local_download, "available", lambda: False)
    row = tool.checks(s)[0]
    assert row.status == FAIL and "yt-dlp" in row.name and "yt-dlp" in row.fix


class FakeYDLBase:
    def __init__(self, opts):
        self.opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def prepare_filename(self, meta):
        return meta["_path"]


def test_a_stream_still_on_the_air_is_refused_with_wait_for_its_end(tmp_path, monkeypatch):
    """Decision 17 (B9): yt-dlp would record a live stream until it ends; the request is refused with what to do."""
    local_on(monkeypatch)
    seen = {}

    class Live(FakeYDLBase):
        def extract_info(self, url, download=True):
            seen["socket_timeout"] = self.opts.get("socket_timeout")
            return {"id": "x", "is_live": True, "live_status": "is_live"}

        def process_ie_result(self, meta, download=True):
            raise AssertionError("a live stream is never downloaded")

    monkeypatch.setitem(sys.modules, "yt_dlp", types.SimpleNamespace(YoutubeDL=Live))
    with pytest.raises(ingest.IngestError, match="Эфир ещё идёт — дождитесь его конца"):
        ingest.from_link("https://www.twitch.tv/someone", tmp_path)
    assert seen["socket_timeout"] and not list(tmp_path.glob("source_audio.*"))


def test_a_half_downloaded_part_is_never_taken_for_the_audio(tmp_path, monkeypatch):
    """B10: the fallback search skips .part/.ytdl files."""
    local_on(monkeypatch)

    class Partial(FakeYDLBase):
        def extract_info(self, url, download=True):
            return {"id": "x", "ext": "webm", "_path": str(tmp_path / "source_audio.webm")}

        def process_ie_result(self, meta, download=True):
            (tmp_path / "source_audio.webm.part").write_bytes(b"half")
            return meta

    monkeypatch.setitem(sys.modules, "yt_dlp", types.SimpleNamespace(YoutubeDL=Partial))
    with pytest.raises(local_download.LocalDownloadError, match="no audio file"):
        local_download.audio("https://www.twitch.tv/videos/1", tmp_path)


def test_the_downloaded_file_is_the_one_yt_dlp_names(tmp_path, monkeypatch):
    local_on(monkeypatch)

    class Named(FakeYDLBase):
        def extract_info(self, url, download=True):
            return {"id": "x", "ext": "webm", "_path": str(tmp_path / "wrong.webm")}

        def process_ie_result(self, meta, download=True):
            (tmp_path / "source_audio.m4a").write_bytes(b"whole")
            return {**meta, "requested_downloads": [{"filepath": str(tmp_path / "source_audio.m4a")}]}

    monkeypatch.setitem(sys.modules, "yt_dlp", types.SimpleNamespace(YoutubeDL=Named))
    path, _ = local_download.audio("https://www.twitch.tv/videos/1", tmp_path)
    assert path.name == "source_audio.m4a"


def test_without_ffmpeg_a_link_is_not_downloaded_and_a_download_is_used_again(tmp_path, monkeypatch):
    """B8: ffmpeg is checked before the download (hours of the day); audio already fetched is converted, not fetched again."""
    local_on(monkeypatch, False)
    tickets = []

    class Ticket:
        def __init__(self, url, on_wait=None):
            tickets.append(url)
            self.source = {"url": url, "title": "t", "platform": "twitch", "id": "1"}

        def fetch(self, track, dest, start_s=None, end_s=None, on_progress=None):
            dest.write_bytes(b"fmp4")

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(media, "Ticket", Ticket)
    monkeypatch.setattr(ingest, "_has_ffmpeg", lambda: False)
    with pytest.raises(ingest.IngestError, match="ffmpeg not found"):
        ingest.from_link("https://www.twitch.tv/videos/1", tmp_path)
    assert tickets == []
    # downloaded once, then the conversion failed: the next run converts what is there
    monkeypatch.setattr(ingest, "_has_ffmpeg", lambda: True)
    monkeypatch.setattr(ingest, "_ffmpeg_to_wav", lambda src, wav: (_ for _ in ()).throw(ingest.IngestError("broken")))
    with pytest.raises(ingest.IngestError, match="broken"):
        ingest.from_link("https://www.twitch.tv/videos/1", tmp_path)
    assert len(tickets) == 1 and (tmp_path / "source_audio.mp4").exists()
    monkeypatch.setattr(ingest, "_ffmpeg_to_wav", lambda src, wav: wav.write_bytes(b"RIFF"))
    info = ingest.from_link("https://www.twitch.tv/videos/1", tmp_path)
    assert len(tickets) == 1 and info["title"] == "t" and not (tmp_path / "source_audio.mp4").exists()
    assert not (tmp_path / ingest.DOWNLOADED_INFO).exists()


def test_a_download_ffmpeg_finds_broken_is_fetched_again_next_time(tmp_path, monkeypatch):
    """A cut-short download that ffmpeg cannot read is not kept as «fetched»: «Продолжить» fetches it again."""
    local_on(monkeypatch, False)
    tickets = []

    class Ticket:
        def __init__(self, url, on_wait=None):
            tickets.append(url)
            self.source = {"url": url, "title": "t", "platform": "twitch", "id": "1"}

        def fetch(self, track, dest, start_s=None, end_s=None, on_progress=None):
            dest.write_bytes(b"fmp4")

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(media, "Ticket", Ticket)
    monkeypatch.setattr(ingest, "_has_ffmpeg", lambda: True)
    monkeypatch.setattr(ingest, "_ffmpeg_to_wav", lambda src, wav: (_ for _ in ()).throw(ingest.Unreadable("broken")))
    with pytest.raises(ingest.IngestError, match="broken"):
        ingest.from_link("https://www.twitch.tv/videos/1", tmp_path)
    assert not (tmp_path / "source_audio.mp4").exists() and not (tmp_path / ingest.DOWNLOADED_INFO).exists()
    monkeypatch.setattr(ingest, "_ffmpeg_to_wav", lambda src, wav: wav.write_bytes(b"RIFF"))
    ingest.from_link("https://www.twitch.tv/videos/1", tmp_path)
    assert len(tickets) == 2


def test_an_unreadable_source_json_is_made_again_not_a_traceback(tmp_path, monkeypatch):
    """B25: audio.wav is there, source.json is empty (a full disk): the facts are read again, the audio is kept."""
    video = tmp_path / "v.mp4"
    video.write_bytes(b"video")
    job = tmp_path / "job"
    job.mkdir()
    (job / "audio.wav").write_bytes(b"RIFF")
    (job / "source.json").write_text("", encoding="utf-8")
    monkeypatch.setattr(ingest, "_probe_duration", lambda p: 12.0)
    monkeypatch.setattr(ingest, "_ffmpeg_to_wav", lambda src, wav: (_ for _ in ()).throw(AssertionError("not again")))
    info = ingest.ingest(str(video), job)
    assert info["title"] == "v" and info["duration_s"] == 12.0 and info["source_key"].startswith("file:")
    assert ingest.ingest(str(video), job)["title"] == "v"
    assert not list(job.glob("*.tmp"))


def test_a_folder_of_another_recording_is_not_reused(tmp_path, monkeypatch):
    """A2: a job folder whose source.json is about another recording gives its clips to no one."""
    video = tmp_path / "b" / "stream.mp4"
    video.parent.mkdir()
    video.write_bytes(b"video")
    job = tmp_path / "job"
    job.mkdir()
    (job / "audio.wav").write_bytes(b"RIFF")
    (job / "source.json").write_text('{"kind": "file", "path": "/a/stream.mp4", "title": "stream"}', encoding="utf-8")
    with pytest.raises(ingest.IngestError, match="другая запись"):
        ingest.ingest(str(video), job)


def test_a_file_changed_since_its_audio_was_read_is_noticed(tmp_path, monkeypatch):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"video")
    job = tmp_path / "job"
    monkeypatch.setattr(ingest, "_probe_duration", lambda p: 1.0)
    monkeypatch.setattr(ingest, "_ffmpeg_to_wav", lambda src, wav: wav.write_bytes(b"RIFF"))
    ingest.ingest(str(video), job)
    video.write_bytes(b"another, longer video")
    with pytest.raises(ingest.IngestError, match="изменился"):
        ingest.ingest(str(video), job)


@pytest.mark.parametrize("a,b", [
    ("https://www.twitch.tv/videos/123", "https://www.twitch.tv/videos/123?t=1h2m3s"),
    ("https://www.youtube.com/watch?v=abcDEF12345", "https://youtu.be/abcDEF12345?si=xyz&t=60"),
    ("https://www.youtube.com/watch?v=abcDEF12345&list=PL1&index=3", "https://m.youtube.com/live/abcDEF12345"),
])
def test_one_recording_has_one_key_whatever_the_link_looks_like(a, b):
    assert ingest.source_key(a) == ingest.source_key(b)


def test_two_recordings_have_two_keys():
    assert ingest.source_key("https://www.twitch.tv/videos/123") != ingest.source_key("https://www.twitch.tv/videos/124")
    assert ingest.source_key("/a/stream.mp4") != ingest.source_key("/b/stream.mp4")
