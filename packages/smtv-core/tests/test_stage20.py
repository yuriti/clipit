"""Stage 20: presets of the OpenAI-compatible kind, the schema→object fallback, Ollama's own API with the window size,
the cloud Whisper's cutting into ≤25 MB windows, and the speech model of each language."""
import http.server
import json
import threading
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

from smtv_core import presets
from smtv_core.asr import catalog as speech
from smtv_core.asr import cloud, whisper
from smtv_core.asr.language import choose
from smtv_core.llm import ollama, providers
from smtv_core.settings import OPENAI, ModelSettings, Provider, Settings

SCHEMA = {"type": "object", "properties": {"n": {"type": "integer"}}, "required": ["n"]}
KEY = "sk-test-STAGE20-0123456789abcdef"  # gitleaks:allow (made-up key)


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)
    providers._no_schema.clear()
    ollama._shown.clear()


class Fake:
    """A tiny HTTP server: `answer(path, body) -> (status, dict | list of dicts as NDJSON)`; requests are kept."""

    def __init__(self, answer):
        self.seen = []
        fake = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _go(self):
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n) if n else b""
                try:
                    body = json.loads(raw) if raw and self.headers.get("Content-Type", "").startswith("application/json") else raw
                except ValueError:
                    body = raw
                fake.seen.append((self.command, self.path, body, dict(self.headers)))
                status, data = answer(self.path, body)
                out = b"".join(json.dumps(x).encode() + b"\n" for x in data) if isinstance(data, list) else json.dumps(data).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

            do_GET = do_POST = do_DELETE = _go

        self.srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


# --- presets ------------------------------------------------------------------------------------------------------

def test_every_preset_is_complete_and_the_named_services_are_there():
    ids = [p.id for p in presets.PRESETS_LIST]
    assert len(ids) == len(set(ids))
    assert set(presets.LOCAL) == {"ollama", "lmstudio", "vllm", "llamacpp"}
    assert set(presets.CLOUD) == {"deepseek", "groq", "mistral", "xai", "together", "fireworks", "qwen", "kimi", "glm", "cerebras"}
    for p in presets.PRESETS_LIST:
        assert p.json_mode in ("schema", "object"), p.id
        if p.id != "custom":
            assert p.base_url.startswith("https://" if not p.local else "http://127.0.0.1:"), p.id
            assert p.key_url.startswith("https://"), p.id
    assert presets.BY_ID["ollama"].base_url.endswith(":11434") and presets.BY_ID["ollama"].api == "ollama"
    assert [presets.BY_ID[i].base_url.rsplit(":", 1)[1] for i in ("lmstudio", "vllm", "llamacpp")] == ["1234/v1", "8000/v1", "8080/v1"]


def test_local_presets_need_no_key_cloud_ones_do_and_ollama_has_its_column():
    local = Provider(id="ollama", kind=OPENAI, preset="ollama", base_url=presets.BY_ID["ollama"].base_url)
    cloud_p = Provider(id="deepseek", kind=OPENAI, preset="deepseek", base_url=presets.BY_ID["deepseek"].base_url)
    own = Provider(id="mine", kind=OPENAI, preset="custom", base_url="https://my.server/v1")
    assert local.local() and not local.needs_key() and local.table_key() == "ollama"
    assert local.connection("qwen3:14b").api == "ollama"
    assert not cloud_p.local() and cloud_p.needs_key() and cloud_p.table_key() is None and cloud_p.connection("x").api == "openai"
    assert not own.needs_key()                    # an own address may take no key
    assert presets.preset_of_url("https://api.groq.com/openai/v1") == "groq"
    assert presets.preset_of_url("http://127.0.0.1:11434") == "custom"


def test_find_on_this_computer_counts_only_a_server_that_lists_its_models():
    ollama_srv = Fake(lambda path, body: (200, {"models": [{"name": "qwen3:8b"}]}) if path == "/api/tags" else (404, {}))
    other = Fake(lambda path, body: (200, {"hello": "I am something else"}))
    try:
        found = presets.probe(presets.BY_ID["ollama"], ollama_srv.url)
        assert found["found"] and found["models"] == ["qwen3:8b"]
        assert not presets.probe(presets.BY_ID["lmstudio"], other.url + "/v1")["found"]
        assert not presets.probe(presets.BY_ID["vllm"], "http://127.0.0.1:9/v1", timeout=0.5)["found"]
    finally:
        ollama_srv.close()
        other.close()


# --- the schema → object fallback ----------------------------------------------------------------------------------

def _openai(answer):
    srv = Fake(answer)
    m = ModelSettings(provider=OPENAI, model="m1", base_url=srv.url + "/v1", json_mode="schema", timeout_s=5)
    return srv, m


def _reply(text):
    return {"choices": [{"message": {"content": text}}], "usage": {"prompt_tokens": 3, "completion_tokens": 1}}


def test_a_server_that_refuses_the_schema_is_asked_once_more_for_an_object_and_remembered():
    def answer(path, body):
        if body["response_format"]["type"] == "json_schema":
            return 400, {"error": {"message": "response_format json_schema is not supported by this model"}}
        return 200, _reply('{"n": 7}')
    srv, m = _openai(answer)
    try:
        a = providers.call(m, "count", SCHEMA)
        assert a.data == {"n": 7}
        kinds = [b["response_format"]["type"] for _, _, b, _ in srv.seen]
        assert kinds == ["json_schema", "json_object"]
        assert '"required": ["n"]' in srv.seen[1][2]["messages"][0]["content"][0]["text"]    # the schema rides in the prompt
        providers.call(m, "count", SCHEMA)
        assert [b["response_format"]["type"] for _, _, b, _ in srv.seen][2:] == ["json_object"]   # no second refusal
    finally:
        srv.close()


def test_the_object_answer_is_checked_against_the_schema():
    srv, m = _openai(lambda path, body: (200, _reply('{"n": "seven"}')))
    m.json_mode = "object"
    try:
        with pytest.raises(providers.ProviderError, match="does not match the schema"):
            providers.call(m, "count", SCHEMA)
    finally:
        srv.close()


def test_another_refusal_is_not_retried_as_object():
    srv, m = _openai(lambda path, body: (400, {"error": {"message": "model m1 does not exist"}}))
    try:
        with pytest.raises(providers.ProviderError, match="HTTP 400"):
            providers.call(m, "count", SCHEMA)
        assert len(srv.seen) == 1
    finally:
        srv.close()


# --- Ollama -----------------------------------------------------------------------------------------------------

def test_num_ctx_follows_the_prompt_and_never_cuts_silently():
    assert ollama.MIN_CTX <= ollama.num_ctx("short") <= ollama.ANSWER_TOKENS + ollama.STEP_CTX
    long_prompt = "я" * 100_000
    ctx = ollama.num_ctx(long_prompt)
    assert ctx >= 100_000 / ollama.CHARS_PER_TOKEN + ollama.ANSWER_TOKENS and ctx % ollama.STEP_CTX == 0
    assert ollama.num_ctx("x" * 10_000, images=5) > ollama.num_ctx("x" * 10_000)
    assert ollama.num_ctx(long_prompt, limit=40960) == 40960            # never above the model's own window
    with pytest.raises(ollama.OllamaError, match="does not fit"):
        ollama.num_ctx("x" * 400_000, limit=40960)                      # 100k tokens at the very least: an error, not a cut


def test_ollama_is_called_through_its_own_chat_with_the_window_and_the_schema(tmp_path):
    frame = tmp_path / "f.jpg"
    frame.write_bytes(b"\xff\xd8jpeg")

    def answer(path, body):
        if path == "/api/show":
            return 200, {"capabilities": ["completion", "vision"], "model_info": {"qwen3vl.context_length": 40960}}
        if path == "/api/chat":
            return 200, {"message": {"content": '{"n": 3}'}, "prompt_eval_count": 50, "eval_count": 4}
        return 404, {"error": "no"}
    srv = Fake(answer)
    try:
        p = Provider(id="ollama", kind=OPENAI, preset="ollama", base_url=srv.url)
        a = providers.call(p.connection("qwen3-vl:8b"), "x" * 60_000, SCHEMA, [frame])
        chat = next(b for _, path, b, _ in srv.seen if path == "/api/chat")
        assert chat["options"]["num_ctx"] >= 60_000 / ollama.CHARS_PER_TOKEN and chat["options"]["num_ctx"] <= 40960
        assert chat["format"]["required"] == ["n"] and chat["stream"] is False and chat["messages"][0]["images"]
        assert a.data == {"n": 3} and (a.tokens_in, a.tokens_out) == (50, 4)
        assert not any(path.startswith("/v1") for _, path, _, _ in srv.seen)   # never the OpenAI-compatible path
    finally:
        srv.close()


def test_ollama_lists_pulls_with_progress_and_deletes():
    def answer(path, body):
        if path == "/api/tags":
            return 200, {"models": [{"name": "qwen3:8b", "size": 5_200_000_000, "details": {"parameter_size": "8.2B", "quantization_level": "Q4_K_M"}}]}
        if path == "/api/show":
            return 200, {"capabilities": ["completion"], "model_info": {"qwen3.context_length": 40960}}
        if path == "/api/pull" and body["model"] == "qwen3:8b":
            return 200, [{"status": "pulling manifest"}, {"status": "pulling abc", "total": 100, "completed": 40},
                         {"status": "pulling abc", "total": 100, "completed": 100}, {"status": "success"}]
        if path == "/api/pull":
            return 200, [{"error": "pull model manifest: file does not exist"}]
        if path == "/api/delete":
            return 200, {}
        return 404, {}
    srv = Fake(answer)
    try:
        rows = ollama.models(srv.url)
        assert rows == [{"id": "qwen3:8b", "size_bytes": 5_200_000_000, "params": "8.2B", "quant": "Q4_K_M", "images": False, "context": 40960}]
        seen = []
        ollama.pull(srv.url, "qwen3:8b", seen.append)
        assert [e["completed"] for e in seen] == [0, 40, 100, 0] and seen[-1]["status"] == "success"
        with pytest.raises(ollama.OllamaError, match="file does not exist"):
            ollama.pull(srv.url, "nope:1b")
        ollama.delete(srv.url, "qwen3:8b")
        assert ("DELETE", "/api/delete", {"model": "qwen3:8b"}) in [(a, b, c) for a, b, c, _ in srv.seen]
    finally:
        srv.close()
    with pytest.raises(ollama.OllamaError, match="not running"):
        ollama.models("http://127.0.0.1:9", timeout=0.5)


# --- cloud Whisper: cutting the sound -----------------------------------------------------------------------------

def _wav(path: Path, seconds: float) -> Path:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(b"\x01\x00" * int(seconds * 16000))
    return path


def test_every_window_for_the_cloud_is_under_25_mb_and_the_windows_cover_the_whole_stream():
    plan = cloud.windows(0.0, 6 * 3600.0)
    assert len(plan) >= 36
    for w in plan:
        assert (w["end"] - w["start"]) * cloud.BYTES_PER_S + cloud.WAV_HEADER < cloud.LIMIT_BYTES
    assert plan[0]["grid_start"] == 0.0 and plan[-1]["grid_end"] == 6 * 3600.0
    assert all(a["grid_end"] == b["grid_start"] for a, b in zip(plan, plan[1:]))
    assert all(b["start"] < a["end"] for a, b in zip(plan, plan[1:]))      # overlap: no word is cut at a seam
    assert cloud.grid_s(limit_bytes=5_000_000) < cloud.grid_s()             # a smaller limit, shorter windows


def test_a_window_is_a_wav_of_its_own(tmp_path):
    wav = _wav(tmp_path / "a.wav", 30)
    chunk = cloud.wav_bytes(wav, 10.0, 20.0)
    assert len(chunk) == 10 * 16000 * 2 + cloud.WAV_HEADER and chunk[:4] == b"RIFF"


def test_cloud_recognizer_sends_each_window_with_word_timings_and_stitches(tmp_path, monkeypatch):
    monkeypatch.setattr(cloud, "MAX_GRID_S", 20.0)
    wav = _wav(tmp_path / "a.wav", 50)
    sent = []

    def send(url, body, ctype, key, timeout):
        sent.append((url, body, ctype, key))
        # every window answers a word at its own 1 s and one in its overlap at the end
        return {"words": [{"word": "Hello", "start": 1.0, "end": 1.4}, {"word": "seam", "start": 21.0, "end": 21.3}]}

    rec = cloud.CloudRecognizer("groq", lambda: KEY, "en", send=send).load()
    words = rec.transcribe_file(wav)
    assert len(sent) == 3 and all(s[0] == cloud.SERVICES["groq"]["url"] and s[3] == KEY for s in sent)
    body = sent[0][1].decode("latin-1")
    for field in ('name="model"\r\n\r\nwhisper-large-v3-turbo', 'name="response_format"\r\n\r\nverbose_json',
                  'name="timestamp_granularities[]"\r\n\r\nword', 'name="language"\r\n\r\nen', 'filename="audio.wav"'):
        assert field in body
    assert [w["word"] for w in words][:1] == [" Hello"] and words[0]["start"] == 1.0
    assert all(a["start"] <= b["start"] for a, b in zip(words, words[1:]))
    assert len(words) == len({round(w["start"], 1) for w in words})        # nothing twice at a seam


def test_a_cloud_error_never_carries_the_key():
    srv = Fake(lambda path, body: (401, {"error": {"message": f"Invalid API Key {KEY}"}}))
    try:
        with pytest.raises(providers.ProviderError) as e:
            cloud._send(srv.url + "/audio", b"x", "multipart/form-data; boundary=a", KEY, 5)
        assert KEY not in str(e.value) and "HTTP 401" in str(e.value)
    finally:
        srv.close()


def test_a_cloud_model_without_a_key_says_where_to_add_it():
    with pytest.raises(providers.ProviderError, match="Groq provider"):
        speech.cloud_key(speech.GROQ_M, Settings())


def test_the_cloud_key_is_the_groq_providers():
    from smtv_core.settings import set_secret
    s = Settings(providers=[Provider(id="groq", kind=OPENAI, preset="groq", base_url=presets.BY_ID["groq"].base_url)])
    set_secret("provider.groq", KEY)
    assert speech.cloud_key(speech.GROQ_M, s) == KEY
    with pytest.raises(providers.ProviderError, match="OpenAI provider"):
        speech.cloud_key(speech.OPENAI_M, s)


# --- the speech model of each language -----------------------------------------------------------------------------

def test_defaults_by_language():
    assert speech.model_for("ru")[0].id == "gigaam"
    assert speech.model_for("de")[0].id == "parakeet" and speech.model_for("en-US")[0].id == "parakeet"
    assert speech.model_for("ja")[0].id == "whisper" and speech.model_for("kk")[0].id == "whisper"
    assert speech.model_for("latin")[0].id == "parakeet"
    assert all(source == "default" for _, source in map(speech.model_for, ("ru", "de", "ja")))


def test_a_language_takes_the_model_chosen_for_it_and_others_share_one_row():
    s = Settings()
    speech.set_choice(s, "en", "groq")
    speech.set_choice(s, "ru", "whisper")
    speech.set_choice(s, "*", "openai")
    assert speech.model_for("en", s) == (speech.GROQ_M, "own")
    assert speech.model_for("latin", s)[0].id == "groq"                    # a Latin-script stream goes as English does
    assert speech.model_for("ru", s)[0].id == "whisper"
    assert speech.model_for("sw", s)[0].id == "openai"                     # no row of its own: «every other language»
    assert speech.model_for("ja", s)[0].id == "whisper"                    # its own row (default) wins over «*»
    assert speech.model_for("de", s)[0].id == "parakeet"
    speech.set_choice(s, "en", None)
    assert speech.model_for("en", s)[0].id == "parakeet"
    with pytest.raises(ValueError):
        speech.set_choice(s, "en", "gigaam")                               # GigaAM knows only Russian
    with pytest.raises(ValueError):
        speech.set_choice(s, "*", "parakeet")
    with pytest.raises(ValueError):
        speech.set_choice(s, "zz", "whisper")


def test_a_choice_survives_saving_and_a_model_that_cannot_do_the_language_is_ignored(tmp_path):
    s = Settings()
    s.tools.setdefault("smtv", {})["speech"] = {"de": "gigaam", "en": "nonsense"}      # edited by hand
    s.save()
    loaded = Settings.load()
    assert speech.model_for("de", loaded) == (speech.PARAKEET_M, "default")
    assert speech.model_for("en", loaded) == (speech.PARAKEET_M, "default")


def test_a_language_whisper_knows_is_taken_from_the_recording():
    assert choose("ja") == "ja" and choose("pt-BR") == "pt" and choose("ru") == "ru"
    assert choose("xx") is None and choose(None) is None


def test_removing_a_model_removes_only_its_folder_and_a_link_only_as_a_link(tmp_path):
    models = tmp_path / "home" / "models"
    (models / "whisper").mkdir(parents=True)
    (models / "whisper" / "model.bin").write_bytes(b"x")
    (models / "whisper" / "config.json").write_text("{}", encoding="utf-8")
    assert speech.is_installed(speech.WHISPER_M)
    assert speech.remove(speech.WHISPER_M) and not (models / "whisper").exists()
    elsewhere = tmp_path / "kept" / "gigaam"
    elsewhere.mkdir(parents=True)
    (elsewhere / "m.onnx").write_bytes(b"x")
    (models / "gigaam").symlink_to(elsewhere)
    assert speech.remove(speech.GIGAAM_M)
    assert (elsewhere / "m.onnx").exists() and not (models / "gigaam").exists()
    with pytest.raises(ValueError):
        speech.remove(speech.GROQ_M)


def test_whisper_words_are_ours_with_the_window_offset():
    W = SimpleNamespace
    segs = [W(words=[W(word=" Hello", start=0.5, end=0.9, probability=0.91), W(word=" ", start=1.0, end=1.0, probability=0.1)]),
            W(words=[W(word="world.", start=1.2, end=1.2, probability=0.5)])]
    assert whisper.words_of(segs, 100.0) == [
        {"word": " Hello", "start": 100.5, "end": 100.9, "probability": 0.91},
        {"word": " world.", "start": 101.2, "end": 101.22, "probability": 0.5}]


def test_the_pipeline_turns_a_recognizer_with_its_own_reading_into_segments(tmp_path):
    from smtv_core.asr.engines import transcribe
    wav = _wav(tmp_path / "a.wav", 5)

    class Own:
        engine = SimpleNamespace(name="groq")

        def transcribe_file(self, wav, start, end, progress):
            progress(end, end)
            return [{"word": " One.", "start": 0.1, "end": 0.5}, {"word": " Two", "start": 3.0, "end": 3.3}]

    ticks = []
    segs = transcribe(wav, Own(), progress=lambda a, b: ticks.append((a, b)))
    assert [s["text"] for s in segs] == ["One.", "Two"] and segs[0]["sid"] == "s00000" and ticks == [(5.0, 5.0)]


def test_doctor_needs_no_key_for_a_local_server_but_does_for_a_cloud_preset():
    from smtv_core.checks import check_model
    local = Provider(id="ollama", kind=OPENAI, preset="ollama", base_url=presets.BY_ID["ollama"].base_url, name="Ollama")
    cloud_p = Provider(id="groq", kind=OPENAI, preset="groq", base_url=presets.BY_ID["groq"].base_url, name="Groq")
    c = check_model(Settings(providers=[local, cloud_p]))
    assert c.status == "ok" and "Ollama" in c.detail and "Groq: no key" in c.detail
    assert check_model(Settings(providers=[cloud_p])).status == "fail"


def test_a_prompt_ollama_cut_is_an_error_not_an_answer():
    srv = Fake(lambda path, body: (200, {"capabilities": ["completion"], "model_info": {"q.context_length": 8192}}) if path == "/api/show"
               else (200, {"message": {"content": '{"n": 1}'}, "prompt_eval_count": 8192, "eval_count": 3}))
    try:
        p = Provider(id="ollama", kind=OPENAI, preset="ollama", base_url=srv.url)
        with pytest.raises(providers.ProviderError, match="cut it"):
            providers.call(p.connection("q:8b"), "word " * 3000, SCHEMA)
    finally:
        srv.close()


def test_another_program_answering_with_a_list_is_not_a_server():
    srv = Fake(lambda path, body: (200, ["not", "a", "server"]))
    try:
        assert not presets.probe(presets.BY_ID["ollama"], srv.url)["found"]
    finally:
        srv.close()


def test_a_masked_key_of_the_new_services_is_cut_too():
    from smtv_core.llm.keycheck import redact
    for k in ("gsk_ABCDEFGHIJ...wxyz", "xai-abcdef123456", "csk-abcdef123456", "fw_abcdef123456"):
        assert k not in redact(f"Invalid API Key: {k}")


def test_cloud_send_retries_a_busy_service_and_stops_on_quota(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda s: None)
    answers = [(503, {"error": "busy"}), (503, {"error": "busy"}), (200, {"words": []})]
    srv = Fake(lambda path, body: answers.pop(0))
    try:
        assert cloud._send(srv.url + "/a", b"x", "text/plain", KEY, 5) == {"words": []} and len(srv.seen) == 3
    finally:
        srv.close()
    srv = Fake(lambda path, body: (429, {"error": {"message": "insufficient_quota"}}))
    try:
        with pytest.raises(providers.QuotaExceeded):
            cloud._send(srv.url + "/a", b"x", "text/plain", KEY, 5)
        assert len(srv.seen) == 1
    finally:
        srv.close()


def test_text_without_word_timings_is_an_error_not_an_empty_transcript(tmp_path):
    wav = _wav(tmp_path / "a.wav", 10)
    rec = cloud.CloudRecognizer("openai", lambda: KEY, "en", send=lambda *a: {"text": "hello there"}).load()
    with pytest.raises(providers.ProviderError, match="without word timings"):
        rec.transcribe_file(wav)
