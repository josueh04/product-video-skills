# QA gate before any delivery

Nothing reaches the reviewer until every box is ticked. Agents report "clean" more often than
they are; whoever delivers re-runs the evidence (REPORT.md, sheets, strips) personally.
`"$PY"` is `"$PVS_HOME/bin/pvs-py"` and `"$S"` is `"$PVS_HOME/skills/render-qa/scripts"`, as in SKILL.md.

## 1. Build and lint

- [ ] `build.py` prints the expected duration and clip count, and its timing table has no
      beat landing before the word it is anchored to.
- [ ] `lint_motion.py <video_dir>/video` (seek-safe-motion): 0 errors.
- [ ] `npx --yes hyperframes@<pinned> check`: 0 lint errors and 0 runtime warnings, with its
      output in a file. Expected findings: layout or contrast caused by the product's real
      tokens, titles over the blurred product, intentional overlaps marked with
      `data-layout-allow-occlusion`, overflow in boxes that really scroll. Anything else gets
      fixed. Real defects it caught: `clipped_text` (a name 4 px too wide),
      `multiple_root_compositions`, `gsap_non_transform_motion`.
- [ ] `banned_terms.py <video_dir>/video/src <video_dir>/audio/lines.tsv`: clean. Old product
      names, vendors, competitors and real customer names out of the template and the script.

## 2. Stills before rendering

- [ ] `snapshot . --at <every setup beat, every modal, every end-screen state> --no-end
      --describe false -o <dir>` (`--describe false`: no frame goes to an external vision API).
- [ ] Look at every still: whole sections in frame, no label cut by a frame edge, pop-ups
      complete and centred, no empty or broken field, no overflowing text, fonts loaded,
      icons are the originals from the product's code.
- [ ] For every new tween: a snapshot at its start time and a bit later, against one at the
      later time alone. The frames must match (seek-safety).
- [ ] Trace the position and visibility of every moving element across its whole life. `check`
      once passed a video whose moving cards were invisible in three of four stretches.

## 3. Render

- [ ] `render . -o renders/<video>-v<N>.mp4 --fps <fps> --quality delivery`, output to a log
      file. A new file name per version; never delete an older render.
- [ ] `"$PY" "$S/scan_render.py" renders/<video>-v<N>.mp4`: no `WORKER PATTERN` line.

## 4. Full QA

- [ ] `"$PY" "$S/qa.py" <video_dir> renders/<video>-v<N>.mp4`, then read `qa/REPORT.md`:
  - loudness within 1 LU of `voice.mix_lufs`, true peak at or under -1 dBFS, 0 clipped samples;
  - no black frames except the intended fades;
  - clicks classified: inside an SFX or a consonant is fine, outside every clip is a defect;
  - no overlapping narration;
  - ASR match at 0.93 or more, and every multi-word diff read;
  - no banned term heard, shown or scripted; camera zoom warnings confirmed or fixed.
- [ ] Look at EVERY contact sheet in `qa/sheets/`.
- [ ] Strips at 5 to 6 fps around every modal open and close, scroll, camera move, chapter
      change, changed beat and the end screen to lockup handoff, and look at each one.
- [ ] `"$PY" "$S/edges.py" <mp4> <video_dir>`, and listen to every marked edge in the mix.
- [ ] If this version edits an approved one: `"$PY" "$S/parity.py" approved.mp4 new.mp4 --skip A:B`
      for each beat that changed on purpose; mean diff under 1.0 everywhere else.

## 5. Deliver (only when the user asks)

- [ ] BRIEF.md updated: structure table, a `### v<N>` section with what changed, sources,
      assumptions.
- [ ] `"$PY" "$S/deliver.py" <video_dir> <mp4> --archive-previous`. It refuses a failed, draft or
      mismatched report; do not work around a refusal, fix what it names.
- [ ] Message to the reviewer: one table (video, version, duration, what changed) plus at
      most three decisions, each with a recommended default. Closed questions with a default
      get answered in minutes; open lists of things to veto never get answered.
- [ ] If an earlier version was uploaded anywhere, say that the upload is now stale.
