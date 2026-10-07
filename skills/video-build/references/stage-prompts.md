# Stage prompts for /video-build

Short, self-contained prompts for the stages before the builder. Fill every `<...>`. Each
subagent loads one model-invoked skill with the Skill tool and follows it; the prompt only adds
what the skill cannot know (which video, which screens, what the coordinator already found).
Every prompt ends with the same report rule: short, a table, file paths, and what is
unverified. A subagent's "done" is checked with `stages.py --require <stage>`, never trusted.

Common header for every stage (paste it first):

> You work on <PRODUCT NAME>, video `<VIDEO>` v<N>, in `<VIDEO_DIR>` (product folder
> `<PRODUCT_DIR>`). Read `<PRODUCT_DIR>/kit/RULES.md`, `product.yaml`, and the video's
> `BRIEF.md`, `COVERAGE.md` (signed) and `CLAIMS.md` (signed). Work autonomously; list choices
> for veto in your report. Read-only everywhere except the files named below. No browser, no
> downloads, never print a secret, never kill a process you did not start. Report in under 250
> words.

## recon (source-recon)

> Load the `source-recon` skill. If `<PRODUCT_DIR>/sources.lock` is missing or the brief says
> the code changed, fetch first. Then map every screen the chapters and coverage rows need to
> its route, components, i18n strings and state, and write `<VIDEO_DIR>/SOURCES.md`. List the
> screens that have no code and the no-code references that exist for them. Write only
> `SOURCES.md` (and `sources/`, `sources.lock` through the fetch script).

## truth (product-truth)

> Load the `product-truth` skill. Back every coverage row, every claim in CLAIMS.md and every
> chapter's intended sentence with a source (`<role>/<path>:<line>@<sha>` or a docs page), mark
> whether it is visible in the UI or backend only, and give a verdict. Write
> `<VIDEO_DIR>/TRUTH.md`. Anything without a source is cut or raised as a closed question with a
> recommended option; never soften it into a vague claim.

## specs (ui-spec-from-code), one subagent per screen

> Load the `ui-spec-from-code` skill. Your screen: `<SCREEN>` (from SOURCES.md: route
> `<ROUTE>`, components `<FILES>`), states needed: `<STATES from the chapter table>`. Write
> `<VIDEO_DIR>/specs/<SCREEN>.md` and `specs/<SCREEN>.html` with literal values and citations.
> Read-only on sources. Write only those two files.

## reference (ui-reference-capture), only for screens without code

> Load the `ui-reference-capture` skill. Screen `<SCREEN>` has no usable code. Use, in order of
> preference: the recordings in `<PRODUCT_DIR>/references/`, recovered captures, a local
> instance if the brief allows it. Never the reviewer's browser. Write into
> `<PRODUCT_DIR>/references/<SCREEN>/` and a spec at `<VIDEO_DIR>/specs/<SCREEN>.md` marked as
> measured from a reference.

## voice (script-and-voice)

> Load the `script-and-voice` skill. Write the narration as `<VIDEO_DIR>/audio/lines.tsv`, one
> clip per sentence, only from sentences TRUTH.md backs, in the chapter order of BRIEF.md, using
> CLAIMS.md's positioning and tagline and none of its phrases to avoid. Then generate clips and
> `timings.json` with `tts.py` (<PROVIDER>; at most two takes per line, the provider quota is
> shared). Apply `product.pronounce`. Write only under `<VIDEO_DIR>/audio/`.

## Fix requests to a live subagent (SendMessage)

When a subagent is still running and needs a correction, send a condensed version of the same
structure: the problem, its time range, what is expected, "do not change anything else", the
render name, and "confirm in 3 lines after looking frame by frame at <t0> to <t1> s". If it is
no longer running, start a new one with the full prompt: state lives in the files.
