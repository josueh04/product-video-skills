# Truth: tour

Locked: frontend copy@1318473. Checked: 2026-10-07.

| id | sentence | source | visibility | verdict | notes |
|---|---|---|---|---|---|
| N1 | Maya runs Northwind Bakery, and her day starts in Acme Tasks. | frontend/index.html:26-27@1318473; frontend/app.js:7-12@1318473 | ui | backed | Today is the default screen; Maya and Northwind Bakery are the fictional cast (product.yaml), the first-run tasks are a bakery's day |
| N2 | One click on Plan my day puts every task in order by time. | frontend/i18n/en.json:8@1318473; frontend/app.js:120@1318473; frontend/app.js:72-76@1318473; frontend/app.js:26-34@1318473 | ui | backed | one click handler, a sort by minutes after midnight; tasks without a time go last (not shown) |
| N3 | Add a task with a time, and it lands in the right slot. | frontend/app.js:90-96@1318473; frontend/i18n/en.json:16@1318473 | ui | backed | true once the day is planned (the video adds after Plan my day); before planning a new task goes to the end |
| N4 | Acme Tasks is the to-do list that plans your day. | frontend/i18n/en.json:3@1318473 | docs | approved | the positioning (product.yaml, CLAIMS.md); the app ships it as its tagline string |
| screen:today | Today with four unplanned tasks, Plan my day and Add task buttons | frontend/index.html:27-42@1318473; frontend/app.js:55-69@1318473 | ui | backed | date fixed to "Tuesday, March 3" (runtime value in the app) |
| screen:today-planned | Rows slide into time order, "Planned by time" chip | frontend/app.js:72-88@1318473; frontend/index.html:38@1318473; frontend/styles/app.css:78@1318473 | ui | backed | slide 420 ms, cubic-bezier(0.2, 0, 0, 1) |
| screen:add-dialog | New task dialog with Task, Time and Project, then the new row and the toast | frontend/index.html:46-77@1318473; frontend/app.js:100@1318473; frontend/i18n/en.json:21@1318473 | ui | backed | the native select is drawn as a styled field (a fix, BRIEF notes) |
| screen:end | End screen cards and lockup | (designed) | mock | mock | designed pieces; the cards reuse the real row and toast markup |

## Open questions
None.
