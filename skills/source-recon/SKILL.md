---
name: source-recon
description: Pin a product's source code (read-only exports in sources/ plus sources.lock), confirm that the pinned commit is what runs in production, and map every screen of a video brief to its route, components, i18n strings and state, written to the video's SOURCES.md. Use it whenever a video needs to know where a screen lives in the code, when sources/ is missing or stale, before ui-spec-from-code or product-truth start on a video, after the product's frontend changed ("what changed", "which videos are affected", "refresh the sources", "is this checkout current", "which commit is in prod"), and when there is no code and you need an inventory of the no-code references (recordings, recovered captures, docs) a screen can be rebuilt from.
---

# Source recon

Every pixel and every sentence of a video is checked against code later, so the code has to be
the right code. In the production these skills come from, the main frontend checkout was about
two months behind production while the current code sat in another worktree that nobody looked
at for three days. Three versions of one video were rebuilt from the old code before anyone
noticed. This skill exists so that never happens again: pin the sources first, prove they are
production, then map screens to files.

Work read-only. You read code; you never edit, check out, fetch into, or create worktrees in the
user's repositories. Their working tree can hold uncommitted work, and a checkout or a fetch
changes state they did not ask you to change.

## 1. Pin the sources

```bash
PVS_HOME="$(cd "$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/../.." && pwd)"
"$PVS_HOME/bin/pvs-py" "$PVS_HOME/skills/source-recon/scripts/fetch_sources.py" <product_dir>
```

It reads `sources:` from product.yaml and, per role:

- `url:` shallow-clones the branch into `sources/.git-cache/<role>.git` and exports it.
- `path:` to a git repo: `git archive` of the newer of `<branch>` and `origin/<branch>`. It
  warns when the local branch is behind or has diverged, when origin refs were fetched more
  than a week ago, and when another worktree of the same repo is newer than the export.
- `path:` that is not a git repo: copied and pinned by a hash of its files (`"pinned": false`,
  so citations to it can go stale without warning; prefer a git source).

Exports land in `sources/<role>/`, read-only, and `sources.lock` records the commit. A locked
role that is missing on disk (a fresh clone of the product repo) is restored at its locked
commit, so citations keep pointing at the same lines. Read every `note:` line it prints and
act on it before going on: each one is a way the export may not be production.

Citations everywhere downstream use `<role>/<path>:<line>@<short sha>`, where the path is
relative to the repo root (so `sources/<role>/<path>` exists) and the sha is the locked one.

## 2. Prove it is production

A branch name is not proof. Production is whatever the deploy pipeline last built. Before
mapping any screen, establish which commit is live, in this order of strength:

1. A release record: a release tag, a deploy log, a "last deployed sha" file in a deploy repo.
2. The deploy pipeline config: which branch it builds from, and its build arguments
   (environment variables baked into the build can change branding or hide features).
3. The newest branch the team confirms is deployed, checked against `git worktree list`, branch
   dates and `merge-base`.

Read `references/freshness.md` for the exact commands and the traps (stale remote refs, feature
flags, build arguments that change what renders). If you cannot confirm the production commit,
say so at the top of SOURCES.md ("production commit unconfirmed") and ask the user one closed
question with a recommended answer, for example: "Export `origin/develop` (newest, contains
main) as production? Recommended: yes, it is what the deploy workflow builds."

When the user confirms a different branch, change `branch:` in product.yaml and run
`fetch_sources.py <product_dir> --refresh --role <role>` (if videos already cite this source,
run `changed_since.py` first, section 6).

## 3. Map each screen

Take the screens and states from the video's BRIEF.md (chapters) and COVERAGE.md. Launch one
read-only Explore subagent per screen, or per small group of screens that share components, in
parallel. Give each the prompt in `references/recon-prompt.md`, pointed at `sources/<role>/`
(the pinned export, never the user's checkout) so every line number it returns matches the lock.

Each subagent returns, with citations: the route, the page and child components (template,
logic, style files), the i18n keys and their exact strings in the video's language, the state
that decides what renders (defaults, flags, feature gates, empty states, permission checks),
the icon sets and assets in use, and anything that looks unreleased, gated or restricted.

Then check the copy against production yourself: spot-check two or three strings per screen
against any reference you have (a recording, a recovered capture, the docs). A string that
differs means the export is not production or the screen is behind a flag; resolve it before
writing SOURCES.md.

## 4. Write SOURCES.md

One file per video, at `videos/<video>/SOURCES.md`:

```markdown
# Sources: <video>

Locked: frontend main@1a2b3c4 (2026-01-12), backend main@5d6e7f8 (2026-01-10)
Production: confirmed by <release tag v4.2.0 | deploy workflow builds main | team confirmation>

| screen | route | components | citation |
|---|---|---|---|
| Board, empty | /board | BoardPage > TaskList > EmptyState | frontend/src/pages/board/BoardPage.tsx:14@1a2b3c4 |

## Board, empty
- Strings: `board.empty.title` "Nothing planned yet" (frontend/src/i18n/en.json:88@1a2b3c4)
- State: renders when `tasks.length === 0` (frontend/src/pages/board/TaskList.tsx:41@1a2b3c4)
- Icons: lucide `calendar-plus` (frontend/src/pages/board/EmptyState.tsx:9@1a2b3c4)
- Flags or gates: none found
- Not found: <anything the brief needs that the code does not have>

## No-code references
<what exists for each screen without code, see section 5>
```

A screen with no citation does not go in the video. List it under "Not found" and tell the user;
inventing a screen is the one mistake reviewers do not forgive, because it shows a product that
does not exist.

## 5. List the no-code references

For screens the code cannot show (third-party UI, runtime output, a backend not in the repos,
or no frontend code at all), list what is available, in this order of preference: analyzed
screen recordings in `references/`, captures recoverable from past session transcripts, a local
instance of the app built like production, public docs and screenshots. Do not capture anything
yourself here; that is `ui-reference-capture`. Never plan on the reviewer's personal browser.

## 6. When the code changes

```bash
"$PVS_HOME/bin/pvs-py" "$PVS_HOME/skills/source-recon/scripts/changed_since.py" <product_dir> [--offline]
```

It diffs each locked commit against the current branch head and lists every video (and kit file)
whose SOURCES.md, TRUTH.md, specs or `video/src/` cite a changed file, marking citations whose
exact lines changed. It moves nothing. Run it before any `--refresh`: it compares the lock with
the head, and a refresh makes them equal, so afterwards the list of what changed is gone (the
script then prints a hint instead). Show the user that list, then, if they want the new code,
run `fetch_sources.py --refresh`, rerun `ui-spec-from-code` for the affected screens and
`product-truth` for the affected lines. Videos that cite nothing changed are left alone.

## Rules and why

- **Read the export, cite the lock.** Line numbers from a different checkout silently point at
  the wrong code after the next refresh.
- **Never print secrets you find in code.** Frontends often hold keys and tokens. Report the
  file and line only, and treat it as a security finding for the user.
- **Unreleased, gated or restricted features are facts too.** Mark them in SOURCES.md
  (`gate: <flag>`, `restricted: <who sees it>`). product-truth decides whether the video can
  show them, usually with the reviewer's sign-off.
- **Real data stays out.** Fixtures and seed files in a repo can hold real customer names. Cite
  their structure, never their values.
