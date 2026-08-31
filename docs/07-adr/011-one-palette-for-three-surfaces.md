# ADR 011 — One palette, generated into three surfaces, and only one theme

**Status:** accepted · unreleased

## Context

Three surfaces paint this product: the console, the review pages, and the
extension's side panel and options page. Each kept its own colours.

- `frontend/src/features/console/theme.ts` held eighteen hex literals and an
  orange, `#F47B20`, on a warm-grey ground.
- `new-chrome-extension/src/panel/panel.css` held a different orange, `#e8621f`,
  on a different warm grey.
- `new-chrome-extension/src/options/options.css` held a third palette with no
  orange at all — cool grey, a red alarm — and was, in the same window as the
  panel, visibly a different product.
- `frontend/src/app/globals.css` held stock shadcn neutral: every token
  `oklch(x 0 0)`, pure greyscale, `--primary` near-black. The brand colour was
  not in the design system at all, so every review page rendered black and white
  while the console rendered orange.

None of the three oranges was the brand's. The published system at
`aisro.greymatter.greyorange.com` is `#DC582A` on `#08090b`, dark-first, with
Space Grotesk, Inter and JetBrains Mono.

Nothing was going to hold three hand-maintained palettes in step. They had
already diverged twice and nothing failed when they did.

## Decision

**One file owns colour.** `frontend/src/app/brand.css` holds the palette under
the brand's own names. `globals.css` maps shadcn's vocabulary onto it; the
extension's two stylesheets map theirs. Neither vocabulary has to win.

**`make tokens` copies that file into the extension**, and
`new-chrome-extension/src/tokens.test.mjs` fails when the copy is stale. This
follows `gen-recorder` and `make types`: a generated artifact verified only in a
pipeline is a generated artifact that drifts, so the question is asked where the
code is.

**The application is dark, and there is no toggle.** `<html>` carries a
permanent `dark` class. `next-themes` is not wired up.

**`theme.ts` stays, as a `var()` reader rather than a second palette.** Its
eighteen keys became CSS variables. Twelve files read them through 314 inline
`style={{}}` objects, and a `var()` resolves everywhere a hex did — including
inside a template literal — so the console changed theme without any of those
twelve files changing.

Rejected, and why:

- **A theme toggle.** The brand commits to one visual world. Building a light
  theme means maintaining a second palette nobody asked for, and the argument
  that once justified a light console — that it wrapped a white customer WMS in
  an iframe — no longer holds: a run happens in the operator's own Chrome
  (`docs/14-extension-protocol.md`), not in a viewport we own.
- **Editing `components/ui/` for dark.** The shadcn CLI overwrites that
  directory, and `docs/04-frontend-walkthrough.md` says to wrap rather than edit.
  The primitives already carry `dark:` variants tuned for a dark ground, so
  turning the variant on was the smaller change and the one that survives an
  update.
- **A bundler for the extension.** It has no build step and does not want one for
  a stylesheet. A copy plus a test that notices staleness costs a make target.
- **Deleting `theme.ts` now.** Correct end state, wrong moment: converting 314
  inline styles in the same change as a palette swap is the change most likely to
  regress the console silently, and it can be done file by file afterwards.

## Consequences

A palette change is one file. The two wrong oranges cannot come back without
`tokens.test.mjs` failing.

Twelve `--chart-*` and `--sidebar-*` tokens were deleted; nothing referenced
them.

The costs, honestly:

- **The extension carries a copied file.** It can be stale between the edit and
  `make tokens`. The test is what makes that loud rather than silent.
- **`theme.ts` still exists**, so the console has two ways to reach a colour —
  Tailwind classes and the `ink` object — until the de-inlining lands. That is a
  known intermediate state, not the destination.
- **Anything that assumed a light ground is now wrong** and has to be found by
  looking. Roughly forty light-theme hex literals lived outside `theme.ts` and
  were moved onto tokens; two defects that only appear on dark were found by
  measuring computed styles rather than by reading the diff — a `dark:` variant
  in a primitive outranking a plain utility, and `font-heading` being applied by
  only two components so every page title rendered in the body face.
- **No automated check catches a colour regression.** There is no visual
  regression suite. `make panel-shot` and a browser pass are the check, and they
  are manual.
