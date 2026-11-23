// VodCut's places in SMTV's window (smtv_core.tool.Page): the form of a new request (mountNew) and an open request,
// watched live from its events (mountJob). The list of requests, the rail and Settings are the window's own.

const STAGES = ["audio", "speech", "scan", "rating", "pick", "fit", "render", "recap"];
const WEIGHT = { audio: 10, speech: 34, scan: 16, rating: 10, pick: 2, fit: 3, render: 28, recap: 40 };
const STAGE_OF = { language: "speech", model: "speech" };


const I = {
  ext: '<path d="M14 5h5v5M19 5l-8 8M18 14v4a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4"/>',
  pause: '<rect x="7" y="5.5" width="3.2" height="13" rx="1.2"/><rect x="13.8" y="5.5" width="3.2" height="13" rx="1.2"/>',
  heart: '<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z"/>',
  left: '<path d="m15 18-6-6 6-6"/>', right: '<path d="m9 18 6-6-6-6"/>',
  playRound: '<path d="M8.5 6.2v11.6a1 1 0 0 0 1.5.86l9.3-5.8a1 1 0 0 0 0-1.72L10 5.34a1 1 0 0 0-1.5.86z" fill="currentColor" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  up: '<path d="M12 19V5M6 11l6-6 6 6"/>',
  copy: '<rect x="8" y="8" width="12" height="12" rx="2.5"/><path d="M16 8V6.5A2.5 2.5 0 0 0 13.5 4h-7A2.5 2.5 0 0 0 4 6.5v7A2.5 2.5 0 0 0 6.5 16H8"/>',
  chev: '<path d="m9 6 6 6-6 6"/>',
  play: '<path d="M8 5.5v13l10.5-6.5z" fill="currentColor" stroke="none"/>', file: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>',
  link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
  down: '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>', stop: '<rect x="7" y="7" width="10" height="10" rx="2"/>', redo: '<path d="M4 12a8 8 0 0 1 14-5.3L20 9M20 4v5h-5M20 12a8 8 0 0 1-14 5.3L4 15M4 20v-5h5"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>', spark: '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
  chip: '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
  film: '<rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/>',
  image: '<rect x="3.5" y="4.5" width="17" height="15" rx="2.5"/><circle cx="9" cy="10" r="1.8"/><path d="m20.5 16-5-5-8.5 8.5"/>',
  tv: '<rect x="3" y="5" width="18" height="12.5" rx="2.5"/><path d="M8.5 21h7M12 17.5V21"/>',
  wave: '<path d="M3 12h2M7 8v8M11 5v14M15 9v6M19 7v10M21 12h0"/>', search: '<circle cx="11" cy="11" r="6.5"/><path d="m20 20-4.2-4.2"/>',
  star: '<path d="m12 3.5 2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9 6.8 19.6l1-5.8-4.3-4.1 5.9-.9z"/>', filter: '<path d="M4 5h16l-6 7.5V19l-4 1.5v-8z"/>',
  scissors: '<circle cx="6" cy="6.5" r="2.5"/><circle cx="6" cy="17.5" r="2.5"/><path d="M8 8.2 20 18M8 15.8 20 6"/>', alert: '<circle cx="12" cy="12" r="8.5"/><path d="M12 8v4.5M12 16v.2"/>',
  eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/>',
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>', crop: '<path d="M7 3v14h14M3 7h14v14"/>', brain: '<path d="M9 4.5a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 6 1V6a2.5 2.5 0 0 0-3-1.5ZM15 4.5a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-6 1"/>',
};
const STAGE_ICON = { audio: I.wave, speech: I.chip, scan: I.search, rating: I.star, pick: I.filter, fit: I.crop, render: I.scissors, recap: I.tv };



// YouTube asked to sign in (the error carries [youtube_sign_in]): say why in plain words; VodCut never reads the browser.
// A link without a StreamMoment account ([streammoment_sign_in], stage 23): the way to sign in, or a file.
let API = null;
function signInOr(message, plain) {
  if (API && String(message).includes("streammoment_sign_in"))
    return [API.h("span", API.t("sm_sign_in")), " ", API.h("button.btn.btn-sm", { type: "button", onclick: () => API.openSettings("account") }, API.t("sm_sign_in_btn"))];
  if (!API || !String(message).includes("youtube_sign_in")) return [plain];
  return [API.h("span", API.t("yt_sign_in"))];
}

// The form of a new request (owner, 20.11): one field in the middle and nothing else — a link or a path, a file button,
// «Start». The language is chosen by itself; the other settings are gone from here. A file dropped anywhere in the
// window while this page is open is uploaded and started at once.
export function mountNew(root, api) {
  API = api;
  const { t, h, icon, fmt, getJSON, postJSON, text, region, sig } = api;
  const tool = api.tool.name;

  const src = h("input.vc-src", { type: "text", placeholder: t("source_ph"), autocomplete: "off", spellcheck: "false", "aria-label": t("source_ph") });
  const fileInput = h("input", { type: "file", accept: "video/*,audio/*,.mkv,.flv,.ts", hidden: true });
  // In SMTV's own window the system dialog gives the file's path: the video is read where it lies, never copied
  // (a 10 GB recording would take 10 GB more). In a browser or on a phone it is uploaded as before (decision 16).
  const pickFile = async () => {
    try {
      const r = await postJSON("/api/pick-file", {});
      if (r.path) { src.value = r.path; await start(); }
    } catch (e) {
      if (e.code === "no_native" || e.status === 404) fileInput.click(); else api.toast(e.message, "bad");
    }
  };
  const fileBtn = h("button.vc-round", { type: "button", title: t("file"), "aria-label": t("file"), onclick: pickFile }, icon(I.file));
  const startBtn = h("button.vc-round.vc-go", { type: "button", title: t("start"), "aria-label": t("start"), disabled: true }, icon(I.up));
  const est = h("div.vc-est", { "aria-live": "polite" });
  // the line under the field: a plain text changes in place (an upload says its percent many times a second)
  const say = (line) => { region(est, line == null ? "" : "line", () => line == null ? [] : h("span")); if (line != null) text(est.firstChild, line); };
  // under the field, at the placeholder's own left edge: what can go into it. A link's start goes into the field;
  // «File» opens the picker. While the field has text, the estimate takes this line's place.
  const prefill = (text) => { src.value = text; src.focus(); src.setSelectionRange(text.length, text.length); scheduleEstimate(); };
  const hints = h("div.vc-hints",
    h("button.vc-hint", { type: "button", onclick: () => prefill("https://www.twitch.tv/videos/") }, "Twitch"),
    h("button.vc-hint", { type: "button", onclick: () => prefill("https://www.youtube.com/watch?v=") }, "YouTube"),
    h("button.vc-hint", { type: "button", onclick: () => fileInput.click() }, t("hint_file")));
  const under = h("div.vc-under", hints, est);
  root.append(h("div.vc-new", h("div.vc-field", src, fileInput, fileBtn, startBtn), under));
  setTimeout(() => src.focus(), 0);

  let estTimer = null, estSeq = 0, busy = false;
  const fields = () => ({ source: src.value.trim(), language: "auto" });
  const sync = () => { startBtn.disabled = busy || !src.value.trim(); under.classList.toggle("filled", !!src.value.trim() || busy); };
  const scheduleEstimate = () => { sync(); clearTimeout(estTimer); estTimer = setTimeout(runEstimate, 650); };
  async function runEstimate() {     // one quiet line under the field: how long, how much
    const f = fields();
    if (!f.source) { say(null); return; }
    const seq = ++estSeq;
    say(t("estimating"));
    try {
      const e = await postJSON(`/api/tools/${tool}/estimate`, f);
      if (seq !== estSeq) return;
      say([e.title || null, t("est_rec", { h: fmt.hours(e.duration_s) }), t("est_clips", { n: e.clips }), t("estimate", { t: fmt.dur(e.seconds) })]
        .filter(Boolean).join(" · "));
    } catch (err) {
      if (seq === estSeq) region(est, sig("error", err.message), () => signInOr(err.message, h("span.vc-est-err", err.message)));
    }
  }
  src.addEventListener("input", scheduleEstimate);
  src.addEventListener("keydown", (e) => { if (e.key === "Enter") start(); });

  async function sendFile(file) {
    busy = true; sync(); fileBtn.disabled = true;
    try {
      const r = await api.upload(file, (p) => say(t("uploading", { p: Math.round(p * 100) })));
      src.value = r.path;
      busy = false;
      await start();                   // a file is started right away
    } catch (e) { api.toast(e.message, "bad"); say(null); }
    busy = false; sync(); fileBtn.disabled = false;
  }
  fileInput.onchange = () => fileInput.files[0] && sendFile(fileInput.files[0]);

  // the whole window takes a dropped file while this page is open
  const veil = h("div.vc-veil", h("div", icon(I.file), h("b", t("drop_here"))));
  let depth = 0;
  const hasFiles = (e) => [...(e.dataTransfer?.types || [])].includes("Files");
  const enter = (e) => { if (!hasFiles(e)) return; e.preventDefault(); if (depth++ === 0) document.body.append(veil); };
  const over = (e) => { if (hasFiles(e)) { e.preventDefault(); e.dataTransfer.dropEffect = "copy"; } };
  const leave = (e) => { if (hasFiles(e) && --depth <= 0) { depth = 0; veil.remove(); } };
  const dropped = (e) => {
    if (!hasFiles(e)) return;
    e.preventDefault(); depth = 0; veil.remove();
    const f = e.dataTransfer.files[0];
    if (f && !busy) sendFile(f);
  };
  document.addEventListener("dragenter", enter); document.addEventListener("dragover", over);
  document.addEventListener("dragleave", leave); document.addEventListener("drop", dropped);

  async function start() {
    const f = fields();
    if (!f.source || busy) { src.focus(); return; }
    busy = true; sync();
    try {
      const job = await postJSON(`/api/tools/${tool}/jobs`, f);
      api.refreshRequests();
      api.openRequest(tool, job.id);
    } catch (e) {
      api.toast(e.code === "busy" ? t("busy", { j: e.message.split(": ").pop() }) : e.message, "bad");
    }
    busy = false; sync();
  }
  startBtn.onclick = start;

  return {
    close: () => {
      clearTimeout(estTimer); veil.remove();
      document.removeEventListener("dragenter", enter); document.removeEventListener("dragover", over);
      document.removeEventListener("dragleave", leave); document.removeEventListener("drop", dropped);
    },
  };
}

// An open request: the whole job live from its events (stages, numbers, clips, episodes, the feed, model calls).
export function mountJob(root, api, id) {
  API = api;
  const { t, h, icon, fmt, getJSON, postJSON, text, attr, keyed, region, sig, signal, effect, batch } = api;
  const tool = api.tool.name;
  root.classList.add("vc-job");

  // ---------- one job, live
  // S is the job folded from its events; each part of the page has a signal that apply() touches when the part changed,
  // and the drawing of that part is an effect that reads it (V6, owner 22.11). The clock is a signal of its own.
  let S = null, closeStream = null, raf = 0, clock = 0, seq = 0, pending = [], effects = [];
  const PARTS = ["head", "stages", "stats", "episodes", "model", "feed", "clips", "recap"];
  let P = {}, clipSigs = new Map();
  const now = signal(Date.now() / 1000);
  function changed(...names) {
    for (const n of names) {
      if (n.startsWith("clip:")) { const id = n.slice(5); if (!clipSigs.has(id)) clipSigs.set(id, signal(0)); clipSigs.get(id).touch(); }
      else P[n].touch();
    }
  }
  const clipSig = (id) => { if (!clipSigs.has(id)) clipSigs.set(id, signal(0)); return clipSigs.get(id); };

  function fresh(id) {
    return { id, info: {}, status: "new", running: false, conn: "open", stages: {}, current: null, progress: {}, episodes: new Map(), clips: new Map(), fitted: new Map(),
      model: { calls: 0, seconds: 0, tin: 0, tout: 0, cost: 0, costKnown: false, errors: 0, list: [] }, feed: [], analysis: null, render: null,
      error: null, cancelled: false, first: null, last: null, lastProgressKey: null, recap: { state: "none" } };
  }

  function stageDone(name) {
    const st = S.stages[name];
    if (st?.state === "done") return;
    S.stages[name] = { ...(st || {}), state: "done", t1: st?.t1 || S.last };
  }

  function apply(e) {
    const d = e.data || {};
    S.first ??= e.t; S.last = e.t;
    const type = e.type;
    if (type === "source_ready") {        // what the request is about: title, channel, picture, length, link or file
      S.info = { ...S.info, ...d, source: d.source || S.info.source };
      changed("head");
    } else if (type === "stage") {
      if (d.source && !S.info.source) S.info.source = d.source;      // the link is known from the very first event
      const name = STAGE_OF[d.name] || d.name;
      const idx = STAGES.indexOf(name);
      if (idx >= 0) {
        for (const prev of STAGES.slice(0, idx)) {   // a later stage began: the earlier ones are done, in this run or in an earlier one
          if (S.stages[prev]?.state === "active") S.stages[prev] = { ...S.stages[prev], state: "done", t1: e.t };
          else if (!S.stages[prev]) S.stages[prev] = { state: "done" };
        }
        const keep = S.stages[name]?.t0 && S.stages[name].state === "active" ? S.stages[name].t0 : e.t;
        S.stages[name] = { ...(S.stages[name] || {}), state: "active", t0: keep, t1: null, data: { ...(S.stages[name]?.data || {}), ...d } };
        S.current = name;
        if (name === "audio" || name === "render") { S.error = null; S.cancelled = false; }
        if (name === "recap") { S.recap = { state: "working", step: "story" }; S.progress.recap = 0; changed("recap"); }
      }
      changed("stages", "head");
    } else if (type === "progress") {
      const name = STAGE_OF[d.stage] || d.stage;
      if (d.stage === "download") { S.download = d; changed("stages"); }
      else if (name === "audio") { S.progress.audio = d; S.download = null; stageDone("audio"); }
      else if (name === "speech") S.progress.speech = d.stage === "model" ? 0 : d.percent / 100;
      else if (name === "scan" || name === "rating" || name === "fit") S.progress[name] = d.total ? d.done / d.total : 0, S.progress[name + "_n"] = [d.done, d.total];
      else if (name === "recap") { S.recap = { ...S.recap, state: "working", step: d.step, done: d.done, total: d.total }; S.progress.recap = recapFraction(d); changed("recap"); }
      else if (name === "render") {
        if (d.title) { S.progress.render = [d.done, d.total]; const c = clipOf(d.clip, { title: d.title }); c.status = "working"; c.step = "video"; changed("clip:" + d.clip); }
        else if (d.step) { const c = clipOf(d.clip); c.status = "working"; c.step = d.step === "frames" && c.frames ? "layout" : d.step; changed("clip:" + d.clip); }
      }
      changed("stages");
    } else if (type === "episode_found") {
      const ep = S.episodes.get(d.episode_id) || {}; S.episodes.set(d.episode_id, { ...ep, found: d, id: d.episode_id, start: d.start_s, end: d.end_s, isNew: true });
      changed("episodes", "stats");
    } else if (type === "episode_rated") {
      const ep = S.episodes.get(d.episode_id) || { id: d.episode_id }; S.episodes.set(d.episode_id, { ...ep, rated: d, isNew: true });
      changed("episodes", "stats");
    } else if (type === "model_call") {
      const m = S.model; m.calls++; m.seconds += d.seconds || 0; m.tin += d.tokens_in || 0; m.tout += d.tokens_out || 0;
      if (d.cost_usd != null) { m.cost += d.cost_usd; m.costKnown = true; }
      if (d.error) m.errors++;
      m.list.unshift({ ...d, t: e.t, id: ++seq }); if (m.list.length > 60) m.list.pop();
      changed("model", "stats");
    } else if (type === "layout_chosen") {
      const c = clipOf(d.clip); c.layout = d.mode; c.layoutBy = d.by; if (d.frames) c.frames = d.frames; c.step = "layout_done"; changed("clip:" + d.clip);
    } else if (type === "ads_found") {
      const c = clipOf(d.clip); c.ads = d.count; c.adsBy = d.by; changed("clip:" + d.clip);
    } else if (type === "clip_reviewed") {
      clipOf(d.clip).critic = d; changed("clip:" + d.clip);
    } else if (type === "clip_ready") {
      const c = clipOf(d.clip, d); Object.assign(c, { status: "ready", file: d.file, title: d.title || c.title, layout: d.layout || c.layout, ads: d.ads_blurred ?? c.ads,
        bleeps: d.bleeps, loudness: d.loudness, start: d.start_s ?? c.start, end: d.end_s ?? c.end, fresh: !d.existing, critic: d.critic || c.critic });
      changed("clip:" + d.clip, "stats");
    } else if (type === "clip_fitted") {
      S.fitted.set(d.clip, d);
      const c = clipOf(d.clip); c.start = d.after.start_s; c.end = d.after.end_s; c.duration = d.after.end_s - d.after.start_s; c.fit = d;
      changed("clip:" + d.clip, "stages");
    } else if (type === "recap_ready") {
      S.recap = { state: "ready", data: d, fresh: !d.existing }; stageDone("recap"); changed("recap", "stages");
    } else if (type === "recap_failed") {
      S.recap = { state: "failed", error: d.error }; if (S.stages.recap) S.stages.recap.state = "failed"; changed("recap", "stages");
    } else if (type === "clip_failed") {
      const c = clipOf(d.clip, d); c.status = "failed"; c.error = d.error; changed("clip:" + d.clip, "stats");
    } else if (type === "done") {
      if (d.stage === "analysis") {
        S.analysis = d; for (const s of ["audio", "speech", "scan", "rating", "pick"]) stageDone(s); if (S.stages.fit) stageDone("fit");
        for (const c of d.clips || []) { const x = clipOf(c.id, c); x.score = c.score; x.start = c.start_s; x.end = c.end_s; x.duration = c.duration_s; }
        for (const c of d.clips || []) for (const ep of S.episodes.values()) if (ep.rated?.title === c.title) ep.clip = c.id;
        changed("episodes", "clips");
      } else if (d.stage === "render") { S.render = d; stageDone("render"); }
      else if (d.stage === "recap") {
        if (d.skipped) { S.recap = { state: "skipped", reason: d.reason }; stageDone("recap"); }
        else if (d.failed) { if (S.stages.recap) S.stages.recap.state = "failed"; if (S.recap.state !== "failed") S.recap = { state: "failed", error: d.reason }; }
        else stageDone("recap");
        changed("recap");
      }
      changed("stages", "head", "stats");
    } else if (type === "error") {
      if (d.stage !== "subscriber") { S.error = d.message; if (S.current && S.stages[S.current]) S.stages[S.current].state = "failed"; stopClips(); }
      changed("stages", "head");
    } else if (type === "cancelled") {
      S.cancelled = true;
      // a pause at a safe point comes after a finished step: that step is done; stopped at once, it was cut off
      if (S.current && S.stages[S.current]?.state === "active") { if (d.graceful && d.stage !== S.current) stageDone(S.current); else S.stages[S.current].state = "cancelled"; }   // paused between two clips: the montage itself waits
      stopClips();
      changed("stages", "head");
    }
    feed(e);
  }

  function stopClips() {   // the job ended: a clip that was being made is not being made any more
    for (const c of S.clips.values()) if (c.status === "working") { c.status = "stopped"; changed("clip:" + c.id); }
    if (S.recap.state === "working") { S.recap = { ...S.recap, state: "stopped" }; changed("recap"); }
  }

  function clipOf(id, data = {}) {
    let c = S.clips.get(id);
    if (!c) { c = { id, status: "waiting", title: data.title || "", start: data.start_s, end: data.end_s }; S.clips.set(id, c); changed("clips"); }
    if (data.title && !c.title) c.title = data.title;
    return c;
  }

  // ---------- feed lines
  const purpose = (p) => t("p_" + p) === "p_" + p ? p : t("p_" + p);
  function feed(e) {
    const d = e.data || {};
    let text = null, kind = "", ico = I.spark, key = null;
    switch (e.type) {
      case "stage": { const n = STAGE_OF[d.name] || d.name; text = t("ev_stage", { s: t("st_" + n) }) + (d.engine ? ` · ${d.engine}, ${d.language}` : "") + (d.duration_s ? ` · ${fmt.hours(d.duration_s)}` : "")
        + (d.segments ? ` · ${fmt.num(d.segments)}` : "") + (d.episodes ? ` · ${d.episodes}` : "") + (d.clips ? ` · ${d.clips}` : ""); ico = STAGE_ICON[n] || I.spark; kind = "stage"; break; }
      case "progress":
        if (d.stage === "speech") { text = t("ev_speech", { p: d.percent }); key = "speech"; ico = I.chip; }
        else if (d.stage === "model") { text = t("ev_model", { p: d.percent, d: (d.done / 1024).toFixed(1), t: (d.total / 1024).toFixed(1) }); key = "model"; ico = I.chip; }
        else if (d.stage === "scan") { text = t("ev_scan", { d: d.done, t: d.total }); key = "scan"; ico = I.search; }
        else if (d.stage === "rating") { text = t("ev_rating", { d: d.done, t: d.total }); key = "rating"; ico = I.star; }
        else if (d.stage === "missing") { text = t({ rating: "ev_missing_rating", look: "ev_missing_look", fit: "ev_missing_fit", critic: "ev_missing_critic" }[d.step] || "ev_missing_scan", { d: d.done, t: d.total }); ico = I.alert; kind = "bad"; }
        else if (d.stage === "fit") { text = null; }
        else if (d.stage === "recap") { text = t("st_recap") + " · " + recapStep(d); key = "recap"; ico = I.tv; }
        else if (d.stage === "audio") { text = t("ev_audio", { h: fmt.hours(d.duration_s), s: fmt.dur(d.seconds) }); ico = I.wave; kind = "good"; }
        else if (d.stage === "render" && d.title) { text = t("ev_render_clip", { c: d.clip, title: d.title }); ico = I.film; kind = "stage"; }
        else if (d.stage === "render" && d.step) { text = t("ev_render_step", { c: d.clip, step: t("step_" + d.step) }); key = "render:" + d.clip; ico = I.film; }
        break;
      case "episode_found": text = t("ev_found", { a: fmt.hms(d.start_s), b: fmt.hms(d.end_s) }) + (d.why_interesting ? " · " + d.why_interesting : ""); ico = I.search; break;
      case "episode_rated": text = d.status === "ok" ? t("ev_rated", { title: d.title || d.episode_id, score: d.score }) + " · " + t("v_" + d.verdict) : `${d.episode_id}: ${t("v_no_verdict")}`;
        ico = I.star; kind = ["strong", "good"].includes(d.verdict) ? "good" : ""; break;
      case "model_call": text = d.error ? t("ev_call_err", { p: purpose(d.purpose), e: d.error }) : t("ev_call", { p: purpose(d.purpose), s: t("unit_s", { n: fmt.dec(d.seconds || 0) }) })
        + (d.tokens_in != null ? " · " + t("tokens", { i: fmt.num(d.tokens_in), o: fmt.num(d.tokens_out) }) : "") + (d.cost_usd != null ? " · " + fmt.money(d.cost_usd) : "");
        ico = I.brain; kind = d.error ? "bad" : "model"; break;
      case "layout_chosen": text = t("ev_layout", { c: d.clip, m: d.mode }); ico = I.film; kind = "model"; break;
      case "ads_found": text = t("ev_ads", { c: d.clip, ads: d.count ? t("ads", { n: d.count }) : t("no_ads") }); ico = I.film; break;
      case "clip_ready": text = t("ev_ready", { c: d.clip }) + (d.title ? " · " + d.title : ""); ico = I.check; kind = "good"; break;
      case "clip_failed": text = t("ev_failed", { c: d.clip, e: d.error }); ico = I.alert; kind = "bad"; break;
      case "clip_checked": text = d.by === "error" ? t("ev_checked_err", { c: d.clip, e: d.error || "" }) : t("ev_checked", { c: d.clip, v: d.verdict, s: d.score }); ico = I.eye; kind = "model"; break;
      case "clip_fixed": text = t("ev_fixed", { c: d.clip, f: fixName(d.fix) }); ico = I.eye; kind = "model"; break;
      case "clip_reviewed": text = d.fix ? t(d.outcome === "fixed" ? "ev_reviewed_fixed" : "ev_reviewed_kept", { c: d.clip }) : null; ico = I.eye; break;
      case "recap_ready": text = t("ev_recap_ready", { m: fmt.dur(d.duration_s) }) + (d.title ? " · " + d.title : ""); ico = I.tv; kind = "good"; break;
      case "recap_failed": text = t("ev_recap_failed", { e: d.error }); ico = I.alert; kind = "bad"; break;
      case "clip_fitted": {
        const sec = (x) => (x > 0 ? "+" : x < 0 ? "−" : "±") + t("unit_s", { n: fmt.dec(Math.abs(x)) });
        text = d.by === "model" ? t("ev_fitted", { c: d.clip, a: sec(d.after.start_s - d.before.start_s), b: sec(d.after.end_s - d.before.end_s), len: fmt.dur(d.after.end_s - d.after.start_s) })
          : t("ev_fit_kept", { c: d.clip, e: d.reason || d.status });
        ico = I.crop; kind = d.by === "model" ? "model" : ""; break; }
      case "error": text = d.stage === "subscriber" ? `${d.subscriber}: ${d.message}` : t("ev_error", { e: d.message }); ico = I.alert; kind = "bad"; break;
      case "done": if (d.stage === "recap") { text = d.skipped ? t("ev_recap_skipped", { e: d.reason || "" }) : null; ico = I.tv; break; }
        text = d.stage === "analysis" ? t("ev_done_analysis", { n: (d.clips || []).length, h: fmt.hours(d.duration_s) })
        : t("ev_done_render", { ok: (d.report || []).filter((r) => r.status === "done").length, n: (d.report || []).length }); ico = I.check; kind = "good"; break;
      case "cancelled": text = t("ev_cancelled"); ico = I.stop; kind = "bad"; break;
      case "source_ready": text = t("ev_source", { title: d.title || d.source || "", from: [d.channel, d.duration_s ? fmt.hours(d.duration_s) : null].filter(Boolean).join(" · ") }); ico = I.film; kind = "good"; break;
    }
    if (!text) return;
    const top = S.feed[0];
    if (key && top && top.key === key) { Object.assign(top, { text, t: e.t, n: e.n }); top.changed = true; }
    else { S.feed.unshift({ id: ++seq, n: e.n, t: e.t, text, kind, ico, key, isNew: true }); if (S.feed.length > 300) S.feed.pop(); }
    changed("feed");
  }

  // ---------- drawing (V6, owner 22.11): every part follows the state by key and touches only what changed — a text
  // its text, a list its new, gone and moved rows. Nothing is rebuilt to show the same thing again, so the scroll,
  // open details, hover and the clips' pictures stay as they are. The clock touches only its own text.
  const J = {};
  // events come in bursts (a journal replayed on opening): they are folded once a frame, as one change
  function take(e) {
    pending.push(e);
    if (!raf) raf = requestAnimationFrame(() => { raf = 0; const list = pending; pending = []; batch(() => { for (const x of list) apply(x); }); });
  }
  function watch() {      // each part of the page follows its own signals
    const on = (fn) => effects.push(effect(fn));
    on(() => { P.head.value; P.stages.value; drawHead(); });
    // the clock is a binding: its text follows the time and the job's state, nothing else
    effects.push(api.bindText(J.clock, () => { now.value; P.head.value; const secs = elapsed(); return secs < 1 && !S.running ? "—" : fmt.hms(secs); }));
    on(() => { now.value; P.stages.value; drawClock(); });
    on(() => { P.stages.value; drawStages(); });
    on(() => { P.stats.value; P.model.value; drawStats(); });
    on(() => { P.episodes.value; drawEpisodes(); });
    on(() => { P.model.value; drawModel(); });
    on(() => { P.feed.value; drawFeed(); });
    on(() => { P.clips.value; drawClips(); });
    on(() => { P.recap.value; drawRecap(); });
  }
  function unwatch() { for (const off of effects) off(); effects = []; }

  // The open request (owner, 20.11): the clips straight on the window's background, the recap first and three clips wide;
  // on the right a column of small floating widgets — the request, the controls, the progress, the numbers, and the
  // details (episodes, the live feed, model calls) folded until asked for. The folding is remembered.
  function widget(id, title, body, { open = true, count = null, ico = null } = {}) {
    const key = "vodcut.widget." + id;
    let keep = null;
    try { keep = localStorage.getItem(key); } catch {}
    const d = h("details.vc-w", { "data-w": id }, h("summary.vc-w-head", ico ? icon(ico) : null, h("span", title), count, h("span.vc-w-chev", icon(I.chev))), h("div.vc-w-body", body));
    d.open = keep === null ? open : keep === "1";
    d.addEventListener("toggle", () => { try { localStorage.setItem(key, d.open ? "1" : "0"); } catch {} });
    return d;
  }

  function buildJob() {
    J.meta = h("div.vc-meta"); J.pill = h("span.pill"); J.conn = h("span.vc-conn"); J.channel = h("div.vc-channel");
    J.clock = h("b.vc-clock"); J.actions = h("div.vc-actions"); J.overall = h("i"); J.now = h("div.vc-now");
    J.stages = h("ol.vc-stages"); J.stats = h("div.vc-stats");
    J.episodes = h("div.vc-episodes"); J.epCount = h("span.vc-w-count"); J.feed = h("ol.vc-feed"); J.model = h("div.vc-model"); J.modelCount = h("span.vc-w-count");
    J.clips = h("div.vc-clips");
    J.err = h("div.vc-error", { hidden: true });
    J.recap = h("article.vc-clip.vc-recap-tile");
    root.replaceChildren(h("div.vc-board",
      h("section.vc-center", J.clips),     // the request's name is in the window's top bar
      J.side = h("aside.vc-widgets",
        widget("request", t("w_request"), [h("div.vc-state-row", J.pill, J.conn), J.channel, J.meta, J.actions]),
        widget("progress", t("w_progress"), [h("div.vc-now-row", J.now, J.clock), h("div.bar.vc-overall", J.overall), J.err,
          h("details.vc-stages-box", h("summary", t("w_stages")), J.stages)]),
        widget("numbers", t("w_numbers"), J.stats),
        widget("episodes", t("episodes"), J.episodes, { open: false, count: J.epCount }),
        widget("feed", t("feed"), J.feed, { open: false }),
        widget("model", t("model"), J.model, { open: false, count: J.modelCount }))));
  }

  function elapsed() {
    if (!S.first) return 0;
    const end = S.running ? Date.now() / 1000 : S.last;
    const begin = S.runStart && S.running ? Math.min(S.runStart, end) : S.first;
    return Math.max(0, end - begin);
  }

  function drawHead() {
    const info = S.info;
    if (J.shownTitle !== (info.title || S.id)) { J.shownTitle = info.title || S.id; api.setTitle?.(J.shownTitle); }
    const facts = sig(info.channel, info.avatar, info.platform, info.duration_s, info.source);
    region(J.channel, facts, () => info.channel ? [info.avatar ? h("img.vc-avatar", { src: fileUrl(info.avatar), alt: "" }) : null, h("b", info.channel),
      info.platform && info.platform !== "file" ? h("span.faint", info.platform.replace(/vod$/, "")) : null] : []);
    attr(J.channel, "hidden", !info.channel);
    region(J.meta, facts, () => [info.duration_s ? h("span", t("w_length", { h: fmt.hours(info.duration_s) })) : null,
      info.source ? h("span.vc-source", { title: info.source }, info.source) : null]);
    attr(J.pill, "class", "vc-state " + S.status); text(J.pill, t("s_" + S.status));   // a quiet word with a small dot, not a badge
    attr(J.conn, "class", "vc-conn " + (S.running ? S.conn : ""));
    text(J.conn, S.running && S.conn !== "open" ? t("reconnecting") : "");   // «live» read as a live stream: only a lost link is said
    // the buttons only when the job's state changes: a button rebuilt under the cursor would lose the click
    region(J.actions, sig(S.running, S.status, !!S.info.restart, !!S.info.pausing), actionButtons);
    attr(J.err, "hidden", !S.error);
    region(J.err, sig(S.error, S.status), () => [icon(I.alert), h("div.vc-error-text", ...signInOr(S.error || "", h("span", S.error || "")),
      S.status === "failed" ? api.reportButton?.(tool, S.id) : null)]);   // «Report a problem» under a failure (stage 17)
    const cur = S.status === "done" ? null : STAGES.find((n) => S.stages[n]?.state === "active") || S.current;
    text(J.now, S.status === "queued" ? queueText(S.info.queue)
      : S.status === "done" ? t("s_done") : cur ? [t("st_" + cur), stageSub(cur)].filter(Boolean).join(" · ") : t("s_" + S.status));
  }

  // the running stage's time, every second while the job runs (the clock's own text is a binding)
  function drawClock() {
    for (const li of J.stages.children) if (li.__key && S.stages[li.__key]?.state === "active") text(li.__small, stageLine(li.__key, "active"));
  }

  // A waiting request (stage 16): what it waits for, and its place when more than one waits
  function queueText(q) {
    if (!q) return t("s_queued");
    const after = q.after ? t("q_after", { t: q.after.title || q.after.id }) : t("q_next");
    return q.waiting > 1 ? after + " · " + t("q_place", { p: q.position, n: q.waiting }) : after;
  }

  // «Pause» stops at the next safe point — between two steps or two clips — so nothing done is lost; the page says so and
  // waits. «Stop now» kills the job at once: the step it is in is done again on «Continue»; it asks first.
  const stageName = () => { const n = S.current; return n ? t("st_" + n) : ""; };
  function actionButtons() {
    const acts = [];
    const url = (what) => `/api/jobs/${tool}/${encodeURIComponent(S.id)}/${what}`;
    if (S.status === "queued") {
      const b = h("button.btn", { type: "button" }, icon(I.x), t("unqueue"));
      b.onclick = async () => { b.disabled = true; try { await postJSON(url("cancel")); api.refreshRequests(); } catch (e) { api.toast(e.message, "bad"); b.disabled = false; } };
      acts.push(b);
    } else if (S.running) {
      const pausing = !!S.info.pausing;
      const pause = h("button.btn", { type: "button", disabled: pausing }, icon(I.pause), pausing ? t("pausing") : t("pause"));
      pause.onclick = async () => {
        pause.disabled = true;
        try { S.info = { ...S.info, ...(await postJSON(url("pause"))) }; changed("head"); }
        catch (e) { api.toast(e.message, "bad"); pause.disabled = false; }
      };
      const now = h("button.btn.btn-ghost.vc-stop-now", { type: "button" }, t("stop_now"));
      now.onclick = async () => {
        const ok = await api.confirm({ title: t("stop_now_title"), text: t("stop_now_text", { step: stageName() || "—" }), ok: t("stop_now"), danger: true });
        if (!ok) return;
        now.disabled = true;
        try { await postJSON(url("cancel")); } catch (e) { api.toast(e.message, "bad"); now.disabled = false; }
      };
      acts.push(pause, now);
      if (pausing) acts.push(h("p.vc-pause-note", t("pause_note", { step: stageName() || "—" })));
    } else if (S.info.restart && S.status === "done") {
      // a finished request is never overwritten: «Run again» makes a new request beside it (same source, its audio reused)
      const b = h("button.btn", { type: "button" }, icon(I.redo), t("restart_done"));
      b.onclick = async () => {
        b.disabled = true;
        try { const job = await postJSON(url("again")); api.refreshRequests(); api.openRequest(tool, job.id); }
        catch (e) { api.toast(e.code === "busy" ? t("busy", { j: e.message.split(": ").pop() }) : e.message, "bad"); b.disabled = false; }
      };
      acts.push(b);
    } else if (S.info.restart) {
      const b = h("button.btn", { type: "button" }, icon(I.redo), t("restart"));
      b.onclick = async () => { b.disabled = true; try { await postJSON(url("restart")); openJob(S.id, true); api.refreshRequests(); } catch (e) { api.toast(e.message, "bad"); b.disabled = false; } };
      acts.push(b);
    }
    return acts;
  }

  function fraction(name) {
    const st = S.stages[name];
    if (!st) return S.analysis && name !== "render" && name !== "recap" ? 1 : 0;
    if (st.state === "done") return 1;
    if (name === "speech") return S.progress.speech || 0;
    if (name === "scan" || name === "rating" || name === "fit" || name === "recap") return S.progress[name] || 0;
    if (name === "render") { const [d, tt] = S.progress.render || [0, 1]; const ready = [...S.clips.values()].filter((c) => c.status === "ready" || c.status === "failed").length; return Math.min(1, Math.max(ready, d - 1) / (tt || 1)); }
    return 0.1;
  }

  function stageSub(name) {
    const st = S.stages[name] || {}, d = st.data || {};
    switch (name) {
      case "audio": return S.progress.audio ? t("sub_rec", { h: fmt.hours(S.progress.audio.duration_s) })
        : st.state !== "active" ? ""
        : S.download?.queue > 0 ? t("sub_audio_queue", { p: S.download.queue })
        : S.download?.percent != null ? t("sub_audio_pct", { p: S.download.percent }) : t("sub_audio_wait");
      case "speech": return st.state === "active" ? [d.engine, `${Math.round((S.progress.speech || 0) * 100)}%`].filter(Boolean).join(" · ") : [d.engine, d.language].filter(Boolean).join(" · ");
      case "scan": { const n = [...S.episodes.values()].filter((x) => x.found).length; return st.state === "active" && S.progress.scan_n ? t("sub_windows", { d: S.progress.scan_n[0], t: S.progress.scan_n[1] }) : n ? t("sub_found", { n }) : ""; }
      case "rating": { const g = [...S.episodes.values()].filter((x) => ["strong", "good"].includes(x.rated?.verdict)).length; return st.state === "active" && S.progress.rating_n ? t("sub_batches", { d: S.progress.rating_n[0], t: S.progress.rating_n[1] }) : g ? t("sub_good", { n: g }) : ""; }
      case "pick": return S.analysis ? t("sub_clips", { n: (S.analysis.clips || []).length }) : "";
      case "fit": {
        if (!st.state) return S.analysis ? t("sub_fit_off") : "";
        if (st.state === "active" && S.progress.fit_n) return t("sub_fit", { d: S.progress.fit_n[0], t: S.progress.fit_n[1] });
        const cut = [...S.fitted.values()].reduce((a, x) => a + (x.cut_s || 0), 0);
        return S.fitted.size ? t("sub_fit_cut", { n: fmt.dec(cut) }) : ""; }
      case "render": { const ready = [...S.clips.values()].filter((c) => c.status === "ready").length; const total = S.progress.render?.[1] || d.clips || S.clips.size; return total ? t("sub_rendered", { d: ready, t: total }) : ""; }
      case "recap": return S.recap.state === "working" ? recapStep(S.recap) : S.recap.state === "ready" ? fmt.dur(S.recap.data.duration_s) : S.recap.state === "failed" ? t("failed") : "";
    }
    return "";
  }

  function stageState(name) {
    const st = S.stages[name];
    return st?.state || (name === "recap" ? (S.status === "done" ? "skip" : "wait") : S.analysis && name === "fit" ? "skip" : S.analysis && name !== "render" ? "done" : "wait");
  }
  function stageLine(name, state) {
    const st = S.stages[name];
    const secs = st?.t0 ? ((st.t1 || (state === "active" && S.running ? Date.now() / 1000 : S.last)) - st.t0) : null;
    return [stageSub(name), secs != null && secs >= 0.5 ? fmt.dur(secs) : ""].filter(Boolean).join(" · ") || t(state === "wait" ? "st_waiting" : "st_skipped");
  }
  function drawStages() {   // a compact list, folded under «Stages»: the progress line above says the rest
    let total = 0, done = 0;
    const shown = STAGES.filter((name) => !(name === "recap" && !S.stages[name] && !S.recapOn && !S.running));   // switched off and never made: not a stage of this request
    for (const name of shown) {
      const state = stageState(name);
      if (name !== "recap" || S.stages[name] || S.recapOn) { total += WEIGHT[name]; done += WEIGHT[name] * (state === "done" ? 1 : fraction(name)); }
    }
    keyed(J.stages, shown, {
      key: (name) => name,
      create: (name) => {
        const li = h("li", { "data-stage": name }, h("span.vc-stage-icon"),
          h("div.vc-stage-text", h("b", h("span.vc-stage-n", String(STAGES.indexOf(name) + 1)), t("st_" + name)), h("small")),
          h("div.bar.vc-stage-bar", h("i")));
        li.__small = li.querySelector("small"); li.__bar = li.lastChild;
        return li;
      },
      update: (li, name) => {
        const state = stageState(name);
        attr(li, "class", "vc-stage " + state);
        region(li.firstChild, state === "done", () => icon(state === "done" ? I.check : STAGE_ICON[name]));
        text(li.__small, stageLine(name, state));
        attr(li.__bar, "hidden", state !== "active");
        if (state === "active") attr(li.__bar.firstChild, "style", `width:${Math.round(fraction(name) * 100)}%`);
      },
    });
    const all = S.status === "done" ? 1 : done / total;
    attr(J.overall, "style", `width:${Math.round(all * 1000) / 10}%`);
  }

  function drawStats() {
    const eps = [...S.episodes.values()];
    const good = eps.filter((x) => ["strong", "good"].includes(x.rated?.verdict)).length;
    const ready = [...S.clips.values()].filter((c) => c.status === "ready").length;
    const m = S.model;
    const known = eps.length || S.analysis || S.stages.scan?.t0;   // a journal with only a render does not know the episodes
    keyed(J.stats, [
      ["m_episodes", known ? fmt.num(eps.filter((x) => x.found).length || S.analysis?.episodes_found || 0) : "—"],
      ["m_good", known ? fmt.num(good) : "—"],
      ["m_clips", `${ready}/${S.clips.size || 0}`],
      ["m_calls", fmt.num(m.calls), m.calls ? fmt.dur(m.seconds) : ""],
      ["m_tokens", m.tin || m.tout ? fmt.num(m.tin + m.tout) : "—", m.tin || m.tout ? `${fmt.num(m.tin)} / ${fmt.num(m.tout)}` : (m.calls ? t("no_tokens") : "")],
      ["m_cost", m.costKnown ? fmt.money(m.cost) : "—"]], {
      key: (x) => x[0],
      create: (x) => h("div.vc-stat", h("small", t(x[0])), h("b"), h("span.faint")),
      update: (el, [, value, extra]) => { text(el.children[1], value); text(el.children[2], extra || ""); attr(el.children[2], "hidden", !extra); },
    });
  }

  function drawEpisodes() {
    const eps = [...S.episodes.values()].sort((a, b) => (a.start ?? 1e9) - (b.start ?? 1e9));
    text(J.epCount, eps.length ? String(eps.length) : "");
    // an episode is built again only when what is known of it changed (found, then rated, then turned into a clip)
    keyed(J.episodes, eps.length ? eps : [null], {
      key: (ep) => ep ? ep.id : "",
      sig: (ep) => ep ? sig(ep.found, ep.rated, ep.clip, ep.start, ep.end) : "",
      create: (ep) => {
        if (!ep) return h("p.faint.vc-empty", t("episodes_empty"));
        const r = ep.rated, f = ep.found || {};
        const verdict = r?.verdict || (r ? "no_verdict" : null);
        const node = h("article", { class: "vc-ep " + (verdict || "pending") + (ep.isNew ? " new" : "") },
          h("div.vc-ep-top", h("span.mono.vc-ep-time", ep.start != null ? `${fmt.hms(ep.start)}–${fmt.hms(ep.end)}` : ep.id),
            f.episode_type ? h("span.chip", f.episode_type) : null, verdict ? h("span", { class: "chip v-" + verdict }, t("v_" + verdict)) : null,
            ep.clip ? h("span.chip.accent", t("to_clip", { c: ep.clip })) : null),
          h("p.vc-ep-title", r?.title || f.why_interesting || f.text_preview || ""),
          r?.title && f.why_interesting ? h("p.vc-ep-why", f.why_interesting) : null,
          r?.score != null ? h("div.vc-score", h("div.bar", h("i", { style: `width:${r.score}%` })), h("b", String(r.score))) : null);
        ep.isNew = false;
        return node;
      },
    });
  }

  function drawModel() {
    const m = S.model;
    text(J.modelCount, m.calls ? String(m.calls) : "");
    if (!m.calls) { keyed(J.model, [0], { key: () => "empty", create: () => h("p.faint.vc-empty", t("calls_empty")) }); return; }
    keyed(J.model, [0], { key: () => "list", create: () => h("ul.vc-calls") });
    keyed(J.model.firstChild, m.list.slice(0, 12), {      // a call never changes: new ones come on top, old ones leave
      key: (c) => c.id,
      create: (c) => h("li", { class: c.error ? "bad" : "" },
        h("span.chip.accent", purpose(c.purpose)),
        h("span.vc-call-model.faint", c.model || ""),
        h("span.vc-call-num", c.error ? h("span.vc-call-err", c.error) : [t("unit_s", { n: fmt.dec(c.seconds || 0) }),
          c.tokens_in != null ? " · " + t("unit_tok", { n: fmt.num((c.tokens_in || 0) + (c.tokens_out || 0)) }) : "",
          c.cost_usd != null ? " · " + fmt.money(c.cost_usd) : ""].join("")),
        c.images ? h("span.chip", { title: t("frames_n", { n: c.images }) }, icon(I.film), String(c.images)) : null),
    });
  }

  function drawFeed() {
    // a line is added once; a progress line that only counts on (speech 41 %, 42 %…) changes its text in place
    keyed(J.feed, S.feed.length ? S.feed.slice(0, 80) : [null], {
      key: (f) => f ? f.id : "",
      create: (f) => {
        if (!f) return h("li.faint.vc-empty", t("feed_empty"));
        const li = h("li", { class: "vc-line " + f.kind + (f.isNew ? " new" : "") }, h("span.vc-line-icon", icon(f.ico)), h("span.vc-line-text"), h("time.mono.faint"));
        f.isNew = false;
        return li;
      },
      update: (li, f) => { if (f) { text(li.children[1], f.text); text(li.children[2], fmt.clock(f.t)); } },
    });
  }

  const clipNodes = new Map();
  function drawClips() {
    const list = [...S.clips.values()].sort(byFavourite);      // the recap first, then the favourites, then the rest
    for (const id of [...clipNodes.keys()]) if (!S.clips.has(id)) clipNodes.delete(id);
    // no clips yet: one empty card stands where they will come, so the recap already has a clip's height
    keyed(J.clips, ["recap", ...(list.length ? list.map((c) => c.id) : [""])], {
      key: (k) => k,
      create: (k) => {
        if (k === "recap") return J.recap;
        if (!k) return h("article.vc-clip.vc-clip-empty", h("div.vc-clip-media", h("div.vc-clip-ph", h("div.vc-empty-ph", icon(I.film), h("span", t("clips_empty"))))));
        const node = h("article.vc-clip");
        clipNodes.set(k, node);
        effects.push(effect(() => { clipSig(k).value; drawClip(k); }));     // the card follows its clip
        return node;
      },
    });
    for (const fn of clipListeners) fn();
  }

  // ---------- the recap (stage 12): a 16:9 tile three clips wide before the clips; its own viewer with the chapters,
  // «Download» and «Cover». One component for the computer and the phone.
  function recapFraction(d) {      // the story, the pieces, the look and the encode as one line: the encode is most of it
    const share = { story: [0, 0.08], video: [0.08, 0.3], look: [0.3, 0.38], encode: [0.38, 1] }[d.step] || [0, 0];
    return share[0] + (share[1] - share[0]) * (d.total ? d.done / d.total : 0);
  }
  function recapStep(d) {
    if (d.step === "story" || !d.step) return t("recap_story");
    const text = t("recap_" + d.step, { d: d.done ?? 0, t: d.total ?? "?" });
    return text === "recap_" + d.step ? d.step : text;
  }
  function recapMinutes(sec) { return fmt.dur(sec); }

  function drawRecap() {
    const R = S.recap, node = J.recap;
    attr(node, "class", "vc-clip vc-recap-tile " + (R.state === "ready" ? "ready" : R.state === "working" ? "working" : R.state === "failed" ? "failed" : "") + (R.fresh ? " fresh" : ""));
    attr(node, "title", R.state === "ready" ? R.data.title || t("recap") : "");
    const ph = (...body) => h("div.vc-clip-media", h("div.vc-clip-ph", h("div.vc-recap-ph", ...body)));
    // built again only when the recap changes its state; the step it is on («pieces 3 of 9») is a text of its own
    region(node, sig(R.state, R.error, R.data?.file, R.data?.cover, R.data?.seconds, R.data?.title, S.recapOn, !!S.stages.recap, S.status), () => {
      if (R.state === "ready") {
        const d = R.data;
        const box = h("div.vc-clip-media",
          h("img.vc-recap-poster", { src: fileUrl(d.cover) + "?v=" + encodeURIComponent(String(d.seconds ?? "")), alt: "" }),
          h("button.vc-play", { type: "button", "aria-label": t("play"), onclick: (e) => { e.stopPropagation(); openRecap(); } }, icon(I.playRound)),
          h("div.vc-recap-cap", h("span.vc-recap-badge", icon(I.tv), t("recap")), h("b", d.title || ""), h("span", t("recap_meta", { m: recapMinutes(d.duration_s), p: d.parts, c: (d.chapters || []).length }))));
        box.onclick = () => openRecap();
        return box;
      }
      if (R.state === "working") return ph(icon(I.tv), h("b", t("recap")), h("div.vc-clip-step", h("span.vc-spinner"), J.recapStep = h("span")));
      if (R.state === "failed") return ph(icon(I.alert), h("b", t("recap_failed")), h("span.vc-recap-err", R.error || ""));
      if (R.state === "skipped") return ph(icon(I.tv), h("b", t("recap")), h("span", t("recap_skipped")));
      if (R.state === "stopped") return ph(icon(I.tv), h("b", t("recap")), h("span", t("stopped")));
      if (S.recapOn === false && !S.stages.recap) {          // switched off: say so, and where to switch it on
        return ph(icon(I.tv), h("b", t("recap")), h("span", t("recap_off")),
          h("button.btn.btn-sm", { type: "button", onclick: (e) => { e.stopPropagation(); api.openSettings("tool-" + tool); } }, t("recap_turn_on")));
      }
      return ph(icon(I.tv), h("b", t("recap")), h("span", t(S.status === "done" ? "recap_none" : "recap_wait")));
    });
    if (R.state === "working") text(J.recapStep, recapStep(R));
  }

  // Under an open viewer the page holds still (owner, 21.11): every other video pauses and the grid drops its blur
  // (`vc-viewing` on <html>, section.css), so the browser composes one flat layer under the viewer. Closing plays again
  // only what was playing.
  function holdPage(viewer) {
    const paused = [];
    for (const v of document.querySelectorAll("video")) if (!viewer.contains(v) && !v.paused) { v.pause(); paused.push(v); }
    document.documentElement.classList.add("vc-viewing");
    return () => {
      if (!document.querySelector(".vc-v-back")) document.documentElement.classList.remove("vc-viewing");
      for (const v of paused) if (v.isConnected) v.play().catch(() => {});
    };
  }

  async function openRecap() {
    const d = S.recap.data;
    if (!d) return;
    const video = h("video.vc-v-video", { controls: true, autoplay: true, playsinline: true, poster: fileUrl(d.cover), src: fileUrl(d.file) });
    let release = () => {};
    const close = () => { video.pause(); back.remove(); release(); document.removeEventListener("keydown", key, true); };
    const key = (e) => { if (e.key === "Escape") { e.preventDefault(); close(); } };
    const info = h("div.vc-v-info");
    const back = h("div.vc-v-back", { onclick: (e) => { if (e.target === back) close(); } },
      h("div.vc-v-wrap",
        h("button.vc-v-close", { type: "button", "aria-label": t("close"), title: t("close"), onclick: close }, icon(I.x)),
        h("div.vc-v.vc-v-wide", { role: "dialog", "aria-modal": "true", "aria-label": t("recap") }, h("div.vc-v-media", video), h("div.vc-v-side", info))));
    document.body.append(back);
    release = holdPage(back);
    document.addEventListener("keydown", key, true);
    const name = (rel) => rel.split("/").pop();
    const stem = (S.info.channel ? S.info.channel + "-" : "") + "recap";
    const actions = h("div.vc-v-acts",
      h("a.btn.vc-v-dl", { href: fileUrl(d.file, true), download: stem + ".mp4" }, icon(I.down), t("download")),
      h("a.btn.btn-ghost.vc-v-dl", { href: fileUrl(d.cover, true), download: stem + "-cover.jpg" }, icon(I.image), t("cover")));
    const chapters = h("ol.vc-v-lines.vc-v-chapters", (d.chapters || []).map((c, i) =>
      h("li", { onclick: () => { video.currentTime = i ? c.start_s : 0; video.play().catch(() => {}); } }, h("time", fmt.hms(i ? c.start_s : 0)), h("span.vc-v-text", c.title))));
    let text = "";
    try { const r = await fetch(fileUrl(d.description_file), { cache: "no-store" }); if (r.ok) text = await r.text(); else loadFailed("lf_desc"); } catch { loadFailed("lf_desc"); }
    if (!back.isConnected) return;
    info.replaceChildren(
      h("div.vc-v-top", h("span.vc-recap-badge.on-panel", icon(I.tv), t("recap")), h("span.faint", t("recap_meta", { m: recapMinutes(d.duration_s), p: d.parts, c: (d.chapters || []).length }))),
      block(t("v_title"), h("p.vc-v-title", d.title || ""), d.title || null),
      actions,
      block(t("v_chapters"), chapters, d.chapters?.length ? (d.chapters || []).map((c, i) => `${fmt.hms(i ? c.start_s : 0)} ${c.title}`).join("\n") : null),
      block(t("v_description"), text ? h("p.vc-v-desc", text.trim()) : h("p.faint", t("v_not_yet")), text.trim() || null));
  }

  // the critic (stage 14): the name of its edit, and what it did with this clip — only when it suggested an edit
  function fixName(fix) { const s = t("fix_" + fix); return s === "fix_" + fix ? (fix || "") : s; }
  function criticNote(cr) {
    if (!cr?.fix) return null;
    const head = t(cr.outcome === "fixed" ? "critic_fixed" : "critic_kept", { f: fixName(cr.fix) });
    const score = cr.score_before != null && cr.score != null ? `${cr.score_before} → ${cr.score}` : null;
    return block(t("v_critic"), h("div.vc-v-critic", h("p", head), h("p.faint", [cr.wish || cr.reason, score].filter(Boolean).join(" · "))));
  }

  function fileUrl(rel, download) { return `/api/jobs/${tool}/${encodeURIComponent(S.id)}/files/${rel.split("/").map(encodeURIComponent).join("/")}${download ? "?download=1" : ""}`; }

  function drawClip(id) {
    const c = S.clips.get(id), node = clipNodes.get(id);
    if (!c || !node) return;
    const ready = c.status === "ready" && c.file;
    attr(node, "class", "vc-clip " + c.status + (ready && c.fresh ? " fresh" : ""));
    attr(node, "title", c.title || "");
    // one frame of the ones the model looks at (the middle one) fills the card: five nearly equal frames stacked
    // looked like the picture had been tripled
    const shot = ready ? null : (c.frames || [])[Math.floor(((c.frames || []).length - 1) / 2)];
    const fav = favourites().has(id), got = downloaded().has(id);
    // the card is built again only when what it shows changes (waiting → working → ready, a new frame, the heart);
    // the step it is on (frames, layout, captions…) is a text of its own
    region(node, sig(c.status, ready ? c.file : null, shot, ready && fav, ready && got, ready && c.critic?.outcome === "fixed" ? c.critic.fix : null), () => {
      let media;
      node.__step = null;
      if (ready) {
        // only the card: the clip's first frame and a round «play»; a press opens the viewer. Its picture is kept.
        const keep = node.querySelector("video");
        const video = keep && keep.dataset.src === c.file ? keep : h("video", { muted: true, playsinline: true, preload: "metadata", src: fileUrl(c.file) + "#t=0.5", "data-src": c.file, tabindex: "-1" });
        media = [video, h("button.vc-play", { type: "button", "aria-label": t("play"), onclick: (e) => { e.stopPropagation(); openViewer(c.id); } }, icon(I.playRound))];
      } else {
        media = h("div.vc-clip-ph", shot ? h("div.vc-frames", h("img", { src: fileUrl(shot), alt: "", loading: "lazy" })) : h("span.vc-clip-num", id.replace(/\D/g, "")),
          c.status === "working" ? h("div.vc-clip-step", h("span.vc-spinner"), node.__step = h("span")) : null,
          c.status === "waiting" ? h("div.vc-clip-step.dim", t("waiting")) : null,
          c.status === "stopped" ? h("div.vc-clip-step.dim", t("stopped")) : null,
          c.status === "failed" ? h("div.vc-clip-step.bad", icon(I.alert), t("failed")) : null);
      }
      const box = h("div.vc-clip-media", ...[media].flat(),
        ready ? heart(c.id, "vc-heart") : null,
        ready && got ? h("span.vc-got", { title: t("v_downloaded") }, icon(I.check)) : null,
        // a quiet mark when the critic edited the clip; why is in the viewer
        ready && c.critic?.outcome === "fixed" ? h("span.vc-critic", { title: t("critic_mark") + " · " + fixName(c.critic.fix), "aria-label": t("critic_mark") }, icon(I.eye)) : null);
      if (ready) box.onclick = () => openViewer(c.id);      // the whole card opens the viewer
      return box;
    });
    if (node.__step) {
      const step = c.step === "frames" && !c.frames ? "frames" : c.step === "layout_done" ? (c.ads == null ? "layout" : "captions") : c.step;
      text(node.__step, t("step_" + step) === "step_" + step ? step : t("step_" + step));
    }
  }

  // --- the viewer (owner, 20.11): a large modal, the clip plays at once on the left; on the right its title, description
  // and keywords, each with «copy», «Download», and the clip's transcript with the line being spoken lit up.
  let words = null;          // the job's transcript, read once (job file transcript.json), in the stream's own time
  let facts = null;          // clips.json: each clip's place in the stream and the model's notes
  async function jobFile(rel) {
    const r = await fetch(fileUrl(rel), { cache: "no-store" });
    if (!r.ok) throw new Error(r.statusText);
    return r.json();
  }
  // a file of the request that did not load: one plain message, not silence and not one per file (review В2, C14)
  let loadFailedShown = false;
  function loadFailed(what) {
    if (loadFailedShown) return;
    loadFailedShown = true;
    api.toast(t("load_failed", { w: t(what) }), "bad");
  }
  async function clipFacts(id) {
    if (!facts) { try { facts = (await jobFile("clips.json")).clips || []; } catch { facts = []; loadFailed("lf_clips"); } }
    return facts.find((x) => x.id === id) || {};
  }
  async function clipLines(start, end) {
    if (words === null) { try { words = (await jobFile("transcript.json")).segments || []; } catch { words = []; loadFailed("lf_text"); } }
    // each phrase with its words, moved into the clip's own time (the clip starts at `start` in the stream)
    return words.filter((g) => g.end > start && g.start < end).map((g) => ({
      start: Math.max(0, g.start - start), end: g.end - start, text: (g.text || "").trim(),
      words: (g.words || []).filter((w) => w.end > start && w.start < end).map((w) => ({ start: w.start - start, end: w.end - start, text: (w.word || "").trim() })),
    }));
  }

  function block(label, body, copyText) {
    const head = h("div.vc-v-head", h("span", label));
    if (copyText) { const b = h("button.vc-v-copy", { type: "button", title: t("copy_this"), "aria-label": t("copy_this") }, icon(I.copy)); b.onclick = () => api.copy(copyText, b); head.append(b); }
    return h("section.vc-v-block", head, body);
  }

  // Favourites (owner, 20.11): a heart in the card's top right corner — white and filled when set, an outline on hover
  // otherwise; a click sets or clears it. Favourites come first, right after the recap: in the grid, the strip and
  // «previous / next». Kept in this window, per request.
  const favKey = () => "vodcut.favourite." + S.id;
  function favourites() { try { return new Set(JSON.parse(localStorage.getItem(favKey()) || "[]")); } catch { return new Set(); } }
  function byFavourite(x, y) { const f = favourites(); return (f.has(y.id) - f.has(x.id)) || x.id.localeCompare(y.id); }
  const heartListeners = new Set();
  const clipListeners = new Set();    // an open viewer: its strip follows the clips as they get ready
  function toggleFavourite(id) {
    const f = favourites(); f.has(id) ? f.delete(id) : f.add(id);
    try { localStorage.setItem(favKey(), JSON.stringify([...f])); } catch {}
    changed("clips");
    for (const fn of heartListeners) fn();
  }
  function heart(id, cls) {
    const on = favourites().has(id);
    const b = h("button", { type: "button", class: cls + (on ? " on" : ""), "aria-pressed": String(on), title: t(on ? "fav_off" : "fav_on"), "aria-label": t(on ? "fav_off" : "fav_on") },
      icon(I.heart));
    b.addEventListener("click", (e) => { e.stopPropagation(); e.preventDefault(); toggleFavourite(id); });
    return b;
  }

  // Downloads are remembered in this window, per request and clip: the viewer, its strip and the grid mark them;
  // downloading again is always there.
  const dlKey = () => "vodcut.downloaded." + S.id;
  function downloaded() { try { return new Set(JSON.parse(localStorage.getItem(dlKey()) || "[]")); } catch { return new Set(); } }
  function markDownloaded(id) {
    const d = downloaded(); d.add(id);
    try { localStorage.setItem(dlKey(), JSON.stringify([...d])); } catch {}
    changed("clip:" + id);
  }
  const readyClips = () => [...S.clips.values()].filter((x) => x.status === "ready" && x.file).sort(byFavourite);

  // the viewer: one modal for all the ready clips — the clip on the left with «previous» and «next» beside it (and the
  // arrow keys), on the right a strip of every clip, the AI score, title, description, keywords, «Download», the transcript
  // the place in the original recording where the clip starts: Twitch takes ?t=1h2m3s, YouTube &t=123s
  function sourceAt(url, seconds) {
    if (!url || !/^https?:/.test(url) || seconds == null) return null;
    const s = Math.max(0, Math.floor(seconds));
    try {
      const u = new URL(url);
      if (/(^|\.)twitch\.tv$/.test(u.hostname)) { const hh = Math.floor(s / 3600), mm = Math.floor(s % 3600 / 60); u.searchParams.set("t", `${hh}h${mm}m${s % 60}s`); return u.href; }
      if (/(^|\.)(youtube\.com|youtu\.be)$/.test(u.hostname)) { u.searchParams.set("t", `${s}s`); return u.href; }
    } catch { return null; }
    return null;
  }

  // Brings `el` into view inside `box` only. scrollIntoView also moved the viewer itself (an overflow-hidden box still
  // scrolls), and the close button slid out of sight.
  function reveal(box, el, axis) {
    if (!box || !el) return;
    const b = box.getBoundingClientRect(), r = el.getBoundingClientRect();
    if (axis === "x") {
      if (r.left < b.left) box.scrollLeft -= b.left - r.left + 16; else if (r.right > b.right) box.scrollLeft += r.right - b.right + 16;
    } else {
      const top = b.top + 120;          // below the sticky strip of clips
      if (r.top < top) box.scrollTop -= top - r.top; else if (r.bottom > b.bottom - 24) box.scrollTop += r.bottom - b.bottom + 24;
    }
  }

  async function openViewer(id) {
    const video = h("video.vc-v-video", { controls: true, autoplay: true, playsinline: true });
    const prev = h("button.vc-v-nav.prev", { type: "button", "aria-label": t("v_prev"), title: t("v_prev") }, icon(I.left));
    const next = h("button.vc-v-nav.next", { type: "button", "aria-label": t("v_next"), title: t("v_next") }, icon(I.right));
    const strip = h("div.vc-v-strip");
    // a mouse wheel (up and down) moves the strip sideways: with forty clips it is a long row
    strip.addEventListener("wheel", (e) => {
      if (Math.abs(e.deltaY) <= Math.abs(e.deltaX) || strip.scrollWidth <= strip.clientWidth) return;
      e.preventDefault(); strip.scrollLeft += e.deltaY;
    }, { passive: false });
    const info = h("div.vc-v-info");
    const side = h("div.vc-v-side", strip, info);
    // The person reads the side on their own (wheel, finger, scrollbar, keys): the transcript stops pulling the page to
    // the word being said for a few seconds after the last such move (owner, 22.11). A click on a line or another clip
    // gives the following back at once.
    let handsOff = 0;
    const byHand = () => { handsOff = performance.now() + 4000; };
    for (const ev of ["wheel", "touchmove", "pointerdown", "keydown"]) side.addEventListener(ev, byHand, { passive: true });
    const onClips = () => { if (back.isConnected) drawStrip(); };
    clipListeners.add(onClips);
    const onFav = () => { drawStrip(); const hb = info.querySelector(".vc-v-heart"); if (hb) hb.replaceWith(heart(current, "vc-v-heart")); };
    heartListeners.add(onFav);
    let release = () => {};
    const close = () => { video.pause(); stop(); heartListeners.delete(onFav); clipListeners.delete(onClips); back.remove(); release(); document.removeEventListener("keydown", key, true); };
    const key = (e) => {
      if (e.key === "Escape") { e.preventDefault(); close(); }
      else if (e.key === "ArrowRight" && !e.metaKey) { e.preventDefault(); go(+1); }
      else if (e.key === "ArrowLeft" && !e.metaKey) { e.preventDefault(); go(-1); }
    };
    const back = h("div.vc-v-back", { onclick: (e) => { if (e.target === back) close(); } },
      h("div.vc-v-wrap",       // the close button hangs just outside the viewer's top right corner: close by, never over the clips
        h("button.vc-v-close", { type: "button", "aria-label": t("close"), title: t("close"), onclick: close }, icon(I.x)),
        h("div.vc-v", { role: "dialog", "aria-modal": "true", "aria-label": t("play") },
          h("div.vc-v-media", video, prev, next), side)));
    document.body.append(back);
    release = holdPage(back);
    document.addEventListener("keydown", key, true);

    let current = null, raf = 0, spans = [], litWord = null, litLine = null, shown = 0;
    const stop = () => { cancelAnimationFrame(raf); raf = 0; };
    const go = (step) => { const list = readyClips(); const i = list.findIndex((x) => x.id === current); const to = list[i + step]; if (to) show(to.id); };
    prev.onclick = () => go(-1); next.onclick = () => go(+1);

    // the strip follows the ready clips by key: switching clips only moves the mark, a new clip adds its own thumb, a
    // favourite moves its thumb forward; their pictures never reload (no flicker)
    function drawStrip(bring = false) {
      const done = downloaded(), fav = favourites();
      keyed(strip, readyClips(), {
        key: (x) => x.id,
        create: (x) => h("button.vc-v-thumb", { type: "button", title: x.title || x.id, onclick: () => show(x.id) },
          h("video", { muted: true, preload: "metadata", src: fileUrl(x.file) + "#t=0.5", tabindex: "-1" }), h("span.vc-v-got", { title: t("v_downloaded") }, icon(I.check)),
          h("span.vc-v-fav", icon(I.heart))),
        update: (b, x) => { attr(b, "aria-current", String(x.id === current)); b.classList.toggle("got", done.has(x.id)); b.classList.toggle("fav", fav.has(x.id)); },
      });
      const l = readyClips(), i = l.findIndex((x) => x.id === current);
      prev.disabled = i <= 0; next.disabled = i < 0 || i >= l.length - 1;
      if (bring) reveal(strip, [...strip.children].find((b) => b.__key === current), "x");
    }

    async function show(clipId) {
      const c = S.clips.get(clipId);
      if (!c?.file) return;
      current = clipId; stop();
      const ticket = ++shown;
      const list = readyClips(), i = list.findIndex((x) => x.id === clipId);
      prev.disabled = i <= 0; next.disabled = i < 0 || i >= list.length - 1;
      video.src = fileUrl(c.file); video.play().catch(() => {});
      drawStrip(true);
      const f = await clipFacts(clipId);
      const phrases = (c.start ?? f.start_s) != null && (c.end ?? f.end_s) != null ? await clipLines(c.start ?? f.start_s, c.end ?? f.end_s) : [];
      if (ticket !== shown || !back.isConnected) return;
      const title = c.title || f.title || clipId, score = c.score ?? f.score;
      const keywords = (f.keywords || f.tags || []).filter(Boolean);
      const lines = h("ol.vc-v-lines");
      const got = downloaded().has(clipId);
      const dl = h("a", { class: "btn vc-v-dl" + (got ? " got" : ""), href: fileUrl(c.file, true), download: c.file.split("/").pop(),
        onclick: () => setTimeout(() => { markDownloaded(clipId); dl.classList.add("got"); dl.replaceChildren(icon(I.check), t("download_again")); drawStrip(); }, 0) },
        icon(got ? I.check : I.down), got ? t("download_again") : t("download"));
      const start = c.start ?? f.start_s, end = c.end ?? f.end_s;
      const origin = (at) => {
        if (at == null) return null;
        const link = sourceAt(S.info.source, at);
        const where = [S.info.platform && S.info.platform !== "file" ? S.info.platform.replace(/vod$/, "") : null, fmt.hms(at)].filter(Boolean).join(" · ");
        return block(t("v_source"), link
          ? h("a.vc-v-src", { href: link, target: "_blank", rel: "noopener noreferrer" }, where, icon(I.ext))
          : h("p", where));
      };
      const fresh = [
        h("div.vc-v-top", score != null ? h("div.vc-v-score", h("span", t("v_score")), h("b", String(score)), h("span.faint", "/ 100")) : h("span"), heart(clipId, "vc-v-heart")),
        block(t("v_title"), h("p.vc-v-title", title), title),
        block(t("v_description"), f.description ? h("p", f.description) : h("p.faint", t("v_not_yet")), f.description || null),
        block(t("v_keywords"), keywords.length ? h("div.vc-chips", keywords.map((k) => h("span.chip", k))) : h("p.faint", t("v_not_yet")), keywords.length ? keywords.join(" ") : null),
        dl,
        criticNote(c.critic),
        origin(start),
        block(t("v_transcript"), lines)].filter(Boolean);

      // the transcript: the clip's part of the stream, in the clip's own time. Read from the job's transcript, never from
      // the video: the clip itself is not touched. The word being said is lit as it is said, its line a little too.
      // Everything is ready before it replaces the previous clip's side: one swap, no empty frame in between.
      spans = []; litWord = null; litLine = null;
      if (!phrases.length) { lines.replaceChildren(h("li.faint", t("v_no_transcript"))); info.replaceChildren(...fresh); side.scrollTop = 0; return; }
      const items = phrases.map((l) => {
        const ws = l.words.length ? l.words : [{ start: l.start, end: l.end, text: l.text }];
        const li = h("li", { onclick: () => { handsOff = 0; video.currentTime = l.start; video.play(); } }, h("time", fmt.hms(l.start)));
        li.append(h("span.vc-v-text", ...ws.flatMap((w, k) => { const sp = h("span.w", w.text); spans.push({ el: sp, w, li }); return k ? [" ", sp] : [sp]; })));
        return li;
      });
      lines.replaceChildren(...items);
      info.replaceChildren(...fresh);
      side.scrollTop = 0; handsOff = 0;
      if (!video.paused) run();
    }

    const follow = () => {
      const now = video.currentTime;
      const hit = spans.find((x) => now >= x.w.start && now < x.w.end) || null;
      if (hit !== litWord) {
        litWord?.el.classList.remove("now");
        litWord = hit;
        if (hit) {
          hit.el.classList.add("now");
          if (hit.li !== litLine) { litLine?.classList.remove("now"); litLine = hit.li; litLine.classList.add("now"); if (performance.now() >= handsOff) reveal(side, litLine, "y"); }
        }
      }
      raf = video.paused || !back.isConnected ? 0 : requestAnimationFrame(follow);
    };
    const run = () => { if (!raf) raf = requestAnimationFrame(follow); };
    video.addEventListener("play", run);
    video.addEventListener("seeked", () => { if (!raf) follow(); });
    video.addEventListener("ended", () => go(+1));      // the next clip follows on its own
    show(id);
  }

  function openJob(id, force) {
    if (S?.id === id && !force) return;
    closeJob();
    S = fresh(id);
    P = Object.fromEntries(PARTS.map((k) => [k, signal(S)]));
    clipSigs = new Map(); clipNodes.clear(); J.recapStep = null;
    buildJob();
    watch();
    getJSON(`/api/tools/${tool}/options`).then((opts) => { if (S?.id !== id) return; S.recapOn = !!(opts || []).find((o) => o.name === "recap")?.value; changed("recap", "stages"); }).catch(() => {});
    getJSON(`/api/jobs/${tool}/${encodeURIComponent(id)}`).then((info) => { if (S?.id !== id) return; S.info = info; S.status = info.status; api.setTitle?.(info.title || id); changed("head"); })
      .catch((e) => { root.replaceChildren(h("div.card.empty", h("div.result.bad", e.message))); });
    const mine = S;
    closeStream = api.stream(`/api/jobs/${tool}/${encodeURIComponent(id)}/events`, {
      onEvent: (e) => { if (S === mine) take(e); },
      onStatus: (s) => {
        if (S !== mine) return;
        const was = S.running; S.status = s.status; S.running = s.running; if (s.started) S.runStart = s.started;
        S.info = { ...S.info, queue: s.queue || null };
        batch(() => changed("head", "stages", "recap"));
        if (was && !s.running) { api.refreshRequests(); getJSON(`/api/jobs/${tool}/${encodeURIComponent(id)}`).then((i) => { if (S !== mine) return; S.info = i; changed("head"); }).catch(() => loadFailed("lf_info")); }
      },
      onState: (st) => { if (S !== mine) return; S.conn = st; changed("head"); },
    });
    clock = setInterval(() => { if (S?.running) now.value = Date.now() / 1000; }, 1000);
  }

  function closeJob() {
    closeStream?.(); closeStream = null; clearInterval(clock); cancelAnimationFrame(raf); raf = 0; pending = []; unwatch(); S = null;
  }

  openJob(id);
  return { close: closeJob };
}
