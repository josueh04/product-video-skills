# Adapter: React (unproven)

Status: unproven. Written from the proven Angular method and general React knowledge. Follow it,
tell the user it is unproven, and add a "Learned on <product>" section at the end when done.
If the app styles with Tailwind, read `tailwind.md` too.

## Where values hide

| Layer | Files | Gives |
|---|---|---|
| Routes | `react-router` config, Next.js `app/` or `pages/`, Remix `routes/` | which page renders the screen |
| Components | `*.tsx` / `*.jsx` | DOM, conditional rendering (`cond && <X/>`, ternaries), list rendering, props defaults |
| State | `useState` initial values, reducers, stores (Redux, Zustand, Jotai), query hooks | default tabs and toggles, loading and empty states |
| Styles | CSS Modules (`*.module.css`), global CSS, Sass, styled-components / Emotion (`styled.div\`...\``, `css` props), vanilla-extract (`*.css.ts`) | sizes, spacing, colors |
| Theme | MUI `createTheme`, Chakra `extendTheme`, a `theme.ts` object, CSS variables in `globals.css` (shadcn/ui) | tokens; CSS-in-JS themes are JS objects, so resolve them by reading the object, not by running it |
| Library defaults | `node_modules/@mui/material/styles/*`, `node_modules/@chakra-ui/theme`, Radix primitives (unstyled) | default paddings, radii, shadows, transitions |
| Copy | `react-i18next` (`t('key')` with `locales/<lang>/*.json`), `react-intl` (`<FormattedMessage id>` with message catalogs), `next-intl`, or literals in JSX | every string |
| Icons | `lucide-react`, `@heroicons/react`, `react-icons`, `@mui/icons-material`, inline SVG components | names map to SVG files in the package (`collect_icons.py`) |
| Motion | `framer-motion` / `motion` (`initial`, `animate`, `transition` with spring stiffness and damping), CSS transitions, `react-transition-group` class timings | durations, easings, springs |

## Traps to expect

- **className composition.** `clsx`, `cn` and `tailwind-merge` decide the final classes at
  runtime; evaluate them for the story's state, and note that `tailwind-merge` drops conflicting
  classes.
- **Runtime themes.** A theme provider can switch tokens by user setting or system preference.
  Record which branch the video shows.
- **Server components and data.** Next.js server components fetch data; the screen's empty and
  loaded states depend on it. Rebuild with fictional data in the same shape.
- **Springs are not durations.** A framer-motion spring has no fixed duration. Record stiffness,
  damping and mass, and simulate it in the build (or sample it) instead of guessing a curve.
- **Portals.** Dialogs, popovers and toasts render into `document.body` and miss container styles,
  like Angular overlays.
- **Unstyled primitives.** Radix and Headless UI ship no styles; all values come from the app.

## Learned on products

(Add a dated section per product: what matched, what surprised you, what to check first.)
