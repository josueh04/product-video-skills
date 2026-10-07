# Builder prompt: one video, composition to render

The coordinator fills every `<...>` and sends this as the prompt of one background subagent per
video (several videos in parallel). It is self-contained on purpose: the subagent sees nothing
of the coordinator's conversation, and a replacement agent must be able to pick the work up
from this prompt and the files alone. Keep the twelve parts even when a part is short; each one
is there because a build went wrong without it.

---

You are building one product video with HyperFrames: <PRODUCT NAME>, video `<VIDEO>` v<N>,
from the signed brief to a rendered, QA-checked MP4. Work autonomously: do not ask questions.
When you must choose (a cast detail, a tagline, a voice), decide, and list the choice for veto
in your report.

## 1. Read first, in this order

1. `<PRODUCT_DIR>/kit/RULES.md` and `<PRODUCT_DIR>/product.yaml` (positioning, names, cast,
   banned terms, voice). Follow them exactly.
2. `<VIDEO_DIR>/BRIEF.md`, `COVERAGE.md` and `CLAIMS.md` (both signed by <REVIEWER>). The
   coverage matrix is what the reviewer will judge: every "yes" row must be explained on screen
   in its chapter, not only listed at the end.
3. `<VIDEO_DIR>/SOURCES.md`, `TRUTH.md`, `specs/*.md` and the narration in `audio/lines.tsv`
   with `audio/timings.json`.
4. <SIBLING VIDEO, if any: `<PRODUCT_DIR>/videos/<sibling>/video/` for the app shell and
   components to reuse, and why>.

## 2. Skills to load (Skill tool)

- `ui-demo-composer`: the stage, camera, titles, cursors, typing, pop-ups, end screen, and the
  `build.py` that anchors every beat to a word of the narration.
- `seek-safe-motion`: the motion rules. Run its lint before every render.
- `render-qa`: the checks you run on your own render before reporting.
- `ui-spec-from-code` only if a screen in the chapters has no spec yet (one nested read-only
  subagent per missing screen).

## 3. Where you may write

Only `<VIDEO_DIR>/video/` and `<VIDEO_DIR>/qa/`, plus `<VIDEO_DIR>/BRIEF.md` (structure table
and notes). Everything else is read-only: `sources/`, `kit/`, other videos, the workbench.
Never write to `<PRODUCT_DIR>/deliveries/`: the coordinator delivers after its own QA.

## 4. Hard limits (restated because breaking one means rejection)

- No browser and no preview servers unless the coordinator said otherwise. Never the
  reviewer's personal browser.
- Never kill a process you did not start: other agents render on this machine.
- No downloads. Assets come from `kit/` and `sources/` only.
- Fictional data only: the cast in product.yaml, 555 numbers, example domains. Nothing from a
  real workspace.
- Never print a secret. Never read `.env`; scripts load keys themselves.
- None of these on screen or in narration: <BANNED TERMS and NEVER-SAY PHRASES>. Product
  names exactly as: <CANONICAL NAMES vs LEGACY STRINGS>.

## 5. Product truth

Rebuild the UI 1:1 from the specs, which cite `<role>/<path>:<line>@<sha>`. If a screen or a
behaviour has no source, do not show it: invented UI is the fastest way to lose the reviewer's
trust. Keep the real look, but fix visible production glitches (padding, overflow, clipped
text, native media players) and note each fix in BRIEF.md.

## 6. Content

Chapters (from BRIEF.md, target <DURATION> s):

<CHAPTER TABLE: # | chapter | what it shows | coverage rows | target s>

The narration is fixed and timed (`audio/timings.json`). Do not rewrite lines. If a beat cannot
fit a line, say so in the report with the line id; the coordinator decides.

## 7. What the coordinator already found

<FILE:LINE pointers, traps, components to reuse, anything verified in the code. "Nothing yet"
is acceptable but write it.>

## 8. Narration and sound

Timing has one source: the words in `timings.json`. Every beat is `T[clip] + word time`, so a
regenerated line moves everything with it. SFX from `audio/sfx/` only (recorded sounds, no
whoosh, no music bed unless the brief says so).

## 9. Look, pacing and motion

- Open on context: the product title over the UI racked out of focus, never mid-UI.
- One idea per chapter, one framing per chapter, a two-tone chapter title over the blurred
  product, changes 0.6 to 1 s apart, a hold of about 0.8 s at the end of each chapter.
- The whole page at 1x by default; pop-ups centred at natural size; push-ins only gentle (up to
  `video.max_zoom`, never cutting a label). A video in the original production was rejected
  twice for deep zooms.
- Seek-safety: every property in a `fromTo` `from` is also in its `to`; never tween `display`;
  no `Date`, `Math.random` or timers. A title once vanished every third frame because parallel
  render workers seek independently; it was invisible in the preview.
- End screen with breadth (what else the product does), then the lockup with the tagline from
  CLAIMS.md.

## 10. Process and QA gate

1. `python build.py` (the signatures are set, so no `--draft`), then
   `npx --yes hyperframes@<HF_VERSION> check` with 0 errors and 0 runtime warnings, then the
   motion lint.
2. Snapshots at every chapter start and every pop-up; look at each frame.
3. Render from `video/`: `npx --yes hyperframes@<HF_VERSION> render . -o renders/<VIDEO>-v<N>.mp4
   --fps <FPS> --quality delivery` (build.py prints this exact line).
4. `bin/pvs-py skills/render-qa/scripts/qa.py <VIDEO_DIR> <mp4>` and add `--strip name:t0:t1`
   around every modal, every chapter title and the end screen to lockup handoff. Look at every
   contact sheet and strip: a 1 fps pass once missed a 0.3 s flash before a lockup.
5. Fix and re-render under the same version name until QA passes. Never overwrite a render of a
   previous version.

## 11. Delivery

Do not deliver and do not copy anything to `deliveries/`. Report; the coordinator re-runs QA
itself and delivers.

## 12. Report (under 400 words)

- MP4 path and duration.
- Chapter table with start times, and which coverage row each chapter explains.
- QA summary: loudness and true peak, clipping, clicks, overlaps, ASR match, worker pattern,
  black frames, and what you saw in the sheets and strips.
- For veto: names, tagline, any voice you picked.
- Sources used (file paths) and production glitches fixed.
- Anything you could not verify or could not fit.
