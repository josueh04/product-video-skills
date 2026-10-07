---
name: video-setup
description: Check this machine and install the pinned video toolchain of the Product Video Skills workbench (HyperFrames CLI, its rendering Chrome and its agent skills from the same release, the Python environment, the speech model for QA), then run the self-check. Safe to run again. `/video-setup check` only reports.
disable-model-invocation: true
argument-hint: "[check]"
---

# /video-setup

Get the workbench from a fresh clone to `passed N, failed 0` in one step. `setup.sh` does the
work; your job is to explain it, get a yes, run it, and turn every FAIL line into its fix.

Find the workbench first (this works from the workbench and from a product folder):

```bash
PVS_HOME="$(cd "$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/../.." && pwd)"
```

Talk to the user in their language. Keep it short: they want a working setup, not a tour.

## With the argument `check`

Run `bash "$PVS_HOME/setup.sh" --check` and show the result. It installs nothing, downloads
nothing and writes nothing. For each FAIL line, give its fix (the line ends with it). Stop there.

## Otherwise

### 1. Report the machine

Run `bash "$PVS_HOME/setup.sh" --check` first. It prints one line per item: `ok`, `warn` or `FAIL`
with the exact fix.

- If a line under **Machine** fails (node 22+, python 3.9+, ffmpeg, git), setup cannot continue.
  Give the user the fix from the line (for example `brew install ffmpeg`) and ask them to run it
  in their terminal, then run the check again. Installing system packages is their call, so do
  not run `brew` or `apt` yourself unless they ask you to.
- A `warn` on Claude Code is informational.
- FAIL lines under **Toolchain** are what setup installs. That is expected on a first run.

### 2. Say what will be downloaded, and ask once

Tell the user, in one short list, only the pieces the check reported missing:

| Piece | Size | Where |
|---|---|---|
| HyperFrames CLI at the pinned version, with its dependencies | about 128 MB | `node_modules/` |
| The Chrome build HyperFrames renders with | about 195 MB (skipped if cached) | the HyperFrames cache |
| HyperFrames agent skills from the same release tag | a few MB | `vendor/hyperframes/skills/` |
| Python packages, mostly torch for speech to text | about 339 MB | `.venv/` |
| The whisper `small.en` speech model the QA uses | 484 MB | `~/.cache/whisper/` |

Ask one closed question: "Install these now? (yes / no)". The setup should happen in one step
from the first `/video-setup`, so do not split it into several confirmations.

### 3. Run it

On yes, run `bash "$PVS_HOME/setup.sh" --yes` (the `--yes` is the user's answer, already given).
It takes a few minutes on a first run and seconds when everything is cached; use a timeout of at
least 10 minutes. It is idempotent: running it again only redoes what is missing.

### 4. Handle each FAIL

Every FAIL line names its fix. The common ones:

| FAIL | What to do |
|---|---|
| `npm install failed` | Network or registry problem. Show the last lines of the log it names, then run setup again |
| `hyperframes browser ensure failed` | Run `npx hyperframes browser ensure --force` from the workbench, then setup again |
| `could not clone heygen-com/hyperframes` | Network or GitHub access. Check `git ls-remote https://github.com/heygen-com/hyperframes`, then setup again |
| `python3 -m venv failed` | On Debian or Ubuntu: `sudo apt install python3-venv` (the user runs it) |
| `pip install -r requirements.txt failed` | Show the log tail. A Python newer than the pins can need a newer wheel; report it rather than editing the pins |
| `hyperframes doctor: ...` | The line names the failing check and its fix. Version, Docker and the optional local voice and music checks are ignored on purpose |
| `tests/run.sh: passed N, failed M` | Run `bash "$PVS_HOME/tests/run.sh"` and show the failing tests with their output |

Never "fix" a FAIL by running `hyperframes upgrade` or `hyperframes skills update`. The workbench
pins one HyperFrames release and takes its skills from the same tag, because a CLI and skills
from different releases disagree about the composition contract. A version change is a pull
request that passes `tests/run.sh`. The guard hook blocks both commands anyway.

### 5. The voice key

Setup creates `.env` from `.env.example` and tells you whether the ElevenLabs key is set,
without printing it. If it is empty, tell the user:

- Open `.env` (in the workbench folder) in their own editor and paste the key after
  `ELEVENLABS_API_KEY=`. Never in the chat: anything in the chat is stored in the transcript.
  If they paste it here anyway, tell them to rotate it.
- Without a key, `voice.provider: say` in a product's `product.yaml` uses the free macOS voices,
  good enough for drafts and tests.

Never open, read or print `.env` yourself. The settings deny it and the guard hook blocks it, and
the scripts load the key through `lib/pvs.py` on their own.

### 6. Close

Confirm the last lines of the output say `passed N, failed 0` and `Setup done`. Then give the
next step in one line: `/product-new <slug>` to bring their product, or `/video-ask` to see where
things stand.
