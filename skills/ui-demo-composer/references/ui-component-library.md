# The product UI component library

Rebuild each piece of the product once, keep it in the product kit, and include it in every
video that shows it. Copying markup from one video's template into the next is how two videos
end up with two slightly different sidebars, and how a fix (a padding glitch, a renamed menu
item) lands in one video and not the other.

## Layout

```
products/<slug>/kit/ui/
  shell.html        the app frame: sidebar, top bar (the parts every screen shares)
  shell.css
  task-row.html     one reusable piece per file
  task-row.css
  README.md         name | what it is | source citation | states (hov, sel, foc) | used by
videos/<video>/video/src/ui/
  task-row.html     optional: a per-video override (same name wins over the product's)
```

- `{{UI:task-row}}` in `template.tpl` (or inside another component) is replaced by the file's
  markup at build time. The video's `src/ui/` is searched first, then the product's `kit/ui/`.
  Includes nest (a shell can include its nav), up to 6 levels.
- Every `*.css` in `kit/ui/` (then in `src/ui/`) is inlined at `{{UI_CSS}}`, before the video's
  `app.css`, so a video can adjust a shared piece without editing it.
- Each component's CSS keeps the literal values of its spec and one comment naming its source
  (`/* TASK ROW (frontend/src/components/TaskRow.tsx:12@1a2b3c4) */`).
- States are classes the timeline switches (`.hov`, `.foc`, `.sel`, `.dis`), defined in the
  component CSS, so every video hovers the same way.
- Ids inside a component must be unique in the page. Give repeated pieces their ids in the
  template (wrap them: `<div id="row2">{{UI:task-row}}</div>`), or keep the component id-free and
  target it by a wrapper.
- Fictional data in components comes from product.yaml `cast`, so one character keeps one name
  across every video. A person whose surname changed between videos stayed unresolved for a
  whole production; fixing it in one place avoids that.

## When to promote a piece

Promote a piece to `kit/ui/` the second time a video needs it, or the first time when it is the
app shell. Leave one-off states (a dialog that only one video opens) in the video's template.

## When the frontend changes

`source-recon --refresh` lists the videos whose sources changed. Re-extract the spec of the
changed component, update the one file in `kit/ui/`, rebuild each affected video and compare its
setup snapshots against the previous version before rendering.
