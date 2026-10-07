# Adapter: plain HTML, server templates and other stacks (unproven)

Status: unproven. Covers static sites, server-rendered templates (Django or Jinja, Rails ERB,
Laravel Blade, Handlebars, Go templates), web components, and anything the other adapters do not.
Tell the user it is unproven and add a "Learned on <product>" section when done.

## Where values hide

| Layer | Files | Gives |
|---|---|---|
| Routes | server routes (`urls.py`, `routes.rb`, `web.php`, a router file) or the file path of a static page | which template renders the screen |
| Templates | `*.html`, `*.jinja`, `*.erb`, `*.blade.php`, `*.hbs`, `*.tmpl`, partials and layouts they extend | DOM, conditionals, loops, the layout chrome around the page |
| Styles | linked stylesheets, `<style>` blocks, Sass or Less sources, a CSS framework (Bootstrap, Bulma, Foundation) and its variables | sizes, colors, spacing |
| Behaviour | vanilla JS, jQuery, Alpine.js (`x-data`, `x-show`), htmx attributes, Stimulus controllers | what a click changes, transitions, defaults |
| Copy | literals in templates, gettext catalogs (`*.po`), Rails `config/locales/*.yml`, Laravel `lang/` | every string |
| Assets | `static/`, `public/`, `assets/` | logos, images, icon sprites (`<symbol>` in an SVG sprite) |

## Traps to expect

- **Layouts and partials.** The visible page is the template plus every layout it extends and
  partial it includes; follow the chain to the base layout.
- **CSS frameworks.** Bootstrap and similar compile their defaults from Sass variables; read the
  variables file of the installed version, and the project's overrides, before the compiled CSS.
- **Server state.** Flash messages, permissions and feature checks decide what renders; record the
  branch the story shows.
- **Web components.** Shadow DOM styles live inside the component definition, and only CSS custom
  properties and `::part()` cross the boundary.
- **Icon sprites.** An `<svg><use href="#icon-x"></svg>` points into a sprite file; copy the
  `<symbol>` verbatim.

## Learned on products

(Add a dated section per product: what matched, what surprised you, what to check first.)

### 2026-10-07: Acme Tasks (examples/acme, plain HTML, CSS custom properties, vanilla JS)

- Strings and icons are applied at runtime (`[data-i18n]` from a JSON catalog, `[data-icon]` SVGs
  fetched and inlined), so the HTML alone is not the screen: read the script that fills it.
- Values computed at runtime (the date next to a title) have no literal to cite; record the code
  line and the fictional value the video uses.
- A FLIP reorder (`getBoundingClientRect`, a transform set and released on the next frame)
  rebuilds as one `fromTo` on `y` per row, from 0 to (new slot minus old slot) times the row pitch.
- A source folder inside the product (not a repo of its own) is pinned by a hash of its files, so
  every citation changes when any file of it changes: finish the frontend before citing it.
- Contrast: `hyperframes check` measured the active nav item at 4.49:1, a real production
  defect that only the check caught; fix it in the product, or list it as a glitch fixed in the video.
