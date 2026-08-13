# The accessibility tree on this app: what it does and does not give

Accessibility-first automation is the right default for most modern sites: the tree is semantic,
small, and stable, where a raw DOM dump is noise. This note is not an argument against that. It is
the measurement of what the tree actually contains **on Blue Yonder SCE's ExtJS 4.2.2 portal**, so
that anything built on it is built on numbers.

Measured by `tools/cdp/a11y-vs-ext.mjs` (Playwright ARIA snapshot vs `Ext.ComponentQuery`), four
screens, Add opened where the screen has one. Raw output: `index/a11y-vs-ext.json`.

| screen | a11y nodes | `button` | `textbox` | `combobox` | `gridcell` | Ext fields | payload keys in a11y |
|---|---|---|---|---|---|---|---|
| Location Preference Rules | 459 | 0 | 0 | 7 | 350 | 14 | **0 of 14** |
| Customer Types | 73 | 2 | 8 | 6 | 0 | 18 | **0 of 18** |
| Business Units | 18 | 0 | 2 | 1 | 0 | 2 | **0 of 2** |
| Carriers (grid, 1,581 rows) | 9 | 0 | 0 | 1 | 0 | — | — |

## Correction to an earlier draft of this note

The first version of this file was written from the Location Preference Rules sample alone and
said the tree exposes **no** buttons and **no** textboxes anywhere in the app. Customer Types
falsifies that: 2 buttons, 8 textboxes. The honest statement is that **role coverage is erratic and
screen-dependent**, which is a different and more awkward problem than absence — absence is
detectable, inconsistency is not. A driver that finds its control by role on one screen and silently
finds nothing on the next is the failure mode that is hardest to notice.

## What holds across every sample

**Payload keys are never present: 0 of 34 fields, on all four screens.** This is the finding that
does not vary, and it is the one that matters most here, because an agent's job is to send a JSON
body, not to click. The body needs `policyVariable`, `supplierNumber`, `inventoryRotationMethod`.
The tree offers the visible labels — "Storage Options", "Supplier", "Inventory Rotation Method" —
and the mapping between the two exists nowhere in it.

There are three vocabularies for one field, and they do not derive from one another:

| | example |
|---|---|
| visible label (a11y tree) | `Description` |
| JSON key (request body) | `businessUnitDescription` |
| DB column (API's 422 error) | `lngdsc` |

Only the component model holds all three ends together, which is why the capture reads
`Ext.ComponentQuery` for field models and button `itemId`s.

**Grid data dominates where it appears.** 350 of 459 nodes on one screen are `gridcell` — page one
of a table we already read from the API, typed, paged and complete. Meanwhile the Carriers grid,
holding 1,581 server-paged rows, produced a 9-node tree.

## Where the accessibility view is still the right tool

- **Non-ExtJS surfaces.** The help corpus and any plain HTML page in the portal read far better as a
  tree than as DOM.
- **A change fingerprint.** Roles-and-names is a compact way to assert a screen actually changed.
  This app updates the URL and `document.title` while leaving the DOM frozen on the previous screen,
  so both of those proved to be liars; a tree digest would not have been.
- **Ancestry for disambiguation**, where roles do appear — "which of the three Save buttons" is a
  question the tree answers well and the flat DOM does not.

## The rule this leaves

Prefer the accessibility tree when the application's own model is out of reach — the usual case, and
why the advice is good advice. Where a framework publishes its component model in the page, as
ExtJS does, that model is strictly richer: it carries the JSON keys, required flags, types and
constraints, and it is the same source the application itself uses to build its requests.

Anything driving this app by role alone should first check `index/a11y-vs-ext.json` for the screen
it is about to drive, and treat a missing role as likely rather than exceptional.
