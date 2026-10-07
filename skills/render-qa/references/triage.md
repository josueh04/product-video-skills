# Triage: what each failure turned out to be

From the production these skills come from: five narrated product demos, 33 renders. Every
row happened. When a check fails or warns, find the row, confirm with the "how to tell"
column, and fix the cause in the source, never in the generated `index.html`.

## Real defects

| Signal | Cause | How it was confirmed | Fix |
|---|---|---|---|
| `WORKER PATTERN` over the opening title, reviewer saw "stuttering and flashing" | `fromTo` with `opacity` only in fromVars; one worker's seek reverted it | Snapshots of frames 0, 3, 6 ... in that order (one worker's sequence) reproduced the missing title; `--at 1.0` showed it, `--at 0.5,1.0` did not | Every fromVars key in toVars, or `set` + `to` (seek-safe-motion) |
| Click in the mix at the end of a narration line | The clip ended on a cut breath | `edges.py` loud `tail`; listened in the mix | Fade out about 0.4 s after the last word when normalizing the clip |
| Ghost text and a clipped modal over 0.8 s | A menu still open when the modal opened; the modal scaled in from outside the frame | Seen on a 1 fps sheet, confirmed on a 10 fps strip | Close the menu one frame before opening the modal; place the modal where it fits whole |
| 0.3 s of sharp UI before the lockup | The end screen faded with its background, exposing the UI under it | 6 fps strip of the handoff | Fade only the end screen's content; keep its background until the lockup is in |
| `clipped_text` in `check` | A name 4 px wider than its box | `check` output and a full-resolution crop | Wrap or shorten the fictional name |
| Cursor off screen while choosing an option | Camera framed the list, the cursor's target was outside it | Snapshot of the beat | Frame the whole section, or move the target into frame |
| A scrolled column past its end; two cursor moves fighting | Scroll range not clamped to the content; a reset tween inside the next move | Strip of the scroll; a seek to the middle of the move | Clamp scroll stops to real line boxes; never two tweens on one property at once |
| Feature chips on screen 1.2 s | Too short to read | Strip | Hold readable states 2 s or more |
| Two narration lines overlapping 0.04 s | Gap between clips computed from clip ends, not from spoken words | `voice_overlap` on word timings | Recompute the beat from the word timings |
| Vendor credential cards still visible | A screen copied from the live app showed a third-party vendor | Banned-term scan of the template | Keep that part out of frame, and not as an empty hole either |

## False positives

| Signal | Reality | How it was ruled out |
|---|---|---|
| A run of outliers during a fast scroll | Scroll at full speed | Per-frame offset ramps 0 to 19 to 0 px |
| Isolated outliers after a modal closes | Camera easing back | Difference boxes move continuously |
| Outliers at a chapter title | Steps of the title's blur rack | Frame by frame at 10 fps |
| "Clip N14 overlaps N15 by 0.43 s" | Silent tails; 0.35 s gap between the voices | Word timings (the check now uses spoken words) |
| ASR match about 0.80 on a good render | Script compared in lines.tsv order, not playback order | Playback order gave 0.967 (the check now sorts by `data-start`) |
| Abrupt starts at an SFX | A pop and a ring starting | Clip map (SFX onsets no longer count) |
| Dots flashing near a title for one or two frames | Descenders of a "y" peeking over the title mask | Bright-pixel scan; gone 0.1 s later; accepted |
| Titles "cut" at the top left of a sheet | The sheet's time label | Full-resolution frame |
| A duplicated label in a two-time snapshot | Not in the MP4 | A single-time snapshot did not show it; the MP4 did not either |
| Clicks inside narration | Consonants (a "k" at the end of a word) | Word timings at that second |
| ASR diffs | Spelling only (a name spelled two ways, "10am" as "ten a m", a brand word as two words) | Read the diff |

## When a number is just outside the threshold

- Loudness 1.1 LU off: re-mix to the target rather than widening the tolerance. The
  threshold is what every delivered final met.
- ASR at 0.92 with only spelling diffs: fix the spelling in `lines.tsv` if the TTS reads it
  the same, or add the brand word to the pronunciation map; do not lower `asr_min` for one video.
- A camera warning on a zoomed-out canvas or a narrow column: an approved exception in the
  production went up to 1.9x on a canvas shown at 50 %. Say it in the delivery message and let
  the reviewer decide; on a full-page or settings screen, bring it back to 1x.
