"""Stage 27: the window's words live in files, one per language — `web/i18n/en.json` the source, `ru.json` and whatever
translators add through Weblate beside it — for the window and for each tool (VodCut's in its own `web/i18n`). Every key
the code asks for is in en.json, every language has the same keys, no text is written into the code, and a key a
language lacks is shown in English."""
import json
import re
from pathlib import Path

import pytest

from smtv import i18n, serve
from vodcut import page as vodcut_page

REPO = Path(__file__).resolve().parents[3]
WEB = Path(serve.__file__).parent / "web"
FOLDERS = {"window": WEB / "i18n", "vodcut": vodcut_page.WEB / "i18n"}
CODE = {"window": WEB / "app.js", "vodcut": vodcut_page.WEB / "section.js"}
PY = Path(serve.__file__).parent


def words(folder: Path, lang: str) -> dict:
    return json.loads((folder / f"{lang}.json").read_text(encoding="utf-8"))


def code_only(js: str) -> str:
    """The script without its comments (a comment may quote Russian words)."""
    js = re.sub(r"/\*.*?\*/", "", js, flags=re.S)
    return "\n".join(re.sub(r"(^|\s)//.*$", "", line) for line in js.splitlines())


@pytest.mark.parametrize("part", FOLDERS)
def test_every_language_has_the_same_keys_and_only_text(part):
    folder = FOLDERS[part]
    en = words(folder, "en")
    assert len(en) > 100
    files = sorted(folder.glob("*.json"))
    assert {p.stem for p in files} >= {"en", "ru"}
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        assert set(data) == set(en), (path.name, sorted(set(en) ^ set(data))[:10])
        assert all(isinstance(v, str) for v in data.values()), path.name
        # the same {placeholders} as the English text: a translation never loses or invents a value
        for k, v in data.items():
            assert set(re.findall(r"\{(\w+)\}", v)) == set(re.findall(r"\{(\w+)\}", en[k])), (path.name, k)
    assert all(v.strip() for v in en.values())


@pytest.mark.parametrize("part", FOLDERS)
def test_every_key_the_code_asks_for_is_in_en_json(part):
    js = CODE[part].read_text(encoding="utf-8")
    asked = set(re.findall(r'(?<![\w.])t\("([a-z][\w.]*)"\s*[,)]', js))       # t("key") and t("key", {...}), not t("prefix_" + x)
    known = set(words(FOLDERS[part], "en")) | set(words(FOLDERS["window"], "en"))   # a tool may use the window's words
    assert asked and not asked - known, sorted(asked - known)


def test_every_key_the_python_side_asks_for_is_in_en_json():
    en = words(FOLDERS["window"], "en")
    asked = set()
    for path in PY.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        asked |= set(re.findall(r'i18n\.text\("([\w.]+)"', text))
        asked |= {f"refused_{k}_{f}" for k in re.findall(r'refused_page\("(\w+)"', text) for f in ("title",)}
    assert asked and not asked - set(en), sorted(asked - set(en))


@pytest.mark.parametrize("part", CODE)
def test_no_text_is_written_into_the_code(part):
    js = code_only(CODE[part].read_text(encoding="utf-8"))
    assert not re.search(r"[А-Яа-яЁё]", js), re.search(r".*[А-Яа-яЁё].*", js).group(0)
    assert "Object.assign(STRINGS" not in js and not re.search(r'\b(en|ru):\s*\{\s*[\w"]', js)
    assert not re.search(r'lang(\(\))? === "ru"', js)        # units and dates come from the files too
    # a phrase written straight into the page: a capitalised word and more words as an argument
    phrase = re.search(r'[(,]\s*"([A-Z][a-z]+(?: [a-z]+)+[.…!?]?)"\s*[,)]', js)
    assert phrase is None, phrase and phrase.group(0)


def test_the_page_template_has_no_text_of_its_own():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    body = re.sub(r"<script.*?</script>", "", html.split("<body>", 1)[1], flags=re.S)
    assert not re.sub(r"<[^>]+>", "", body).strip()


def test_the_python_side_keeps_no_text_of_both_languages():
    for name in ("window.py", "activity.py", "desktop.py", "about.py", "serve.py"):
        text = (PY / name).read_text(encoding="utf-8")
        assert not re.search(r'== "ru"|"ru": \{', text), name


def test_the_steps_of_the_ai_and_the_tools_keep_their_words_in_the_files():
    """V9: the AI's steps (agents) and a tool's own places have no text in the code; every step has its six texts in
    English — the core's shared steps in the window's files, a tool's own in the tool's."""
    from smtv_core import agents as core_agents
    from smtv_core import tool as core_tool
    from vodcut import agents as vodcut_agents
    for path in (Path(core_agents.__file__), Path(core_tool.__file__), Path(vodcut_agents.__file__), Path(vodcut_page.__file__)):
        code = path.read_text(encoding="utf-8")
        assert not re.search(r'"ru":|[А-Яа-яЁё]', code), path.name
    fields = ("title", "short", "does", "stage", "needs", "why")
    for agent in vodcut_agents.AGENTS:
        en = words(FOLDERS["window" if agent.shared else "vodcut"], "en")
        assert all(en.get(f"agent.{agent.id}.{f}") for f in fields), agent.id
    vodcut_en = words(FOLDERS["vodcut"], "en")
    page = vodcut_page.page
    assert all(vodcut_en.get(k) for k in (page.about, page.request.title, page.request.about))


def test_a_text_is_looked_up_in_the_tool_then_in_the_window(folder, tmp_path):
    tool = tmp_path / "tool"
    tool.mkdir()
    (tool / "en.json").write_text(json.dumps({"hello": "Hi from the tool", "only": "Tool only"}), encoding="utf-8")
    (tool / "ru.json").write_text(json.dumps({"hello": "Привет от кубика"}), encoding="utf-8")
    assert i18n.texts("hello", tool) == {"en": "Hi from the tool", "ru": "Привет от кубика"}
    assert i18n.texts("only", tool) == {"en": "Tool only"}                # a language without it: the page shows English
    assert i18n.texts("bye", tool) == {"en": "Bye"}                       # the tool lacks it: the window's words
    assert i18n.texts("Plain English", tool) == {"en": "Plain English"}   # no file has it: shown as it is
    assert i18n.texts("", tool) == {}
    assert i18n.texts("hello", tmp_path / "missing") == {"en": "Hello, {name}", "ru": "Привет, {name}"}


def test_a_broken_tool_english_file_falls_back_to_the_window(folder, tmp_path):
    tool = tmp_path / "tool"
    tool.mkdir()
    (tool / "en.json").write_text("{broken", encoding="utf-8")
    assert i18n.texts("bye", tool) == {"en": "Bye"} and i18n.texts("Plain", tool) == {"en": "Plain"}
    (tool / "en.json").write_text("[1, 2]", encoding="utf-8")            # not an object of words
    i18n.strings.cache_clear()
    assert i18n.texts("hello", tool)["en"] == "Hello, {name}"


def test_soon_json_holds_no_words():
    data = json.loads((PY / "soon.json").read_text(encoding="utf-8"))
    assert all(set(x) <= {"id", "kind", "icon"} for x in data["items"])


# --- choosing the language and falling back -------------------------------------------------------------------------------

@pytest.fixture
def folder(tmp_path, monkeypatch):
    (tmp_path / "en.json").write_text(json.dumps({"hello": "Hello, {name}", "bye": "Bye"}), encoding="utf-8")
    (tmp_path / "ru.json").write_text(json.dumps({"hello": "Привет, {name}", "bye": ""}), encoding="utf-8")
    (tmp_path / "pt-BR.json").write_text("{broken", encoding="utf-8")
    monkeypatch.setattr(i18n, "FOLDER", tmp_path)
    i18n.strings.cache_clear()
    yield tmp_path
    i18n.strings.cache_clear()


def test_a_missing_or_empty_translation_is_shown_in_english(folder):
    assert i18n.text("hello", "ru", name="Аня") == "Привет, Аня"
    assert i18n.text("bye", "ru") == "Bye"                       # Weblate leaves an untranslated string empty
    assert i18n.text("bye", "pt-BR") == "Bye"                    # a broken file: English, not a crash
    assert i18n.text("bye", "../etc/passwd") == "Bye"            # never a path
    assert i18n.text("nothing", "ru") == "nothing"


def test_the_language_follows_the_system_and_falls_back_to_english(folder):
    assert i18n.languages() == ["en", "pt-BR", "ru"]
    assert i18n.best(["ru_RU.UTF-8"]) == "ru"
    assert i18n.best(["pt-BR"]) == "pt-BR" and i18n.best(["pt_PT"]) == "en"
    assert i18n.best(["de-DE", "ru"]) == "ru"
    assert i18n.best(["C", "POSIX"]) == "en"
    assert i18n.from_accept_language("de-DE,de;q=0.9,ru;q=0.8") == "ru"
    assert i18n.from_accept_language(None) == "en"


def test_the_page_is_told_which_languages_exist(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert '<meta name="smtv-languages" content="{{SMTV_LANGUAGES}}">' in html
    js = (WEB / "app.js").read_text(encoding="utf-8")
    assert 'meta[name="smtv-languages"]' in js and "await loadWords(\"/static\")" in js
    # a tool's words come from its own folder, the window's from /static/i18n
    assert "loadWords(`/tools/${encodeURIComponent(tool.name)}`)" in js


def test_the_weblate_setup_names_the_real_files():
    conf = (REPO / ".weblate").read_text(encoding="utf-8")
    doc = (REPO / "docs" / "translations.md").read_text(encoding="utf-8")
    for folder in FOLDERS.values():
        rel = folder.relative_to(REPO).as_posix()
        assert f"{rel}/*.json" in doc and f"{rel}/en.json" in doc
    assert "hosted.weblate.org" in conf
