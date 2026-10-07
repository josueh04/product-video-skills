# The /product-new interview

Every question maps to a key of `product.yaml` (docs/contracts.md section 2). Each one exists
because its absence cost at least one re-render in the production these skills come from.

| Question | Key | Why it is asked now |
|---|---|---|
| What is the product, in one sentence? | `product.positioning` | The positioning is fixed by the team, not taken from a document. A company doc once titled a product with a phrase the team had banned, and the video repeated it until a review caught it. |
| How must it never be described? | `product.never_say` | Banned phrasings get grepped in the script and the render. Without the list they are found by the reviewer, one render later. |
| Where is the frontend? Which branch is in production? Which app dir, which framework? | `sources[]` (`role`, `url` or `path`, `branch`, `app_dir`, `framework`) | The UI is rebuilt from production code. A stale checkout (the deployed code lived in another worktree) made agents rebuild old screens. |
| Is there a backend, design repo or anything else with behaviour? | `sources[]` | Claims about behaviour need a source. The backend is read to verify, never drawn. |
| Where are the docs? | `docs` | `product-truth` backs sentences with docs pages. Read-only MCPs go in as `mcp:<name>`. |
| Is the brand (logo, font) outside the frontend? | `brand` | Hand-drawn logos and icons were rejected on the first review. Official assets only. |
| Which fictional company and people appear? | `cast` | Real customers, team emails and phone numbers appeared in the reference recording. A demo name the reviewer disliked was vetoed late; a person ended up with two surnames across videos. Propose once, freeze. |
| Which names are current, and which legacy strings may the UI still show? | `product.names` | Two renamed products still had their old names in the live UI. Each rename cost a render per video. |
| How are brand words pronounced? | `product.pronounce` | The TTS mispronounced the brand name on the first take. The spoken form goes to the TTS only; the screen keeps the spelling. |
| What must never be seen or heard? | `product.banned_terms` | Third-party vendor names in a pitch video were a turn-off for the audience; they came out one video at a time. |
| Who reviews and signs? | `review.reviewer` | `/video-new` stops until this person signs coverage and claims. |

## How to ask

- Two or three questions per message. Infer what you can (a `package.json` names the framework,
  a README states the positioning) and ask the user to confirm instead of to type.
- For the cast, propose concrete names and ask one closed question: "Use this cast? (default:
  yes)". Open lists of vetoes went unanswered in the original production, and silence then
  meant nothing in particular.
- Emails on `example.com`, `.example` or `.test` domains, phones with 555 numbers. The script
  refuses anything else.
- Never ask for tokens, passwords or keys. The TTS key lives in `$PVS_HOME/.env`, which the user
  writes themselves (`/video-setup` explains how).

## answers.json

Same shape as `product.yaml`, any subset. Lists replace the template's list; mappings merge.
See `answers.example.json` next to this file.
