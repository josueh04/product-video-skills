/* ============================================================================
   ui-demo-composer stage kit (GSAP 3, HyperFrames seek-safe).

   Usage inside src/template.tpl, after GSAP and this file are inlined:

     PVS.ready((S) => {            // runs after document.fonts.ready
       S.fadeFromBlack(0.1);
       S.chapter("#ch1", { at: T.ch1, rack: T.rack1 });
       S.clickOn("#row2", T.open1, { hover: "hov" });
       ...
     });                           // registers the timeline when the callback returns

   Seek-safety rules every helper follows (the render seeks each frame from
   several parallel workers, stepping 1 ms back and forward):
   - every property in a fromTo's fromVars is also in its toVars, and every
     fromTo after t = 0 has immediateRender: false;
   - display and class changes are zero-length tl.set calls, never tweens;
   - scrolls are fromTo with explicit start and end;
   - the cursor and the camera warn when a move starts before the previous one
     on the same property has ended (two tweens fighting over one property);
   - no Date, timers or Math.random: everything derives from T (timings.json).
   ========================================================================== */
(function () {
  "use strict";

  /* WebKit UnitBezier, so CSS timing functions of the app run exactly */
  function bez(p1x, p1y, p2x, p2y) {
    const cx = 3 * p1x, bx = 3 * (p2x - p1x) - cx, ax = 1 - cx - bx;
    const cy = 3 * p1y, by = 3 * (p2y - p1y) - cy, ay = 1 - cy - by;
    const sx = (t) => ((ax * t + bx) * t + cx) * t;
    const sy = (t) => ((ay * t + by) * t + cy) * t;
    const dx = (t) => (3 * ax * t + 2 * bx) * t + cx;
    return (x) => {
      if (x <= 0) return 0;
      if (x >= 1) return 1;
      let t = x;
      for (let i = 0; i < 8; i++) {
        const e = sx(t) - x;
        if (Math.abs(e) < 1e-6) return sy(t);
        const d = dx(t);
        if (Math.abs(d) < 1e-6) break;
        t -= e / d;
      }
      let lo = 0, hi = 1; t = x;
      while (lo < hi) {
        const v = sx(t);
        if (Math.abs(v - x) < 1e-6) break;
        if (x > v) lo = t; else hi = t;
        t = (lo + hi) / 2;
        if (hi - lo < 1e-7) break;
      }
      return sy(t);
    };
  }
  const EASE = {
    css: bez(0.25, 0.1, 0.25, 1),       // CSS "ease"
    out: bez(0, 0, 0.58, 1),            // CSS "ease-out"
    in: bez(0.42, 0, 1, 1),             // CSS "ease-in"
    inOut: bez(0.42, 0, 0.58, 1),       // CSS "ease-in-out"
    standard: bez(0.4, 0, 0.2, 1),      // Material standard (drawers, sidebars)
  };

  const CURSOR_SVG = '<svg viewBox="0 0 22 30" width="22" height="30"><path d="M2 2 L2 24 L7.6 18.8 L11.4 27.4 L15 25.8 L11.3 17.4 L19 17.4 Z" stroke-width="1.6" stroke-linejoin="round"/></svg>';

  function cssLen(name, fallback) {
    const v = parseFloat(getComputedStyle(document.documentElement).getPropertyValue(name));
    return isNaN(v) ? fallback : v;
  }
  const round3 = (n) => Math.round(n * 1000) / 1000;

  function create(opts) {
    opts = opts || {};
    const T = opts.T || window.PVS_T;
    if (!T || typeof T !== "object") throw new Error("PVS: no beat table; the template must set window.PVS_T to the beat table JSON, or pass {T: ...}");
    const id = opts.id || "main";
    const cfg = Object.assign({ W: 1440, H: 810, K: 1920 / 1440, X: 0, Y: 0, maxZoom: 1.35, blur: 14 }, window.PVS_STAGE || {}, opts.stage || {});
    cfg.blur = cssLen("--pvs-blur", cfg.blur);
    const app = document.getElementById("app");
    if (!app) throw new Error("PVS: the template has no #app");
    const tl = gsap.timeline({ paused: true, defaults: { ease: "power3.out" } });
    const S = { tl, T, cfg, id, bez, ease: EASE, warnings: [] };
    const warn = (msg) => { S.warnings.push(msg); console.warn("PVS: " + msg); };

    /* ---------- elements and measurement ---------- */
    S.el = (sel) => {
      const e = typeof sel === "string" ? document.querySelector(sel) : sel;
      if (!e) throw new Error("PVS: no element matches " + sel);
      return e;
    };
    S.all = (sel) => {
      const list = typeof sel === "string" ? Array.from(document.querySelectorAll(sel)) : [].concat(sel);
      if (!list.length) throw new Error("PVS: no element matches " + sel);
      return list;
    };
    /* layout box in app pixels (offsets up to #app; camera scale and transforms do not affect it) */
    S.box = (sel) => {
      const target = S.el(sel);
      // elements inside a hidden pop-up or panel have no layout: show their hidden ancestors
      // for the measurement only (inline styles are restored right after)
      const shown = [];
      for (let e = target; e && e !== app; e = e.parentElement) {
        if (getComputedStyle(e).display === "none") {
          shown.push([e, e.style.display]);
          e.style.display = e.classList.contains("pvs-modal") ? "flex" : "block";
        }
      }
      let el = target, x = 0, y = 0;
      const w = el.offsetWidth, h = el.offsetHeight;
      while (el && el !== app) { x += el.offsetLeft; y += el.offsetTop; el = el.offsetParent; }
      shown.reverse().forEach(([e, d]) => { e.style.display = d; });
      if (el !== app) warn("box(" + sel + ") is not inside #app; its position is relative to the page");
      return { x, y, w, h, cx: x + w / 2, cy: y + h / 2 };
    };
    /* start time of a word of a narration clip, from T.W (written by buildlib) */
    S.w = (clip, word) => {
      const m = (T.W || {})[clip];
      if (!m) throw new Error("PVS: no clip " + clip + " in T.W");
      const k = String(word).toLowerCase();
      if (!(k in m)) throw new Error("PVS: word '" + word + "' not in " + clip + ": " + Object.keys(m).join(" "));
      return T[clip] + m[k];
    };

    /* ---------- state ---------- */
    S.init = (sel, vars) => { gsap.set(sel, vars); tl.set(sel, vars, 0); return S; };
    S.set = (sel, vars, t) => { tl.set(sel, vars, t); return S; };
    S.show = (sel, t, display) => { tl.set(sel, { display: display || "block" }, t); return S; };
    S.hide = (sel, t) => { tl.set(sel, { display: "none" }, t); return S; };
    const baseClass = new WeakMap();
    /* class state: S.state("#btn", "hov", t) sets the authored classes plus "hov"; null resets */
    S.state = (sel, extra, t) => {
      S.all(sel).forEach((el) => {
        if (!baseClass.has(el)) baseClass.set(el, el.getAttribute("class") || "");
        const base = baseClass.get(el);
        tl.set(el, { attr: { class: extra ? (base + " " + extra).trim() : base } }, t);
      });
      return S;
    };
    S.hover = (sel, t) => S.state(sel, "hov", t);
    S.fadeIn = (sel, t, d, y) => {
      d = d == null ? 0.25 : d; y = y || 0;
      tl.fromTo(sel, { opacity: 0, y }, { opacity: 1, y: 0, duration: d, ease: EASE.out, immediateRender: false }, t);
      return S;
    };
    S.fadeOut = (sel, t, d) => { tl.to(sel, { opacity: 0, duration: d == null ? 0.2 : d, ease: "power2.in" }, t); return S; };
    /* a seeded PRNG for anything that should look random but render the same every time */
    S.rng = (seed) => { let s = (seed >>> 0) || 1; return () => { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; return ((s >>> 0) % 1e6) / 1e6; }; };

    /* ---------- camera (app coordinates in, screen transform out) ---------- */
    let camBusy = -1;
    const camXY = (s, cx, cy) => {
      let x = 960 - (cfg.X + cx * cfg.K) * s, y = 540 - (cfg.Y + cy * cfg.K) * s;
      x = Math.min(0, Math.max(1920 - 1920 * s, x));
      y = Math.min(0, Math.max(1080 - 1080 * s, y));
      return { x, y };
    };
    S.cam = (t, s, at, d, ease) => {
      d = d == null ? 0.9 : d;
      if (s > cfg.maxZoom + 1e-6) { warn("camera " + s + "x at " + t + " s is above max_zoom " + cfg.maxZoom + "; clamped"); s = cfg.maxZoom; }
      if (s < 1) { warn("camera " + s + "x at " + t + " s is below 1x and would show outside the stage; clamped to 1"); s = 1; }
      let cx = cfg.W / 2, cy = cfg.H / 2;
      if (typeof at === "string" || (at && at.nodeType)) { const b = S.box(at); cx = b.cx; cy = b.cy; }
      else if (Array.isArray(at)) { cx = at[0]; cy = at[1]; }
      if (t < camBusy - 1e-6) warn("camera move at " + t + " s starts before the previous one ends (" + round3(camBusy) + " s)");
      camBusy = t + d;
      const p = camXY(s, cx, cy);
      tl.to("#camera", { x: p.x, y: p.y, scale: s, duration: d, ease: ease || "power2.inOut" }, t);
      return S;
    };
    S.camReset = (t, d, ease) => S.cam(t, 1, null, d, ease);
    /* the plan buildlib writes into T.CAM: [{t, s, at, d, ease}] */
    S.camPlan = (plan) => { (plan || T.CAM || []).forEach((m) => S.cam(m.t, m.s, m.at, m.d, m.ease)); return S; };

    /* ---------- focus: blur and veil travel together ---------- */
    /* The veil also turns hit-testable from the first frame of a rack in to the last frame of a
       rack out. The contrast pass of `hyperframes check` skips text flagged
       data-layout-allow-occlusion only while its probe points hit another element, so product
       text is ignored exactly while it is blurred and audited again once in focus. A timeline
       set (not a DOM event) keeps this seek-safe. */
    S.rack = (t, on, d) => {
      d = d == null ? 0.6 : d;
      const ease = on ? "power2.out" : "power2.inOut";
      tl.to("#blurWrap", { filter: on ? "blur(" + cfg.blur + "px)" : "blur(0px)", duration: d, ease }, t);
      tl.to("#veil", { opacity: on ? 1 : 0, duration: d, ease }, t);
      tl.set("#veil", { pointerEvents: on ? "auto" : "none" }, on ? t : t + d);
      return S;
    };

    /* ---------- title lines through their mask ---------- */
    S.lineIn = (sel, t, d) => {
      tl.fromTo(sel, { yPercent: 110, opacity: 1 }, { yPercent: 0, opacity: 1, duration: d == null ? 0.75 : d, ease: "expo.out", immediateRender: false }, t);
      return S;
    };
    S.lineOut = (sel, t, d) => {
      d = d == null ? 0.45 : d;
      tl.fromTo(sel, { yPercent: 0, opacity: 1 }, { yPercent: -110, opacity: 1, duration: d, ease: "power3.in", immediateRender: false }, t);
      tl.set(sel, { opacity: 0 }, t + d);
      return S;
    };
    /* every .pvs-ln of a .pvs-ttl block: in at tIn (number, or one time per line), out at tOut */
    S.title = (sel, tIn, tOut, o) => {
      o = o || {};
      const lines = S.el(sel).querySelectorAll(".pvs-ln");
      lines.forEach((ln, i) => {
        S.lineIn(ln, Array.isArray(tIn) ? tIn[i] : tIn + i * (o.stagger == null ? 0.12 : o.stagger), o.d);
        if (tOut != null) S.lineOut(ln, tOut + i * 0.04, o.dOut);
      });
      return S;
    };
    /* a chapter: rack in (unless already out of focus), title in, title out, rack out */
    S.chapter = (sel, o) => {
      if (!o || o.at == null || o.rack == null) throw new Error("PVS: chapter(" + sel + ") needs {at, rack}");
      if (!o.blurred) S.rack(o.at, true, 0.6);
      S.title(sel, o.at + 0.25, o.rack - 0.1, o);
      S.rack(o.rack, false, o.dRack == null ? 0.8 : o.dRack);
      return S;
    };

    /* ---------- cursor and clicks (app pixels; the tip is at the element origin) ---------- */
    let curBusy = -1;
    const cur = "#pvsCur", rip = "#pvsRip";
    S.cursorAt = (x, y, t) => { tl.set(cur, { x, y }, t == null ? 0 : t); return S; };
    S.cursorShow = (t, d) => { tl.to(cur, { opacity: 1, duration: d == null ? 0.3 : d, ease: "power1.out" }, t); return S; };
    S.cursorHide = (t, d) => { tl.to(cur, { opacity: 0, duration: d == null ? 0.3 : d, ease: "power1.in" }, t); return S; };
    S.move = (x, y, t, d) => {
      d = d == null ? 0.6 : d;
      if (t < curBusy - 1e-6) warn("cursor move at " + t + " s starts before the previous one ends (" + round3(curBusy) + " s)");
      curBusy = t + d;
      tl.to(cur, { x, y, duration: d, ease: "power2.inOut" }, t);
      return S;
    };
    const point = (sel, o) => {
      const b = S.box(sel);
      return { x: b.x + (o.ax == null ? b.w / 2 : o.ax) + (o.dx || 0), y: b.y + (o.ay == null ? b.h / 2 : o.ay) + (o.dy || 0) };
    };
    S.moveTo = (sel, t, d, o) => { const p = point(sel, o || {}); return S.move(p.x, p.y, t, d); };
    S.click = (x, y, t) => {
      tl.to(cur, { scale: 0.86, duration: 0.07, ease: "power2.in", transformOrigin: "2px 2px" }, t);
      tl.to(cur, { scale: 1, duration: 0.16, ease: "power2.out" }, t + 0.07);
      tl.fromTo(rip, { x, y, scale: 0.3, opacity: 0.9 }, { x, y, scale: 1.5, opacity: 0, duration: 0.45, ease: "power2.out", immediateRender: false }, t);
      return S;
    };
    /* travel to an element, hover it, click it at t (the click sfx belongs to the same t in build.py) */
    S.clickOn = (sel, t, o) => {
      o = o || {};
      const p = point(sel, o);
      const travel = o.travel == null ? 0.6 : o.travel;
      if (travel > 0) S.move(p.x, p.y, t - travel - 0.15, travel);
      if (o.hover) S.state(o.hoverEl || sel, o.hover === true ? "hov" : o.hover, t - 0.12);
      S.click(p.x, p.y, t);
      if (o.hover && o.unhover != null) S.state(o.hoverEl || sel, null, o.unhover);
      return p;
    };

    /* ---------- typing and streaming ---------- */
    const charSpans = (el, text) => {
      el.textContent = "";
      for (const ch of text) { const s = document.createElement("span"); s.textContent = ch; el.appendChild(s); }
      return Array.from(el.children);
    };
    /* types text into an element, one span per character, evenly over d seconds */
    S.type = (sel, text, t, d) => {
      const el = S.el(sel);
      const spans = charSpans(el, text);
      S.init(spans, { opacity: 0 });
      tl.to(spans, { opacity: 1, duration: 0.01, stagger: { amount: Math.max(0, d - 0.01) }, ease: "none" }, t);
      return S;
    };
    const wordify = (el) => {
      const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      const nodes = [];
      while (walker.nextNode()) nodes.push(walker.currentNode);
      for (const n of nodes) {
        const frag = document.createDocumentFragment();
        n.textContent.split(/(\s+)/).forEach((p) => {
          if (!p) return;
          if (/^\s+$/.test(p)) frag.appendChild(document.createTextNode(p));
          else { const s = document.createElement("span"); s.className = "pvs-w"; s.textContent = p; frag.appendChild(s); }
        });
        n.parentNode.replaceChild(frag, n);
      }
      return Array.from(el.querySelectorAll(".pvs-w"));
    };
    /* streams the words already in an element (an agent reply, a generated summary) over d seconds */
    S.stream = (sel, t, d) => {
      const words = wordify(S.el(sel));
      S.init(words, { opacity: 0 });
      tl.to(words, { opacity: 1, duration: 0.12, stagger: { amount: Math.max(0, d - 0.12) }, ease: "none" }, t);
      return S;
    };
    /* a caret that blinks every 0.53 s between t0 and t1 (zero-length sets, seek-safe) */
    S.blink = (sel, t0, t1, period) => {
      period = period || 0.53;
      let on = true;
      for (let t = t0; t < t1; t += period) { tl.set(sel, { opacity: on ? 1 : 0 }, round3(t)); on = !on; }
      tl.set(sel, { opacity: 0 }, t1);
      return S;
    };

    /* ---------- pop-ups (.pvs-modal > .pvs-backdrop + .pvs-box) ---------- */
    S.popupOpen = (sel, t, o) => {
      o = o || {};
      const m = S.el(sel), box = m.querySelector(".pvs-box"), bd = m.querySelector(".pvs-backdrop");
      if (!box) throw new Error("PVS: popup " + sel + " has no .pvs-box");
      const sc = o.scale == null ? 0.7 : o.scale, y = o.y == null ? 30 : o.y, d = o.d == null ? 0.3 : o.d, delay = o.delay == null ? 0.06 : o.delay;
      tl.set(m, { display: "flex" }, t);
      if (bd) tl.set(bd, { opacity: 1 }, t);
      tl.set(box, { opacity: 0, scale: sc, y }, t);
      tl.fromTo(box, { opacity: 0, scale: sc, y }, { opacity: 1, scale: 1, y: 0, duration: d, ease: o.ease || EASE.out, immediateRender: false }, t + delay);
      return S;
    };
    S.popupClose = (sel, t, o) => {
      o = o || {};
      const m = S.el(sel), box = m.querySelector(".pvs-box"), bd = m.querySelector(".pvs-backdrop");
      const d = o.d == null ? 0.2 : o.d, bdAt = o.backdropAt == null ? 0.3 : o.backdropAt;
      tl.fromTo(box, { opacity: 1, scale: 1, y: 0 }, { opacity: 0, scale: o.scale == null ? 0.9 : o.scale, y: 0, duration: d, ease: EASE.in, immediateRender: false }, t);
      if (bd) tl.set(bd, { opacity: 0 }, t + bdAt);
      tl.set(m, { display: "none" }, t + Math.max(d, bdAt) + 0.01);
      return S;
    };

    /* ---------- toast ---------- */
    S.toast = (sel, t, hold, o) => {
      o = o || {};
      const y = o.y == null ? 18 : o.y;
      tl.fromTo(sel, { opacity: 0, y }, { opacity: 1, y: 0, duration: 0.2, ease: EASE.out, immediateRender: false }, t);
      if (hold != null) tl.fromTo(sel, { opacity: 1, y: 0 }, { opacity: 0, y: 0, duration: 0.2, ease: EASE.in, immediateRender: false }, t + hold);
      return S;
    };

    /* ---------- scroll an inner column inside its viewport (clamped to the real range) ---------- */
    S.scroll = (sel, from, to, t, d, ease) => {
      const el = S.el(sel), vp = el.parentElement;
      const max = Math.max(0, el.scrollHeight - vp.clientHeight);
      const clamp = (v) => {
        if (v > max + 0.5) { warn("scroll(" + sel + ") to " + v + " px is past the end (" + max + " px); clamped"); return max; }
        return Math.max(0, v);
      };
      from = clamp(from); to = clamp(to);
      tl.fromTo(el, { y: -from }, { y: -to, duration: d == null ? 0.8 : d, ease: ease || "power2.inOut", immediateRender: false }, t);
      return S;
    };
    /* the scroll offset that puts an element's top at `pad` px below the viewport top */
    S.scrollTarget = (sel, inner, pad) => {
      const el = S.el(sel), base = S.el(inner);
      let y = 0, e = el;
      while (e && e !== base) { y += e.offsetTop; e = e.offsetParent; }
      return Math.max(0, y - (pad || 0));
    };

    /* ---------- opening, end screen, lockup, fades ---------- */
    S.fadeFromBlack = (t, d) => { tl.to("#fade", { opacity: 0, duration: d == null ? 0.8 : d, ease: "power1.out" }, t == null ? 0.1 : t); return S; };
    S.fadeToBlack = (t, d) => { tl.to("#fade", { opacity: 1, duration: d == null ? 0.7 : d, ease: "power1.in" }, t); return S; };
    /* end screen: rack in, background up, headline and cards on the words that name them */
    S.endScreen = (t, o) => {
      o = o || {};
      if (!o.blurred) S.rack(t, true, 0.7);
      tl.set("#endS", { opacity: 1 }, t);
      tl.fromTo("#endS .pvs-end-bg", { opacity: 0 }, { opacity: 1, duration: 0.5, ease: "power1.out", immediateRender: false }, t);
      if (o.head) S.title(o.head[0], o.head[1], null, { d: 0.8 });
      (o.cards || []).forEach(([sel, tc]) => {
        tl.fromTo(sel, { opacity: 0, y: 40, scale: 0.98 }, { opacity: 1, y: 0, scale: 1, duration: 0.7, ease: "expo.out", immediateRender: false }, tc);
      });
      return S;
    };
    /* lockup: only the end screen CONTENT leaves; its background stays until the lockup is up,
       so no sharp frame of the product flashes between them */
    S.lockup = (t, o) => {
      o = o || {};
      tl.fromTo("#endS .pvs-end-content", { opacity: 1, y: 0 }, { opacity: 0, y: -30, duration: 0.5, ease: "power2.in", immediateRender: false }, t);
      tl.set("#lock", { opacity: 1 }, t + 0.35);
      const part = (sel, at, from) => {
        if (!document.querySelector(sel)) return;
        tl.fromTo(sel, Object.assign({ opacity: 0 }, from), Object.assign({ opacity: 1, y: 0, scale: 1, duration: 0.7, ease: "expo.out", immediateRender: false }, {}), at);
      };
      part("#lock .pvs-lkLogo", o.logo == null ? t + 0.4 : o.logo, { y: 16, scale: 1 });
      part("#lock .pvs-lkT", o.title == null ? t + 0.55 : o.title, { y: 40, scale: 0.96 });
      part("#lock .pvs-lkS", o.sub == null ? t + 0.95 : o.sub, { y: 24, scale: 1 });
      part("#lock .pvs-lkU", o.url == null ? t + 1.5 : o.url, { y: 0, scale: 1 });
      return S;
    };

    /* ---------- initial state of the shared layers ---------- */
    const cursorEl = document.querySelector(cur);
    if (cursorEl && !cursorEl.innerHTML.trim()) cursorEl.innerHTML = CURSOR_SVG;
    S.init("#camera", { x: 0, y: 0, scale: 1, transformOrigin: "0 0" });
    S.init("#fade", { opacity: opts.startBlack === false ? 0 : 1 });
    S.init("#blurWrap", { filter: opts.startFocused ? "blur(0px)" : "blur(" + cfg.blur + "px)" });
    S.init("#veil", { opacity: opts.startFocused ? 0 : 1, pointerEvents: opts.startFocused ? "none" : "auto" });
    const q = (s) => Array.from(document.querySelectorAll(s));
    if (q(".pvs-ttl .pvs-ln").length) S.init(".pvs-ttl .pvs-ln", { yPercent: 110, opacity: 0 });
    if (q("#endS .pvs-ln").length) S.init("#endS .pvs-ln", { yPercent: 110, opacity: 0 });
    if (q("#endS").length) S.init("#endS", { opacity: 0 });
    if (q(".pvs-card").length) S.init(".pvs-card", { opacity: 0, y: 40 });
    if (q("#lock").length) S.init("#lock", { opacity: 0 });
    if (q("#lock > *").length) S.init("#lock > *", { opacity: 0 });
    if (cursorEl) S.init(cur, { opacity: 0, x: cfg.W * 0.6, y: cfg.H * 0.7 });
    if (q(rip).length) S.init(rip, { opacity: 0 });
    if (q(".pvs-modal").length) S.init(".pvs-modal", { display: "none" });
    if (q(".pvs-toast").length) S.init(".pvs-toast", { opacity: 0 });
    /* Intentional layering, so the layout audit of `hyperframes check` does not flag it. The audit
       reads the flags on each text element (not inherited): the product text sits under the veil,
       titles and pop-up backdrops by design, and the titles sit over the product. Masks clip their
       lines on purpose while a line travels. Pass {auditApp: true} to PVS.ready to leave the product
       text unflagged and let check audit layering inside the app (expect veil findings). */
    const flagLayers = () => {
      const texty = (root) => Array.from(root.querySelectorAll("*")).filter((e) => Array.from(e.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim()));
      if (!opts.auditApp) texty(app).forEach((e) => { e.setAttribute("data-layout-allow-occlusion", ""); e.setAttribute("data-layout-allow-overlap", ""); });
      q(".pvs-ttl, #endS, #lock").forEach((r) => texty(r).forEach((e) => { e.setAttribute("data-layout-allow-overlap", ""); e.setAttribute("data-layout-allow-occlusion", ""); }));
      q(".pvs-ttl, #endS, #lock, .pvs-mask").forEach((e) => e.setAttribute("data-layout-allow-overflow", ""));
    };

    S.register = () => {
      flagLayers();          // after the build, so typed and streamed spans are flagged too
      publish(id, tl);
      window.__pvsWarnings = S.warnings;
      return tl;
    };
    return S;
  }

  /* build after fonts load (positions depend on text metrics), register when the build is done */
  function ready(fn, opts) {
    const go = () => { const S = create(opts); fn(S); return S.register(); };
    return document.fonts && document.fonts.ready ? document.fonts.ready.then(go) : Promise.resolve().then(go);
  }

  /* The registration is written after ready() on purpose: `hyperframes check`
     (gsap_timeline_registered_before_async_build) flags a window.__timelines assignment that
     appears in the source before document.fonts.ready when any .to/.fromTo follows, which is
     every template that writes its own tweens. At runtime it still runs after the build. */
  function publish(id, tl) {
    window.__timelines = window.__timelines || {};
    window.__timelines[id] = tl;
    if (window.__hfForceTimelineRebind) window.__hfForceTimelineRebind();
  }

  window.PVS = { create, ready, bez, EASE };
})();
