// The window's DOM helpers (V6): a list follows its items by key and touches only what changed. Run: node --test
import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { install, journal, resetJournal } from "./fakedom.mjs";

install();
const { h, text, attr, keyed, blocks, region, sig } = await import("../../src/smtv/web/dom.js");

let root;
beforeEach(() => { root = h("div"); document.body.replaceChildren(root); resetJournal(); });

const rows = (parent, items, made = []) => keyed(parent, items, {
  key: (x) => x.id,
  create: (x) => { made.push(x.id); return h("li", h("b"), h("small")); },
  update: (li, x) => { text(li.firstChild, x.title); attr(li, "class", x.state); },
});
const ids = (parent) => parent.children.map((n) => n.__key);

test("text changes a lone text node in place, and nothing when the text is the same", () => {
  const b = h("b", "1:00"); root.append(b); resetJournal();
  text(b, "1:00");
  assert.deepEqual([journal.added, journal.removed, journal.text], [0, 0, 0]);
  text(b, "1:01");
  assert.deepEqual([journal.added, journal.removed, journal.text], [0, 0, 1]);
  assert.equal(b.textContent, "1:01");
  const empty = h("span"); root.append(empty); text(empty, "now"); assert.equal(empty.textContent, "now");
});

test("attr writes only a different value; false and null remove", () => {
  const el = h("div"); root.append(el); resetJournal();
  attr(el, "hidden", false); attr(el, "class", "a"); attr(el, "class", "a"); attr(el, "hidden", true); attr(el, "hidden", true);
  assert.equal(journal.attr, 2);
  attr(el, "hidden", null); assert.equal(el.hasAttribute("hidden"), false);
});

test("the same items again touch nothing", () => {
  const list = h("ol"); root.append(list);
  const items = [{ id: "a", title: "A", state: "done" }, { id: "b", title: "B", state: "active" }];
  rows(list, items); resetJournal();
  rows(list, items.map((x) => ({ ...x })));
  assert.deepEqual([journal.added, journal.removed, journal.text, journal.attr], [0, 0, 0, 0]);
});

test("a new item on top adds one node; the others are the same nodes", () => {
  const list = h("ol"); root.append(list);
  rows(list, [{ id: "a", title: "A" }, { id: "b", title: "B" }]);
  const [a, b] = list.children; resetJournal();
  const made = [];
  rows(list, [{ id: "n", title: "N" }, { id: "a", title: "A" }, { id: "b", title: "B" }], made);
  assert.deepEqual(made, ["n"]);
  assert.deepEqual(ids(list), ["n", "a", "b"]);
  assert.equal(list.children[1], a); assert.equal(list.children[2], b);
  assert.deepEqual([journal.added, journal.removed], [1, 0]);
});

test("a gone item is removed, a changed one is edited in place", () => {
  const list = h("ol"); root.append(list);
  rows(list, [{ id: "a", title: "A" }, { id: "b", title: "B" }, { id: "c", title: "C" }]);
  const c = list.children[2]; resetJournal();
  rows(list, [{ id: "a", title: "A" }, { id: "c", title: "C, renamed" }]);
  assert.deepEqual(ids(list), ["a", "c"]);
  assert.equal(list.children[1], c);
  assert.equal(c.firstChild.textContent, "C, renamed");
  assert.deepEqual([journal.added, journal.removed, journal.text], [0, 1, 1]);
});

test("a new order moves only the nodes out of place", () => {
  const list = h("ol"); root.append(list);
  rows(list, ["a", "b", "c", "d"].map((id) => ({ id, title: id })));
  const before = new Map(list.children.map((n) => [n.__key, n])); resetJournal();
  rows(list, ["b", "c", "d", "a"].map((id) => ({ id, title: id })));     // the first goes last: one move
  assert.deepEqual(ids(list), ["b", "c", "d", "a"]);
  assert.deepEqual([journal.added, journal.removed], [1, 1]);
  for (const n of list.children) assert.equal(n, before.get(n.__key));
  resetJournal();
  rows(list, ["d", "c", "b", "a"].map((id) => ({ id, title: id })));
  assert.deepEqual(ids(list), ["d", "c", "b", "a"]);
  for (const n of list.children) assert.equal(n, before.get(n.__key));
});

test("without update, a node is built again only when its sig changed", () => {
  const list = h("div"); root.append(list);
  const draw = (eps) => keyed(list, eps, { key: (e) => e.id, sig: (e) => sig(e.verdict), create: (e) => h("article", e.verdict || "…") });
  draw([{ id: 1 }, { id: 2 }]);
  const [one, two] = list.children; resetJournal();
  draw([{ id: 1 }, { id: 2, verdict: "good" }]);
  assert.equal(list.children[0], one);
  assert.notEqual(list.children[1], two);
  assert.equal(list.children[1].textContent, "good");
  assert.deepEqual([journal.added, journal.removed], [1, 1]);
});

test("keyed owns its parent: a placeholder without a key goes", () => {
  const list = h("div", h("div.faint", "…")); root.append(list);
  rows(list, [{ id: "a", title: "A" }]);
  assert.deepEqual(ids(list), ["a"]);
});

test("blocks: static blocks stay, a block with a new sig is rebuilt in its place, null entries are skipped", () => {
  let n = 0;
  const draw = (busy, count) => blocks(root, [["lead", null, () => h("p", "lead " + ++n)], busy ? ["busy", null, () => h("div", "busy")] : null, ["list", count, () => h("ul", "x" + count)]]);
  draw(false, 1);
  const lead = root.children[0];
  draw(true, 1);
  assert.equal(root.children[0], lead);
  assert.deepEqual(ids(root), ["lead", "busy", "list"]);
  const list = root.children[2];
  draw(true, 2);
  assert.notEqual(root.children[2], list);
  assert.equal(root.children[2].textContent, "x2");
  assert.equal(n, 1);
});

test("region builds again only for a new sig; lists and nulls in what it builds are fine", () => {
  const box = h("div"); root.append(box);
  let n = 0;
  region(box, "a", () => [h("b", String(++n)), null, [h("i")]]);
  const first = box.firstChild; resetJournal();
  region(box, "a", () => h("b", String(++n)));
  assert.equal(box.firstChild, first); assert.equal(journal.added + journal.removed, 0);
  region(box, "b", () => h("b", String(++n)));
  assert.equal(box.textContent, "2");
});

test("focus, open details and a playing video survive an update because their nodes stay", () => {
  const list = h("div"); root.append(list);
  const draw = (items) => keyed(list, items, {
    key: (x) => x.id,
    create: () => h("details", h("summary"), h("video")),
    update: (d, x) => text(d.firstChild, x.title),
  });
  draw([{ id: "c1", title: "one" }]);
  const d = list.firstChild; d.open = true; const v = d.querySelector("video");
  draw([{ id: "c0", title: "zero" }, { id: "c1", title: "one, more" }]);
  assert.equal(list.children[1], d); assert.equal(d.open, true); assert.equal(d.querySelector("video"), v);
});

test("a key met twice gets two nodes, not one node shown once", () => {
  const list = h("ol"); root.append(list);
  rows(list, [{ id: "a", title: "A" }, { id: "a", title: "A again" }]);
  assert.equal(list.children.length, 2);
  assert.deepEqual(list.children.map((n) => n.firstChild.textContent), ["A", "A again"]);
  const made = [], nodes = [...list.children];
  rows(list, [{ id: "a", title: "A" }, { id: "a", title: "A again" }], made);
  assert.deepEqual(made, []);                                    // both nodes kept on the next pass
  assert.deepEqual(list.children, nodes);
});

test("every name app.js takes from dom.js is exported by it (else the window would not load)", async () => {
  const { readFile } = await import("node:fs/promises");
  const src = await readFile(new URL("../../src/smtv/web/app.js", import.meta.url), "utf8");
  const dom = await import("../../src/smtv/web/dom.js");
  const names = [...src.matchAll(/import \{([^}]+)\} from "\.\/dom\.js"/g)].flatMap((m) => m[1].split(",").map((x) => x.trim()).filter(Boolean));
  assert.ok(names.length >= 10, names.join(","));
  for (const n of names) assert.ok(n in dom, n);
});

// --- signals
const { signal, computed, effect, batch } = await import("../../src/smtv/web/dom.js");

test("an effect runs once at once and again only when a signal it read changes", () => {
  const a = signal(1), b = signal(10), seen = [];
  const stop = effect(() => seen.push(a.value));
  b.value = 11; a.value = 1;             // not read / the same value: nothing
  a.value = 2;
  assert.deepEqual(seen, [1, 2]);
  stop(); a.value = 3;
  assert.deepEqual(seen, [1, 2]);
});

test("batch runs each effect once after all the changes", () => {
  const a = signal(1), b = signal(2), seen = [];
  effect(() => seen.push(a.value + b.value));
  batch(() => { a.value = 5; b.value = 6; a.value = 7; });
  assert.deepEqual(seen, [3, 13]);
});

test("an effect follows only what it read last time (a branch not taken is not a dependency)", () => {
  const on = signal(false), x = signal(1), seen = [];
  effect(() => seen.push(on.value ? x.value : "off"));
  x.value = 2;
  on.value = true; x.value = 3; on.value = false; x.value = 4;
  assert.deepEqual(seen, ["off", 2, 3, "off"]);
});

test("touch tells a value changed in place; peek reads without depending", () => {
  const clips = signal(new Map()), seen = [], other = signal(0);
  effect(() => seen.push(clips.value.size + other.peek()));
  clips.peek().set("c1", {}); clips.touch();
  other.value = 100;
  assert.deepEqual(seen, [0, 1]);
});

test("a computed keeps its value from other signals; an effect reading it follows it", () => {
  const first = signal(10), now = signal(15), seen = [];
  const elapsed = computed(() => now.value - first.value);
  effect(() => seen.push(elapsed.value));
  now.value = 16; now.value = 17;
  assert.deepEqual(seen, [5, 6, 7]);
});

test("an effect that throws does not stop the others", () => {
  const a = signal(0), seen = [];
  const err = console.error; console.error = () => {};
  effect(() => { if (a.value) throw new Error("x"); });
  effect(() => seen.push(a.value));
  a.value = 1;
  console.error = err;
  assert.deepEqual(seen, [0, 1]);
});

test("a region on a node that keyed keeps is not built again by keyed's own pass", () => {
  const list = h("div"); root.append(list);
  let n = 0;
  const draw = () => keyed(list, [{ id: "c1" }], { key: (x) => x.id, create: () => h("article") });
  draw();
  const card = list.firstChild;
  region(card, "ready", () => h("video", String(++n)));
  draw();
  region(card, "ready", () => h("video", String(++n)));
  assert.equal(n, 1);
});

test("get() and set() are the same as .value", () => {
  const a = signal(1), seen = [];
  effect(() => seen.push(a.get()));
  a.set(1); a.set(2);
  assert.deepEqual(seen, [1, 2]);
  assert.equal(a.value, 2);
});

test("an effect that keeps changing what it reads is stopped, not looped forever", () => {
  const a = signal(0);
  const err = console.error; let said = "";
  console.error = (m) => { said = String(m); };
  effect(() => { a.value = a.value + 1; });
  a.value = 100;
  console.error = err;
  assert.match(said, /keep changing/);
  assert.ok(a.peek() < 300, String(a.peek()));
});

test("bindText and bindAttr follow their signal and stop when asked", async () => {
  const { bindText, bindAttr } = await import("../../src/smtv/web/dom.js");
  const el = h("b"); root.append(el);
  const s = signal("1:00"), cls = signal("a");
  const stop = bindText(el, () => s.value); bindAttr(el, "class", () => cls.value);
  resetJournal();
  s.value = "1:01"; cls.value = "b";
  assert.equal(el.textContent, "1:01"); assert.equal(el.className, "b");
  assert.deepEqual([journal.added, journal.removed, journal.text, journal.attr], [0, 0, 1, 1]);
  stop(); s.value = "1:02";
  assert.equal(el.textContent, "1:01");
});
