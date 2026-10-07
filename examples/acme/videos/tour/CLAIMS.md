# Positioning and claims: Acme Tasks in 20 seconds

The reviewer reads this sheet and signs it by writing their name into `claims_signed_by` in
BRIEF.md. No narration is recorded before that.

## Positioning

Acme Tasks is the to-do list that plans your day. (product.yaml `product.positioning`; the app's
own tagline, frontend/i18n/en.json:3@1318473)

## Phrases to avoid

| Phrase | Why |
|---|---|
| the last app you will ever need | product.yaml never_say: an overclaim the team rejected |
| Planzo | product.yaml banned_terms: a competitor, never seen or heard |
| AcmeTodo, Acme To-Do | product.yaml names: legacy names, the canonical name is Acme Tasks |
| automatically, AI | the plan is a sort by time triggered by a click, not automatic or AI |

## Claims that need approval

| Claim | Source | Answer |
|---|---|---|
| "One click on Plan my day puts every task in order by time." | frontend/app.js:72-76@1318473 (planDay sorts by time) | yes: true, tasks without a time go last, which the video does not show |
| "it lands in the right slot" (a new task is placed by its time) | frontend/app.js:90-96@1318473 (insert at the first later task once planned) | yes, only after Plan my day; the video adds the task after planning |

## Approved taglines

| Tagline | Use |
|---|---|
| One list, planned for you. | end screen headline |
| The to-do list that plans your day. | lockup, and the closing line N4 in full |

## Product names

| Say | Never say (legacy or wrong) |
|---|---|
| Acme Tasks | AcmeTodo, Acme To-Do |
| Plan my day (the button label) | auto plan, planner |
