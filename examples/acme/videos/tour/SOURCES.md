# Sources: tour

Locked: frontend copy@1318473 (2026-10-07; a folder inside the product, not a git repo: pinned by a hash of its files)
Production: the example's frontend/ folder is the production code by definition (a fictional product with no deploy)

| screen | route | components | citation |
|---|---|---|---|
| Today, four tasks unplanned | / (default route, `#today`) | shell > sidebar + main.page-head + list-meta + ul.task-list > li.task | frontend/index.html:27-42@1318473 |
| Today, planned | / after "Plan my day" | same, rows reordered by `planDay()`, `#plannedChip` shown | frontend/app.js:72-88@1318473 |
| Add task dialog | overlay on / (`#addDialog`) | div.dialog-backdrop > form.dialog > head, fields, foot | frontend/index.html:46-77@1318473 |

## Today, four tasks unplanned
- Strings: `today.title` "Today" (frontend/i18n/en.json:7@1318473), `today.add` "Add task" (frontend/i18n/en.json:10@1318473), `today.plan` "Plan my day" (frontend/i18n/en.json:8@1318473), `today.count` "{count} tasks" (frontend/i18n/en.json:11@1318473), `nav.today` "Today", `nav.upcoming` "Upcoming", `nav.projects` "Projects" (frontend/i18n/en.json:4-6@1318473), `app.name` "Acme Tasks" (frontend/i18n/en.json:2@1318473)
- State: four first-run tasks in insertion order, 11:30 AM, 2:00 PM, 6:00 AM, 4:30 PM (frontend/app.js:7-12@1318473); `planned` starts false, so the chip is hidden (frontend/app.js:17@1318473, frontend/app.js:67@1318473); Today is the active nav item (frontend/index.html:20@1318473)
- Date: `new Date()` formatted "weekday, month day" at runtime (frontend/app.js:131@1318473); the video shows "Tuesday, March 3"
- Icons: sun, calendar, folder (nav), plus, sparkle (buttons), clock (chip), from frontend/icons/ (frontend/index.html:20-38@1318473)
- Flags or gates: none found
- Not found: behaviour for Upcoming and Projects (nav buttons only, no screens) and for the check circle

## Today, planned
- Action: `#planBtn` click runs `planDay()` (frontend/app.js:120@1318473): sort by time (frontend/app.js:75@1318473), `planned = true`, re-render, then each row slides from its old top to its new one over `--acme-duration-plan` 420ms `--acme-ease-out` (frontend/app.js:80-87@1318473, frontend/styles/app.css:78@1318473, frontend/styles/tokens.css:47-48@1318473)
- Strings: `today.planned` "Planned by time" (frontend/i18n/en.json:9@1318473)

## Add task dialog
- Opens on `#addTaskBtn` (frontend/app.js:121@1318473): form reset, backdrop shown, focus in the Task field (frontend/app.js:112-116@1318473); entry animation `dialog-in` 200ms (frontend/styles/app.css:100-102@1318473)
- Strings: `dialog.title` "New task", `dialog.name` "Task", `dialog.name.placeholder` "What needs doing?", `dialog.time` "Time", `dialog.time.placeholder` "e.g. 3:00 PM", `dialog.project` "Project", `dialog.cancel` "Cancel", `dialog.submit` "Add task" (frontend/i18n/en.json:13-20@1318473); project options "No project", Orders, Supplies, Kitchen, Office (frontend/index.html:63-69@1318473)
- Submit: `addTask()` inserts before the first later task once planned (frontend/app.js:90-96@1318473), marks the row `is-new` (`task-in` 200ms, frontend/styles/app.css:85-86@1318473), closes the dialog and shows the toast `toast.added` "Added to Today at {time}" for 2400 ms (frontend/app.js:100@1318473, frontend/i18n/en.json:21@1318473, frontend/app.js:13@1318473)
- Risks: the Project field is a native `<select>` (frontend/index.html:63@1318473): fixed in the video as a styled field (BRIEF notes)

## No-code references
None needed: every screen of this video is in the code.
