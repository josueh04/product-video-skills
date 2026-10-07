---
name: product-new
description: Interview the user about a product, then create products/<slug>/ with its own git history, a filled product.yaml and linked skills, fetch its sources and build its kit. Run only when the user types /product-new.
disable-model-invocation: true
argument-hint: "<slug> [--from examples/acme]"
---

# /product-new

Create one product folder in the workbench: a short interview, one script that writes the folder,
then the two model-invoked skills that fill it (`source-recon` fetches the code, `product-kit`
extracts tokens, fonts, icons, logos, cast and names).

Why an interview before anything else: in the production these skills come from, the cast, the
product names and the positioning arrived one review at a time, and each one forced a re-render.
Every answer collected here is one review round that does not happen later.

## Before you start

Resolve the workbench from this skill's real path (it works from the workbench and from a
product folder):

```bash
PVS_HOME="$(cd "$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/../.." && pwd)"
```

Check the slug from the arguments: 2 to 40 lowercase letters, digits or dashes, starting with a
letter. If `$PVS_HOME/products/<slug>` already exists, stop and say so: never overwrite a
product, it has its own history and probably signed briefs. If the user passed
`--from examples/acme` (or another folder), the interview only needs what differs from it.

Tell the user, once, before connecting any repo: Claude reads the product's code, which means it
is sent to the model as context. They should make sure their company allows that.

## 1. Interview

Ask in small groups (two or three questions per message), in the user's language. Propose a
default for anything you can infer, so the user mostly confirms. The full question list with
the reason behind each one is in `references/interview.md`; read it before asking.

1. **The product**: its name, what it is in one sentence (the positioning), who it is for.
2. **Never-say phrases**: descriptions the team rejects, even if a company document uses them.
3. **Sources**: for each one (frontend, backend, design, docs), a git URL or a local path, the
   branch that is in production, the app dir and the framework (`angular-primeng`, `react`,
   `vue`, `svelte`, `html`, `other`). Ask which branch is really deployed: a stale checkout
   cost real time in the original production.
4. **Docs**: URLs, repo paths or `mcp:<name>` (read-only).
5. **Brand**: only if it is not in the frontend (logo and font files). Otherwise `product-kit`
   finds it.
6. **Fictional cast**: propose a company and two or three people with full names, a 555 phone
   and an email on an `example`/`.test` domain. Offer it for veto in one closed question with
   your proposal as the default. Reviewers react strongly to bland or real-sounding names, and
   a person whose surname changes between videos is a bug that ships.
7. **Names and pronunciations**: the canonical names, the legacy strings the live UI may still
   show, and how brand words are spoken.
8. **Banned terms**: competitors, vendors, real customers, anything that must never be seen or
   heard.
9. **Reviewer**: who signs the coverage matrix and the claims sheet of each video.

Never ask for a token, a password or an SSH key, and never offer to store one. Sources are
fetched with the git access the machine already has. If a URL contains credentials
(`https://user:token@...`), ask the user to remove them; the script refuses them anyway.

## 2. Write the folder

Write the answers to a scratch file shaped like `product.yaml` (any subset; see
`references/answers.example.json`), outside the repo, then run:

```bash
"$PVS_HOME/bin/pvs-py" "$PVS_HOME/skills/product-new/scripts/new_product.py" <slug> \
  --answers <scratch>/answers.json [--from examples/acme]
```

The script copies `_template/product` and then the `--from` folder over it (so an example that
lacks a file, like `kit/RULES.md`, still gets the template's), merges the answers into
`product.yaml` line by line (the template's comments are the user's documentation, so they are
kept), writes `CLAUDE.md` and `.gitignore` when the template has none, runs
`scripts/link-skills.sh` so `cd products/<slug> && claude` sees the same skills, and makes a
first git commit. It refuses an existing slug, credentials in a URL, and cast emails or phones
that are not obviously fictional. If it fails, fix the answer it names and run it again; do not
create the folder by hand.

If it prints "still to fill in product.yaml", those are template placeholders the interview did
not cover. Ask about them, or tell the user which ones remain.

## 3. Fill it

Call these model-invoked skills through the Skill tool, in this order:

1. `source-recon`, to fetch every source into `products/<slug>/sources/` and pin it in
   `sources.lock`. If a fetch fails for access, report the exact git error and stop: the user
   fixes access on their machine, never by giving you a credential.
2. `product-kit`, to extract `kit/tokens.css`, fonts, icons, logos, and to write the cast,
   names and pronunciations into the kit and `kit/RULES.md`.

Both write only inside the product folder. Never edit anything in `sources/`.

## 4. Report

One short table, then the next command:

| Item | Value |
|---|---|
| Folder | `products/<slug>/` (git: first commit or why not) |
| Sources | role, branch, commit from `sources.lock` |
| Kit | what product-kit extracted, and what it could not find |
| Cast | the frozen names, for a last veto |
| Open | placeholders still in product.yaml, anything unverified |

Next: `cd products/<slug> && claude`, then `/video-new <video>`.
