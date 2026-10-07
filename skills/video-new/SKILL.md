---
name: video-new
description: Start a new video of the current product - create videos/<video>/, write BRIEF.md, the feature coverage matrix (COVERAGE.md) and the claims sheet (CLAIMS.md), propose chapters, then stop for the reviewer's sign-off. Never builds. Run only when the user types /video-new.
disable-model-invocation: true
argument-hint: "<video> [--format pitch|tour|docs|tutorial|loop]"
---

# /video-new

Write down, before anything is built, what the video must explain and what it may claim, and get
the reviewer to sign both. Then stop.

Why this exists: in the production these skills come from, 9 of 26 versions happened because a
video did not explain a feature the reviewer cared about. Nobody had written those features down
before building, so each one surfaced in a review, cost a full render and QA cycle, and then had
to be applied by hand to every other video. Positioning and claims cost 3 more versions the same
way. Two signed sheets up front are cheaper than any of those rounds.

## Before you start

```bash
PVS_HOME="$(cd "$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/../.." && pwd)"
```

Find the product: the nearest folder above the current directory with a `product.yaml`. If there
is none, tell the user to run `/product-new` first (you cannot run it for them: it is
user-invoked). Read `product.yaml`, `kit/RULES.md` and the BRIEF of any sibling video in
`videos/`: a sibling's coverage matrix and claims are the best starting point, and the cast must
stay identical across videos.

The video id comes from the argument (lowercase, digits, dashes). If `videos/<video>/` exists,
stop: an existing video moves forward with `/video-review`, never by starting over.

## 1. Ask what the video is for

One message, at most four questions, each with a proposed default:

- Who watches it and where it is published (pitch deck, a short product tour, docs page,
  onboarding, landing loop).
- What the viewer must believe or be able to do afterwards (one sentence).
- Roughly how long (defaults: pitch 90 s, tour 30 s, docs 120 s, tutorial 240 s, loop 15 s).
  A tour is a pitch cut to one or two features: same opening, end screen and lockup, fewer
  chapters. Pick it when the reviewer says "quick tour" or asks for under 45 s.
- Which features matter most to the reviewer. Ask for them by name, and ask which of them must
  be shown working rather than mentioned.

## 2. Create the folder

```bash
"$PVS_HOME/bin/pvs-py" "$PVS_HOME/skills/video-new/scripts/new_video.py" <product_dir> <video> \
  --format <format> [--title "<title>"] [--duration <s>]
```

It copies `_template/video`, fills the BRIEF frontmatter (title, video, format, duration, lang
and reviewer from `product.yaml`, version 1) and leaves both signatures empty. It refuses a
duplicate id.

## 3. Write the three sheets

Read `references/sheets.md` for the format of each sheet and worked rows before writing.

- **BRIEF.md**: intent (quote the user's own words), audience, the proposed chapters, notes with
  every fictional name and number the video will use (from the product's cast, never new ones
  without asking), and an empty changelog entry for v1.
- **COVERAGE.md**: one row per feature with "must explain on screen? yes/no", the chapter that
  explains it, and the proof (what the viewer sees happen). A feature that is only named on the
  end screen is not covered: that is exactly the gap that cost the most versions. Include the
  configurable parts (settings, triggers including scheduled ones, handover, follow-ups) because
  those were the features reviewers kept asking for after the fact.
- **CLAIMS.md**: the positioning line (from `product.yaml`, never from a marketing document),
  the phrases to avoid (`never_say` plus anything the user adds), every claim the narration
  wants to make that needs approval, approved taglines, and the canonical product names against
  their legacy strings.

Check every claim and feature against what you can see in `sources/` and the docs. If the
product does not do something the user asked for, say so with a closed question and a
recommended option ("show only what exists" is usually the right default). Do not draft a
feature into the matrix that the code cannot back.

## 4. Propose the chapters

Add the chapter table to BRIEF.md. One idea per chapter, one framing per chapter, every
"must explain" feature mapped to a chapter. Open on context (the product name and one line on
what it is), never mid-UI. Frame the whole page at 1x by default; deep zooms were rejected twice
in the original production. End with breadth (what else the product does), then the lockup.

## 5. Stop and ask for the signatures

Show the user, in one message:

1. The coverage matrix (the "yes" rows) and the chapter table.
2. The positioning line, the claims needing approval, and the proposed tagline.
3. At most three closed decisions, each with a default (for example the tagline, a cast name,
   leaving a feature out). Say what silence means: the default.

Then ask the reviewer to sign. Either they write their name into `coverage_signed_by` and
`claims_signed_by` in BRIEF.md themselves, or they tell you in their own words to sign under
their name, and you run:

```bash
"$PVS_HOME/bin/pvs-py" "$PVS_HOME/skills/video-new/scripts/sign.py" <video_dir> \
  --coverage "<reviewer name>" --claims "<reviewer name>"
```

Never sign on your own initiative, never sign because the sheets "look complete", and never
sign with a name the reviewer did not give. The signature is the reviewer's statement that the
matrix is what they will judge the video against. `sign.py` refuses an empty matrix or a missing
positioning line; with no flags it only shows the status.

Do not build, render, record narration or dispatch subagents here, even if the user signs in the
same message. Building is `/video-build`, typed by the user. This split is what keeps the agent
from starting an expensive build on an unsigned brief.

## Report

| Item | Value |
|---|---|
| Video | `videos/<video>/`, format, target length |
| Coverage | N features to explain on screen, M listed only, chapters |
| Claims | positioning, claims awaiting approval |
| Decisions | the up to three closed questions and their defaults |
| Signatures | unsigned (or signed by whom) |

Next, once signed: `/video-build <video>`.
