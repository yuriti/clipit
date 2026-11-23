// SMTV's DOM helpers (V6, owner 22.11). The window and every tool's page use them, from app.js (the api object) or
// imported directly: no framework, no build step. Tested with node --test (web/tests/dom.test.mjs).

// tiny DOM helper: h("div.card#id", {attrs}, ...children)
export function h(tag, attrs, ...kids) {
  const m = tag.match(/^([a-z0-9]+)?((?:[.#][\w-]+)*)$/i);
  const el = document.createElement(m[1] || "div");
  for (const part of (m[2] || "").match(/[.#][\w-]+/g) || []) part[0] === "." ? el.classList.add(part.slice(1)) : (el.id = part.slice(1));
  if (attrs && (typeof attrs !== "object" || attrs instanceof Node || Array.isArray(attrs))) { kids.unshift(attrs); attrs = null; }
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "html") el.innerHTML = v;
    else if (k === "text") el.textContent = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid != null && kid !== false) el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  return el;
}
// --- one way the window changes (V6, owner 22.11): state → subscriptions by key → only the nodes that changed are
// touched. Nothing is rebuilt to show the same thing again, so focus, hover, selected text, open <details>, playing
// videos and scroll positions stay as they are by themselves.
// text(el, v): the text only when it differs; a lone text node is edited in place (one characterData change).
export function text(el, value) {
  const v = value == null ? "" : String(value), only = el.firstChild;
  if (only && only === el.lastChild && only.nodeType === 3) { if (only.data !== v) only.data = v; }
  else if (el.textContent !== v) el.textContent = v;
  return el;
}
// attr(el, name, v): set when it differs; null, undefined or false removes it
export function attr(el, name, value) {
  if (value == null || value === false) { if (el.hasAttribute(name)) el.removeAttribute(name); }
  else { const v = value === true ? "" : String(value); if (el.getAttribute(name) !== v) el.setAttribute(name, v); }
  return el;
}
// keyed(parent, items, {key, create, update, sig}): the children of `parent` follow `items`, one node per key. A new
// key gets create(item); a key that left is removed; the order is fixed by moving only the nodes out of place. A kept
// node gets update(node, item) when there is one; without update, a node whose sig(item) changed is built again (a
// block whose shape changes), and one whose sig is the same is left alone. `parent` belongs to keyed: other children go.
export function keyed(parent, items, { key, create, update = null, sig = null }) {
  const old = new Map();     // key → its nodes, in order (a key met twice keeps both of its nodes)
  for (const n of parent.childNodes) if (n.__key !== undefined) { if (!old.has(n.__key)) old.set(n.__key, []); old.get(n.__key).push(n); }
  const want = [];
  for (const item of items) {
    const k = key(item), s = sig ? sig(item) : undefined;
    let node = old.get(k)?.shift();
    if (node && !update && sig && node.__ksig !== s) node = null;     // its shape changed: built again in its place
    if (!node) { node = create(item); node.__key = k; if (update) update(node, item); }
    else if (update) update(node, item);
    node.__ksig = s;           // keyed's own mark: a region on the same node keeps its __sig
    want.push(node);
  }
  const keep = new Set(want);
  for (const n of [...parent.childNodes]) if (!keep.has(n)) n.remove();
  let ref = null;
  for (let i = want.length - 1; i >= 0; i--) {
    const n = want[i];
    if (n.parentNode !== parent || n.nextSibling !== ref) parent.insertBefore(n, ref);
    ref = n;
  }
  return parent;
}
// blocks(parent, [[key, sig, build], …]): a page made of blocks, each built again only when its sig changes (null
// entries are skipped). The usual draw() of a page that answers clicks and server data.
export function blocks(parent, list) {
  return keyed(parent, list.filter(Boolean), { key: (b) => b[0], sig: (b) => b[1] ?? null, create: (b) => b[2]() });
}
// region(el, sig, build): el's children are built again only when sig changes
export function region(el, sig, build) {
  if (el.__sig === sig && el.__built) return el;
  el.__sig = sig; el.__built = true;
  el.replaceChildren(...[build()].flat(Infinity).filter((x) => x != null && x !== false));
  return el;
}
export const sig = (...parts) => JSON.stringify(parts);


// --- signals (V6, owner 22.11): the state the page shows. A signal holds a value; an effect runs once and again
// whenever a signal it read changes; a computed is a value kept from other signals; batch makes several changes count
// as one, so each effect runs once after all of them. No Proxy: a value changed in place (a Map of clips) says so with
// touch(). Effects run in the order they were made; one that throws is logged and the others still run.
let running = null;              // the effect being run: the signals it reads, it depends on
let depth = 0, flushing = false;
const queue = new Set();
function flush() {
  if (flushing) return;
  flushing = true;
  try {
    for (let rounds = 0; queue.size; rounds++) {
      if (rounds > 100) { console.error("signals: effects keep changing what they read"); queue.clear(); break; }
      const list = [...queue];
      queue.clear();
      for (const e of list) if (e.alive) e.run();
    }
  } finally { flushing = false; }
}
export function signal(value) {
  const subs = new Set();
  return {
    get value() { if (running) { subs.add(running); running.deps.add(subs); } return value; },
    set value(v) { if (Object.is(v, value)) return; value = v; this.touch(); },
    get() { return this.value; },
    set(v) { this.value = v; },
    peek: () => value,                                   // read without depending on it
    touch() { for (const e of subs) queue.add(e); if (!depth) flush(); },   // the value changed in place
  };
}
export function effect(fn) {
  const e = {
    deps: new Set(), alive: true,
    run() {
      for (const subs of e.deps) subs.delete(e);
      e.deps.clear();
      const prev = running;
      running = e;
      try { fn(); } catch (err) { console.error(err); } finally { running = prev; }
    },
  };
  e.run();
  return () => { e.alive = false; queue.delete(e); for (const subs of e.deps) subs.delete(e); e.deps.clear(); };
}
export function computed(fn) {
  const out = signal(undefined);
  const stop = effect(() => { out.value = fn(); });
  return { get value() { return out.value; }, peek: out.peek, stop };
}
export function batch(fn) {
  depth++;
  try { return fn(); } finally { if (!--depth) flush(); }
}

// bindings: an effect that keeps one node's text or one attribute equal to fn(); returns the stop function
export const bindText = (el, fn) => effect(() => text(el, fn()));
export const bindAttr = (el, name, fn) => effect(() => attr(el, name, fn()));
