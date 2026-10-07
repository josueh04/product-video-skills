<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.svg">
    <img alt="Product Video Skills" src="assets/logo-light.svg" width="440">
  </picture>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/status-alpha-orange" alt="status: alpha">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-Apache%202.0-blue" alt="license: Apache 2.0"></a>
  <img src="https://img.shields.io/badge/Claude%20Code-2.1%2B-d97757" alt="Claude Code 2.1+">
  <img src="https://img.shields.io/badge/node-%3E%3D22-brightgreen" alt="node >= 22">
  <a href="https://github.com/heygen-com/hyperframes"><img src="https://img.shields.io/badge/built%20on-HyperFrames-6366F1" alt="built on HyperFrames"></a>
</p>

<h3 align="center">Read your code. Rebuild your UI. Render the demo.</h3>

<p align="center">
  <a href="#installation-15-minute-setup">Install</a> |
  <a href="#why-these-skills-exist">Why</a> |
  <a href="#reference">Skills</a> |
  <a href="#what-your-product-needs-to-provide">Inputs</a> |
  <a href="#roadmap">Roadmap</a> |
  <a href="CONTRIBUTING.md">Contributing</a>
</p>



<div style="position: relative; padding-bottom: 56.2500%; height: 0;"><iframe style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0;" src="https://www.tella.tv/video/vid_cmuyf2jkq004b05nt2wz88lcp/embed?b=0&title=0&a=1&loop=0&t=0&muted=0&wt=0" allow="autoplay; fullscreen" allowtransparency></iframe></div>



Agent skills that turn your product's real source code into narrated product videos: demos for a pitch, walkthroughs for your docs, tutorials for your users.

No screen recordings and no invented UI. The skills rebuild your interface 1:1 in HTML and CSS from your production code, animate it as if someone were using it, sync every movement to a word of the narration, and render it to MP4 with [HyperFrames](https://github.com/heygen-com/hyperframes). Every frame and every sentence is checked before a video is delivered.

They come out of a real production: five narrated product demos, 26 versions and 33 renders. Every rule in them exists because something went wrong without it.

> [!IMPORTANT]
> **Alpha.** All 15 skills, the setup and the self-check work, and a fictional example product renders end to end on macOS. Only one real product has been through the pipeline so far, and only the Angular with PrimeNG adapter is proven. The [Roadmap](#roadmap) says what is next.

## Installation (15-minute setup)

### 1. Get the workbench

```bash
git clone https://github.com/josueh04/product-video-skills.git
cd product-video-skills
claude
```

This repo is a workbench, not only a set of skills: it pins the video engine, ships the scripts the skills call, and keeps one folder per product. That is why you clone it instead of installing a plugin. A plugin for skills-only installs is on the [roadmap](#roadmap).

<details>
<summary><strong>What you need</strong></summary>

| Need | Detail |
|---|---|
| macOS | Linux should work except OCR of screen recordings (untested) |
| Claude Code | 2.1 or newer |
| Node.js | 22 or newer (HyperFrames requires it) |
| Python | 3.9 or newer |
| ffmpeg | `brew install ffmpeg` on macOS |
| An ElevenLabs account | For the narration. Without one you can try a local voice |
| Disk | About 1.1 GB for the first setup |

</details>

### 2. Run `/video-setup`

The first time, it:

- Checks your machine and gives you the exact fix for anything missing
- Installs HyperFrames at the pinned version, its rendering Chrome and its agent skills, all from the same release
- Creates the Python environment and downloads the speech model the QA uses
- Asks you to paste your ElevenLabs key into `.env` yourself, never into the chat
- Runs the self-check (it must end with `passed N, failed 0`), then voices, renders and QA-checks the fictional example video

It tells you what it will download and asks before installing anything. Prefer a terminal? `bash setup.sh` runs the same installs.

### 3. Bring your product

```
/product-new acme
```

A short interview: what the product is and how it is positioned, where its code lives, its brand, a fictional cast for the demo data, and the names that must never appear on screen. It creates `products/acme/` with its own git history and extracts your design tokens, fonts, icons and logos.

### 4. Make a video

```
cd products/acme && claude
/video-new pitch
```

`/video-new` writes the brief, the feature coverage matrix and the claims sheet, then stops until your reviewer signs them. After that, `/video-build` makes the video and `/video-review` turns the next round of feedback into the next version.

## Why These Skills Exist

### #1: The Video Shows a Product That Doesn't Exist

**The Problem.** Mockups and AI video tools invent screens, buttons and features. A demo that shows something the product can't do is worse than no demo.

**The Fix.** The UI is rebuilt from your production code, never drawn from memory. `ui-spec-from-code` cites `file:line@commit` for every value it uses, and `product-truth` blocks any sentence of the script that has no source in the code or the docs.

### #2: Screen Recordings Go Stale

**The Problem.** A recording is frozen. A renamed button, a typo, a real customer's name in a list, and you record it all again.

**The Fix.** The interface is HTML and the data is fictional from day one. Every movement is anchored to a word of the narration, so changing a sentence regenerates that line of voice and re-times the whole video. When your frontend changes, `source-recon --refresh` lists the videos that cite files that changed.

### #3: The Reviewer Keeps Sending It Back

**The Problem.** In the production these skills come from, 9 of the 26 versions happened for one reason: a video didn't explain a feature the reviewer cared about. Nobody had written those features down before building.

**The Fix.** `/video-new` writes a feature coverage matrix (what each video must explain on screen, not only list at the end) and a claims sheet (positioning, phrases to avoid, claims that need approval). Nothing gets built until the reviewer signs both, and the check is code, not a reminder.

### #4: Glitches Ship

**The Problem.** Flicker from parallel render workers, a click in the audio, a narration that drifted from the script, a competitor's name on screen.

**The Fix.** `render-qa` checks every render: black frames, overlaps, loudness, clipping, clicks at clip edges, speech-to-text against the script and banned terms, plus contact sheets and frame strips at every transition. The delivery script refuses an MP4 without a passing QA report.

## Reference

Like [mattpocock/skills](https://github.com/mattpocock/skills), these split on one axis: who can invoke them. **User-invoked** skills run only when you type them, and they orchestrate. **Model-invoked** skills hold one discipline each, and the agent reaches for them when the task fits. A user-invoked skill may call model-invoked skills but never another user-invoked one, so the agent can't create a product or deliver a video on its own.

### User-invoked

- **[video-setup](skills/video-setup/SKILL.md)**: Check the machine, install the pinned toolchain and render the example. Safe to run again; `/video-setup check` only reports.
- **[video-ask](skills/video-ask/SKILL.md)**: Which product and video this session is on, at which stage, and what to type next.
- **[product-new](skills/product-new/SKILL.md)**: Interview, then create a product folder with its kit: tokens, fonts, icons, logos, fictional cast, names and pronunciations.
- **[video-new](skills/video-new/SKILL.md)**: Write the brief, the feature coverage matrix and the claims sheet, then stop for sign-off.
- **[video-build](skills/video-build/SKILL.md)**: Coordinate the build with subagents: product truth, UI specs, voice, composition, render, QA and delivery. It coordinates and never builds itself.
- **[video-review](skills/video-review/SKILL.md)**: Turn a batch of feedback into one fix per video, run them in parallel, check them and deliver the next version.

### Model-invoked

- **[product-kit](skills/product-kit/SKILL.md)**: Extract what every video of a product reuses: tokens, fonts, icon subsets, logos, the fictional cast, names and pronunciations.
- **[source-recon](skills/source-recon/SKILL.md)**: Map each screen of the brief to its route and components, and check that the copy of the code matches production.
- **[product-truth](skills/product-truth/SKILL.md)**: Back every sentence and every screen with a source, or cut it.
- **[ui-spec-from-code](skills/ui-spec-from-code/SKILL.md)**: One read-only subagent per screen returns static HTML, CSS with literal values and citations, and transitions with their timings. One adapter per framework; Angular with PrimeNG is the only one proven so far.
- **[ui-reference-capture](skills/ui-reference-capture/SKILL.md)**: For UI without code: frames and timed OCR from screen recordings, a local instance of the app, or research on third-party apps.
- **[script-and-voice](skills/script-and-voice/SKILL.md)**: The script as `lines.tsv` with one clip per sentence, word timings, pronunciation fixes, sound effects and loudness.
- **[ui-demo-composer](skills/ui-demo-composer/SKILL.md)**: The stage (camera, focus, titles, cursors, typing, pop-ups, end screen) and the build that anchors every beat to a word.
- **[seek-safe-motion](skills/seek-safe-motion/SKILL.md)**: The animation rules that keep parallel render workers from dropping or flickering elements.
- **[render-qa](skills/render-qa/SKILL.md)**: Automatic checks, contact sheets, frame strips, and parity against the approved version.

## What Your Product Needs to Provide

| Input | Required? | How |
|---|---|---|
| Frontend repo | Yes, for UI rebuilt from code. Without it, only screen recordings | A git URL or a local path, plus the branch that is in production |
| Backend repo | Recommended | Same as the frontend. Used to verify claims, never drawn |
| Docs | Optional | A URL, a repo or a read-only MCP |
| Screen recordings | Strongly recommended | One `.mov` or `.mp4` per feature |
| Brand | Only if it isn't in the frontend | Logo and font files |

The skills never ask for tokens or passwords: they use the git access your machine already has. Your code stays on your machine, read-only, in `products/<slug>/sources/`, pinned to a commit in `sources.lock`.

> [!NOTE]
> Claude reads your code, which means it is sent to the model as context. Make sure your company allows that before you connect a repo.

## Roadmap

| Phase | What | Status |
|---|---|---|
| 1. Skeleton | `setup.sh`, `/video-setup`, `/video-ask`, the rules, hooks, templates, a fictional example product and the self-check | Done on macOS. Not yet tried on a fresh machine by someone else |
| 2. Port what's proven | One TTS client, the QA scripts with their gates, the stage kit and the build library | Done. QA reproduces the original production's numbers on one of its renders |
| 3. Orchestrators | `/product-new`, `/video-new`, `/video-build`, `/video-review` and the research skills | Written and unit-tested. The example ran through every stage; the subagent dispatch of `/video-build` has not run end to end yet |
| 4. Pilot | Someone outside the project, with their own product and another frontend framework | Next. Done when it works by changing only `product.yaml` and a framework adapter |
| 5. Distribution | A Claude Code plugin, `npx skills add`, Codex, long tutorials, other languages | Later. Done when `claude plugin validate . --strict` passes |

## License

[Apache-2.0](LICENSE). Built on [HyperFrames](https://github.com/heygen-com/hyperframes) by HeyGen (also Apache-2.0), which setup installs and this repo does not bundle.
