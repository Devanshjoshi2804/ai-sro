# Screen recipes

One file per app screen (or per logical sub-view, e.g. a tab within a screen). This is the
finer-grained companion to `../KNOWLEDGE-BASE.md` and `../index/write-endpoints.json` — those
two are the platform-wide summary and the flat allowlist; **these files are the "how to do it"
detail per screen**, so a future automated workflow can act on a screen without re-discovering
its buttons and payloads live.

Every recipe file follows this shape:

```markdown
# Screen: <name>

nav_path, route hash, help topic link

## Tabs / sub-views
list, if the screen has more than one (e.g. Clients has "Clients" and "Groups")

## Buttons and actions
table: button label -> what it does -> API call(s) it fires -> payload shape -> notes/quirks

## Fields
table: field -> type -> required? -> notes (validation, truncation, default)

## Verified write operations
which of PUT/POST/DELETE were actually tested end-to-end (edit->verify->revert or
create->verify->delete->verify), with a pointer to the matching entry in write-endpoints.json

## Open items
anything not yet tested (a button clicked but not exercised, a field not tried, a bulk action)
```

**Do not write a recipe entry from documentation, a guess, or a watched network tab.**

Watching the network panel by eye is exactly the method that produced every falsified claim in
this repo: "suppliers duplicate leaves no orphan" (the address POST fired and was missed),
"carriers duplicate is server-side" (the modal appeared with zero requests sent), and
"transportEquipmentTypes exists" (proved by a 404 that a nonexistent route returns forever).

Every row in "Buttons and actions" must cite a **stored exchange or flow plus its case name** —
a file under `../http/exchanges/` or `../http/flows/`. A claim with no citation belongs under
"Open items" as unverified, never in the actions table. When a recipe and `../http/` disagree,
`../http/` wins and the recipe is corrected.
