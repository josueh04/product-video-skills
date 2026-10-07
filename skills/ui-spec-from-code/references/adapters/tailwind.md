# Adapter: Tailwind CSS (unproven)

Status: unproven. Use together with the adapter of the framework that renders the markup (React,
Vue, plain HTML). Tell the user it is unproven and add a "Learned on <product>" section when done.

## Where values hide

| Layer | Files | Gives |
|---|---|---|
| Config (v3) | `tailwind.config.(js|cjs|mjs|ts)`: `theme` and `theme.extend`, `presets`, `plugins`, `darkMode` | the project's scale; `resolve_tokens.py` reads literal values statically |
| Theme (v4) | CSS with `@theme { --color-*: ...; }` and `@import "tailwindcss"` | tokens as CSS custom properties; `resolve_tokens.py` reads them as the base scope |
| Default scale | the installed package: v3 `node_modules/tailwindcss/stubs/config.full.js`, v4 `node_modules/tailwindcss/theme.css` | values for classes the project did not override (`p-4`, `text-sm`, `rounded-lg`) |
| Markup | class lists in JSX, templates, `cn()` / `clsx()` calls, `@apply` in CSS | which utilities apply |
| Variants | `dark:`, `hover:`, `focus-visible:`, `md:`, `data-[state=open]:`, `group-hover:` | state and breakpoint styles |

## Resolving a class to literals

1. Read the version from the lockfile; v3 and v4 differ in default scales and naming.
2. For each utility, find its value in the project config (or `@theme`) first, then in the
   package's default scale, and cite both the class (template line) and the value (config line
   or package file).
3. Arbitrary values (`p-[18px]`, `bg-[#0f172a]`) are literal already; cite the template line.
4. Breakpoint variants: evaluate them at the canvas width (`app_canvas.logical`). At 1440 px,
   `md:`, `lg:` and `xl:` apply with default screens; `2xl:` does not.
5. `dark:` follows `darkMode` (`media`, `class`, or a selector). Record which the video uses.

## Traps to expect

- **Presets and plugins** (a company design-system preset, `@tailwindcss/forms`,
  `@tailwindcss/typography`) add values static reading cannot see; `resolve_tokens.py` reports
  spreads and function calls it skipped. Read them by hand from node_modules.
- **`tailwind-merge`** removes conflicting classes at runtime; the last conflicting class wins.
- **Preflight** resets margins, borders and form controls; rebuilt HTML needs the same reset or
  default browser styles leak in.
- **Opacity modifiers** (`bg-black/50`) and `color-mix()` in v4 resolve to rgba or oklch values;
  convert and cite.
- **Purged classes** never exist in production CSS; a class in the source that no config or
  default defines applies nothing.

## Learned on products

(Add a dated section per product: what matched, what surprised you, what to check first.)
