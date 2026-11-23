// VodCut's open request (V6): a running request changes only what changed — the clock its own text, a new line of the
// feed one node, a clip its own card. Run: node --test (the window's fake DOM keeps a journal of every change).
import { test, before } from "node:test";
import assert from "node:assert/strict";
import { install, journal, resetJournal } from "../../../smtv/tests/web/fakedom.mjs";

const { flush } = install();
const dom = await import("../../../smtv/src/smtv/web/dom.js");
const { mountJob } = await import("../../src/vodcut/web/section.js");

// the clock: the page's setInterval is caught, the test ticks it
let tick = null;
globalThis.setInterval = (fn) => { tick = fn; return 1; };
globalThis.clearInterval = () => {};

const fmt = {
  num: (n) => String(Math.round(n || 0)), dec: (n) => (n || 0).toFixed(1), money: (n) => "$" + (n || 0).toFixed(2),
  hms: (s) => { s = Math.max(0, Math.floor(s || 0)); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); },
  dur: (s) => Math.round(s || 0) + " s", hours: (s) => Math.round((s || 0) / 3600) + " h", clock: (t) => String(Math.floor(t)), date: String,
};
let events = null, status = null, nth = 0;
const api = {
  ...dom, fmt, tool: { name: "vodcut" },
  t: (k, vars = {}) => k + (Object.keys(vars).length ? " " + Object.values(vars).join(",") : ""),
  icon: () => dom.h("svg"),
  getJSON: async (url) => (url.endsWith("/options") ? [{ name: "recap", value: true }] : { status: "running", title: "Stream" }),
  postJSON: async () => ({}),
  stream: (url, handlers) => { events = handlers.onEvent; status = handlers.onStatus; return () => {}; },
  toast() {}, setTitle() {}, openSettings() {}, copy() {}, confirm: async () => true, refreshRequests() {}, openRequest() {},
  reportButton: () => dom.h("button", "report"),
};
const send = (type, data) => events({ type, data, t: 1000 + ++nth, n: nth });
const q = (sel) => document.querySelector(sel);
const all = (sel) => document.querySelectorAll(sel);

let root;
before(async () => {
  root = dom.h("div");
  document.body.append(root);
  mountJob(root, api, "2934000001");
  await new Promise((r) => setTimeout(r, 0));
  status({ status: "running", running: true, started: 1000 });
  send("source_ready", { title: "Stream", channel: "buster", platform: "twitchvod", duration_s: 19800, source: "https://www.twitch.tv/videos/1" });
  send("stage", { name: "audio" }); send("stage", { name: "speech", engine: "gigaam", language: "ru" }); send("stage", { name: "scan" });
  for (let i = 0; i < 4; i++) { send("episode_found", { episode_id: "e" + i, start_s: 600 * i, end_s: 600 * i + 40 }); send("model_call", { purpose: "scan", model: "m", seconds: 2 }); }
  send("stage", { name: "render" });
  for (let i = 1; i <= 3; i++) send("clip_ready", { clip: "c" + i, file: `clips/c${i}.mp4`, title: "Clip " + i });
  send("progress", { stage: "render", clip: "c4", title: "Clip 4", done: 4, total: 5 });
  send("progress", { stage: "render", clip: "c4", step: "captions" });
  flush();
  for (const d of all("details")) d.open = true;    // the widgets the person opened
});

const quiet = () => [journal.added, journal.removed];

test("the clock touches only its own text and the running stage's time", () => {
  const real = Date.now;
  let at = real();
  Date.now = () => at;
  try {
    const clockText = q("b.vc-clock").textContent;
    resetJournal();
    for (let i = 0; i < 5; i++) { at += 1000; tick(); flush(); }
    assert.deepEqual(quiet(), [0, 0]);
    assert.equal(journal.attr, 0);
    assert.notEqual(q("b.vc-clock").textContent, clockText);       // it does tick
    assert.equal(journal.text, 10, journal.log.join("\n"));       // the clock and the running stage's time, five times
  } finally { Date.now = real; }
});

test("the same state sent again changes nothing", () => {
  resetJournal();
  status({ status: "running", running: true, started: 1000 });
  send("progress", { stage: "render", clip: "c4", step: "captions" });
  flush();
  assert.deepEqual(quiet(), [0, 0], journal.log.join("\n"));
});

test("a new line of the feed is one new node on top; a counting line changes its text in place", () => {
  const feed = q("ol.vc-feed"), first = feed.firstChild;
  resetJournal();
  send("clip_failed", { clip: "c9", error: "x" }); flush();
  assert.equal(feed.children[1], first);
  assert.ok(feed.firstChild.classList.contains("vc-line"));
  send("progress", { stage: "speech", percent: 10 }); flush();
  const line = feed.firstChild;
  const added = journal.added;
  send("progress", { stage: "speech", percent: 11 }); flush();
  assert.equal(feed.firstChild, line);
  assert.equal(journal.added, added);
  assert.match(line.textContent, /11/);
});

test("a clip that gets ready changes its own card; the other cards and their videos stay", () => {
  const cards = new Map([...all("article.vc-clip")].map((n) => [n.__key, n]));
  const video = cards.get("c1").querySelector("video");
  resetJournal();
  send("clip_ready", { clip: "c4", file: "clips/c4.mp4", title: "Clip 4" }); flush();
  for (const id of ["recap", "c1", "c2", "c3", "c4"]) assert.equal([...all("article.vc-clip")].find((n) => n.__key === id), cards.get(id), id);
  assert.equal(cards.get("c1").querySelector("video"), video);
  assert.ok(cards.get("c4").querySelector("video"));
  assert.ok(!journal.log.some((x) => x === "removed ARTICLE"), journal.log.join("\n"));
});

test("a working clip's step changes its text, not its card", () => {
  send("progress", { stage: "render", clip: "c5", title: "Clip 5", done: 5, total: 5 }); flush();
  const card = [...all("article.vc-clip")].find((n) => n.__key === "c5");
  const inner = card.firstChild;
  resetJournal();
  send("progress", { stage: "render", clip: "c5", step: "video" }); flush();
  assert.equal(card.firstChild, inner);
  assert.match(card.textContent, /video/);
  assert.deepEqual(journal.log.filter((x) => x.startsWith("added") || x.startsWith("removed")), ["added LI"]);   // only its line in the feed
});

test("a rated episode rebuilds that episode only; the stages and numbers are the same nodes", () => {
  const eps = [...all("article.vc-ep")], stages = [...all("li.vc-stage")], stats = [...all("div.vc-stat")];
  resetJournal();
  send("episode_rated", { episode_id: "e1", status: "ok", title: "Good one", score: 80, verdict: "good" }); flush();
  const now = [...all("article.vc-ep")];
  assert.equal(now[0], eps[0]); assert.notEqual(now[1], eps[1]); assert.equal(now[2], eps[2]);
  assert.deepEqual([...all("li.vc-stage")], stages);
  assert.deepEqual([...all("div.vc-stat")], stats);
});

test("model calls: a new call on top, never more than twelve shown", () => {
  for (let i = 0; i < 12; i++) send("model_call", { purpose: "rating", model: "m", seconds: 1 });
  flush();
  const list = q("ul.vc-calls"), top = list.firstChild;
  resetJournal();
  send("model_call", { purpose: "fit", model: "m", seconds: 1 }); flush();
  assert.equal(list.children.length, 12);
  assert.equal(list.children[1], top);
  assert.deepEqual(quiet(), [2, 1]);      // the call and its line in the feed; the oldest call leaves
});

test("the widgets the person opened stay open", () => {
  for (const d of all("details")) assert.equal(d.open, true);
});
