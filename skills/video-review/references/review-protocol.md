# Review protocol

How a round of feedback is read, consolidated and closed. Each point comes from a round that
went wrong without it in the production these skills come from.

## Reading the notes

- **Keep the reviewer's words verbatim**, in their language, in the table and in the fix
  prompt. Your reading goes in a separate column. A fixer that only sees your paraphrase fixes
  your paraphrase.
- **Expect dictation errors.** Reviewers dictate. A word that makes no sense is often a
  near-homophone of a product term ("zoomed in" came through as a nonsense word once, and a
  feature name as two unrelated words). Read it against the product's vocabulary before asking.
- **Times and screenshots locate notes.** "At 0:30", "around 1:02" go into the Where column and
  become strips in the acceptance check.
- **"Use X as the example"** means a sibling video is the model: name it in the fix prompt and
  say what to imitate (framing, pacing, how a setting is explained).
- **A note can be a rule.** "Explain the configuration", "never say Y", "no zoom at the start":
  apply it to every video in the round and add it to `kit/RULES.md` when the round closes.
- **A note can conflict with the product.** If the reviewer asks for a behaviour the code does
  not have, ask one closed question with the honest option recommended ("show only what
  exists"). Never animate an invented feature to satisfy a note.

## Consolidated table

Per video: `# | Reviewer's words | Where | Meaning | Acceptance | Rule for all videos?`.

- **Meaning** includes what must NOT change. Fixers that knew only what to change also changed
  approved parts.
- **Acceptance** is checkable: a time range, a frame, a strip, a line of narration, a parity
  skip. "Looks better" is not acceptance.
- Videos with no notes: listed as untouched. They get no agent and no new version.

## Asking

- At most three decisions per message, closed, each with a default, and say that silence means
  the default. Two closed questions in the original production were answered in minutes; eleven
  open veto lists were never answered, and the silence left a character with two surnames.
- Never ask the reviewer to repeat a rule for another video. If you are unsure whether a note
  is a rule, propose applying it everywhere as the default.

## Versions

- One file per version: `renders/<video>-v<N>.mp4`. Never overwrite a file that may have been
  shared; the first render of a video in the original production was overwritten twice.
- The previous version's sources are backed up by `bump_version.py` before any edit.
- One `### v<N>` section per version in BRIEF.md: date, the quote, the changes, the sources for
  new screens, the parity numbers, how to revert.

## Closing the round

1. Rules that came out of the notes go into `kit/RULES.md`, dated, with the quote.
2. Every BRIEF changelog section is filled.
3. Stale goals are cleared: if the reviewer changed direction mid-round, drop the old plan
   explicitly. An old goal kept firing in the original production after the reviewer said stop.
4. If the reviewer said stop at any point, stop every action, including cleanup.
