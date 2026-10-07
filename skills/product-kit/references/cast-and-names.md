# Cast, names and pronunciations

## Fictional contact details

| Kind | Use | Why |
|---|---|---|
| North American phone | `+1 <area> 555 0100` to `0199` | The only 555 range reserved for fiction; other 555 numbers can be real services |
| UK phone | `07700 900000` to `900999` (mobile), `020 7946 0000` to `0999` (London) | Ofcom's drama ranges |
| Email | `name@<company>.example`, `name@example.com` | `.example`, `.test`, `.invalid` and `example.com/.net/.org` are reserved (RFC 2606, RFC 6761) and can never belong to anyone |
| Website | `<company>.example` | same |
| Ids, order numbers | Obviously invented (`TSK-1042`) | Real ids leak workspaces |

Do not invent a plausible `.com` domain and check that it is free: it can be registered tomorrow.
Other countries: use a reserved range if the regulator publishes one, else show the number
partly masked.

## The cast

- One company with a city, one owner, the people the stories need (a customer, a teammate, a
  lead). Fewer is better: each one has to be consistent across every video.
- Full names, one surname per person, forever. Two first names that start the same way confuse
  viewers; vary them.
- Names that read as people, not placeholders ("Test User", "John Doe" read as fake).
- Diverse, plausible for the company's city, and not the name of a well-known person.
- AI agents or bots in the product may have a single name; mark their role as `agent`.
- Avatars: initials tiles or the product's own illustrations, never a photo of a real person.

## Names map

`product.yaml names` maps each canonical name to the legacy strings that must not appear:

```yaml
names:
  Acme Tasks: ["AcmeTodo", "Acme To-Do"]
  Smart Plan: ["Auto Planner"]
```

Before every render, grep templates, specs and lines.tsv for each legacy string. Keep the rest of
the element as the real UI has it (a badge, a position, a style); only the name changes.

## Pronunciations

`product.yaml pronounce` maps the written word to what the voice engine receives:

```yaml
pronounce:
  Acme: AK-mee
  SaaS: sass
```

The text on screen never changes; only the voice input does. Listen to the first take of every
line with a brand word in it, and fix the map rather than the script.

## Banned terms

Anything that must never be seen or heard: competitors, third-party AI or service vendors the
team keeps out of the story, real customer and workspace names, internal code names, staff names.
The render QA greps narration transcripts and on-screen text for them.
