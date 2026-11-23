// A small DOM for the window's JS tests (V6): only what dom.js and the pages' drawing use, and a journal of every change
// made to the document (what a MutationObserver would see: nodes added and removed, texts, attributes). No dependency:
// the helpers touch a handful of DOM calls, and a fake that records each of them proves «nothing changed» exactly.

export const journal = { added: 0, removed: 0, text: 0, attr: 0, log: [] };
export function resetJournal() { Object.assign(journal, { added: 0, removed: 0, text: 0, attr: 0, log: [] }); }
const note = (node, kind, what) => {
  if (!node.isConnected) return;
  journal[kind]++;
  journal.log.push(kind + " " + what);
};

export class Node {
  constructor(type, name) { this.nodeType = type; this.nodeName = name; this.parentNode = null; this.childNodes = []; this.listeners = {}; }
  get firstChild() { return this.childNodes[0] || null; }
  get lastChild() { return this.childNodes[this.childNodes.length - 1] || null; }
  get nextSibling() { const p = this.parentNode; return p ? p.childNodes[p.childNodes.indexOf(this) + 1] || null : null; }
  get previousSibling() { const p = this.parentNode; return p ? p.childNodes[p.childNodes.indexOf(this) - 1] || null : null; }
  get isConnected() { let n = this; while (n.parentNode) n = n.parentNode; return n === globalThis.document; }
  get children() { return this.childNodes.filter((n) => n.nodeType === 1); }
  get firstElementChild() { return this.children[0] || null; }
  contains(n) { for (; n; n = n.parentNode) if (n === this) return true; return false; }
  insertBefore(node, ref) {
    if (node.nodeType === 11) { for (const k of [...node.childNodes]) this.insertBefore(k, ref); return node; }
    if (node.parentNode) node.remove();
    const i = ref ? this.childNodes.indexOf(ref) : -1;
    if (ref && i < 0) throw new Error("insertBefore: ref is not a child");
    if (i < 0) this.childNodes.push(node); else this.childNodes.splice(i, 0, node);
    node.parentNode = this;
    note(node, "added", node.nodeName);
    return node;
  }
  appendChild(node) { return this.insertBefore(node, null); }
  append(...nodes) { for (const n of nodes) this.appendChild(typeof n === "string" ? globalThis.document.createTextNode(n) : n); }
  remove() {
    const p = this.parentNode;
    if (!p) return;
    note(this, "removed", this.nodeName);
    p.childNodes.splice(p.childNodes.indexOf(this), 1);
    this.parentNode = null;
  }
  replaceChildren(...nodes) { for (const n of [...this.childNodes]) n.remove(); this.append(...nodes); }
  replaceWith(n) { this.parentNode.insertBefore(n, this); this.remove(); }
  get textContent() { return this.childNodes.map((n) => n.textContent).join(""); }
  set textContent(v) { this.replaceChildren(); if (v !== "") this.append(String(v)); }
  addEventListener(type, fn) { (this.listeners[type] ||= []).push(fn); }
  removeEventListener(type, fn) { this.listeners[type] = (this.listeners[type] || []).filter((x) => x !== fn); }
  dispatch(type, extra = {}) {
    const e = { type, target: this, currentTarget: this, preventDefault() {}, stopPropagation() {}, ...extra };
    for (const fn of this.listeners[type] || []) fn(e);
    this["on" + type]?.(e);
  }
  click() { this.dispatch("click"); }
}

export class Text extends Node {
  constructor(data) { super(3, "#text"); this._data = data; }
  get data() { return this._data; }
  set data(v) { this._data = String(v); note(this, "text", JSON.stringify(this._data)); }
  get textContent() { return this._data; }
  set textContent(v) { this.data = v; }
}

class ClassList {
  constructor(el) { this.el = el; }
  get list() { return (this.el.getAttribute("class") || "").split(/\s+/).filter(Boolean); }
  contains(c) { return this.list.includes(c); }
  add(...cs) { const l = this.list; for (const c of cs) if (!l.includes(c)) l.push(c); this.el.setAttribute("class", l.join(" ")); }
  remove(...cs) { if (cs.some((c) => this.contains(c))) this.el.setAttribute("class", this.list.filter((c) => !cs.includes(c)).join(" ")); }
  toggle(c, on = !this.contains(c)) { if (on) { if (!this.contains(c)) this.add(c); } else this.remove(c); return on; }
}

export class Element extends Node {
  constructor(tag) { super(1, tag.toUpperCase()); this.tagName = this.nodeName; this.attrs = new Map(); this.classList = new ClassList(this); this.style = {}; }
  getAttribute(n) { return this.attrs.has(n) ? this.attrs.get(n) : null; }
  hasAttribute(n) { return this.attrs.has(n); }
  setAttribute(n, v) { this.attrs.set(n, String(v)); note(this, "attr", n); }
  removeAttribute(n) { if (this.attrs.delete(n)) note(this, "attr", n); }
  get className() { return this.getAttribute("class") || ""; }
  set className(v) { this.setAttribute("class", v); }
  get id() { return this.getAttribute("id") || ""; }
  set id(v) { this.setAttribute("id", v); }
  get hidden() { return this.hasAttribute("hidden"); }
  set hidden(v) { if (v) this.setAttribute("hidden", ""); else this.removeAttribute("hidden"); }
  get open() { return this.hasAttribute("open"); }
  set open(v) { if (v) this.setAttribute("open", ""); else this.removeAttribute("open"); }
  get title() { return this.getAttribute("title") || ""; }
  set title(v) { this.setAttribute("title", v); }
  get dataset() {
    const el = this;
    const name = (k) => "data-" + k.replace(/[A-Z]/g, (c) => "-" + c.toLowerCase());
    return new Proxy({}, { get: (_, k) => el.getAttribute(name(k)) ?? undefined, set: (_, k, v) => { el.setAttribute(name(k), v); return true; } });
  }
  set innerHTML(v) { this.replaceChildren(); this._html = v; }
  get innerHTML() { return this._html || ""; }
  setSelectionRange() {}
  focus() {}
  matches(sel) {   // «tag», «.class», «tag.class», «[attr]»
    return sel.split(",").some((one) => {
      const m = one.trim().match(/^([a-z0-9]*)((?:\.[\w-]+)*)(?:\[([\w-]+)\])?$/i);
      if (!m) throw new Error("fakedom: selector " + one);
      return (!m[1] || m[1].toUpperCase() === this.nodeName) && (m[2].split(".").filter(Boolean).every((c) => this.classList.contains(c))) && (!m[3] || this.hasAttribute(m[3]));
    });
  }
  querySelectorAll(sel) {
    const out = [];
    const walk = (n) => { for (const k of n.children) { if (k.matches(sel)) out.push(k); walk(k); } };
    walk(this);
    return out;
  }
  querySelector(sel) { return this.querySelectorAll(sel)[0] || null; }
}

class Document extends Element {
  constructor() { super("#document"); this.documentElement = new Element("html"); this.body = new Element("body"); this.appendChild(this.documentElement); this.documentElement.appendChild(this.body); this.title = ""; }
  createElement(tag) { return new Element(tag); }
  createElementNS(_, tag) { return new Element(tag); }
  createTextNode(text) { return new Text(String(text)); }
  createDocumentFragment() { const f = new Element("#fragment"); f.nodeType = 11; return f; }
  get isConnected() { return true; }
}

export function install() {
  globalThis.Node = Node;
  globalThis.document = new Document();
  const mem = new Map();
  globalThis.localStorage = { getItem: (k) => (mem.has(k) ? mem.get(k) : null), setItem: (k, v) => mem.set(k, String(v)), removeItem: (k) => mem.delete(k), clear: () => mem.clear() };
  const frames = [];
  globalThis.requestAnimationFrame = (fn) => { frames.push(fn); return frames.length; };
  globalThis.cancelAnimationFrame = () => {};
  globalThis.performance ||= { now: () => Date.now() };
  return { flush: () => { while (frames.length) frames.splice(0).forEach((fn) => fn(performance.now())); } };
}
