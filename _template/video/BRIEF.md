---
title: "{{TITLE}}"
video: "{{VIDEO}}"
format: "{{FORMAT}}"
duration_s: 60
lang: en
reviewer: ""
version: 1
coverage_signed_by: ""
claims_signed_by: ""
---

<!--
The BRIEF is this video's memory: an agent that reads only this file must be able to continue
the work. Update it on every version. build.py refuses to build until the reviewer has set
coverage_signed_by (after reading COVERAGE.md) and claims_signed_by (after reading CLAIMS.md);
`build.py --draft` builds anyway, and a draft can be rendered and checked but never delivered.
-->

# {{TITLE}}

## Intent

<!-- What this video is for, who asked for it (quote their words), what the viewer must believe
after watching, and what it deliberately does not show. -->

## Audience

<!-- Who watches it, what they already know about {{PRODUCT_NAME}}, where it is embedded. -->

## Chapters

<!-- One idea per chapter. Each chapter opens with a two-tone title over the product out of focus
and ends on a hold of about 0.8 s. Framing: 1x full page unless a row says otherwise. -->

| t (s) | Chapter | Title on screen | Framing | What happens (beats, UI states, fictional data) | Lines |
|---|---|---|---|---|---|
| 0-3 | Opening | {{PRODUCT_NAME}} | 1x, out of focus | Logo, product name and one line on what it is | N1 |
| | | | | | |
| | End | | | End screen with breadth, then the lockup | |

## Notes

- Fictional data (names, numbers, emails) for veto:
- Production glitches fixed instead of copied:
- Assumptions (anything not in a local source):
- Seek-safety: lint_motion.py clean, no fromTo with props missing from toVars.
- Render: 30 fps, quality delivery, renders/{{VIDEO}}-v<k>.mp4 (older versions kept).

## Changelog

### v1

<!-- What changed in this version and why (quote the feedback), and how to revert. -->
