# Adapter: Angular with PrimeNG (proven)

Status: proven. Five narrated videos were rebuilt from an Angular app with PrimeNG (Aura preset,
dark theme), PrimeFlex utilities, PrimeIcons, Boxicons and Material Symbols, and checked against
recordings and captures down to a tenth of a pixel on one element.

## Where values hide

| Layer | Files | Gives |
|---|---|---|
| Template | `*.component.html` | DOM, real class names, `*ngIf` / `@if` / `@for` branches, translate keys (`{{ 'KEY' \| translate }}`) |
| Styles | `*.component.scss` | sizes, paddings, gaps, radii, borders, `:host` rules |
| Logic | `*.component.ts` | defaults (which accordions start closed), option lists, label builders, what a click changes, debounce times |
| Global styles | `styles.scss`, `src/assets/**/abstracts/*.scss`, theme css files | tokens, base text, resets |
| Theme preset | a `*.preset.ts` built with `definePreset(Aura, {...})`, plus the Aura tokens in `node_modules/@primeuix/themes` (or `@primeng/themes` in older versions) | surface ramp, primary color, component tokens (paddings, radii, overlay colors) |
| Config | `app.config.ts` / `providePrimeNG({ theme: { preset, options: { darkModeSelector, cssLayer } } })` | dark mode selector, CSS layer order |
| Utilities | PrimeFlex (`flex`, `gap-2`, `mt-3`) | spacing; a class that no stylesheet defines applies nothing |
| Copy | `src/assets/i18n/<lang>.json` | every string |
| Icons | `primeicons/primeicons.css` (codepoints), `boxicons/svg/**`, Material Symbols names, inline `<svg>` in templates, PrimeNG's own icon components in `node_modules/primeng/fesm2022/primeng-icons-*.mjs` | the original glyphs |

## Traps that cost time

- **Root font size set at runtime.** The app shell can set `document.documentElement.style.fontSize`
  in TypeScript, overriding the SCSS. Search for `fontSize` in the root component before
  converting any `rem`. In the proven production it was 14 px, so Aura's 1.25rem padding measured
  17.5 px.
- **Dark mode is a selector.** `darkModeSelector` decides it (e.g. `.app-dark` on `html`). Check
  whether the app adds it by default.
- **Cascade layers.** With `cssLayer` set, the order (for example reset, primeng, app) decides
  that app rules win over PrimeNG. Without layers, specificity and load order decide.
- **View encapsulation.** `:host ::ng-deep` rules do not reach overlays PrimeNG appends to the
  body (drawers, popovers, select panels), so those use the preset's defaults. Resolve their
  values from the preset, not from the component SCSS.
- **Undefined variables.** Theme variables that existed in an older PrimeNG version
  (`--surface-border`, `--text-color-secondary`, `--green-500`) may not exist in the installed
  one. They paint their fallback or inherit. Record what production paints, then decide whether
  it is a glitch to fix.
- **Custom pop-ups that look like library dialogs.** Check the selector: an app library
  (`lib/*-pop-up`, `modules/*-ui`) with its own keyframes is not `p-dialog`.
- **Overlay placement.** PrimeNG places overlays below the target and flips above when there is
  no room in the viewport, with a gutter (around 2 px for selects, 10 px for popovers in the
  proven version), and animates them in with `showTransitionOptions` (read the default in the
  component source in node_modules; it was a 0.12 s scale-in in the proven version).
- **Accordion and tab defaults.** Start from the component's defaults (often all closed) and open
  with a click in the story. Opening one in the first frame can expose fields (vendor pickers)
  the video must keep out of frame.
- **Line height normal.** `line-height: normal` comes from the font's metrics; measure with
  fontTools and mark the value as computed.
- **Stale checkout.** Icons "not found" in the code but visible in a recording mean the export is
  older than production. Go back to source-recon.

## Behaviour to port 1:1

- Easings: CSS `ease`, `ease-out` and Material's standard curve are cubic beziers; port them with a
  UnitBezier implementation so motion matches the app.
- Pop-ups: backdrop timing and the pop-up's own in and out keyframes (scale, offset, duration).
- Debounces on search inputs and the skeleton rows shown meanwhile.
- Editor behaviours (chips that form when a `{{variable}}` closes) from the editor extension code.
- Geometry code (connector paths, node layout) ported line by line from the TypeScript.

## Build notes from the proven run

- `app.css` was transcribed by hand to literal CSS, one block per component with a comment naming
  it; Angular and Sass were never built.
- State changes were extra classes (`.hov`, `.foc`, `.sel`, `.dis`) toggled by the timeline.
- The build wrote `.pi-*:before` rules from PrimeIcons' own codepoints and failed on an unknown
  icon name.
