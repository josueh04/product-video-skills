# Prompt: reference for a third-party UI (no source code)

Use when the video shows another company's product (a calendar, a CRM record, a sign-in or
consent page, a chat app). There is no code, so a research subagent gathers public references
and measurements and another agent rebuilds a simplified but faithful version.

Choose the access level before launching, and write it into the prompt:
- **Web research only** (official docs, help centers, press kits, official screenshots). The
  default.
- **Headless browser on a public demo page owned by the vendor**, only if the user allows it.
  Fresh headless profile, never logged in, never submit, never book, never a private person's
  page, block trackers and abort every request that is not a GET.

---

Goal: build a faithful visual reference of `<vendor>` `<widget or screen>`, so another agent can
rebuild it close to pixel level in HTML and CSS for a product video (`<one line on what the
video shows>`). You only gather references and measurements; you do not build anything.

## What to capture
1. `<state 1, e.g. month view with one event>`
2. `<state 2>`
3. `<state 3, e.g. confirmation: from the help center or marketing screenshots, never by
   completing a real action>`

## How
- `<access level from above>`. Start from the vendor's own docs or embed examples.
- If a browser is allowed: viewport `<W>x<H>` CSS px at device scale 2; read computed styles
  from the DOM (font family, and the closest free font if it is proprietary; sizes and weights
  per text role; colors as hex; radii, paddings, cell and button sizes, dividers).
- From screenshots only: measure against a known size in the image (a standard icon, a known
  font size), and say so.
- Language: capture `<languages>`. Strings you cannot reach go in a list with the help-center
  URL where you found them, marked verified or not.
- Logos: official SVG or PNG from the vendor's brand or press page only.

## Output
Save under `<scratch>/<vendor>/`: PNG references per state (`en-01-<state>.png`), DOM snapshots
per state if a browser was allowed (scripts removed), and `notes.md` with source URLs, exact
strings per state and language, a measurement table where every value is marked **verified**
(read from a stylesheet or the DOM), **measured** (from pixels) or **inferred**, and a gaps list.

## Rules
- Read-only. Never sign in, sign up, submit, book or send anything.
- Never use anyone's personal browser profile, cookies or saved sessions.
- Time box about 30 minutes; if a state cannot be captured, say what is missing and why.
- Report back concisely: which files exist, the font recommendation, and the gaps.
