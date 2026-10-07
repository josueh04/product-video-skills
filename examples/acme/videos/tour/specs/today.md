# Spec: today
Source: frontend@1318473 (see SOURCES.md). Canvas 1440x810, theme light, rem 16. Adapter: html (unproven).

## Geometry
| element | x | y | w | h | citation |
|---|---|---|---|---|---|
| sidebar | 0 | 0 | 232 | 810 | frontend/styles/app.css:20-26@1318473 |
| main content box (after padding) | 296 | 40 | 920 max | auto | frontend/styles/app.css:42-43@1318473 |
| page head | 296 | 40 | 920 | 40 | frontend/styles/app.css:43@1318473, frontend/styles/app.css:50@1318473 |
| list meta | 296 | 104 | 920 | 28 | frontend/styles/app.css:61@1318473 |
| task rows (4) | 296 | 144, 208, 272, 336 | 920 | 56 | frontend/styles/app.css:70-79@1318473 |

## States
S1 unplanned: rows in first-run order (Confirm the cake order with Omar Haddad 11:30 AM Orders; Order flour for Saturday 2:00 PM Supplies; Bake the morning bread 6:00 AM Kitchen; Send the weekly invoices 4:30 PM Office), "4 tasks", chip hidden. HTML in today.html, section S1.
S2 planned: rows in time order (6:00 AM, 11:30 AM, 2:00 PM, 4:30 PM), chip "Planned by time" visible. Same markup, rows translated.
S3 with the new task: "Call the oven repair shop" 1:00 PM, no project, third row; "5 tasks". Toast "Added to Today at 1:00 PM" bottom centre.

## CSS
```css
body { background: #f7f7f5; color: #1c1d1f; font-family: "Inter", system-ui, sans-serif; font-size: 15px; line-height: 22px; } /* frontend/styles/app.css:7-14@1318473 */
.sidebar { width: 232px; background: #ffffff; border-right: 1px solid #e4e4e0; padding: 20px 14px; } /* frontend/styles/app.css:20-26@1318473 */
.brand { display: flex; align-items: center; gap: 10px; height: 36px; padding: 0 8px; margin-bottom: 20px; } /* frontend/styles/app.css:27@1318473 */
.brand img { width: 30px; height: 30px; } /* frontend/styles/app.css:28@1318473 */
.brand-name { font-weight: 700; font-size: 15px; letter-spacing: -0.1px; } /* frontend/styles/app.css:29@1318473 */
.nav-item { height: 38px; padding: 0 10px; gap: 10px; border-radius: 6px; color: #6b6f76; } /* frontend/styles/app.css:31-37@1318473 */
.nav-item.is-active { background: #e9f6f3; color: #0e7c6b; font-weight: 700; } /* frontend/styles/app.css:39@1318473 */
.main { padding: 40px 64px; } /* frontend/styles/app.css:42@1318473 */
.page-head { gap: 16px; margin-bottom: 24px; max-width: 920px; } /* frontend/styles/app.css:43@1318473 */
.page-title { font-size: 30px; line-height: 38px; font-weight: 700; letter-spacing: -0.4px; } /* frontend/styles/app.css:44@1318473 */
.page-date { color: #6b6f76; } /* frontend/styles/app.css:45@1318473 */
.btn { height: 40px; padding: 0 16px; gap: 8px; border-radius: 10px; font-weight: 700; font-size: 15px; } /* frontend/styles/app.css:48-54@1318473 */
.btn-primary { background: #0e7c6b; color: #ffffff; border: 1px solid #0e7c6b; } /* frontend/styles/app.css:55@1318473 */
.btn-primary:hover { background: #0b6a5b; } /* frontend/styles/app.css:56@1318473 */
.btn-secondary { background: #ffffff; border: 1px solid #e4e4e0; } /* frontend/styles/app.css:57@1318473 */
.btn-secondary:hover { border-color: #c9cac4; } /* frontend/styles/app.css:58@1318473 */
.list-meta { height: 28px; gap: 12px; margin-bottom: 12px; color: #6b6f76; font-size: 13px; } /* frontend/styles/app.css:61@1318473 */
.planned-chip { height: 26px; padding: 0 10px; gap: 6px; border-radius: 13px; background: #e9f6f3; color: #0e7c6b; font-weight: 700; } /* frontend/styles/app.css:62-66@1318473 */
.task-list { gap: 8px; max-width: 920px; } /* frontend/styles/app.css:70@1318473 */
.task { height: 56px; padding: 0 18px; gap: 14px; border-radius: 10px; background: #ffffff; border: 1px solid #e4e4e0; box-shadow: 0 1px 2px rgba(28, 29, 31, 0.04); } /* frontend/styles/app.css:71-79@1318473 */
.task-check { width: 20px; height: 20px; border-radius: 50%; border: 2px solid #c9cac4; } /* frontend/styles/app.css:81@1318473 */
.task-project { font-size: 13px; color: #6b6f76; background: #f7f7f5; border-radius: 6px; padding: 2px 8px; } /* frontend/styles/app.css:83@1318473 */
.task-time { width: 84px; text-align: right; color: #6b6f76; font-variant-numeric: tabular-nums; } /* frontend/styles/app.css:84@1318473 */
.toast { bottom: 32px; padding: 12px 18px; border-radius: 10px; background: #1c1d1f; color: #ffffff; box-shadow: 0 12px 30px rgba(28, 29, 31, 0.25); } /* frontend/styles/app.css:123-128@1318473 */
```

## Motion
| what | property | from | to | duration | easing | delay | citation |
|---|---|---|---|---|---|---|---|
| plan: each row to its new slot | translateY | old top minus new top | 0 | 420 ms | cubic-bezier(0.2, 0, 0, 1) | 0 | frontend/app.js:80-87@1318473, frontend/styles/app.css:78@1318473 |
| new row enters | opacity, translateY | 0, 6 px | 1, 0 | 200 ms | cubic-bezier(0.2, 0, 0, 1) | 0 | frontend/styles/app.css:85-86@1318473 |
| button hover | background-color | #0e7c6b | #0b6a5b | 120 ms | cubic-bezier(0.2, 0, 0, 1) | 0 | frontend/styles/app.css:53@1318473 |
| toast | display | hidden | shown, hidden after 2400 ms | instant | none | 0 | frontend/app.js:104-110@1318473 |

## Icons
| key | library | name | file in kit/icons | citation |
|---|---|---|---|---|
| nav Today | acme | sun | acme-sun.svg | frontend/index.html:20@1318473 |
| nav Upcoming | acme | calendar | acme-calendar.svg | frontend/index.html:21@1318473 |
| nav Projects | acme | folder | acme-folder.svg | frontend/index.html:22@1318473 |
| Add task | acme | plus | acme-plus.svg | frontend/index.html:32@1318473 |
| Plan my day | acme | sparkle | acme-sparkle.svg | frontend/index.html:33@1318473 |
| chip | acme | clock | acme-clock.svg | frontend/index.html:38@1318473 |

## Strings
| key | text | citation |
|---|---|---|
| app.name | Acme Tasks | frontend/i18n/en.json:2@1318473 |
| nav.today / nav.upcoming / nav.projects | Today / Upcoming / Projects | frontend/i18n/en.json:4-6@1318473 |
| today.title | Today | frontend/i18n/en.json:7@1318473 |
| today.plan | Plan my day | frontend/i18n/en.json:8@1318473 |
| today.planned | Planned by time | frontend/i18n/en.json:9@1318473 |
| today.add | Add task | frontend/i18n/en.json:10@1318473 |
| today.count | {count} tasks | frontend/i18n/en.json:11@1318473 |
| toast.added | Added to Today at {time} | frontend/i18n/en.json:21@1318473 |

## Fixes (production glitches fixed in the video)
| what | production does | video does | why |
|---|---|---|---|
| none | | | the Today screen has no visible defect |

## Not verified
- Exact text widths (button widths, title baseline): measured at build time by the stage kit, not from a browser render of the app.
