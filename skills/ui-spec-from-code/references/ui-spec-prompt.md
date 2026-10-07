# Prompt: extract a 1:1 UI spec of one screen from source code

Use one read-only subagent per screen or panel, before the screen is built. Fill every `<...>`,
delete the hints in parentheses, and append the "where values hide" section of the framework's
adapter.

---

You are extracting a precise UI spec from production source code so the screen can be rebuilt
1:1 as static HTML and CSS in an animated product video. READ-ONLY task: do not create, edit or
delete any file; do not run builds, installs, checkouts or fetches; do not use a browser or any
web tool. Never print API keys, tokens or other secrets you see in files: give the file and line
only. Your final message is all I receive.

Source: `<product_dir>/sources/<role>/`, a read-only export at commit `<short sha>`
(`<framework and component library with versions>`, theme `<light|dark>`). Cite every value as
`<role>/<path>:<line>@<short sha>`, the path relative to `sources/<role>/`. For a library default
that is not in the export, cite the package and version from the lockfile and the file inside
the package, or mark it unverified.

Start here (follow imports as needed):
- `<template file>`: `<which elements, which branches, which buttons>`
- `<logic file>`: `<what each action in the story changes: flags, defaults, timers, debounce>`
- `<style file>`: `<geometry: widths, paddings, gaps, radii, borders, z-index, transitions>`
- Shared components it uses: `<buttons, tabs, inputs, selects, toasts, dialogs, icon component>`
- Tokens: `kit/tokens.css` (already resolved and cited) and `<theme or preset file>`
- Copy: `<i18n file>`; use the exact `<language>` strings

Rendering context: the app is rebuilt at a logical viewport of `<W>x<H>` CSS px (scaled later),
root font size `<rem_px>` px at runtime, theme selector `<selector>`. Render facts:
`kit/render-facts.md`. Already rebuilt, match it: `<pieces and their CSS>`. Fonts loaded:
`<list>`; tell me if this screen needs another font or icon set.

States to rebuild (fictional data only):
- S1: `<state, with the exact fictional values to show>`
- S2: `<state after the action>`
- S3: `<final state>`

Deliver, compactly:
A) Geometry of the piece inside the viewport (x, y, width, height), each with a citation or
   marked "computed" with the arithmetic.
B) Static HTML for each state, no framework syntax, class names prefixed `<px>-` (keep the real
   class names after the prefix so the CSS maps back to the source).
C) One CSS block with every value literal (px, hex or rgba, font family, size, weight, line
   height, letter spacing), each line with a short citation comment. Include hover, focus,
   active, disabled and loading states that appear in the story, as extra classes.
D) Motion: every transition, animation and keyframe in the story, with property, from, to,
   duration, easing (the exact curve, e.g. cubic-bezier values), delay, and the logic that
   triggers it (debounce, stagger, insertion order).
E) Icons: library and exact name for each, or the inline SVG verbatim with its viewBox.
F) Strings: i18n key and exact text for every visible string.
G) Production glitches you notice (missing padding, overflow, undefined variables, native
   controls, clipped text), with what production does. Do not fix them in A to F; list them.
H) Not verified: everything you could not cite. Do not invent values.
