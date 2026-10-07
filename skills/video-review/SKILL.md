---
name: video-review
description: Turn a batch of reviewer feedback on the product's videos into one table per video, fix every video that got notes in parallel (one subagent each) while keeping approved parts, re-run QA and parity, bump versions and deliver. Run only when the user types /video-review.
disable-model-invocation: true
argument-hint: "[<feedback text or file>]"
---

# /video-review

One review round: collect the whole batch, consolidate it per video, fix every video that got
notes at the same time, check each result yourself, deliver the next versions, report.

Why batch and parallel: in the production these skills come from, three notes arrived five
minutes apart and the agent started fixing the first one in its own context. The context
filled, the reviewer had to stop it, and said that feedback handled one note at a time was not
efficient. Consolidated into one table and handed to three parallel subagents, the same three
fixes were reviewed and delivered 70 minutes later. A fix is never just a render: editing,
narration, render, QA and the report took 50 to 90 minutes per video, so serial fixes multiply.

## 0. Setup

```bash
PVS_HOME="$(cd "$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/../.." && pwd)"
PY="$PVS_HOME/bin/pvs-py"
```

Find the product (nearest `product.yaml` above the current directory) and list its videos with
their current version and delivery status (`skills/video-build/scripts/stages.py` on each).

## 1. Get the whole batch

If the argument is a file, read it; if it is text, use it. Then ask once: "Is this all the
feedback for this round, for every video? Videos with no notes stay as they are." Wait for the
answer before fixing anything. If notes keep arriving while you consolidate, add them to the
same round; do not start a fix per message.

## 2. Consolidate into one table per video

```bash
"$PY" "$PVS_HOME/skills/video-review/scripts/feedback_table.py" <product_dir> <notes file or -> \
  --out <product_dir>/reviews/round-<date>.md
```

It sorts each note, verbatim, under the video it names (by id, title or heading), puts notes
about "all videos" in a shared section, and lists notes it cannot place. Then you fill, per
row: **Meaning** (your reading, including what must not change), **Acceptance** (how you will
check it: a time range, a strip, a frame), and **Rule for all videos?**

Read `references/review-protocol.md` before filling it: it covers dictation errors, notes that
are really rules, and notes that conflict with the product.

Three questions to ask of every note:

1. Is it really a rule? Then it applies to every video in this round, not only the one the
   reviewer pointed at. A reviewer once gave a coverage rule on one video and had to ask again,
   hours later, for it to be applied to all of them.
2. Does the product actually do it? Check the code before promising a fix. If not, a closed
   question with a recommended option ("show only what exists").
3. Is it a feature that was missing from COVERAGE.md? Then the fix adds the row.

Show the consolidated tables to the user with at most three closed decisions (defaults
stated). Silence means the defaults. Videos without notes are listed as untouched.

## 3. Open the next version of each video with notes

```bash
"$PY" "$PVS_HOME/skills/video-review/scripts/bump_version.py" <video_dir> --note "<quote>" ...
```

It backs up `lines.tsv`, `timings.json` and `video/src` as v<N>, bumps the BRIEF version to
N+1 and opens a changelog section with the quotes. It refuses when v<N> was never rendered
(that would skip a version). The v<N> render stays untouched: it is the parity reference, and a
file the reviewer may have shared is never overwritten.

## 4. One fix subagent per video, all at once

Fill `references/fix-prompt.md` for each video (the reviewer's words verbatim, your meaning and
acceptance, what you already found in the code with `file:line`, the shared rules) and launch
every fixer in the same turn with the Agent tool, in the background. Do the code lookups that
feed "what I already found" yourself before launching, briefly; they save each fixer the same
search and catch notes the product cannot satisfy.

While they run, do not fix anything yourself and do not poll them with messages. Watch files
(`stages.py`, modification times, render logs). If a fixer needs an approval, ask the user one
closed question and relay the answer. If a fixer stops, start a new one with the same prompt
plus where it stopped: the state is in the files.

## 5. Check every result yourself

For each video, whatever the fixer reported:

1. Parity against the previous version, outside the stretches that changed on purpose:
   `"$PY" "$PVS_HOME/skills/render-qa/scripts/parity.py" <old mp4> <new mp4> --skip a:b ...`.
   An approved stretch that changed is a regression: send it back.
2. QA: `"$PY" "$PVS_HOME/skills/render-qa/scripts/qa.py" <video_dir> <new mp4> --strip ...`
   with strips at every changed beat. Load `render-qa` for how to read it; look at the sheets
   and strips yourself.
3. Each note's acceptance check from your table. A note the render does not satisfy goes back
   to the same fixer (SendMessage: the problem, the time range, "change nothing else").
4. The changelog section in BRIEF.md is filled.

## 6. Deliver and close the round

```bash
"$PY" "$PVS_HOME/skills/render-qa/scripts/deliver.py" <video_dir> <new mp4> --archive-previous
```

Then close the round, together: notes that became rules go into `kit/RULES.md` (with the date
and the reviewer's words) so the next build inherits them; each BRIEF changelog is complete. A
rules file that stops being updated becomes wrong, and rules then get repeated by hand in every
prompt. If the reviewer already uploaded previous versions somewhere, say which files need
uploading again.

## 7. Report

| Video | From | To | Notes applied | Where to see it | Parity | QA | Delivered as |
|---|---|---|---|---|---|---|---|

Then: untouched videos, rules added to `kit/RULES.md`, anything unverified, at most three
closed decisions. In the user's language, short, tables first.

## References

- `references/review-protocol.md`: before filling the consolidated tables.
- `references/fix-prompt.md`: before launching the fixers.
