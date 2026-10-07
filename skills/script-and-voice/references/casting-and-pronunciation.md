# Casting and pronunciation

Read this before proposing voices, when a reviewer says a voice or a name sounds wrong, and when
`pronounce_check.py` raises a flag.

Contents: [Roles in product.yaml](#roles-in-productyaml) | [Casting](#casting) |
[Provider settings](#provider-settings) | [Quota](#quota) | [Pronunciation](#pronunciation) |
[The vowel check](#the-vowel-check) | [Known ASR false positives](#known-asr-false-positives)

## Roles in product.yaml

```yaml
voice:
  provider: elevenlabs            # or say
  env_key: ELEVENLABS_API_KEY     # tts.py reads it from the environment or PVS_HOME/.env
  roles:
    narrator:       {voice: "<voice id>", model: eleven_multilingual_v2, say_voice: Samantha}
    narrator_close: {voice: "<voice id>", model: eleven_multilingual_v2, say_voice: Samantha,
                     settings: {stability: 0.6, style: 0.1}}       # steadier read for the last line
    agent:          {voice: "<voice id>", model: eleven_v3, say_voice: Karen, treatment: phone}
    customer:       {voice: "<voice id>", model: eleven_v3, say_voice: Daniel}
  clip_lufs: -18
  mix_lufs: -16
```

| Key | Meaning |
|---|---|
| voice | ElevenLabs voice id (a public catalog id or one added to the account). |
| model | ElevenLabs model id. Default `eleven_multilingual_v2`. |
| settings | Overrides of the provider's voice settings for this role (see below). |
| context | Send the neighbouring lines of the same role as `previous_text` / `next_text`. Default on, off for `eleven_v3`. |
| say_voice | macOS voice for `provider: say` (`say -v '?'` lists them). |
| say_rate | Words per minute for `say` at speed 1.0. Default 180. |
| treatment | `phone` (320 Hz to 3.6 kHz band, 3:1 compression) or `room` (140 Hz to 7.2 kHz, 2.5:1), applied before normalization. |

A **per-line read** is a role variant: same voice, other settings, chosen in the role column of
that line. The choice lives in config, so a re-run reproduces it, and the line's hash changes
when the read changes, so it is voiced again exactly once.

## Casting

1. **List the roles** the script needs: narrator, and each character that speaks.
2. **Shortlist three to six voices per role.** Prefer the most natural model the account has for
   characters. Do not default to the voice the product itself uses: in the production these
   skills come from, the product's own default voice and two library voices on a fast model were
   all judged "very fake", and a cheap local model was rejected outright.
3. **Audition in context**: two real consecutive lines of the script per candidate, not a
   generic sentence. A voice that is fine alone can be wrong next to the other roles.
4. **Ask a closed question with a default**: "Narrator: B (warm, unhurried). Agent: E on the
   expressive model with phone treatment. Keep both?" At most three decisions per message. Open
   lists of candidates went unanswered and decisions stalled for days.
5. **Write the choice into product.yaml**, so every video of the product uses the same cast.
6. **Pick the treatment per role**: the agent on a call sounds like a phone, a recorded meeting
   sounds like a room, the narrator is clean.

Character names, voices and taglines are always proposed for veto before animating: a rejected
demo name costs every frame it appears in.

## Provider settings

ElevenLabs defaults used by `tts.py`:

| Model | Default settings |
|---|---|
| `eleven_multilingual_v2` and others | stability 0.45, similarity_boost 0.8, style 0.15, use_speaker_boost true |
| `eleven_v3` | stability 0.5, similarity_boost 0.8 |

The `speed` column is sent as `speed` in every case. Output is `mp3_44100_128` (lower plans
refuse raw PCM), decoded to WAV. Reads that worked in review:

| Line | Settings | Why |
|---|---|---|
| Opening line | stability 0.8, style 0.0, speed 0.96 | the default read sounded "too hype" alone at the start |
| Closing line | stability 0.6, style 0.1, speed 0.9 | a settled, complete-sounding end |

For a pause inside a sentence, split it into two clips and let build.py place the gap: the gap
is then exact, adjustable without a new take, and nothing but words reaches the captions.

The `say` provider is macOS text to speech plus whisper word timings. It is free and offline;
use it for drafts, timing work and tests, never for a delivered video.

## Quota

Provider plans are metered in characters, and a team usually shares one plan. `check_script.py`
prints how many characters the next run will send. Before a full run, say it to the user; keep
to two takes per line unless they ask for more. If a run is interrupted, rerun the same command:
lines already voiced are skipped by hash.

## Pronunciation

The script and the screen keep the real spelling; `product.pronounce` changes only what the TTS
receives. Matching is exact and case-sensitive on word boundaries, longest key first, so
`Acme Tasks` wins over `Acme` when both exist.

```yaml
product:
  pronounce:
    Acme: AK-mee                                         # respelling only
    Acme Tasks: {say: "AK-mee Tasks", vowel: ae, confusable: ey}
    FAQ: "F.A.Q."                                        # letters read one by one
    AI Notes: "A.I. Notes"
```

When a name is said wrong:

1. Write three or four candidate respellings (`AK-mee`, `Ack-mee`, `Akmee`).
2. Voice one line with each (a scratch role or `--only` with a temporary pronounce entry).
3. Measure each with `pronounce_check.py` (recognition and, when set, the vowel check) and
   listen to the passing ones.
4. Keep the winner in product.yaml and re-check every line that contains the word: providers
   vary per take, so one good take does not prove the others.

In `timings.json` the word keeps its canonical spelling in `w` and carries the respelling in
`say`; anchors in build.py use `w`.

## The vowel check

Some mispronunciations are a vowel, not a sound the ASR notices: "DAY-ko" instead of "DAK-o"
still transcribes as the brand. `pronounce_check.py` measures the first vowel of the word:
pre-emphasis, 22 ms Hamming frames, LPC of order 12, formants from the roots of the polynomial,
median F1 and F2 over the loud frames of the first 45 % of the word (located with timings.json).

It then compares the measurement with reference averages of American English vowels (male and
female speakers, after Hillenbrand et al. 1995), in log-formant space:

| Label | As in | Label | As in | Label | As in |
|---|---|---|---|---|---|
| iy | beet | ae | bat | ow | boat |
| ih | bit | ah | but | uh | book |
| ey | bait | aa | hot | uw | boot |
| eh | bet | ao | bought | er | bird |

- With `confusable:`, the check passes when the vowel is closer to `vowel` than to `confusable`.
  This is the useful form: "is it /ae/ (dap) rather than /ey/ (day)?"
- Without it, the check passes when `vowel` is the nearest of all twelve.
- `f1_min`, `f1_max`, `f2_min`, `f2_max` (Hz) replace the table with explicit limits when you
  have measured a good take of a specific voice. For one male narrator, /ae/ versus /ey/ was
  separated by F1 >= 580 Hz and F2 <= 1950 Hz.

Formant tracking is unreliable on whispered or very short vowels and on phone-treated audio;
a failure there means "listen", not "regenerate".

## Known ASR false positives

A flag from the speech-to-text means listen to the clip. These turned out to be the ASR, not the
voice, in the production these skills come from:

| Flag | Reality |
|---|---|
| A brand name heard as a common word that sounds like it (a short brand heard as an everyday word) | ASR error; the voice was right |
| A cast name spelled two ways (Kira and Kyra) | spelling only |
| `nine` versus `9`, `ten a m` versus `10am` | spelling only |
| A brand with an unusual capital (`dX` style) heard as two words | spelling only |
| A "click" inside a clip on a word with a hard consonant (k, t) | the consonant |
| Low transcript match on a line with numbers or times | number formatting |

If you cannot tell whether a mismatch is the voice or the ASR, say so in the report instead of
spending a take.
