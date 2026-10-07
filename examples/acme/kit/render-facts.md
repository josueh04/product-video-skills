# Render facts: Acme Tasks

Measured from frontend@1318473 (a non-git copy, pinned by hash). Every screen spec depends on these.

| fact | value | citation |
|---|---|---|
| root font size at runtime | 16 px (`html { font-size: 16px }`; no script changes it) | frontend/styles/app.css:6@1318473 |
| theme | light only; no theme selector or dark scope exists | frontend/styles/tokens.css:2@1318473 |
| token file and order | `app.css` imports `fonts/fonts.css`, then `tokens.css`; component rules follow | frontend/styles/app.css:2-3@1318473 |
| component library | none: plain HTML, CSS and vanilla JS, no lockfile | frontend/index.html:9@1318473 |
| fonts actually loaded | Inter 400 and 700 via @font-face (woff2 in fonts/); weights 500 and 600 are never used | frontend/fonts/fonts.css:2-15@1318473 |
| desktop breakpoint | the sidebar collapses at 720 px and below; 1440x810 shows the desktop layout | frontend/styles/app.css:132@1318473 |
| icons | 24 px stroke SVGs in icons/, fetched and inlined at runtime into `[data-icon]` | frontend/app.js:42-47@1318473 |
| strings | i18n/en.json, applied at runtime to `[data-i18n]`; the HTML carries the same English text | frontend/app.js:36-40@1318473 |
| dynamic values | the date next to the title is `new Date()` at runtime; the video uses a fixed fictional date | frontend/app.js:131@1318473 |
