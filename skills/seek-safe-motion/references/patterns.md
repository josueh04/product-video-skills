# Seek-safe patterns

Before and after code for each lint rule, and helpers that are safe by construction. Times
come from the build (`T.<beat>`), which anchors every beat to a word of the narration.

## SS001: fromVars keys missing from toVars

```js
// Unsafe: opacity exists only in fromVars. One worker renders the title invisible.
tl.fromTo("#title .line", { yPercent: 110, opacity: 1 }, { yPercent: 0, duration: 0.75, ease: "expo.out" }, T.open);

// Safe: the same keys on both sides.
tl.fromTo("#title .line", { yPercent: 110, opacity: 1 },
  { yPercent: 0, opacity: 1, duration: 0.75, ease: "expo.out", immediateRender: false }, T.open);

// Also safe: set, then tween.
tl.set("#title .line", { yPercent: 110, opacity: 1 }, T.open);
tl.to("#title .line", { yPercent: 0, duration: 0.75, ease: "expo.out" }, T.open);
```

## SS003 and SS004: immediate render and from()

```js
// Unsafe: writes opacity 0 at build time, over the state an earlier beat left.
tl.from("#card", { opacity: 0, y: 12, duration: 0.3 }, T.card);

// Safe
tl.fromTo("#card", { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.3, immediateRender: false }, T.card);
```

## SS005: display and visibility

```js
// Unsafe: display cannot interpolate; it flips somewhere inside the 0.3 s.
tl.to("#menu", { display: "none", opacity: 0, duration: 0.3 }, T.close);

// Safe: fade, then a zero-duration set at an explicit time.
tl.to("#menu", { opacity: 0, duration: 0.3 }, T.close);
tl.set("#menu", { display: "none" }, T.close + 0.3);
```

## SS006: deterministic "randomness" and clocks

```js
// A seeded generator: same sequence in every worker and every render.
function seeded(seed) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}
const rnd = seeded(42);
const gaps = TEXT.split("").map(() => 0.05 + rnd() * 0.04);  // typing rhythm

// A timer on screen comes from the timeline time, never from Date.
const tl = gsap.timeline({ paused: true, onUpdate: () => {
  const s = Math.max(0, tl.time() - T.callStart);
  timer.textContent = `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;
}});
```

## SS007, SS011, SS012: one paused timeline, registered after the build

```js
document.fonts.ready.then(() => {
  layoutAll();                       // positions measured from the real text metrics
  const tl = gsap.timeline({ paused: true, defaults: { ease: "power3.out" } });
  build(tl);                         // every tween added here
  window.__timelines["main"] = tl;   // registered last; the key matches data-composition-id
  if (window.__hfForceTimelineRebind) window.__hfForceTimelineRebind();
});
```

## Helpers that are safe by construction

```js
// Initial state: written now AND at time 0 of the timeline, so seeking to 0 restores it.
const init = (sel, vars) => { gsap.set(sel, vars); tl.set(sel, vars, 0); };

// Title line through a mask.
const lineIn = (sel, t, d = 0.75) => tl.fromTo(sel, { yPercent: 110, opacity: 1 },
  { yPercent: 0, opacity: 1, duration: d, ease: "expo.out", immediateRender: false }, t);
const lineOut = (sel, t, d = 0.45) => tl.to(sel, { yPercent: -110, duration: d, ease: "power3.in" }, t);

// Typing: each character is a span shown by a zero-duration set.
const typeChars = (chars, t0, dur) => chars.forEach((c, i) => tl.set(c, { opacity: 1 }, t0 + (i * dur) / chars.length));

// Scroll: explicit start and end, clamped by the caller to real line boxes.
const scrollCol = (sel, from, to, t, d = 0.6) =>
  tl.fromTo(sel, { y: -from }, { y: -to, duration: d, ease: "power2.inOut", immediateRender: false }, t);

// Click: press and release are separate tweens that never overlap.
function click(t) {
  tl.to("#cursor", { scale: 0.86, duration: 0.07, ease: "power2.in" }, t);
  tl.to("#cursor", { scale: 1, duration: 0.16, ease: "power2.out" }, t + 0.07);
  tl.fromTo("#ripple", { scale: 0.3, opacity: 0.9 }, { scale: 1.5, opacity: 0, duration: 0.45, immediateRender: false }, t);
}

// Class and state changes: zero-duration sets, never tweens.
const state = (sel, cls, t) => tl.set(sel, { attr: { class: cls } }, t);
```

## What the lint sees and what it does not

| Sees | Does not see |
|---|---|
| Literal object vars in `to`, `from`, `fromTo`, including `startAt` | Vars built at runtime (`Object.assign`, spreads, variables): counted as "not checkable" |
| `Date`, `performance.now`, `Math.random`, timers, `requestAnimationFrame` outside comments | A clock read inside a library loaded with `<script src>` |
| `gsap.timeline()` without `paused: true`; `.play()`; a missing `__timelines` registration | Registration before an async build finished |
| `display`, `visibility` and layout keys in tweens | Two tweens on one property overlapping in time |
| Tweens whose target string selects `.clip` | A `.clip` element reached through a variable |

For what it cannot see, use the snapshot reproduction in SKILL.md, and read the build's
timing table for overlapping beats on the same element.
