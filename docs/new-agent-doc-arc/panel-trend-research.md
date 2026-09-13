# UI/UX Trend Report — 2026-09-10

For: the AI-SRO Chrome extension side panel (`new-chrome-extension/src/panel/`).

## Instrument note

Browser access worked. Screenshots were taken with `mcp__claude-in-chrome__computer`
against three Dribbble popular feeds on 2026-09-10, three viewports each:

- `dribbble.com/shots/popular/web-design` — 3 captures
- `dribbble.com/shots/popular/mobile` — 3 captures
- `dribbble.com/shots/popular/product-design` — 2 captures

Roughly 90 shots seen above the sign-up wall. Everything in "Top Visual Trends"
below names a shot I actually looked at. Nothing here is recalled from training
data; where I extrapolate past what the screenshots showed, it says so.

The panel critique is read off the code as it stands on branch `model-first-rig`:
`panel.html`, `panel.css` (717 lines), `run-card.js`, `ledger.js`, `today.js`,
`nudge.js`, `strip.js`, and the card builder in `panel.js`.

---

## Top Visual Trends

1. **The dark operational surface has stopped being a "mode" and become a
   genre.** Nizam's campaign console, Dstudio's analytics shot, Cloud 2 Voice,
   and Nixtio's purple-on-black instrument panel are all single-theme dark, all
   near-black grounds with one saturated accent, all data-dense. None of them
   offers a light variant in the shot. This is the same commitment the AI-SRO
   brand already made; the trend is that it is no longer a differentiator, it is
   the baseline for tooling.

2. **The row has beaten the card.** Confidency's two shots (19.4k and 3.8k
   views) are the clearest example: dense document and record lists drawn as
   flat rows separated by hairlines, no per-row border, no per-row shadow, no
   per-row radius. Korsa's dashboard does the same under its charts. The
   card-with-border-and-radius is now reserved for things that are genuinely
   separate objects; sequences of homogeneous facts are rows on a shared
   ground. This is the single most transferable finding for a 380px column.

3. **Status is a chip, and the chip carries a shape as well as a colour.** In
   Korsa, Layo, Fireart and Dstudio, state appears as a small pill with a
   coloured dot *and* a word, at 10–11px, uppercase or sentence case, never a
   bare coloured dot and never a bare coloured word. The redundant encoding is
   the trend, not the colour.

4. **Numeric type is monospaced or tabular, and it is the largest thing in the
   composition.** Nixtio (`13,159,201`), Dstudio (`49.3k`, `12.4%`), Korsa
   (`$412,000 / 142 / 4.8 days / 11.2%`). The pattern is a big tabular number
   with a small muted label above or below it, no chart required. Numbers get
   display treatment; labels get muted small caps.

5. **The AI/agent surface has converged on a transcript with inline affordances.**
   Alamin Hossen's "AI Agents for Lending Operations", Jabel Ahmed's automation
   shot, Framer's "professional canvas with built-in agents", Ilias Miah's two
   shots. All of them are a vertical thread where the model's turns carry
   embedded controls — a form, a diff, a confirm — rather than pushing the
   operator to a separate screen. The panel already does this. It is on-trend by
   accident of being correct.

6. **Approval and confirmation moments are drawn as a distinct object, not a
   button.** In the agent shots above, the "do you want me to do this" moment is
   consistently a bounded block: its own inset ground, its own border, the
   payload rendered in mono inside it, and the accept/reject pair sitting inside
   that boundary rather than under the message. It reads as a form the thread
   has stopped at, not as a message with buttons.

7. **Motion is confined to state transitions and to one element at a time.**
   The video-badged shots (Ilias Miah, Bato, AmazingUI, Purrweb) show either a
   single element crossfading, a number ticking, or a row settling into place.
   Full-screen orchestrated entrances, which were everywhere two years ago, are
   now confined to marketing shots (Framer, Korsa's hero, BL/S®).

8. **Hairline > shadow on dark.** Every dark shot separates surfaces with a
   1px low-alpha white line and a one-step elevation change in the ground
   colour. Drop shadows appear only in the light shots. The brand's
   `--brand-shadow-card` already encodes this correctly (an inset white hairline
   plus a very soft dark spread).

9. **Uppercase micro-labels with wide tracking are back, and they are load-
   bearing.** Purrweb ("EVERY SCAN. EVERY HUB."), Endurance/Rylic, Dstudio's
   section keys. In product work they are used as section keys at 10px with
   ~0.08em tracking in a muted grey. The panel's `.stage` and `#here h2` already
   use exactly this, at exactly these values.

10. **Rounded-rect radii have settled around 8–16px for components, with 999px
    reserved for dots, pills and avatars.** Nothing in the sample used the 20px+
    "squircle everything" treatment on functional controls. The brand's
    8/10/16/22/999 ladder matches, and the panel's use of 10px for cards, 7px
    for buttons and 999px for dots is inside it.

---

## Color Trends

Reported for completeness; **the AI-SRO palette is fixed and none of this
changes it.**

- **Primary colours trending**: warm orange-to-red (Ronas IT, Purrweb,
  Endurance, Phenomenon) is having a strong run — the brand's `#DC582A` is
  squarely in the current moment rather than fighting it. Electric violet
  (`#7C5CFF`-ish: Nixtio, Layo, Pixcut) and acid green (Conceptzilla, Sigma)
  are the two other dominant accents.
- **Background approaches**: near-black (`#0A0A0C`–`#101014`) with a one-step
  raised surface, or bone/off-white (`#F5F3EF`). True `#000` and true `#FFF`
  both essentially absent.
- **Accent colours**: one accent, used sparingly, almost never for "good".
  Semantic green/amber/red are kept separate from brand accent in every dense
  shot I looked at. `brand.generated.css` already states this rule in a comment
  and follows it.

**Verdict: no palette recommendation. The extension's palette is correct and
`tokens.test.mjs` is what keeps it correct.**

---

## Typography Trends

Reported for completeness; **the typefaces are fixed and none of this changes
them.**

- **Heading styles**: geometric/grotesque sans at 600–700, tight tracking
  (−0.01 to −0.02em) at display sizes. Space Grotesk is a member of exactly this
  family. Serif display had a visible run in the lifestyle/wellness shots
  (Yscale, HALO LAB, Nasim) and is absent from every operational shot.
- **Body text**: neutral grotesque, 13–15px, 1.5–1.6 line height. Inter is the
  default of this genre.
- **Font weight trends**: a wide gap — 400 body against 600/700 headings, with
  500 used for secondary controls. Very little 300.
- **Numbers**: tabular or monospaced, and given more size than the label beside
  them. JetBrains Mono is a correct choice; what the trend adds is that the mono
  is often *larger* than the body, not smaller. The panel does the opposite —
  see the critique.

**Verdict: no typeface recommendation. One size recommendation, in "What
applies here".**

---

## Layout Patterns

1. **Hairline-separated row lists on a shared ground** (Confidency ×2, Korsa).
   Rows carry a leading glyph/avatar, a flexible label, and a trailing
   right-aligned value. No per-row chrome.
2. **Sticky header + sticky footer with one scroll region between** (nearly
   every mobile shot). The panel already implements this exactly:
   `#strip` / `#scroll` / `#ask-bar` with `height: 100vh` and `min-height: 0`.
3. **Inset payload blocks** — a mono block on a darker inset ground with its own
   radius, used for code, ids, diffs and about-to-be-executed commands (Jabel
   Ahmed, Alamin Hossen, Framer). The panel has `.fix` doing precisely this and
   uses it in one place.
4. **Bento grids** — still very common (Gleb Kuznetsov, Joyce, Fahema Yesmin,
   RonDesignLab) and completely inapplicable here.
5. **Segmented/tab bars pinned under the header** — common in mobile shots. Not
   applicable: the panel has one surface and should keep it.
6. **A leading time/meta rail down the left edge of a log or thread** (Dstudio's
   activity list; several of the agent shots). The panel already has this in
   `.message .when`, at a fixed 40px, printing the minute only when it changes.
   This is a good pattern and it is already implemented well.

---

## Elements to Avoid

- **Glassmorphism / backdrop blur.** Almost entirely gone from the operational
  shots and expensive to composite over a live WMS.
- **Gradient text and gradient borders.** Present only in marketing shots
  (Framer, Nuvora, Korsa hero).
- **Progress bars as a proxy for state.** The trend has moved to per-step rows;
  `run-card.js` already argues this in its header comment, but `panel.css`
  `.progress` and `panel.js:130–137, 539` still draw the old bar for backend
  runs. It is now the only place in the panel that says "4 of 7" without saying
  which four.
- **3D renders and product mockups.** Fine on Dribbble, noise in a 380px column.
- **Skeleton shimmer loaders.** Nothing here takes long enough; a static muted
  line is cheaper and does not animate beside a live warehouse screen.
- **Theme toggles.** Not applicable — single theme by decision.
- **Neobrutalism** (thick black borders, hard offset shadows). Visible in the
  print/branding feeds, absent from product. Would be actively harmful here: it
  spends the loudest visual register on chrome rather than on state.

---

## Recommended Direction

**"Instrument, not dashboard."** Keep everything the panel already does that
matches the trend — the pinned composer, the time rail, the transcript with
inline controls, the mono for ids and money, the hairline separation — and spend
the redesign budget on exactly one thing: **making the eight run states
distinguishable without reading a sentence.**

Concretely, three moves:

1. **Give state a DOM hook and a redundant encoding.** Today `run-card.js` sets
   `card.dataset.status = run.status` and `panel.css` never reads it, and the
   step row carries no outcome attribute at all. Add `row.dataset.outcome` in
   `stepRow()` and style on it. Every state then gets glyph + word + colour +
   one structural difference (indent, rule, inset), which is what makes it
   survive a colour-blind operator and a glance.
2. **Demote the run card's chrome, promote its rows.** A run is a homogeneous
   sequence — trend #2 says that is a row list, not a stack of bordered blocks.
   The panel is close to this already; what it lacks is a consistent leading
   gutter so the glyph column lines up down the whole card.
3. **Promote the one moment that is not homogeneous.** See the last section.

---

## What applies here and what does not

Per trend, against a 320–480px single-column panel with no build step.

| # | Trend | Survives 380px? | Why |
|---|---|---|---|
| 1 | Dark single-theme operational surface | **Yes — already done** | Nothing to change. `brand.generated.css` + `tokens.test.mjs` is the right mechanism and it passes. |
| 2 | Rows over cards | **Yes, and it is the highest-value borrow** | At 380px a card costs ~28px of horizontal chrome (2×14px padding) plus 2px border. The panel currently nests `.card` (10px radius, 13/14px padding) inside `#cards` which itself has 14px padding. Homogeneous run steps and thread entries should be rows on the ground; only genuinely separate objects (a run, an offer, a failure) keep card chrome. |
| 3 | Status chip = dot + word | **Yes** | Costs ~60px of a 380px row. The strip's `.chip` already does dot + host + word. The *step rows* do not — they have a glyph and no word for the state. |
| 4 | Big tabular numbers with muted labels | **Partially — invert the current sizing** | The panel's numbers are its *smallest* type: `.today` at 11px, `.metrics` at 11.5px, `.run .meta` at 11px, all in `--ink-mute`. Recommendation: the three `today` numbers go to 13–14px mono in `--brand-bright`, with their words staying 11px muted. This is the one type-size change worth making, and it is a size, not a typeface. |
| 5 | Agent transcript with inline affordances | **Yes — already done, and well** | `ledger.js` + `KINDS` table is a better implementation than most of the shots: one table of answers, no per-kind branch, unknown kinds degrade to words. Do not touch. |
| 6 | Approval as a distinct bounded object | **Yes — and it is the biggest gap.** | See the next section. |
| 7 | Motion on state transitions, one element | **Yes — already done, conservatively** | The only animations are `beat` on the recording dot and a 180ms colour transition on `.run .glyph`, both killed under `prefers-reduced-motion`. Correct. One addition worth making is in the next section; nothing else should animate. |
| 8 | Hairline over shadow on dark | **Yes — already done** | `--brand-line-soft/-line/-line-strong` are used throughout. The panel never uses `--brand-shadow-card`; it does not need to. |
| 9 | Uppercase tracked micro-labels | **Yes — already done** | `.stage` and `#here h2` are 10.5px/700/0.08em/uppercase/muted. Reuse `.stage` for the step-state word rather than inventing a class. |
| 10 | 8–16px radii, 999px for dots | **Yes — mostly done** | Minor inconsistency: `.card`/`.menu`/`#candidates li` use 10px, buttons use 7px, `.fix` uses 6px, the focus ring overrides `border-radius: 4px`. Four ad-hoc values where the brand ships a ladder. Low priority, but `--brand-radius-sm/-md` exist and are unused by `panel.css`. |
| — | **Bento grids** | **No** | Requires ≥2 columns to mean anything. At 380px a bento degrades to a stack, which is what the panel already is. Reject. |
| — | **Wide hero / full-bleed imagery** | **No** | No hero. The first thing on the surface must be state. Reject. |
| — | **Multi-column dashboards, KPI grids** | **No** | `today` is the panel's entire dashboard and it is one line of three numbers, absent on an empty day. That restraint is correct — do not grow it. Reject. |
| — | **Segmented tab bars** | **No** | A tab bar is a claim that the operator navigates this surface. They do not; they are mid-task in a WMS and the panel reports facts. Reject. |
| — | **Glassmorphism / backdrop-filter** | **No** | Compositing cost beside a live WMS, plus it destroys contrast on `#08090b`. Reject on both counts. |
| — | **Skeleton shimmer** | **No** | Animates continuously beside live work for no information. Reject. |
| — | **Progress bars** | **No — and remove the one that is left** | `.progress` in `panel.css` and `panel.js:130–137` survive for backend runs. `run-card.js`'s own header comment explains why this is the wrong picture. It should become the same step rows. Reject and delete. |
| — | **Theme toggle / light mode** | **N/A** | Single theme by decision. |
| — | **Neobrutalism** | **No** | Spends the loudest register on chrome. Reject. |
| — | **3D / illustration** | **No** | Reject. |

### Constraint check on every recommendation above

Everything recommended is CSS on existing DOM plus, in two places, one extra
`dataset` assignment in existing JS. No dependency, no build step, no new file,
nothing that would trip `no-undef`. All motion proposed is a single `transition`
already covered by the existing `prefers-reduced-motion` block.

---

## The parked-approval state

**The finding.** A step waiting for a human to approve a live warehouse write is
currently the *least* distinguished state on the surface, not the most.

Read from the code, not inferred:

- In `run-card.js:stepRow()`, the awaiting branch appends `.planned`, an
  Approve button and a quiet Stop **to the ordinary `.step` row**. The row gets
  no class, no `data-outcome`, no marker. `panel.css` therefore *cannot* target
  it — grep confirms no rule in the stylesheet matches an awaiting row.
- Its glyph is `⏸`, which `glyphFor()` returns for `withheld` as well. A write
  that a dry run declined to send and a write that is sitting in front of a
  human waiting to be authorised render the identical character.
- `.run .step:has(.glyph) .glyph { color: var(--ink-mute); }` at `panel.css:678`
  flattens **every** glyph to `#6b7280` — `✓`, `✓!`, `⏸`, `✗`, `●`, `○` all
  arrive in the same muted grey. The 180ms colour transition above it has
  nothing to transition to. So the entire step-state vocabulary is currently
  carried by one character at 12px in the palette's lowest-contrast grey.
- The Approve button inherits the bare `button` rule: accent fill, `#fff` text,
  7px radius, 12.5px/600. That is byte-for-byte the same button as "Do the next
  one", "Yes, do it", "Run it", "Undo that" and "Try another way". The control
  that commits a change to a live warehouse record is visually identical to the
  control that dismisses a suggestion.
- `--ink-mute` (`#6b7280`) on `--brand-surface` (`#0d0f13`) measures **3.93:1**;
  on `--brand-ground` (`#08090b`), **4.08:1**. Both are below WCAG AA's 4.5:1
  for normal-size text, and every use of it in the panel is 10.5–11.5px, i.e.
  normal size. `.note`, `.today`, `.metrics`, `.run .meta`, `.run .note`,
  `.stage`, `.chip .says` and the chevron are all affected. This is a measured
  failure, not a judgement call.

**The recommendation — one move, three redundant channels, no new colour.**

Draw the parked-approval step as **a bounded inset block that interrupts the row
rhythm**, the way trend #6 draws it, and make it the *only* thing on the surface
allowed to do so.

1. **Structure (the channel that works with no colour vision at all).** Give the
   row a hook — in `stepRow()`, `row.dataset.outcome = "awaiting"` — then in CSS
   pull it out of the flat step list: `background: var(--brand-surface-2)`, full
   `--brand-radius-md`, `padding: 10px 12px`, `margin: 6px 0`, and a 3px
   `border-left: var(--brand-warn)`. Nothing else in the run card has a filled
   ground, so "the row that became a box" is unambiguous even in greyscale, at a
   glance, from the corner of the eye. The existing `.card[data-tone="attention"]`
   rule is already exactly this treatment — reuse its shape so the panel has one
   idea of "this needs you", not two.

2. **Words (the channel that works for a screen reader and for a photocopy).**
   Add a `.stage` micro-label above `.planned` reading **`WAITING FOR YOU`**, and
   change the awaiting glyph from `⏸` to a distinct character so it stops
   colliding with `withheld` — `▶︎` is wrong (it reads as "play"); use **`⏵?`**
   or simply drop the glyph in this state, since the box replaces it. Also
   append the host to the `.planned` line: an operator approving `POST /orders`
   should see *which* system, and `wordsFor()` already has the full URL in hand.

3. **Colour, last and as reinforcement only.** `--brand-warn` `#f59e0b` on
   `--brand-surface-2` measures well over 4.5:1 and is already the panel's
   "attention" semantic. Do **not** use the accent — `brand.generated.css` says
   in its own comment that the accent must never mean state, and an orange
   approve button beside an orange brand mark is exactly the confusion that rule
   exists to prevent. Keep the Approve button's accent *fill* (it is the primary
   action) but give it a visible weight difference from every other primary
   button in the panel: `padding: 9px 18px`, and a persistent
   `box-shadow: var(--brand-glow-accent)` — a token that already exists and that
   `panel.css` uses nowhere. One glowing button on the whole surface, only ever
   in this state.

4. **Motion — one, cheap, interruptible.** When the block appears, a single
   `border-left-color` transition from `transparent` to `--brand-warn` over
   ~200ms. Nothing repeating, nothing that reflows, nothing that steals focus,
   and it is already covered by the existing `prefers-reduced-motion` block. Do
   **not** add a pulse: a repeating animation beside a live WMS is exactly the
   competition for attention the panel is designed to avoid, and a state that
   throbs until answered trains the operator to answer it without reading.

5. **Focus.** The Approve button should be the block's first focusable element,
   and the block should be reachable by keyboard from the top of the run card.
   The existing `:focus-visible` ring (2px accent, 2px offset) is fine on
   `--brand-surface-2` and needs no change.

**Why this and not the obvious alternatives.** A modal blocks input beside a live
WMS and is the one thing this surface must never do. A colour-only treatment
fails the colour-blind case, which the brief names as a warehouse-record-level
risk. A pulse or a badge count trains dismissal. A separate "approvals" section
breaks the rule that the answer must sit on the step it is answering — a rule
`run-card.js` already states in a comment and gets right today. The bounded
inset block is the only option that is unmistakable, uses no new colour, costs
one `dataset` line and a dozen lines of CSS, and leaves the panel's existing
structure — which is largely correct — intact.

---

## Appendix: other things in the current panel that are already wrong

Ordered by how much they cost an operator. All verified against the code.

1. **`--ink-mute` fails WCAG AA everywhere it is used** — 3.93:1 on the card
   ground, 4.08:1 on the panel ground, at 10.5–11.5px. 21 uses in `panel.css`.
   The palette has `--brand-body` `#97a0ac` at **7.2:1** on the same ground.
   Recommendation: `--ink-mute` should map to `--brand-body` for anything that
   is text a person is expected to read (`.note`, `.today`, `.metrics`,
   `.run .meta`), and stay at `--brand-muted` only for genuinely decorative
   marks (the chevron glyph, placeholder text). This is a one-line token
   remapping in `panel.css:26–28`.

2. **`.run .step:has(.glyph) .glyph { color: var(--ink-mute) }` (line 678)
   destroys the whole step-state vocabulary.** It overrides nothing above it
   because nothing above it sets a glyph colour — which means the rule's stated
   purpose ("a step that has been checked, and one that only came back 200")
   is not implemented at all. `✓` and `✓!` differ by one 12px character in
   4:1 grey. The distinction the read-back rung exists to draw is invisible.
   This is the second-most-important state on the surface after parked approval,
   and it currently has no visual expression.

3. **`.run[data-status]` is set in JS and read by no CSS rule.** A run that was
   `refused` and one that `held` render identically apart from a sentence in the
   title. Same for `data-why` on the strip chip (set in `strip.js`, never
   styled) and `data-answered` on a spent offer (set in `ledger.js`, never
   styled). Three state hooks that exist in the DOM and do nothing. That is the
   cheapest available win in the whole file — the JS is already correct, only
   the stylesheet is missing.

4. **The chip conflates "open" with "needs a press".** `strip.js` sets
   `chip.dataset.open = String(why !== null)`, so the chevron direction is the
   *only* signal that the browser is disconnected, the grant expired, the
   channel is down, or the site is excluded. Four states that only the operator
   can fix, expressed as a rotated `›`. Given the `data-why` hook already
   exists, this is a styling gap, not a logic one.

5. **The `.progress` bar is a survivor of the design `run-card.js` replaced.**
   Still drawn for backend runs (`panel.js:130–137, 539`). It is the one place
   the panel says "4 of 7" without saying which four. Should be step rows.

6. **`.card.line .dot` is hard-coded to `--good`.** It is the only colour in
   that component and it is green regardless of what the line says.

7. **Radii are ad-hoc.** 10px cards, 7px buttons, 6px `.fix`, 4px on the focus
   ring, against a brand ladder of 8/10/16/22/999 that `panel.css` imports and
   never uses (`--brand-radius-*` appears zero times). Cosmetic, lowest
   priority, but it is drift of exactly the kind `tokens.test.mjs` exists to
   prevent — the test guards the colours and nothing guards the shapes.

**What is already right and should not be touched:** the pinned-composer /
single-scroll-region frame; the time rail; `ledger.js`'s no-`innerHTML` rule and
its `KINDS` table; the nudge's ninety-second life; `today` being absent rather
than zeroed; `button.danger` being destructive at rest rather than on hover;
`prefers-reduced-motion` being honoured globally; and the decision that the
accent never means "good". Several of those are better than anything in the
sample I looked at.
