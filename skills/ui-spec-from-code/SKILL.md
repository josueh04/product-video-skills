---
name: ui-spec-from-code
description: Turn a product's real frontend code into 1:1 rebuild specs for a video, one read-only subagent per screen, each returning static HTML, CSS with every variable resolved to its literal value and cited (role/path:line@sha), every state, transitions with exact durations and easings, icons from the code's own icon sets, and the exact i18n strings; plus resolve_tokens.py to write the product's design tokens to kit/tokens.css. Use it whenever a screen of the product has to appear in a video, when writing or fixing video/src/app.css or the template markup, when someone asks for exact sizes, colors, fonts, paddings, animations or icons of a screen, when a rebuilt screen "looks off" next to the real app, and when the design tokens or theme of a product need extracting. Framework adapters cover Angular with PrimeNG (proven), React, Vue, Tailwind and plain HTML (unproven).
---

# UI spec from code

The video rebuilds the product's interface in HTML and CSS instead of recording it, so the
interface is only as true as the spec it is built from. Approximations get caught: in the
production these skills come from, a reviewer rejected hand-drawn icons and logos on the first
review, and a hand-built badge with the wrong size and name made him furious. The fixes came
from reading the code, and the code hid traps nobody sees by eye: the root font size was set at
runtime by the app shell (14 px, not the 10 px the stylesheet declared), several CSS variables
did not exist in production and painted their fallback, a component lost its accent bar in a
commit two months earlier, and two "dialogs" were custom pop-ups, not the library's dialog.

So every value in a spec is literal and cited, and a value you cannot cite is flagged, never
guessed.

## Inputs

- `videos/<video>/SOURCES.md` from source-recon: each screen, its route, components and state.
  If it is missing, run source-recon first.
- `sources/<role>/` and `sources.lock`. Every citation uses the locked sha.
- `product.yaml`: `app_canvas.logical` (the viewport the UI is rebuilt at), `app_canvas.theme`,
  `app_canvas.rem_px`, `sources[].framework`.
- The adapter for the framework: `references/adapters/<framework>.md`. Read it before writing
  the subagent prompts; it says where values hide in that stack.

| framework in product.yaml | adapter | status |
|---|---|---|
| `angular-primeng` | `references/adapters/angular-primeng.md` | proven in production |
| `react` | `references/adapters/react.md` | unproven |
| `vue` | `references/adapters/vue.md` | unproven |
| any stack using Tailwind | `references/adapters/tailwind.md` (with the framework's own) | unproven |
| `html`, `other`, server templates | `references/adapters/html.md` | unproven |

For an unproven adapter, tell the user it is unproven, follow it, and add what you learn to it
at the end (a short "Learned on <product>" section), so the next product starts further ahead.

## 1. Global render facts (once per product)

Before any screen, establish the facts every screen depends on and write them to
`kit/render-facts.md` with citations:

- Root font size **at runtime** (search the app shell for code that sets it, not only the CSS),
  so `rem` converts right. Update `app_canvas.rem_px` in product.yaml if it differs.
- Theme: which selector turns the video's theme on, and whether it is on by default.
- Token files, the CSS layer or import order (which rules win), and the component library with
  its exact version from the lockfile and its theme preset.
- Fonts actually loaded (link tags, `@font-face`, font packages), not just named in CSS. A font
  that is declared but never loaded renders as the fallback in production.
- The desktop breakpoint, to confirm `app_canvas.logical` shows the desktop layout.

Then write the tokens, resolved to literals for the video's theme:

```bash
PVS_HOME="$(cd "$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/../.." && pwd)"
"$PVS_HOME/bin/pvs-py" "$PVS_HOME/skills/ui-spec-from-code/scripts/resolve_tokens.py" <product_dir> \
  [--role frontend] [--theme-selector "html.dark"] [--files src/styles/tokens.css ...]
```

It reads CSS custom properties, top-level SCSS variables and a Tailwind v3 theme (statically)
from `sources/<role>/`, resolves every `var()` and `$variable`, and writes `kit/tokens.css` with
a `/* role/path:line@sha */` citation on each line. Lines flagged `UNDEFINED` are variables
production does not define (a likely glitch); `needs a Sass compile` marks values built with Sass
functions, which the subagent must resolve by hand from the function and its inputs. Use
`--files` when the export holds unrelated stylesheets (docs sites, email templates, vendored
CSS).

## 2. One subagent per screen

Launch one read-only subagent per screen (or per panel of a large screen), all in parallel, with
`references/ui-spec-prompt.md` filled in and the adapter's "where values hide" list appended.
Point each at `sources/<role>/` (not the user's checkout) and give it the rendering context:
logical canvas size, theme, rem, render facts, tokens, and the CSS of pieces already rebuilt so
the new piece matches.

Each returns: geometry inside the canvas, static HTML per state (no framework syntax), one CSS
block with literal values and a citation per value, hover/focus/active/disabled/loading states
as extra classes, transitions and keyframes with exact durations and easings, icons by library
and name (or inline SVG verbatim), every visible string, and an explicit "not verified" list.

The coordinator (you) does not extract specs itself: one screen of a real app can take tens of
kilobytes of findings, and a coordinator whose context fills up mid-video loses track of the
whole build.

## 3. Icons and images

Icons come from the product's own icon sets and assets, never drawn and never from a browser
profile or extension folder. Run `references/icon-extraction-prompt.md` once per product (and
again for new screens) to map every icon a video needs to its library and name, then hand the
names to product-kit's `collect_icons.py`, which copies the SVGs into `kit/icons/` with
citations. For icon fonts with no SVG files, the build writes the codepoints from the library's
own CSS and must fail on an unknown name rather than render an empty box.

## 4. Write the specs

For each screen, `videos/<video>/specs/<screen>.md` and `specs/<screen>.html`:

```markdown
# Spec: <screen>
Source: frontend@1a2b3c4 (see SOURCES.md). Canvas 1440x810, theme light, rem 16.

## Geometry
| element | x | y | w | h | citation |

## States
S1 <name>: <what is shown, fictional data>. HTML in <screen>.html, section S1.

## CSS
<one block, literal values, each line with /* role/path:line@sha */>

## Motion
| what | property | from | to | duration | easing | delay | citation |

## Icons
| key | library | name | file in kit/icons | citation |

## Strings
| key | text | citation |

## Fixes (production glitches fixed in the video)
| what | production does | video does | why |

## Not verified
- <value or behaviour, why, and the best available reference>
```

## Keep the look, fix the glitches

Rebuild layout, tokens and behaviour 1:1, including the animations, hovers, typing and loading
states that make it feel like the real product. But fix visible production defects, because the
video shows the product at its best and a reviewer will ask why a bug is on screen: missing
padding, overflow, clipped text, a native browser control (a grey default audio player) where
the product means a designed one, an undefined variable painting a fallback, a focus ring left
after a click. List every fix in the spec's Fixes table and in the BRIEF notes. Keep oddities
that are design decisions (a sticky footer covering a field, a sidebar that scrolls with its
content); changing those is redesign, not a fix.

Two more transformations the spec applies and records:

- **Canonical names.** Replace legacy strings from `product.yaml names` with the canonical name
  even when the live UI still shows the old one, and keep everything else about that element.
- **Banned terms.** If a real screen shows a vendor or a term in `banned_terms` (a model picker,
  an integration card), leave that part out of frame. It must not look empty or broken; choose a
  framing or a state where it is naturally absent.

## Data

Specs carry fictional data only, from `product.yaml cast`. Fixtures, seeds and screenshots in
the repo can hold real names; use their shape, never their values.

## Checklist before handing specs to the build

- [ ] Locked commit cited; render facts written; tokens resolved for the video's theme
- [ ] Canvas size above the desktop breakpoint; rem matches runtime
- [ ] Every `var()` resolved; undefined ones listed with their fallback (or fixed as a glitch)
- [ ] Every string from the i18n file or template; canonical names applied
- [ ] Every icon from the app's libraries; the build fails on a missing glyph
- [ ] Logos and images from the repo assets
- [ ] Default states (tabs, accordions, toggles) match the code
- [ ] Overlay, pop-up and transition timings with exact easings
- [ ] Scroll ranges within real content; no text cut at an edge
- [ ] No vendor, banned term, internal id or real customer data in frame
- [ ] Fixes and kept oddities listed; unverified values listed for the reviewer
