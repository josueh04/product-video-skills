# Script templates per format

Pick the template that matches `format:` in BRIEF.md. Each gives the structure, the pacing and an
example in the fictional Acme Tasks product. Adapt the words; keep the structure unless the
reviewer asks for another one.

Rules shared by every format:

- One idea per chapter, one change on screen at a time (0.6 to 1 s apart), and a hold of about
  0.8 s at the end of each chapter. A dense piece with a micro-action every half second was
  rejected as overwhelming; the calm, chaptered version of the same content was approved.
- A scene enters about 0.25 s before its line, never 1 to 2 s before: text that appears long
  before the voice says it makes the viewer read ahead and stop listening.
- About five seconds per scene is a good default for a pitch.
- Open on context (what the product is), never in the middle of the UI.

Contents: [Pitch](#pitch) | [Tour](#tour) | [Docs page](#docs-page) | [Tutorial](#tutorial) | [Silent loop](#silent-loop)

## Pitch

For investors, a landing page or a sales deck. 45 to 120 seconds. The viewer has never used the
product and will not pause the video.

| Part | What it does | Lines |
|---|---|---|
| Opening | Product name over the UI out of focus; the first sentence says what it is and for whom | 1 or 2 |
| Chapters (3 to 6) | Two-tone title, one idea, the UI doing it, the narration explaining each step | 2 to 5 each |
| End screen | Breadth: what else the product does, built from real pieces of the UI (not only a logo) | 1 or 2 |
| Lockup | Logo, product name and tagline; the last line is a complete sentence, read slower | 1 |

```
id	role	speed	text
N1	narrator	0.96	This is Acme Tasks, the to-do list that plans your day.
N2	narrator	1.0	Maya runs Northwind Bakery, and every morning starts with a list.
# Chapter 1: Plan the day
N3	narrator	1.0	She types what has to happen today, in her own words.
N4	narrator	1.0	Acme Tasks reads each task and gives it a slot, around her deliveries.
# Chapter 2: When plans change
N5	narrator	1.0	At ten a.m. a customer moves a pickup to the afternoon.
N6	narrator	1.0	Maya drags it, and the rest of the day moves with it.
# End screen
N7	narrator	1.0	It also shares lists with the team, sends reminders and keeps a weekly review.
N8	narrator	0.92	Acme Tasks is the to-do list that plans your day.
```

Explain the features COVERAGE.md marks "must explain": N4 says what the planner does, not just
that it exists. A wait in the product (the planner thinking) is a short silent moment in the
moment table, not a line.

## Tour

A pitch cut down to one or two features, for a landing page hero, a social post with sound or a
first look. 15 to 45 seconds. Same parts as the pitch, fewer and shorter: there is no time to
set up a story, so the opening names the product and its user in one line.

| Part | What it does | Lines |
|---|---|---|
| Opening | Product name over the UI out of focus, who uses it | 1 |
| Chapters (1 or 2) | Two-tone title, one feature shown working | 1 each |
| End screen and lockup | Real UI pieces of what was shown, then the positioning as the last line | 1 |

```
id	role	speed	text
N1	narrator	0.95	Maya runs Northwind Bakery, and her day starts in Acme Tasks.
# Chapter 1: Plan your day
N2	narrator	1.0	One click on Plan my day puts every task in order by time.
# Chapter 2: Add anything
N3	narrator	1.0	Add a task with a time, and it lands in the right slot.
# End screen
N4	narrator	0.95	Acme Tasks is the to-do list that plans your day.
```

This is the example video in `examples/acme/videos/tour/`. With one line per chapter, each line
must name the action and its result; a chapter whose line only names the feature shows it
without explaining it.

## Docs page

Embedded next to a docs article that already explains the details. 20 to 60 seconds, one feature,
often watched muted: captions or on-screen labels must carry the meaning without sound.

| Part | What it does | Lines |
|---|---|---|
| Context | Where in the product we are (one sentence, the real menu path) | 1 |
| Steps | One step per line, naming the exact UI label the cursor touches | 3 to 6 |
| Result | What the user now has | 1 |

```
id	role	speed	text
N1	narrator	1.0	Recurring tasks live in the task panel, under Repeat.
N2	narrator	1.0	Open a task and choose Repeat.
N3	narrator	1.0	Pick Weekly, then the days it should come back.
N4	narrator	1.0	Save, and the task returns every Monday and Thursday.
```

No opening title card and no lockup: the page around the video already says what it is. Use the
real labels in the exact case of the UI ("Repeat", "Weekly", "Save").

## Tutorial

A longer walkthrough a user follows along with. 2 to 6 minutes, chaptered so a viewer can jump.
Second person ("you"), slower speed (0.95), and pauses where the viewer will be clicking along.

| Part | What it does | Lines |
|---|---|---|
| Goal | What you will have at the end, and what you need before starting | 2 |
| Chapters | One task each: title, steps, a check that it worked | 3 to 8 each |
| Recap | The steps in one sentence each, and where to go next | 2 to 4 |

```
id	role	speed	text
N1	narrator	0.95	By the end of this video, your team will share one list for the week.
N2	narrator	0.95	You need an Acme Tasks workspace and the email of each teammate.
# Chapter 1: Create the shared list
N3	narrator	0.95	Choose New list, and name it Northwind weekly.
N4	narrator	0.95	Under Sharing, choose Team, and add your teammates by email.
N5	narrator	0.95	Each of them now sees the list in their sidebar.
```

Give every check its own line ("Each of them now sees..."): it is the moment a viewer who is
following along confirms they are in the right place.

## Silent loop

A short muted loop for a landing page or a social post: 6 to 30 seconds, no narration, seamless
end-to-start. There is no voice clock, so the moment table carries explicit durations, and the
composer reads them from the BRIEF instead of from timings.json.

| Moment | On screen | Duration | Sound |
|---|---|---|---|
| Hook | One promise as large text over the product | 1.5 s | none |
| Action 1 | A real piece of UI doing one thing | 2.0 s | click |
| Action 2 | The next thing, same framing | 2.0 s | typing |
| Payoff | The result, held | 1.5 s | pop |
| Return | Back to the first frame | 0.5 s | none |

- No admin chrome: use real UI pieces, large, without the app frame around them. A loop that
  jumped between admin screens felt chaotic in review.
- SFX are optional and only matter if the loop is ever played with sound; keep them as library
  clicks, pops and typing, never whooshes.
- Leave `audio/lines.tsv` with only its header; `tts.py` then has nothing to voice.
