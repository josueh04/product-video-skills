# Prompt: verify product behaviour before it is narrated

Use one read-only subagent per product area (a frontend area, each backend, the docs), in
parallel, before narration is written or changed. Fill every `<...>` and delete the hints in
parentheses.

---

Research task for a product video about `<product area>` of `<product name>`. STRICTLY
READ-ONLY: do not create, edit or delete any file; do not run builds, installs, checkouts or
fetches; do not use a browser; do not call any tool that writes to a product workspace. Never
print API keys, tokens, webhook URLs or other secrets: give the file and line only. Never copy
real customer data from fixtures or seeds; describe their structure.

Sources (read-only exports pinned at a commit; cite as `<role>/<path>:<line>@<short sha>` with
the path relative to `sources/<role>/`):
- `<product_dir>/sources/frontend/` at `<sha>`
- `<product_dir>/sources/<backend role>/` at `<sha>`
- Docs: `<URL, repo path, or read-only MCP docs tool>` (cite URLs)
- The document the video illustrates, if any: `<path>`, section `<name>`

Answer each question briefly and only from code or docs. If you cannot find the answer, write
"not found". Do not infer behaviour from names alone.

1. `<How a flow the narration describes really works, e.g. what triggers the daily plan and
   what it reads>`
2. `<What data the video shows, e.g. which fields a task stores and which are shown>`
3. `<Options and limits, e.g. which repeat rules exist, how many reminders, which languages>`
4. `<What the user sees versus what happens only on the server>`
5. `<Who can see it: roles, plans, flags, or internal-only gating>`
6. `<Whether it is released: merged to the production branch, behind a flag, on a branch>`
7. `<Exact visible labels for the options the video names, from the i18n file>`

For every fact, say whether it is visible in the UI (and where: component and line) or
backend-only. Flag anything restricted, gated, unreleased, deprecated, or that names a
third-party vendor.

Output: your final message is all I receive (no files). Markdown, one section per question,
every claim with a citation, under about 3,500 words.
