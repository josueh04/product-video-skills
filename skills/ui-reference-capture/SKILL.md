---
name: ui-reference-capture
description: Gather pixel references for UI that the code cannot show, or to check a rebuild against the real thing, using frames and timed OCR text from screen recordings, captures recovered from past Claude Code session transcripts, a local instance of the app built like production, and web research for third-party apps, plus side-by-side parity images and contact sheets. Use it whenever someone hands over a screen recording (.mov or .mp4) of the product, when a screen has no usable source code (a stale checkout, another company's UI such as a sign-in page, calendar or CRM, runtime output from a backend not in the repos), when asked "what does it really look like", "match the recording", "how long does that animation take in the app", "compare our render to the real app", or when screenshots from an earlier session might already exist. Never uses the reviewer's personal browser.
---

# UI reference capture

The code gives structure, styles, strings and icons. It does not give what happens at runtime
(what a backend answers, in which order things appear, how long the real app waits), and it
says nothing about another company's UI. This skill fills those gaps with references, in a
fixed order of preference, and it never improvises in someone's personal browser.

That last rule has a history. In the production these skills come from, an agent was allowed
into the reviewer's own logged-in browser to capture a live app. The live flows hung, the agent
kept doing "cleanup" steps after the reviewer said stop, it left stray items in a test
workspace, and the session ended badly after about 68 minutes with nothing usable built. The
same captures were later recovered from the session transcript in minutes. Offline references
first; a browser only when the user asks for one, isolated, and stopped the moment they say stop.

## Where things go

- Inputs (recordings, exports, screenshots the user hands over): copy them into
  `products/<slug>/references/<name>/` as soon as they arrive. Downloads folders and the OS's
  temporary capture folders get cleaned, and one recording in the source production lived in a
  folder the system would have deleted. macOS recording names contain a narrow no-break space
  (U+202F) before AM/PM: find them with a glob, not by typing the name.
- Working material (thousands of frames, recovered captures, raw OCR): a scratch folder outside
  every repo, e.g. `$TMPDIR/pvs-<slug>-<name>/`.
- Results worth keeping (the OCR timeline, key frames with real data cropped out, the analysis):
  `references/<name>/`, cited from SOURCES.md.

Recordings and captures of a real workspace hold real customer names, emails, phone numbers,
internal ids and other people's conversations. They never go into the workbench repo, and the
video never shows them: section 1 step 6 lists what must change.

## Choose the technique

| You have | Technique | Read |
|---|---|---|
| A screen recording of the product | 1. Analyze the recording | `references/recording-analysis.md` |
| Past sessions that looked at the app | 2. Recover captures from transcripts | this file, section 2 |
| An app that can run locally | 3. Local instance built like production | `references/local-instance.md` |
| Another company's product | 4. Web research, public sources only | `references/third-party-ui-prompt.md` |
| Nothing (a phone call, an end card, generated text) | Design it from the kit and mark it | product-truth (`mock`) |

Try them in that order. Before asking anyone to record, check section 2: captures may already
exist. If none of the four works, say so; do not fall back to the reviewer's browser.

## 1. Analyze a screen recording

```bash
PVS_HOME="$(cd "$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/../.." && pwd)"
S="$PVS_HOME/skills/ui-reference-capture/scripts"
W="$TMPDIR/pvs-acme-board"                                    # scratch, outside the repo
bash "$S/frames.sh" references/board/rec.mov "$W" --fps 10 --logical-width 1440
bash "$S/ocr.sh" "$W/logical" "$W/ocr.jsonl"                  # macOS only
"$PVS_HOME/bin/pvs-py" "$S/ocr_events.py" "$W/ocr.jsonl" references/board/ocr-timeline.txt --fps 10 \
  --region "panel=0.6,0,1,1@9.8"
"$PVS_HOME/bin/pvs-py" "$S/grid.py" sheet "$W/overview.png" "$W/logical" --every 20 --cols 4
```

1. `frames.sh` writes small thumbs (change detection) and frames at the app's logical width (a
   retina recording is 2x: logical width is half the pixel width), so one frame pixel is one CSS
   px of the rebuilt app.
2. `ocr.sh` compiles `ocr.swift` (Apple Vision) once into a cache folder and writes one JSON line
   per frame. On Linux it exits with "unsupported": read the contact sheets instead.
3. `ocr_events.py` turns per-frame OCR into stable spans, `start-end [region] text`. That
   timeline gives the exact strings the real app shows and when, which beats guessing from a
   video by eye.
4. `grid.py sheet` makes contact sheets: an overview every 2 s, then dense 10 fps sheets per
   phase. `grid.py overlay` draws a logical-px grid on a frame for measuring.
5. Save key frames as `references/<name>/frames/<t>-<state>.jpg` (cropped of real data).
6. Write `references/<name>/analysis.md` with the structure in `references/recording-analysis.md`:
   the real timeline with exact strings, measured motion (how long a panel takes to open, how
   long the cursor rests), a "must change for the video" table (real names, emails, phones,
   workspaces, internal ids, long waits, OS chrome such as the Dock), and product gaps to raise
   before anyone builds on them (a step the story needs that the recording shows failing).

Recordings hide gaps when waits are compressed; note every wait you shorten.

## 2. Recover captures from past sessions

Every image a tool returned in a Claude Code session (browser screenshots, window captures, read
images) and every image pasted into the chat is stored in that session's JSONL.

```bash
"$PVS_HOME/bin/pvs-py" "$S/recover_transcript_images.py" ~/.claude/projects/<project>/<session>.jsonl \
  [--from-line N] [--tool screenshot]
```

With no output folder it writes to a fresh temp folder and refuses any folder inside a git work
tree, because these captures show real accounts. It writes `index.tsv` (file, time, tool, input)
so you can find the screens you need. Review them in contact sheets (`grid.py sheet <out>
<dir> --labels name`), then copy only the cleared ones, with real data cropped out, into
`references/<name>/`. In the source production one whole video was built from 117 recovered
images plus the code.

## 3. A local instance built like production

The most faithful reference when the app can run on the user's machine: build it from the
production commit with the production build arguments, seed it with fictional data, isolate it
from every shared system, and capture it with a headless browser. Read
`references/local-instance.md` before starting; the user must agree to running their app, and
it never uses their accounts or shared databases.

## 4. Third-party UI

For another company's screens, launch a research subagent with
`references/third-party-ui-prompt.md`: public sources only (official docs, help centers, press
kits, marketing screenshots, public embed demos owned by the vendor), never a login, never a
submit or a booking, about 30 minutes. Every value comes back marked verified, measured or
inferred. Prefer the product's own component when it has one (a product that renders a preview
of a chat app has a preview component; use it instead of rebuilding the chat app). Show a full
third-party screen only when it proves a real integration; elsewhere use logos and badges inside
the product.

## Parity: prove the rebuild matches

```bash
"$PVS_HOME/bin/pvs-py" "$S/pair.py" snapshots/nocam-12.4s.png references/board/frames/12.4-board.png \
  640 40 1100 300 "$W/pair-board-header.png" --ref-scale 2 --logical-width 1440 --render-width 1920
```

Take our snapshot with the camera at scale 1 (a copy of the composition with
`#camera{transform:none!important}`), crop the same logical box from both, and stack them. The
script prints the mean absolute difference per channel; iterate until it stops dropping and the
stacked image shows no offset. Measure in app px and convert explicitly: confusing scales was a
recurring source of wrong coordinates.

## Rules and why

- **Never the reviewer's personal browser or profile**, and nothing taken from it (fonts, icons,
  storage). When anyone says stop, stop every browser action at once, cleanup included.
- **Never sign in, never read tokens or browser storage.** If a capture needs a login, the person
  types their own password in their own session, or the capture does not happen.
- **Recovered and recorded material stays private.** Temp folder first, cropped copies only.
- **Mark every inferred value.** A reference that is half guessed must say which half.
