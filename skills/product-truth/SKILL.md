---
name: product-truth
description: Back every sentence of a video's narration (audio/lines.tsv) and every screen it shows with a citation into the pinned source code (role/path:line@sha) or a docs URL, mark what is visible in the UI versus backend-only, flag restricted or unreleased features, and cut or rewrite anything unbacked; writes the video's TRUTH.md and checks it with truth_check.py. Use it whenever a script or narration is drafted or edited, before voice is generated, before a build, when someone asks "can we say this?", "is this true?", "does the product really do X?", when a reviewer asks for a feature or a claim the product may not support, and when a source document (pitch deck, PRD, marketing page) makes claims the video wants to repeat.
---

# Product truth

A product video that shows something the product cannot do is worse than no video. In the
production these skills come from, the costliest moments were all truth failures: a hand-built
badge with the wrong size and the wrong product name, a workflow narrated as "waiting for the
call result" when the product only returns results through a separate trigger, a test call
relabeled as a confirmed booking that nobody had verified end to end, and a company document
whose headline contradicted the positioning the team had agreed on. Each one was caught late,
by a reviewer, and cost a version.

This skill makes the check explicit and mechanical: every line and every screen gets a row in
TRUTH.md with a source, and `truth_check.py` refuses a video where any row is missing, stale or
unbacked.

## Inputs

- `videos/<video>/audio/lines.tsv` (the narration, one sentence per line id)
- `videos/<video>/SOURCES.md` (from source-recon: the screens and their code)
- `videos/<video>/BRIEF.md`, `COVERAGE.md`, `CLAIMS.md` (what the video must explain, the
  positioning, phrases to avoid, claims that need approval)
- `product.yaml`: `positioning`, `never_say`, `names` (canonical name to legacy strings),
  `banned_terms`
- `sources/<role>/` and `sources.lock` (pinned by source-recon; if missing, run source-recon
  first, because citations must point at the locked commit)

## 1. List the claims

Split every line of lines.tsv into the claims it makes. "Acme Tasks reads your calendar and
moves overdue tasks to tomorrow" is two claims: it reads the calendar, and it moves overdue
tasks. Add one claim per screen and per on-screen action from SOURCES.md and the chapters
("clicking Plan my day opens the planner with three suggestions").

Write the questions those claims raise, phrased so code can answer them: what triggers this,
what is stored, which options exist, what the user sees and where, what happens only on the
server.

## 2. Answer them from code and docs

Launch read-only subagents in parallel, one per product area (frontend behaviour, each backend,
docs), with the prompt in `references/product-facts-prompt.md`. Point them at `sources/<role>/`,
never at the user's checkout, so their line numbers match the lock. They answer only from code
or docs, cite every fact, and say "not found" instead of guessing.

## 3. Classify each claim

| visibility | means | the video can |
|---|---|---|
| `ui` | Rendered by the frontend; cite the template or i18n line | show it and narrate it |
| `backend` | True on the server, nothing on screen shows it | narrate it, never draw a UI for it |
| `docs` | Only the docs say it | narrate it with the docs URL; check the code agrees when it can |
| `mock` | A designed piece, not product UI (a phone call screen, an end card, generated text) | show it, marked as designed in the BRIEF |

| verdict | means |
|---|---|
| `backed` | the source says exactly this |
| `approved` | needed sign-off (restricted, unreleased, a claim CLAIMS.md lists) and the reviewer gave it in CLAIMS.md |
| `needs-approval` | true, but restricted, gated, unreleased or listed in CLAIMS.md; waiting for the reviewer |
| `rewrite` | partly true; you propose backed wording in the notes |
| `cut` | not true, or no source found |
| `unbacked` | not checked yet |
| `mock` | with visibility `mock` only |

Only `backed` and `approved` pass for narrated lines. A restricted feature (visible only to some
roles, plans or internal teams), a feature behind a flag, or one on an unmerged branch is
`needs-approval` until the reviewer says yes in CLAIMS.md, and the BRIEF notes that it is
restricted. That happened in the source production: a feature only internal staff could see was
shown at the reviewer's request, and marked.

## 4. Fix what does not hold

- **Rewrite** a partly true sentence into the strongest version the source supports. Keep the
  meaning the writer wanted; change the mechanics to the real ones.
- **Cut** what has no source. Do not soften it into something vague; vague claims are still
  claims.
- **Never let a label drift.** A designed piece marked "illustrative" must not lose that label
  for aesthetics later without re-checking the claim the unlabeled version makes.
- **Positioning wins over documents.** If a deck or PRD says something `never_say` or CLAIMS.md
  forbids, the rule wins and the sentence changes.
- **Current names only.** Use the canonical names in `product.yaml names`, even when the live UI
  or the code still shows a legacy string. Grep lines.tsv, specs and templates for every legacy
  string and every `banned_terms` entry (competitors, third-party vendors the team keeps off
  screen, real customers) and fix each hit.

## 5. When a request conflicts with the product

When the brief or the reviewer asks for something the code does not support, do not build a
fake and do not silently drop it. Ask one closed question with options and a recommended
default, and keep at most three such questions per round, because open-ended lists of vetoes
go unanswered and the silence becomes a decision nobody made. The "only what's real" pattern:

> The brief shows Acme Tasks booking the meeting room itself. The code only creates the task
> and links the room's calendar (frontend/src/rooms/LinkRoom.tsx:22@1a2b3c4); booking happens in
> the calendar app. Which one?
> 1. **Only what's real (recommended):** show the link step and say "links the room's calendar".
> 2. Show the calendar app's booking screen as a designed piece, labeled, and narrate it as the
>    calendar's step.
> 3. Drop the beat.

Record the answer in CLAIMS.md and set the verdict from it.

## 6. Write TRUTH.md

```markdown
# Truth: <video>

Locked: frontend main@1a2b3c4, backend main@5d6e7f8. Checked: 2026-01-12.

| id | sentence | source | visibility | verdict | notes |
|---|---|---|---|---|---|
| N1 | Acme Tasks plans your day from your calendar. | frontend/src/planner/plan.ts:31@1a2b3c4; https://docs.example.com/planner | ui | backed | |
| N2 | Overdue tasks move to tomorrow at midnight. | backend/jobs/rollover.py:12-30@5d6e7f8 | backend | backed | not shown on screen |
| screen:board | Board with three tasks, one overdue | frontend/src/pages/board/BoardPage.tsx:14@1a2b3c4 | ui | backed | |
| screen:call | Phone call with the customer | (designed) | mock | mock | marked in BRIEF |

## Open questions
1. <closed question with a recommended answer>
```

One row per line id of lines.tsv, with the sentence copied exactly (the check compares them, so
editing a line after the truth pass fails until you re-verify it). One row per screen, with id
`screen:<name>` matching SOURCES.md. Several citations go in one cell, separated by `;`.

## 7. Check it

```bash
PVS_HOME="$(cd "$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/../.." && pwd)"
"$PVS_HOME/bin/pvs-py" "$PVS_HOME/skills/product-truth/scripts/truth_check.py" <video_dir>
```

It fails on a line without a row, a changed sentence, a verdict other than backed or approved
on a narrated line, a citation whose role is not locked, whose sha is not the locked one (the
code moved; re-verify), whose file is not in the export, or whose line is past the end of the
file. Fix every failure; do not edit the check.

Report to the user: how many lines and screens are backed, what you rewrote and cut (with the
reason), what waits for approval, and the open questions.
