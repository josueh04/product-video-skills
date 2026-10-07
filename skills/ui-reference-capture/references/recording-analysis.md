# Analyzing a screen recording

Read this when a recording of the product arrives, after copying it into
`references/<name>/`.

## Before the recording (if you can ask for one)

A recording made for the video is worth ten found ones. Give the person a short plan:

- What to do, step by step, in the order the video tells it.
- An answer sheet of fictional values to type (from `product.yaml cast`), so no real data appears.
- A test workspace, never a customer's.
- Record the window, not the whole screen (no Dock, no notifications), at the app's desktop size.
- Leave a two second pause on each important state, and do not trim the waits.

## Pipeline

| Step | Command | Output |
|---|---|---|
| Probe and frames | `frames.sh <rec> <scratch> --fps 10 --logical-width <W>` | `thumb/`, `logical/`, `probe.json`, `frames.json` |
| OCR | `ocr.sh <scratch>/logical <scratch>/ocr.jsonl [en-US,de-DE]` | one JSON line per frame |
| Text timeline | `ocr_events.py <scratch>/ocr.jsonl references/<name>/ocr-timeline.txt --fps 10 [--region ...]` | `start-end [region] text` |
| Overview | `grid.py sheet <scratch>/overview.png <scratch>/logical --every 20` | sheets every 2 s |
| Dense phases | `grid.py sheet <scratch>/phase-build.png <scratch>/logical/00{300..420}.jpg` (or a folder with that range) | 10 fps sheets |
| One sharp frame | `ffmpeg -ss <t> -i <rec> -frames:v 1 <scratch>/hi-<t>.png` | full resolution for measuring |
| Measure | `grid.py overlay <frame> <out> --scale 2 --step 10` | a logical px grid |

Pick `--logical-width` from the recording: a retina capture of a 1440 px wide window is 2880
pixels wide, so the logical width is 1440. Use the same number as `app_canvas.logical[0]` when
the video has no other reason to choose a width.

Use regions when the screen has areas that change independently (a main pane and a side panel
that opens later): `--region "panel=0.6,0,1,1@9.8"` tags text in the right 40 % after 9.8 s.

Query the timeline with `grep` for exact strings, and cut single frames with `ffmpeg -ss` to
crop icons, rows and pills.

## analysis.md structure

```markdown
# Recording: <name>
File: references/<name>/<file> (<duration> s, <pixel size>, <fps> fps, logical width <W>)
Recorded by: <who>, <date>, workspace: <test workspace, never shown>

## Timeline
| t (s) | what happens | exact on-screen text (from ocr-timeline.txt) |

## Motion measured
| what | duration | how measured |
(e.g. home to chat about 0.3 s; streamed text in blocks every 0.1 s; cursor travels 0.3 to 0.5 s
and rests 0.5 to 1 s before a click; modals open in about 0.2 s)

## Must change for the video
| what | where (t) | replace with |
(real company, people, emails, phones, workspace names, internal ids, real conversations, long
waits, OS chrome)

## Product gaps to raise
- <a step the story needs that the recording shows failing or missing, with t>

## Key frames
| file | t | state |

## Elements not found in code
- <element, t, best reference>
```

## What a recording cannot prove

- Behaviour behind a wait you compressed.
- What would have happened on the step that failed.
- Anything outside the frame.
Write these as open items for product-truth instead of filling them in.
