"""В3 (review before release): the core's fixes — one way to run programs (UTF-8, no console window, the whole tree
stopped), names that pass everywhere, ffmpeg paths with any character, unfinished model downloads, 429 by code, no
second paid call after a timeout, the key file on Windows, and the small ones (C1, C6, C7, C9, C10)."""
from __future__ import annotations

import io
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types
import urllib.error
from pathlib import Path

import pytest

from smtv_core import checks, events, media, paths, proc, prompts
from smtv_core.asr import catalog, engines, whisper
from smtv_core.audio import loudness
from smtv_core.llm import keycheck, providers
from smtv_core.render import captions
from smtv_core.render.ffmpeg import _escape_filter_path
from smtv_core.settings import ModelSettings
from smtv_core.vault import Vault

POSIX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="the fake CLIs are scripts with #!")


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    for key in list(os.environ):
        if key.startswith("SMTV_") and key != "SMTV_HOME":
            monkeypatch.delenv(key)
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)
    return tmp_path / "home"


def script(tmp_path: Path, name: str, body: str) -> Path:
    f = tmp_path / name
    f.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    f.chmod(0o755)
    return f


# --- proc: one way to run a program ------------------------------------------------------------------------------

def test_text_goes_to_a_program_and_back_in_utf8():
    echo = "import sys; d = sys.stdin.buffer.read().decode('utf-8'); sys.stdout.buffer.write(('ответ: ' + d).encode('utf-8'))"
    done = proc.run([sys.executable, "-c", echo], 30, input="расшифровка 🎮 ёж")
    assert done.returncode == 0 and done.stdout == "ответ: расшифровка 🎮 ёж"


def test_without_input_the_program_reads_nothing():
    done = proc.run([sys.executable, "-c", "import sys; print(repr(sys.stdin.read()))"], 30)
    assert done.stdout.strip() == "''"


def test_on_windows_no_program_opens_a_console_window(monkeypatch):
    monkeypatch.setattr(proc.os, "name", "nt")
    no_window = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    assert proc.hidden()["creationflags"] & no_window
    flags = proc.group()["creationflags"]
    assert flags & no_window and flags & getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x200)
    seen = {}

    class Popen:
        def __init__(self, cmd, **kw):
            seen.update(kw)
            self.returncode, self.pid = 0, 1

        def communicate(self, input=None, timeout=None):  # noqa: A002
            seen["input"] = input
            return "", ""

    monkeypatch.setattr(proc.subprocess, "Popen", Popen)
    proc.run(["codex"], 5, input="x")
    assert seen["creationflags"] & no_window and seen["encoding"] == "utf-8" and seen["input"] == "x"


def test_off_windows_a_program_gets_its_own_group(monkeypatch):
    monkeypatch.setattr(proc.os, "name", "posix")
    assert proc.group() == {"start_new_session": True} and proc.hidden() == {}


def test_checks_and_sign_in_checks_go_through_proc(monkeypatch):
    calls = []

    def fake_run(cmd, timeout_s, **kw):
        calls.append((cmd, kw))
        return subprocess.CompletedProcess(cmd, 0, "ok", "")

    monkeypatch.setattr(proc, "run", fake_run)
    assert checks._run(["ffmpeg", "-version"]) == "ok"
    monkeypatch.setattr(keycheck.shutil, "which", lambda name: "/bin/" + name)
    assert keycheck.check(ModelSettings(provider="codex")).status == keycheck.OK
    assert keycheck.check(ModelSettings(provider="claude_code")).status == keycheck.OK
    assert [c[0][0] for c in calls] == ["ffmpeg", "/bin/codex", "/bin/claude"]


def test_a_program_that_hangs_in_a_check_is_no_answer(monkeypatch):
    def hang(cmd, timeout_s, **kw):
        raise proc.TimedOut("hung")

    monkeypatch.setattr(proc, "run", hang)
    assert checks._run(["nvidia-smi"]) is None


# --- A6, A7: Codex and Claude Code ------------------------------------------------------------------------------

FAKE_CODEX = """import json, os, sys
args = sys.argv[1:]
prompt = sys.stdin.buffer.read().decode("utf-8")
if os.environ.get("FAKE_CODEX_HANG") == "1":
    import subprocess, time
    subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])   # a grandchild holding the pipes
    time.sleep(600)
out = args[args.index("-o") + 1]
with open(out, "w", encoding="utf-8") as f:
    json.dump({"echo": prompt, "title": "Заголовок 🎯"}, f, ensure_ascii=False)
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 3, "output_tokens": 2}}))
"""

FAKE_CLAUDE = """import json, sys
prompt = sys.stdin.buffer.read().decode("utf-8")
sys.stdout.buffer.write(json.dumps({"type": "result", "is_error": False, "result": "",
    "structured_output": {"echo": prompt, "title": "Клип про ёжика 🦔"}}, ensure_ascii=False).encode("utf-8"))
"""


@POSIX_ONLY
def test_cli_providers_talk_utf8_whatever_the_locale(tmp_path, monkeypatch):
    monkeypatch.setenv("LC_ALL", "C")
    monkeypatch.setenv("PYTHONIOENCODING", "ascii")       # the program's own default would fail on Cyrillic
    codex = script(tmp_path, "codex", FAKE_CODEX)
    claude = script(tmp_path, "claude", FAKE_CLAUDE)
    prompt = "Расшифровка: «привет» 🎮"
    a = providers.call(ModelSettings(provider="codex", codex_bin=str(codex)), prompt, {"type": "object"})
    assert a.data == {"echo": prompt, "title": "Заголовок 🎯"} and (a.tokens_in, a.tokens_out) == (3, 2)
    b = providers.call(ModelSettings(provider="claude_code", claude_bin=str(claude)), prompt, {"type": "object"})
    assert b.data == {"echo": prompt, "title": "Клип про ёжика 🦔"}


@POSIX_ONLY
def test_a_codex_that_hangs_with_a_grandchild_is_stopped_in_time(tmp_path, monkeypatch):
    monkeypatch.setenv("FAKE_CODEX_HANG", "1")
    codex = script(tmp_path, "codex", FAKE_CODEX)
    started = time.monotonic()
    with pytest.raises(providers.Overloaded, match="did not answer within 1 s"):
        providers.call(ModelSettings(provider="codex", codex_bin=str(codex), timeout_s=1), "x", {"type": "object"})
    assert time.monotonic() - started < 15


# --- A13: 429 by its code, not by its words ---------------------------------------------------------------------

GEMINI_MINUTE = {"error": {"code": 429, "message": "You exceeded your current quota, please check your plan and billing details.",
                           "status": "RESOURCE_EXHAUSTED", "details": [
                               {"@type": "type.googleapis.com/google.rpc.QuotaFailure",
                                "violations": [{"quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"}]},
                               {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "7s"}]}}
GEMINI_DAY = {"error": {"code": 429, "message": "You exceeded your current quota, please check your plan and billing details.",
                        "details": [{"@type": "type.googleapis.com/google.rpc.QuotaFailure",
                                     "violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}}
OPENAI_RATE = {"error": {"message": "Rate limit reached for requests per min. Visit https://platform.openai.com/account/billing",
                         "type": "requests", "code": "rate_limit_exceeded"}}
OPENAI_MONEY = {"error": {"message": "You exceeded your current quota, please check your plan and billing details.",
                          "type": "insufficient_quota", "code": "insufficient_quota"}}


def _http_error(code, body, headers=None):
    return urllib.error.HTTPError("https://x", code, "err", headers or {}, io.BytesIO(json.dumps(body).encode()))


@pytest.mark.parametrize("body,money", [(GEMINI_MINUTE, False), (GEMINI_DAY, True), (OPENAI_RATE, False), (OPENAI_MONEY, True)])
def test_a_rate_limit_is_waited_out_and_only_spent_money_stops(monkeypatch, body, money):
    calls, slept = [], []

    def refuse(*_a, **_k):
        calls.append(1)
        raise _http_error(429, body)

    monkeypatch.setattr(providers.urllib.request, "urlopen", refuse)
    monkeypatch.setattr(providers.time, "sleep", slept.append)
    with pytest.raises(providers.QuotaExceeded if money else providers.Overloaded):
        providers._post("https://x", {}, {}, 5)
    assert len(calls) == (1 if money else 3)
    if body is GEMINI_MINUTE:
        assert slept == [7.0, 7.0], "Gemini's own retryDelay is waited"


def test_retry_after_is_waited_and_claude_out_of_credit_stops(monkeypatch):
    slept, n = [], []

    def busy_then_ok(*_a, **_k):
        n.append(1)
        if len(n) == 1:
            raise _http_error(429, {"error": {"type": "rate_limit_error"}}, {"Retry-After": "12"})
        return io.BytesIO(b'{"ok": 1}')

    monkeypatch.setattr(providers.urllib.request, "urlopen", busy_then_ok)
    monkeypatch.setattr(providers.time, "sleep", slept.append)
    assert providers._post("https://x", {}, {}, 5) == {"ok": 1} and slept == [12.0]
    assert providers.out_of_money(400, '{"error":{"message":"Your credit balance is too low to access the API"}}')
    assert not providers.out_of_money(400, '{"error":{"message":"bad model"}}')


def test_cloud_speech_judges_429_the_same_way(monkeypatch):
    from smtv_core.asr import cloud
    calls = []

    def refuse(*_a, **_k):
        calls.append(1)
        raise _http_error(429, OPENAI_RATE)

    monkeypatch.setattr(providers.urllib.request, "urlopen", refuse)
    monkeypatch.setattr(providers.time, "sleep", lambda s: None)
    with pytest.raises(providers.Overloaded):
        cloud._send("https://x", b"x", "text/plain", "k", 5)
    assert len(calls) == 3


# --- B2: no second paid call after a timeout ----------------------------------------------------------------------

def test_a_call_that_timed_out_after_sending_is_not_paid_again(monkeypatch):
    calls = []

    def slow(*_a, **_k):
        calls.append(1)
        raise TimeoutError("The read operation timed out")

    monkeypatch.setattr(providers.urllib.request, "urlopen", slow)
    monkeypatch.setattr(providers.time, "sleep", lambda s: None)
    with pytest.raises(providers.Overloaded, match="did not answer in 300 s"):
        providers._post("https://x", {}, {}, 300)
    assert len(calls) == 1


def test_a_call_that_never_reached_the_service_is_tried_again(monkeypatch):
    calls = []

    def down(*_a, **_k):
        calls.append(1)
        raise urllib.error.URLError(ConnectionRefusedError("refused"))

    monkeypatch.setattr(providers.urllib.request, "urlopen", down)
    monkeypatch.setattr(providers.time, "sleep", lambda s: None)
    with pytest.raises(providers.Overloaded, match="could not reach"):
        providers._post("https://x", {}, {}, 5)
    assert len(calls) == 3


# --- names --------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text,want", [
    ("стрим_23_11", "strim_23_11"),
    ("Мой стрим", "Moy-strim"),
    ("_23_11", "23_11"),
    ("", "video"),
    ("   ", "video"),
    ("Стрим вчера!!", "Strim-vchera"),
    ("Щука Ёж", "Shchuka-Ezh"),
    ("it's a [test]", "it-s-a-test"),
    ("日本語", "video"),
])
def test_names_are_latin_readable_and_start_with_a_letter_or_digit(text, want):
    got = paths.safe_name(text)
    assert got == want
    assert got[0].isalnum() and all(c.isalnum() or c in "._-" for c in got) and got.isascii()


def test_names_are_cut_and_hashes_are_short_and_stable():
    assert len(paths.safe_name("а" * 500)) <= 60
    assert paths.short_hash("x") == paths.short_hash("x") != paths.short_hash("y") and len(paths.short_hash("x")) == 8


# --- A9: any character in the path of the captions ---------------------------------------------------------------

ASS = """[Script Info]
ScriptType: v4.00+
PlayResX: 320
PlayResY: 240
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,1,0,2,10,10,10,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,hi
"""
AWKWARD = ["it's", "a:b", "[x]", "a,b;c", "Анна папка", "x y", "O'Brien's [old], copy;2"]


def test_a_windows_path_is_written_with_slashes_and_every_special_character_escaped():
    got = _escape_filter_path(Path("C:\\Users\\O'Brien\\a,b"), windows=True)   # str of a Path on Windows
    assert got.startswith("C\\\\:/Users/O") and "'" not in got.replace("\\'", "") and "\\," in got


def _ffmpeg_with_ass() -> str | None:
    for folder in ("/opt/homebrew/opt/ffmpeg-full/bin", "/usr/local/opt/ffmpeg-full/bin", ""):
        exe = shutil.which("ffmpeg", path=folder or None)
        if exe and "ass" in subprocess.run([exe, "-hide_banner", "-filters"], capture_output=True, text=True).stdout.split():
            return exe
    return None


@pytest.mark.parametrize("name", AWKWARD)
def test_ffmpeg_reads_captions_from_a_folder_with_any_name(name):
    exe = _ffmpeg_with_ass()
    if not exe:
        pytest.skip("no ffmpeg with libass here")
    folder = Path(tempfile.mkdtemp()) / name
    folder.mkdir()
    ass = folder / "c.ass"
    ass.write_text(ASS, encoding="utf-8")
    graph = f"[0:v]ass=filename={_escape_filter_path(ass)}:fontsdir={_escape_filter_path(folder)}[v]"
    done = subprocess.run([exe, "-v", "error", "-f", "lavfi", "-i", "color=s=320x240:d=0.2", "-filter_complex", graph,
                           "-map", "[v]", "-f", "null", "-"], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


# --- A11: a speech model downloaded half way ----------------------------------------------------------------------

def test_a_model_downloaded_half_way_is_not_taken_for_one_on_this_computer(tmp_path):
    folder = tmp_path / "gigaam"
    folder.mkdir()
    (folder / "encoder.onnx").write_bytes(b"x")
    assert engines.installed(engines.GIGAAM, tmp_path), "a folder from an older SMTV, without the mark, counts"
    engines.downloading_mark(folder).write_text("", encoding="utf-8")
    assert not engines.installed(engines.GIGAAM, tmp_path)
    assert not catalog.is_installed(catalog.MODELS["gigaam"], tmp_path)


def test_loading_a_half_model_downloads_it_again_and_clears_the_mark(tmp_path, monkeypatch):
    folder = tmp_path / "gigaam"
    folder.mkdir()
    (folder / "encoder.onnx").write_bytes(b"x")
    engines.downloading_mark(folder).write_text("", encoding="utf-8")
    seen = {}

    def load_model(name, where, providers=None):
        seen["existed"] = Path(where).exists()
        seen["mark"] = engines.downloading_mark(Path(where)).exists()
        Path(where).mkdir()
        (Path(where) / "encoder.onnx").write_bytes(b"x")
        (Path(where) / "decoder.onnx").write_bytes(b"x")
        return types.SimpleNamespace(with_timestamps=lambda: types.SimpleNamespace())

    monkeypatch.setitem(sys.modules, "onnx_asr", types.SimpleNamespace(load_model=load_model))
    monkeypatch.setattr(engines, "providers", lambda: ["CPUExecutionProvider"])
    engines.Recognizer(engines.GIGAAM, tmp_path).load()
    assert seen == {"existed": False, "mark": True}, "the half folder went first, the mark stood during the download"
    assert engines.installed(engines.GIGAAM, tmp_path)


def test_a_download_that_fails_leaves_the_mark(tmp_path, monkeypatch):
    def load_model(name, where, providers=None):
        Path(where).mkdir()
        (Path(where) / "encoder.onnx").write_bytes(b"x")
        raise ConnectionError("the network went away")

    monkeypatch.setitem(sys.modules, "onnx_asr", types.SimpleNamespace(load_model=load_model))
    monkeypatch.setattr(engines, "providers", lambda: ["CPUExecutionProvider"])
    with pytest.raises(ConnectionError):
        engines.Recognizer(engines.GIGAAM, tmp_path).load()
    assert not engines.installed(engines.GIGAAM, tmp_path)


def test_whisper_downloaded_half_way_is_not_installed(tmp_path, monkeypatch):
    def download_model(repo, output_dir):
        (Path(output_dir) / "model.bin").write_bytes(b"x")
        (Path(output_dir) / "config.json").write_text("{}", encoding="utf-8")
        raise KeyboardInterrupt

    monkeypatch.setitem(sys.modules, "faster_whisper", types.ModuleType("faster_whisper"))
    monkeypatch.setitem(sys.modules, "faster_whisper.utils", types.SimpleNamespace(download_model=download_model))
    with pytest.raises(KeyboardInterrupt):
        whisper.download(tmp_path)
    assert not whisper.installed(tmp_path)
    monkeypatch.setitem(sys.modules, "faster_whisper.utils", types.SimpleNamespace(download_model=lambda repo, output_dir: None))
    whisper.download(tmp_path)
    assert whisper.installed(tmp_path)
    catalog.remove(catalog.MODELS["whisper"], tmp_path)
    assert not engines.downloading_mark(tmp_path / "whisper").exists()


# --- decision 5: the key file on Windows ------------------------------------------------------------------------

def test_on_windows_the_key_file_stays_on_this_computer(monkeypatch, tmp_path):
    monkeypatch.setattr(paths.sys, "platform", "win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local"))
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    monkeypatch.delenv("SMTV_HOME")
    assert paths.secrets_key_file() == tmp_path / "Local" / "smtv" / "secrets.key"
    assert paths.secrets_file() == tmp_path / "Roaming" / "smtv" / "secrets.json"
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "portable"))
    assert paths.secrets_key_file() == tmp_path / "portable" / "secrets.key", "a portable folder keeps its key"


def test_the_key_file_of_an_older_smtv_is_moved_and_no_key_is_lost(tmp_path):
    roaming, local = tmp_path / "Roaming" / "smtv", tmp_path / "Local" / "smtv"
    old = Vault(roaming / "secrets.json", roaming / "secrets.key")
    old.set("openai", "sk-старый-ключ")
    new = Vault(roaming / "secrets.json", local / "secrets.key")
    assert new.get("openai") == "sk-старый-ключ"
    assert (local / "secrets.key").exists() and not (roaming / "secrets.key").exists()
    new.set("gemini", "g")
    assert Vault(roaming / "secrets.json", local / "secrets.key").get("gemini") == "g"


# --- C1, C6, C7, C9, C10 ------------------------------------------------------------------------------------------

def test_a_value_with_a_placeholder_in_it_is_not_filled_again():
    assert prompts.fill("{title}|{transcript}", title="{transcript}", transcript="X") == "{transcript}|X"
    assert prompts.fill('{"a": 1} {channel}', channel="c") == '{"a": 1} c'


def test_a_backslash_from_a_transcript_never_makes_a_caption_tag():
    out = captions.esc("a\\Nb {x}")
    assert "\\N" not in out and "\\{x\\}" in out and out.replace("\u2060", "") == "a\\\\Nb \\{x\\}".replace("\\\\", "\\")


def test_no_loudness_reading_is_said_in_the_log(monkeypatch, capsys, tmp_path):
    monkeypatch.setattr(proc, "run", lambda cmd, t, **kw: subprocess.CompletedProcess(cmd, 0, "nothing", ""))
    assert loudness.normalize(tmp_path / "clip.mp4", 5) is None
    assert "no reading for clip.mp4" in capsys.readouterr().err
    assert math.isnan(loudness.parse_measure("nothing"))


def test_an_answer_without_a_ticket_is_a_media_error(monkeypatch):
    monkeypatch.setattr(media, "_json", lambda *a, **k: {"state": "ready"})
    with pytest.raises(media.MediaError) as e:
        media.Ticket("https://www.twitch.tv/videos/2934906889", sleep=lambda s: None)
    assert e.value.retryable


def test_a_failed_segment_does_not_wait_for_the_others(monkeypatch, tmp_path):
    t = media.Ticket.__new__(media.Ticket)
    t.url, t.id, t.on_wait, t.wait_s, t.sleep = "u", "t1", None, 1, lambda s: None
    listing = {"init": "init.mp4", "segments": [{"name": f"{i}.mp4", "start": i, "duration": 1} for i in range(8)]}
    monkeypatch.setattr(media.Ticket, "playlist", lambda self, track: listing)

    def segment(self, track, name):
        if name == "init.mp4":
            return b"i"
        if name == "0.mp4":
            raise media.MediaError("media_segment_gone", "gone")
        time.sleep(3)
        return b"x"

    monkeypatch.setattr(media.Ticket, "_segment", segment)
    started = time.monotonic()
    with pytest.raises(media.MediaError):
        t.fetch("audio", tmp_path / "a.mp4")
    assert time.monotonic() - started < 2.5
    assert not list(tmp_path.glob("a.mp4*"))


def test_an_event_that_could_not_be_written_leaves_no_gap(tmp_path, monkeypatch):
    j = events.Journal(tmp_path / "job", tool="t", subscribers=[])
    j.emit("stage", name="a")
    real_open = Path.open

    def broken(self, *a, **k):
        if self.name == events.FILE_NAME:
            raise OSError(28, "No space left on device")
        return real_open(self, *a, **k)

    monkeypatch.setattr(Path, "open", broken)
    with pytest.raises(OSError):
        j.emit("stage", name="b")
    monkeypatch.setattr(Path, "open", real_open)
    assert j.emit("stage", name="c")["n"] == 2
