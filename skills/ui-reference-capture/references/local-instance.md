# A local instance built like production

The most faithful reference when the app runs on the user's machine. Ask the user before
running their app; it starts servers and may install dependencies.

## Steps

1. **Separate checkout at the production commit.** A new worktree or clone at the locked commit
   (`sources.lock`), in a folder the user agrees to. Never the user's main checkout, and no
   commits or pushes from it.
2. **Isolation.** A local database (SQLite or a local container) seeded with fictional data.
   Never a shared development database, never production credentials, never the user's real
   accounts. Email to a log, third-party APIs mocked (see 5), auth local.
3. **Production build arguments.** Copy them from the deploy pipeline (environment variables
   baked in at build time change branding, product names and feature flags). Build and serve
   the production way (`next build && next start`, not a dev server), because dev servers render
   differently (overlays, unminified styles, strict-mode double renders).
4. **Fictional data.** Rename seeded accounts to the cast from `product.yaml`, use the cast's
   555 numbers and example-domain emails, and a fictional logo. Fix the time zone and locale of
   the browser before the first visit.
5. **Third-party APIs.** A small mock that answers only the calls the screen needs and rejects
   the rest, so nothing reaches a real account.
6. **Capture with a headless browser** (Playwright or similar) at 2x or 3x, selectors by role.
   Save a PNG, the DOM and the computed CSS per state. The browser is a fresh headless profile,
   never the user's.
7. **Parity proof.** Capture one element both locally and from a public production page (only if
   it is public and needs no login), at the same scale, and compare with `pair.py`. In the source
   production this caught a wrong build argument that had silently switched the brand off; the
   rebuilt element matched production at 636x105 px only after it was fixed.

## Write down

In `references/<name>/local-instance.md`: the commit, the build arguments (names and non-secret
values only; never print secret values), the seed data, the mocks, the capture script, and the
parity result. Stop the servers you started when you are done, and only those.
