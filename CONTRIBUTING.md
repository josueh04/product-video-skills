# Contributing

Thanks for wanting to help. The project is early: the skills are being written, and the [Roadmap](README.md#roadmap) says what exists today.

## Issues

The most useful issue describes something that went wrong in a real session: what you ran, what the skill did, and what you expected. Ideas are welcome too; say which problem they solve.

Never paste real customer data, secrets or private source code into an issue. Use fictional names and leave your paths out.

## Pull requests

- One skill or one fix per pull request.
- A skill lives in `skills/<name>/SKILL.md`, with its scripts in `skills/<name>/scripts/`, called through `${CLAUDE_SKILL_DIR}`.
- A skill is either user-invoked (`disable-model-invocation: true`) or model-invoked. [CLAUDE.md](CLAUDE.md) has the rules.
- Add the skill to the Reference section of the README with a one-line description.
- No real company, customer or person anywhere. The example product is fictional.
- Scripts never print a secret and never read `.env`.
- English everywhere, and no em dashes.
- Once the self-check exists, run `bash tests/run.sh` before you open the pull request.

Contributions are licensed under [Apache-2.0](LICENSE), like the rest of the repo.
