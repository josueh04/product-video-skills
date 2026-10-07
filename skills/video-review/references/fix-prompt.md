# Fix prompt: apply one review round to one video

The coordinator fills every `<...>` and sends this to one background subagent per video that
received feedback, all in parallel. Videos without feedback are not touched and get no agent.
The prompt is self-contained: the subagent sees nothing of the review conversation.

---

You are fixing <PRODUCT NAME>, video `<VIDEO>`, from v<N> to v<N+1>, after the reviewer's
feedback, then rendering and QA-checking the new version. Work autonomously; list choices for
veto in your report.

## Read first

1. `<PRODUCT_DIR>/kit/RULES.md` and `product.yaml`. Breaking a rule means rejection.
2. `<VIDEO_DIR>/BRIEF.md` (structure, notes, changelog), `COVERAGE.md`, `CLAIMS.md`,
   `video/build.py`, `video/src/template.tpl`, `video/src/app.css`, `audio/lines.tsv`.
3. <MODEL TO IMITATE, if the reviewer named one: `<PRODUCT_DIR>/videos/<other>/...` and why>.

Load these skills with the Skill tool as the fix needs them: `ui-demo-composer`,
`seek-safe-motion`, `render-qa`, and `script-and-voice` if a line changes, `product-truth` if a
claim changes, `ui-spec-from-code` if a new screen is needed.

## Hard limits

- Write only inside `<VIDEO_DIR>/` (`video/`, `audio/`, `qa/`, `BRIEF.md`, `COVERAGE.md`).
  `deliveries/`, `kit/`, `sources/` and other videos are read-only.
- No browser, no preview servers, no downloads. Never kill a process you did not start: other
  fixers are rendering on this machine right now.
- Fictional data only. None of: <BANNED TERMS / NEVER-SAY>. Never print a secret.
- Product truth: UI 1:1 from the specs and `sources/`. No source, no screen.

## The reviewer's feedback (verbatim, original language)

<"quote 1" (at 0:42)>
<"quote 2">

Meaning: <the coordinator's reading in one paragraph, including what must NOT change>.
Acceptance: <how the coordinator will check each note, e.g. "the settings chapter at 1x, no
crop of any label, strip at 48 to 52 s">.
<If a note is a rule for every video: "This note applies to every video of the round; apply it
here too, even where the reviewer did not point at it.">

## What I already found (verify, line numbers approximate)

- <file:line and the values or functions involved>
- <timings that will shift, narration lines to rewrite with their new text>
- <traps: e.g. "resetting the zoom alone leaves the sections under the header">

## Keep what was approved

Everything the reviewer did not mention was approved in v<N>. Change only what the notes need.
Before you start, the coordinator ran `bump_version.py`, so v<N> is backed up
(`audio/lines-v<N>.tsv`, `audio/timings-v<N>.json`, `video/_v<N>-src/`) and its render
`video/renders/<VIDEO>-v<N>.mp4` is the parity reference. Never overwrite it.

## Process

1. Edit; `python build.py`; `npx --yes hyperframes@<HF_VERSION> check` (0 errors, 0 runtime
   warnings); the `seek-safe-motion` lint.
2. Narration, only if a line changed: `tts.py <VIDEO_DIR> --only <ids>` (at most two takes per
   line), then rebuild. Every other line keeps its take.
3. Snapshots at every changed beat; look at every frame.
4. Render `renders/<VIDEO>-v<N+1>.mp4` with the line build.py prints.
5. Parity: `bin/pvs-py skills/render-qa/scripts/parity.py renders/<VIDEO>-v<N>.mp4
   renders/<VIDEO>-v<N+1>.mp4 --skip <a>:<b> ...` with one skip per stretch that changed on
   purpose (shift later stretches if the timing moved; compare the unchanged prefix with
   `--end`). It must pass outside the skips: if an approved stretch changed, that is a
   regression to fix, not a note to report.
6. QA: `bin/pvs-py skills/render-qa/scripts/qa.py <VIDEO_DIR> <mp4> --strip <name>:<t0>:<t1>`
   around every change, every modal and the end screen. Look at every sheet and strip. Fix and
   re-render under the same v<N+1> name until it passes.
7. BRIEF.md: update the structure table, and fill the `### v<N+1>` section the coordinator
   opened (feedback quoted, changes, sources for new screens, parity numbers, how to revert).
   If the fix adds a feature, add its row to COVERAGE.md marked "added in v<N+1> from review".

Do not deliver and do not copy anything to `deliveries/`.

## Report (under 300 words)

MP4 path and duration; per note: what changed and where to see it (time); parity (max diff
outside the skips, the skips used); QA summary (loudness, true peak, clicks, overlaps, ASR,
worker pattern, black frames, sheets and strips); anything unverified; choices for veto.
