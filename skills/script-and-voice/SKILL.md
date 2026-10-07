---
name: script-and-voice
description: Write a product video's narration and turn it into voice clips with word timings, pronunciation fixes, sound effects and even loudness. The script becomes a table of moments and then audio/lines.tsv (one clip per sentence, with role and speed columns); tts.py voices it with ElevenLabs or the free macOS say voice, maps brand respellings back to the on-screen spelling, normalizes every clip and writes audio/timings.json for the composer; make_sfx.py builds typing tracks from real keystrokes and places recorded click and pop sounds. Use it whenever a video needs a script, narration, voice-over, lines.tsv, timings.json, TTS, a new take, a voice or casting choice, a pronunciation fix ("it says the name wrong"), a changed sentence, a tone note ("too hype", "sounds cut off"), audio levels, a click at the end of a clip, typing or click sounds, or when the build stage asks for the voice. Also use it for silent loops, which still need a moment table and SFX.
---

# Script and voice

The voice is the clock of the video. Every beat of the animation is anchored to a word of the
narration (`T[clip] + w(clip, "word")` in build.py), so the script and its clips come before the
animation, and changing a sentence regenerates one clip and re-times everything after it. In the
production these skills come from, swapping the whole TTS engine re-timed a finished video with
no manual edits because of that design. Animating first and fitting the voice after means
stretching audio or dragging beats by hand on every change.

Write only under `<video_dir>/audio/` (plus the script section of BRIEF.md). Every sentence must
be backed in TRUTH.md and respect CLAIMS.md; if a sentence you need has no source, ask for it to
be verified or cut it.

Scripts, called as in docs/contracts.md:

```bash
PVS_HOME="$(cd "$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/../.." && pwd)"
S="$PVS_HOME/skills/script-and-voice/scripts"
"$PVS_HOME/bin/pvs-py" "$S/check_script.py" <video_dir>                 # lint lines.tsv
"$PVS_HOME/bin/pvs-py" "$S/tts.py" <video_dir> [--only N3,N4] [--provider say] [--force] [--restore]
"$PVS_HOME/bin/pvs-py" "$S/pronounce_check.py" <video_dir> [--only N3]  # did the ASR hear the brand words?
"$PVS_HOME/bin/pvs-py" "$S/make_sfx.py" <video_dir> [--list]            # sfx.tsv, or list the library
```

## 1. The script is a table of moments

A recording of the product is a reference, not a timeline: real loading waits and screen changes
do not belong in the video. Write the script as moments, each with what happens on screen, the
sentence (or silence) and how long it lasts. A moment lasts as long as the longer of its action
and its sentence. Compress real waits: forty seconds of loading become about two seconds of a
thinking state.

Add the table to BRIEF.md under `## Script`, in chapter order:

| Moment | On screen | Line | Text (or silence) | Holds |
|---|---|---|---|---|
| Opening | Product name over the app out of focus | N1 | This is Acme Tasks, the to-do list that plans your day. | 0.8 s after |
| Wait | The plan is being built | (silence) | | 2.0 s |

Then pick the template for the video's format and follow its structure: read
`references/script-templates.md` (pitch, tour, docs page, tutorial, silent loop).

How to write the lines, and why:

- **Explain the important features; do not list them.** Say what a feature does for the viewer
  while the UI does it. In the production these skills come from, 9 of 26 versions happened
  because a video named a feature without explaining it. COVERAGE.md says which features must be
  explained on screen: every row marked "must explain" needs at least one line that explains it.
- **Explain each step to someone who has never seen the product.** Who the character is, what
  they ask for, what each step does. A fast, unexplained opening was rejected in review.
- **One idea per sentence and one sentence per clip.** A changed sentence then costs one clip.
- **Name what the cursor touches as it touches it.** The beats anchor to those words, so the
  noun on screen and the word in the clip must be the same.
- **Use the real UI label**, even when the reviewer uses another word for it. The video then
  matches what the viewer will see in the product.
- **Write numbers and times as words** ("ten a.m.", "thirty minutes later"). TTS engines read
  digits inconsistently and the speech-to-text QA compares words, not digits.
- **Leave air around waits.** About three seconds before a phone rings, "about a minute" instead
  of a precise number nobody can verify.
- **End on a complete sentence, read a little slower.** A tagline fragment as the last line
  sounded cut off in review; a full sentence with the positioning from CLAIMS.md did not.
- Keep the person consistent within a video: first person as the fictional user ("First, I
  connect my calendar.") or third person about them. Use only the fictional cast from
  product.yaml, with the same name in every video.
- Positioning comes from CLAIMS.md, not from source documents: a source doc can contain a
  phrase the team has banned, and the rule wins.

## 2. lines.tsv

`audio/lines.tsv`, tab separated, header `id	role	speed	text`, one clip per row in playback
order, `#` lines are comments. Full format and how build.py reads the result:
`references/audio-formats.md`.

- **id**: `N1`, `N2`, `N7b` for narration; other letters for characters (`A1` for an agent,
  `C1` for a customer). Inserting a line between N7 and N8 as `N7b` keeps every other id, and
  every anchor that uses it, stable.
- **role**: a key of `voice.roles` in product.yaml (`narrator`, `agent`, `customer`, or a read
  variant such as `narrator_close`, see section 3). The role, not the id, picks the voice.
- **speed**: 1.0 by default, 0.7 to 1.2. Use 0.9 to 0.96 for the opening and closing lines.
- **text**: exactly as it appears on screen and in captions, with the canonical spelling of
  product names. Never write a respelling here; pronunciation lives in product.yaml.

Before changing lines of a delivered version, copy `lines.tsv` to `lines-v<N>.tsv` and
`timings.json` to `timings-v<N>.json`, so the previous version can be rebuilt.

Run `check_script.py` after every edit. It fails on duplicate ids, unknown roles, speeds out of
range, clips over 40 words, banned terms, never_say phrases, legacy names and respellings in the
script, and warns on long clips, digits and dashes. Fix every error before voicing: a banned
phrase that reaches the TTS costs a take, and one that reaches a render costs a version.

## 3. Casting

Read `references/casting-and-pronunciation.md` before proposing voices. In short:

- Offer realistic voices first. The product's own default voice and the cheapest models were
  judged "very fake" in review; the most natural model available is worth it for characters.
- Audition in context: two real consecutive lines per role, three to six candidates per role.
- Propose each choice for veto as a closed question with a recommended default ("Narrator: voice
  B, warm and unhurried. Keep it?"). Open lists of options went unanswered for days.
- Decide the treatment per role: `treatment: phone` for someone on a call, `treatment: room` for a
  recorded meeting, nothing for the narrator.
- A per-line read (steadier, slower, less style) is a role variant that points at the same voice
  with other settings, so the choice is in config and survives a re-run.

`voice.provider: say` (or `--provider say`) uses the free macOS voice and whisper for word
timings. Use it for drafts, tests and timing work before a key exists; deliver with the real voice.

## 4. Generate the clips

```bash
"$PVS_HOME/bin/pvs-py" "$S/tts.py" <video_dir>
```

For each line it respells brand words for the TTS only, keeps the untouched take in `audio/raw/`
(the previous take moves to `audio/raw/prev/`), trims silence, resamples to 48 kHz mono, applies
the role's treatment, normalizes to `voice.clip_lufs` (ffmpeg loudnorm, two passes; peaks under
-1.5 dBTP), fades both edges, and merges the clip's entry into `audio/timings.json`.

Why each processing step exists:

- **Raw takes are always archived and always the source.** An earlier client normalized from a
  stale raw file after a full re-render; here a clip is always rebuilt from the take that
  produced it.
- **The tail is cut at most 0.6 s after the last word, with a fade.** A TTS take can end with a
  click or the onset of another phrase; one such click shipped as a "weird cut" in the audio.
- **Every clip at the same loudness.** One character voice came out 6 dB louder than the
  narrator before normalization.
- **Unchanged lines are skipped** (hash of text, voice and settings in `audio/raw/cache.json`),
  so a full run after editing one line calls the provider once. If only `clip_lufs` or the
  processing changed, clips are rebuilt from the archived takes for free. `--force` asks for a
  new take anyway.

The key is read by the script from the environment or `PVS_HOME/.env` and never printed. Never
read `.env` yourself and never ask for the key in the chat: if it is missing, tell the user to
add the line to `.env` themselves, or switch to `say`.

Run `pronounce_check.py` after any new take. It transcribes each clip without prompting the ASR,
flags brand and cast words that were not recognized, legacy names that were heard, and vowels
that drifted (section 5). A flag means listen, not regenerate: ASRs mishear brand words that
were said right.

## 5. Pronunciation

The script and the screen keep the real spelling. `product.pronounce` changes only what is sent
to the TTS, and tts.py maps the timings back, so `timings.json` holds the on-screen word in `w`
and the respelling in `say` (`{"w": "Acme", "say": "AK-mee", ...}`). Anchors in build.py use
the on-screen word.

```yaml
product:
  pronounce:
    Acme: AK-mee                                    # plain respelling
    Acme Tasks: {say: AK-mee Tasks, vowel: ae, confusable: ey}   # with a first-vowel check
```

When a reviewer says the name sounds wrong, try three or four respellings on one line, measure
them with the vowel check, keep the one that passes, then check every other line that has the
word: providers vary per take. Details and the vowel table: `references/casting-and-pronunciation.md`.

## 6. Takes

- At most two takes per line unless the user says otherwise; provider quotas are usually shared
  across a team. Say how many characters a full run will cost before running it.
- Regenerate only the line that needs it: `tts.py <video_dir> --only N7 --force`.
- If the new take is worse, `--only N7 --restore` swaps it back with its timings.
- For a tone note ("too hype", "sounds like half a sentence"), make two or three variants as role
  variants or speed changes, and let the reviewer compare them in context with the line before.
- Changing a line, in order: copy the version files, edit the row, `check_script.py`,
  `tts.py --only <id>`, `pronounce_check.py --only <id>`, then the composer rebuilds; everything
  after that clip moves on its own.

## 7. Sound effects

Use recorded sounds only, from the library that ships with HyperFrames (`make_sfx.py --list`).
Synthesized typing sounded "like a straw, not a keyboard" and a synthesized whoosh like "white
noise" in review, so whooshes and risers are refused by the script, and nothing goes under the
narration as music unless the brief asks for it. The production these skills come from shipped
with no music bed and no ducking, and nobody missed it.

- **Typing**: `typing_track(text, start, cps)` builds a track from single keystrokes cut out of a
  real recording, with a heavier stroke on spaces and a seeded rhythm, so it is deterministic and
  the same text always sounds the same. Make it last exactly as long as the beat that shows the
  text (`dur=`), and let the typed words land on the spoken ones.
- **Clicks and pops**: `library_sfx("click", start)` on the frame the cursor presses.
- `audio/sfx/CREDITS.md` lists every library file used and carries the library's license.
- Suggested levels: narration 1.0, characters 1.0, clicks 0.35 (0.22 on a drag release), typing
  0.45, pops 0.12 to 0.3. Two clips on the same audio track must never overlap: start a clip at
  least 0.02 s after the previous one ends, or move it to another track.

build.py imports the functions; `make_sfx.py <video_dir>` with an `audio/sfx.tsv` prebuilds the
same files from the command line (format in the script's docstring).

## 8. Hand-off to the composer

Deliver, under `<video_dir>/audio/`: `lines.tsv`, `clips/<id>.wav`, `timings.json`, and `sfx/`
with `CREDITS.md`. Tell the composer which words each beat should anchor to (the noun the cursor
touches, the word the typing lands on) and the waits from the moment table. Never edit
`timings.json` by hand: it is regenerated from the clips, and a hand edit is lost on the next run.

Report to the user: the lines voiced, each clip's duration, any pronounce flags and what you heard,
the voices used (with the recommended default for anything still open), and the provider
characters spent.
