# Feature coverage: Acme Tasks in 20 seconds

What this video must EXPLAIN on screen. "Explain" means the feature is shown working, with
narration that says what it does and why it matters. A name on the end screen is not coverage.

The reviewer reads this matrix and signs it by writing their name into `coverage_signed_by` in
BRIEF.md. Nothing is built before that.

| Feature | Must explain on screen? | Chapter | Proof (what the viewer sees) |
|---|---|---|---|
| Plan my day | yes | 1. Plan your day | Maya's four tasks are out of order; the cursor clicks "Plan my day"; the rows slide into time order (6:00 AM first) and "Planned by time" appears while N2 says it puts every task in order by time |
| Add task with a time | yes | 2. Add anything | The New task dialog opens; "Call the oven repair shop" and "1:00 PM" are typed; after "Add task" the row appears between 11:30 AM and 2:00 PM and the toast says "Added to Today at 1:00 PM" |
| Today list | no | 1. Plan your day | The Today screen is the stage of both chapters: title, date, task count, rows with project and time |

## Configurable parts shown

- The task's time and project in the New task dialog (time typed, project left at "No project").

## Deliberately out of this video

- Upcoming and Projects: in the sidebar only; their screens have no code yet.
- Completing a task: the check circle has no behaviour in the code.
