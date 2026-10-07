---
name: render-qa
description: >
  Check a rendered product video before anyone else sees it: worker-pattern flicker, black
  frames, loudness and true peak, clipping, clicks at clip edges, overlapping narration,
  speech to text against the script, banned terms and legacy names, camera zoom, contact
  sheets, frame strips at transitions and parity against the approved version; then write
  qa/REPORT.json, the only thing deliver.py accepts. Use it after every HyperFrames render,
  whenever someone asks "is the render clean", "QA this", "check the video", "check the
  audio", "why does it flicker", "there is a click", "compare v3 with v2", "did the approved
  part change", or before showing, sending, uploading or delivering any MP4, even when the
  request does not say QA. Also use it to triage a defect a reviewer reported in a render.
---

# Render QA

A render is not done when the renderer exits. It is done when the evidence says it is clean:
the automatic report, every contact sheet looked at, strips at every transition looked at,
and the narration edges listened to. In the production these skills come from, subagents
reported renders as clean that had a 0.3 s UI flash before the lockup, a clipped modal and
a title that vanished on every third frame. The scripts and the strips found all three.

The scripts live next to this file. Resolve the workbench once:

```bash
PVS_HOME="$(cd "$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/../.." && pwd)"
PY="$PVS_HOME/bin/pvs-py"
S="$PVS_HOME/skills/render-qa/scripts"
```

Keep the interpreter and the script folder in separate variables and quote both
(`"$PY" "$S/qa.py"`): one variable holding a command plus a path is not split by zsh and
breaks in bash as soon as a path has a space.

`<video_dir>` is `products/<slug>/videos/<video>/` (it holds `BRIEF.md`, `audio/`, `video/`).

## The gate, in order

1. **Before rendering.** Run the motion lint (`seek-safe-motion` skill), `hyperframes check`,
   and snapshots of every setup beat. `check` alone is not enough: it once passed a video in
   which moving elements were invisible for three of their four stretches. The pre-render
   steps are in `references/checklist.md`.
2. **Right after the render**, the fast scan (a few seconds):
   `"$PY" "$S/scan_render.py" <mp4>`. A `WORKER PATTERN` line means a seek-safety bug: stop and fix
   the timeline (see `seek-safe-motion`), do not run the rest yet.
3. **The full report**: `"$PY" "$S/qa.py" <video_dir> <mp4>`. It runs every automatic check, writes
   `qa/REPORT.json` and `qa/REPORT.md`, contact sheets in `qa/sheets/`, strips in
   `qa/strips/` (each outlier run and the last 5 s), and the transcript in `qa/asr.txt`.
   About 15 s for a 2 to 3 minute 60 fps video on a recent Mac, speech to text included.
   Read `REPORT.md` top to bottom, including the warnings and every ASR diff.
4. **The pass by eye.** The report ends with what the scripts cannot see. Do all of it:
   - Look at every contact sheet, not a sample.
   - Make strips at 5 to 6 fps around every modal open and close, scroll, camera move,
     chapter change, beat that changed in this version, and the end screen to lockup
     handoff: `"$PY" "$S/strips.py" <mp4> <video_dir>/qa/strips modal:21.0:23.4:8 lockup:57:60`.
     A 1 fps sheet samples one frame per second; a 0.3 s flash fits between two samples.
   - Run `"$PY" "$S/edges.py" <mp4> <video_dir>` and listen to every edge it marks.
   - If this version edits an approved one, prove the rest did not move:
     `"$PY" "$S/parity.py" <approved.mp4> <new.mp4> --skip 41.0:48.5`.
   How to read sheets, strips and parity output: `references/reading-sheets-and-strips.md`.
5. **Triage** every failure and warning with `references/triage.md`: it lists the real
   defects these checks found and the false positives, with how each was told apart. Fix
   the cause in the source (template, build, lines.tsv, audio), rebuild, re-render, and run
   the gate again from step 2. Never edit `index.html` by hand: the build regenerates it.
6. **Delivery** is not this skill's call. `deliver.py` runs only when the user, or a
   user-invoked skill the user started (`/video-build`, `/video-review`), asks to deliver.
   It refuses unless the report passed, is not a draft and matches the MP4 byte for byte.

## What the checks measure

| Check | Fails when | Why this threshold |
|---|---|---|
| `size`, `fps` | size differs from `video.size`; fps only warns | A wrong size is a broken render; a different fps can be intended (30 vs 60) |
| `worker_pattern` | a run of 4 or more outlier frames all on one frame index mod 3 | HyperFrames renders with 3 interleaved workers; one losing state hits every third frame |
| `outliers` | never (warning) | Scrolls at full speed, blur racks and camera returns make isolated outliers too; look at each strip |
| `black_frames` | mean luma under 3 outside the first 1 s and last 2 s | Fades from and to black are intended; black mid-video is a bug |
| `voice_overlap` | two voice clips' spoken words overlap by more than 20 ms | Measured on word timings, not clip bounds: silent tails overlapping is fine |
| `loudness` | integrated loudness more than 1 LU from `voice.mix_lufs` | Delivered finals measured -16.8 to -15.3 LUFS for a -16 target |
| `true_peak` | above -1.0 dBFS | Headroom for the lossy encoders of upload platforms |
| `clipping` | any sample at 0.995 or more on a real channel | Measured per channel, not on a downmix, so one clipped side is not hidden |
| `clicks_outside_clips` | an impulsive click outside every audio clip | Inside an SFX is expected; inside voice it is almost always a consonant |
| `abrupt_edges` | never (warning) | A sound ending in 5 ms outside an SFX is usually a badly trimmed clip; listen |
| `asr` | word match under 0.93, or skipped | Finals measured 0.953 to 0.988; script compared in playback order, not file order |
| `banned_terms_*` | a banned term, never-say phrase or legacy name heard, visible in index.html, or in lines.tsv | From `product.yaml`; the live UI may still show an old name, the video must not |
| `camera_zoom` | never (warning) above `video.max_zoom` | Full-page screens at about 2x were rejected twice as "super zoomed in"; a zoomed-out canvas tolerates more |
| `motion_lint` | the seek-safe-motion lint reports an error | Catches the timeline bugs before they cost a render |

`--no-asr` makes the report fail on purpose: a narration that drifted from the script is
exactly what a reviewer hears first. Speech to text uses whisper `small.en` for English and
the multilingual `small` model for any other `lang` (it downloads once if missing).

## The report contract

`qa/REPORT.json` follows `docs/contracts.md`: `mp4` (relative to the video folder), `sha256`,
`created`, `draft`, `checks` (`name`, `passed`, `detail`, and `level: warn` for warnings),
`passed`. It also carries `draft_reason`, `probe`, `artifacts` and the ASR diffs. `draft` is
true when either signature in `BRIEF.md` is empty or `video/index.html` carries
`<meta name="pvs-draft" content="1">` (written by `build.py --draft`). A draft can pass every
check and still never be delivered: unsigned coverage is how a video ends up missing the
feature the reviewer cared about.

## Delivering (only when asked)

```bash
"$PY" "$S/deliver.py" <video_dir> <mp4> [--archive-previous] [--dry-run]
```

It copies to `<product_dir>/deliveries/` as `review.naming` (default
`{product} {video} v{version}.mp4`, version from `BRIEF.md`) with an APFS clone where
possible, verifies the copy byte for byte, and writes `<same name>.BRIEF.md` beside it. It
never overwrites: the same bytes again is a no-op, different bytes under a delivered name
bump the version in the file name (then bump `BRIEF.md` to match). `--archive-previous`
moves older versions of the video into `deliveries/previous/` so the reviewer's folder holds
only the latest. After delivering, tell the reviewer in one table: video, version, duration,
what changed, and at most three open decisions, each with a recommended default. Any copy
already uploaded somewhere is now stale: say so.

## Rules that come from incidents

- **Re-run the evidence yourself.** When a subagent says a render is clean, read its
  `REPORT.md`, open the sheets and strips, and check the sha256 matches the file you will
  deliver. "Clean" from an agent is a claim, the report is evidence.
- **Every version gets its own file name** in `renders/`; never delete an older one. Overwrite
  only a version the reviewer has not seen yet, inside a fix cycle.
- **Never kill processes you did not start** (Chrome, ffmpeg, node): other agents render on
  the same machine.
- **Snapshots without the vision API**: pass `--describe false` to `hyperframes snapshot`, so
  no frame of an unreleased product leaves the machine.
- **Spelling-only ASR diffs are fine** (a brand word heard as two words, a time written in
  words). Read each diff before deciding; a diff of several words is a cut or garbled line.

## Scripts

| Script | Use |
|---|---|
| `qa.py <video_dir> <mp4> [--out DIR] [--no-asr] [--strip name:t0:t1[:fps]]` | The full report; exit 1 when not passed |
| `scan_render.py <mp4> [--json]` | Fast flicker, black and loudness scan; exit 1 on worker pattern or mid-video black |
| `qa_full.py <video_dir> <mp4> [--out DIR] [--no-asr]` | The measurements alone, as `REPORT.txt` |
| `sheets.py <mp4> <outdir> [--fps 1]` | 1 fps contact sheets, 4x4 |
| `strips.py <mp4> <outdir> name:t0:t1[:fps] ...` | Labelled strips around transitions (default 6 fps) |
| `edges.py <mp4> <video_dir or index.html>` | Level before and after every narration clip |
| `parity.py <old> <new> [--end T] [--skip A:B] [--threshold 1.0] [--audio]` | Frame parity; exit 1 above the threshold |
| `banned_terms.py [--product DIR] [--text T] [FILE or DIR ...]` | Banned terms, never-say phrases and legacy names; exit 1 on hits |
| `deliver.py <video_dir> <mp4> [--archive-previous] [--dry-run]` | The delivery gate |

`banned_terms.find_banned(text, product)` returns `[(term, kind)]` for other skills to reuse.

## References

- `references/checklist.md`: the whole gate as boxes to tick, from build to the reviewer
  message. Read it before the first render of a video and before any delivery.
- `references/reading-sheets-and-strips.md`: what to look for in sheets, strips, crops,
  parity and the numeric checks (bright-pixel counts, diff boxes). Read it when doing step 4.
- `references/triage.md`: every failure this QA produced, real or false, and how it was told
  apart and fixed. Read it as soon as any check fails or warns.
