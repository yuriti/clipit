"""VodCut's section of the page: the form becomes a job command, the estimate, the switches."""
import pytest

from smtv_core.events import Journal, contract
from smtv_core.llm import Answer
from smtv_core.settings import ModelSettings, Settings

from vodcut import options, page
from vodcut.model import Asker
from vodcut.tool import tool


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))


def test_vodcut_has_a_section_with_its_script():
    assert tool.page is page.page and (page.WEB / "section.js").exists() and (page.WEB / "section.css").exists()


def test_a_link_becomes_a_run_in_its_own_job_folder():
    job = page.start({"source": " https://www.twitch.tv/videos/123 ", "language": "RU", "max_clips": "8", "channel": "someone"})
    assert job.folder.parent == page.jobs() and job.folder.name.startswith("123_")
    assert job.args == ["run", "https://www.twitch.tv/videos/123", "--language", "ru", "--max-clips", "8", "--channel=someone", "--out", str(job.folder)]


def test_a_file_is_used_by_its_full_path_and_no_render_is_passed(tmp_path):
    video = tmp_path / "my stream.mp4"
    video.write_bytes(b"x")
    job = page.start({"source": str(video), "no_render": True})
    assert job.args[:2] == ["run", str(video.resolve())] and "--no-render" in job.args and "--max-clips" not in job.args


@pytest.mark.parametrize("fields, message", [
    ({}, "paste a link"), ({"source": "/no/such/file.mp4"}, "no such file"), ({"source": "https://x.tv/v/1", "language": "russian"}, "language"),
    ({"source": "https://x.tv/v/1", "max_clips": "many"}, "whole number"), ({"source": "https://x.tv/v/1", "max_clips": 500}, "from 1 to 100"),
])
def test_wrong_fields_say_what_to_fix(fields, message):
    with pytest.raises(ValueError, match=message):
        page.start(fields)


def test_estimate_counts_only_the_steps_left(monkeypatch):
    monkeypatch.setattr(page, "_probe", lambda source: {"duration_s": 7200.0, "title": "t", "kind": "link"})
    monkeypatch.setattr(page, "_has_gpu", lambda: False)
    fresh = page.estimate({"source": "https://www.twitch.tv/videos/9"})
    assert fresh["clips"] == 7                                       # about 3.5 per hour, as production
    assert [s["name"] for s in fresh["steps"]] == ["audio", "speech", "scan", "rating", "fit", "render", "recap"] and not fresh["resumes"]
    assert {s["name"]: s["seconds"] for s in fresh["steps"]}["fit"] == 13         # 7 clips: two requests side by side
    assert 300 < {s["name"]: s["seconds"] for s in fresh["steps"]}["recap"] < 400   # 2 h: ~10 min of the stream fetched and encoded
    from smtv_core.settings import Settings
    settings = Settings.load()
    options.set_option(settings, "recap", False)
    settings.save()
    assert "recap" not in [s["name"] for s in page.estimate({"source": "https://www.twitch.tv/videos/9"})["steps"]]
    from vodcut.pipeline import job_dir
    folder = job_dir("https://www.twitch.tv/videos/9", page.jobs())
    folder.mkdir(parents=True)
    (folder / "audio.wav").write_bytes(b"")
    (folder / "transcript.json").write_text("{}", encoding="utf-8")
    again = page.estimate({"source": "https://www.twitch.tv/videos/9", "no_render": True})
    steps = {s["name"]: s["seconds"] for s in again["steps"]}
    assert steps["audio"] == 0 and steps["speech"] == 0 and "render" not in steps and again["resumes"] and again["seconds"] < fresh["seconds"]


def test_a_short_recording_is_not_promised_six_clips(monkeypatch):
    monkeypatch.setattr(page, "_probe", lambda source: {"duration_s": 63.0, "title": "t", "kind": "file"})
    monkeypatch.setattr(page, "_has_gpu", lambda: False)
    assert page.estimate({"source": "https://www.twitch.tv/videos/10"})["clips"] == 1


def test_switches_are_listed_and_changed_through_the_page():
    settings = Settings()
    assert {o["name"]: o["value"] for o in page.list_options(settings)} == {"loudness": True, "bleep": True, "peak_lines": False, "ad_blur": True, "precise": True,
                                                                          "critic": options.CRITIC_DEFAULT, "recap": options.RECAP_DEFAULT, "local_download": False}
    page.page.set_option(settings, "peak_lines", True)
    assert {o["name"]: o["value"] for o in page.list_options(settings)}["peak_lines"] is True


def test_describe_reads_the_source_and_counts_clips(tmp_path):
    (tmp_path / "source.json").write_text('{"title": "A stream", "channel": "someone", "platform": "twitchvod", "url": "https://x", "duration_s": 60}', encoding="utf-8")
    (tmp_path / "clips").mkdir()
    (tmp_path / "clips" / "clip01.mp4").write_bytes(b"")
    assert page.describe(tmp_path) == {"title": "A stream", "channel": "someone", "platform": "twitchvod", "duration_s": 60, "source": "https://x", "clips": 1}


def test_a_model_call_carries_its_cost_when_prices_are_set(tmp_path):
    model = ModelSettings(provider="openai", model="m", price_in=2.0, price_out=8.0)
    caller = lambda m, prompt, schema, images=None: Answer({"ok": True}, "", 1.2, 1_000_000, 500_000)  # noqa: E731
    with Journal(tmp_path, tool="vodcut", subscribers=[]) as j:
        Asker(model, caller, journal=j).ask("p", {"type": "object"}, purpose="rating")
        Asker(ModelSettings(provider="openai", model="m"), caller, journal=j).ask("p", {"type": "object"}, purpose="rating")
        priced, unpriced = j.read()
    assert priced["data"]["cost_usd"] == 6.0 and "cost_usd" not in unpriced["data"]
    assert contract.validate(priced) == [] and contract.undeclared(priced) == []


def test_vodcut_plugs_into_the_window_as_a_kind_of_request():
    import json
    req = page.page.request
    words = {lang: json.loads((page.WEB / "i18n" / f"{lang}.json").read_text(encoding="utf-8")) for lang in ("en", "ru")}
    assert words["ru"][req.title] == "Запись стрима" and words["en"][req.title] and req.icon      # keys of its words (V9)
    assert words["ru"][page.page.about] and words["en"][page.page.about] and page.page.icon and page.page.nav is None
    js = (page.WEB / "section.js").read_text(encoding="utf-8")
    assert "export function mountNew(root, api)" in js and "export function mountJob(root, api, id)" in js
    assert "export function mount(" not in js          # the old one-section contract is gone
    assert "api.openRequest(" in js and "api.refreshRequests(" in js


# --- the channel's picture in the list of requests ------------------------------------------------------------

def _job(tmp_path, source):
    folder = tmp_path / "job"
    folder.mkdir()
    (folder / "source.json").write_text(__import__("json").dumps(source), encoding="utf-8")
    return folder


def test_the_channel_page_is_known_only_for_a_real_channel():
    from vodcut import avatar
    assert avatar.channel_page({"platform": "twitchvod", "channel": "Vika_Karter"}) == ("twitch-vika_karter", "https://www.twitch.tv/vika_karter")
    assert avatar.channel_page({"platform": "twitchvod", "channel_id": "login_1", "channel": "Кириллица"})[1].endswith("/login_1")
    uc = "UC" + "a" * 22
    assert avatar.channel_page({"platform": "youtube", "channel_id": uc}) == (f"youtube-{uc}", f"https://www.youtube.com/channel/{uc}")
    for bad in ({"platform": "file"}, {"platform": "twitchvod", "channel": "../../x"}, {"platform": "twitchvod", "channel": "Кириллица"},
                {"platform": "youtube", "channel_id": "evil.com/x"}, {"platform": "youtube"}):
        assert avatar.channel_page(bad) is None


def test_only_a_picture_from_the_platforms_own_hosts_is_taken():
    from vodcut import avatar
    page = '<meta property="og:image" content="https://static-cdn.jtvnw.net/jtv_user_pictures/x-profile_image-300x300.png"/>'
    assert avatar.image_url(page, "twitchvod").endswith("profile_image-300x300.png")
    assert avatar.image_url('<meta property="og:image" content="https://static-cdn.jtvnw.net/ttv-static-metadata/twitch_logo3.jpg">', "twitchvod") is None
    assert avatar.image_url('<meta property="og:image" content="https://evil.example/a.png">', "youtube") is None
    assert avatar.image_url("<meta property='og:image' content='https://yt3.googleusercontent.com/abc=s900'>", "youtube").startswith("https://yt3.")
    assert avatar.image_url("<html></html>", "twitchvod") is None


def test_the_picture_lands_in_the_job_and_is_kept_once_per_channel(tmp_path, monkeypatch):
    from vodcut import avatar
    calls = []

    def fake_get(url, limit):
        calls.append(url)
        if "twitch.tv" in url:
            return b'<meta property="og:image" content="https://static-cdn.jtvnw.net/u/p-profile_image-300x300.png">', "text/html"
        return b"\x89PNG...", "image/png"
    monkeypatch.setattr(avatar, "_get", fake_get)
    folder = _job(tmp_path, {"platform": "twitchvod", "channel": "someone"})
    assert avatar.fetch(folder, tmp_path / "cache") == "avatar.png" and (folder / "avatar.png").read_bytes() == b"\x89PNG..."
    other = tmp_path / "job2"
    other.mkdir()
    (other / "source.json").write_text((folder / "source.json").read_text(encoding="utf-8"), encoding="utf-8")
    assert avatar.fetch(other, tmp_path / "cache") == "avatar.png" and len(calls) == 2       # the same channel: no new download


def test_a_failed_look_is_not_repeated_for_a_day_and_a_file_is_never_looked_up(tmp_path, monkeypatch):
    from vodcut import avatar
    monkeypatch.setattr(avatar, "_get", lambda url, limit: (_ for _ in ()).throw(OSError("offline")))
    folder = _job(tmp_path, {"platform": "twitchvod", "channel": "someone"})
    assert avatar.fetch(folder, tmp_path / "cache") is None and (folder / avatar.MISS).exists()
    assert avatar.due(folder) is False and avatar.due(folder, now=__import__("time").time() + avatar.RETRY_S + 1) is True
    started = []
    monkeypatch.setattr(avatar.threading, "Thread", lambda **kw: started.append(kw) or type("T", (), {"start": lambda self: None})())
    assert avatar.ensure(folder, tmp_path / "cache") is None and started == []                   # failed today: not again
    file_job = tmp_path / "f"
    file_job.mkdir()
    (file_job / "source.json").write_text('{"platform": "file", "kind": "file"}', encoding="utf-8")
    assert avatar.ensure(file_job, tmp_path / "cache") is None and started == []


def test_describe_names_the_picture_once_it_is_there(tmp_path):
    folder = _job(tmp_path, {"platform": "file", "title": "x"})
    assert "avatar" not in page.describe(folder)
    (folder / "avatar.jpg").write_bytes(b"jpg")
    assert page.describe(folder)["avatar"] == "avatar.jpg"


def test_the_new_request_is_one_field_and_takes_a_file_dropped_on_the_whole_window():
    js = (page.WEB / "section.js").read_text(encoding="utf-8")
    form = js[js.index("export function mountNew"):js.index("export function mountJob")]
    for gone in ("max_clips", "no_render", "channel", "vc-more", "LANGS"):        # owner 20.11: one field, nothing else
        assert gone not in form
    assert 'language: "auto"' in form                                            # the language chooses itself
    assert 'document.addEventListener("drop", dropped)' in form and 'document.removeEventListener("drop", dropped)' in form   # only while open


def test_a_clip_card_is_only_the_picture_and_opens_the_viewer_with_the_transcript():
    js = (page.WEB / "section.js").read_text(encoding="utf-8")
    draw = js[js.index("  function drawClip(id) {"):js.index("  // --- the viewer")]
    for gone in ("vc-clip-title", "vc-dl", "post_text", "vc-chips"):          # owner 20.11: only the card on the grid
        assert gone not in draw
    assert "openViewer(c.id)" in draw
    viewer = js[js.index("  async function openViewer"):js.index("  function openJob")]
    assert 'jobFile("transcript.json")' in js and ".ass" not in viewer         # the text comes from the transcript, the video is not touched
    assert "requestAnimationFrame(follow)" in viewer                            # the word being said is followed while it plays


def test_run_again_is_a_new_request_beside_the_old_one_with_its_audio(tmp_path):
    old = tmp_path / "2933609914"
    old.mkdir()
    (old / "audio.wav").write_bytes(b"RIFF")
    (old / "source.json").write_text("{}", encoding="utf-8")
    (old / "clips").mkdir()
    args = ["run", "https://www.twitch.tv/videos/2933609914", "--language", "auto", "--out", str(old)]
    job = page.again(old, args)
    assert job.folder == tmp_path / "2933609914-2" and job.args == [*args[:4], "--out", str(job.folder)]
    assert (job.folder / "audio.wav").read_bytes() == b"RIFF" and (job.folder / "source.json").exists()   # the audio is not fetched again
    assert not (job.folder / "clips").exists() and (old / "clips").exists()                               # the old request stays, the new one starts clean
    assert page.again(job.folder, job.args).folder == tmp_path / "2933609914-3"                           # from a copy: the next free name


def _parse(argv):
    import argparse
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    tool.add_commands(sub.add_parser("vodcut"))
    return parser.parse_args(["vodcut", *argv])


def test_a_terminal_run_becomes_the_same_job_as_from_the_window(tmp_path, monkeypatch):
    """Stage 16: `smtv vodcut run …` typed while SMTV runs goes to SMTV with the window's folder and arguments."""
    spec = page.command_job(_parse(["run", "https://www.twitch.tv/videos/123", "--language", "ru", "--max-clips", "8", "--workers", "2"]))
    assert spec.folder.name.startswith("123_") and spec.echo is not None
    assert spec.args == ["run", "https://www.twitch.tv/videos/123", "--language", "ru", "--max-clips", "8", "--workers", "2", "--out", str(spec.folder)]
    monkeypatch.chdir(tmp_path)
    (tmp_path / "my stream.mp4").write_bytes(b"x")
    spec = page.command_job(_parse(["run", "my stream.mp4", "--no-render"]))     # a relative file: the job runs in its own folder
    assert spec.args[:2] == ["run", str((tmp_path / "my stream.mp4").resolve())] and spec.folder.name.startswith("my-stream_")
    assert "--no-render" in spec.args


def test_render_and_recap_from_a_terminal_are_jobs_only_with_clips_to_work_on(tmp_path):
    assert page.command_job(_parse(["render", "https://www.twitch.tv/videos/9"])) is None      # nothing analysed: the command says so
    from vodcut.pipeline import job_dir
    folder = job_dir("https://www.twitch.tv/videos/9", page.jobs())
    folder.mkdir(parents=True)
    (folder / "clips.json").write_text("{}", encoding="utf-8")
    spec = page.command_job(_parse(["render", "https://www.twitch.tv/videos/9", "--clips", "clip01"]))
    assert spec.folder == folder and spec.args == ["render", str(folder), "--clips", "clip01"]
    assert page.command_job(_parse(["recap", str(folder)])).args == ["recap", str(folder)]
    assert page.command_job(_parse(["set"])) is None and page.command_job(_parse(["check"])) is None


def test_a_channel_name_starting_with_a_dash_is_not_an_option(tmp_path):
    """C2: «-nick» after --channel would be read by argparse as an option (exit code 2)."""
    job = page.start({"source": "https://www.twitch.tv/videos/5", "channel": "-nick"})
    assert "--channel=-nick" in job.args
    assert _parse(job.args).channel == "-nick"


def test_run_again_after_unanswered_parts_takes_the_kept_answers_along(tmp_path):
    """A1, decision 1: a request finished with parts the model did not answer — «Run again» asks only for those."""
    old = tmp_path / "rec_ab12cd34"
    old.mkdir()
    for name in ("audio.wav", "source.json", "transcript.json", "pass1.windows.json", "pass2.items.json"):
        (old / name).write_text("{}", encoding="utf-8")
    job = page.again(old, ["run", "x.mp4", "--out", str(old)])
    assert {p.name for p in job.folder.iterdir()} >= {"transcript.json", "pass1.windows.json", "pass2.items.json"}
    full = tmp_path / "full_ab12cd34"
    full.mkdir()
    for name in ("audio.wav", "source.json", "transcript.json", "pass1.json", "pass2.json", "pass1.windows.json"):
        (full / name).write_text("{}", encoding="utf-8")
    fresh = page.again(full, ["run", "x.mp4", "--out", str(full)])
    assert not (fresh.folder / "transcript.json").exists() and not (fresh.folder / "pass1.windows.json").exists()


def test_a_file_on_a_drive_that_does_not_answer_is_a_plain_error(tmp_path, monkeypatch):
    """B6: reading the file (ffmpeg -i) goes through proc.run with a time limit."""
    from smtv_core import proc
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x")

    def hangs(cmd, timeout_s, **kw):
        raise proc.TimedOut("ffprobe did not finish in 30 s and was stopped")
    monkeypatch.setattr(proc, "run", hangs)
    with pytest.raises(ValueError, match="did not open in 30 seconds"):
        page.estimate({"source": str(video)})
