"""Settings → About (stage 18): one list of what is coming (soon.json) read by every place that shows it, «soon» buttons
that install nothing, and the support link in exactly one place of the code."""
import json
import re
import sys
import threading
from pathlib import Path

import pytest

from smtv import about, i18n, serve
from smtv import jobs as jobs_module
from smtv.tools import CATALOG, SOON, plugins

sys.path.insert(0, str(Path(__file__).parent))
from test_serve import CHILD, Client, make_tool  # noqa: E402

PKG = Path(about.__file__).parent
APP_JS = PKG / "web" / "app.js"
REPO = PKG.parents[3]


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("SMTV_HOME", str(tmp_path / "home"))
    monkeypatch.setattr("smtv_core.settings._keyring", lambda: None)


@pytest.fixture
def server(tmp_path):
    root = tmp_path / "jobs"
    root.mkdir()
    runner = jobs_module.Runner(lambda name, args: [sys.executable, "-c", CHILD, *args])
    app = serve.App([make_tool(root)], [], runner)
    srv = serve.make_server(app, port=0)
    threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True).start()
    yield Client(srv.server_address[1], app.token), app
    app.stopping.set()
    runner.stop_all()
    srv.shutdown()
    srv.server_close()


# --- the file itself ---------------------------------------------------------------------------------------------------

def test_the_soon_file_lists_everything_planned_in_both_languages():
    items = about.soon()
    ids = [x["id"] for x in items]
    # what the owner named (21.11): LiveCut, Scheduled, Promotion, Campaigns; MCP and own plugins, auto-publishing,
    # TikTok hashtags and music; Ollama and Whisper, the StreamMoment cloud
    assert ids == ["livecut", "scheduled", "promotion", "campaigns", "mcp", "own-plugins", "autopublish", "tiktok-hashtags",
                   "tiktok-music", "local-models", "cloud"]
    for x in items:
        assert x["title"]["ru"] and x["title"]["en"] and x["summary"]["ru"] and x["summary"]["en"]
    assert about.soon_item("campaigns")["title"]["ru"] == "Заказы"
    assert "может меняться" in about.soon_item("campaigns")["note"]["ru"]
    assert "Условия могут измениться" in about.soon_item("promotion")["note"]["ru"]


def test_the_soon_file_has_no_dates():
    words = [v for lang in i18n.languages() for k, v in i18n.strings(lang).items() if k.startswith("soon.")]
    text = json.dumps(words, ensure_ascii=False)
    assert not re.search(r"\b20\d\d\b|\bQ[1-4]\b|квартал|январ|феврал|март[ае]?\b|весн|летом|осен|зимой|spring|summer|autumn|winter", text, re.I)


WORDS = {"en": {"soon.x.title": "X", "soon.x.summary": "x"}, "ru": {"soon.x.title": "Икс"}}


@pytest.mark.parametrize("broken, words, why", [
    ({"items": []}, WORDS, "lists nothing"),
    ({"items": [{"id": "x", "kind": "plugin"}]}, {"en": {"soon.x.summary": "x"}}, "title"),
    ({"items": [{"id": "x", "kind": "someday"}]}, WORDS, "kind"),
    ({"items": [{"id": "x", "kind": "page"}] * 2}, WORDS, "unique"),
    ({"items": [{"id": "x", "kind": "page"}]}, {"en": {"soon.x.title": "X"}}, "summary"),
    ({"items": [{"id": "x", "kind": "page", "title": {"en": "X"}}]}, WORDS, "not into soon.json"),
    ({"items": [{"id": "x", "kind": "page"}]}, {"en": {**WORDS["en"], "soon.gone.title": "Gone"}}, "does not list: gone"),
])
def test_a_broken_soon_file_is_refused(broken, words, why):
    with pytest.raises(ValueError, match=why):
        about.parse_soon(broken, words)


def test_soon_words_come_from_the_language_files_and_fall_back_to_english():
    item = about.parse_soon({"items": [{"id": "x", "kind": "page"}]},
                            {**WORDS, "en": {**WORDS["en"], "soon.x.points.1": "one", "soon.x.points.2": "two"}})[0]
    assert item["title"] == {"en": "X", "ru": "Икс"}
    assert item["summary"] == {"en": "x"}                     # the window shows the English one in Russian
    assert item["points"] == [{"en": "one"}, {"en": "two"}]


# --- every place reads the file ----------------------------------------------------------------------------------------

def test_the_soon_plugins_come_from_the_file():
    assert SOON == {x["id"]: x["summary"]["en"] for x in about.soon() if x["kind"] == "plugin"}
    assert list(SOON) == ["livecut", "mcp", "autopublish", "tiktok-hashtags", "tiktok-music"]
    cards = [p for p in plugins([], []) if p["status"] == "soon"]
    assert [p["soon"] for p in cards] == [about.soon_item(p["name"]) for p in cards]


def test_the_window_gets_the_list_and_about_from_the_server(server):
    client, _ = server
    _, st = client.request("GET", "/api/state")
    assert st["soon"] == list(about.soon())
    assert st["support"] == about.SUPPORT_URL
    soon_cards = {p["name"]: p["soon"] for p in st["plugins"] if p["status"] == "soon"}
    assert soon_cards == {n: about.soon_item(n) for n in SOON}
    status, a = client.request("GET", "/api/about")
    assert status == 200
    assert a["version"] == serve.__version__ and a["support"] == about.SUPPORT_URL and a["license"] == "MIT"
    assert a["soon"] == list(about.soon())
    assert a["core"]["package"] == "smtv-core" and a["core"]["version"]
    assert [p["name"] for p in a["core"]["plugins"]] == ["demo"]       # the installed plugins that run on the core
    assert a["changes"] and a["changes"][0]["version"] == serve.__version__ and a["changes"][0]["notes"]


def test_the_window_keeps_no_copy_of_the_soon_texts():
    """The «soon» cards, the rail's soon pages and the «Add a plugin» window read state.soon; app.js holds none of the texts."""
    js = APP_JS.read_text(encoding="utf-8")
    for x in about.soon():
        for f in ("lead", "summary", "note"):
            for lang in ("en", "ru"):
                if f in x:
                    assert x[f][lang] not in js, (x["id"], f, lang)
    for gone in ("SOON_PAGE", "SOON_ICON", "promotion_sub", "scheduled_sub", "soon_mcp_lead", "nav_promotion", "nav_scheduled"):
        assert gone not in js, gone
    for page in ("scheduled", "promotion", "campaigns"):
        assert f'soonOf("{page}")' in js or f'"{page}"' in js
    assert 'soonOf("own-plugins")' in js


# --- «soon» installs nothing -------------------------------------------------------------------------------------------

def test_nothing_announced_can_be_installed(server):
    client, app = server
    spawned = []
    app.updates.spawn = spawned.append
    app.updates.kind = "uv"
    for x in about.soon():
        assert x["id"] not in CATALOG
        status, data = client.request("POST", f"/api/plugins/{x['id']}/install", {})
        assert status in (404, 409) and data.get("error") in ("not_in_catalog", "not_found"), (x["id"], data)
    assert spawned == []


def _function(js: str, name: str) -> str:
    start = js.index(f"function {name}(")
    depth, i = 0, js.index("{", start)
    for j in range(i, len(js)):
        depth += {"{": 1, "}": -1}.get(js[j], 0)
        if depth == 0:
            return js[start:j + 1]
    raise AssertionError(name)


@pytest.mark.parametrize("fn", ["addPluginDialog", "showSoon", "soonBody"])
def test_the_soon_buttons_ask_the_server_nothing(fn):
    body = _function(APP_JS.read_text(encoding="utf-8"), fn)
    for call in ("postJSON", "getJSON", "fetch(", "call(", "changeSmtv", "/api/"):
        assert call not in body, (fn, call)


def test_a_soon_plugin_page_has_only_a_disabled_install_button():
    body = _function(APP_JS.read_text(encoding="utf-8"), "pluginActions")
    first = body.split("\n")[2]
    assert 'p.status === "soon"' in first and "disabled: true" in first and "onclick" not in first


# --- the support link: one place in the code -------------------------------------------------------------------------

def test_the_support_link_lives_in_one_place_of_the_code():
    assert about.SUPPORT_URL == "https://boosty.to/smtv"
    found = []
    for path in (REPO / "packages").rglob("*"):
        if path.is_file() and path.suffix in (".py", ".js", ".json", ".css", ".html", ".toml") and "__pycache__" not in path.parts \
                and "tests" not in path.parts:
            if "boosty.to" in path.read_text(encoding="utf-8", errors="ignore"):
                found.append(path.relative_to(REPO).as_posix())
    assert found == ["packages/smtv/src/smtv/about.py"]


def test_the_repository_names_the_support_page():
    assert (REPO / ".github" / "FUNDING.yml").read_text(encoding="utf-8").strip() == f"custom: {about.SUPPORT_URL}"
    assert about.SUPPORT_URL in (REPO / "README.md").read_text(encoding="utf-8")


def test_the_window_shows_support_quietly():
    """One link at the bottom of Settings (owner, 21.11: out of the profile menu), opened in the browser: no pop-up, no
    reminder, no counter."""
    js = APP_JS.read_text(encoding="utf-8")
    assert js.count("side-support") == 1 and js.count("href: state.support") == 1     # one link, in one place
    link = js[js.index("// «Support the project» at the bottom of Settings"):js.index('h("b", t("support"))')]
    assert 'target: "_blank"' in link and "state.support" in link
    for noisy in ("setTimeout", "setInterval", "confirmDialog", "localStorage"):
        assert noisy not in link
