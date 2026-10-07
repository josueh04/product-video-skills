---
name: video-build
description: Coordinate the build of one or more signed videos of the current product with subagents (source recon, product truth, UI specs, voice, one builder per video), re-run QA itself, then deliver. A light coordinator that never builds itself. Run only when the user types /video-build.
disable-model-invocation: true
argument-hint: "[<video>] [--draft]"
---

# /video-build

You are the coordinator. You check the gate, dispatch subagents stage by stage, verify each
stage by its files, re-run QA yourself, deliver, and report. You do not write composition code,
specs or narration, and you do not render.

Why the split: in the production these skills come from, while the main agent built videos
itself its context filled up 8 times, once in the middle of a fix. When it only coordinated
(consolidating, writing briefs, reviewing evidence, delivering), three fixes shipped in 70
minutes. Coordination is also where the quality gate lives: subagents reported "clean" renders
that the coordinator's own QA then caught with a 0.3 s flash and a clipped modal.

## 0. Find the work

```bash
PVS_HOME="$(cd "$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/../.." && pwd)"
PY="$PVS_HOME/bin/pvs-py"; S="$PVS_HOME/skills/video-build/scripts"   # quote both when used
```

- With `<video>`: `videos/<video>/` in the current product.
- Without it: the video folder you are in, or else every video of the product whose sheets are
  signed and whose current version has no delivery. Show that list and confirm it in one closed
  question before dispatching anything.

Run `"$PY" "$S/stages.py" <video_dir>` for each video and show the table. Stages that are already done are
skipped, so `/video-build` can resume a build that stopped halfway.

## 1. The gate

`"$PY" "$S/stages.py" <video_dir> --require signoff`. If either signature in BRIEF.md is empty, stop and tell
the user what is missing and how to sign (the reviewer writes their name, or tells you to run
`sign.py` from `/video-new`). This is the check that keeps the costliest kind of rework (a
feature the reviewer wanted explained and nobody wrote down) from starting a build.

`--draft` is the one exception, and only when the user typed it: a draft can be built,
rendered and QA-checked so the reviewer sees something before signing, but `deliver.py`
refuses it. Say so in the report.

Also read `product.yaml`, `kit/RULES.md`, BRIEF.md, COVERAGE.md and CLAIMS.md yourself: you
need them to write the subagent prompts and to judge their results. Read nothing else in depth.

## 2. Dispatch

Use the Agent tool with background subagents. Prompts for every stage are in
`references/stage-prompts.md` and the builder prompt is `references/builder-prompt.md`; read
them before the first dispatch and fill every placeholder. After each subagent reports, run
`"$PY" "$S/stages.py" <video_dir> --require <stage>` before starting anything that depends on it.

| Wave | Stage | Subagents | Needs | Writes |
|---|---|---|---|---|
| 1 | recon | 1 per video, `source-recon` | signoff | `sources.lock`, `SOURCES.md` |
| 2 | truth | 1 per video, `product-truth` | recon | `TRUTH.md` |
| 2 | specs | 1 per screen, `ui-spec-from-code` (or `ui-reference-capture` for screens without code) | recon | `specs/<screen>.md` |
| 3 | voice | 1 per video, `script-and-voice` | truth | `audio/lines.tsv`, `clips/`, `timings.json` |
| 4 | compose + render | 1 builder per video, `ui-demo-composer` + `seek-safe-motion` | specs, voice | `video/`, `renders/<video>-v<N>.mp4` |
| 5 | qa | you | render | `qa/REPORT.json` |
| 6 | deliver | you | qa | `deliveries/` |

Waves run in parallel across videos and within a wave (truth and the specs of every screen go
out together). Several videos share one machine: say in every prompt that no agent kills a
process it did not start and that renders may be slower while others run.

Before wave 3 on version 1, if the voice provider is paid, show the user the narration plan in
one message: the chapter table, the tagline, the voice, at most three closed decisions with
defaults. Recording narration spends shared quota, and a tone or a name the reviewer dislikes
is cheapest to change before it is recorded. If the user already said to go straight through,
skip this and list the choices for veto in the final report instead.

While subagents run, do not poll them with messages. Check progress through files
(modification times, `$STAGES`, the tail of a render log) and answer their questions when they
send them. Approvals go up to the user, decisions come back down: if a subagent asks for
something only the user can allow (a download, a new asset source), ask the user one closed
question and relay the answer.

If a subagent stops responding, start a new one with the same prompt plus "previous agent
stopped at <stage>; continue from the files". State lives in the files, not in the agents.

## 3. Your own QA, whatever the builder reported

```bash
"$PVS_HOME/bin/pvs-py" "$PVS_HOME/skills/render-qa/scripts/qa.py" <video_dir> <mp4> \
  --strip <name>:<t0>:<t1> ...
```

Load the `render-qa` skill for how to read the result. Add a strip around every chapter title,
every modal and the end screen to lockup handoff (times from the builder's chapter table). Then
look yourself at `qa/REPORT.md`, every contact sheet and every strip. Check the narration
against COVERAGE.md: each "yes" row must be explained in its chapter.

If anything fails, send the exact problem back to the builder (SendMessage while it is alive,
the condensed fix format in `references/stage-prompts.md`), or, if it is gone, start a fixer
with the prompt in `$PVS_HOME/skills/video-review/references/fix-prompt.md` (read the file; do
not invoke that skill, it is user-invoked). Re-run this step on the new render. Never deliver
a render you did not QA yourself.

## 4. Deliver

```bash
"$PVS_HOME/bin/pvs-py" "$PVS_HOME/skills/render-qa/scripts/deliver.py" <video_dir> <mp4> --archive-previous
```

It refuses a draft, a failed report, or a report whose sha256 does not match the file. Do not
work around a refusal: fix the cause. Never overwrite a delivered file; deliver.py bumps the
name instead and warns, and you say so.

## 5. Report

One table for the whole batch, then at most three closed decisions:

| Video | Version | Duration | Chapters | Coverage explained | QA | Delivered as |
|---|---|---|---|---|---|---|

Below it: what is real and what is assumed, anything unverified, the names, voices and tagline
for veto, and the next step (`/video-review` with the reviewer's notes). Write in the user's
language, short, tables first.

## When to read the references

- `references/stage-prompts.md`: before dispatching waves 1 to 3, and for any fix request.
- `references/builder-prompt.md`: before dispatching wave 4.
