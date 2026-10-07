# Prompt: map one screen to its code (read-only Explore subagent)

Fill every `<...>`, delete the hints in parentheses, and launch one subagent per screen (or per
small group of screens that share components), all in parallel.

---

You are mapping one screen of a web app to its source code, so a product video can rebuild it
exactly. READ-ONLY task: do not create, edit or delete any file; do not run installs, builds,
checkouts or fetches; do not use a browser. Never print API keys, tokens or other secrets you see
in files: give the file and line only. Your final message is all I receive.

Source (a read-only export pinned at a commit): `<product_dir>/sources/<role>/`
Locked commit: `<short sha>`. Framework: `<framework from product.yaml>`. App code: `<app_dir>`.
Cite every fact as `<role>/<path>:<line>@<short sha>` with the path relative to
`sources/<role>/`.

Screen: `<name>`, as the video shows it: `<one or two lines from the brief: what is on screen,
which states, which actions>`.

Find:
1. **Route.** The URL path and where it is declared.
2. **Components.** The page component and every child that renders on this screen, with the
   template, logic and style file of each.
3. **Strings.** Every visible string in `<language>`, as i18n key plus exact value, or as a
   literal in the template. Include placeholders, empty states, tooltips and button labels.
4. **State.** What decides what renders: defaults (which tabs, accordions, toggles start open
   or on), conditions, loading and empty states, feature flags, permission or plan checks. Say
   which state the screen is in for the video's story.
5. **Actions.** What each click or keystroke in the story changes (handlers, flags, timers,
   debounce values, navigation).
6. **Visual system.** Which component library and version (from the lockfile), which theme or
   tokens file, which icon sets, which fonts are actually loaded (not only declared).
7. **Assets.** Images, logos and illustrations the screen uses, with their paths.
8. **Risks.** Anything that looks unreleased, gated, restricted to some users, deprecated, or
   different from the brief. Any string that names a third-party vendor or looks like real
   customer data.
9. **Not found.** Everything the brief needs that you could not find. Do not guess.

Output: markdown, one section per item above, citations on every line, under about 2,000 words.
