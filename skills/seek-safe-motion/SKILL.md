---
name: seek-safe-motion
description: >
  The animation rules that keep HyperFrames' parallel render workers from dropping, flashing
  or flickering elements, plus a static lint (lint_motion.py) that finds the violations in a
  video's template before it costs a render. Use it whenever you write or edit GSAP tweens,
  timelines, cursors, camera moves, typing, scrolls or pop-ups in a HyperFrames composition
  or a video's src/template.tpl, whenever a render shows flicker, stutter, an element that
  vanishes on some frames, a title that flashes, or a "WORKER PATTERN" line from
  scan_render.py or qa.py, and whenever the preview looks right but the MP4 does not. Also
  use it to review someone else's timeline code before rendering.
---

# Seek-safe motion

HyperFrames does not play the timeline. It seeks it: for every frame the renderer sets the
timeline to that frame's time and captures the page. With HyperFrames 0.8.x it does this
with three workers in parallel, each taking every third frame, and each seek steps 1 ms back
and then forward to settle. So every frame must be a pure function of its time. Anything that
depends on what was rendered before, on the clock, or on chance renders differently in each
worker, and the result is an element that is missing on every third frame.

That bug is invisible in the Studio preview (which plays in order) and in single snapshots.
In the production these skills come from it was the only defect that reached the reviewer:
the opening title "stuttering and flashing" for its first seven seconds.

## Lint first

```bash
PVS_HOME="$(cd "$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/../.." && pwd)"
"$PVS_HOME/bin/pvs-py" "$PVS_HOME/skills/seek-safe-motion/scripts/lint_motion.py" <video_dir>/video
```

It reads `index.html`, `src/*.tpl` and the `*.js` beside them (inline scripts only), prints
`file:line: severity RULE: why` plus the fix, and exits 1 on any error (`--strict` makes
warnings fail too, `--json` for tools). Run it after every edit to the timeline and before
every render. It is static: it cannot see vars computed at runtime (it counts them as "not
checkable") or two tweens overlapping in time. Those stay on you, with the reproduction
below. `qa.py` (render-qa) runs it too and fails the report on an error.

## The rules, and why each exists

1. **Every key in a `fromTo`'s fromVars also appears in its toVars** (SS001, error). When a
   worker's frame lands exactly on a tween's start, the 1 ms step back reverts the tween to
   before it started, and a key that only exists in fromVars is never written again. The
   title tween was `fromTo(sel, {yPercent: 110, opacity: 1}, {yPercent: 0})`: `opacity: 1`
   lived only in fromVars, so one worker kept the title at opacity 0 for the rest of the
   tween. Write `{yPercent: 110, opacity: 1}` to `{yPercent: 0, opacity: 1}`, or a `tl.set()`
   followed by a `tl.to()`. The same goes for `startAt` inside a `to()` (SS002).
2. **`immediateRender: false` on every `fromTo` after time 0** (SS003, warning). Otherwise the
   tween writes its start values when the timeline is built, over whatever earlier tweens set,
   and a seek into the middle of the timeline starts from the wrong state.
3. **Prefer `fromTo` to `from`** (SS004, warning). A `from()` ends on whatever the element was
   at build time; once earlier tweens touch the element, workers disagree on that.
4. **Never animate `display` or `visibility`** (SS005, error). They cannot be interpolated;
   they flip at an arbitrary point of the tween. Change them with a zero-duration `tl.set()`
   at an explicit time, and fade with `opacity` or `autoAlpha`.
5. **No clock, no chance, no timers** (SS006, error): no `Date`, `performance.now()`,
   `Math.random()`, `setTimeout`, `setInterval` or `requestAnimationFrame` for anything
   visible. A typing jitter or a waveform uses a seeded generator; a call timer shown on
   screen is computed from `tl.time()` inside the timeline's `onUpdate`.
6. **One paused timeline, registered, never played** (SS007, SS011, SS012). Create it with
   `gsap.timeline({ paused: true })`, build it completely (inside `document.fonts.ready` when
   positions depend on text metrics), and only then assign
   `window.__timelines["<composition id>"] = tl`. Registering an empty timeline before the
   build finishes renders a blank video; `tl.play()` fights the renderer's seeks.
7. **Scrolls are `fromTo` with explicit start and end** so every worker computes the same
   offset, clamped to the real content so no line or icon stops cut at an edge.
8. **Never two tweens on the same property of the same element at once.** A cursor reset that
   fell inside the next move left the pointer in the wrong place after a seek. Not linted:
   check the timing table of the build.
9. **Animate transforms, not layout** (SS009, warning): `x`, `y`, `scale`, `clip-path` instead
   of `left`, `top`, `width`, `margin`. Layout tweens reflow every frame and `hyperframes
   check` flags them as `gsap_non_transform_motion`. A short width change on a real product
   control (a sidebar expanding) can be accepted when it reproduces the product.
10. **Never tween a `.clip` element** (SS010, error). HyperFrames owns a clip's visibility
    through `data-start` and `data-duration`; animate a wrapper inside it.
11. **Finite repeats** (SS008, warning). `repeat: -1` is only allowed under a finite root
    `data-duration`; compute a count with `Math.max(0, Math.floor(span / period) - 1)`.
12. **Set every initial state explicitly at time 0.** A helper that does `gsap.set(sel, vars)`
    should also do `tl.set(sel, vars, 0)`, so seeking back to 0 restores the first frame
    instead of keeping the last state a worker rendered.

## Reproduce a suspected bug before rendering

The lint finds patterns; a snapshot proves pixels. For a suspect tween starting at `t0`:

```bash
npx --yes hyperframes@<pinned> snapshot . --at <t0 + 0.3> --no-end --describe false -o a
npx --yes hyperframes@<pinned> snapshot . --at <t0>,<t0 + 0.3> --no-end --describe false -o b
```

The frame at `t0 + 0.3` must be identical in `a` and `b`. If it differs, seeking through the
tween start changed the state. To replay one worker exactly, snapshot frames `0, 3, 6, ...`
in that order up to just past the tween. Bisect by halving the time range until one tween is
left. After rendering, `scan_render.py` (render-qa) reports the same bug as a `WORKER
PATTERN` run: outlier frames that all share one frame index mod 3.

## References

- `references/patterns.md`: before and after code for each rule, the helpers that keep a
  template safe (`lineIn`, `init`, typing, scrolls, cursor clicks) and what the lint can and
  cannot see. Read it when writing a new helper or fixing a lint finding.
