# Framing and pacing

The rules, the numbers, and the review notes they came from.

## Framing

| Situation | Framing |
|---|---|
| Settings, forms, tables, any full page | 1x, full page, the whole video if it can |
| Pop-ups, dialogs, drawers | At natural size and centred, as the app shows them, at 1x |
| One section deserves attention | One gentle push-in, at most `video.max_zoom` (1.35 by default), whole section in frame |
| A canvas shown far out (for example at 50 %), a narrow chat column | More zoom is tolerable: raise `max_zoom` in product.yaml for that product |
| End screen and lockup | Camera back to 1x behind the blur |

- Never put a frame edge through a label, a field title or an icon. Snapshot every setup beat
  and look at the edges.
- One framing per chapter. The camera moves between chapters (behind the title) or in one slow
  signature move, not back and forth.
- `b.cam()` and `S.cam()` clamp above `max_zoom` and below 1x and warn; `cam()` also clamps
  the position so the stage never shows outside the canvas.

Where the numbers come from. In the production these skills come from, a settings video was
sent back twice for zoom: a 1.67x punch-in cut labels and sliders in half ("I can't tell what
is happening"), and framings of about 2x per column were "super zoomed in at the start" even
with nothing cut. The reviewer's model was a video that stayed at 1x the whole time: "it is not
zoomed in and you understand what is happening". A canvas video with push-ins of 1.12x to 1.3x
(and up to 1.9x on a canvas shown at 50 %) and a chat video at 1.05x to 1.5x on a narrow column
were approved.

## Pacing

| Rule | Number |
|---|---|
| Chapter title holds | at least about 1.4 s; 1.1 to 1.5 s alone before the narration resumes |
| Gap between changes | 0.6 to 1 s, one change at a time |
| Hold at the end of a chapter | about 0.8 s |
| A UI event before the word that names it | 0.05 to 0.45 s |
| Real waits of the product | compressed to 1 or 2 s |
| Typing | 17 to 21 characters per second |
| Rack focus | in 0.6 s (`power2.out`), out 0.8 s (`power2.inOut`), blur 14 px with the veil |

- Open on context, never in the middle of the UI.
- The narration explains each step to someone who has never seen the product: who it is for,
  what is asked, what each step does.
- A longer video that reads calmly beats a short dense one.

Where the numbers come from. A dense one-take hero with a micro-action every 0.5 s and many
reframes was "too fast, too much at once, overwhelming", opened mid-editor with no context, and
its zooming in and out made the results impossible to follow. The rebuild in chapters (titles
as pauses, one idea each, one framing each) was approved and became the rule for every piece.

## Motion quality

The narrated demos needed no springs or motion blur: GSAP eases, the product's exact CSS curves
(`PVS.bez`) and the calm rhythm were enough. For landing-page loops with no narration the bar is
higher (closed-form springs, real motion blur by rendering at 240 fps and blending subframes,
transitions as shape morphs or camera moves rather than fades); see the hyperframes-animation
and hyperframes-keyframes skills when a brief asks for that.
