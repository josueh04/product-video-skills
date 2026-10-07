# {{PRODUCT_NAME}} videos: rules for every piece

Every agent that writes a script, a spec, a composition or a render for {{PRODUCT_NAME}} reads
this file first. Each rule is here because breaking it cost a version in the production these
skills come from. Product-specific values (names, cast, banned terms, voice) live in
`product.yaml`; this file says how to use them.

When a review round ends, add a dated entry to the review log at the bottom and fix the rule
above it in the same edit. Rules restated by hand in each brief drift apart; this file is the
one copy.

## 1. Signed before the first build

- **Feature coverage matrix** (`COVERAGE.md` of each video): the features the video must
  *explain on screen*, not only list on the end screen. In the original production, 9 of 26
  versions came from "this video also needs to explain X". When the reviewer gives a note that
  is really a rule, apply it to every video in the same round.
- **Claims sheet** (`CLAIMS.md`): the one-line positioning, phrasings to avoid, approved
  taglines, and claims that need sign-off even when a company document makes them. A source
  document can contradict the positioning; the positioning wins.
- `build.py` refuses a non-draft build until both are signed in `BRIEF.md`. Draft builds can be
  rendered and checked, never delivered.

## 2. Product truth

- **Never invent UI or behaviour.** If you cannot find the source of a screen, a label or a
  feature, do not show it. A hand-drawn badge with the wrong size and product name was the
  single angriest review of the original production.
- Every screen cites its component as `<role>/<path>:<line>@<short sha>` (see `SOURCES.md`
  and `specs/`). Every sentence of the narration has a row in `TRUTH.md` with its source.
- Production code wins, but check that it is the production checkout: the branch in
  `product.yaml` and the commit in `sources.lock`. A stale local checkout once hid the real
  version of a whole screen.
- Only real mechanics. If a step of a workflow really happens later through a trigger, show the
  trigger, not a step that waits.
- Keep the look and behaviour 1:1 (animations, states, typing, streaming, hovers), but fix
  visible production glitches: padding, overflow, clipped text, native media players. Note each
  fix in the BRIEF.
- Show what is configurable when the audience will ask "can I change that?".
- `sources/` is a read-only export. Never edit it; refresh it with `fetch_sources.py --refresh`.

## 3. Names, brand and assets

- Product names exactly as `product.names` says, even when the live UI still shows a legacy
  name. Grep every template for the legacy strings before rendering.
- Nothing from `product.banned_terms` or `product.never_say` is seen or heard: competitors,
  third-party AI vendors (model pickers, logos, voice names), real customers. If a real screen
  shows one, keep that part out of frame without leaving a hole that looks broken.
- **Official assets only**: icons from the component source, logos and fonts from `kit/`
  (extracted from the frontend or the brand files). Hand-drawn icons and logos were rejected on
  the first review. Pick the logo variant by background (a light logo vanishes on white).
- Fix brand-word pronunciation with `product.pronounce`, never by changing on-screen text.

## 4. Fictional data only

- The cast in `product.yaml` (company, people) is the only data on screen: one full name per
  person across every video, 555 phone numbers, emails on `example.com`, `.example` or `.test`
  domains, invented ids. A real recording once showed a real customer, the team's own email
  and phone, and real chats.
- Propose demo names in your report for the reviewer to veto before animating, as a closed
  question with a default. Open lists of vetoes never get answered, and the silence left one
  character with two surnames.
- Never read real data from the product (APIs, workspaces, browser sessions) to fill a screen.

## 5. Framing, pacing and motion

- **Framing: the whole page at 1x by default.** Pop-ups open centred at their natural size, as
  in the app. Push-ins only when gentle, up to `video.max_zoom` (1.35x), and never cutting a
  label. A full settings page at about 1.7x and then about 2x on one column were each rejected
  as "too zoomed in"; the video framed at 1x throughout was the model. A zoomed-out canvas or a
  narrow chat column may justify more, with the reviewer's approval.
- Open on context, never mid-UI: the product title over the UI out of focus and one line that
  says what it is.
- Chapters: a title over the product racked out of focus, one idea per chapter, one change at a
  time (0.6 to 1 s apart), about 0.8 s of hold at the end, one framing per chapter. A hero that
  did everything at once was sent back as "too fast".
- The narration explains each step to someone who has never seen the product: who this is,
  what is being asked, what each step does. Waits get breathing room.
- End screen: breadth (what else the product does, from the docs), built from real UI pieces,
  then the lockup. A logo alone was not enough.
- Sound: recorded effects only, typing built from real keystrokes. No whoosh and no music bed
  unless the reviewer asks; synthesized ones sounded like a straw and white noise.

## 6. Narration drives time

- One source of truth for timing: the word timings in `audio/timings.json`. Every beat is
  `T[clip] + w(clip, "word")`, so regenerating one line re-times the whole video. Never
  hard-code a second.
- One clip per sentence in `audio/lines.tsv`. Regenerate only the line that changed, at most two
  takes per line. Clips end with a short fade so there is no click at the edge.

## 7. Seek-safety and determinism (HyperFrames)

- In every `fromTo`, each property in the from-vars is also in the to-vars. Otherwise an element
  vanishes on every third frame, because the render runs three interleaved workers and each seek
  lands just before the tween. It was invisible in preview and in single snapshots.
- Never tween `display`. No `Date`, `Math.random` or timers: seeded jitter, times from
  `timings.json`. One paused timeline registered as `window.__timelines["main"]`.
- Pin `hyperframes@0.8.134` (the workbench version). Never run `hyperframes upgrade` or
  `skills update`.
- Snapshots use `--describe false`, so frames are never sent to an external vision API.

## 8. QA gate before any delivery

- `hyperframes check` passing is not enough: once, moving items were invisible in three of four
  segments and the check passed.
- Every render goes through `qa.py`: black frames, overlaps, loudness, clipping, clicks at clip
  edges, speech-to-text against the script, banned terms, contact sheets and frame strips at
  5 to 6 fps around every transition. Look at the sheets and strips yourself. Subagents that
  reported "clean" had missed a 0.3 s flash before a lockup and a cut-off modal.
- `deliver.py` refuses an MP4 without a passing, non-draft `qa/REPORT.json` whose `sha256`
  matches the file. Never copy a render to `deliveries/` by hand.

## 9. Safety

- Never print a secret. The voice key lives in the workbench `.env`, which the person writes
  themselves; scripts load it and never echo it. If a key appears in the chat, tell the person
  to rotate it.
- Never use the reviewer's personal browser, never sign in, never read browser storage. When the
  reviewer says stop, stop every action at once, including cleanup.
- Inputs (recordings, exports, documents) go into `references/` as soon as they arrive.
  Downloads and temp folders get cleaned by the system.
- Never kill processes you did not start: other renders may be running.

## 10. Read-only tools

<The product's API or MCP tools agents may call, one per line with what it is for (docs,
catalogs, templates), or "none: everything comes from sources/". Filled by product-kit.>
Every other tool or connection is off limits, and these are read-only even when the credential
behind them could write: ask for a credential scoped to read-only, because an instruction is the
only thing standing between an agent and a write otherwise.

## Review log

<!-- One entry per review round, newest last:
### YYYY-MM-DD: <reviewer>'s review of <video> v<k>
- <the rule that came out of it, and why>
-->
