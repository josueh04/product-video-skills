# End screen and lockup

The ending has two parts: an end screen with breadth (what else the product does, shown with
real UI pieces), then the lockup (logo, tagline, one line, the URL) and a fade to black. A
reviewer's first note on an ending that was only a logo was that it lacked breadth.

## End screen

```html
<div id="endS">
  <div class="pvs-end-bg"></div>
  <div class="pvs-end-content">
    <div class="pvs-eHead" id="eHead"><div class="pvs-mask"><div class="pvs-ln">One list, <em>planned for you.</em></div></div></div>
    <div class="pvs-cards">
      <div class="pvs-card" id="card1">
        <div class="pvs-card-h">Plans your day</div><div class="pvs-card-s">From what is due</div>
        <div class="pvs-card-ui">{{UI:task-row}}</div>
      </div>
      ...
    </div>
  </div>
</div>
```
```python
T["endIn"] = end("N7") + 0.8
T["N8"] = T["endIn"] + 0.45
T["card1"] = T["N8"] + w("N8", "plans") - 0.2      # each card on the word that names it
T["card2"] = T["N8"] + w("N8", "reminds") - 0.2
```
```js
S.cursorHide(T.endIn - 0.4);
S.endScreen(T.endIn, { head: ["#eHead", S.w("N8", "one") - 0.15], cards: [["#card1", T.card1], ["#card2", T.card2]] });
```

- Each card names one capability and carries a real piece of the product UI (rows, an option
  list, a small panel), scaled 1.1x to 1.3x with `.pvs-card-ui { transform: scale(1.2) }` (CSS,
  never tweened). Pieces come from `kit/ui/` so they match the screens exactly.
- The capabilities come from COVERAGE.md and the docs, never from memory. A capability that
  is only listed here is not "explained": the coverage matrix needs a chapter for that.
- Headline and cards form one centred column, so 1 to 4 cards stay balanced. Measure before
  adding rows: a fixed-size card with `overflow: hidden` cut its rows once.
- The cards enter staggered with a soft rise (`opacity, y, scale` in both from and to vars).

## Lockup

```html
<div id="lock">
  <img class="pvs-lkLogo" src="{{LOGO_ON_VEIL}}#lockup" alt="">
  <div class="pvs-lkT">{{PRODUCT_NAME}}</div>
  <div class="pvs-lkS">The to-do list that plans your day.</div>
  <div class="pvs-lkU">acme.example</div>
</div>
```
```python
T["lockup"] = end("N8") + 0.9
T["N9"] = T["lockup"] + 0.5                        # the closing line, if there is one
T["end"] = end("N9") + 1.4
T["DUR"] = round(T["end"] + 0.8, 2)
```
```js
S.lockup(T.lockup, { title: T.N9 - 0.05, sub: S.w("N9", "plans") - 0.1, url: T.N9 + 1.6 });
S.fadeToBlack(T.end);
```

- `S.lockup` fades only the end screen content; its background stays until the lockup is up.
  Fading the whole end screen showed one sharp frame of the product between the two (0.04 s,
  caught only in a 6 fps strip).
- The tagline is the positioning from CLAIMS.md, said in full. A fragment of it in the closing
  voice line sounded cut off and was replaced by the complete phrase.
- The `#lockup` fragment on the logo src gives the second use of the same file a distinct src,
  which keeps `check` from warning `duplicate_media_discovery_risk`.
- Propose the tagline and the closing line for veto in your report; do not invent claims.

## Checks before render

Snapshot `T.endIn + 1.4` and `T.lockup + 1.4`, and extract a 5 to 6 fps strip across
`T.lockup - 0.3` to `T.lockup + 1.0` from the draft render to confirm no product frame flashes
through.
