# Prompt: map the original icons and images of a product's screens

Use once per product, and again when a video adds screens. Hand-drawn approximations of icons
get rejected; this agent finds the originals so the build can use them.

---

You are helping rebuild a real web app 1:1 inside a video. I need the ORIGINAL icons and
images the app uses, so they can be copied, not redrawn. READ-ONLY on the sources: do not edit,
install or run anything. Do not use a browser, and never take an asset from a browser profile or
extension folder. Your only writes go to `<SCRATCH>/icons/`.

Source: `<product_dir>/sources/<role>/` at `<short sha>` (cite as
`<role>/<path>:<line>@<short sha>`). Installed packages, if the user has them:
`<path to the repo's node_modules or equivalent>`. Icon libraries in use (from the lockfile):
`<e.g. lucide-react 0.4xx, @heroicons/react 2.x, an icon font, Material Symbols ligatures,
inline <svg> in templates, images in src/assets>`. Screens: `<paths>`. Reference frames of the
real UI, if any: `<path>`.

For EACH element below, record:
- our key, and where it is used (citation)
- kind: inline-svg | svg-package | font-icon | ligature | asset-image | emoji | text-glyph
- library, version and exact icon name
- the SVG ready to paste (verbatim, with viewBox and stroke width) or, for a font icon, the
  matching SVG file in the package if one exists, else the font file and codepoint from the
  library's CSS; for ligatures, the name plus fill, weight, grade and optical size from the CSS
- for images, the path (copy the file to `<SCRATCH>/icons/assets/` with its original name)
- rendered size and color from the component styles, cited
If an element has no icon in the real app, say so. If you cannot find it, write "not found";
never substitute a similar icon from another set.

Elements (our key: where it appears):
- `<key>`: `<screen and position>`

Output: `<SCRATCH>/icons/ICON-MAP.md` (one section per element, SVG in fenced blocks), the copied
files in `<SCRATCH>/icons/assets/`, and at the end of ICON-MAP.md the list of names per package
for `collect_icons.py` and the list that needs a font subset. Final reply: how many found and not
found, and the path of ICON-MAP.md. Facts only, no design proposals.
