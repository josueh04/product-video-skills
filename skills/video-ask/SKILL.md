---
name: video-ask
description: Say where this session stands in the Product Video Skills workbench (setup state, which product and video the current folder belongs to, the stage of every video) and the exact next command to type. Also answers "how do I..." questions about the workbench from its docs.
disable-model-invocation: true
argument-hint: "[question]"
---

# /video-ask

Orient the user in one screen: where they are, what state things are in, what to type next.

## 1. Read the state from files, not from memory

```bash
PVS_HOME="$(cd "$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/../.." && pwd)"
"$PVS_HOME/bin/pvs-py" "$PVS_HOME/skills/video-ask/scripts/status.py"
```

Pass a folder as the first argument when the user asks about one that is not the current folder.
Add `--json` if you need the fields (paths, versions, stages) to answer a precise question.

The script infers each video's stage from the files `docs/contracts.md` defines, newest stage
reached: brief unsigned, signed, sources fetched, truth, specs, voice, built, rendered, QA failed,
QA passed, delivered. A QA report only counts when its `sha256` matches the newest render, so a
re-render after QA shows as `rendered` again. Trust the script over what an earlier turn of the
conversation said: a subagent may have changed files since.

## 2. Answer

Show the script's output as it is (it is already short), then the next command on its own line.
If the user asked a question (the argument), answer it after the status, using these sources in
order, and say which file you used:

1. `$PVS_HOME/README.md` (what the skills are, the install, the inputs a product needs)
2. `$PVS_HOME/docs/contracts.md` (file formats, folder layout, command lines)
3. The `SKILL.md` of the skill the question is about, under `$PVS_HOME/skills/`
4. The product's `kit/RULES.md` for "why is this rule here" questions

If the answer is not in those files, say so instead of guessing.

## 3. Things to point out when you see them

- **Setup not done:** the next command is `/video-setup`. Nothing else works reliably before it.
- **Voice key not set:** the user pastes it into the workbench `.env` in their own editor, never
  in the chat. `voice.provider: say` works without one. Never read `.env` to check: the script
  already reports set or not set.
- **At the workbench root with products:** each product is its own Claude Code project, with its
  own skills and hooks. The user runs `cd products/<slug> && claude` to work on it.
- **Brief unsigned:** the build waits for the reviewer's two signatures on purpose. In the
  production these skills come from, 9 of 26 versions happened because nobody had agreed which
  features a video must explain. Do not suggest editing the signature fields for the reviewer.
- **QA failed:** point to `qa/REPORT.md` of that video for the failing checks.

Do not start building, fixing or delivering from here. This skill only reports; the user types
the next command.
