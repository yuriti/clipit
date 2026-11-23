// SMTV's window (stage 7): a top bar, a narrow rail of icons on the left (Home, Scheduled, Plugins, the tools' own items;
// below: tokens spent, Advertisers, Connect a phone, Settings, profile), and the work on the right. Home lists every
// request (job) of every tool, newest first, like chats; «New request» offers each tool's kind of request.
// A tool plugs in without changes here: its ES module /tools/<name>/section.js exports any of mountNew(el, api),
// mountJob(el, api, job), mountNav(el, api, path), mountSettings(el, api); its own words are files beside it,
// /tools/<name>/i18n/<language>.json (api.t looks there first, then in the window's) — see smtv_core.tool.Page.

function store(key, value) {
  try { if (value === undefined) return localStorage.getItem(key); localStorage.setItem(key, value); } catch { return null; }
  return null;
}

// --- the window's words (stage 27): web/i18n/<language>.json, English (en.json) the source; translators add languages
// through Weblate (docs/translations.md). The language is the system's until one is chosen in Settings → Language; a
// key a language lacks is shown in English. No text of the window is written in this file.
// step-by-step guides for newcomers (docs/guide/ in the repository, stage V7); the window links them from Settings → AI
const GUIDE = "https://github.com/streammomenttv/smtv/blob/main/docs/guide/";
const LANGS = (document.querySelector('meta[name="smtv-languages"]')?.content || "en").split(",").filter((x) => /^[a-z]{2,3}(-[A-Za-z]{2,4})?$/.test(x));
function systemLang() {
  const wanted = navigator.languages?.length ? navigator.languages : [navigator.language || "en"];
  for (const raw of wanted) {
    const code = String(raw).toLowerCase();
    const hit = LANGS.find((l) => l.toLowerCase() === code) || LANGS.find((l) => l.toLowerCase() === code.split("-")[0]);
    if (hit) return hit;
  }
  return "en";
}
const chosenLang = store("smtv.lang");
let lang = chosenLang && LANGS.includes(chosenLang) ? chosenLang : systemLang();
const wordsMissing = [];
async function loadWords(base) {          // {en: {...}, <lang>: {...}}; a file that does not load counts as empty
  const get = async (l) => {
    try { const r = await fetch(`${base}/i18n/${l}.json`); return r.ok ? await r.json() : null; } catch { return null; }
  };
  const [en, own] = await Promise.all([get("en"), lang === "en" ? null : get(lang)]);
  const out = { en: en || {} };
  if (lang !== "en") out[lang] = own || {};
  if (lang !== "en" && !own && en) wordsMissing.push(`${base}/i18n/${lang}.json`);   // reported once the page is up (boot)
  return out;
}
const STRINGS = await loadWords("/static");
const WORDS_MISSING = !Object.keys(STRINGS.en).length;   // reported once the page is up (boot)
// Each tool's words live apart from the window's: a tool's key never changes the window's text, nor another tool's.
const extra = new Map();   // tool name -> { en: {}, <lang>: {} }

function lookup(own, key) {   // an empty translation counts as missing
  return own?.[lang]?.[key] || STRINGS[lang]?.[key] || own?.en?.[key] || STRINGS.en[key] || key;
}
export function t(key, vars = {}, own = null) {
  return lookup(own, key).replace(/\{(\w+)\}/g, (_, k) => (vars[k] ?? ""));
}

// the DOM helpers live in dom.js (V6): h() builds a node, text/attr/keyed/blocks/region change only what changed
import { h, text, attr, keyed, blocks, region, sig } from "./dom.js";
export { h, text, attr, keyed, blocks, region, sig };
export const icon = (path, cls = "") => { const s = document.createElementNS("http://www.w3.org/2000/svg", "svg"); s.setAttribute("viewBox", "0 0 24 24"); if (cls) s.setAttribute("class", cls); s.innerHTML = path; return s; };
export const ICONS = {
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>', x: '<path d="M6 6l12 12M18 6 6 18"/>', warn: '<path d="M12 8v5M12 16.5v.5"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2.5"/><path d="M16 8V6.5A2.5 2.5 0 0 0 13.5 4h-7A2.5 2.5 0 0 0 4 6.5v7A2.5 2.5 0 0 0 6.5 16H8"/>',
  ext: '<path d="M14 5h5v5M19 5l-8 8M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4"/>',
  sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
  moon: '<path d="M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5Z"/>', auto: '<circle cx="12" cy="12" r="8"/><path d="M12 4v16" /><path d="M12 4a8 8 0 0 1 0 16Z" fill="currentColor"/>',
};

// --- formatting
const nf = () => new Intl.NumberFormat(lang);
export const fmt = {
  num: (n) => nf().format(Math.round(n || 0)),
  dec: (n, d = 1) => new Intl.NumberFormat(lang, { minimumFractionDigits: d, maximumFractionDigits: d }).format(n || 0),
  money: (n) => "$" + new Intl.NumberFormat(lang, { minimumFractionDigits: n < 0.01 && n > 0 ? 4 : 2, maximumFractionDigits: n < 0.01 && n > 0 ? 4 : 2 }).format(n || 0),
  hms: (s) => { s = Math.max(0, Math.floor(s || 0)); const hh = Math.floor(s / 3600), mm = Math.floor(s % 3600 / 60), ss = s % 60; return (hh ? hh + ":" + String(mm).padStart(2, "0") : mm) + ":" + String(ss).padStart(2, "0"); },
  dur: (s) => {
    s = Math.round(s || 0);
    if (s < 60) return t("unit_s", { n: s });
    const m = Math.round(s / 60); if (m < 60) return t("unit_min", { n: m });
    const hh = Math.floor(m / 60), mm = m % 60; return t("unit_h", { n: hh }) + (mm ? " " + t("unit_min", { n: mm }) : "");
  },
  hours: (s) => (s || 0) < 3600 ? fmt.dur(s) : t("unit_h", { n: fmt.dec(s / 3600, 1) }),
  clock: (t) => new Date(t * 1000).toLocaleTimeString(lang === "en" ? "en-GB" : lang, { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
  date: (t) => new Date(t * 1000).toLocaleString(lang === "en" ? "en-GB" : lang, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }),
};

// A page from an earlier start of SMTV reloads to get the new token (A20). Never in a loop: once per 20 s at most.
function reloadStale() {
  let last = 0;
  try { last = Number(sessionStorage.getItem("smtv-stale-reload") || 0); } catch {}
  if (Date.now() - last < 20000) return false;
  try { sessionStorage.setItem("smtv-stale-reload", String(Date.now())); } catch {}
  location.reload();
  return true;
}

// --- server calls: changes carry the session token the server wrote into this page, the proof that it is the page
const TOKEN = document.querySelector('meta[name="smtv-token"]')?.content || "";
async function call(method, url, body) {
  let res;
  try {
    res = await fetch(url, { method, headers: body !== undefined ? { "Content-Type": "application/json", "X-SMTV-Token": TOKEN } : { "X-SMTV-Token": TOKEN },
      body: body !== undefined ? JSON.stringify(body) : undefined });
  } catch { throw Object.assign(new Error(t("offline")), { code: "offline" }); }
  const data = await res.json().catch(() => ({}));
  if (data.error === "stale_page") reloadStale();   // SMTV started again: this page's token is gone (A20)
  if (!res.ok) throw Object.assign(new Error(data.message || res.statusText), { code: data.error, status: res.status });
  return data;
}
export const getJSON = (url) => call("GET", url);
export const postJSON = (url, body = {}) => call("POST", url, body);

export function upload(file, onProgress) {
  return new Promise((resolve, reject) => {
    const x = new XMLHttpRequest();
    x.open("PUT", "/api/uploads");
    x.setRequestHeader("X-SMTV-Token", TOKEN);
    x.setRequestHeader("X-File-Name", encodeURIComponent(file.name));
    x.upload.onprogress = (e) => e.lengthComputable && onProgress?.(e.loaded / e.total);
    x.onload = () => { let d = {}; try { d = JSON.parse(x.responseText); } catch {} if (d.error === "stale_page") reloadStale(); x.status < 300 ? resolve(d) : reject(new Error(d.message || x.statusText)); };
    x.onerror = () => reject(new Error(t("offline")));
    x.send(file);
  });
}

// The job's events, live. The browser reconnects by itself and sends Last-Event-ID, so nothing is lost or repeated.
export function stream(url, { onEvent, onStatus, onState }) {
  const es = new EventSource(url);
  es.addEventListener("job", (m) => { try { onEvent(JSON.parse(m.data)); } catch (e) { console.error(e); } });
  es.addEventListener("status", (m) => { try { onStatus?.(JSON.parse(m.data)); } catch {} });
  es.onopen = () => onState?.("open");
  es.onerror = () => onState?.(es.readyState === 2 ? "closed" : "reconnecting");
  return () => es.close();
}

// --- the window's state (stage 8; signals since V6): what the server's one stream of window events
// (/api/window/events) says — requests, what runs now, tokens, updates — each part a signal. Views show it with
// effects that read the parts they need; nothing asks the server every few seconds.
import { signal, computed, effect, batch, bindText, bindAttr } from "./dom.js";
export { signal, computed, effect, batch, bindText, bindAttr };
export const live = { jobs: signal(null), activity: signal(null), usage: signal(null), update: signal(null), crash: signal(null), link: signal("connecting") };

const byNewest = (a, b) => (b.updated || 0) - (a.updated || 0);
function upsertJob(job) {
  const list = (live.jobs.peek() || []).filter((j) => !(j.tool === job.tool && j.id === job.id));
  live.jobs.value = [...list, job].sort(byNewest);
}
// One connection for the whole window (a browser allows six per site; a request's own stream is the second one). After a
// reconnect the server sends the whole picture again, so nothing is lost. A window that saw SMTV quit for an update
// reloads when SMTV answers again: the new SMTV has a new session token.
let firstSnapshot;
const snapshotReady = new Promise((r) => { firstSnapshot = r; });
function watchWindow() {
  let es = null, leaving = false, bootId = null;
  const open = () => {
    es = new EventSource(`/api/window/events?lang=${lang}`);
    const on = (name, fn) => es.addEventListener(name, (m) => { try { fn(JSON.parse(m.data)); } catch (e) { console.error(e); } });
    on("snapshot", (d) => {
      if (leaving) { location.reload(); return; }
      if (bootId && d.boot && d.boot !== bootId && reloadStale()) return;   // a new start of SMTV: a new token
      bootId = d.boot || bootId;
      batch(() => { live.jobs.value = (d.jobs || []).sort(byNewest); live.activity.value = d.activity; live.usage.value = d.usage; live.update.value = d.update; live.crash.value = d.crash; });
      firstSnapshot();
    });
    on("job", upsertJob);
    on("job_gone", (d) => { live.jobs.value = (live.jobs.peek() || []).filter((j) => !(j.tool === d.tool && j.id === d.id)); });
    on("activity", (v) => { live.activity.value = v; });
    on("usage", (v) => { live.usage.value = v; });
    on("crash", (v) => { live.crash.value = v; });
    on("update", (v) => { if (v?.leaving) leaving = true; live.update.value = v; });
    es.onopen = () => { live.link.value = "open"; };
    es.onerror = () => {
      live.link.value = "lost";
      if (es.readyState === 2) { es.close(); setTimeout(open, 2000); }   // closed for good (a server restarting): open again, every time
      // a phone whose access was switched off on the computer: show «scan the QR code again» instead of waiting forever
      if (PHONE) fetch("/api/hello").then((r) => { if (r.status === 403) location.reload(); }).catch(() => {});
      // a tab whose SMTV started again: its old cookie is refused, the page reloads with the new one
      else fetch("/api/updates").then((r) => r.json()).then((d) => { if (d.error === "stale_page") reloadStale(); }).catch(() => {});
    };
  };
  open();
}

export function toast(message, kind = "") {
  const el = h("div.toast", { class: "toast " + kind, role: "status" }, message);
  document.getElementById("toasts").append(el);
  setTimeout(() => el.remove(), kind === "bad" ? 7000 : 3500);
}

async function copy(text, btn) {
  try { await navigator.clipboard.writeText(text); if (btn) { const o = btn.textContent; btn.textContent = t("copied"); setTimeout(() => (btn.textContent = o), 1200); } } catch {}
}

// --- theme and language
const THEMES = ["auto", "dark", "light"];
let theme = store("smtv.theme") || "auto";
function applyTheme() {
  if (theme === "auto") document.documentElement.removeAttribute("data-theme"); else document.documentElement.dataset.theme = theme;
  // SMTV's window on macOS: the glass and the window's own buttons follow the page's theme. «auto» is sent as it is:
  // the window then follows the system, and so does this page (its prefers-color-scheme comes from the window).
  windowMessage("theme:" + theme);
}
function setTheme(next) { theme = next; store("smtv.theme", theme); applyTheme(); }
// the Windows bridge comes up after the page's first theme; «auto» is said again when the system switches its mode
window.addEventListener("pywebviewready", () => windowMessage("theme:" + theme));
window.matchMedia("(prefers-color-scheme: dark)").addEventListener?.("change", () => { if (theme === "auto") windowMessage("theme:auto"); });
function setLang(next) {   // "" — as in the system
  try { if (next) localStorage.setItem("smtv.lang", next); else localStorage.removeItem("smtv.lang"); } catch {}
  if ((next || systemLang()) !== lang) location.reload();
}
function applyLang() {
  document.documentElement.lang = lang;
  for (const el of document.querySelectorAll("[data-t]")) el.textContent = t(el.dataset.t);
  applyTheme();
}

// --- Settings: a page of its own (#/settings/<section>), opened from the profile menu (owner, 20.11)
let state = null;
let DOCKER = false;  // SMTV runs in Docker (stage 21): opened in a browser, updated by a new image
let PHONE = false;   // this page is open on a phone (stage 9): no model key, no changes to the program here
export function openSettings(tab) { api.go("settings", !tab || tab === "model" ? (PHONE ? "agents" : "providers") : tab); }

// providers and agents (stage 19), then a block for each tool that has one (its switches and/or its own mountSettings), then System
function settingsTools() {
  return (state?.tools || []).filter((x) => x.page && (x.page.options || modules.get(x.name)?.mod?.mountSettings));
}
function settingsSections() {
  return [...(PHONE ? [] : [{ id: "account", label: t("sm_account"), ico: ICONS.user }, { id: "providers", label: t("providers"), ico: ICONS.spark }]),
    { id: "agents", label: t("agents_set"), ico: ICONS.code },
    ...(PHONE ? [] : [{ id: "speech", label: t("speech_set"), ico: ICONS.mic }]),
    ...settingsTools().map((x) => ({ id: "tool-" + x.name, label: x.page.title, ico: toolIcon(x), tool: x })),
    { id: "look", label: t("look_set"), ico: ICONS.globe }, { id: "system", label: t("system"), ico: ICONS.pulse }, { id: "about", label: t("ab_title"), ico: ICONS.info }];
}
// Settings stay mounted while you move between sections (V6): the list keeps its place and only marks the open one;
// the right side shows the section.
let settingsView = null;
function showSettings(parts) {
  markRail("profile");
  const sections = settingsSections();
  // a narrow window shows the list alone until a section is picked: nothing is marked open there
  const narrow = window.matchMedia("(max-width: 860px)").matches;
  const cur = sections.find((x) => x.id === parts[0]) || sections[0];
  const marked = parts[0] || !narrow ? cur : null;
  if (!settingsView || document.getElementById("view").firstChild !== settingsView.node) {
    const sc = screen({ side: true });
    sc.sideHead.append(h("h2.side-title", t("settings")));
    settingsView = sc;
    mountView(sc.node, () => { settingsView = null; });
  }
  const sc = settingsView;
  keyed(sc.sideList, [...sections, ...(state?.support ? [{ id: "support" }] : [])], {
    key: (x) => x.id,
    create: (x) => x.id === "support"
      // «Support the project» at the bottom of Settings (owner, 21.11): a link out, not a section
      ? h("a.side-item.side-support", { href: state.support, target: "_blank", rel: "noopener noreferrer" }, h("span.side-ico", icon(ICONS.heart)), h("span.side-text", h("b", t("support"))))
      : h("a.side-item", { href: `#/settings/${x.id}` }, h("span.side-ico", icon(x.ico)), h("span.side-text", h("b", x.label))),
    update: (el, x) => { if (x.id !== "support") attr(el, "aria-current", x === marked ? "page" : "false"); },
  });
  sc.node.classList.toggle("open", !!parts[0]);
  const key = sig(cur.id, parts.slice(1));
  if (sc.shown === key) return;
  sc.shown = key;
  const body = h("div.settings-body", h("div.faint", "…"));
  sc.main.replaceChildren(h("a.btn.btn-ghost.btn-sm.back", { href: "#/settings" }, icon(ICONS.left), t("settings")),
    h("div.settings-page", h("h1.h-big", cur.label), body));   // a centred column, as the system's own settings
  sc.main.scrollTop = 0;
  if (cur.tool) renderToolSettings(body, cur.tool);
  else ({ account: renderAccount, look: renderLook, providers: renderProviders, agents: renderAgents, speech: renderSpeech, system: renderSystem, about: renderAbout })[cur.id](body, parts.slice(1));
}

// Settings look like the system's own (owner, 20.11): groups under a small heading, each a rounded card of rows split by
// thin lines — the name and a short explanation on the left, the control on the right.
function setGroup(title, ...rows) {
  return h("section.set-group", title ? h("h2.set-group-title", title) : null, h("div.set-card", ...rows.flat().filter(Boolean)));
}
function setRow(label, about, ...controls) {
  return h("div.set-row", h("div.set-text", h("b", label), about ? (about instanceof Node ? about : h("p", about)) : null), h("div.set-ctl", ...controls.filter(Boolean)));
}
function switchFor(checked, onchange, label) {
  const input = h("input", { type: "checkbox", role: "switch", "aria-label": label });
  input.checked = !!checked;
  input.onchange = () => onchange(input);
  return h("label.switch", input, h("span"));
}

// --- Settings → Providers and Settings → Agents (stage 19) -----------------------------------------------------------
// Providers: a list of connections, several of one kind under different keys and names. Agents: every agent of every
// plugin (the core's shared ones once) with its provider and model, both from dropdowns. The model is changed only here;
// a plugin's «Agents» tab shows it read-only with «Change», which opens this page on that agent.

// a kind's note and steps in the window's language; the server's English text otherwise
const own = (key, fallback) => (t(key) === key ? fallback : t(key));
const noteOf = (c) => own("pv_note_" + c.choice, c.note || "");
const GROUPS = ["main", "local", "cloud", "cli"];
const stepsOf = (c) => (t("pv_steps_" + c.kind) === "pv_steps_" + c.kind ? c.steps || [] : t("pv_steps_" + c.kind).split("|"));
const CLI_WHO = { codex: { who: "ChatGPT", org: "OpenAI" }, claude_code: { who: "Claude", org: "Anthropic" } };
const choiceLabel = (c) => own("pv_kind_" + c.choice, c.label || c.name || c.choice);
const keyText = (where) => t(where === "keychain" ? "pv_key_keychain" : "pv_key_file");
function checkText(r, cli) {
  if (r.account) return r.ok ? t("sm_check_ok") : r.reachable ? t("sm_check_signin") : `${r.detail}${r.hint ? " " + r.hint : ""}`;
  if (cli && r.status !== "error") return t(r.ok ? "st_ok_cli" : (r.status === "not_installed" ? "st_not_installed_cli" : "st_not_signed_in_cli"));
  return t(r.ok ? "st_ok" : "st_" + r.status) + (r.ok && r.models ? " " + t("pv_models_n", { n: r.models }) : "") + (r.ok ? "" : " " + (r.detail || ""));
}
function checkResult(r, cli) {
  return h("div", { class: "result " + (r.ok ? "ok" : "bad") }, icon(r.ok ? ICONS.check : ICONS.x), h("div", checkText(r, cli)));
}
// the CLIs: whose subscription it runs on, the rules in force, how to connect
function cliNotice(c) {
  const w = CLI_WHO[c.kind || c.choice];
  return h("div.pv-cli",
    h("div.result.warn", icon(ICONS.warn), h("span", t("pv_cli_warn", w))),
    h("div.result.bad", icon(ICONS.warn), h("span", t("pv_cli_discouraged", w))),
    h("p.hint", t("pv_rules"), " ", ...(c.rules || []).flatMap((r, i) => [i ? " · " : "", h("a", { href: r.url, target: "_blank", rel: "noopener noreferrer" }, r.title)])),
    stepsOf(c).length ? h("details.pv-steps", h("summary", t("pv_how")), h("ol", ...stepsOf(c).map((x) => h("li", x))),
      c.key_url ? h("a.hint", { href: c.key_url, target: "_blank", rel: "noopener noreferrer" }, c.key_url) : null) : null);
}
function priceText(m) {
  const p = m.price || {};
  if (p.kind === "subscription") return t("m_sub");
  if (p.kind === "balance") return t("m_balance");
  if (p.kind === "table") return t("m_price", { i: fmt.dec(p.in, p.in < 1 ? 2 : 2).replace(/[.,]00$/, ""), o: fmt.dec(p.out, 2).replace(/[.,]00$/, "") });
  return t("m_price_unknown");
}
function modelChips(m, withMarks = true) {
  return [withMarks && m.recommended ? h("span.chip.accent", t("m_recommended")) : null,
    withMarks ? (m.tested?.length ? h("span.chip.ok", t("m_tested")) : h("span.chip", t("m_untested"))) : null,
    m.images === true ? h("span.chip", t("m_images")) : m.images === false ? h("span.chip", t("m_no_images")) : null,
    h("span.chip", priceText(m))].filter(Boolean);
}
function modelOptionText(m) {
  const marks = [m.recommended ? t("m_recommended") : null, m.recommended || m.tested?.length ? (m.tested?.length ? t("m_tested") : t("m_untested")) : null,
    m.images ? t("m_images") : null, priceText(m), ...(m.warnings || []).map((w) => t("mw_" + w))].filter(Boolean);
  return `${m.id || (m.price?.kind === "balance" ? t("sm_model") : t("ag_codex_default"))} — ${marks.join(", ")}`;
}

// a model dropdown: the list, «Another model…» with a field to type the name
function modelPicker(list, current, onPick) {
  const OTHER = "\u0000other";
  const ids = list.models.map((m) => m.id);
  const select = h("select.select.set-select", { "aria-label": t("ag_model_sel") },
    ...list.models.map((m) => h("option", { value: m.id }, modelOptionText(m))),
    current != null && !ids.includes(current) ? h("option", { value: current }, current) : null,
    h("option", { value: OTHER }, t("ag_other")));
  select.value = current ?? "";
  const other = h("input.input.set-input", { type: "text", placeholder: t("ag_other_ph"), spellcheck: "false", autocomplete: "off", maxlength: "200" });
  const use = h("button.btn.btn-sm", { type: "button" }, t("ag_typed"));
  const typed = h("div.pv-typed", other, use);
  typed.hidden = true;
  select.onchange = () => {
    typed.hidden = select.value !== OTHER;
    if (select.value === OTHER) { other.focus(); return; }
    onPick(select.value);
  };
  use.onclick = () => { const v = other.value.trim(); if (v) onPick(v); else other.focus(); };
  const note = list.live && !list.live.ok && list.live.detail ? h("p.hint", t("ag_live_failed", { detail: list.live.detail })) : null;
  if (note && !list.models.length) { typed.hidden = false; }
  return { select, typed, note };
}

async function renderProviders(body) {
  let s, open = null, added = null, adding = null;
  const results = new Map();
  const reload = async () => { s = await getJSON("/api/settings"); };
  try { await reload(); } catch (e) { body.replaceChildren(h("div.result.bad", e.message)); return; }
  const choice = (p) => s.choices.find((c) => c.kind === p.kind && (p.kind !== "openai" || c.preset === (p.preset || "openai"))) || {};

  const row = (p) => {
    const c = choice(p);
    const status = [h("span.chip", choiceLabel(c)), p.local ? h("span.chip.info", t("pv_local")) : null, !p.enabled ? h("span.chip.warn", t("pv_off")) : null,
      p.kind === "streammoment" ? h("span.chip", t("sm_by_balance")) : null,
      p.cli ? h("span.chip", t("pv_sub")) : p.key.unreadable ? h("span.chip.bad", t("pv_key_unreadable"))
        : p.key.needed ? h(p.key.saved ? "span.chip.ok" : "span.chip.warn", t(p.key.saved ? "pv_key_saved" : "pv_key_missing")) : null,
      h("span.chip", t("pv_agents", { n: p.agents }))];
    const result = h("div.set-result", { "aria-live": "polite" }, results.get(p.id) || null);
    const check = h("button.btn.btn-sm", { type: "button", onclick: async () => {
      check.disabled = true; check.textContent = t("checking");
      try { const r = await postJSON(`/api/settings/providers/${encodeURIComponent(p.id)}/check`, {}); results.set(p.id, checkResult(r, p.cli)); }
      catch (e) { results.set(p.id, h("div.result.bad", e.message)); }
      result.replaceChildren(results.get(p.id)); check.disabled = false; check.textContent = t("check");
    } }, t("check"));
    const toggle = switchFor(p.enabled, async (input) => {
      try { s = await postJSON(`/api/settings/providers/${encodeURIComponent(p.id)}`, { enabled: input.checked }); toast(t("saved")); refreshDoctorDot(); draw(); }
      catch (e) { input.checked = !input.checked; toast(e.message, "bad"); }
    }, t("pv_on"));
    const edit = h("button.btn.btn-ghost.btn-sm", { type: "button", onclick: () => { open = open === p.id ? null : p.id; draw(); } }, open === p.id ? t("pv_close") : t("pv_edit"));
    return h("div.pv-item", { id: "pv-" + p.id },
      h("div.set-row", h("div.set-text", h("b", p.name), h("div.plugin-meta", ...status.filter(Boolean))), h("div.set-ctl", check, edit, toggle)),
      result, p.kind === "streammoment" ? h("div.pv-account", h("a.btn.btn-sm", { href: "#/settings/account" }, t("sm_open_account"))) : null,
      open === p.id ? editPanel(p, c) : null);
  };

  const editPanel = (p, c) => {
    const form = { name: p.name, base_url: p.base_url };
    const key = p.key.needed || (p.kind === "openai" && p.preset === "custom") ? h("input.input.set-input", { type: "password", autocomplete: "off", spellcheck: "false",
      placeholder: p.key.saved ? t("key_keep") : t("key_placeholder"), "aria-label": t("key") }) : null;
    const save = h("button.btn.btn-primary.btn-sm", { type: "button", onclick: async () => {
      save.disabled = true;
      try {
        s = await postJSON(`/api/settings/providers/${encodeURIComponent(p.id)}`, { ...form, key: key?.value || "" });
        toast(t("saved")); refreshDoctorDot(); open = null; draw();
      } catch (e) { toast(e.message, "bad"); save.disabled = false; }
    } }, t("save"));
    const del = h("button.btn.btn-danger.btn-sm", { type: "button", onclick: async () => {
      if (!await confirmDialog({ title: t("pv_del_title", { name: p.name }), text: t("pv_del_text"), ok: t("pv_delete"), cancel: t("ag_cancel"), danger: true })) return;
      try { s = await postJSON(`/api/settings/providers/${encodeURIComponent(p.id)}/delete`, {}); results.delete(p.id); open = null; refreshDoctorDot(); draw(); }
      catch (e) { toast(e.message, "bad"); }
    } }, t("pv_delete"));
    const recommend = h("button.btn.btn-sm", { type: "button", onclick: () => assign(p, recommend) }, t("pv_rec_btn"));
    const defaultBox = h("div.pv-default");
    if (p.table == null && !p.cli) {   // a server the table does not know: its default model, from its own list
      getJSON(`/api/settings/providers/${encodeURIComponent(p.id)}/models`).then((list) => {
        const pick = modelPicker(list, p.default_model, async (model) => {
          try { s = await postJSON(`/api/settings/providers/${encodeURIComponent(p.id)}`, { default_model: model }); toast(t("saved")); draw(); }
          catch (e) { toast(e.message, "bad"); }
        });
        defaultBox.replaceChildren(pick.select, pick.typed, pick.note || "");
      }).catch((e) => defaultBox.replaceChildren(h("div.result.bad", e.message)));
    }
    return h("div.pv-edit",
      setRow(t("pv_name"), t("pv_name_hint"), h("input.input.set-input", { value: form.name, maxlength: "60", "aria-label": t("pv_name"), oninput: (e) => (form.name = e.target.value) })),
      p.kind === "openai" && (p.preset === "custom" || p.local) ? setRow(t("pv_server"), p.local ? t("pv_server_local") : t("pv_server_hint"), h("input.input.set-input", { value: form.base_url, "aria-label": t("pv_server"), oninput: (e) => (form.base_url = e.target.value) })) : null,
      p.kind === "openai" && p.api !== "ollama" ? setRow(t("pv_json"), t("pv_json_hint"), (() => {
        const sel = h("select.select.set-select", { "aria-label": t("pv_json") }, ...["schema", "object", "none"].map((m) => h("option", { value: m, selected: m === p.json_mode }, t("pv_json_" + m))));
        sel.onchange = async () => { try { s = await postJSON(`/api/settings/providers/${encodeURIComponent(p.id)}`, { json_mode: sel.value }); toast(t("saved")); } catch (e) { toast(e.message, "bad"); } };
        return sel; })()) : null,
      p.api === "ollama" ? ollamaPanel(p) : null,
      key ? setRow(t("key"), h("p", keyText(s.where), p.kind === "openai" && p.table == null ? " " + t("pv_key_optional") : "",
        c.key_url ? [" ", h("a", { href: c.key_url, target: "_blank", rel: "noopener noreferrer" }, t("where_key"))] : null), key) : null,
      p.cli ? cliNotice(c) : null,
      p.table == null && !p.cli ? setRow(t("pv_default_model"), t("pv_default_model_hint"), defaultBox) : null,
      setRow(t("pv_rec_btn"), t("pv_rec_row"), recommend),
      h("div.set-actions.pv-actions", del, save));
  };

  const assign = async (p, btn) => {
    if (btn) btn.disabled = true;
    try {
      const r = await postJSON(`/api/settings/providers/${encodeURIComponent(p.id)}/recommend`, {});
      toast(r.assigned.length ? t("pv_rec_done", { name: p.name, n: r.assigned.length }) : t("pv_rec_none"), r.assigned.length ? "ok" : "");
      added = null; await reload(); draw();
    } catch (e) { toast(e.message, "bad"); if (btn) btn.disabled = false; }
  };

  const addForm = () => {
    const c = s.choices.find((x) => x.choice === adding.choice);
    const result = h("div.set-result", { "aria-live": "polite" });
    const key = c && (c.needs_key || c.choice === "custom") ? h("input.input.set-input", { type: "password", autocomplete: "off", spellcheck: "false", placeholder: t("key_placeholder"), "aria-label": t("key") }) : null;
    const groups = adding.groups || GROUPS;
    const offered = (g) => s.choices.filter((x) => x.group === g && !x.account);
    const kind = h("select.select.set-select", { "aria-label": t("pv_kind"), onchange: (e) => { adding = { choice: e.target.value, groups: adding.groups }; draw(); } },
      h("option", { value: "", disabled: true, selected: !c }, "—"),
      ...groups.filter((g) => offered(g).length).map((g) => h("optgroup", { label: t("pv_group_" + g) },
        ...offered(g).map((x) => h("option", { value: x.choice, selected: x.choice === adding.choice }, choiceLabel(x))))));
    const payload = () => ({ kind: c.kind, preset: c.preset, name: adding.name || "", key: key?.value || "",
      base_url: c.choice === "custom" ? adding.base_url || "" : c.local ? adding.base_url || c.base_url : undefined });
    const check = h("button.btn.btn-sm", { type: "button", onclick: async () => {
      check.disabled = true; check.textContent = t("checking");
      try { result.replaceChildren(checkResult(await postJSON("/api/settings/providers/check", payload()), c.cli)); }
      catch (e) { result.replaceChildren(h("div.result.bad", e.message)); }
      check.disabled = false; check.textContent = t("check");
    } }, t("check"));
    const add = h("button.btn.btn-primary.btn-sm", { type: "button", onclick: async () => {
      add.disabled = true;
      try {
        const r = await postJSON("/api/settings/providers", payload());
        s = r; adding = null; added = { id: r.added, n: r.can_recommend };
        const p = s.providers.find((x) => x.id === r.added);
        toast(t("pv_added", { name: p?.name || "" }), "ok"); refreshDoctorDot(); draw();
      } catch (e) { toast(e.message, "bad"); add.disabled = false; }
    } }, t("pv_add"));
    return h("section.set-group.pv-add", h("h2.set-group-title", t(adding.groups?.includes("cli") ? "ch_other" : adding.groups?.includes("local") ? "ch_local" : "ch_key")), h("div.set-card",
      setRow(t("pv_kind"), c ? noteOf(c) : t("step_provider"), kind),
      c ? setRow(t("pv_name"), t("pv_name_hint"), h("input.input.set-input", { value: adding.name || "", placeholder: c.name, maxlength: "60", "aria-label": t("pv_name"), oninput: (e) => (adding.name = e.target.value) })) : null,
      c?.choice === "custom" || c?.local ? setRow(t("pv_server"), c.local ? t("pv_server_local") : t("pv_server_hint"), h("input.input.set-input", { value: adding.base_url || (c.local ? c.base_url : ""), placeholder: c.local ? c.base_url : "http://127.0.0.1:8080/v1", "aria-label": t("pv_server"), oninput: (e) => (adding.base_url = e.target.value) })) : null,
      c?.local ? h("div.set-row", h("p.hint", t("pv_local_install"), " ", h("a", { href: c.key_url, target: "_blank", rel: "noopener noreferrer" }, c.key_url))) : null,
      key ? setRow(t("key"), h("p", keyText(s.where), c.choice === "custom" ? " " + t("pv_key_optional") : "",
        c.key_url ? [" ", h("a", { href: c.key_url, target: "_blank", rel: "noopener noreferrer" }, t("where_key"))] : null), key) : null,
      c?.cli ? h("div.set-row.pv-cli-row", cliNotice(c)) : null,
      c?.account ? h("div.set-row", h("p.hint", t("sm_add_note"))) : null),
      c ? result : null,
      h("div.set-actions.pv-actions", h("button.btn.btn-ghost.btn-sm", { type: "button", onclick: () => { adding = null; draw(); } }, t("ag_cancel")), c ? check : null, c ? add : null));
  };

  // «Find on this computer»: the usual addresses of Ollama, LM Studio, vLLM and llama.cpp
  let found = null;
  const findBtn = (label = t("pv_find")) => {
    const b = h("button.btn.btn-sm", { type: "button", onclick: async () => {
      b.disabled = true; b.textContent = t("pv_finding");
      try { found = (await postJSON("/api/settings/providers/discover", {})).servers; } catch (e) { toast(e.message, "bad"); }
      draw();
    } }, label);
    return b;
  };
  const foundBox = () => h("div.pv-found", setGroup(t("pv_found_title"), found.map((f) => setRow(f.label,
    h("p", f.found ? t("pv_found_yes", { url: f.base_url, n: f.count }) : t("pv_found_no", { url: f.base_url }),
      !f.found ? [" ", h("a", { href: f.install_url, target: "_blank", rel: "noopener noreferrer" }, t("pv_get_it"))] : null),
    f.added ? h("span.chip.ok", t("pv_found_added")) : f.found ? (() => {
      const b = h("button.btn.btn-primary.btn-sm", { type: "button", onclick: async () => {
        b.disabled = true;
        try {
          const r = await postJSON("/api/settings/providers", { kind: "openai", preset: f.preset, base_url: f.base_url, name: "" });
          s = r; added = { id: r.added, n: r.can_recommend }; found = found.map((x) => x.preset === f.preset ? { ...x, added: r.added } : x);
          toast(t("pv_added", { name: f.label }), "ok"); refreshDoctorDot(); draw();
        } catch (e) { toast(e.message, "bad"); b.disabled = false; }
      } }, t("pv_add_short"));
      return b; })() : h("span.chip", t("pv_found_none"))))),
    h("div.set-actions", h("button.btn.btn-ghost.btn-sm", { type: "button", onclick: () => { adding = { choice: "", groups: ["local"] }; draw(); } }, t("pv_manual"))));

  const banner = () => {
    const p = s.providers.find((x) => x.id === added.id);
    if (!p || !added.n) return null;
    const btn = h("button.btn.btn-primary.btn-sm", { type: "button", onclick: () => assign(p, btn) }, t("pv_rec_btn"));
    return h("div.card.card-pad.pv-banner", h("p", t("pv_rec_ask", { name: p.name, n: added.n })),
      h("div.ag-actions", btn, h("button.btn.btn-ghost.btn-sm", { type: "button", onclick: () => { added = null; draw(); } }, t("pv_later"))));
  };

  // V1 (owner 22.11): a newcomer picks one of three plain ways — through the account (our key), their own key, free on
  // this computer; the subscriptions of the CLIs are hidden under «Other ways». The kinds of each way are in «Connect».
  const ways = () => {
    const none = !s.providers.length;
    const hasAccount = s.providers.some((p) => p.kind === "streammoment");
    const open = (groups) => () => { adding = { choice: "", groups }; draw(); };
    const title = (text, tag) => h("span.pv-way-title", text, tag ? h("span.chip.accent", tag) : null);
    return h("section.set-group.pv-ways", h("h2.set-group-title", t(none ? "ch_title" : "ch_more_title")), h("div.set-card",
      hasAccount ? null : setRow(title(t("ch_account"), t("ch_account_tag")), t("ch_account_text"),
        h(none ? "a.btn.btn-primary.btn-sm" : "a.btn.btn-sm", { href: "#/settings/account" }, t("ch_account_btn"))),
      setRow(title(t("ch_key")), t("ch_key_text"), h("button.btn.btn-sm", { type: "button", onclick: open(["main", "cloud"]) }, t("ch_key_btn"))),
      setRow(title(t("ch_local")), t("ch_local_text"), findBtn(t("ch_local_btn")))),
      h("details.pv-more", h("summary", t("ch_other")),
        h("div.set-row", h("div.set-text", h("p", t("ch_cli_text"))), h("div.set-ctl", h("button.btn.btn-sm", { type: "button", onclick: open(["cli"]) }, t("ch_cli_btn"))))),
      h("p.hint.pv-term", t("ch_term")),
      h("p.hint", h("a", { href: GUIDE + "connect-ai.md", target: "_blank", rel: "noopener noreferrer" }, t("ch_guide"))));
  };
  // each block and each connection's row is built again only when its own data changed (V6): a check's result, a
  // typed name or an open «Change» of another row stay as they are
  const draw = () => {
    blocks(body, [
      ["lead", null, () => h("p.muted.set-lead", t("pv_intro"))],
      s.broken ? ["broken", s.broken, () => h("div.result.bad", t("set_broken", { file: s.broken }))] : null,
      added && banner() ? ["banner", sig(added, s.providers.find((x) => x.id === added.id)?.name), banner] : null,
      s.providers.length ? ["list", null, () => setGroup(t("pv_list"))] : null,
      found ? ["found", sig(found), foundBox] : null,
      adding ? ["add", sig(adding.choice, adding.groups), addForm] : ["ways", sig(s.providers.map((p) => p.kind)), ways]]);
    if (s.providers.length) groupRows(blockOf(body, "list"), s.providers, { key: (p) => p.id, sig: (p) => sig(p, choice(p), open === p.id, s.where), create: row });
  };
  draw();
}

// --- stage 22: the StreamMoment account — sign-in, balance, packages ------------------------------------------------
Object.assign(ICONS, {
  user: '<circle cx="12" cy="8.5" r="3.5"/><path d="M5 19.5c1.2-3.3 3.8-5 7-5s5.8 1.7 7 5"/>',
  globe: '<circle cx="12" cy="12" r="8"/><path d="M4 12h16M12 4c2.2 2.4 3.2 5 3.2 8s-1 5.6-3.2 8c-2.2-2.4-3.2-5-3.2-8s1-5.6 3.2-8Z"/>',
});
// Our server is asked only while this panel is on the page: when it opens, after a purchase (every 5 s for 10 minutes,
// until the balance changes) and by the person's buttons. A sign-in in progress is followed locally (/api/account).

// Settings → Account: the StreamMoment account on its own page (owner, 21.11: signing in must be found without adding a provider).
function renderAccount(body) {
  body.replaceChildren(h("p.muted.set-lead", t("sm_add_note")), setGroup(null, h("div.set-row.sm-row", accountPanel())));
}
// a language by its own name: «Русский», «English», «Português (Brasil)»
const langName = (code) => { try { return (new Intl.DisplayNames([code], { type: "language" }).of(code) || code).replace(/^./, (x) => x.toUpperCase()); } catch { return code; } };
function langSelect() {
  const sel = h("select.select.set-select", { "aria-label": t("ui_language"), onchange: () => setLang(sel.value) },
    h("option", { value: "" }, t("lang_system", { name: langName(systemLang()) })),
    LANGS.map((l) => h("option", { value: l }, langName(l))));
  sel.value = store("smtv.lang") && LANGS.includes(store("smtv.lang")) ? store("smtv.lang") : "";
  return sel;
}
// Settings → Language and theme (owner, 21.11: out of the profile menu)
function renderLook(body) {
  // a press marks its own button (V6): the row is not built again
  const seg = (items, value, set) => {
    const box = h("div.seg", { role: "radiogroup" });
    const mark = (cur) => { for (const b of box.children) { attr(b, "aria-selected", String(b.__v === cur)); attr(b, "aria-checked", String(b.__v === cur)); } };
    box.append(...items.map(([v, label]) => Object.assign(h("button", { type: "button", role: "radio", onclick: () => { set(v); mark(v); } }, label), { __v: v })));
    mark(value);
    return box;
  };
  body.replaceChildren(setGroup(null,
    setRow(t("ui_language"), null, langSelect()),
    setRow(t("theme"), null, seg([["auto", t("th_auto")], ["dark", t("th_dark")], ["light", t("th_light")]], theme, setTheme))));
}

function accountPanel() {
  const box = h("div.pv-account", { "aria-live": "polite" });
  let a = null, paying = null, until = 0, timer = null, problem = null;
  // the balance is in tokens, never in money (owner, 22.11); only a package's price is in rubles: that is what YooKassa takes
  const tok = (n) => { const k = "sm_tok_" + new Intl.PluralRules(lang).select(Math.round(n || 0)); const w = t(k) === k ? t("sm_tok_other") : t(k); return w.replace("{n}", fmt.num(n)); };
  const rub = (kopecks) => fmt.num((kopecks || 0) / 100);
  const stop = () => { if (timer) clearTimeout(timer); timer = null; };
  const later = (ms, fn) => { stop(); timer = setTimeout(() => { if (box.isConnected) fn(); }, ms); };
  const load = async (live) => {
    try { a = await getJSON("/api/account" + (live ? "?live=1" : "")); problem = a.error || null; }
    catch (e) { problem = { detail: e.message }; }
    draw();
    if (a?.login?.state === "waiting") later(2000, () => load(false));
    else if (a?.login?.state === "done" && !a.balance) later(0, () => load(true));
    else if (paying && Date.now() < until) later(5000, async () => {
      const before = a?.balance?.tokens; await load(true);
      if (a?.balance && a.balance.tokens !== before) { paying = null; stop(); draw(); }
    });
  };
  const act = (label, fn, cls = "btn.btn-sm") => {
    const b = h("button." + cls, { type: "button", onclick: async () => { b.disabled = true; try { await fn(); } catch (e) { toast(e.message, "bad"); } b.disabled = false; } }, label);
    return b;
  };
  const login = (mode) => act(mode === "device" ? t("sm_login_code") : t("sm_login"), async () => {
    paying = null; a = await postJSON("/api/account/login", { mode }); draw(); later(2000, () => load(false));
  }, mode === "device" ? "btn.btn-sm" : "btn.btn-primary.btn-sm");
  const check = act(t("sm_check"), async () => {
    const r = await postJSON("/api/account/check", {});
    problem = r.reachable ? null : { detail: r.detail, hint: r.hint }; toast(r.reachable ? t("sm_reachable") : r.detail, r.reachable ? "ok" : "bad"); draw();
  });
  // the panel's lines follow the account by key (V6): asking again every 2 s while a sign-in waits rebuilds nothing
  const draw = () => {
    if (!a) { blocks(box, [["wait", null, () => h("p.hint", t("checking"))]]); return; }
    const rows = [];
    const lg = a.login;
    if (!a.signed_in) {
      rows.push(["out", null, () => h("p", t("sm_out"))]);
      if (lg?.state === "waiting" && lg.user_code) rows.push(["code", sig(lg.url, lg.user_code), () => h("div.sm-lines", h("p", t("sm_code", { url: lg.url })), h("p.sm-code", lg.user_code))]);
      else if (lg?.state === "waiting") rows.push(["waiting", lg.url, () => h("p.hint", t("sm_waiting"), " ", h("a", { href: lg.url, target: "_blank", rel: "noopener noreferrer" }, t("sm_open_again")))]);
      if (lg?.state === "failed" && lg.error !== "cancelled") rows.push(["failed", lg.error, () => h("div.result.bad", icon(ICONS.x), h("span", t("sm_failed", { why: lg.error })))]);
      rows.push(["login", null, () => h("div.set-actions", login("browser"), login("device"), check)]);
    } else {
      const who = a.account || {};
      rows.push(["in", sig(who.name, who.provider), () => h("p", t("sm_in", { name: who.name || "—", via: t("sm_via_" + who.provider) }))]);
      if (a.balance) {
        rows.push(["balance", sig(a.balance), () => h("div.sm-lines", h("p", h("b", t("sm_balance") + ": "), t("sm_balance_val", { tokens: tok(a.balance.free), hours: fmt.dec(a.balance.hours, 1) })),
          a.balance.reserved ? h("p.hint", t("sm_held", { tokens: tok(a.balance.reserved) })) : null,
          h("details.sm-tokens", h("summary", t("sm_tokens_more")), h("p.hint", t("sm_tokens_what", { per_hour: tok(a.balance.tokens_per_hour) }))))]);
        const packs = () => (a.packages || []).map((pk) => {
          const b = act(t(pk.once ? "sm_trial" : "sm_pack", { price: rub(pk.price), tokens: tok(pk.tokens) }), async () => {
            const r = await postJSON("/api/account/buy", { package: pk.id });
            paying = r.url; until = Date.now() + 10 * 60_000; draw(); later(5000, () => load(true));
          }, pk.once ? "btn.btn-primary.btn-sm" : "btn.btn-sm");
          if (!pk.available) { b.disabled = true; b.title = t("sm_bought_once"); }
          return b;
        });
        rows.push(["packs", sig(a.payments, a.packages), () => a.payments ? h("div.set-actions", h("span.hint", t("sm_buy") + ":"), ...packs()) : h("p.hint", t("sm_payments_off"))]);
        if (paying) rows.push(["paying", paying, () => h("p.hint", t("sm_paying"), " ", h("a", { href: paying, target: "_blank", rel: "noopener noreferrer" }, t("sm_pay_link")))]);
      }
      rows.push(["acts", null, () => h("div.set-actions", act(t("sm_refresh"), () => load(true)), check, act(t("sm_logout"), async () => {
        if (!await confirmDialog({ title: t("sm_logout_title"), text: t("sm_logout_text"), ok: t("sm_logout"), cancel: t("ag_cancel"), danger: true })) return;
        stop(); paying = null; a = await postJSON("/api/account/logout", {}); refreshDoctorDot(); draw();
      }, "btn.btn-ghost.btn-sm"))]);
    }
    if (problem) rows.push(["problem", sig(problem), () => h("div.result.bad", icon(ICONS.warn), h("span", problem.detail + (problem.hint ? " " + problem.hint : "")))]);
    blocks(box, rows);
  };
  draw();
  load(true);
  return box;
}

// --- stage 20: local servers, Ollama's models, «Settings → Speech» ---------------------------------------------------
Object.assign(ICONS, { mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21M8.5 21h7"/>' });

const gb = (bytes) => t("unit_gb", { n: fmt.dec(bytes / 1e9, 1) });
const mb = (n) => (n >= 1024 ? t("unit_gb", { n: fmt.dec(n / 1024, 1) }) : t("unit_mb", { n: fmt.num(n) }));
function progressOf(d) {
  if (!d) return null;
  if (d.status === "error") return h("div.result.bad", icon(ICONS.x), h("span", t("sp_failed", { detail: d.detail })));
  if (d.status !== "running") return null;
  return progressTick(h("div.dl", h("div.bar", h("i")), h("span.faint")), d);
}
// a download's bar follows it in place (V6): its width and its numbers, nothing else
function progressTick(el, d) {
  if (!el || !d || d.status !== "running") return el;
  const pct = d.total ? Math.min(100, Math.round(100 * d.done / d.total)) : 0;
  const amount = d.unit === "bytes" ? (d.total ? `${gb(d.done)} / ${gb(d.total)}` : "") : (d.total ? `${mb(d.done)} / ${mb(d.total)}` : "");
  attr(el.firstChild.firstChild, "style", `width:${pct}%`);
  text(el.lastChild, `${pct}%` + (amount ? " · " + amount : "") + (d.detail && d.unit === "bytes" ? " · " + d.detail : ""));
  return el;
}
// the rows of a group follow a list by key; a row is built again only when its own sig changes
function groupRows(group, items, opts) { return keyed(group.querySelector(".set-card"), items, opts); }
const blockOf = (parent, key) => [...parent.children].find((n) => n.__key === key) || null;
// what a download is now, without its numbers: a row is built again when it starts, ends or fails, not on every percent
const dlState = (d) => d ? [d.status, d.status === "error" ? d.detail : null] : null;
// while something downloads, the block asks again every 1.5 s; it stops once it is gone from the page or nothing runs
function pollWhile(node, running, again) {
  if (!running) return;
  setTimeout(() => { if (node.isConnected) again(); }, 1500);
}

// Ollama's models in its provider's panel: installed ones, the recommended ones, any other by name
function ollamaPanel(p) {
  const box = h("div.ol-box", h("div.faint", "…"));
  const url = `/api/settings/providers/${encodeURIComponent(p.id)}/ollama`;
  const act = async (action, model) => {
    try { draw(await postJSON(`${url}/${action}`, { model })); } catch (e) { toast(e.message, "bad"); }
  };
  const pull = async (model, sizeGb) => {
    const size = sizeGb ? t("unit_gb", { n: fmt.dec(sizeGb, 1) }) : t("ol_size_unknown");
    if (await confirmDialog({ title: t("ol_pull_title", { model }), text: t("ol_pull_text", { size }), ok: t("ol_get"), cancel: t("ag_cancel") })) act("pull", model);
  };
  let other = null;
  const draw = (d) => {
    const pulls = d.pulls || {};
    const running = Object.values(pulls).some((x) => x.status === "running");
    const dlRow = (row, model, extra) => {
      const st = pulls[model];
      return st && st.status === "running" ? [row.__dl = progressOf(st), h("button.btn.btn-ghost.btn-sm", { type: "button", onclick: () => act("cancel", model) }, t("ol_cancel"))] : [st?.status === "error" ? h("span.chip.bad", t("ol_failed", { detail: st.detail })) : null, extra];
    };
    other ||= h("input.input.set-input", { type: "text", placeholder: t("ol_other_ph"), spellcheck: "false", autocomplete: "off", maxlength: "160" });
    const rowWith = (label, about, ctl) => { const row = setRow(label, about); row.lastChild.append(...ctl(row).filter(Boolean)); return row; };
    const recRow = (m) => rowWith(m.label + " · " + m.id,
      h("div.plugin-meta", h("span.chip", t("unit_gb", { n: fmt.dec(m.size_gb, 1) })), m.vram_gb ? h("span.chip", t("ol_vram", { n: m.vram_gb })) : null,
        h("span.chip", m.images ? t("m_images") : t("m_no_images")), h("span.chip", t("m_untested")),
        m.for.length ? h("span.chip", t("ol_for", { list: m.for.join(", ") })) : null),
      (row) => dlRow(row, m.id, m.installed ? h("span.chip.ok", t("ol_has")) : d.running ? h("button.btn.btn-sm", { type: "button", onclick: () => pull(m.id, m.size_gb) }, t("ol_get")) : null));
    blocks(box, [
      ["hint", null, () => h("p.hint", t("ol_hint"))],
      !d.running ? ["down", sig(d.detail, d.install_url), () => h("div.result.warn", icon(ICONS.warn), h("span", t("ol_not_running", { detail: d.detail }), " ",
        h("a", { href: d.install_url, target: "_blank", rel: "noopener noreferrer" }, t("ol_install")), " · ",
        h("a", { href: "#", onclick: (e) => { e.preventDefault(); load(); } }, t("ol_retry"))))] : null,
      d.running ? ["installed", sig(d.installed), () => setGroup(t("ol_installed"), d.installed.length ? d.installed.map((m) => setRow(m.id,
        h("div.plugin-meta", h("span.chip", gb(m.size_bytes)), m.params ? h("span.chip", m.params) : null,
          m.images === true ? h("span.chip", t("m_images")) : m.images === false ? h("span.chip", t("m_no_images")) : null,
          m.context ? h("span.chip", t("ol_ctx", { n: fmt.num(m.context) })) : null, m.recommended ? h("span.chip.accent", t("m_recommended")) : null),
        h("button.btn.btn-danger.btn-sm", { type: "button", onclick: async () => {
          if (await confirmDialog({ title: t("ol_del_title", { model: m.id }), text: t("ol_del_text", { size: gb(m.size_bytes) }), ok: t("ol_remove"), cancel: t("ag_cancel"), danger: true })) act("delete", m.id);
        } }, t("ol_remove")))) : [setRow(t("ol_none"), null)])] : null,
      ["recommended", null, () => setGroup(t("ol_recommended"))],
    ]);
    const extra = Object.keys(pulls).filter((k) => !d.recommended.some((m) => m.id === k));
    groupRows(blockOf(box, "recommended"), [...d.recommended.map((m) => ({ k: "m:" + m.id, m })), d.running ? { k: "other" } : null, ...extra.map((k) => ({ k: "x:" + k, x: k }))].filter(Boolean), {
      key: (r) => r.k,
      sig: (r) => r.m ? sig(r.m, d.running, dlState(pulls[r.m.id])) : r.x ? sig(dlState(pulls[r.x])) : "",
      create: (r) => r.m ? recRow(r.m) : r.x ? rowWith(r.x, null, (row) => dlRow(row, r.x, h("span.chip.ok", t("ol_has"))))
        : setRow(t("ol_other"), null, other, h("button.btn.btn-sm", { type: "button", onclick: () => { const v = other.value.trim(); if (v) pull(v, null); else other.focus(); } }, t("ol_get"))),
    });
    for (const row of blockOf(box, "recommended").querySelector(".set-card").children) {
      const id = row.__key.startsWith("m:") || row.__key.startsWith("x:") ? row.__key.slice(2) : null;
      if (id && row.__dl?.isConnected) progressTick(row.__dl, pulls[id]);
    }
    pollWhile(box, running, load);
  };
  const load = async () => { try { draw(await getJSON(url)); } catch (e) { box.replaceChildren(h("div.result.bad", e.message)); } };
  load();
  return h("section.set-group.ol", h("h2.set-group-title", t("ol_title")), box);
}

// «Settings → Speech»: the models (where, languages, licence, size, speed; download / remove) and the model of each language
async function renderSpeech(body) {
  const names = (() => { try { return new Intl.DisplayNames([lang], { type: "language" }); } catch { return null; } })();
  const langName = (c) => c === "*" ? null : (names?.of(c) || c).replace(/^./, (x) => x.toUpperCase());
  let d;
  const load = async () => { try { d = await getJSON("/api/settings/speech"); draw(); } catch (e) { body.replaceChildren(h("div.result.bad", e.message)); } };
  const title = (id) => d.models.find((m) => m.id === id)?.title || id;
  const act = async (m, action) => {
    try { d = await postJSON(`/api/settings/speech/models/${encodeURIComponent(m.id)}/${action}`, {}); draw(); } catch (e) { toast(e.message, "bad"); }
  };
  const modelRow = (m) => {
    const who = m.preset === "groq" ? "Groq" : "OpenAI";
    const chips = [h("span.chip" + (m.where === "cloud" ? ".warn" : ".info"), m.where === "cloud" ? t("sp_cloud", { who }) : t("sp_local")),
      h("span.chip", t("sp_langs", { n: m.languages })), h("span.chip", t("sp_licence", { l: m.license })),
      m.where === "local" ? h("span.chip", mb(m.installed ? m.on_disk_mb || m.size_mb : m.size_mb)) : h("span.chip", t("sp_price", { p: fmt.dec(m.price_hour, 2) })),
      h("span.chip", m.speed_x ? t("sp_speed", { x: m.speed_x, how: own("sp_how_" + m.id, m.speed_how) }) : t("sp_speed_unknown"))];
    const dl = progressOf(m.download);
    const about = h("div", h("div.plugin-meta", ...chips), m.where === "local" ? h("p.hint", own("sp_runs_" + m.id, m.runs_on)) : null,
      m.where === "local" && !m.package ? h("p.hint", t("sp_no_package")) : null, dl);
    let ctl;
    if (m.where === "cloud") {
      ctl = m.key ? h("span.chip.ok", t("sp_key_ok", { name: m.provider_name })) : h("a.btn.btn-sm", { href: "#/settings/providers" }, t("sp_key_add"));
      if (!m.key) about.append(h("p.hint", t("sp_key_none", { who })));
    } else if (m.download?.status === "running") {
      ctl = h("span.faint", "…");
    } else if (m.installed) {
      ctl = [h("span.chip.ok", t("sp_on_disk")), h("button.btn.btn-danger.btn-sm", { type: "button", disabled: d.busy, title: d.busy ? t("sp_busy") : null, onclick: async () => {
        if (await confirmDialog({ title: t("sp_del_title", { model: m.title }), text: t("sp_del_text", { size: mb(m.on_disk_mb || m.size_mb) }), ok: t("sp_remove"), cancel: t("ag_cancel"), danger: true })) act(m, "delete");
      } }, t("sp_remove"))];
    } else {
      ctl = h("button.btn.btn-sm", { type: "button", disabled: !m.package, onclick: async () => {
        if (await confirmDialog({ title: t("sp_get_title", { model: m.title }), text: t("sp_get_text", { size: mb(m.size_mb), folder: d.folder }), ok: t("sp_get"), cancel: t("ag_cancel") })) act(m, "download");
      } }, t("sp_get"));
    }
    const row = setRow(m.title, about, ...[ctl].flat());
    row.__dl = dl;
    return row;
  };
  const langRow = (l) => {
    const optText = (id) => {
      const m = d.models.find((x) => x.id === id);
      const mark = m.where === "cloud" && !m.key ? t("sp_no_key_opt") : m.where === "local" && !m.installed ? t("sp_will_download") : "";
      return title(id) + (mark ? " — " + mark : "");
    };
    const sel = h("select.select.set-select", { "aria-label": langName(l.code) || t("sp_others", { n: l.count }) },
      h("option", { value: "" }, t("sp_default_opt", { m: title(l.default) })),
      ...l.choices.map((id) => h("option", { value: id }, optText(id))));
    sel.value = l.source === "own" ? l.model : "";
    sel.onchange = async () => {
      try {
        d = await postJSON("/api/settings/speech/languages", { language: l.code, model: sel.value || null });
        toast(t("sp_saved", { lang: langName(l.code) || t("sp_others", { n: l.count }), m: title(sel.value || l.default) }), "ok"); draw();
      } catch (e) { toast(e.message, "bad"); sel.value = l.source === "own" ? l.model : ""; }   // refused: back to what is saved
    };
    return setRow(l.code === "*" ? t("sp_others", { n: l.count }) : `${langName(l.code)} · ${l.code}`, t("sp_default", { m: title(l.default) }), sel);
  };
  // a row is built again only when what it shows changed; a download only moves its bar (V6)
  const modelSig = (m) => sig({ ...m, download: dlState(m.download) }, d.busy, d.folder);
  const draw = () => {
    blocks(body, [
      ["lead", null, () => h("p.muted.set-lead", t("sp_intro"))],
      d.busy ? ["busy", null, () => h("div.result.warn", icon(ICONS.warn), h("span", t("sp_busy")))] : null,
      ["languages", null, () => setGroup(t("sp_languages"))],     // what is used first, the models and their files below (V1)
      ["models", null, () => setGroup(t("sp_models"))]]);
    groupRows(blockOf(body, "languages"), d.languages, { key: (l) => l.code, sig: (l) => sig(l, d.models.map(modelSig)), create: langRow });
    groupRows(blockOf(body, "models"), d.models, { key: (m) => m.id, sig: modelSig, create: modelRow });
    for (const row of blockOf(body, "models").querySelector(".set-card").children) progressTick(row.__dl, d.models.find((m) => m.id === row.__key)?.download);
    pollWhile(body, d.models.some((m) => m.download?.status === "running"), load);
  };
  load();
}

async function renderAgents(body, rest = []) {
  let d;
  try { d = await getJSON("/api/settings/agents"); } catch (e) { body.replaceChildren(h("div.result.bad", e.message)); return; }
  const focus = rest[0] && rest[1] ? [rest[0], rest[1]] : null;
  const rowOpen = new Set();     // the steps opened with «Change» stay open when the page is drawn again
  const provName = (id) => d.providers.find((p) => p.id === id)?.name || id;
  const send = async (a, payload) => {
    try {
      d = await postJSON(`/api/settings/agents/${encodeURIComponent(a.tool)}/${encodeURIComponent(a.id)}`, payload);
      const now = d.groups.flatMap((g) => g.agents).find((x) => x.id === a.id && x.tool === a.tool)?.current;
      if (now) toast(t("ag_saved", { agent: txt(a.title), model: `${now.provider_name} · ${modelName(now.model)}` }), "ok");
      draw(null);
    } catch (e) {     // refused: the step's row is built again from what is saved (its dropdowns went back)
      toast(e.message, "bad");
      const el = [...body.querySelectorAll(".agset-row")].find((x) => x.dataset.key === `${a.tool}/${a.id}`);
      if (el) el.__ksig = null;
      draw(null);
    }
  };
  const row = (a) => {
    const cur = a.current;
    const n = a.needs;
    const needs = h("div.plugin-meta", h("span.chip", t("lvl_" + n.level)), h("span.chip", n.images ? t("ag_images") : t("ag_text_only")));
    const box = h("div.agset-ctl");
    const marks = h("div.agset-marks");
    const showMarks = (m) => marks.replaceChildren(h("div.plugin-meta", ...modelChips(m)), ...warningsOf(a, m));
    if (!a.providers.length) {
      box.append(h("p.hint", d.providers.some((p) => p.enabled) ? t("ag_no_suitable") : t("ag_no_providers")));
    } else {
      const prov = h("select.select.set-select", { "aria-label": t("ag_provider") },
        ...a.providers.map((id) => h("option", { value: id, selected: id === cur.provider }, provName(id))));
      const modelBox = h("div.agset-model", h("select.select.set-select", { disabled: true }, h("option", modelName(cur.model))));
      const loadModels = async (pid, pick) => {
        try {
          const list = await getJSON(`/api/settings/providers/${encodeURIComponent(pid)}/models?agent=${encodeURIComponent(a.tool + "/" + a.id)}`);
          if (pick) {      // another provider: its best model for this agent right away
            const first = list.models[0];
            if (first) return send(a, { provider: pid, model: first.id });
          }
          const picker = modelPicker(list, pid === cur.provider ? cur.model : null, (model) => send(a, { provider: pid, model }));
          picker.select.addEventListener("change", () => { const m = list.models.find((x) => x.id === picker.select.value); if (m) showMarks(m); });
          modelBox.replaceChildren(picker.select, picker.typed, picker.note || "");
        } catch (e) { modelBox.replaceChildren(h("div.result.bad", e.message)); }
      };
      prov.onchange = () => loadModels(prov.value, true);
      loadModels(cur.provider || a.providers[0], false);
      box.append(prov, modelBox);
    }
    if (cur.source !== "none") showMarks(cur);
    // V1 (owner 22.11): what the step does in one sentence and what it runs on now; the dropdowns, the marks and the
    // long description open under «Change»
    const now = cur.source === "none" ? h("span.faint", t("ag_no_conn"))
      : h("span.agset-now-text", t("ag_now", { what: `${cur.provider_name} · ${modelName(cur.model)}` }));
    return h("div.agset-row", { "data-key": `${a.tool}/${a.id}`, "data-users": a.users.map((u) => `${u}/${a.id}`).join(" ") },
      h("div.agset-head", h("div.agset-title", h("b", txt(a.title)))),
      h("p.muted.agset-does", txt(a.short) || txt(a.does)),
      cur.instead_of ? h("div.result.warn", icon(ICONS.warn), h("span", t("ag_instead", { name: cur.instead_of }))) : null,
      h("details.agset-more", { open: rowOpen.has(`${a.tool}/${a.id}`), ontoggle: (e) => { const k = `${a.tool}/${a.id}`; e.target.open ? rowOpen.add(k) : rowOpen.delete(k); } },
        h("summary", now, h("span.btn.btn-sm.agset-change", t("ag_change_here"))),
        h("div.agset-body",
          txt(a.short) ? h("p.hint", txt(a.does)) : null,
          needs,
          a.shared ? h("p.hint", t("ag_used_in", { list: a.users.map(pluginName).join(", ") })) : null,
          a.differs ? h("p.hint", t("ag_differs")) : null,
          box, marks,
          cur.source === "own" ? h("div.ag-actions", h("button.btn.btn-ghost.btn-sm", { type: "button", onclick: (e) => { e.target.disabled = true; send(a, { reset: true }); } }, t("ag_reset"))) : null)));
  };
  // a step's row is built again only when the step or the connections changed (V6): the others keep their open
  // dropdowns and their loaded lists of models
  const draw = (focusOn) => {
    const provs = sig(d.providers);
    blocks(body, [
      ["lead", null, () => h("p.muted.set-lead", t("ag_set_intro"))],
      !d.providers.some((p) => p.enabled) && !PHONE ? ["none", null, () => h("div.result.warn", icon(ICONS.warn), h("span", t("ag_no_providers"), " ", h("a", { href: "#/settings/providers" }, t("providers"))))] : null,
      ...d.groups.map((g, i) => ["g" + i + ":" + (g.core ? "core" : g.title), null, () => setGroup(g.core ? t("ag_core_group") : g.title)])]);
    d.groups.forEach((g, i) => groupRows(blockOf(body, "g" + i + ":" + (g.core ? "core" : g.title)), g.agents,
      { key: (a) => `${a.tool}/${a.id}`, sig: (a) => sig(a, provs), create: row }));
    if (focusOn) {
      const key = focusOn.join("/");
      const el = [...body.querySelectorAll(".agset-row")].find((x) => x.dataset.key === key || x.dataset.users.split(" ").includes(key));
      if (el) {
        const more = el.querySelector("details.agset-more");
        if (more) more.open = true;
        el.scrollIntoView({ block: "center", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
        el.classList.add("hl");
        setTimeout(() => el.classList.remove("hl"), 2600);
      }
    }
  };
  draw(focus);
}

async function renderToolSettings(body, tool) {
  const parts = [];
  const tt = tool ? toolApi(tool).t : t;   // switch names come from the tool's own strings (opt_<name>)
  if (tool?.page?.options) {
    let opts = [];
    try { opts = await getJSON(`/api/tools/${tool.name}/options`); } catch (e) { parts.push(h("div.result.bad", e.message)); opts = []; }
    const name = (o) => (tt("opt_" + o.name) === "opt_" + o.name ? o.name : tt("opt_" + o.name));
    const about = (o) => (tt("opt_" + o.name + "_about") === "opt_" + o.name + "_about" ? o.about : tt("opt_" + o.name + "_about"));
    if (opts.length) parts.push(setGroup(t("switches"), opts.map((o) => setRow(name(o), about(o), switchFor(o.value, async (input) => {
      try { await postJSON(`/api/tools/${tool.name}/options`, { name: o.name, value: input.checked }); toast(t("saved")); }
      catch (e) { input.checked = !input.checked; toast(e.message, "bad"); }
    }, name(o))))));
  }
  const own = modules.get(tool?.name)?.mod?.mountSettings;
  if (own) {   // the tool's own block; a failing one shows its error and leaves the rest of Settings alone
    const box = h("div.tool-settings");
    try { own(box, toolApi(tool)); } catch (e) { box.replaceChildren(h("div.result.bad", String(e.message || e))); }
    parts.push(box);
  }
  body.replaceChildren(...(parts.length ? parts : [h("p.muted", t("no_switches"))]));
}

async function renderSystem(body) {
  let d;
  // here the check is done again in full, with a free request to each provider's key (stage 24)
  try { d = await getJSON("/api/doctor?fresh=1&live=1"); } catch (e) { body.replaceChildren(h("div.result.bad", e.message)); return; }
  if (!body.isConnected) return;
  const fails = d.rows.filter((r) => r.status === "fail").length;
  setDoctorDot(!fails);
  // grouped: SMTV's own checks, then each tool's (a tool plugs its checks in through Tool.checks)
  const groups = [];
  for (const r of d.rows) { const g = r.group || "smtv"; let x = groups.find((y) => y.name === g); if (!x) groups.push(x = { name: g, rows: [] }); x.rows.push(r); }
  const groupTitle = (g) => g === "smtv" ? t("set_checks") : (state?.tools.find((x) => x.name === g)?.page?.title || g);
  const mark = (r) => h("span", { class: "set-mark " + r.status, title: r.status }, icon(r.status === "ok" ? ICONS.check : r.status === "warn" ? ICONS.warn : ICONS.x));
  const fixLine = (r) => h("div.fix", h("code", r.fix), (() => { const b = h("button.btn.btn-sm", { type: "button" }, t("copy")); b.onclick = () => copy(r.fix, b); return b; })());
  const about = (r) => h("div.set-about", h("p", plainDetail(r)),
    r.status === "ok" || !r.fix || r.recipe ? null : r.actions?.length ? h("details.fix-more", h("summary", t("fx_cmd")), fixLine(r)) : fixLine(r));
  const redo = () => renderSystem(body);
  // «Check again» changes only the checks whose result changed (V6); the groups below stay as they are
  blocks(body, [
    ["sum", fails, () => h("div", { class: "result " + (fails ? "bad" : "ok") }, icon(fails ? ICONS.x : ICONS.check), h("div", fails ? t("system_fix", { n: fails }) : t("system_ready")),
      h("button.btn.btn-sm.btn-ghost", { type: "button", style: "margin-left:auto", onclick: () => renderSystem(body) }, t("recheck")))],
    ...groups.map((g) => ["g:" + g.name, null, () => setGroup(groupTitle(g.name))]),
    ["upd", null, () => PHONE ? setGroup(t("upd_title"), setRow(t("phone_only_pc"), t("phone_only_pc_about"))) : setGroup(t("upd_title"),
      setRow(t("upd_check_daily"), t("upd_check_daily_about"), switchFor(live.update.value?.check !== false, async (input) => {
        try { live.update.value = await postJSON("/api/updates/settings", { check: input.checked }); } catch (e) { input.checked = !input.checked; toast(e.message, "bad"); }
      }, t("upd_check_daily"))),
      (() => { const b = liveBox("update", updateCard); b.className = "set-row upd upd-row"; return b; })())],
    PHONE ? null : ["report", null, () => setGroup(t("report_group"),
      setRow(t("report_btn"), t("report_about"), h("button.btn.btn-sm", { type: "button", onclick: () => reportDialog({}) }, t("report_btn_short"))))],
    DOCKER ? ["program", null, () => setGroup(t("set_program"), setRow(t("dk_stop"), t("dk_stop_about"), cmdLine("docker compose stop")),
      setRow(t("dk_notify"), t("dk_notify_about"), notifyButton()))] : PHONE ? null : ["program", null, () => setGroup(t("set_program"),
      setRow(t("quit_btn"), t("quit_about"), h("button.btn.btn-sm", { type: "button", onclick: quitSmtv }, t("quit_btn"))),
      renderRemove())],
  ]);
  for (const g of groups) groupRows(blockOf(body, "g:" + g.name), g.rows, { key: (r) => r.id, sig: (r) => sig(r), create: (r) => setRow(checkName(r), about(r), ...checkControls(r, redo), mark(r)) });
}

// --- «Fix» (stage 24): a check that can be fixed has a recipe built into SMTV. The dialog shows the whole command and
// links to its official pages before anything runs; then its output, line by line, with «Stop»; at the end the check
// runs again. What needs administrator rights only opens a terminal with the command. Not from a phone.
// V1 (owner 22.11): the checks speak English on the server; the window says the usual ones in plain words of its language
// and shows the server's text for the rest
function plainDetail(r) {
  const d = String(r.detail || ""), ok = r.status === "ok";
  let m;
  switch (r.id) {
    case "model":
      if (!ok && /^no provider set up/.test(d)) return t("chd_model_none");
      if (ok && (m = d.match(/^(.*?) \(keys in the /))) return t("chd_model_ok", { list: m[1] });
      break;
    case "gpu":
      if (/^none found/.test(d)) return t("chd_gpu_none");
      if ((m = d.match(/^(.*) \(used to speed things up\)$/))) return t("chd_gpu_ok", { name: m[1] });
      break;
    case "ffmpeg":
      if (!ok) return t("chd_ffmpeg_none");
      if ((m = d.match(/^ffmpeg version (\S+)/))) return t("chd_ffmpeg_ok", { v: m[1] });
      break;
    case "libass": return t(ok ? "chd_libass_ok" : "chd_libass_fail");
    case "disk": if ((m = d.match(/^(\d+) GB free/))) return t("chd_disk", { n: m[1] }); break;
    case "window": if (ok && /own window$/.test(d)) return t("chd_window_ok"); break;
    case "vodcut-links":
      if (ok && (m = d.match(/^signed in as (.*)$/))) return t("chd_links_in", { name: m[1] });
      if (/^not signed in/.test(d)) return t("chd_links_out");
      break;
    case "speech":
      if ((m = d.match(/^(.*) is on this computer$/))) return t("chd_speech_here", { m: m[1] });
      if ((m = d.match(/^(.*) is not downloaded yet: .*about (\d+) MB/))) return t("chd_speech_later", { m: m[1], n: m[2] });
      break;
  }
  return d;
}
function checkName(r) {
  const k = "chk_" + String(r.id || "").replace(/[^a-z0-9]+/g, "_");
  return t(k) === k ? r.name : t(k);
}
const fmtBytes = (n) => n >= 1e9 ? t("unit_gb", { n: fmt.dec(n / 1e9, 1) }) : t("unit_mb", { n: fmt.dec(n / 1e6, 0) });
// the buttons of a check: «Fix» with its recipe, and what the window itself can do for it
function checkControls(r, after) {
  if (r.status === "ok") return [];
  const out = [];
  if (r.recipe && !PHONE) out.push(h("button.btn.btn-sm.btn-primary", { type: "button", onclick: () => fixDialog(r, after) },
    t(r.recipe.kind === "terminal" ? "fx_terminal_btn" : "fx_fix")));
  for (const a of r.actions || []) {
    if (a === "sign_in") out.push(h("a.btn.btn-sm", { href: "#/settings/account" }, t("fx_sign_in")));
    else if (a === "providers" && !PHONE) out.push(h("a.btn.btn-sm", { href: "#/settings/providers" }, t("fx_providers")));
    else if (a === "speech") out.push(h("a.btn.btn-sm", { href: "#/settings/speech" }, t("fx_speech")));
    else if (a === "open_folder" && !PHONE && !DOCKER) out.push(h("button.btn.btn-sm", { type: "button", onclick: async () => {
      try { await postJSON("/api/folder/open"); } catch (e) { toast(e.message, "bad"); }
    } }, t("fx_open_folder")));
    else if (a === "clear_cache" && !PHONE) out.push(cacheButton(after));
  }
  return out;
}
function cacheButton(after) {
  const b = h("button.btn.btn-sm", { type: "button" }, t("fx_cache"));
  let bytes = null;
  getJSON("/api/cache").then((c) => { bytes = c.bytes; b.textContent = t("fx_cache_size", { size: fmtBytes(bytes) }); }).catch(() => {});
  b.onclick = async () => {
    if (bytes === 0) { toast(t("fx_cache_empty")); return; }
    const size = bytes == null ? "?" : fmtBytes(bytes);
    if (!await confirmDialog({ title: t("fx_cache_title"), text: t("fx_cache_text", { size }), ok: t("fx_cache_ok"), danger: true })) return;
    b.disabled = true;
    try { const r = await postJSON("/api/cache/clear"); toast(t("fx_cache_done", { size: fmtBytes(r.freed) })); after?.(); }
    catch (e) { toast(e.message, "bad"); b.disabled = false; }
  };
  return b;
}
const hostOf = (u) => { try { return new URL(u).host; } catch { return u; } };
function fixDialog(r, after) {
  const rc = r.recipe, terminal = rc.kind === "terminal";
  let es = null, fid = null, running = false, finished = false;
  const done = () => { es?.close(); document.removeEventListener("keydown", key, true); back.remove(); };
  const key = (e) => { if (e.key === "Escape" && !running) { e.preventDefault(); done(); } };
  const con = h("pre.fx-console", { hidden: true, "aria-live": "polite" });
  const status = h("div.fx-status");
  const cancel = h("button.btn", { type: "button", onclick: () => { if (!running) done(); } }, t("cancel"));
  const go = h("button.btn.btn-primary", { type: "button" }, t(terminal ? "fx_open_terminal" : "fx_run"));
  const stop = h("button.btn.btn-danger", { type: "button", hidden: true }, t("fx_stop"));
  const show = (s) => {
    running = s.status === "running";
    stop.hidden = !running; cancel.disabled = running;
    const tone = { running: "wait", done: "ok", opened: "ok", failed: "bad", stopped: "wait" }[s.status] || "wait";
    region(status, s.status, () => h("div", { class: "result " + tone }, t("fx_" + s.status)));
    if (!running && !finished) {
      finished = true; es?.close(); cancel.textContent = t("close");
      if (s.status === "done") after?.();
    }
  };
  go.onclick = async () => {
    go.disabled = true;
    let s;
    try { s = await postJSON("/api/fixes", { check: r.id }); }
    catch (e) { go.disabled = false; status.replaceChildren(h("div.result.bad", e.message)); return; }
    fid = s.id; go.hidden = true; con.hidden = false;
    show({ status: "running" });         // the stream sends every line, then how it ended
    es = new EventSource(`/api/fixes/${encodeURIComponent(fid)}/events`);
    es.addEventListener("line", (m) => { try { con.append(JSON.parse(m.data).text + "\n"); con.scrollTop = con.scrollHeight; } catch {} });
    es.addEventListener("status", (m) => { try { show(JSON.parse(m.data)); } catch {} });
  };
  stop.onclick = async () => {
    stop.disabled = true;
    try { await postJSON(`/api/fixes/${encodeURIComponent(fid)}/stop`); } catch (e) { toast(e.message, "bad"); stop.disabled = false; }
  };
  const back = h("div.modal-back", { onclick: (e) => { if (e.target === back && !running) done(); } },
    h("div.modal.fx-modal", { role: "dialog", "aria-modal": "true", "aria-labelledby": "fx-title" },
      h("h2#fx-title", t("fx_fix_title", { name: checkName(r) })),
      h("p", plainDetail(r)),
      h("p", t(terminal ? "fx_terminal_text" : "fx_command_text")),
      h("pre.fx-cmd", rc.command),
      rc.consent ? h("p.hint", rc.consent) : null,
      rc.links?.length ? h("p.hint", t("fx_what"), " ", ...rc.links.flatMap((u, i) => [i ? " · " : "", h("a", { href: u, target: "_blank", rel: "noopener noreferrer" }, hostOf(u))])) : null,
      con, status, h("div.modal-acts", cancel, stop, go)));
  document.body.append(back);
  document.addEventListener("keydown", key, true);
  go.focus();
}

// Home: a failed check this kind of request needs puts «To start, fix this» above the field and makes the field inert
// (the server refuses such a start too); warnings do not block.
async function blockIfNotReady(hv, pick, page, form) {
  let d;
  try { d = await getJSON("/api/doctor"); } catch { return; }
  if (!page.isConnected) return;
  const ids = d.blocks?.[pick.name] || [];
  const rows = d.rows.filter((r) => r.status === "fail" && ids.includes(r.id));
  if (!rows.length) return;
  form.inert = true;
  form.classList.add("new-blocked");
  const redo = () => { if (!page.isConnected) return; hv.close?.(); hv.close = null; showNew(hv, pick.name); refreshDoctorDot(); };
  const fixRow = (r) => {
    const ctl = checkControls(r, redo);
    return h("div.fix-first-row", h("div.fix-first-text", h("b", checkName(r)), h("p", plainDetail(r))),
      h("div.fix-first-ctl", ...ctl, ctl.length ? null : h("a.btn.btn-sm", { href: "#/settings/system" }, t("fx_details"))));
  };
  const noAi = rows.find((r) => r.id === "model");
  // the speech model is not in the app (B11): on the first run it is offered right here, with its download and progress
  const speech = d.rows.filter((r) => r.id === "speech" && r.status === "warn" && r.recipe);
  const rest = rows.filter((r) => r !== noAi);
  if (!noAi) { form.before(h("div.fix-first", h("b.fix-first-title", t("fx_first")), ...rest.map(fixRow))); return; }
  // V1 (owner 22.11): no AI yet is the first run — a welcome that leads to the first clip, not an error
  page.querySelector(".new-title")?.setAttribute("hidden", "");
  const step = (n, title, text, ...ctl) => h("li.ob-step", h("span.ob-num", String(n)), h("div.ob-text", h("b", title), h("p", text), ...ctl));
  form.before(h("div.ob",
    h("h2.ob-title", t("ob_title")), h("p.ob-lead", t("ob_text")),
    h("ol.ob-steps",
      step(1, t("ob_step1"), t("ob_step1_text"), h("a.btn.btn-primary.btn-sm.ob-go", { href: "#/settings/providers" }, t("ob_btn"))),
      step(2, t("ob_step2"), t("ob_step2_text")),
      step(3, t("ob_step3"), t("ob_step3_text"))),
    rest.length ? h("div.fix-first.ob-more", h("b.fix-first-title", t("ob_other")), ...rest.map(fixRow)) : null,
    speech.length ? h("div.fix-first.ob-more", h("b.fix-first-title", t("ob_speech")), ...speech.map(fixRow)) : null));
}

// The desktop app (dmg, exe, zip) is removed the system's way: the window says where
const appRemoveKey = () => /Mac/.test(navigator.platform) ? "remove_app_mac" : "remove_app_win";
// «Remove SMTV from this computer»: a row of the «Program» group; the data only with its own switch, asked in the
// window's own dialog
function renderRemove() {
  const row = setRow(t("remove_title"), t("remove_about"), h("span.faint", "…"));
  (async () => {
    let p;
    try { p = await getJSON("/api/uninstall"); } catch (e) { row.querySelector(".set-ctl").replaceChildren(h("span.set-bad", e.message)); return; }
    const size = t("unit_gb", { n: fmt.dec(p.data_bytes / 1e9, 1) });
    const data = h("input", { type: "checkbox" });
    const go = h("button.btn.btn-sm.btn-danger", { type: "button", onclick: async () => {
      const ok = await confirmDialog({ title: t("remove_confirm"), text: data.checked ? t("remove_confirm_data", { size }) : t("remove_about"), ok: t("remove_btn_short"), danger: true });
      if (!ok) return;
      go.disabled = true; go.textContent = t("removing");   // the browser clears this site's data first: a few seconds
      try {
        const r = await postJSON("/api/uninstall", { confirm: "remove", data: data.checked });
        try { localStorage.clear(); } catch {}
        document.getElementById("view").replaceChildren(h("div.card.empty", h("div.result.ok", t("removed")),
          r.program === "manual" ? h("p.muted", t("remove_manual", { cmd: r.program_command })) : r.program === "app" ? h("p.muted", t(appRemoveKey())) : null));
      } catch (e) { toast(e.message, "bad"); go.disabled = false; go.textContent = t("remove_btn_short"); }
    } }, t("remove_btn_short"));
    row.querySelector(".set-text").append(h("label.check-line", data, h("span", t("remove_data", { size, folder: p.data_folder }))),
      ...(p.program === "manual" ? [h("p.hint", t("remove_manual", { cmd: p.program_command }))] : p.program === "app" ? [h("p.hint", t(appRemoveKey()))] : []));   // append(null) writes «null»
    row.querySelector(".set-ctl").replaceChildren(go);
  })();
  return row;
}

// --- «Report a problem» (stage 17): the window shows every file of the archive before it is saved; keys are already cut
// out, links and file names only with the checkbox. Saving shows the archive in Finder or Explorer and opens a new GitHub
// issue with the title and summary filled in; the person drags the archive in. Nothing is sent by SMTV.
// what each file of the archive is, in the window's language (the server's own words are English)
function fileAbout(f) {
  const n = f.name, k = n === "summary.json" ? "rf_summary" : n === "doctor.txt" ? "rf_doctor" : n === "settings.json" ? "rf_settings"
    : n.endsWith("/events.jsonl") ? "rf_events" : n.endsWith("/run.log") ? "rf_runlog" : n.startsWith("logs/") ? "rf_log" : n.startsWith("crashes/") ? "rf_crash" : null;
  return k ? t(k) : f.about;
}
const kb = (n) => t("unit_kb", { n: fmt.dec(n / 1024, 1) });
const revealLabel = () => /Mac/.test(navigator.platform) ? t("report_reveal_mac") : /Win/.test(navigator.platform) ? t("report_reveal_win") : t("report_reveal");

export function reportDialog({ tool = null, job = null } = {}) {
  let rep = null, seq = 0;
  const done = () => { document.removeEventListener("keydown", key, true); back.remove(); };
  const key = (e) => { if (e.key === "Escape") { e.preventDefault(); done(); } };
  const names = h("input", { type: "checkbox" });
  const files = h("div.report-files", h("p.muted", t("report_loading")));
  const about = h("p.report-job", { hidden: true });
  const cancel = h("button.btn", { type: "button", onclick: done }, t("cancel"));
  const save = h("button.btn.btn-primary", { type: "button", disabled: true }, t("report_save"));
  const acts = h("div.modal-acts", cancel, save);
  const body = h("div.report-body", about, h("h3", t("report_files")), files,
    h("label.check-line", names, h("span", t("report_names"))), h("p.hint", t("report_privacy")));
  const modal = h("div.modal.modal-wide", { role: "dialog", "aria-modal": "true", "aria-labelledby": "report-title" }, h("h2#report-title", t("report_title")), body, acts);
  const back = h("div.modal-back", { onclick: (e) => { if (e.target === back) done(); } }, modal);
  const load = async () => {
    const mine = ++seq; save.disabled = true;
    if (!rep) files.replaceChildren(h("p.muted", t("report_loading")));
    const q = new URLSearchParams({ names: names.checked ? "1" : "0", ...(tool && job ? { tool, job } : {}) });
    try { rep = await getJSON("/api/report?" + q); } catch (e) { if (mine === seq) files.replaceChildren(h("div.result.bad", e.message)); return; }
    if (mine !== seq) return;
    about.hidden = !rep.job; about.textContent = rep.job ? t("report_about_job", { job: rep.job.id, error: rep.job.error || t("s_" + rep.job.status) }) : "";
    // by file (V6): «with names» changes only the files whose text changed; an opened file stays open
    keyed(files, rep.files, { key: (f) => f.name, sig: (f) => sig(f.size, f.text),
      create: (f) => h("details.report-file", h("summary", h("code", f.name), h("span.faint", fileAbout(f)), h("span.faint.report-size", kb(f.size))), h("pre", f.text)) });
    save.disabled = false;
  };
  names.onchange = load;
  save.onclick = async () => {
    save.disabled = true;
    let r;
    try { r = await postJSON("/api/report", { id: rep.id }); } catch (e) { toast(e.message, "bad"); save.disabled = false; return; }
    const file = r.path.split(/[\\/]/).pop();
    const reveal = r.download ? h("a.btn.btn-sm", { href: r.download, download: file }, t("report_download"))
      : h("button.btn.btn-sm", { type: "button", onclick: () => postJSON("/api/report/reveal", { id: rep.id }).catch((e) => toast(e.message, "bad")) }, revealLabel());
    const again = h("button.btn.btn-sm", { type: "button", onclick: () => postJSON("/api/report", { id: rep.id }).catch((e) => toast(e.message, "bad")) }, t("report_github"));
    const link = h("div.fix", h("code", r.url), (() => { const b = h("button.btn.btn-sm", { type: "button" }, t("copy")); b.onclick = () => copy(r.url, b); return b; })());
    body.replaceChildren(h("div.result.ok", icon(ICONS.check), h("div", t("report_saved", { file }))), h("p", t(r.browser ? "report_next" : "report_next_manual")),
      h("div.report-again", reveal, again), ...[r.browser ? h("p.hint", t("report_url")) : null, link].filter(Boolean));   // append(null) writes «null»
    acts.replaceChildren(h("button.btn.btn-primary", { type: "button", onclick: done }, t("report_done")));
  };
  document.body.append(back);
  document.addEventListener("keydown", key, true);
  cancel.focus();
  load();
}

// After an unexpected error (a crash file appeared) the window offers to report it, once per new crash.
let crashNote = null;
function watchCrashes() {
  if (PHONE) return;
  effect(() => {
    const c = live.crash.value;
    if (!c?.unseen) { crashNote?.remove(); crashNote = null; return; }   // reported or dismissed, here or in another window
    if (crashNote?.dataset.newest === c.newest) return;
    crashNote?.remove();
    const seen = () => { crashNote?.remove(); crashNote = null; postJSON("/api/crashes/seen").catch(() => {}); };
    crashNote = h("div.toast.crash-note", { role: "alert", "data-newest": c.newest },
      h("b", t("crash_title")), h("p", t("crash_text")),
      h("div.crash-acts", h("button.btn.btn-sm", { type: "button", onclick: seen }, t("crash_later")),
        h("button.btn.btn-sm.btn-primary", { type: "button", onclick: () => { seen(); reportDialog({}); } }, t("report_btn"))));
    document.getElementById("toasts").append(crashNote);
  });
}

// The window's own errors (its JavaScript) become crash files too: a few per page, never an error from a lost connection
// or an answer of the server (those are said where they happen).
let windowErrors = 0;
function sendWindowError(where, err) {
  if (windowErrors >= 3 || !err || err.code) return;
  windowErrors++;
  const message = String(err.message || err).slice(0, 2000), stack = String(err.stack || "").slice(0, 8000);
  try { fetch("/api/crash", { method: "POST", headers: { "Content-Type": "application/json", "X-SMTV-Token": TOKEN }, body: JSON.stringify({ where, message, stack }) }).catch(() => {}); } catch {}
}
window.addEventListener("error", (e) => sendWindowError("window " + (e.filename || "").split("/").pop() + ":" + (e.lineno || ""), e.error || e.message));
window.addEventListener("unhandledrejection", (e) => sendWindowError("window promise", e.reason));

function setDoctorDot(ready) { const dot = document.getElementById("settings-dot"); if (dot) attr(dot, "hidden", ready); }
async function refreshDoctorDot() {
  try { const d = await getJSON("/api/doctor"); setDoctorDot(d.ready); } catch {}
}

// --- what runs now: header line and window title. Read from /api/activity; in a browser these requests also tell the
// server a page is open (with no page and no job it stops by itself after a few minutes).

function showActivity(a) {
  const el = document.getElementById("activity");
  const n = a?.running || 0;
  el.classList.toggle("busy", n > 0);
  const parts = n ? [t("act_jobs", { n })] : [t("act_idle")];
  if (n && a.clips_total) parts.push(t("act_clips", { a: a.clips_ready, b: a.clips_total }));
  else if (n === 1 && a.jobs[0]?.stage) parts.push(t("stage_" + a.jobs[0].stage) === "stage_" + a.jobs[0].stage ? a.jobs[0].stage : t("stage_" + a.jobs[0].stage));
  if (n && a.eta_s != null) parts.push(t("act_left", { d: fmt.dur(a.eta_s) }));
  if (a?.queued) parts.push(t("act_queued", { n: a.queued }));
  text(el, parts.join(" · "));
  const title = n ? t("title_jobs", { n }) : "SMTV";
  if (document.title !== title) document.title = title;
}

function watchActivity() {
  effect(() => {
    const link = live.link.value, a = live.activity.value;
    if (link !== "lost") { showActivity(a); return; }
    if (live.update.peek()?.leaving) return;          // quitting for an update: the overlay says what happens
    const el = document.getElementById("activity"); el.classList.remove("busy"); text(el, t("act_lost"));
  });
}

// --- SMTV's own window: on macOS the page's header holds the window's buttons and drags the window ----------------
// The server marks the page (<html class="shell shell-mac">) from the first frame; a press on the header's empty space
// asks the window to be dragged (a double press zooms it), as macOS title bars do.
// SMTV's own window: on macOS its message handler, on Windows pywebview's bridge (window.pywebview.api, from V9)
function windowMessage(what) {
  try {
    if (window.webkit?.messageHandlers?.smtvWindow) window.webkit.messageHandlers.smtvWindow.postMessage(what);
    else window.pywebview?.api?.message?.(what)?.catch?.(() => {});
  } catch {}
}

async function quitSmtv() {
  const running = live.activity.value?.running || 0;
  if (running && !confirm(t("quit_jobs", { n: running }))) return;
  try {
    await postJSON("/api/quit");
    document.getElementById("view").replaceChildren(h("div.card.empty", h("div.result.ok", t("quitting"))));
  } catch (e) { toast(e.message, "bad"); }
}


// --- Settings → About (stage 18): the version and its changes, the core every plugin runs on, what is coming, support
// The support page's address comes from the server (smtv/about.py, SUPPORT_URL); its link is at the bottom of Settings.
const CORE_GIVES = ["ab_core_asr", "ab_core_render", "ab_core_captions", "ab_core_sound", "ab_core_blur", "ab_core_agents", "ab_core_models", "ab_core_events", "ab_core_doctor"];
async function renderAbout(body, rest = []) {
  let a;
  try { a = await getJSON("/api/about"); } catch (e) { body.replaceChildren(h("div.result.bad", e.message)); return; }
  const out = (href, label) => h("a.btn.btn-sm", { href, target: "_blank", rel: "noopener noreferrer" }, label);
  const list = (items) => h("ul.about-list", items.map((x) => h("li", x)));
  const soonHref = (x) => x.kind === "plugin" ? `#/plugins/${encodeURIComponent(x.id)}` : x.kind === "page" ? `#/${x.id}` : null;
  const soonRow = (x) => { const href = soonHref(x);
    const inner = [h("span.about-ico", icon(soonIcon(x))), h("span.about-soon-text", h("b", txt(x.title)), h("span", txt(x.summary)))];
    return href ? h("a.set-row.about-soon", { href }, ...inner, icon('<path d="m9 6 6 6-6 6"/>', "about-go")) : h("div.set-row.about-soon", ...inner); };
  body.replaceChildren(
    setGroup(null,
      setRow(`SMTV ${a.version}`, t("ab_sub", { license: a.license }), out(a.repo, "GitHub")),
      PHONE ? null : setRow(t("report_btn"), t("report_about"), h("button.btn.btn-sm", { type: "button", onclick: () => reportDialog({}) }, t("report_btn_short")))),
    setGroup(t("ab_changes"), a.changes.length
      ? a.changes.map((c) => h("div.set-row.about-ver", h("b", c.version), list(c.notes)))
      : setRow(t("ab_no_changes"), null)),
    h("div.about-anchor#about-core", setGroup(t("ab_core_title"),
      setRow(`SMTV Core ${a.core.version}`, t("ab_core_builtin")),
      h("div.set-row.about-block", h("b", t("ab_core_gives")), list(CORE_GIVES.map((k) => t(k)))),
      h("div.set-row.about-block", h("b", t("ab_core_plugins")),
        a.core.plugins.length ? list(a.core.plugins.map((x) => `${txt(x.title)} ${x.version}`)) : h("p.faint", t("ab_core_none"))))),
    h("section.set-group.about-anchor#about-soon", h("h2.set-group-title", t("ab_soon")), h("p.about-lead", t("ab_soon_sub")),
      h("div.set-card", a.soon.map(soonRow))));
  const at = { core: "about-core", soon: "about-soon" }[rest[0]];
  if (at) requestAnimationFrame(() => document.getElementById(at)?.scrollIntoView({ block: "start" }));
}


// --- the frame (stage 7) ------------------------------------------------------------------------------------------
Object.assign(ICONS, {
  home: '<path d="M4 10.5 12 4l8 6.5V19a1.5 1.5 0 0 1-1.5 1.5H15v-6H9v6H5.5A1.5 1.5 0 0 1 4 19z"/>',
  calendar: '<rect x="3.5" y="5" width="17" height="15.5" rx="3"/><path d="M8 3v4M16 3v4M3.5 10h17M8 14h2M14 14h2M8 17h2"/>',
  puzzle: '<path d="M9 4.5a2 2 0 1 1 4 0V6h3.5A1.5 1.5 0 0 1 18 7.5V11h1.5a2 2 0 1 1 0 4H18v3.5a1.5 1.5 0 0 1-1.5 1.5H13v-1.5a2 2 0 1 0-4 0V20H5.5A1.5 1.5 0 0 1 4 18.5V15h1.5a2 2 0 1 0 0-4H4V7.5A1.5 1.5 0 0 1 5.5 6H9z"/>',
  gear: '<path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1Z"/>',
  megaphone: '<path d="M4 10v4a1 1 0 0 0 1 1h2l6 4V5L7 9H5a1 1 0 0 0-1 1Z"/><path d="M17 9a4 4 0 0 1 0 6M19.5 6.5a7.5 7.5 0 0 1 0 11"/>',
  phone: '<rect x="7" y="2.5" width="10" height="19" rx="2.5"/><path d="M11 18.5h2"/>',
  plus: '<path d="M12 5v14M5 12h14"/>', spark: '<path d="M12 3.5l1.9 5.2 5.1 1.9-5.1 1.9L12 17.7l-1.9-5.2-5.1-1.9 5.1-1.9z"/>',
  pulse: '<path d="M3 12h4l2.5-6 5 12 2.5-6h4"/>', chevron: '<path d="m6 9 6 6 6-6"/>',
  pin: '<path d="M9 4h6l-1 5 3 3v2H7v-2l3-3zM12 14v6"/>', pinOff: '<path d="M9 4h6l-1 5 3 3v2H7v-2l3-3zM12 14v6M4 4l16 16"/>',
  trash: '<path d="M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-12M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>', left: '<path d="m15 18-6-6 6-6"/>', quit: '<path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3M10 16l-4-4 4-4M6 12h10"/>',
  live: '<circle cx="12" cy="12" r="2.5"/><path d="M7.8 16.2a6 6 0 0 1 0-8.4M16.2 7.8a6 6 0 0 1 0 8.4M5 19a10 10 0 0 1 0-14M19 5a10 10 0 0 1 0 14"/>',
  box: '<path d="M4 7.5 12 3.5l8 4v9l-8 4-8-4z"/><path d="M4 7.5l8 4 8-4M12 11.5v9"/>',
});
Object.assign(ICONS, {
  code: '<path d="m8 8-4 4 4 4M16 8l4 4-4 4M13.5 5l-3 14"/>',
  upload: '<path d="M12 15V4M7.5 8.5 12 4l4.5 4.5M5 14v4.5A1.5 1.5 0 0 0 6.5 20h11a1.5 1.5 0 0 0 1.5-1.5V14"/>',
  hash: '<path d="M10 4 8 20M16 4l-2 16M4.5 9h15M4 15h15"/>',
  music: '<path d="M9 18V6l10-2v12"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="16.5" cy="16" r="2.5"/>',
  cloud: '<path d="M7 18.5h10a4 4 0 0 0 .6-7.95A6 6 0 0 0 6.1 9.6 4.5 4.5 0 0 0 7 18.5Z"/>',
  heart: '<path d="M12 20s-7.5-4.4-7.5-10A4.3 4.3 0 0 1 12 7.4 4.3 4.3 0 0 1 19.5 10c0 5.6-7.5 10-7.5 10Z"/>',
  info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11v5.5M12 7.8v.2"/>',
});
// What is coming (stage 18): one list in the package, soon.json, served as state.soon — the «soon» plugin cards and their
// pages, the «soon» pages of the rail, the «Add a plugin» window and Settings → About read only it. Texts are {en, ru}.
const soonOf = (id) => (state?.soon || []).find((x) => x.id === id) || null;
const soonIcon = (item) => ({ live: ICONS.live, code: ICONS.code, upload: ICONS.upload, hash: ICONS.hash, music: ICONS.music, plus: ICONS.plus,
  spark: ICONS.spark, cloud: ICONS.cloud, clock: RAIL.clock.o, promo: RAIL.promo.o, campaigns: RAIL.campaigns.o })[item?.icon] || ICONS.box;
// an announced thing's short text: the lead, a list, the notes; no dates, no promises
function soonBody(item) {
  if (!item) return null;
  return [
    item.lead ? h("p.plug-about", txt(item.lead)) : null,
    item.points ? h("ul.plug-points", item.points.map((x) => h("li", txt(x)))) : null,
    ...(item.notes || []).map((x) => h("p.plug-note", txt(x))),
    item.note ? h("p.plug-note", txt(item.note)) : null,
  ];
}
// The rail's icons: an outline (o) and a filled one (f) for the open place. Cut-outs in a filled icon are drawn in the
// rail's own colour (--rail-cut), so they read as holes.
const RAIL = {
  home: { o: ICONS.home, f: '<path d="M4 10.5 12 4l8 6.5V19a1.5 1.5 0 0 1-1.5 1.5H15v-6H9v6H5.5A1.5 1.5 0 0 1 4 19z" fill="currentColor"/>' },
  clock: { o: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    f: '<circle cx="12" cy="12" r="8.5" fill="currentColor"/><path d="M12 7.5V12l3 2" stroke="var(--rail-cut)" stroke-width="2"/>' },
  plug: { o: '<path d="M9 3v4.5M15 3v4.5M6.5 7.5h11V11a5.5 5.5 0 0 1-11 0zM12 16.5V21"/>',
    f: '<path d="M9 3v4.5M15 3v4.5M12 16.5V21"/><path d="M6.5 7.5h11V11a5.5 5.5 0 0 1-11 0z" fill="currentColor"/>' },
  // a price tag (owner, 21.11: a megaphone read as a sound switch)
  promo: { o: '<path d="M3.5 12.6V5A1.5 1.5 0 0 1 5 3.5h7.6a1.5 1.5 0 0 1 1 .44l6.5 6.5a1.5 1.5 0 0 1 0 2.12l-7.6 7.6a1.5 1.5 0 0 1-2.12 0l-6.5-6.5a1.5 1.5 0 0 1-.44-1Z"/><circle cx="8.5" cy="8.5" r="1.5"/>',
    f: '<path d="M3.5 12.6V5A1.5 1.5 0 0 1 5 3.5h7.6a1.5 1.5 0 0 1 1 .44l6.5 6.5a1.5 1.5 0 0 1 0 2.12l-7.6 7.6a1.5 1.5 0 0 1-2.12 0l-6.5-6.5a1.5 1.5 0 0 1-.44-1Z" fill="currentColor"/><circle cx="8.5" cy="8.5" r="1.5" fill="var(--rail-cut)" stroke="var(--rail-cut)"/>' },
  // Campaigns: a briefcase (a job to take)
  campaigns: { o: '<rect x="3.5" y="7.5" width="17" height="12" rx="2.5"/><path d="M9 7.5V6a1.5 1.5 0 0 1 1.5-1.5h3A1.5 1.5 0 0 1 15 6v1.5M3.5 12.5h17"/>',
    f: '<rect x="3.5" y="7.5" width="17" height="12" rx="2.5" fill="currentColor"/><path d="M9 7.5V6a1.5 1.5 0 0 1 1.5-1.5h3A1.5 1.5 0 0 1 15 6v1.5"/><path d="M3.5 12.5h17" stroke="var(--rail-cut)"/>' },
  phone: { o: ICONS.phone, f: '<rect x="7" y="2.5" width="10" height="19" rx="2.5" fill="currentColor"/><path d="M11 18.5h2" stroke="var(--rail-cut)"/>' },
  gear: { o: ICONS.gear, f: '<path fill="currentColor" fill-rule="evenodd" d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1ZM12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"/>' },
};

// a tool's text: one string, or {"en": …, "ru": …}
export const txt = (v) => (v && typeof v === "object" ? v[lang] ?? v.en ?? Object.values(v)[0] ?? "" : v || "");
const toolIcon = (tool) => tool?.page?.icon || ICONS.box;
fmt.compact = (n) => new Intl.NumberFormat(lang, { notation: "compact", maximumFractionDigits: 1 }).format(n || 0);

// --- tools' modules: loaded once at start; a module that fails to load breaks only its own places --------------------
const modules = new Map();   // name -> {mod} | {error}
async function loadModules() {
  await Promise.all(state.tools.filter((x) => x.page).map(async (tool) => {
    try {
      const mod = await import(`/tools/${encodeURIComponent(tool.name)}/section.js`);
      const link = h("link", { rel: "stylesheet", href: `/tools/${encodeURIComponent(tool.name)}/section.css` });
      link.onerror = () => link.remove();
      document.head.append(link);
      modules.set(tool.name, { mod });
      extra.set(tool.name, await loadWords(`/tools/${encodeURIComponent(tool.name)}`));   // its words, before any of its views opens
    } catch (e) {
      console.error(e);
      modules.set(tool.name, { error: String(e.message || e) });
    }
  }));
}

const api = {
  t, h, icon, ICONS, fmt, txt, text, attr, keyed, blocks, region, sig, signal, computed, effect, batch, bindText, bindAttr, getJSON, postJSON, upload, stream, toast, openSettings, copy, live,
  lang: () => lang,
  route: () => location.hash.replace(/^#\/?/, "").split("/").filter(Boolean).map(decodeURIComponent),
  go: (...parts) => { location.hash = "#/" + parts.map(encodeURIComponent).join("/"); },
  // a tool calls these after it started a job: the request opens and the list on Home shows it at once
  openRequest: (tool, job) => { api.go("home", tool, job); },
  refreshRequests: () => loadRequests(),
  setTitle: (title) => setTopTitle(title),
  confirm: (opts) => confirmDialog(opts),     // the window's own modal question; resolves true for the main button   // the open request's name, small, in the window's top bar
  // «Report a problem» about one request (stage 17): a tool puts this button where it shows a failure; null on a phone
  reportButton: (tool, job) => PHONE ? null : h("button.btn.btn-sm.report-btn", { type: "button", onclick: () => reportDialog({ tool, job }) }, t("report_btn")),
};
const toolApi = (tool) => {
  if (!extra.has(tool.name)) extra.set(tool.name, { en: {} });
  const own = extra.get(tool.name);
  return { ...api, tool, t: (key, vars = {}) => t(key, vars, own) };
};

// --- the top bar: the open request's name after a short divider, nothing elsewhere (owner, 20.11)
function setTopTitle(name) {
  const el = document.getElementById("top-title");
  if (!el.firstElementChild) el.append(h("span"));
  text(el.firstElementChild, name || ""); attr(el, "title", name || ""); attr(el, "hidden", !name);
}

// --- the rail
// Strict minimalism (owner, 20.11): icons only, no captions, no «soon» marks; the open one is white and filled.
function railItem({ id, href, label, ico, onclick, dot }) {
  const kids = [h("span.ico", icon(ico.o, "o"), icon(ico.f, "f")), dot || null];
  const attrs = { class: "rail-item", "data-id": id, title: label, "aria-label": label };
  return onclick ? h("button", { ...attrs, type: "button", onclick }, ...kids) : h("a", { ...attrs, href }, ...kids);
}
function drawRail() {
  const navTools = state.tools.filter((x) => x.page?.nav && !modules.get(x.name)?.error && modules.get(x.name)?.mod?.mountNav);
  document.getElementById("rail-main").replaceChildren(
    railItem({ id: "home", href: "#/home", label: t("nav_home"), ico: RAIL.home }),
    railItem({ id: "scheduled", href: "#/scheduled", label: txt(soonOf("scheduled")?.title), ico: RAIL.clock }),
    railItem({ id: "promotion", href: "#/promotion", label: txt(soonOf("promotion")?.title), ico: RAIL.promo }),
    railItem({ id: "campaigns", href: "#/campaigns", label: txt(soonOf("campaigns")?.title), ico: RAIL.campaigns }),
    railItem({ id: "plugins", href: "#/plugins", label: t("nav_plugins"), ico: RAIL.plug }),
    ...navTools.map((x) => { const d = x.page.nav.icon || toolIcon(x);
      return railItem({ id: "x:" + x.name, href: `#/x/${encodeURIComponent(x.name)}/${x.page.nav.id}`, label: txt(x.page.nav.title), ico: { o: d, f: d } }); }));
  const dot = h("span.dot-bad#settings-dot", { hidden: true });
  document.getElementById("rail-foot").replaceChildren(...[
    PHONE ? null : railItem({ id: "phone", href: "#/phone", label: t("nav_phone"), ico: RAIL.phone }),
    (() => { const b = h("button.rail-item.rail-me", { type: "button", "data-id": "profile", title: t("nav_profile"), "aria-label": t("nav_profile"), "aria-haspopup": "menu" },
      h("span.avatar", "SM"), dot, h("span.dot-new#update-dot", { hidden: !live.update.value?.available })); b.onclick = () => openProfile(b); return b; })()].filter(Boolean));
}
function markRail(id) {
  for (const el of document.querySelectorAll(".rail-item[data-id]")) el.setAttribute("aria-current", el.dataset.id === id ? "page" : "false");
}


// --- profile menu (owner, 21.11, like Claude's): who — the StreamMoment account or this computer —, «Sign in» or the
// account, Settings, and «Log out» of the account when signed in (quitting SMTV is in Settings → System). Small, and it opens upwards from the button: it is pinned by its bottom edge, so text that
// arrives later (the account's name) grows it up, never below the window. Tokens are still counted (/api/usage) but
// not shown for now.
let menuEl = null;
function closeMenu() { menuEl?.remove(); menuEl = null; }
function openProfile(anchor) {
  if (menuEl) { closeMenu(); return; }
  const who = h("b", t("profile_local")), whoSub = h("small", t(PHONE ? "profile_sub_phone" : "profile_sub", { v: state.version }));
  const avatar = h("span.avatar", "SM");
  const acct = h("div.menu-account"), signOut = h("div.menu-account");
  const signIn = h("button.menu-btn", { type: "button", onclick: async () => {
    closeMenu();
    try { await postJSON("/api/account/login", { mode: "browser" }); } catch (e) { toast(e.message, "bad"); }
    location.hash = "#/settings/account";
  } }, icon(ICONS.user), t("sm_login"));
  if (!PHONE) getJSON("/api/account").then((a) => {
    if (!menuEl) return;
    if (!a.signed_in) { acct.replaceChildren(signIn); return; }
    const name = a.account?.name || t("sm_account");
    who.textContent = name; whoSub.textContent = t("sm_via_" + a.account?.provider);
    avatar.textContent = name.split(/\s+/).map((w) => w[0] || "").join("").slice(0, 2).toUpperCase() || "SM";
    acct.replaceChildren(h("a.menu-btn", { href: "#/settings/account", onclick: () => closeMenu() }, icon(ICONS.user), t("sm_account_short")));
    // «Log out» is the account's, not the program's (owner, 21.11): shown only when signed in; quitting SMTV is in Settings → System
    signOut.replaceChildren(h("hr"), h("button.menu-btn", { type: "button", onclick: async () => {
      closeMenu();
      if (!await confirmDialog({ title: t("sm_logout_title"), text: t("sm_logout_text"), ok: t("sm_logout_short"), cancel: t("ag_cancel"), danger: true })) return;
      try { await postJSON("/api/account/logout", {}); toast(t("sm_logged_out"), "ok"); } catch (e) { toast(e.message, "bad"); }
    } }, icon(ICONS.quit), t("sm_logout_short")));
  }).catch(() => {});
  menuEl = h("div.menu", { role: "menu" },
    h("div.menu-head", avatar, h("div", who, whoSub)),
    h("hr"),
    PHONE ? null : acct,
    live.update.value?.available ? h("a.menu-btn.menu-new", { href: "#/plugins", onclick: () => closeMenu() }, icon(ICONS.spark), t("upd_available", { v: live.update.value.available.version })) : null,
    h("a.menu-btn", { href: "#/settings", onclick: () => closeMenu() }, icon(ICONS.gear), t("settings"), h("span.dot-bad.menu-dot", { hidden: document.getElementById("settings-dot")?.hidden ?? true })),
    PHONE ? null : signOut);
  document.body.append(menuEl);
  const r = anchor.getBoundingClientRect(), m = menuEl.getBoundingClientRect();
  const phone = window.innerWidth <= 640;
  menuEl.style.left = phone ? `${Math.max(8, window.innerWidth - m.width - 8)}px` : `${r.right + 8}px`;
  // the bottom edge stays where it is put: on a phone above the bottom bar, else level with the button's bottom
  menuEl.style.bottom = phone ? `${Math.max(8, window.innerHeight - r.top + 8)}px` : `${Math.max(8, window.innerHeight - r.bottom)}px`;
  setTimeout(() => document.addEventListener("mousedown", function away(e) {
    if (!menuEl || menuEl.contains(e.target)) return; closeMenu(); document.removeEventListener("mousedown", away);
  }), 0);
}

// --- the views: each is mounted into #view and closed when another one opens
let viewClose = null;
// The side list's width: drag its right edge (owner, 20.11). Kept between starts; the top bar's request name follows it.
const LIST_W = { min: 180, max: 420 };
function setListWidth(px) {
  const w = Math.round(Math.min(LIST_W.max, Math.max(LIST_W.min, px)));
  document.documentElement.style.setProperty("--list-w", w + "px");
  return w;
}
{ const saved = Number(store("smtv.listWidth")); if (saved) setListWidth(saved); }
function resizer() {
  const bar = h("div.side-resize", { role: "separator", "aria-orientation": "vertical", title: "" });
  bar.addEventListener("pointerdown", (e) => {
    if (e.button !== 0) return;
    e.preventDefault();
    const side = bar.parentElement, left = side.getBoundingClientRect().left;
    try { bar.setPointerCapture(e.pointerId); } catch {}   // keeps the drag when the pointer leaves the thin edge
    bar.classList.add("dragging"); document.documentElement.classList.add("resizing");
    let w = side.getBoundingClientRect().width;
    const move = (ev) => { w = setListWidth(ev.clientX - left); };
    const up = () => {
      bar.removeEventListener("pointermove", move); bar.removeEventListener("pointerup", up); bar.removeEventListener("pointercancel", up);
      bar.classList.remove("dragging"); document.documentElement.classList.remove("resizing"); store("smtv.listWidth", String(w));
    };
    bar.addEventListener("pointermove", move); bar.addEventListener("pointerup", up); bar.addEventListener("pointercancel", up);
  });
  bar.addEventListener("dblclick", () => { document.documentElement.style.removeProperty("--list-w"); try { localStorage.removeItem("smtv.listWidth"); } catch {} });
  return bar;
}

function solo(content) { const sc = screen(); sc.main.append(content); return sc.node; }
function mountView(node, close) { viewClose?.(); viewClose = close || null; document.getElementById("view").replaceChildren(node); }

// One page component, two formats (owner, 20.11). With a side list — Home (requests), Settings (sections): the list
// on the left, the open item on the right; on a narrow window one of them at a time (class `open` shows the item).
// Without — Plugins, Scheduled, Phone, a plugin's page: the content alone, centred. Every page is built with it.
function screen({ side = false } = {}) {
  const main = h("div.screen-main.scroll");
  if (!side) return { node: h("div.screen.solo", main), main };
  const sideHead = h("div.side-head"), sideList = h("div.side-list");
  return { node: h("div.screen.split", h("aside.screen-side", sideHead, sideList, resizer()), main), sideHead, sideList, main };
}

// Home stays mounted while you move between requests: the list keeps its scroll, only the right side changes
let home = null;
function homeView() {
  if (home) return home;
  const sc = screen({ side: true });
  // «New request» is a row like the requests below it, as «New chat» in ChatGPT and Codex
  sc.sideHead.append(h("a.side-item.side-new", { href: "#/home" }, h("span.side-ico", icon(ICONS.plus)), h("span.side-text", h("b", t("new_request")))));
  home = { node: sc.node, list: sc.sideList, work: sc.main, open: null, close: null };
  return home;
}

let requests = [];
// The list follows its signals (V6): the requests, the pins, the folded groups, the open request; while a row is
// dragged it holds still (the stream keeps changing it).
const homeOn = signal(false), openReq = signal(null), dragging = signal(null);
// a tool that just started a job asks for the list at once (the stream brings it within a second anyway)
let requestsToldAt = 0;
async function loadRequests() {
  try { live.jobs.value = (await getJSON("/api/jobs")).sort(byNewest); }
  catch (e) {   // said once a minute at most: the window's stream brings the list as soon as SMTV answers again (C14)
    if (Date.now() - requestsToldAt > 60000) { requestsToldAt = Date.now(); toast(t("requests_load_failed", { e: e.message }), "bad"); }
  }
}
function dayGroup(ts) {
  const now = new Date(), start = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime() / 1000;
  if (ts >= start) return "g_today";
  if (ts >= start - 86400) return "g_yesterday";
  if (ts >= start - 6 * 86400) return "g_week";
  return "g_older";
}
// What a request's dot says (owner, 20.11): white — something new (running, or changed since it was last opened),
// red — failed, yellow — paused (cancelled or stopped). Done and already seen: no dot.
let seen = null;
function loadSeen() {
  try { seen = JSON.parse(store("smtv.seen") || "null"); } catch { seen = null; }
  if (!seen) { seen = {}; for (const j of requests) seen[j.tool + "/" + j.id] = j.updated; saveSeen(); }   // what was there before: seen
}
function saveSeen() { try { localStorage.setItem("smtv.seen", JSON.stringify(seen)); } catch {} }
function markSeen(tool, id) {
  const j = requests.find((r) => r.tool === tool && r.id === id);
  if (!j || !seen || seen[tool + "/" + id] === j.updated) return;
  seen[tool + "/" + id] = j.updated; saveSeen();
}
function dotOf(j) {
  if (j.status === "failed") return "bad";
  if (j.status === "cancelled" || j.status === "unfinished") return "paused";
  if (j.status === "running") return "new live";
  if (j.status === "queued") return null;
  return seen && (seen[j.tool + "/" + j.id] ?? 0) < j.updated ? "new" : null;
}
// Pinned requests (owner, 20.11): drag a request up into «Pinned» to keep it on top; drag it back down to unpin. Inside
// «Pinned» the order is the list's own (newest first), never a hand-made one. Kept in this window's storage.
const pins = signal(new Set());
try { pins.value = new Set(JSON.parse(store("smtv.pinned") || "[]")); } catch {}
function savePinned() { try { localStorage.setItem("smtv.pinned", JSON.stringify([...pins.peek()])); } catch {} }

// A request's row is built once and then follows its request (V6): its text, mark and buttons change in place, its
// picture is loaded once. The handlers read the request from the row, never from the moment it was built.
function requestRow(key) {
  const row = h("a.side-item.req", { draggable: "false", "data-key": key },
    h("span.side-ico"), h("span.side-text", h("b")), h("span.req-end"));
  row.addEventListener("pointerdown", (e) => pressRow(e, row, key));
  row.addEventListener("click", (e) => { if (dragged) { e.preventDefault(); dragged = false; } });   // a drag is not a click
  return row;
}
function updateRow(row, j, known, pinned, opened) {
  const key = j.tool + "/" + j.id;
  row.__job = j;
  const open = opened && opened[0] === j.tool && opened[1] === j.id;
  attr(row, "href", `#/home/${encodeURIComponent(j.tool)}/${encodeURIComponent(j.id)}`);
  attr(row, "aria-current", open ? "page" : "false");
  attr(row, "title", [j.title || j.id, j.channel, t("s_" + j.status)].filter(Boolean).join(" · "));
  const [ico, name, end] = row.children;
  region(ico, sig(j.avatar, j.tool), () => j.avatar
    ? h("img.side-avatar", { src: `/api/jobs/${encodeURIComponent(j.tool)}/${encodeURIComponent(j.id)}/files/${j.avatar}`, alt: "", loading: "lazy", draggable: "false" })
    : icon(toolIcon(known.get(j.tool))));
  text(name.firstChild, j.title || j.id);
  const dot = dotOf(j), place = j.queue && j.queue.waiting > 1 ? j.queue.position : null;
  region(end, sig(dot, place, pinned.has(key), j.status === "queued"), () => [
    dot ? h("span", { class: "req-dot " + dot }) : null,
    // a waiting request: its place, when more than one waits (owner, 20.11)
    place != null ? h("span.req-place", { "aria-label": t("s_queued") + " " + place }, String(place)) : null,
    h("span.req-acts",   // on hover: pin or unpin, take out of the queue, delete
      rowAction(pinned.has(key) ? ICONS.pinOff : ICONS.pin, t(pinned.has(key) ? "unpin" : "pin"), () => togglePin(key)),
      j.status === "queued" ? rowAction(ICONS.x, t("unqueue"), () => unqueue(row.__job)) : null,
      rowAction(ICONS.trash, t("delete"), () => deleteRequest(row.__job)))]);
}
function rowAction(ico, label, fn) {
  const b = h("button.req-act", { type: "button", title: label, "aria-label": label, draggable: "false" }, icon(ico));
  b.addEventListener("click", (e) => { e.preventDefault(); e.stopPropagation(); fn(); });
  return b;
}
function togglePin(key) { if (pins.peek().has(key)) { pins.peek().delete(key); savePinned(); pins.touch(); } else placePin(key, 0); }   // the pin button puts it on top

// A waiting request leaves the queue (it stays in the list, paused; «Continue» puts it back at the end).
export async function unqueue(j) {
  try { await postJSON(`/api/jobs/${encodeURIComponent(j.tool)}/${encodeURIComponent(j.id)}/cancel`, {}); }
  catch (e) { toast(e.message, "bad"); return; }
  await loadRequests();
  toast(t("unqueued"));
}

// Deleting is for good: the whole request (clips, frames, journal) goes. The window asks first, in its own dialog.
async function deleteRequest(j) {
  const ok = await confirmDialog({ title: t("delete_title"), text: t("delete_text", { name: j.title || j.id }), ok: t("delete_ok"), danger: true });
  if (!ok) return;
  try {
    await postJSON(`/api/jobs/${encodeURIComponent(j.tool)}/${encodeURIComponent(j.id)}/delete`, { confirm: "delete" });
  } catch (e) { toast(e.code === "running" ? t("delete_running") : e.message, "bad"); return; }
  const key = j.tool + "/" + j.id;
  pins.peek().delete(key); savePinned(); pins.touch();
  if (seen) { delete seen[key]; saveSeen(); }
  if (home?.open && home.open[0] === j.tool && home.open[1] === j.id) api.go("home");
  await loadRequests();
  toast(t("deleted"));
}

// A modal question in the window's own look. Resolves true for the main button; Escape, the backdrop or «Cancel» —
// false. The cancel button has the focus, so a stray Enter never deletes anything.
export function confirmDialog({ title, text, ok, cancel, danger = false }) {
  return new Promise((resolve) => {
    const done = (v) => { document.removeEventListener("keydown", key, true); back.remove(); resolve(v); };
    const key = (e) => { if (e.key === "Escape") { e.preventDefault(); done(false); } };
    const no = h("button.btn", { type: "button", onclick: () => done(false) }, cancel || t("cancel"));
    const yes = h("button", { type: "button", class: "btn " + (danger ? "btn-danger-solid" : "btn-primary"), onclick: () => done(true) }, ok);
    const back = h("div.modal-back", { onclick: (e) => { if (e.target === back) done(false); } },
      h("div.modal", { role: "alertdialog", "aria-modal": "true", "aria-labelledby": "modal-title" },
        h("h2#modal-title", title), text ? h("p", text) : null, h("div.modal-acts", no, yes)));
    document.body.append(back);
    document.addEventListener("keydown", key, true);
    no.focus();
  });
}

// Dragging a request is the window's own (pointer events), not the browser's drag and drop: inside SMTV's window
// (WKWebView in pywebview) the native drop never arrived. A press that moves more than a few pixels lifts the row; a copy
// follows the pointer, «Pinned» shows and lights up under it; releasing over «Pinned» pins, over the list unpins.
// «Pinned» has its own order (owner, 20.11): over it an empty slot opens where the row would land, as if it were
// already there; dragging a pinned row inside «Pinned» moves it.
let dragged = false;
const DRAG_START_PX = 5;
function pressRow(e, row, key) {
  if (e.button !== 0 || e.target.closest(".req-act")) return;
  const x0 = e.clientX, y0 = e.clientY, box = row.getBoundingClientRect();
  let ghost = null, over = null;
  // Where a release lands: «Pinned» (pin, or move inside it), or — for a pinned row — anywhere outside «Pinned», wherever
  // it is released (owner, 21.11): it is unpinned as soon as it has left the block. The list then lights up as the place
  // it goes back to.
  const zoneAt = (x, y) => {
    const zone = home?.list.querySelector(".pin-zone");
    const inside = zone && (() => { const b = zone.getBoundingClientRect(); return x >= b.left && x <= b.right && y >= b.top && y <= b.bottom; })();
    if (inside) return zone;
    return pins.peek().has(key) ? home?.list.querySelector(".req-rest") || null : null;
  };
  const move = (ev) => {
    if (!ghost) {
      if (Math.hypot(ev.clientX - x0, ev.clientY - y0) < DRAG_START_PX) return;
      dragging.value = key;
      ghost = row.cloneNode(true);
      ghost.classList.add("drag-ghost");
      ghost.style.width = box.width + "px";
      document.body.append(ghost);
      row.classList.add("drag-src"); home?.list.classList.add("dragging"); document.documentElement.classList.add("dragging-row");
      if (pins.peek().has(key)) row.classList.add("lifted");   // a pinned row leaves its place: the slot shows where it goes
    }
    ghost.style.transform = `translate(${ev.clientX - (x0 - box.left)}px, ${ev.clientY - (y0 - box.top)}px)`;
    const z = zoneAt(ev.clientX, ev.clientY);
    if (z !== over) { over?.classList.remove("drop-on", "drop-out"); z?.classList.add(z.classList.contains("pin-zone") ? "drop-on" : "drop-out"); over = z; }
    ghost.classList.toggle("leaving", !!z && !z.classList.contains("pin-zone"));   // out of «Pinned»: it will be unpinned
    if (z?.classList.contains("pin-zone")) placeSlot(z, ev.clientY); else removeSlot();
  };
  const up = (ev) => {
    window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); window.removeEventListener("pointercancel", up);
    if (!ghost) return;                              // a plain click: the row opens as usual
    dragged = true; setTimeout(() => { dragged = false; }, 0);
    ghost.remove();
    const z = ev.type === "pointerup" ? zoneAt(ev.clientX, ev.clientY) : null;
    over?.classList.remove("drop-on", "drop-out");
    const at = slotIndex();
    removeSlot();
    endDrag();
    if (z?.classList.contains("pin-zone")) placePin(key, at);
    else if (z && pins.peek().has(key)) togglePin(key);
  };
  window.addEventListener("pointermove", move); window.addEventListener("pointerup", up); window.addEventListener("pointercancel", up);
}

// The slot: an empty row in «Pinned» at the place the dragged row would take (by the pointer's height against the
// middles of the pinned rows); its index there is where the request goes.
let slot = null;
function placeSlot(zone, y) {
  const rows = [...zone.querySelectorAll(".req:not(.lifted)")];
  const before = rows.find((r) => { const b = r.getBoundingClientRect(); return y < b.top + b.height / 2; });
  slot ||= h("div.pin-slot");
  if (before ? slot.nextElementSibling === before : slot.parentElement === zone && slot.nextElementSibling?.classList.contains("pin-hint")) return;
  if (before) zone.insertBefore(slot, before); else zone.insertBefore(slot, zone.querySelector(".pin-hint"));
  zone.classList.add("has-slot");
}
function removeSlot() { slot?.parentElement?.classList.remove("has-slot"); slot?.remove(); }
function slotIndex() {
  if (!slot?.parentElement) return -1;
  return [...slot.parentElement.children].filter((el) => el === slot || (el.classList.contains("req") && !el.classList.contains("lifted"))).indexOf(slot);
}
function placePin(key, at) {
  const order = [...pins.peek()].filter((k) => k !== key);
  order.splice(at < 0 ? order.length : Math.min(at, order.length), 0, key);
  pins.value = new Set(order); savePinned();
}

function endDrag() {
  document.documentElement.classList.remove("dragging-row");
  if (home) {
    home.list.classList.remove("dragging");
    for (const el of home.list.querySelectorAll(".drag-src, .drop-on, .drop-out, .lifted")) el.classList.remove("drag-src", "drop-on", "drop-out", "lifted");
  }
  dragging.value = null;
}

// Every group (Pinned, Today, Yesterday…) folds by a click on its name; remembered in this window.
const folds = signal(new Set());
try { folds.value = new Set(JSON.parse(store("smtv.folded") || "[]")); } catch {}
function groupHead(g) {
  const b = h("button.side-group.group-head", { type: "button" }, h("span", t(g)), icon(ICONS.chevron));
  b.onclick = () => { const f = folds.peek(); f.has(g) ? f.delete(g) : f.add(g); try { localStorage.setItem("smtv.folded", JSON.stringify([...f])); } catch {} folds.touch(); };
  return b;
}

// The list (V6): «Pinned» and the rest are built once; their rows, group names and hints follow the requests by key,
// so a running request that changes every second touches only its own row.
function listItems(parts) {
  return parts.map((x) => x.g ? { k: "h:" + x.g, g: x.g } : x.j ? { k: "r:" + x.j.tool + "/" + x.j.id, j: x.j } : { k: x.hint, hint: x.hint });
}
function fillList(box, items, known, pinned, folded, opened) {
  keyed(box, items, {
    key: (x) => x.k,
    create: (x) => x.g ? groupHead(x.g) : x.j ? requestRow(x.j.tool + "/" + x.j.id) : h("div", { class: x.hint }, t(x.hint === "pin-hint" ? "pin_hint" : "unpin_hint")),
    update: (node, x) => { if (x.g) attr(node, "aria-expanded", String(!folded.has(x.g))); else if (x.j) updateRow(node, x.j, known, pinned, opened); },
  });
}
effect(() => {
  requests = live.jobs.value || [];
  const pinned = pins.value, folded = folds.value, open = openReq.value;
  if (!homeOn.value || dragging.value) return;
  drawRequests(pinned, folded, open);
});
function drawRequests(pinned, folded, opened) {
  if (!seen) loadSeen();
  if (opened) {
    markSeen(...opened);
    // the open request's name in the top bar follows the list: the stream's title arrives only after its audio is in
    const open = requests.find((r) => r.tool === opened[0] && r.id === opened[1]);
    if (open?.title) setTopTitle(open.title);
  }
  const known = new Map(state.tools.map((x) => [x.name, x]));
  for (const key of [...pinned]) if (!requests.some((j) => j.tool + "/" + j.id === key)) pinned.delete(key);   // removed jobs
  const byKey = new Map(requests.map((j) => [j.tool + "/" + j.id, j]));
  const top = [...pinned].map((k) => byKey.get(k)).filter(Boolean);     // the order the person gave
  const top2 = [{ g: "g_pinned" }, ...(folded.has("g_pinned") ? [] : top.map((j) => ({ j }))), { hint: "pin-hint" }];
  // «Waiting» first, in the queue's order (owner, 20.11): what starts next is on top
  const waiting = requests.filter((j) => j.status === "queued" && !pinned.has(j.tool + "/" + j.id))
    .sort((a, b) => (a.queue?.position ?? 0) - (b.queue?.position ?? 0) || a.tool.localeCompare(b.tool));
  const rest = [{ hint: "unpin-hint" }];
  if (waiting.length) { rest.push({ g: "g_queue" }); if (!folded.has("g_queue")) rest.push(...waiting.map((j) => ({ j }))); }
  let group = null;
  for (const j of requests) {
    if (pinned.has(j.tool + "/" + j.id) || j.status === "queued") continue;
    const g = dayGroup(j.updated);
    if (g !== group) { rest.push({ g }); group = g; }
    if (!folded.has(g)) rest.push({ j });
  }
  keyed(home.list, requests.length ? ["pins", "rest"] : ["empty"], {
    key: (k) => k,
    create: (k) => k === "pins" ? h("div.pin-zone") : k === "rest" ? h("div.req-rest") : h("p.side-empty", t("no_requests")),
  });
  if (!requests.length) return;
  const [pinBox, restBox] = home.list.children;
  pinBox.classList.toggle("has", top.length > 0);
  fillList(pinBox, listItems(top2), known, pinned, folded, opened);
  fillList(restBox, listItems(rest), known, pinned, folded, opened);
}

function showHome(parts) {
  const hv = homeView();
  if (document.getElementById("view").firstChild !== hv.node) mountView(hv.node, () => { hv.close?.(); hv.close = null; hv.open = null; home = null; batch(() => { homeOn.value = false; openReq.value = null; }); });
  markRail("home");
  const [toolName, job] = parts;
  const key = toolName && job ? [toolName, job] : null;
  const same = key && hv.open && hv.open[0] === key[0] && hv.open[1] === key[1];
  // with no requests yet, a narrow window shows the new request (the welcome of the first run), not an empty list (V1)
  hv.node.classList.toggle("open", !!key || parts[0] === "new" || !requests.length);
  if (same) return;
  hv.close?.(); hv.close = null; hv.open = key;
  hv.work.scrollTop = 0;
  batch(() => { homeOn.value = true; openReq.value = key; });
  if (!key) { showNew(hv, parts[0] === "new" ? parts[1] : null); return; }
  const tool = state.tools.find((x) => x.name === toolName);
  const back = h("a.btn.btn-ghost.btn-sm.back", { href: "#/home" }, icon(ICONS.left), t("back"));
  const req = requests.find((r) => r.tool === toolName && r.id === job);
  setTopTitle(req?.title || job);
  const box = h("div.page");
  hv.work.replaceChildren(back, box);
  const entry = modules.get(toolName);
  if (!tool || !entry || entry.error || !entry.mod.mountJob) {
    box.replaceChildren(h("div.card.empty", h("b", tool?.page?.title || toolName), h("div.result.bad",
      !tool ? t("open_failed", { e: toolName }) : entry?.error ? t("section_failed", { name: tool.page.title, e: entry.error }) : t("no_job_view"))));
    return;
  }
  try {
    const handle = entry.mod.mountJob(box, toolApi(tool), job) || {};
    hv.close = () => { try { handle.close?.(); } catch (e) { console.error(e); } };
  } catch (e) {
    box.replaceChildren(h("div.card.empty", h("div.result.bad", t("section_failed", { name: tool.page.title, e: String(e.message || e) }))));
  }
}

let lastKind = store("smtv.kind");
// «New request» (owner, 20.11): a question and one field in the middle of the page, nothing else. With more than one
// kind of request, a quiet switch above the field picks it.
function showNew(hv, want) {
  const kinds = state.tools.filter((x) => x.page?.request && modules.get(x.name)?.mod?.mountNew);
  const pick = kinds.find((x) => x.name === want) || kinds.find((x) => x.name === lastKind) || kinds[0];
  const form = h("div.new-form");
  const page = h("div.new-page", h("div.new-center",
    h("h1.new-title", t("new_question")),
    kinds.length > 1 ? h("div.kinds", { role: "group" }, kinds.map((x) => h("button.kind", { type: "button", "aria-pressed": String(x === pick),
      onclick: () => { lastKind = x.name; store("smtv.kind", x.name); api.go("home", "new", x.name); } }, txt(x.page.request.title)))) : null,
    form));
  hv.work.replaceChildren(page);
  if (!pick) { form.replaceChildren(h("p.muted", t("no_kinds")), h("a.btn", { href: "#/plugins" }, t("go_plugins"))); return; }
  try {
    const handle = modules.get(pick.name).mod.mountNew(form, toolApi(pick)) || {};
    hv.close = () => { try { handle.close?.(); } catch {} };
    blockIfNotReady(hv, pick, page, form);
  } catch (e) { form.replaceChildren(h("div.result.bad", t("section_failed", { name: pick.page.title, e: String(e.message || e) }))); }
}

// Plugins: a card per plugin (installed, broken, can be added, soon); a plugin's own page
function pluginStatus(p) {
  if (p.status === "installed" && modules.get(p.name)?.error) return ["broken", t("p_broken"), "bad"];
  return { installed: ["installed", t("p_installed"), "ok"], broken: ["broken", t("p_broken"), "bad"], available: ["available", t("p_available"), "info"], soon: ["soon", t("p_soon"), "warn"] }[p.status];
}
// a plugin's state as a dot and a word, and its version as quiet text: calm, the same on a card and on its page
const pluginState = (label, tone) => h("span", { class: "p-state " + tone }, label);
const pluginVersion = (v) => h("span.p-ver", { title: t("p_version", { v }) }, "v" + v);
const pluginSummary = (p) => p.soon ? txt(p.soon.summary) : t("sum_" + p.name) === "sum_" + p.name ? p.summary : t("sum_" + p.name);
const pluginIcon = (p) => p.icon || (p.soon ? soonIcon(p.soon) : ICONS.box);
const pluginTitle = (p) => p.status === "installed" ? p.title : p.soon ? txt(p.soon.title) : ({ vodcut: "VodCut" }[p.name] || p.title);
// what a plugin's page says about it: its own text; an announced one — its short page from soon.json
function pluginAbout(p, tool) {
  if (p.status !== "soon" || !p.soon) return h("p.plug-about", txt(tool?.page?.about) || pluginSummary(p));
  return h("div.plug-soon", ...(p.soon.lead || p.soon.points || p.soon.notes ? soonBody(p.soon) : [h("p.plug-about", txt(p.soon.summary))]));
}
function showPlugins(parts) {
  markRail("plugins");
  const plugins = state.plugins || [];
  if (!parts[0]) {
    mountView(solo(h("div.page",
      h("div.plugins-head", h("div", h("p.h-eyebrow", "SMTV"), h("h1.h-big", t("plugins_title")), h("p.muted", { style: "margin:8px 0 0" }, t("plugins_sub"))),
        h("button.btn.add-plugin", { type: "button", onclick: addPluginDialog }, icon(ICONS.plus), t("p_add"))),
      (() => { const b = liveBox("update", updateCard, "section"); b.className = "card card-pad upd"; return b; })(),
      h("div.plugins", plugins.map((p) => {
        const [cls, label, chip] = pluginStatus(p);
        // one shape for every card (owner, 21.11: chips under the title made the cards uneven): icon and a quiet status
        // on top, title and summary, the version at the bottom
        const newer = newerChip(p);
        return h("a.card.plugin", { class: "card plugin " + cls, href: `#/plugins/${encodeURIComponent(p.name)}` },
          h("div.plugin-top", h("span.p-ico", icon(pluginIcon(p))), pluginState(label, chip)),
          h("div.plugin-body", h("h3", pluginTitle(p)), h("p", pluginSummary(p)),
            modules.get(p.name)?.error ? h("p.hint", t("p_section_broken")) : null),
          p.version || newer ? h("div.plugin-foot", p.version ? pluginVersion(p.version) : null, newer) : null);
      })))));
    return;
  }
  const p = plugins.find((x) => x.name === parts[0]);
  if (!p) { api.go("plugins"); return; }
  const [, label, chip] = pluginStatus(p);
  const tool = state.tools.find((x) => x.name === p.name);
  const others = state.tools.filter((x) => x.name !== p.name).map((x) => x.name);
  const cmd = p.status === "installed" ? `uv tool install --reinstall "smtv${others.length ? `[${others.join(",")}]` : ""}"` : p.add || null;
  const err = modules.get(p.name)?.error || p.error;
  // Agents belong to plugins (owner, 20.11): a tab on the plugin's page, no item of their own in the rail
  const tab = tool?.agents && parts[1] === "agents" ? "agents" : "about";
  const head = [
    h("a.btn.btn-ghost.btn-sm", { href: "#/plugins", style: "justify-self:start" }, icon(ICONS.left), t("plugins_title")),
    h("div.plug-hero", h("span.p-ico", { class: "p-ico" }, icon(pluginIcon(p))),
      h("div", h("h1.h-big", pluginTitle(p)), h("div.plugin-meta", { style: "margin-top:8px" }, pluginState(label, chip), p.version ? pluginVersion(p.version) : null))),
    tool?.agents ? pluginTabs(p, tool, tab) : null,
  ];
  if (tab === "agents") { mountView(solo(h("div.page", ...head, agentsPane(p.name))), null); return; }
  mountView(solo(h("div.page", ...head,
    h("section.card.card-pad", { style: "display:grid;gap:14px" },
      pluginAbout(p, tool),
      err ? h("div.result.bad", h("div", h("b", t("p_broken_about")), h("div.mono", { style: "margin-top:6px" }, err))) : null),
    (() => { const b = liveBox("update", (u) => pluginActions(p, u, cmd)); b.className = "card card-pad plug-act-card"; return b; })(),
    p.status === "installed" || p.status === "available" ? (() => { const b = liveBox("update", (u) => pluginNews(p, u)); b.className = "card card-pad"; return b; })() : null,
  )), null);
}

// --- agents on a plugin's page (stage 10) ------------------------------------------------------------------------
// A card per agent: what it does and needs, the model it takes now (and changing it), what was tested, its calls, and
// its prompt and schema to read and copy. A shared agent of the core shows the same card on every plugin that uses it.

function pluginTabs(p, tool, current) {
  const tab = (id, label) => h("button", { type: "button", role: "tab", "aria-selected": String(current === id),
    onclick: () => (id === "about" ? api.go("plugins", p.name) : api.go("plugins", p.name, id)) }, label);
  return h("div.seg.plug-tabs", { role: "tablist" }, tab("about", t("ag_tab_about")), tab("agents", t("ag_tab_agents", { n: tool.agents })));
}

const isoDay = (d) => d ? new Date(d + "T12:00:00").toLocaleDateString(lang === "en" ? "en-GB" : lang, { day: "numeric", month: "long", year: "numeric" }) : "";
const modelName = (id) => id || t("ag_codex_default");
const pluginName = (n) => PKG_TITLE[n] || state.tools.find((x) => x.name === n)?.page?.title || n;

function agentsPane(name) {
  const box = h("div.agents", h("div.faint", "…"));
  const draw = (d) => box.replaceChildren(agentsHead(d), ...d.agents.map((a) => agentCard(name, a, d)),
    h("p.hint", t("ag_prompts", { v: d.prompts.version, date: isoDay(d.prompts.date) })));
  getJSON(`/api/tools/${encodeURIComponent(name)}/agents`).then(draw).catch((e) => box.replaceChildren(h("div.result.bad", e.message)));
  return box;
}

function agentsHead(d) {
  return h("div.ag-intro",
    h("p.muted", t("ag_intro")),
    h("div.plugin-meta",
      d.providers ? null : h("span.chip.warn", t("ag_no_conn")),
      !d.providers && !PHONE ? h("a.btn.btn-sm", { href: "#/settings/providers" }, t("ag_conn_set")) : null));
}

function warningsOf(a, m) {
  return (m.warnings || []).map((w) => h("div.result.warn", icon(ICONS.warn), h("span", t("w_" + w, { need: t("lvl_" + a.needs.level) }))));
}

function agentCard(name, a, d) {
  const cur = a.current;
  // the provider and the model it takes now, read only: they are changed in «Settings → Agents» (owner, 21.11)
  const change = h("a.btn.btn-sm", { href: `#/settings/agents/${encodeURIComponent(name)}/${encodeURIComponent(a.id)}` }, t("ag_open_settings"));
  const model = cur.source === "none"
    ? h("div.ag-model", h("div.ag-model-line", h("span.faint", t("ag_no_conn")), h("div.ag-actions", change)))
    : h("div.ag-model",
      h("div.ag-model-line",
        h("div.ag-model-name", h("span.faint", t("ag_model_now")),
          h("b", h("span", cur.provider_name), h("span.faint", " · "), h(cur.model ? "span.mono" : "span", modelName(cur.model)))),
        h("div.ag-actions", change)),
      cur.instead_of ? h("div.result.warn", icon(ICONS.warn), h("span", t("ag_instead", { name: cur.instead_of }))) : null,
      ...warningsOf(a, cur));
  // what it needs
  const n = a.needs;
  const needs = h("div.ag-needs",
    h("div.plugin-meta", h("span.chip", t("lvl_" + n.level)), h("span.chip", n.images ? t("ag_images") : t("ag_text_only")),
      txt(n.text) ? h("span.chip", txt(n.text)) : null, n.strict_json ? h("span.chip", t("ag_json")) : null),
    txt(n.why) ? h("p.muted", txt(n.why)) : null);
  // tested and recommended, for each connection the table knows
  const recs = h("div.ag-recs", ...(a.recommendations || []).map((r) => h("div.ag-rec", { class: "ag-rec" + (r.connected ? " cur" : "") },
    h("div.ag-rec-top", h("span.ag-rec-prov", r.label), h(r.model ? "span.mono" : "span", modelName(r.model)),
      r.tested.length ? h("span.chip.ok", t("ag_tested_on", { date: isoDay(r.tested[0].date) })) : h("span.chip", t("ag_untested"))),
    ...r.tested.map((x) => h("p.hint", `${x.with} · ${x.how || ""} — ${x.result}`)))));
  // one line of numbers from the journals
  const st = a.stats;
  const stats = h("p.ag-stats", st.calls ? t("ag_stats", { n: fmt.num(st.calls), s: st.avg_s != null ? t("unit_s", { n: fmt.dec(st.avg_s, 1) }) : t("ag_avg_unknown"),
    e: fmt.num(st.errors), cost: st.cost_usd != null ? fmt.money(st.cost_usd) : t("ag_cost_unknown") }) : t("ag_stats_none"));
  // the prompt and the schema: read only, copy
  const source = (label, file, text, href) => {
    const btn = h("button.btn.btn-sm", { type: "button" }, icon(ICONS.copy), t("copy"));
    btn.onclick = (e) => { e.preventDefault(); copy(text || "", btn); };
    return h("details.ag-src", h("summary", h("span", label), h("span.mono.faint", file)),
      h("div.ag-src-bar", btn, href ? h("a.btn.btn-ghost.btn-sm", { href, target: "_blank", rel: "noopener" }, icon(ICONS.ext), t("ag_in_repo")) : null),
      h("pre.ag-pre", text || "—"));
  };
  const tag = `v${d.prompts.version}`;
  // V1 (owner 22.11): the step in one sentence and what it runs on now; everything for the curious under «More»
  return h("section.card.card-pad.ag-card",
    h("div.ag-head", h("div", h("h3", txt(a.title)), h("p.muted", txt(a.short) || txt(a.does)))),
    model,
    h("details.ag-more", h("summary", t("ag_more")),
      h("div.ag-more-body",
        txt(a.short) ? h("p.muted", txt(a.does)) : null,
        h("div.plugin-meta", h("span.chip", t("ag_stage", { s: txt(a.stage) })), a.shared ? h("a.chip.info.chip-link", { href: "#/settings/about/core", title: t("ab_core_title") }, t("ag_shared")) : null),
        a.shared ? h("p.hint", t("ag_used_by", { list: a.users.map(pluginName).join(", ") })) : null,
        cur.source === "none" ? null : h("div.plugin-meta", ...modelChips(cur), t("src_" + cur.source) ? h("span.faint.ag-src-note", t("src_" + cur.source)) : null),
        h("div.ag-block", h("h4", t("ag_needs")), needs),
        h("div.ag-block", h("h4", t("ag_tested_title")), recs),
        stats,
        source(t("ag_prompt"), a.prompt, a.prompt_text, `${d.prompts.repo}/blob/${tag}/${a.prompt}`),
        source(t("ag_schema"), `schemas/${a.schema}.json`, a.schema_text, `${d.prompts.repo}/blob/${tag}/schemas/${a.schema}.json`))));
}

// --- updates and plugins from the window (stage 8) -----------------------------------------------------------------
const PKG_TITLE = { smtv: "SMTV", "smtv-core": "SMTV core", vodcut: "VodCut", livecut: "LiveCut" };
const canChange = (u) => u && (u.kind === "uv" || u.kind === "pip");          // plugins: only uv and pip
const canUpdate = (u) => canChange(u) || (u && (u.kind === "dmg" || u.kind === "exe"));   // the apps: by their installer
const isApp = (u) => u && ["dmg", "exe", "zip"].includes(u.kind);   // the desktop apps: plugins inside, no terminal
const RELEASES = "https://github.com/streammomenttv/smtv/releases/latest";
// a check that failed, in plain words (the server's code before the colon; channel.ChannelError)
const updError = (e) => { const key = "upd_err_" + String(e).split(":")[0]; return t(key) === key ? t("upd_error", { e }) : t(key); };

// A box that follows one part of the window's state, and lets go once it left the page. Built again only when that
// part really changed (V6): the same picture sent again touches nothing.
function liveBox(key, draw, tag = "div") {
  const box = h(tag);
  let off = null;
  off = effect(() => {
    const v = live[key].value;
    if (box.dataset.on && !box.isConnected) { queueMicrotask(() => off?.()); return; }
    box.dataset.on = "1";
    region(box, sig(v), () => draw(v));   // a draw may return nested lists
  });
  return box;
}

function lastText(l) {
  const names = (a, b) => (b || []).filter((x) => !(a || []).includes(x)).map((x) => PKG_TITLE[x] || x).join(", ");
  const name = l.action === "install" ? names(l.from?.tools, l.to?.tools) : names(l.to?.tools, l.from?.tools);
  const what = t("what_" + l.action, { name });
  if (l.state === "done") return l.action === "update" ? t("upd_done", { a: l.from?.version, b: l.to?.version })
    : t(l.action === "install" ? "upd_inst_done" : "upd_rm_done", { name });
  if (l.state === "rolled_back") return t("upd_back", { what, a: l.from?.version, log: l.log || "" });
  return t("upd_failed", { what, log: l.log || "" });
}

function watchUpdates() {
  let overlay = null;
  effect(() => {
    const u = live.update.value;
    if (!u) return;
    const dot = document.getElementById("update-dot"); if (dot) attr(dot, "hidden", !u.available);
    if (u.leaving && !overlay) {
      overlay = h("div.modal-back.updating", h("div.modal", { role: "alertdialog", "aria-modal": "true" },
        h("h2", t("upd_overlay_title")), h("p", t("upd_overlay_text")), h("div.upd-spin", { "aria-hidden": "true" })));
      document.body.append(overlay);
    } else if (!u.leaving && overlay) { overlay.remove(); overlay = null; }
    const l = u.last;
    if (l && !l.seen && ["done", "rolled_back", "failed"].includes(l.state)) {   // said once, after SMTV opened again
      toast(lastText(l), l.state === "done" ? "" : "bad");
      postJSON("/api/updates/seen").catch(() => {});
    }
  });
}

async function changeSmtv(action, tool = null) {
  const u = live.update.value || {};
  const name = PKG_TITLE[tool] || tool;
  const jobs = u.running ? t("upd_confirm_jobs", { n: u.running }) : "";
  const ask = action === "update" ? { title: t("upd_confirm_title", { v: u.available?.version }), text: [t("upd_confirm"), jobs].join(" ").trim(), ok: t("upd_go") }
    : action === "install" ? { title: t("p_install_title", { name }), text: [t("p_install_text"), jobs].join(" ").trim(), ok: t("p_install") }
    : { title: t("p_remove_title", { name }), text: [t("p_remove_text"), jobs].join(" ").trim(), ok: t("p_remove"), danger: true };
  if (!(await confirmDialog(ask))) return;
  try { live.update.value = await postJSON(action === "update" ? "/api/updates/update" : `/api/plugins/${encodeURIComponent(tool)}/${action}`, {}); }
  catch (e) { toast(e.message, "bad"); }
}
async function updateNow() {
  const p = live.update.value?.pending;
  if (!p || !(await confirmDialog({ title: t("upd_stop_title"), text: t("upd_stop_text"), ok: t("upd_stop_go"), danger: true }))) return;
  try { live.update.value = await postJSON(p.action === "update" ? "/api/updates/update" : `/api/plugins/${encodeURIComponent(p.tool)}/${p.action}`, { now: true }); }
  catch (e) { toast(e.message, "bad"); }
}
async function checkNow(btn) {
  if (btn) btn.disabled = true;
  try { live.update.value = await postJSON("/api/updates/check"); } catch (e) { toast(e.message, "bad"); }
  if (btn) btn.disabled = false;
}
const DOCKER_UPDATE = "docker compose up -d --build";
const installCmd = () => DOCKER ? DOCKER_UPDATE : `uv tool install --reinstall "smtv${state.tools.length ? `[${state.tools.map((x) => x.name).join(",")}]` : ""}"`;
function cmdLine(cmd) { const b = h("button.btn.btn-sm", { type: "button" }, t("copy")); b.onclick = () => copy(cmd, b); return h("div.fix", h("code", cmd), b); }

// What changed, package by package: the index's own list for every version newer than the installed one
function changesList(u, only = null) {
  const rows = Object.entries(u?.packages || {}).filter(([n, p]) => (!only || n === only) && p.latest && p.changes?.length && p.latest !== p.current);
  if (!rows.length) return null;
  return h("div.upd-changes", rows.map(([n, p]) => h("div.upd-pkg",
    only ? null : h("b", `${PKG_TITLE[n] || n} ${p.current} → ${p.latest}`),
    p.changes.map((c) => h("div.upd-ver", h("small.faint", c.version), h("ul", c.notes.map((x) => h("li", x))))))));
}

// The card of SMTV's own version: on Plugins and in Settings → System
function updateCard(u) {
  if (!u) return h("p.faint", "…");
  if (PHONE) return h("div.upd-head", h("div.upd-text", h("b", `SMTV ${u.packages?.smtv?.current || state.version}`),
    h("p", { class: u.available ? "upd-line new" : "upd-line" }, u.available ? t("upd_available", { v: u.available.version }) + " · " + t("phone_only_pc") : t("phone_only_pc"))));
  const cur = u.packages?.smtv?.current || state.version;
  const btns = [];
  let line;
  if (u.kind === "dev") line = t("upd_dev");
  else if (u.kind === "docker") line = (u.available ? t("upd_available", { v: u.available.version }) + ". " : "") + t("upd_docker");
  else if (u.kind === "zip") line = h("span", t("upd_zip"), " ", h("a", { href: RELEASES, target: "_blank", rel: "noopener" }, t("upd_zip_link")));
  else if (!canUpdate(u)) line = t("upd_none");
  else if (u.leaving) line = t(u.kind === "dmg" || u.kind === "exe" ? "upd_installer" : "upd_leaving");
  else if (u.pending) {
    line = t("upd_pending", { n: u.running });
    btns.push(h("button.btn.btn-sm.btn-danger", { type: "button", onclick: updateNow }, t("upd_pending_now")),
      h("button.btn.btn-sm.btn-ghost", { type: "button", onclick: async () => { live.update.value = await postJSON("/api/updates/cancel"); } }, t("upd_cancel")));
  } else if (u.checking) line = t("upd_checking");
  else if (u.available) {
    line = t("upd_available", { v: u.available.version });
    btns.push(h("button.btn.btn-sm.btn-primary", { type: "button", onclick: () => changeSmtv("update") }, u.running ? t("upd_after_jobs") : t("upd_button")));
  } else line = u.checked ? t("upd_latest", { when: fmt.date(u.checked) }) : t("upd_never");
  if ((canUpdate(u) || u.kind === "docker") && !u.leaving && !u.pending) {
    const b = h("button.btn.btn-sm.btn-ghost", { type: "button", disabled: u.checking }, t("upd_now"));
    b.onclick = () => checkNow(b);
    btns.push(b);
  }
  const l = u.last && ["done", "rolled_back", "failed"].includes(u.last.state) ? u.last : null;
  return [
    h("div.upd-head", h("div.upd-text", h("b", `SMTV ${cur}`), h("p", { class: u.available ? "upd-line new" : "upd-line" }, line)), h("div.upd-btns", ...btns)),
    !canUpdate(u) && u.kind !== "dev" && !isApp(u) ? cmdLine(installCmd()) : null,
    u.error && !u.checking ? h("div.result.bad", updError(u.error)) : null,
    u.available && !u.leaving ? changesList(u) : null,
    l ? h("p", { class: "hint upd-last " + l.state }, lastText(l)) : null,
  ];
}

function newerChip(p) {
  const u = live.update.value;
  const latest = u?.packages?.[p.name]?.latest;
  return p.version && latest && latest !== p.version && u.packages[p.name].current !== latest ? h("span.chip.accent", t("p_new_version", { v: latest })) : null;
}
// Install / Remove on a plugin's page (stage 8): the same updater as an update; only plugins of SMTV's own list
function pluginActions(p, u, cmd) {
  if (PHONE) return h("p.hint", t("phone_only_pc_about"));
  if (p.status === "soon") return h("div.plug-actions", h("button.btn.btn-primary", { type: "button", disabled: true }, t("p_install")), h("span.chip.warn", t("p_soon")));
  const can = canChange(u) && (p.status === "installed" || p.status === "available") && !u.leaving;
  const mine = u?.pending && u.pending.tool === p.name;
  const busy = !!(u?.pending || u?.leaving);
  const btn = p.status === "available"
    ? h("button.btn.btn-primary", { type: "button", disabled: !can || busy, onclick: () => changeSmtv("install", p.name) }, t("p_install"))
    : h("button.btn", { type: "button", disabled: !can || busy || p.status !== "installed", onclick: () => changeSmtv("remove", p.name) }, t("p_remove"));
  return [
    h("div.plug-actions", btn,
      mine ? h("span.hint", t("p_pending", { n: u.running })) : null,
      mine ? h("button.btn.btn-sm.btn-danger", { type: "button", onclick: updateNow }, t("upd_pending_now")) : null,
      mine ? h("button.btn.btn-sm.btn-ghost", { type: "button", onclick: async () => { live.update.value = await postJSON("/api/updates/cancel"); } }, t("upd_cancel")) : null,
      u?.leaving ? h("span.hint", t("upd_leaving")) : null),
    u?.kind === "docker" ? h("p.hint", t("p_docker")) : isApp(u) ? h("p.hint", t("p_app"))
      : !canChange(u) && cmd ? [h("p.hint", u?.kind === "dev" ? t("upd_dev") : t("p_cannot")), cmdLine(cmd)] : null,
  ];
}
function pluginNews(p, u) {
  const pk = u?.packages?.[p.name];
  const latest = pk?.latest || u?.catalog?.[p.name]?.latest;
  return [h("p.h-eyebrow", t("p_whats_new")),
    p.status === "available" ? h("p.muted", { style: "margin:0" }, t("p_will_install", { v: u?.packages?.smtv?.current || state.version }))
      : pk && pk.latest && pk.latest !== pk.current ? (changesList(u, p.name) || h("p.muted", { style: "margin:0" }, t("p_new_version", { v: pk.latest })))
      : h("p.muted", { style: "margin:0" }, u?.checked ? t("p_latest") : t("p_not_checked"))];
}

// a «soon» page of the rail (Scheduled, Promotion, Campaigns): its text from soon.json
function showSoon(id) {
  const item = soonOf(id);
  if (!item) { api.go("home"); return; }
  markRail(id);
  mountView(solo(h("div.soon-page", h("div", h("span.p-ico", { class: "p-ico" }, icon(soonIcon(item))), h("h1.h-big", txt(item.title)),
    item.lead ? h("p", txt(item.lead)) : null,
    item.points ? h("ul.soon-points", item.points.map((x) => h("li", txt(x)))) : null,
    item.note ? h("p.soon-note", txt(item.note)) : null, h("span.chip.warn", t("p_soon"))))));
}

// «Add a plugin» (stage 18): a small «soon» window. Installs nothing and asks the server nothing.
function addPluginDialog() {
  const item = soonOf("own-plugins");
  const done = () => { document.removeEventListener("keydown", key, true); back.remove(); };
  const key = (e) => { if (e.key === "Escape") { e.preventDefault(); done(); } };
  const ok = h("button.btn.btn-primary", { type: "button", onclick: done }, t("got_it"));
  const back = h("div.modal-back", { onclick: (e) => { if (e.target === back) done(); } },
    h("div.modal.add-plugin-modal", { role: "dialog", "aria-modal": "true", "aria-labelledby": "modal-title" },
      h("div.add-plugin-top", h("span.p-ico", icon(ICONS.plus)), h("span.chip.warn", t("p_soon"))),
      h("h2#modal-title", txt(item?.title) || t("p_add")),
      ...(soonBody(item) || []),
      h("div.modal-acts", h("a.btn.btn-ghost", { href: "#/settings/about/soon", onclick: done }, t("whats_next")), ok)));
  document.body.append(back);
  document.addEventListener("keydown", key, true);
  ok.focus();
}

// a tool's own rail item
function showToolNav(parts) {
  const [name, id, ...rest] = parts;
  const tool = state.tools.find((x) => x.name === name && x.page?.nav?.id === id);
  const entry = modules.get(name);
  if (!tool || !entry?.mod?.mountNav) { api.go("home"); return; }
  markRail("x:" + name);
  const box = h("div.page");
  let handle = {};
  mountView(solo(box), () => { try { handle.close?.(); } catch {} });
  try { handle = entry.mod.mountNav(box, toolApi(tool), rest) || {}; }
  catch (e) { box.replaceChildren(h("div.result.bad", t("section_failed", { name: tool.page.title, e: String(e.message || e) }))); }
}

// --- Phone (stage 9): the same page on a phone over home Wi-Fi. A switch, a QR code with the address and a key, and
// what to know. Kept simple (owner, 20.11): no pairing codes, no device list; switching off cuts every phone.
function showPhone() {
  markRail("phone");
  const body = h("div.settings-body", h("div.faint", "…"));
  mountView(solo(h("div.settings-page", h("h1.h-big", t("phone_title")), body)));
  let busy = false;
  const set = async (on, address) => {
    if (busy) return; busy = true;
    try { draw(await postJSON("/api/phone", address ? { on, address } : { on })); }
    catch (e) { toast(e.message, "bad"); for (const b of body.children) b.__ksig = null; load(); }   // refused: drawn again from what is saved
    busy = false;
  };
  const limits = (p) => setGroup(t("ph_limits"), [...["ph_l_wifi", "ph_l_firewall", "ph_l_http", "ph_l_page", "ph_l_off"].map((k) => t(k)),
    ...(p.docker_hosts?.length ? [t("ph_l_hosts", { hosts: p.docker_hosts.join(", ") })] : [])].map((text) => h("div.set-row", h("div.set-text", h("p.ph-limit", text)))));
  const draw = (p) => {
    const addrs = p.addresses || [];
    blocks(body, [
      ["switch", sig(p.on, addrs, p.address), () => setGroup(null,
        setRow(t("ph_switch"), addrs.length || p.on ? t("ph_switch_about") : t(DOCKER ? "ph_no_network_docker" : "ph_no_network"),
          switchFor(p.on, (input) => set(input.checked), t("ph_switch"))),
        addrs.length > 1 ? setRow(t("ph_address"), t("ph_address_about"),
          h("select.select.set-select", { "aria-label": t("ph_address"), onchange: (e) => set(true, e.target.value), disabled: !p.on },
            addrs.map((a) => h("option", { value: a, selected: a === (p.address || addrs[0]) }, a)))) : null)],
      p.on ? ["card", sig(p.qr, p.page), () => h("section.ph-card",
        h("img.ph-qr", { src: "data:image/svg+xml;charset=utf-8," + encodeURIComponent(p.qr), alt: "QR", width: "220", height: "220" }),
        h("div.ph-text", h("b", t("ph_scan")), h("code.ph-addr", p.page), h("p", t("ph_scan_about"))))] : null,
      ["limits", sig(p.docker_hosts), () => limits(p)],
      ["denied", null, () => setGroup(null, setRow(t("ph_denied"), t("ph_denied_about")))],
    ]);
  };
  const load = async () => { try { draw(await getJSON("/api/phone")); } catch (e) { body.replaceChildren(h("div.result.bad", e.message)); } };
  load();
}

function route() {
  closeMenu();
  setTopTitle("");
  const parts = api.route();
  const [first, ...rest] = parts;
  // old addresses (#/<tool>/<job>) still open the request
  if (first && state.tools.some((x) => x.name === first)) { api.go("home", first, ...rest); return; }
  if (!first || first === "home") return showHome(rest);
  if (first === "plugins") return showPlugins(rest);
  if (first === "settings") return showSettings(rest);
  if (["scheduled", "promotion", "campaigns"].includes(first)) return showSoon(first);
  if (first === "phone") return PHONE ? api.go("home") : showPhone();
  if (first === "x") return showToolNav(rest);
  api.go("home");
}

// The window's own focus: the navigation and the top bar turn grey while another window is in front. In SMTV's window
// on macOS the page also tells the window what it saw (`focus:<0|1>:<event>`), at the event and once more half a second
// later: the window writes it into its log beside its own state (key, main, active), so a page that stays grey in a
// window that is in front shows up there with the reason (stage 16).
function watchFocus() {
  const look = (why) => {
    const on = document.hasFocus();
    document.documentElement.classList.toggle("inactive", !on);
    windowMessage(`focus:${on ? 1 : 0}:${why}`);
  };
  const seen = (e) => { look(e.type); setTimeout(() => look(e.type + "+500"), 500); };
  window.smtvFocusCheck = (why) => look(String(why || "native"));   // the window: «I just became key / active»
  window.addEventListener("focus", seen); window.addEventListener("blur", seen); document.addEventListener("visibilitychange", seen);
  seen({ type: "start" });
}

// A file dropped where no page takes it is ignored: otherwise the window would open the file itself instead of SMTV.
window.addEventListener("dragover", (e) => { if ([...(e.dataTransfer?.types || [])].includes("Files")) e.preventDefault(); });
window.addEventListener("drop", (e) => { if ([...(e.dataTransfer?.types || [])].includes("Files")) e.preventDefault(); });

async function boot() {
  watchFocus();
  applyLang();
  if (WORDS_MISSING) sendWindowError("words", new Error("/static/i18n/en.json did not load"));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeMenu(); });
  try { state = await getJSON("/api/state"); PHONE = !!state.phone; DOCKER = !!state.docker; document.documentElement.classList.toggle("on-phone", PHONE); } catch (e) { document.getElementById("view").replaceChildren(h("div.card.empty", h("div.result.bad", e.message))); return; }
  await loadModules();
  if (wordsMissing.length) sendWindowError("words", new Error(`did not load, shown in English: ${wordsMissing.join(", ")}`));
  drawRail();
  watchWindow();
  watchActivity();
  watchUpdates();
  watchCrashes();
  if (DOCKER) watchDockerApp();
  // the list's «new» marks start from what was there when the window opened: wait for the first picture (briefly)
  await Promise.race([snapshotReady, new Promise((r) => setTimeout(r, 3000))]);
  if (live.jobs.value == null) await loadRequests();
  window.addEventListener("hashchange", route);
  route();
  refreshDoctorDot();
}
// --- SMTV in Docker (stage 21): installed from Chrome or Edge, the page gets back what SMTV's own window has ---------
// A badge with the number of running jobs on the app's icon, and a notification when a job ends while the page is not
// looked at. Both only where the browser has them; nothing here is needed for the page to work.
function notifyButton() {
  if (!("Notification" in window)) return h("span.faint", t("dk_notify_none"));
  if (Notification.permission === "granted") return h("span.chip.ok", t("dk_notify_on"));
  if (Notification.permission === "denied") return h("span.faint", t("dk_notify_blocked"));
  const b = h("button.btn.btn-sm", { type: "button" }, t("dk_notify_ask"));
  b.onclick = async () => { try { await Notification.requestPermission(); } catch {} b.replaceWith(notifyButton()); };
  return b;
}
function watchDockerApp() {
  if (navigator.setAppBadge) {
    effect(() => {
      const a = live.activity.value;
      const n = (a?.running || 0) + (a?.queued || 0);
      (n ? navigator.setAppBadge(n) : navigator.clearAppBadge()).catch(() => {});
    });
  }
  const seen = new Map();   // job → its last status, so only a change from running to done or failed is told
  effect(() => {
    for (const j of live.jobs.value || []) {
      const key = j.tool + "/" + j.id, before = seen.get(key);
      seen.set(key, j.status);
      if (!before || before === j.status || !["running", "queued"].includes(before) || !["done", "failed"].includes(j.status)) continue;
      if (!("Notification" in window) || Notification.permission !== "granted" || document.visibilityState === "visible") continue;
      const name = j.title || j.id;
      try {
        new Notification(t(j.status === "done" ? "dk_done" : "dk_failed"),
          { body: t(j.status === "done" ? "dk_done_text" : "dk_failed_text", { name, n: j.clips ?? 0 }), icon: "/static/icons/icon-256.png", tag: key });
      } catch {}
    }
  });
}

boot();
