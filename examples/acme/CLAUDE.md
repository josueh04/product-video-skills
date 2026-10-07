# Acme Tasks: product videos

This folder is one product of the Product Video Skills workbench. The workbench is two levels up
(`../..`); the session-start hook also exports its path as `$PVS_HOME`. Answer the user in their
language; write files in English.

## Read first

1. `kit/RULES.md`: the video rules for this product. Every agent reads it before working.
2. `product.yaml`: names, banned terms, cast, brand, voice. Never hard-code what it holds.
3. `$PVS_HOME/CLAUDE.md` and `$PVS_HOME/docs/contracts.md`: workbench conventions and file
   formats.

## The pipeline

Each video lives in `videos/<video>/` and moves through these stages. `/video-ask` tells you the
stage of every video and the next command.

| Stage | What exists | Next |
|---|---|---|
| brief unsigned | `BRIEF.md`, `COVERAGE.md`, `CLAIMS.md` | The reviewer signs both sheets in the BRIEF frontmatter |
| signed | both signatures | `/video-build <video>` |
| sources fetched | `sources.lock`, `SOURCES.md` | product truth |
| truth | `TRUTH.md` | UI specs |
| specs | `specs/<screen>.md` | voice |
| voice | `audio/clips/`, `audio/timings.json` | composition and build |
| built | `video/index.html` | render |
| rendered | `video/renders/<video>-v<k>.mp4` | QA |
| QA passed | `qa/REPORT.json` with `"passed": true` | delivery |
| delivered | `deliveries/<name>.mp4` | `/video-review <video>` with the next feedback |

Start a video with `/video-new <video>`. Build with `/video-build <video>`. Turn a round of
feedback into the next version with `/video-review`.

## Never

- Edit anything in `sources/`. It is a read-only export pinned in `sources.lock`; the guard hook
  blocks writes. Refresh it with the source-recon fetch script and `--refresh`.
- Edit `video/index.html` by hand: `build.py` generates it.
- Read `.env` or print a key. Deliver an MP4 without a passing QA report.
- Show a real customer, person, phone or email. Use the cast in `product.yaml`.
