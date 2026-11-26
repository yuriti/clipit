"""V1 (owner 22.11): SMTV is for ordinary streamers and clippers who do not know what a model, provider, agent or API key
is. The window's own words on the newcomer's path are plain; the technical ones live only behind «More»; the first run
is a welcome that leads to the first clip; every step of the AI says what it does in one sentence."""
import json
import re
import sys
from pathlib import Path

import pytest

from smtv import serve
from smtv_core import agents as core_agents
from vodcut import agents as vodcut_agents
from vodcut import page as vodcut_page

sys.path.insert(0, str(Path(__file__).parent))
from test_about import _function  # noqa: E402
from test_serve import isolated, server  # noqa: E402,F401 — the fixtures (isolated: never the real SMTV folder)

WEB = Path(serve.__file__).parent / "web"
APP_JS = (WEB / "app.js").read_text(encoding="utf-8")
APP_CSS = (WEB / "app.css").read_text(encoding="utf-8")
SECTION_JS = (vodcut_page.WEB / "section.js").read_text(encoding="utf-8")

JARGON_RU = re.compile(r"провайдер|агент|\bLLM\b|токен|промпт|\bAPI\b|\bCLI\b|JSON", re.I)
JARGON_EN = re.compile(r"provider|agent|\bLLM\b|token|prompt|\bAPI\b|\bCLI\b|JSON", re.I)


def strings(web: Path, lang: str) -> dict[str, str]:
    """The window's (or a tool's) words in one language: web/i18n/<lang>.json (stage 27)."""
    return json.loads((web / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))


RU, EN = strings(WEB, "ru"), strings(WEB, "en")
VC_RU, VC_EN = strings(vodcut_page.WEB, "ru"), strings(vodcut_page.WEB, "en")

# what a newcomer reads on the way from the first run to the first clip
NEWCOMER = ["ob_title", "ob_text", "ob_step1", "ob_step1_now", "ob_step2_pick", "ob_step2_pick_text", "ob_step3", "ob_step3_text", "ob_btn",
            "ch_title", "ch_account", "ch_account_soon_text", "ch_account_btn", "ch_key", "ch_key_text", "ch_key_btn",
            "ch_local", "ch_local_text", "ch_local_btn", "ch_other", "pv_none", "ag_set_intro", "ag_intro", "sp_intro",
            "sm_soon_note", "sm_soon_btn", "sm_out_soon", "sm_not_open", "fx_first", "fx_providers", "chd_model_none",
            "chd_gpu_none", "chd_links_soon",
            "providers", "agents_set", "speech_set", "sm_account", "system", "switches", "ag_tab_agents", "pv_list", "pv_agents"]


def test_the_account_is_just_account():
    assert RU["sm_account"] == "Аккаунт" and EN["sm_account"] == "Account"
    assert "StreamMoment" not in RU["sm_account"] + RU["sm_logout_title"] + RU["sm_logged_out"]


def test_the_settings_sections_have_plain_names():
    names = {k: RU[k] for k in ("sm_account", "providers", "agents_set", "speech_set", "system", "look_set")}
    assert names == {"sm_account": "Аккаунт", "providers": "Нейросеть", "agents_set": "Шаги нейросети",
                     "speech_set": "Распознавание речи", "system": "Проверка компьютера", "look_set": "Язык и тема"}
    for k in names:
        assert not JARGON_EN.search(EN[k]), (k, EN[k])


@pytest.mark.parametrize("key", NEWCOMER)
def test_the_newcomer_path_has_no_jargon_in_both_languages(key):
    assert key in RU and key in EN, key
    assert not JARGON_RU.search(RU[key]), (key, RU[key])
    assert not JARGON_EN.search(EN[key]), (key, EN[key])


def test_a_key_is_explained_where_it_is_asked_for():
    """The one place that names the term: a plain sentence first, the English word second."""
    assert RU["ch_term"].startswith("Что такое ключ?") and "API key" in RU["ch_term"]
    assert EN["ch_term"].startswith("What is a key?")


def test_the_three_ways_to_connect_an_ai_and_the_subscriptions_hidden():
    body = _function(APP_JS, "renderProviders")
    for key in ("ch_account", "ch_key", "ch_local", "ch_other", "ch_cli_btn", "ch_term"):
        assert f't("{key}")' in body, key
    assert 'h("details.pv-more"' in body                                     # the CLIs only under «Other ways»
    assert 'open(["main", "cloud"])' in body and 'open(["cli"])' in body
    assert "!x.account" in body                                              # «Your own key» never offers the account
    assert 't("pv_add")))].filter' not in body                               # the old «Add a provider» row is gone


def test_sign_in_is_coming_soon_so_the_ways_that_work_now_come_first():
    """0.1.0: sign-in to the account is not open on the site. Your own key and the free AI on this computer come first
    (the key is the primary button), the account last with «soon», never «simplest»; the account page says so and leads
    to «Settings → AI»; «Sign in» stays, and the site's «not open yet» is told in the window's words."""
    ways = _function(APP_JS, "renderProviders")
    ways = ways[ways.index("const ways = () =>"):]
    assert ways.index('t("ch_key")') < ways.index('t("ch_local")') < ways.index('t("ch_account")')
    assert 'none ? "button.btn.btn-primary.btn-sm"' in ways and 'title(t("ch_account"), t("soon"))' in ways
    assert '"a.btn.btn-primary.btn-sm" : "a.btn.btn-sm", { href: "#/settings/account" }' not in ways
    for lang in (RU, EN):
        assert "ch_account_tag" not in lang and "sm_add_note" not in lang          # «simplest» is gone
        assert not re.search(r"прост|simplest|easiest", lang["sm_soon_note"] + lang["ch_account_soon_text"] + lang["ob_step1_now"], re.I)
    assert re.search(r"скоро", RU["sm_soon_note"] + RU["ch_account_soon_text"] + RU["sm_out_soon"]) and "soon" in EN["sm_soon_note"]
    page = _function(APP_JS, "renderAccount")
    assert 't("sm_soon_note")' in page and '"#/settings/providers"' in page
    panel = _function(APP_JS, "accountPanel")
    assert 'login("browser"), login("device")' in panel                       # «Sign in» is still there
    assert 'e.code !== "not_open"' in panel and 't("sm_not_open"), soft: true' in panel   # expected, so not red
    assert 'problem.soft ? "div.result.warn" : "div.result.bad"' in panel
    menu = _function(APP_JS, "openProfile")
    assert 't("sm_login"), h("span.menu-soon", t("soon"))' in menu and 'e.code === "not_open" ? t("sm_not_open")' in menu
    assert ".menu-soon" in APP_CSS


def test_a_link_without_the_account_leads_to_vodcut_s_switch_not_to_sign_in():
    assert 'API.t("link_no_account")' in SECTION_JS and 'API.openSettings("tool-" + API.tool.name)' in SECTION_JS
    assert 'openSettings("account")' not in SECTION_JS
    for lang, switch in ((VC_RU, "Скачивать ссылки самому"), (VC_EN, "Download links myself")):
        assert "sm_sign_in" not in lang and switch in lang["link_no_account"] and lang["opt_local_download"] == switch
        assert "yt-dlp" in lang["link_no_account"]


def test_the_first_run_is_a_welcome_with_three_steps():
    body = _function(APP_JS, "blockIfNotReady")
    assert 'r.id === "model"' in body and 't("ob_title")' in body
    assert "const step = " in body and body.count("step(") == 3 and '"#/settings/providers"' in body   # three steps
    assert ".new-title" in body                                             # the welcome takes the question's place
    show = _function(APP_JS, "showHome")
    assert "!requests.length" in show                                       # a narrow window shows it, not an empty list


def test_vodcut_no_longer_repeats_the_window_s_model_note():
    assert "need_model" not in SECTION_JS and "modelNote" not in SECTION_JS
    assert "vc-note" not in (vodcut_page.WEB / "section.css").read_text(encoding="utf-8")


@pytest.mark.parametrize("key", ["episodes", "model", "m_calls", "episodes_empty", "calls_empty", "opt_precise_about",
                                 "opt_critic_about", "opt_recap_about", "opt_ad_blur_about", "link_no_account",
                                 "opt_local_download_about"])
def test_vodcut_words_are_plain(key):
    assert not re.search(r"модел|провайдер|агент|токен|LUFS", VC_RU[key], re.I), (key, VC_RU[key])
    assert not re.search(r"\bmodel|provider|agent|token|LUFS", VC_EN[key], re.I), (key, VC_EN[key])


def test_the_checks_are_told_in_plain_words():
    body = _function(APP_JS, "plainDetail")
    for server_text in ("no provider set up", "none found", "used to speed things up", "GB free", "own window$",
                        "signed in as", "coming soon", "is on this computer", "is not downloaded yet", "ffmpeg version"):
        assert server_text in body, server_text
    for key in re.findall(r't\("(chd_\w+)"', body):
        assert key in RU and key in EN, key
    assert "plainDetail(r)" in _function(APP_JS, "fixDialog") and "plainDetail(r)" in _function(APP_JS, "renderSystem")
    system = _function(APP_JS, "renderSystem")
    assert 'h("details.fix-more"' in system                                  # a terminal command only under its fold
    # the server still says what each check means: the window only translates the usual ones
    from smtv_core import checks
    src = Path(checks.__file__).read_text(encoding="utf-8")
    assert '"no provider set up"' in src and "none found: everything runs on the processor" in src


def test_every_step_of_the_ai_says_what_it_does_in_one_sentence():
    steps = [*core_agents.CORE.values(), *vodcut_agents.AGENTS]
    assert {a.id for a in steps} == {"scan", "rating", "fit", "recap", "layout", "banner", "critic"}
    words = {lang: {**json.loads((WEB / "i18n" / f"{lang}.json").read_text(encoding="utf-8")),
                    **json.loads((vodcut_page.WEB / "i18n" / f"{lang}.json").read_text(encoding="utf-8"))} for lang in ("ru", "en")}
    for a in steps:
        for lang in ("ru", "en"):
            say = lambda field: words[lang][f"agent.{a.id}.{field}"]       # noqa: E731 — the steps' words are in the files (V9)
            short, does = say("short"), say("does")
            assert short and short.endswith(".") and short.count(". ") == 0, (a.id, lang, short)
            assert len(short) <= 90 < len(does) or len(short) < len(does), (a.id, lang)
            assert not re.search(r"pass ?\d|Fit|транскрипт|transcript", short + say("title") + say("stage")), (a.id, lang)


def test_the_settings_and_the_plugin_tab_get_the_short_sentence(server):  # noqa: F811
    _, c, *_ = server
    _, data = c.request("GET", "/api/settings/agents")
    rows = {x["id"]: x for g in data["groups"] for x in g["agents"]}
    short = json.loads((WEB / "i18n" / "ru.json").read_text(encoding="utf-8"))["agent.layout.short"]
    assert rows["layout"]["short"]["ru"] == short and rows["finder"]["short"] == {}   # a plugin may not declare one
    _, tab = c.request("GET", "/api/tools/demo/agents")
    assert {a["id"]: a["short"] for a in tab["agents"]}["layout"]["ru"] == short


def test_the_steps_show_one_sentence_and_hide_the_rest():
    row = _function(APP_JS, "renderAgents")
    assert 'txt(a.short) || txt(a.does)' in row and 'h("details.agset-more"' in row and 't("ag_now"' in row
    assert "more.open = true" in row                                         # «Change» on a plugin's tab opens that step
    card = _function(APP_JS, "agentCard")
    assert 'txt(a.short) || txt(a.does)' in card and 'h("details.ag-more"' in card
    head = _function(APP_JS, "agentsHead")
    assert "ag_prompts" not in head                                          # the prompts' version is not a chip at the top


def test_buttons_in_a_row_do_not_touch_and_long_lines_do_not_widen_settings():
    assert re.search(r"\.set-actions \{[^}]*gap: 8px", APP_CSS)
    assert ".settings-page > *, .settings-body, .settings-body > * { min-width: 0; }" in APP_CSS
    assert ".set-text .chip { white-space: normal; }" in APP_CSS
    assert "gradient" not in APP_CSS.split("V1 (owner 22.11)")[1]           # calm, like Claude and ChatGPT
