# Is this code production?

Read this before trusting a pinned commit. Every command here only reads the repo.

## Find the newest candidate

```bash
git -C <repo> worktree list                      # other checkouts of the same repo
for b in main develop origin/main origin/develop; do
  git -C <repo> log -1 --format="%h %cs %s" "$b" 2>/dev/null | sed "s#^#$b  #"
done
git -C <repo> merge-base --is-ancestor origin/main origin/develop && echo "develop contains main"
git -C <repo> for-each-ref --sort=-committerdate --count=10 --format="%(committerdate:short) %(refname:short)" refs/heads refs/remotes
stat -f "%Sm" "$(git -C <repo> rev-parse --absolute-git-dir)/FETCH_HEAD"   # when origin refs were last updated (macOS stat)
```

Remote-tracking refs are only as fresh as the last `git fetch`. `fetch_sources.py` warns when
they are older than a week. It never fetches into the user's repo: ask the user to run
`git fetch` themselves, or add the repo as a `url:` source, which the script clones on its own.

## Find what is deployed

Look for these, in the repo and in any deploy repo next to it:

| Evidence | Where it usually lives |
|---|---|
| Release tags | `git tag --sort=-creatordate | head` |
| Deploy workflow | `.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile`, `vercel.json`, `netlify.toml`, `Dockerfile` |
| Last deployed commit | A state file a deploy job writes, a release-notes file, a changelog entry |
| Build arguments | `env:` and `build-args:` in the workflow, `.env.production`, `ARG` lines in a Dockerfile |

Build arguments matter as much as the commit. A variable baked into the build (a product name,
a brand switch, a feature flag) can change what renders. In the production these skills come
from, one wrong build argument in a local instance silently turned the brand off and a badge
was rebuilt wrong. Copy the production values into SOURCES.md next to the commit.

## Read a ref without touching the checkout

`fetch_sources.py` already exports the right ref. When you need to look at another branch
before deciding, read it in place:

```bash
git -C <repo> show origin/develop:src/pages/board/BoardPage.tsx
git -C <repo> grep -n "board.empty" origin/develop -- src
git -C <repo> ls-tree -r --name-only origin/develop -- src/pages/board
git -C <repo> cat-file -e "origin/develop:src/styles.css" && echo exists
git -C <repo> diff --stat main origin/develop -- src/pages/board
```

## Traps

- **The local branch is old.** The script exports `origin/<branch>` when it is newer, but only
  if origin refs were fetched recently.
- **The newest work is on another branch.** A feature branch that contains `origin/develop` can
  be what the team demos. Ask; do not guess.
- **Feature flags.** Code can be merged and hidden. Search for the flag names around a screen
  (`flag`, `feature`, `isEnabled`, `gate`, `canary`, `beta`) and record which state production
  uses.
- **Permission gates.** Some screens render only for some roles or plans. Record who sees it.
- **Generated or vendored UI.** A component library in `node_modules` is not in the export. Note
  the package and version from the lockfile so ui-spec-from-code can find its defaults.
- **Monorepos.** Several apps share one repo; `app_dir` in product.yaml says which one renders.
