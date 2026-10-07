---
name: product-kit
description: Extract, once per product, everything every video of it reuses and write it to kit/ and product.yaml (design tokens, font subsets as woff2, icon subsets as SVG from the product's own icon packages, logos in light, dark and app-tile variants from the repo, a fictional cast proposed once for veto and then frozen, the canonical-names map, pronunciations, banned terms and the read-only tool list). Use it when a product is set up or its kit is missing or incomplete, when a video needs an icon, font or logo that is not in kit/ yet, when someone asks for demo names, fake customers, phone numbers or emails, when a brand word is mispronounced or an old product name shows up, and when checking that demo data is fictional.
---

# Product kit

Every video of a product draws from the same kit, so the kit is extracted once, approved once,
and reused. In the production these skills come from, doing this piecemeal was expensive: an
icon font was downloaded without asking, then with approval, then widened three times, and in
between a subagent took two glyphs from a font inside a browser extension folder; the same
demo customer ended up with two different surnames in two videos because a list of names to veto
was never answered; and a renamed product kept its old name on screen until a reviewer caught it.

## Before you start

- Sources are pinned (`sources.lock`, `sources/<role>/`). If not, run source-recon first: every
  kit file cites the locked commit.
- Ask once for every download the kit needs (font packages, icon packages not in the repo), in a
  single list with what, where from and about how big. Nothing is downloaded without that yes,
  and nothing ever comes from a browser profile or extension folder.

```bash
PVS_HOME="$(cd "$(cd "${CLAUDE_SKILL_DIR}" && pwd -P)/../.." && pwd)"
K="$PVS_HOME/skills/product-kit/scripts"
```

## 1. Tokens

Run ui-spec-from-code's resolver for the product's theme, and write the render facts it
describes (runtime rem, theme selector, fonts actually loaded) to `kit/render-facts.md`:

```bash
"$PVS_HOME/bin/pvs-py" "$PVS_HOME/skills/ui-spec-from-code/scripts/resolve_tokens.py" <product_dir> \
  [--theme-selector "<dark selector>"]
```

Set `brand.accent` in product.yaml from the token the product uses for its primary color, citing it.

## 2. Fonts

Find which fonts the app really loads (link tags, `@font-face`, font packages in the lockfile),
not only the ones CSS names. Take the files from the repo or from the installed package (for
example a `@fontsource/<family>` package in node_modules); a font that only exists on a web font
service needs the user's approval to download. Then subset:

```bash
"$PVS_HOME/bin/pvs-py" "$K/subset_fonts.py" <product_dir> <font files...> \
  [--text-file videos/*/audio/lines.tsv] [--license OFL-1.1] [--source <citation>]
```

It writes `kit/fonts/<family>-<weight>.woff2`, rebuilds `kit/fonts/fonts.css` (font-display
block, so a render never paints a fallback first), copies the license text it finds beside the
font or in its package (the OFL requires the text to travel with the font) and records source,
license and license file in `kit/fonts/fonts.md`. A font with an "unknown" license or a
"missing" license file is not ready: find them or ask. Set
`brand.font` in product.yaml. For an icon font that works by ligatures, pass `--all-features` and
the ligature names as `--text`, and check each name renders as a glyph, not as letters.

## 3. Icons

Get the list of icons from ui-spec-from-code's icon extraction (or the specs), grouped by
package. Copy them from the product's own packages:

```bash
"$PVS_HOME/bin/pvs-py" "$K/collect_icons.py" <product_dir> --package <dir with svg files> \
  --names calendar,check,plus [--variant outline/24] [--prefix bx-] [--clean]
```

It copies each SVG to `kit/icons/<set>-<name>.svg` and adds a row to `kit/icons/icons.md`
(file, name, set, source citation, license). It fails on a missing or ambiguous name instead of
picking a look-alike, because a near-miss icon is what made a reviewer reject a whole first cut.
Icons that only exist as an icon font: subset the font (section 2) and take codepoints from the
library's own CSS; the build must fail on an unknown name.

## 4. Logos

From the repo's assets (or a brand package the user hands over) only: never redrawn, traced or
taken from a website. List the candidates, look at them, then copy the three variants:

```bash
"$PVS_HOME/bin/pvs-py" "$K/collect_logos.py" <product_dir>            # candidates in sources/
"$PVS_HOME/bin/pvs-py" "$K/collect_logos.py" <product_dir> --light frontend/assets/logo.svg \
  --dark frontend/assets/logo-white.svg --tile frontend/public/icon-512.png [--root <brand folder>]
```

It writes `kit/logos/logo-light.*` (for light backgrounds), `logo-dark.*` (for dark
backgrounds) and `app-tile.*` (the square icon), SVG when the product has one, with a cited row
each in `kit/logos/logos.md`; it refuses URLs. Then set `brand.logo_light`, `brand.logo_dark`
and `brand.app_tile` in product.yaml to the paths it prints. Pick the variant by background in
every video: a light mark on a white page disappears, which happened in the source production.

## 5. Cast

Demo data is fictional from the first frame, and it is the same in every video. Read
`references/cast-and-names.md` for the reserved number ranges and domains. Propose one full cast
in a single closed question, with your proposal as the recommended default:

> Demo cast for every Acme Tasks video (recommended: use as is):
> Northwind Bakery, Portland OR (northwind.example); owner Maya Lindqvist,
> maya@northwind.example; customer Omar Haddad, +1 503 555 0172. Use it, or change which names?

Full names, one surname per person, kept forever; numbers in 555-0100 to 555-0199; emails and
sites on reserved domains. Reviewers veto names on taste (a bland name was rejected in the source
production), so ask before anything is animated. If the reviewer does not answer, say you are
freezing the proposal and freeze it: silence must not leave two versions of one person. Write it
to `cast:` in product.yaml and check it:

```bash
"$PVS_HOME/bin/pvs-py" "$K/check_cast.py" <product_dir>
```

It fails on a missing surname, a first name with two surnames, a non-555 or non-fictional phone,
and an email or website on a real-looking domain.

## 6. Names, pronunciations, banned terms

Ask the user, then write to product.yaml:

- `names`: canonical name to the legacy strings that must never appear (old product names the
  live UI or the code may still show). Every video uses the canonical name even where the real
  UI is behind, and grep finds the legacy ones before a render.
- `pronounce`: brand words to the spelling the voice engine says right (a made-up product name
  read as a different word was caught by ear in the source production).
- `banned_terms`: competitors, third-party vendors the team keeps off screen, real customers,
  internal code names.
- `never_say` and `positioning`: the one-line identity and the phrasings it must never take.

## 7. Read-only tools

Fill section 10 of `kit/RULES.md`, "Read-only tools" (the template ships it with a
placeholder), with the product's API or MCP tools agents may call
(docs, catalogs, templates), and say that everything else is off limits. A connection with write
access stays read-only by this rule; recommend a credential scoped to read-only, because in the
source production read-only was enforced only by instruction.

## 8. Report

Show the user the kit inventory (tokens count and flags, fonts with licenses, icons by set,
logos, cast), what still needs approval, and the product.yaml keys you changed.
