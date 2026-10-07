# Product Video Skills

A workbench of agent skills that rebuild a product's real UI from its source code and render
narrated videos with HyperFrames. Status: phase 1 in progress (see the Roadmap in `README.md`).

Answer the user in their language. Write files, skills and docs in English.

## Conventions for working on this repo

- Skills live in `skills/<name>/SKILL.md`, with their scripts in `skills/<name>/scripts/`, called
  through `${CLAUDE_SKILL_DIR}`. `.claude/skills/` holds per-skill links made by
  `scripts/link-skills.sh` (gitignored).
- Every skill is either user-invoked (`disable-model-invocation: true`, reachable only when the
  user types it) or model-invoked. A user-invoked skill may call model-invoked skills through the
  Skill tool, never another user-invoked one. Anything that creates a product, starts a build or
  delivers a video is user-invoked.
- Every skill appears in the Reference section of `README.md` with a one-line description, its
  name linked to its `SKILL.md` once it ships.
- No real company, customer, person, workspace id, phone number or email anywhere in this repo.
  The example product is fictional. Nothing from the production this repo was distilled from is
  copied as is: rewrite it generic.
- Scripts never print a secret. The agent never reads `.env` (settings deny it); only
  `lib/pvs.py:env_value` loads a key, inside the script that needs it.
- Formats, paths and command lines are fixed in `docs/contracts.md`. Change a contract and every
  skill that reads it in the same pull request.
- HyperFrames is pinned in `package.json` and its skills come from the same release tag. Never run
  `hyperframes upgrade` or `hyperframes skills update` here: a version change is a pull request
  that passes `tests/run.sh`.
- No em dashes anywhere. Rewrite the sentence with a comma, colon, period or parentheses.
