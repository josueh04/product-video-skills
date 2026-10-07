# Beat recipes

One recipe per kind of beat: the build.py lines that time it, the template lines that animate
it, and the detail that went wrong without it. Times use the example lines
`N1 "Every morning, your plan for the day is ready before you open the app."` and
`N2 "Type a task, and it lands in the right slot."`.

Contents: opening, chapter, hover and click, typing, agent reply (streaming), pop-up, dropdown
or popover, toast, scroll, push-in, waits, two cursors, live counters.

## Opening

```python
T["open"] = 0.35
T["ch1"] = 2.3                                  # or end of an opening line + 0.15
```
```js
S.fadeFromBlack(0.1);
S.title("#tOpen", [T.open, T.open + 0.15, T.open + 0.6], T.ch1 - 0.05);   // logo, name, line
```
Open on context: who it is for and what it is, over the product out of focus. An opening in the
middle of an editor, with no context, was rejected. The subtitle line may land on a word of the
first narration line (`T.N1 + w("N1", "everything") - 0.45`).

## Chapter

```python
T["ch2"] = T["close1"] + 0.8                    # hold ~0.8 s after the last change
T["rack2"] = max(T["N2"] + w("N2", "type") - 0.5, T["ch2"] + 1.4)
```
```js
S.chapter("#tCh2", { at: T.ch2, rack: T.rack2 });          // blurred: true after the opening
```
The title enters 0.25 s after the cue and leaves 0.1 s before focus returns. Change screens,
open panels and move the camera between `T.ch2 + 0.6` and `T.rack2`, while the product is out
of focus: one shot, no hard cuts. A title that holds alone and then the narration starting as
focus returns (`T.N2 = T.rack2 - 0.1`) reads as a pause; titles under 1 s read as flicker.

## Hover and click

```python
T["open1"] = T["N1"] + w("N1", "ready") - 0.1
b.click(T["open1"])
```
```js
S.cursorShow(T.rack1 + 0.4);
S.clickOn("#row2", T.open1, { hover: "hov", unhover: T.close1 + 0.3 });
```
The cursor appears after the first rack and leaves before the end screen. Rest it on what the
narration names. The hover class goes on about 0.12 s before the click; a click with no hover
reads as a teleport. Keep one cursor move at a time: a reset that landed inside the next move
left the pointer in the wrong place after a seek (the kit warns).

## Typing

```python
TEXTS = {"t1": "Call the supplier at 3 pm"}     # fictional, listed in BRIEF notes for veto
T["inClick"] = T["N2"] + w("N2", "type") - 0.05
T["type1"] = T["inClick"] + 0.25
T["type1Dur"] = round(len(TEXTS["t1"]) / 17.0, 3)
b.dur("type1", T["type1Dur"])
b.typing(TEXTS["t1"], T["type1"], dur=T["type1Dur"])
```
```js
S.state("#addRow", "foc", T.inClick);
S.hide("#addPh", T.type1);
S.type("#addIn", T.texts.t1, T.type1, T.type1Dur);
```
Speed is 17 to 21 characters per second for prose, one keystroke per character for a short
search. The sound is real recorded keystrokes laid on the same beat; synthesized typing sounded
"like a straw, not a keyboard" and was rejected.

## Agent reply (streaming)

```js
S.fadeIn("#thinking", T.send1 + 0.2);                     // "Thinking..." with the product's label
S.hide("#thinking", T.msg1);
S.show("#reply1", T.msg1);
S.stream("#reply1 .text", T.msg1, 1.6);
```
Labels such as "Thinking..." or "Calling <tool>" come from the code that builds them, not from
memory. Real waits compress to 1 or 2 s.

## Pop-up

```js
S.popupOpen("#pop1", T.open1);
S.clickOn("#dlgClose", T.close1, { travel: 0.5 });
S.popupClose("#pop1", T.close1);
```
At 1x and centred at natural size, as the app shows it. Replace the defaults (`scale .7`,
`y 30`, `0.3 s` in, `0.2 s` out, backdrop off at 300 ms) with the product's own keyframes from
the spec. If a menu is open, hide it one frame before the modal opens.

## Dropdown or popover

Open below the trigger, above when it does not fit in the app viewport (`app_canvas.logical`
height), with the library's gutter (for example 2 px for a select, 10 px for a popover) and its
entry (for example `scaleY .8 to 1` in 0.12 s). Measure the trigger with `S.box()`, place the
panel with `S.set(panel, {x, y}, 0)`, and animate with a `fromTo` that repeats every from key
in its to vars.

## Toast

```js
S.toast("#toast1", T.add + 0.1, 1.8);
```
Use the product's real toast texts and position (`.pvs-toast-slot` bottom centre, or
`.top-right`). A toast that covers the next button the cursor needs is a layout bug: move it or
shorten `hold`.

## Scroll

```js
const to = S.scrollTarget("#row12", "#listIn", 24);
S.scroll("#listIn", 0, to, T.scroll1, 0.9);
```
The inner column moves inside a `.pvs-scroll` viewport. Stay within the real range (one video
framed 177 px past the end of a list) and pick stops where no line or icon is cut at an edge.

## Push-in

```python
b.cam(T["ch2"] + 0.6, 1.2, "#addRow", d=0.4, label="behind the title")     # one framing for the chapter
b.cam(T["endIn"] + 0.3, 1.0, d=0.8, label="back to 1x behind the end screen")
```
```js
S.camPlan();
```
Up to `video.max_zoom`. Make it while the product is out of focus, or as one slow signature
move (for example 1.28x over 2.6 s on a line that asks the viewer to read). Never zoom in and
out within a chapter: the results of one video became impossible to follow that way.

## Waits

Real product waits (a run, a call connecting, a sync) compress to 1 or 2 s. Leave air where the
story needs it: about 3 s between "call me" and the phone ringing read as real.

## Two cursors

When a product has its own agent cursor next to the user's, give each a distinct look and its
own rhythm (for example the agent's: a 0.45 s settle, 0.42 s travel per target, one target
every 1.02 s with a small pop), and never move both at once.

## Live counters

A call timer or a progress number is computed from the timeline time inside an `onUpdate` on
`S.tl` (`S.tl.eventCallback("onUpdate", () => { el.textContent = fmt(S.tl.time() - T.call0); })`),
never from `Date` or timers. Waveform bars and jitter use `S.rng(seed)`.
