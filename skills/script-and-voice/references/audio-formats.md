# Audio formats: lines.tsv, timings.json, the raw archive and sfx

Everything lives in `<video_dir>/audio/`. You write `lines.tsv` (and optionally `sfx.tsv`);
the scripts write the rest. `build.py` reads `timings.json` and derives every cue of the video
from it, so a regenerated line re-times the whole video.

```
audio/
  lines.tsv              # the script, written by hand
  lines-v<N>.tsv         # copies of earlier versions (and timings-v<N>.json)
  raw/<id>.mp3|.aiff     # untouched provider takes (gitignored)
  raw/<id>.json          # per take: hash, provider, spoken text, provider word timings
  raw/prev/              # the take before the current one, for --restore
  raw/cache.json         # {id: {take, proc}} hashes used to skip unchanged lines
  clips/<id>.wav         # 48 kHz mono, trimmed, treated, normalized, faded
  timings.json           # {id: {dur, words}}
  sfx.tsv                # optional: sounds to prebuild with make_sfx.py
  sfx/                   # typing tracks, library sounds, manifest.json, CREDITS.md
```

## lines.tsv

Tab separated. Header `id	role	speed	text`. Lines starting with `#` are comments. One row per
clip, in playback order.

| Column | Meaning | Example |
|---|---|---|
| id | Clip id: the file name and the key in timings.json. `N` for narration, another letter per character. Insert with a suffix (`N7b`) so other ids stay stable. | `N7b` |
| role | A key of `voice.roles` in product.yaml. Picks voice, model, settings, say voice and treatment. | `narrator` |
| speed | Read speed, 1.0 by default, 0.7 to 1.2. Sent to the provider (ElevenLabs `speed`, `say -r`). | `0.95` |
| text | The words as they appear on screen and in captions, canonical spelling. | `Maya opens Acme Tasks.` |

```
id	role	speed	text
# Opening
N1	narrator	0.96	This is Acme Tasks, the to-do list that plans your day.
N2	narrator	1.0	Maya runs Northwind Bakery, and every morning starts with a list.
C1	customer	1.0	Hi Maya, can I pick up the cake at ten a.m.?
```

## timings.json

```json
{
 "N1": {
  "dur": 3.111,
  "words": [
   {"w": "This", "s": 0.0, "e": 0.16},
   {"w": "is", "s": 0.16, "e": 0.28},
   {"w": "Acme", "s": 0.28, "e": 0.68, "say": "AK-mee"},
   {"w": "Tasks,", "s": 0.68, "e": 1.12}
  ]
 }
}
```

| Field | Meaning |
|---|---|
| dur | Length of `clips/<id>.wav` in seconds, after trimming and fades. |
| words[].w | The canonical word as written in lines.tsv, with its punctuation. One entry per whitespace token of the text. |
| words[].say | Only when the pronounce map changed the word: what was sent to the TTS. |
| words[].s / e | Start and end in seconds from the start of the trimmed clip. |

Word times come from the ElevenLabs character alignment, or from whisper for the `say`
provider. Whisper times are accurate to about 50 ms; good for anchoring beats, worth a look for
anything that must land on a syllable.

## How build.py uses it

```python
TIM = json.loads((AUDIO / "timings.json").read_text())
D = {k: v["dur"] for k, v in TIM.items()}

def w(clip, prefix):
    """Start of the first word in `clip` that begins with `prefix` (punctuation and case ignored)."""
    for x in TIM[clip]["words"]:
        if x["w"].lower().strip(".,!?:;\"'").startswith(prefix.lower()):
            return x["s"]
    raise KeyError(f"{prefix} not in {clip}")

T["N4"] = T["ch2"] + 0.6                         # the line starts 0.6 s after the chapter title
T["click"] = T["N4"] + w("N4", "today") - 0.1    # the click lands just before "today"
```

Every visual beat is `T[clip] + w(clip, "word") +/- offset`, and the audio tags come from the
same `T`, so picture and sound cannot drift apart. In the production these skills come from,
each video had 18 to 42 word anchors, with the picture leading the word by a median of 0.10 to
0.15 s; a slight lead reads as the cursor causing what is said.

## Loudness

- Each clip: loudnorm two-pass to `voice.clip_lufs` (default -18 LUFS integrated), true peak at
  most -1.5 dBTP. When loudnorm would miss by more than 0.5 LU (short clips), a plain gain into a
  limiter replaces it. Fades: 5 ms in, 80 ms out at the end of the trimmed clip.
- The final mix is checked by render-qa against `voice.mix_lufs` (default -16).

## sfx.tsv (optional)

```
id	kind	value	cps
type1	typing	Plan the Saturday orders	14
click	library	click
```

`make_sfx.py <video_dir>` writes `sfx/type1.wav`, copies `sfx/click.mp3`, and records both in
`sfx/manifest.json` (`{id: {src, dur, kind, from}}`) and `sfx/CREDITS.md`. Most builds call
`typing_track()` and `library_sfx()` from build.py instead, which do the same and return cues
with a start time.
