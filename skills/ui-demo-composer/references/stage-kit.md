# Stage kit reference

The API of `scripts/buildlib.py` (Python, build time) and `kit/stage.js` (JavaScript, the
timeline), the template placeholders and the CSS variables.

Contents: 1. Template skeleton. 2. Placeholders. 3. CSS variables. 4. buildlib API.
5. stage.js API. 6. Audio tracks.

## 1. Template skeleton

```html
<head>
  {{GSAP}}
  <style>{{FONTS_CSS}} {{STAGE_CSS}} {{STAGE_VARS}} {{TITLES_CSS}} {{TOKENS_CSS}} {{UI_CSS}} {{APP_CSS}}</style>
</head>
<body>
  <div id="root" data-composition-id="main" data-start="0" data-duration="{{DUR}}" data-fps="{{FPS}}" data-width="1920" data-height="1080">
    <div id="stage">
      <div id="camera"><div id="blurWrap"><div id="app">
        ... the product UI ...
        <div class="pvs-modal" id="pop1"><div class="pvs-backdrop"></div><div class="pvs-box">...dialog...</div></div>
        <div class="pvs-toast-slot"><div class="pvs-toast" id="toast1">...</div></div>
        <div class="pvs-rip" id="pvsRip"></div>
        <div class="pvs-cur" id="pvsCur"></div>          <!-- last child: on top of everything -->
      </div></div></div>
      <div id="veil"></div>
      <div class="pvs-ttl" id="tCh1"><div class="pvs-mask"><div class="pvs-ln pvs-chT">Plan <em>your day.</em></div></div></div>
      <div id="endS"><div class="pvs-end-bg"></div><div class="pvs-end-content">...</div></div>
      <div id="lock">...</div>
      <div id="fade"></div>
    </div>
    {{AUDIO}}
  </div>
  <script>
    const T = (window.PVS_T = {{T_JSON}});
    {{STAGE_JS}}
    PVS.ready((S) => { /* the timeline */ });
  </script>
</body>
```

Keep the order of the style placeholders: the kit defaults, then the product tokens (which may
override any `--pvs-*`), then shared UI pieces, then this video's CSS. The template is `.tpl`,
not `.html`, so HyperFrames never sees two root compositions in the folder (a second HTML file
once made `check` fail with `multiple_root_compositions` and could have doubled the audio).

## 2. Placeholders

Replaced by `Build.write()`. Any `{{UPPER_CASE}}` left over fails the build.

| Placeholder | Becomes |
|---|---|
| `{{GSAP}}` | The GSAP 3.14.2 script tag |
| `{{FONTS_CSS}}` | `kit/fonts/fonts.css` of the product, urls rewritten to `assets/fonts/` (files copied) |
| `{{STAGE_CSS}}`, `{{TITLES_CSS}}` | `kit/stage.css`, `kit/titles.css` of this skill |
| `{{STAGE_VARS}}` | `:root` with `--pvs-app-*` from `app_canvas`, `--pvs-accent`, `--pvs-font`, theme colours |
| `{{TOKENS_CSS}}` | `kit/tokens.css` of the product |
| `{{UI_CSS}}` | Every `*.css` in the product's `kit/ui/`, then the video's `src/ui/` |
| `{{APP_CSS}}` | `video/src/app.css` |
| `{{STAGE_JS}}` | `window.PVS_STAGE = {W,H,K,X,Y,maxZoom,theme}` plus `kit/stage.js` |
| `{{T_JSON}}` | The beat table, plus `T.W` (words per clip), `T.texts`, `T.CAM` |
| `{{ICONS_JSON}}` | `{name: svg}` from the product's `kit/icons/` and `src/icons/` (optional) |
| `{{AUDIO}}` | The `<audio>` tags for narration and sound effects |
| `{{DUR}}`, `{{FPS}}` | `T["DUR"]`, `video.fps` |
| `{{PRODUCT_NAME}}`, `{{POSITIONING}}` | From product.yaml, HTML-escaped |
| `{{LOGO_LIGHT}}`, `{{LOGO_DARK}}`, `{{APP_TILE}}` | The brand files, copied to `assets/` |
| `{{LOGO_ON_VEIL}}` | The logo variant readable on the veil: `brand.logo_light` (made for light backgrounds) on a light theme, `brand.logo_dark` on a dark theme |
| `{{TEXT_<KEY>}}` | `texts[key]` passed to `write()`, HTML-escaped (`{{TEXT_T1}}`) |
| `{{UI:name}}` | `src/ui/name.html` of the video, else `kit/ui/name.html` of the product (nests) |
| `<i data-icon="name"></i>` | That icon's SVG inline (`class="pvs-ic"`); a missing icon fails a signed build |

Pick logo variants by background: a light mini logo disappears on a white page; use the dark
logo or the app tile there.

## 3. CSS variables

Set in `stage.css`, overridden by `{{STAGE_VARS}}` from product.yaml, then by `tokens.css`.

| Variable | Default (dark / light theme) | Used by |
|---|---|---|
| `--pvs-accent` | `brand.accent` | Second tone of titles, lockup tagline |
| `--pvs-font` | `brand.font` | Titles, end screen, lockup |
| `--pvs-bg` | `#000` / `#fff` | Behind the app |
| `--pvs-veil` | `rgba(8,8,9,.62)` / `rgba(246,247,249,.72)` | The veil that travels with the blur |
| `--pvs-blur` | `14px` | Rack focus |
| `--pvs-title`, `--pvs-sub`, `--pvs-muted` | Light on dark / dark on light | Title colours |
| `--pvs-backdrop` | `rgba(63,63,63,.7)` | Pop-up backdrop (use the product's real one) |
| `--pvs-end-bg`, `--pvs-card-bg`, `--pvs-card-border` | | End screen |
| `--pvs-cursor-fill`, `--pvs-cursor-stroke`, `--pvs-ripple` | white arrow, dark outline | Cursor |
| `--pvs-app-w/h/k/x/y` | from `app_canvas.logical` | `#app` size, scale and letterbox offset |

## 4. buildlib API (`b = buildlib.Build(__file__)`)

| Call | Does |
|---|---|
| `Build(__file__, argv=None)` | Parses `--draft`, `--fake-timings`, `--quiet`; enforces the signature gate (exit 2); loads product.yaml, BRIEF.md, `audio/timings.json`, `lines.tsv` roles |
| `b.T` | The beat table. A key that is a clip id of timings.json places that clip (its `<audio>` is written) |
| `b.w(clip, prefix, nth=1)` | Start of the nth word starting with `prefix` (case-insensitive, punctuation stripped), relative to the clip. Raises `BuildError` listing the words when missing |
| `b.we(clip, prefix, nth=1)` | End of that word |
| `b.lw(clip)` | End of the last spoken word (clips carry a silent tail) |
| `b.at(clip, prefix, nth=1)` | Absolute time: `T[clip] + w(...)` |
| `b.end(key)` | `T[key]` plus the clip duration, or the duration set with `b.dur(key, d)` |
| `b.dur(key, d)` | Gives a non-clip beat (a typing run, a build animation) a duration |
| `b.click(t, vol=.35)`, `b.pop(t, vol=.18)`, `b.sfx(name, t, vol, track)` | Library sound effects via script-and-voice `make_sfx.library_sfx` |
| `b.typing(text, t, dur=None, cps=14, vol=.45)` | A typing track of real keystrokes (`make_sfx.typing_track`) |
| `b.cue(cue, vol, track)` | Any cue dict `{id, src, start, dur}` with `src` relative to the video dir |
| `b.cam(t, scale, at=None, d=.9, ease, label)` | Records a camera move into `T.CAM` (`at`: selector or `[x, y]` app px). Clamps above `video.max_zoom` and below 1x, warns on overlapping moves |
| `b.snap(t, label)` | A setup beat; the build prints one `snapshot --at ...` command for all of them |
| `b.write(texts=None, values=None)` | Checks (DUR set, no clip past DUR, no clip before 0, unplaced clips, narration overlaps), writes `index.html`, copies audio and assets into `video/`, prints the beat table, warnings, the snapshot and render commands |
| `buildlib.main_guard(fn)` | Runs `fn`, turns a `BuildError` into `build failed: ...` and exit 1 |
| `buildlib.svg_clean(svg)` | Inline-ready SVG: no XML header, ids, comments or size; `fill="currentColor"` |

In a draft, problems that would block delivery (a missing clip WAV, a missing icon, no
make_sfx) are warnings; in a signed build they fail. `--fake-timings` needs `--draft` and
stamps `<meta name="pvs-fake-timings">`.

## 5. stage.js API (`PVS.ready((S) => {...}, opts)`)

`PVS.ready` waits for `document.fonts.ready` (positions depend on text metrics), builds one
paused timeline, calls your function, then registers `window.__timelines["main"]` at the end
(registering before the build finishes renders a blank video). Options: `{T, id: "main",
startBlack: true, startFocused: false, auditApp: false}`.

| Helper | Does |
|---|---|
| `S.tl`, `S.T`, `S.cfg` | The timeline, the beat table, the stage numbers (`W,H,K,X,Y,maxZoom`) |
| `S.box(sel)` | `{x,y,w,h,cx,cy}` in app px, measured through offsets (shows hidden ancestors for the measurement) |
| `S.w(clip, word)` | Absolute time of a word from `T.W` (prefer computing beats in build.py) |
| `S.init(sel, vars)` | `gsap.set` plus `tl.set` at 0, so seeking back to 0 restores the first frame |
| `S.set(sel, vars, t)`, `S.show(sel, t, display)`, `S.hide(sel, t)` | Zero-length state changes (display is never tweened) |
| `S.state(sel, cls, t)`, `S.hover(sel, t)` | Authored classes plus `cls` (`hov`, `foc`, `sel`, `dis`); `null` restores |
| `S.fadeIn(sel, t, d=.25, y=0)`, `S.fadeOut(sel, t, d=.2)` | Seek-safe fades |
| `S.cam(t, s, at, d=.9, ease)`, `S.camReset(t, d)`, `S.camPlan()` | Camera: centre app point `at` at scale `s`, clamped to the stage edges and to `maxZoom`. `camPlan()` applies `T.CAM` from build.py |
| `S.rack(t, on, d=.6)` | Blur and veil in or out together |
| `S.lineIn(sel, t, d=.75)`, `S.lineOut(sel, t, d=.45)` | A title line through its mask (`expo.out` in, `power3.in` out) |
| `S.title(sel, tIn, tOut, {stagger})` | Every `.pvs-ln` of a title block; `tIn` may be one time per line |
| `S.chapter(sel, {at, rack, blurred})` | Rack in at `at`, title in at `at + .25`, out at `rack - .1`, focus back at `rack` |
| `S.cursorShow(t)`, `S.cursorHide(t)`, `S.cursorAt(x, y, t)` | Cursor visibility and position |
| `S.move(x, y, t, d=.6)`, `S.moveTo(sel, t, d, {dx, dy, ax, ay})` | Travel with `power2.inOut`; warns when a move starts before the last one ends |
| `S.click(x, y, t)` | Press (scale .86 in .07 s, release .16 s) and ripple (.3 to 1.5 over .45 s) |
| `S.clickOn(sel, t, {travel=.6, hover, unhover, dx, dy})` | Arrive .15 s before `t`, hover at `t - .12`, click at `t` |
| `S.type(sel, text, t, d)` | One span per character, evenly over `d` |
| `S.stream(sel, t, d)` | The element's words appear one by one over `d` |
| `S.blink(sel, t0, t1, period=.53)` | A caret blink as alternating sets |
| `S.popupOpen(sel, t, {scale=.7, y=30, d=.3, delay=.06})` | Backdrop at once, box in at `t + delay` |
| `S.popupClose(sel, t, {d=.2, backdropAt=.3})` | Box out, backdrop off at `t + .3`, hidden after |
| `S.toast(sel, t, hold, {y=18})` | In over .2 s, out after `hold` |
| `S.scroll(sel, from, to, t, d=.8)` | Inner column `fromTo` within the real range (clamps and warns past the end) |
| `S.scrollTarget(sel, inner, pad)` | The offset that brings `sel` to `pad` px below the viewport top |
| `S.fadeFromBlack(t=.1, d=.8)`, `S.fadeToBlack(t, d=.7)` | `#fade` |
| `S.endScreen(t, {head: [sel, t], cards: [[sel, t], ...], blurred})` | See end-screen-and-lockup.md |
| `S.lockup(t, {logo, title, sub, url})` | Same |
| `S.rng(seed)` | A seeded PRNG (never `Math.random`) |
| `PVS.bez(x1, y1, x2, y2)`, `PVS.EASE.{css,out,in,inOut,standard}` | Exact CSS cubic-bezier curves (WebKit UnitBezier), so the app's transitions move as in production |

Kit warnings collect in `window.__pvsWarnings` and print as console warnings, which `check`
reports under Runtime. Treat each one as a defect.

`check`'s layout audit reads `data-layout-allow-*` flags on each text element. At register time
the kit flags the product text (it sits under the veil, titles and backdrops by design) and the
title, end screen and lockup text (they sit over the product). `{auditApp: true}` leaves the
product text unflagged so `check` audits layering inside the app; expect veil findings then.

The contrast pass skips flagged text only while another element covers its probe points, and
`S.rack` makes `#veil` hit-testable (`pointer-events: auto`) from the start of a rack in to the
end of the rack out. So product text is ignored exactly while it is blurred (measuring white on a
veiled button reads 1.5:1 and fails every racked sample) and audited normally in focus. It is a
timeline `set`, so it holds under seeking and parallel workers. Audit in-focus moments with
`check --at <times>`; the build prints that command with the setup beat times.

## 6. Audio tracks

`data-track-index` is a Studio lane; the renderer ignores it, but `check` warns when two clips
overlap on one track. buildlib assigns: narration 10, other characters 11, clicks 20, typing
21, pops 22, other effects 23, and moves an overlapping clip to `track + 30`.
