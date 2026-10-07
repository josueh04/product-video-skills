# The three sheets of a new video

Worked examples use the fictional product Acme Tasks (a to-do app) and its cast: Northwind
Bakery, Maya Lindqvist (owner), Omar Haddad (customer).

## COVERAGE.md

| Feature | Must explain on screen? | Chapter | Proof (what the viewer sees) |
|---|---|---|---|
| Plan my day | yes | 2. Your day, planned | Maya clicks "Plan my day"; tasks reorder by due time; the narration says why the order changed |
| Recurring tasks | yes | 3. Set it once | The repeat picker opens at natural size, "Every weekday" is chosen, the next five dates appear |
| Shared lists | yes | 4. Work together | Omar is invited; his avatar appears on the list; a task assigned to him moves to his view |
| Reminders | yes | 3. Set it once | A reminder is set for 8 AM; the notification preview appears |
| Integrations | no | End screen | Listed among "Acme Tasks also works with" |
| Settings: theme, week start | yes | 5. Your way | The settings page at 1x, week start changed to Monday, the calendar re-renders |

Rules for writing it:

- "Explain" means shown working, with narration that says what it does for the viewer. The
  test: could a viewer who never saw the product describe the feature after watching?
- Settings and configuration get their own rows. In the original production, the most repeated
  note was "you also need to explain how it is configured", across four videos.
- Every trigger type gets a row when the product has triggers, including scheduled ones. A
  missing schedule example cost a version.
- Anything the reviewer agrees to leave out goes under "Deliberately out", with the reason.
  Silence about a feature is how it comes back in a review.
- The proof column names concrete UI states and fictional data, never "shows the feature".

## CLAIMS.md

- **Positioning**: one sentence, from `product.yaml` `product.positioning` unless the reviewer
  corrects it now. Never from a deck or a marketing page: a company document once used the exact
  phrase the team had banned.
- **Phrases to avoid**: `product.never_say`, plus anything the reviewer adds, each with its
  reason. These get grepped in the script and checked in the ASR transcript.
- **Claims that need approval**: numbers ("saves 3 hours a week"), comparisons, anything about
  security, compliance, AI, pricing or availability, and any feature that is behind a flag or
  not launched. Each gets the source you found (`<role>/<path>:<line>` or a docs URL) and an
  Answer column the reviewer fills.
- **Approved taglines**: propose one or two for the lockup; the reviewer picks.
- **Product names**: canonical name against the legacy strings the live UI may still show
  (`product.names`). The video always uses the canonical name, even when the real UI is wrong.

## BRIEF.md body

- **Intent**: who asked, their words quoted, what the video shows and deliberately does not.
- **Audience**: who watches and what they already know.
- **Chapters**: `| t (s) | Chapter | Title on screen | Framing | What happens (beats, UI states, fictional data) | Lines |`,
  the same columns as `_template/video/BRIEF.md` and the example. Opening on context, one idea
  per chapter, one framing per chapter, end screen with breadth, lockup. `t (s)` is the target
  range now and the measured one after the voice; `Lines` stays empty until script-and-voice
  writes `lines.tsv`. The link to coverage lives in COVERAGE.md's Chapter column, so it is not
  repeated here.
- **Notes**: every fictional name, number, email and id the video will use. Production glitches
  to fix rather than copy (padding, clipped text, native media players). Assumptions.
- **Changelog**: `### v1` with the date. `/video-review` adds one section per version.

The BRIEF is the video's memory. A subagent that reads only this file must be able to continue
the work, because agents get replaced mid-production and the state has to live in files.
