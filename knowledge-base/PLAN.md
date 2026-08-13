# Plan — completing the Blue Yonder knowledge base

Written 2026-08-13. Supersedes the informal "area done" language used earlier, which turned out to
be wrong: an area was being called done once its screens were *mapped*, while its read shapes and
write behaviour were still unknown.

## Definition of done

A screen is complete when all six dimensions hold. Anything less is partial, and
`index/coverage.json` measures it rather than asserting it.

| # | dimension | what it means |
|---|---|---|
| 1 | structure | grid columns, toolbar actions, screen kind |
| 2 | form model | the Add form's real field model: JSON key, label, required, type, maxLength |
| 3 | read APIs | which resources the screen GETs |
| 4 | read shapes | what those GETs actually return — a recorded response body, not just a name |
| 5 | write APIs | create/update/delete proven with a real captured payload |
| 6 | failure modes | duplicate, empty body, bad id, double delete — the status matrix |

Dimension 4 is the one most often skipped, and dimension 6 is where the surprises live: the
`create-duplicate` contract turned out to be 409 on 14 resources but 422 on three, and DELETE is
NOT universally idempotent.

## Why parallel agents cannot do the capture

The browser is a single serial resource and must stay that way:

- one authenticated session, one tab;
- the SPA attaches an iframe per screen visited and never releases them — 333 accumulated frames
  wedged the view layer and eventually crashed the renderer, so the page must be reset every ~30
  screens;
- the OIDC session lives in a session cookie, so a Chrome restart costs a manual login;
- two drivers navigating the same tab produce exactly the stale-frame corruption that already
  cost a day: correct URL, correct title, wrong DOM.

So: **the main thread owns the browser and captures serially. Agents do everything that does not
touch it.** That is a real constraint, not a preference.

### Split

| owner | work |
|---|---|
| main thread (browser, serial) | form models, read-shape capture, write lifecycles, failure batteries |
| agent | coverage tracker (`tools/coverage.mjs`) |
| agent | recipe audit against the evidence store |
| agent | payload candidates and blocked-field analysis |
| agent | graph rebuild and edge validation |

Each agent keeps to the smallest thing that works: reuse the existing scripts, add no abstraction
until a second caller exists, and leave one runnable check behind rather than a test suite.

## Phases

**A — read-only capture (browser).** Finish the 56 remaining Add-form models. Then capture read
*shapes*: one recorded GET response per resource, which closes dimension 4 across every screen at
once because resources are shared.

**B — derivation (agents, parallel).** Coverage tracker; recipe audit; candidate payloads with an
explicit blocked list for required combos, address composites and lookups, where inventing a value
would link the new record to the wrong parent.

**C — writes, Configuration only (browser).** Per creatable screen: create → read back → update →
delete → confirm `RECORD-MISSING`. Then the failure battery per resource. Throwaway records only;
every run ends with a paged cleanup sweep, because that sweep has produced four false negatives
already (stale marker list, missing collection, unpaged read, mid-scan navigation race).

**D — graph and operational tier.** Rebuild the graph so dataflow edges come from real cascades.
Operational screens stay read-only unless a specific area is approved: those screens release work
and move live inventory, and several actions have no clean revert.

## Standing rules carried forward

- Evidence outranks prose. When a recipe and `http/` disagree, `http/` wins.
- Route and title are not load signals; require the rendered content fingerprint to change.
- A UI modal is not proof of a server round-trip — check for a recorded request.
- A 404 with `"url":"/ws/..."` means the endpoint does not exist; only an `errors[]` 404 proves a
  record was deleted.
- Payload keys cannot be derived from API errors: the 422 names the DB column (`lngdsc`) while the
  body needs a camelCase key (`businessUnitDescription`). Capture from the form model or the UI.
- Never trust a cleanup sweep that read one unpaged page.
