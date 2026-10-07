# Spec: add-dialog
Source: frontend@1318473 (see SOURCES.md). Canvas 1440x810, theme light, rem 16. Adapter: html (unproven).

## Geometry
| element | x | y | w | h | citation |
|---|---|---|---|---|---|
| backdrop | 0 | 0 | 1440 | 810 | frontend/styles/app.css:89-93@1318473 |
| dialog, centred by grid place-items | 480 | about 244 | 480 | about 322 | frontend/styles/app.css:91@1318473, frontend/styles/app.css:95-101@1318473 |
| Time field | dialog x + 24 | | 160 | 44 + label | frontend/styles/app.css:108@1318473 |
| Project field | after Time + 12 | | rest of the row | 44 + label | frontend/styles/app.css:107-109@1318473 |

## States
S1 open, empty: placeholders "What needs doing?" and "e.g. 3:00 PM", Project "No project", focus in Task. HTML in add-dialog.html.
S2 typed: Task "Call the oven repair shop", Time "1:00 PM" (typed in that order), Project unchanged.
S3 closed after "Add task": the backdrop hides at once (no exit animation in the code).

## CSS
```css
.dialog-backdrop { position: fixed; inset: 0; display: grid; place-items: center; background: rgba(28, 29, 31, 0.36); } /* frontend/styles/app.css:89-93@1318473 */
.dialog { width: 480px; padding: 24px; border-radius: 16px; background: #ffffff; box-shadow: 0 24px 60px rgba(28, 29, 31, 0.22); } /* frontend/styles/app.css:95-101@1318473 */
.dialog-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; } /* frontend/styles/app.css:103@1318473 */
.dialog-title { font-size: 18px; line-height: 26px; font-weight: 700; } /* frontend/styles/app.css:104@1318473 */
.icon-btn { width: 32px; height: 32px; border-radius: 6px; color: #6b6f76; } /* frontend/styles/app.css:105@1318473 */
.field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; } /* frontend/styles/app.css:106@1318473 */
.field-row { display: flex; gap: 12px; } /* frontend/styles/app.css:107@1318473 */
.field-label { font-size: 13px; font-weight: 700; color: #6b6f76; } /* frontend/styles/app.css:110@1318473 */
.input { height: 44px; padding: 0 14px; border-radius: 10px; border: 1px solid #e4e4e0; background: #ffffff; color: #1c1d1f; } /* frontend/styles/app.css:111-117@1318473 */
.input::placeholder { color: #6b6f76; } /* frontend/styles/app.css:118@1318473 */
.input:focus { border-color: #0e7c6b; box-shadow: 0 0 0 3px rgba(14, 124, 107, 0.18); } /* frontend/styles/app.css:119@1318473, via --acme-color-focus (frontend/styles/tokens.css:16@1318473) */
.dialog-foot { display: flex; justify-content: flex-end; gap: 8px; margin-top: 8px; } /* frontend/styles/app.css:120@1318473 */
.btn-ghost { background: transparent; border: 1px solid transparent; color: #6b6f76; } /* frontend/styles/app.css:59@1318473 */
```

## Motion
| what | property | from | to | duration | easing | delay | citation |
|---|---|---|---|---|---|---|---|
| dialog enters | opacity, translateY, scale | 0, 8 px, 0.97 | 1, 0, 1 | 200 ms | cubic-bezier(0.2, 0, 0, 1) | 0 | frontend/styles/app.css:100-102@1318473 |
| backdrop | display | hidden | shown | instant | none | 0 | frontend/app.js:114@1318473 |
| close | display | shown | hidden | instant | none | 0 | frontend/app.js:117@1318473 |
| focus ring on the focused input | border-color, box-shadow | | | instant | none | 0 | frontend/styles/app.css:119@1318473 |

## Icons
| key | library | name | file in kit/icons | citation |
|---|---|---|---|---|
| close | acme | x | acme-x.svg | frontend/index.html:50@1318473 |

## Strings
| key | text | citation |
|---|---|---|
| dialog.title | New task | frontend/i18n/en.json:13@1318473 |
| dialog.name | Task | frontend/i18n/en.json:14@1318473 |
| dialog.name.placeholder | What needs doing? | frontend/i18n/en.json:15@1318473 |
| dialog.time | Time | frontend/i18n/en.json:16@1318473 |
| dialog.time.placeholder | e.g. 3:00 PM | frontend/i18n/en.json:17@1318473 |
| dialog.project | Project | frontend/i18n/en.json:18@1318473 |
| (option) | No project | frontend/index.html:64@1318473 |
| dialog.cancel | Cancel | frontend/i18n/en.json:19@1318473 |
| dialog.submit | Add task | frontend/i18n/en.json:20@1318473 |

## Fixes (production glitches fixed in the video)
| what | production does | video does | why |
|---|---|---|---|
| Project field | a native `<select class="input">` (platform arrow and padding) | a styled field with the same .input box and a drawn chevron | a native control renders as a grey platform widget, not the product's design |

## Not verified
- The dialog's rendered height (about 322 px) is computed from the CSS, not measured in a browser; the stage centres it by measurement.
