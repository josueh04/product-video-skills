---
title: Acme Tasks in 20 seconds
video: tour
format: tour
duration_s: 20
lang: en
reviewer: Example Reviewer
version: 1
coverage_signed_by: Example Reviewer
claims_signed_by: Example Reviewer
---
<!--
The BRIEF is this video's memory: an agent that reads only this file must be able to continue
the work. Update it on every version. build.py refuses to build until the reviewer has set
coverage_signed_by (after reading COVERAGE.md) and claims_signed_by (after reading CLAIMS.md);
`build.py --draft` builds anyway, and a draft can be rendered and checked but never delivered.
-->

# Acme Tasks in 20 seconds

## Intent

The example video of the workbench. The reviewer asked for "a twenty second tour that shows the
two things Acme Tasks does: it puts your day in order, and a new task finds its own slot". The
viewer should leave believing that Acme Tasks orders the day by time with one click and keeps it
ordered as tasks are added. It deliberately does not show Upcoming or Projects (no code behind
them yet) or any setting.

## Audience

Someone opening the workbench for the first time: they have never seen Acme Tasks and want to
see what a finished video from this pipeline looks like. Shown by `bash setup.sh` and the tests.

## Chapters

| t (s) | Chapter | Title on screen | Framing | What happens (beats, UI states, fictional data) | Lines |
|---|---|---|---|---|---|
| 0-4 | Opening | Acme Tasks | 1x, out of focus | Logo, product name and the positioning over the Today screen, out of focus | N1 |
| 4-10 | 1. Plan your day | Plan *your day.* | 1x full page | Today with four tasks out of order. The cursor clicks "Plan my day"; the rows slide into time order and the "Planned by time" chip appears | N2 |
| 10-17 | 2. Add anything | Add *anything.* | 1x full page | The cursor clicks "Add task"; the dialog opens centred at natural size; "Call the oven repair shop" and "1:00 PM" are typed; "Add task" is clicked; the row lands between 11:30 AM and 2:00 PM; the toast "Added to Today at 1:00 PM" | N3 |
| 17-23 | End | One list, *planned for you.* | end screen, then lockup | Two cards with real UI pieces (a planned row, the toast), then the lockup with the positioning | N4 |

## Script

| Moment | On screen | Line | Text (or silence) | Holds |
|---|---|---|---|---|
| Opening | Product name over Today out of focus | N1 | Maya runs Northwind Bakery, and her day starts in Acme Tasks. | 0.4 s after |
| Plan | Click Plan my day, rows reorder | N2 | One click on Plan my day puts every task in order by time. | 0.8 s after the rows settle |
| Add | Dialog, typing, the row lands | N3 | Add a task with a time, and it lands in the right slot. | the toast holds 1.8 s |
| End | End screen, lockup | N4 | Acme Tasks is the to-do list that plans your day. | 1.4 s after |

## Notes

- Fictional data for veto: Northwind Bakery (Portland OR), Maya Lindqvist (owner), Omar Haddad
  (customer, in a task title). Tasks: "Bake the morning bread" 6:00 AM Kitchen, "Confirm the cake
  order with Omar Haddad" 11:30 AM Orders, "Order flour for Saturday" 2:00 PM Supplies, "Send the
  weekly invoices" 4:30 PM Office (the app's own first-run tasks), plus the typed "Call the oven
  repair shop" at 1:00 PM. Date next to the title: "Tuesday, March 3" (runtime date in the app).
- Production glitches fixed instead of copied: the Project field is a native select in the app;
  the video draws it as a styled field with a chevron (the native control renders as a grey
  platform widget). The app has no hover state on rows during the reorder; none is added.
- Designed pieces (not product UI): the opening, chapter titles, the end screen cards and the lockup.
  The cards reuse the real task row and toast markup.
- Assumptions: none; every screen is in frontend/ (a non-git copy pinned by hash).
- Seek-safety: lint_motion.py clean, no fromTo with props missing from toVars.
- Render: 30 fps, quality standard for the example, renders/tour-v<k>.mp4.

## Changelog

### v1

2026-10-07: first version, built end to end by the pipeline as the workbench example.
