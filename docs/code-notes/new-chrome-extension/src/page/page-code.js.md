# Notes for `new-chrome-extension/src/page/page-code.js`

Comments and docstrings moved out of [`new-chrome-extension/src/page/page-code.js`](../../../../../new-chrome-extension/src/page/page-code.js). Each note names the code it explains (the `sroPage` method, then the line in the current file) and keeps the original text, updated where the code it describes moved (spec §6.4): the functions this file exposes as `globalThis.sroPage` used to be exported from `new-chrome-extension/src/background/in-page.js` and handed to `chrome.scripting.executeScript` one at a time as `func`; they are unchanged in body, but the file around them is now a classic script with no `import`/`export` at all, loaded whole -- by the extension with `executeScript({files})`, by Steel with `add_init_script(path=…)`, and by the backend image through a BuildKit named context -- so the same code runs identically in all three.

## module, [line 1](../../../../../new-chrome-extension/src/page/page-code.js#L1): Docstring

> The half of a command that has to happen inside the page.
>
> Nothing in this file may reference anything outside `globalThis` -- no
> imports, no module constants, no helpers next door. Each `sroPage` method is
> therefore self-contained and a little repetitive, and that is the price of
> being evaluated as a classic script in a realm this file's own module scope
> does not exist in: the extension serialises and runs it with
> `chrome.scripting.executeScript({files: ["src/page/page-code.js"]})`, Steel
> with Playwright's `add_init_script(path=…)`, and both then call one named
> method off `globalThis.sroPage`.
>
> `perform` and the two that go with it (`performAt`, `screenSize`) run in the
> page's own realm (`world: "MAIN"`), because the component locator is a
> question only the application's own framework can answer -- the same reason
> the recorder had to move realms. `send` runs in the isolated world instead:
> it is same-origin with the page, so it carries the operator's cookies, but
> the page's patched `fetch` is not the one it calls, so a replayed request
> never enters the evidence plane as though the operator had made it.

## `REPAIR_THRESHOLD`, [line 2](../../../../../new-chrome-extension/src/page/page-code.js#L2): Constant

> What a live control has to score in `score` before `repair` will act on
> it, AFTER the two gates `repair` applies first: its role must equal the
> recorded role exactly, and its landmark path must equal the recorded path
> exactly. Kind and scope are therefore never points that can be traded for
> something else -- the review of 2026-09-24 showed an additive score where
> role, name and landmarks were all points let a `<button>Customer</button>`
> stand in for a relabelled textbox, and let `Delete` in an "Orders" section
> stand in for `Delete` in a "Confirm delete" dialog that never opened.
>
> What is left to score is identity beyond kind and scope: 3 for an exact
> name, 1 for a partial one (the live name contains the whole recorded
> name, not just a word of it), 1 each for `name`, `autocomplete` and
> `placeholder`, 2 for an identical component chain, 1 for sitting within
> `NEAR_PX`. 3 means an exact name alone, or a partial name plus one more
> signal (2 points, not 3), or a component chain plus one more signal --
> never position alone, never one attribute alone.
>
> That guarantee is weaker on ExtJS: a page with generated itemIds gives
> every sibling field the same xtype-only chain, so chain (2) plus
> proximity (1) reaches the threshold from layout alone, and the landmark
> gate is vacuous on pages without aria landmarks. Only `REPAIR_MARGIN`
> stops a wrong sibling there -- a lead of 2 cannot come from position
> alone.
>
> The failure mode of setting it too high is "drops to sight". A wrong pick
> is not verified away downstream, because a repaired control used to be
> checked by re-running the same repair; so `act` now reports `repaired`,
> `holds` checks only the element `act` pinned, and a write is never
> repaired at all (see `find`).

## `REPAIR_MARGIN`, [line 3](../../../../../new-chrome-extension/src/page/page-code.js#L3): Constant

> How far the best repair candidate has to lead the runner-up. A tie is a
> coin flip wearing a threshold's confidence; a lead of 1 is nearly the
> same, because the single point can come from `NEAR_PX` proximity alone,
> which depends on layout. 2 means the lead has to include at least one
> signal that is not position.

## `NEAR_PX`, [line 6](../../../../../new-chrome-extension/src/page/page-code.js#L6): Constant

> How close, in CSS pixels, a live control's centre has to sit to the
> recorded `bounds` centre to earn the one "still roughly where it was"
> point in `score`, and how `nearest` breaks a tie between several matches.
> Both compare PAGE coordinates (`boundsOf`: the viewport box plus the
> window's scroll), which is also what the recorder records, so a recording
> made while scrolled and a replay at the top of the page compare the same
> thing. Wide enough that a control nudged by a responsive layout or a
> sidebar toggling still counts as "there".

## `GENERATED_ID`, [line 7](../../../../../new-chrome-extension/src/page/page-code.js#L7): Constant

> What `attributeSelector` refuses to build a selector out of: an id ExtJS
> assigned rather than one the page's own author wrote. `ext-gen4443` is a
> different control after every reload -- render order, not identity --
> and a component library that names its own generated ids differently
> tomorrow is still caught by the SHAPE (a vendor prefix, or three digits
> in a row) rather than by a list of prefixes this deployment happens to
> have seen. A list is a per-vendor branch waiting to be wrong the first
> time this runs against a second WMS; the shape is the actual rule ExtJS
> ids follow, stated once.

## `readers`, [line 10](../../../../../new-chrome-extension/src/page/page-code.js#L10): Constant

> How a control is named, placed, scoped and pathed -- `roleOf`, `ownName`,
> `nameOf`, `landmarkRole`, `landmarksOf`, `cmpOf`, `chainOf`, `xpathOf`,
> `boundsOf`, `framePathOf` -- written once, here, and used twice: by this
> file to resolve a control, and by the recorder
> (`backend/src/sro/infrastructure/steel/recorder.js`) to record one.
> `_recorder_script` in `capture.py` cuts this block out of this file (from
> `  const readers = ` to the first `  })();` line after it) and splices it
> in where `recorder.js` says `__PAGE_READERS__`; `make gen-recorder` writes
> the extension's copy the same way. The two used to be copies and had
> already drifted (the recorder followed `aria-labelledby` for a landmark's
> name, this file did not), so evidence named a control one way and replay
> looked for it another. One block in its own IIFE, because this file may
> reference nothing outside `globalThis` and the recorder cannot import it.
> `test_generated_scripts_are_current.py` checks the block appears in the
> recorder verbatim.

## `roleOf`, [line 93](../../../../../new-chrome-extension/src/page/page-code.js#L93): Function

> What kind of control this is, whether or not the page bothered to say.
>
> `getAttribute('role')` reads only what an author wrote down, and almost
> nobody writes `role="button"` on a `<button>` -- the browser knows it
> implicitly. So the one identity this system has for a control that carries
> no framework component and no test id was `name|<label>`, which reads
> exactly the same as an accessible name on a `<div>` -- and a `<div>` in a
> mailbox is labelled with the mail.
>
> Measured on the deployment 2026-09-20 over 732 gestures: 132 identities
> came through that branch, and they are two different things wearing one
> shape. `Username or email` (30), `Sign In` (14), `Subject` (5) are
> controls on an `<input>` or a `<button>`. `Devansh Joshi` (17),
> `Tanisha Pradhan` (13), `104` (7), `2,486` are a sender, a subject and a
> message count -- content, on a div, changing with every mail, and every
> change mints another job. `Reply to Email` reached five rows that way.
>
> The implicit role separates them at the source: an `<input>` becomes
> `textbox|Username or email` and the `<div>` keeps no role at all.
>
> Only the roles this system actually meets. A full implicit-role table is
> the ARIA spec's own, it is long, and every row of it that nothing here has
> ever seen is a row nobody can check. `password` is deliberately a
> textbox: what keeps the secret out is the redaction over the value, not a
> missing role on the element.

## `nameOf`, [line 139](../../../../../new-chrome-extension/src/page/page-code.js#L139): Function

> Best-effort accessible name: `aria-label`, then every id in
> `aria-labelledby`, then the field's `<label>`, then placeholder, title,
> visible text, and an input button's own `value` (its caption). Never any
> other field's `value`: that is what was typed, which is neither a name nor
> safe to record as one. The recorder wraps this with its credential check,
> so a secret field is never named at all. The authoritative accessible name
> on Steel still comes from the AX tree.

## `labelled`, [line 132](../../../../../new-chrome-extension/src/page/page-code.js#L132): Function

> The text of a field's first `<label>`, for `nameOf` and `labelOf`. A label
> that holds no control is read with `innerText`, exactly as before. A label
> that wraps its control (`<label>Carrier <select>...`) is walked instead
> (`textBeside`), skipping every control, editing host, script and style in
> it (`NOT_LABEL`) and every descendant that is not laid out: `innerText`
> would give "Carrier UPS Ground FedEx", putting the option list -- or a
> wrapped textarea's text -- into the name and the outline (E6 review, M3).
> Keeping `innerText` for the common case leaves every existing locator's
> name unchanged.

## `ext`, [line 713](../../../../../new-chrome-extension/src/page/page-code.js#L713): Function

> The DOM behind every visible component a query matches, through `partOf`:
> for a click, a combobox's trigger arrow when it has one, otherwise its
> input, button or plain element. Measured 2026-09-22: a click on the input
> of "Create Shipment By" never opened the list; a click on the trigger does.
> `perform` and the strategy ladder share the one `partOf`, so the two cannot
> disagree about where a component is clicked.

## `chainOf`, [line 175](../../../../../new-chrome-extension/src/page/page-code.js#L175): Function

> The component a DOM element belongs to (`cmpOf`: walking up from an id
> Ext registered, stripping the `-inputEl`/`-btnInnerEl` suffix Ext gives
> sub-elements, in the element's own window since a frame has its own Ext),
> then its `ownerCt`/`floatParent` chain of xtypes, outermost first. The
> recorder records this as `component.chain`; `score` compares it with one
> `.join(" ") ===`; `hitTest` teaches a query built from it.

## `xpathOf`, [line 184](../../../../../new-chrome-extension/src/page/page-code.js#L184): Function

> A positional path from the document root, with no depth cap. The cap of
> 12 it used to have produced `/div[1]/...` for anything deeper -- a path
> that does not start at the root and resolves to nothing, so a recorded or
> taught xpath for a deep ExtJS control was dead on arrival.

## `boundsOf`, [line 197](../../../../../new-chrome-extension/src/page/page-code.js#L197): Function

> The element's box in page coordinates: the viewport box plus its own
> window's scroll. The recorder records this and `nearest`/`score` compare
> against it, so neither depends on where the page was scrolled at either
> end. Scroll inside an inner container (an ExtJS grid body) is not
> included; ponytail: add the scrolling ancestors' offsets if a recorded
> grid row ever resolves to its neighbour.

## `framePathOf`, [line 202](../../../../../new-chrome-extension/src/page/page-code.js#L202): Function

> The index chain from the top document down to this frame, with each
> hop's own URL where it can be read. `parent.frames[i] === here` is how a
> same-origin ancestor is asked which child this frame is -- `frameElement`
> does the same job one level up, but only within the parent's own origin,
> and a cross-origin parent throws reading it. A cross-origin ancestor's
> `location.href` throws too; `ancestorOrigins`, indexed from the immediate
> parent outward, is the one thing it still exposes -- an origin, not a full
> URL, but enough to tell one frame from a sibling. Shared so a recorded
> `frame_path` and one `hitTest` teaches have the same shape.

## `CANDIDATES`, [line 8](../../../../../new-chrome-extension/src/page/page-code.js#L8): Constant

> What `repair` scores when every named strategy has missed: every element
> a person could plausibly act on, cast as wide as the interactive HTML
> elements plus anything that says `role` or `tabindex` -- an ARIA widget
> built out of `<div>`s, which this deployment's ExtJS grids are. Not
> `document.querySelectorAll("*")`: scoring every node on a warehouse grid
> against the evidence is the same unbounded-walk mistake `viewport`'s own
> code note already tells the story of, paid again here.

## `landmarkRole`, [line 147](../../../../../new-chrome-extension/src/page/page-code.js#L147): Function

> Named landmarks only -- `region`, `dialog`, `alertdialog`, `grid`,
> `treegrid`, `form` -- never every ancestor. A `<div>` wrapper with no ARIA
> role and no landmark tag says nothing about scope; recording it would give
> `within` a chain of unnamed boxes that changes with every unrelated markup
> refactor, which is the opposite of a stable path. `landmarksOf` keeps them
> outermost first and skips a landmark with no name (`ownName`: its
> `aria-label` or `aria-labelledby`), since an unnamed dialog is not a scope
> a runner could name back to a person.

## `STRATEGIES`, [line 754](../../../../../new-chrome-extension/src/page/page-code.js#L754): Constant

> The one order, spec §6.4, with `learned` prepended. `learned` is not one
> of the eight: it is a locator a VERIFIED run already proved finds this
> control, on this build of this page, which is a stronger claim than any
> of the eight can make about themselves -- they are guesses about what
> will still be true, `learned` is a fact about what was. Trying it first
> costs nothing when it is absent (`p.learned` is `null` until a run has
> verified one) and saves seven guesses when it is there.
>
> After it, the eight in the order the spec names: a framework's own
> component identity survives a rebuild that a css path does not
> (`component_chain`, `component`); a scoped role and name survives a
> reorder that an unscoped one does not (`within_role_name`); an author's
> own test id is the most deliberate identity a page can offer
> (`test_id`); the attributes a form control is functionally built from
> outlive a class name (`attributes`); visible text outlives an attribute a
> refactor renamed (`text`); a structural path outlives nothing much, but
> outlives less than a css class list does (`xpath`); the exact selector
> recorded is tried last because it is the most literal, and the most
> literal is what render-order ids like ExtJS's break first (`css_path`).

## `score`, [line 783](../../../../../new-chrome-extension/src/page/page-code.js#L783): Function

> Only what `repair` has not already required: 3 for an exact accessible
> name and 1 for a partial one (the live name contains the whole recorded
> name, not just a word of it), 1 apiece for `name`, `autocomplete` and
> `placeholder`, 2 for an identical component chain (this deployment's
> strongest structural fact), 1 for sitting within `NEAR_PX`. Role and
> landmarks are gates in `repair`, not points; `type` is not scored because
> the role gate already says it.

## `repair`, [line 796](../../../../../new-chrome-extension/src/page/page-code.js#L796): Function

> Snapshot repair. Candidates must have exactly the recorded role and
> exactly the recorded landmark path, a missing role means no repair, and
> the best survivor must clear `REPAIR_THRESHOLD` and lead the runner-up by
> `REPAIR_MARGIN`. Anything less drops to sight, which asks a model to look
> rather than a script to guess. Whether `repair` may run at all for this
> step is decided by its caller, `find` -- this function only ranks
> candidates once asked to.

## `REPAIRABLE_ACTIONS`, [line 4](../../../../../new-chrome-extension/src/page/page-code.js#L4): Constant

> The re-review of 2026-09-24 found repair running for every non-write
> action, including `type`, `select` and a checkbox `click` -- because
> `find` keyed only on `payload.write === false`, and X4 sends that flag
> for every field-entry step, not only reads and navigation. Repair may
> only stand in a wrong element for a step that reads or moves around --
> `click`, `hover`, `scroll` -- where a bad choice costs one more look, not
> a value written into the wrong field.

## `UNREPAIRABLE_ROLES`, [line 5](../../../../../new-chrome-extension/src/page/page-code.js#L5): Constant

> Belt beside `REPAIRABLE_ACTIONS`'s suspenders: a checkbox, radio, switch,
> option or combobox toggles its state on the same `click` a read step
> uses, so the action alone cannot tell a safe click from one that writes.
> These roles are refused regardless of action.

## `find`, [line 808](../../../../../new-chrome-extension/src/page/page-code.js#L808): Function

> The ladder, then repair only when the payload says `write: false`, the
> action is one of `REPAIRABLE_ACTIONS`, and the target's role is not one
> of `UNREPAIRABLE_ROLES`. A payload that does not say is treated as a
> write, so a caller that forgets the flag gets the safe answer. A wrong
> click is a wrong write, and no check after the fact undoes one; so a
> write whose every strategy missed answers `control_not_found` and the
> lane drops to sight.

## `actOn`, [line 842](../../../../../new-chrome-extension/src/page/page-code.js#L842): Function

> `perform`'s own acting half, moved out to module scope: the same click,
> type, select, press, hover, scroll and upload-refusal, on whatever
> element the caller already resolved, unchanged in every particular. X2
> gives it a second caller -- `sroPage.act` -- that resolves through the
> strategy ladder instead of `perform`'s locator list, and the two must not
> answer differently for the same action on the same element, which one
> shared function guarantees and two copies would not. `short` (what a
> field would not take -- see `landed`) is this call's own local now,
> returned rather than left on a variable the caller has to know to read;
> nothing about that was unsafe before, since `perform` already gave each
> of its own calls a fresh `short`, but a function with a return value is
> the ordinary shape and the old one was an artefact of `type`/`act` having
> been inner closures of `perform` rather than functions in their own
> right.

## module, [line 1541](../../../../../new-chrome-extension/src/page/page-code.js#L1541): Comment

Code: `globalThis.sroPage = sroPage;`

> A plain assignment, deliberately, and not `Object.defineProperty` with
> `writable: false, configurable: false`. That was tried: it stopped a bare
> `window.sroPage = fake`, and nothing else -- the page can still write
> `window.sroPage.perform = fake`, since only the property holding the
> object was frozen, never the object itself; a page that defines `sroPage`
> first, non-configurable, makes THIS assignment throw (caught, silently,
> by the `try`/`catch` re-injection needed anyway), and its object answers
> every later command with no sign anything is wrong. The one thing frozen
> actually stopped -- a plain overwrite, after this file has already run --
> is the least likely of the three.
>
> It also cost more than it bought. `sroCall` re-injects this file on every
> command, into whatever document the tab is currently showing, and a
> non-configurable `sroPage` cannot be replaced by a second injection into
> the same document -- only left in place, via the same `try`/`catch`. An
> ordinary BY tab stays open for hours; an extension reload or update
> mid-shift left that tab answering with the sroPage it loaded an hour
> ago, silently out of step with the worker sending it payloads shaped for
> the version that replaced it -- exactly the two-versions-at-once state
> "one page-code source" (spec §6.4) exists to rule out. A plain assignment
> replaces `sroPage` on every injection, which is what keeps a document
> current and is worth more than a protection that does not protect.
>
> MAIN world is the page's own `window`, so this line is inherently
> tamperable by whatever else runs there -- a third party's script,
> including one that runs before this one ever does, which injection always
> risks since nothing here is a persistent content script. That is not
> hardened here and is not meant to be: no property on a page's own global
> can be defended against the page it belongs to. What holds instead is
> downstream of this line entirely -- `repair_drift`, the lane ladder and
> the verified-write ledger judge a step by whether the WMS actually changed
> the way the run expected, not by trusting whatever answered `sroPage`'s
> name.

## `perform`, [line 942](../../../../../new-chrome-extension/src/page/page-code.js#L942): Docstring

> Find a control by the first locator that resolves, act on it, and say which
> one worked.
>
> The strategies mirror `infrastructure/steel/ui_driver.py` deliberately: the
> same skill, replayed on the server or in the operator's own browser, has to
> find the same control or the two mediums are not interchangeable.

## `perform`, [line 942](../../../../../new-chrome-extension/src/page/page-code.js#L942): Comment

> The rung's own scope first, then the command's.
>
> Every locator the backend sends carries `within`, and until 2026-09-22
> this read only the payload's -- so a rung scoped to a grid view matched
> the first such element anywhere on the page, and the docstring on
> `Locator` promising the scope was read "at the wire" was describing a
> field nothing read. (`within`)
>
> The trigger of a field that has one -- the arrow beside a dropdown.
>
> Ext keeps it in two shapes across versions: `triggerEl` is an Element on
> some and a CompositeElement of several on others, and newer ones carry a
> `triggers` object keyed by name. Read rather than assumed, and null where
> the component has none, which is every ordinary button and text box.
> (`triggerOf`)
>
> Which element of a component a command has to land on.
>
> A combobox's `inputEl` is its text box. Clicking that focuses the field
> and nothing else: the list opens from the TRIGGER, a separate element
> beside it. Measured on the deployment 2026-09-22 -- `Click the Create
> Shipment By dropdown` landed every time (`ok: true, matched_by:
> component`), the list never opened, and the step after it had no option
> to select. The operator's own recording of that click names the trigger:
> `div#ext-gen2855`, at `.../td[3]/div[1]` inside the field's own table,
> xtype `combobox`. We were resolving the right control and then handing
> the one part of it that cannot do the job.
>
> Only for a click, and only where a trigger exists. `type` and `select`
> want the input they always wanted.
>
> ponytail: a click recorded merely to FOCUS an editable combobox now opens
> its list instead. Nothing on this deployment records one -- a step that
> focuses is followed by a `type`, which focuses anyway -- and telling the
> two apart needs the recorded target's tag in the payload, which the plan
> does not carry today. Add it if a stray open list is ever seen. (`partOf`)
>
> Ask the application, not the DOM. Its ids are assigned in render order, so
> `#ext-gen4443` is a different control after a reload. (`resolve`, case
> `"component"`)
>
> Only elements whose *own* text is the query: without that, every
> ancestor up to `<body>` contains the words and the match is the page.
> (`resolve`, case `"text"`)
>
> What the field would not take, where it took less than it was given.
> Set by `type` and read into the reply; null when the box holds exactly
> what it was asked to. (`short`)
>
> What the field ended up holding, against what it was asked to hold.
>
> The browser truncates, and it does it silently and BEFORE the request.
> `Warehouse.Description` on this deployment stops at about 28 characters
> with no error and no warning -- observed live, §5 of the knowledge base --
> so the shortened value is what goes into the body, comes back from the
> read, and appears in the photograph. Every belt the run has agrees,
> because every one of them is comparing the record to itself. The only
> moment the difference exists is here, in the page, between what was asked
> for and what the box will take.
>
> A prefix that is shorter is truncation: data is gone. Anything else --
> trimmed spaces, a case the field normalised, a character it refused -- is
> a difference worth saying and not worth stopping for. (`landed`)
>
> Through the prototype's own setter, so a framework that watches the
> property (React and its imitators do) sees the change it is listening
> for rather than a value that appeared without one. (`type`, `put`)
>
> A keystroke at a time, because this WMS's combo boxes filter on them: a
> value assigned whole leaves the picker closed and the field unvalidated,
> which is how a replay silently fills a form nobody accepts. (`type`, the
> per-character loop)
>
> Read back before the field is left, because leaving it is what commits
> whatever it decided to keep. (`type`, `short = landed(...)`)
>
> And then LEFT, which is when a field commits.
>
> A framework keeps its own value and takes the DOM's when the field is
> left -- ExtJS does, and it is not alone. Typing without leaving fills
> the box on the screen and not the model behind it, so the form looks
> right to a person and to a photograph, and the application validates
> the empty value it still holds.
>
> Measured on the deployment, 2026-09-17 at 23:40: `run_6ddc89d5` typed
> GT2, the screen showed GT2, and the Save came back "a validation error
> on Customer Type". A person never hits this because clicking the next
> control blurs the last one; a synthetic click does not move focus, so
> nothing here ever left the field. (`type`, `el.blur()`)
>
> `blur()` fires these natively, and dispatching them costs nothing and
> covers a field whose own `blur` has been overridden -- which is a thing
> component libraries do. (`type`, the `focusout`/`blur` dispatches)
>
> The whole sequence, not `el.click()`: this application binds
> `mousedown` on half its controls and never sees a bare click. (`act`,
> case `"click"`)
>
> A file input's value cannot be set by script, by design, in every
> browser. Saying so is the honest answer; pretending it worked would
> have the run verify against a form that was never filled. (`act`, case
> `"upload"`)
>
> A probe looks and does not touch.
>
> The control may be in any frame of the page, so the search runs in all of
> them -- and a search that acted where it looked would click in every frame
> that happened to match. So the frames answer where the control is, the
> worker picks one, and only that frame is asked to act. (`payload.probe`)
>
> What this control IS, so the job can be told and stop re-deriving it.
>
> A step whose recorded identity has rotted is found by a rung further
> down -- text, a css path, a point on a picture -- and until now that
> discovery lived for exactly one command. The next run climbed the same
> ladder and paid for the same model calls to reach the same control.
> Measured on the deployment, 2026-09-17: the rung that looks at a picture
> worked out "Customer Types is under Partners" three times in one
> afternoon and the job knew no more at the end of it than at the start.
> (`naming`)
>
> The locator that actually worked, for the job to keep. (`matched`)
>
> What the box would not take. Null on every step that is not a type
> and on every field that took what it was given. See `landed`: this
> is the only moment the difference between what was asked for and
> what the warehouse will hold actually exists. (`short`, in the reply)
>
> Defined HERE, inside the function that is injected, and this is why.
>
> `chrome.scripting.executeScript({func})` serialises that function and
> nothing else: a helper sitting beside it in this module does not exist in
> the page. Calling one throws a ReferenceError there, and since Chrome 117
> the promise RESOLVES with `{result: undefined, error}` -- so a call that
> blew up arrives at the run as no answer at all.
>
> Measured on the deployment across 2026-09-16 and 17: every UI step ever
> attempted on the warehouse host failed with "the page did not answer",
> and the only one that ever held was on a mailbox. The difference was not
> the page. On the mailbox a locator MATCHED, so this line was never
> reached; on the warehouse nothing matched, the near-miss report was asked
> for, and the report is what exploded. The step that was meant to explain
> the failure was the failure. (`nearMisses`)
>
> A near miss and not a catalogue: something the step's own words are
> part of, or that is part of them. (`nearMisses`, the `wanted.some(...)` filter)
>
> Said in the DETAIL as well as the field, because the detail is what
> travels: the socket adapter keeps a reply's `kind` and `detail` and drops
> everything else, and the detail is what reaches the run's own record and
> the model asked to rescue the step. (`also`)
>
> The locators that were attempted, as data rather than prose.
>
> `detail` has carried this as a sentence since it was written, and a
> sentence is what a person reads, not what a record keeps: `_result` in
> the backend keeps `error_kind` and drops the rest, so a
> `control_not_found` in `workflow_run_steps` said only that something was
> not found. On 2026-09-21 the same step refused twice -- KKYT on the 20th,
> SMK1 that night -- and answering "which locator, in which frame, against
> what" took five rounds of pasting into a console with the dialog held
> open by hand. The browser knew all of it at the time and threw it away.
> (`result: { tried: ... }`)
>
> What the page DOES have where the step was looking.
>
> "no control matched: role_and_name=button|Save, css_path=..." says
> what was tried and nothing about what is there, which is the fact a
> person reading the run -- or the model asked to rescue the step --
> has to have. A screen whose Save became "Save and close" reads as a
> screen with no Save at all.
>
> Deliberately not acted on here. A near miss is evidence, and this
> extension does not get to decide that a control with a different name
> is the one the operator used: `repair_drift` in the backend already
> settles that question from verified runs that agree more than once,
> and never from one page's guess. (`nearby`, in the error)

## `performAt`, [line 1116](../../../../../new-chrome-extension/src/page/page-code.js#L1116): Docstring

> Act at a point, because the gesture came from pixels rather than from a
> control the demonstration identified. Coordinates are CSS pixels in the
> viewport -- the same space `viewport` reports, so the picture the model
> was shown and the point it answers with measure the same thing.
>
> What the field would not take. See `landed` in `perform`: the same
> rule, and the same reason it can only be known here. (`shortAt`)

## `performAt`, [line 1116](../../../../../new-chrome-extension/src/page/page-code.js#L1116): Comment

> A point inside a frame lands on the `<iframe>` itself from this document:
> the events below would fire on the frame element and reach nothing, and
> the answer would still say performed. The control is in a document this
> script is not running in, which is a control it did not find.
>
> The control is in a document this script is not running in. Firing the
> events here would hit the frame element, reach nothing, and report
> `performed` -- so instead this says WHERE, and the worker asks that
> frame the same question with the point moved into its coordinates.
>
> Measured on the deployment, 2026-09-17: the rung that looks at a picture
> finally pointed at a control and got "that point is inside a frame". The
> warehouse application runs in one, so every point in the picture lands
> on the frame element from the top document -- which made the picture
> rung useless on the one system it exists for. (the `IFRAME`/`FRAME`
> branch)
>
> What the worker needs to ask the frame itself: where the frame sits
> in this document, and what it is showing. (`error.frame`)
>
> Focused explicitly, and typed into the element under the point rather
> than into `document.activeElement`. A synthetic click does not move
> focus -- only a trusted one does -- so reading activeElement here
> found whatever the operator had last focused, or `<body>`: the
> keystrokes went into some other field, or nowhere at all, and the
> command still answered `performed`. (case `"type"`)
>
> Through the prototype's own setter, for the same reason `perform`
> does it: a framework watching the property has to see the change.
> (case `"type"`, `put`)
>
> Read back before the field is left, because leaving it is what
> commits whatever the box decided to keep. The browser truncates
> silently and BEFORE the request, so this is the only moment the
> difference exists -- see `landed` in `perform`. (case `"type"`,
> `shortAt = ...`)
>
> And left, so the framework behind the box takes the value. See the
> same lines in the locator path's `type`. (case `"type"`, `el.blur()`)
>
> The element at the point, focused first: the same trap as `type`, and
> an Enter delivered to `<body>` submits nothing. (case `"press"`)
>
> What the point turned out to be. This is the expensive discovery --
> a model looked at a picture to find it -- and naming it is what lets
> the next run find it with a locator instead. (`control`, in the reply)

## `screenSize`, [line 1257](../../../../../new-chrome-extension/src/page/page-code.js#L1257): Docstring

> How big the screen is and where it is, and nothing else.
>
> The cheap half of `viewport`, for when the whole of it cannot be had:
> three property reads, no layout, no selector. The picture is what the rung
> that looks actually needs -- the digest beside it is a help, and a help that
> costs the command its deadline is not one.

## `viewport`, [line 1266](../../../../../new-chrome-extension/src/page/page-code.js#L1266): Docstring

> The visible controls and where they are, plus the size of the space those
> coordinates are in.
>
> Normalised to 0-1000 because that is the space the vision model answers in,
> and measured in CSS pixels because that is the space `performAt` acts
> in. A picture measured in device pixels and a click measured in CSS pixels
> are out by the display's scale factor, which on any retina screen is a click
> halfway up the page.

## `viewport`, [line 1266](../../../../../new-chrome-extension/src/page/page-code.js#L1266): Comment

> Bounded, because this used to walk the whole document and the document is
> a warehouse grid.
>
> `getBoundingClientRect` forces layout, and it was called on every match of
> a selector that includes `.x-grid-cell` -- tens of thousands of cells on a
> Blue Yonder grid, each one a synchronous reflow -- and then 200 of the
> answers were kept and the rest thrown away. Measured on the deployment,
> 2026-09-17 at 17:30: `run_0c3bd2ae` step 2 failed
> `no screen to look at: timeout: the browser did not answer within 20s`,
> and the same timeout had been read as three different faults across the
> afternoon -- a refused screen, a tab that was not visible, my own console
> tab stealing focus. None of them. The page simply could not be measured
> in the time the run was willing to wait.
>
> Two limits and they are different limits. `K_LOOKED_AT` bounds the WORK --
> how many elements are measured at all, which is what costs the time.
> `K_NAMED` bounds the ANSWER, and was the only one here before.
>
> Where this document sits in the picture the model is shown.
>
> The warehouse application runs in a frame -- `performAt` learned
> that the hard way -- and a frame measures itself from its own top left.
> Names taken from inside it were being reported as though the frame were
> the window, which puts a control a hundred pixels below the nav bar at the
> very top of a picture where the nav bar is.
>
> `frameElement` is readable only from a same-origin parent. A frame from
> somewhere else keeps its own coordinates, which is the best that can be
> had from inside it and is still better than no names at all. (`dx`/`dy`/
> `acrossX`/`acrossY`, and the `try`/`catch` around `window.frameElement`)
>
> A dropdown's items are none of these.
>
> Measured on the deployment 2026-09-19: `Delete a Customer Type` failed
> five times running on "Opens the filter dropdown", every one of them with
> the control FOUND and pressed -- the screen belt read a digest with the
> portal's top bar in it and concluded nothing had opened. ExtJS floats its
> combo list as a `div` of `li`s appended to the body, and not one of them
> is an input, a button or a link, so no budget and no walk order could ever
> have described the thing the step exists to open.
>
> By ARIA role first, which is the web's own way of saying "this is a thing
> to choose" -- and `.x-boundlist-item` beside it for the same reason
> `.x-grid-cell` is already here: the one application this system is pointed
> at renders its lists before it labels them. (`all`, the selector)
>
> What the page is SAYING, before what it is offering.
>
> The digest was names of controls and nothing else, so a page whose whole
> message was a dialog produced a digest with the dialog's buttons in it and
> not a word of what the dialog said. Measured on the deployment, 2026-09-17
> at 23:05: `run_21b92747` filled the form on the page and the Save came
> back "An exception dialog appeared and the record has not been created" --
> the model's paraphrase, because the screen text it was given had the
> dialog's OK button and none of its sentence.
>
> By ARIA role, which is the web's own way of saying "this is the page
> talking to you" and belongs to no vendor. First in the digest because a
> message is the thing a reader wants first, and a handful of elements, so
> it costs nothing against the budget below. (the `[role=alert]` loop)
>
> Both ends of the document, not the first two hundred elements of it.
>
> A page is written header-first, so walking it in order spends the whole
> budget on the application's own chrome. Measured on the deployment,
> 2026-09-17 at 23:40: the digest for a screen showing an error dialog was
> "Search: 865,18 Workstation: 681,18 SG: 625,18 ..." -- the top bar, and
> not one word of the dialog the run had just failed on.
>
> A dialog is appended to the body, so it is at the END. Half the budget
> from each end catches both what the screen is FOR and what it is saying,
> and neither is reachable by reading the other.
>
> Not front-then-back: the ANSWER is capped too, and two hundred names of
> header controls fill it before the walk ever reaches the other end. Taking
> one from each end in turn means a page longer than either budget is still
> described from both, which is the whole point. (`order`, the front/back walk)
>
> Off the screen entirely. This is what the digest is FOR -- what the
> operator is looking at -- and the coordinates beside each name are
> fractions of the viewport, so a row scrolled a thousand pixels below it
> was being described at `y: 4300` in a space that ends at 1000. Wrong as
> well as slow. (the `rect.bottom < 0 || ...` guard)

## `csrfToken`, [line 1342](../../../../../new-chrome-extension/src/page/page-code.js#L1342): Docstring

> The one header this extension knows how to read live: Blue Yonder keeps
> its write token in a page-level JS global, never in a cookie, so a
> recording can only ever capture a value the recorder correctly redacts.
> Runs in the MAIN world -- `Ext` is the page's own framework object, not
> reachable from the isolated world `send` runs in -- and answers
> `null`, never throws, when the page has no such global to read.

## `requestedWith`, [line 1346](../../../../../new-chrome-extension/src/page/page-code.js#L1346): Docstring

> What this page marks its own XHRs with.
>
> Read off the page first and only then defaulted, which is the difference
> between sending what the application sends and sending what a spec says it
> ought to. Blue Yonder's ExtJS puts it on `Ajax.defaultHeaders` beside the
> CSRF token; a framework that names itself instead would be sent its own
> name, and one that sets nothing gets the value every XHR library has used
> for twenty years.
>
> Not a credential, and that is why it can be defaulted at all. The recorder
> strikes it out because it sits in `SECRET_HEADERS` beside the real ones, so
> the recording carries a marker and not a value -- and a write that arrives
> without it is refused by an application that expects it before it is ever
> routed. Nothing is carried from the backend either way: the name is asked
> for, the value is found here.

## `send`, [line 1352](../../../../../new-chrome-extension/src/page/page-code.js#L1352): Docstring

> Send a request from a tab that is already on that origin, so the operator's
> own session applies -- which is why a skill can be replayed against a system
> this deployment holds no credentials for at all.
>
> Runs in the isolated world. Same origin, same cookie jar, but the page's
> patched `fetch` is not the one called here: a replayed request must not
> arrive in the evidence plane looking like something the operator did.

## `send`, [line 1352](../../../../../new-chrome-extension/src/page/page-code.js#L1352): Comment

> Bounded, and it says how long it took either way.
>
> `TypeError: Failed to fetch` is what a browser says for every one of: the
> host did not resolve, the connection was refused, CORS refused the
> response, and the document running this was torn down mid-request. Four
> faults, one sentence, and no clue which -- so the one thing that tells
> them apart, how long it took to fail, was being thrown away.
>
> Measured on the deployment, 2026-09-17: `run_e1ff6362` step 6 failed
> `unreachable: TypeError: Failed to fetch`, and the only reason anybody
> knows it stalled for 54 seconds first is that two log lines on the SERVER
> happened to bracket it. An instant failure is a refusal; a long one is a
> connection nobody answered. Those want different fixes.
>
> `timeout_ms` is the command's own where it carries one, because a call has
> no business outliving the deadline the run is waiting on. (`K_CALL_MS`,
> `giveUp`)
>
> And WHICH of the four it was, where one cheap question can say.
>
> The comment above lists them: the host did not resolve, the connection
> was refused, CORS refused the response, the document was torn down. It
> leaves out the one that is commonest in a warehouse and is not a
> network fault at all -- the session expired, the endpoint answered 302
> to an identity provider on another origin, and `redirect: "follow"`
> walked the fetch across an origin boundary it is not allowed to cross.
> Same `TypeError: Failed to fetch`, and nothing about it is unreachable.
>
> Measured on the deployment 2026-09-21. `GET /data/WM/wm/customerTypes`
> answered 200 with fifty records at 18:30 and `Failed to fetch after
> 341ms` at 20:10, with the operator's own machine reaching that exact
> address in 12ms and being answered 302. Between the two, they had been
> signed out. The panel said "unreachable", which sent everybody looking
> at the network.
>
> Only on the failure path, and only one request: `redirect: "manual"`
> does not follow, so a redirect comes back as an opaque response instead
> of an exception. A run's own replayed calls keep following redirects,
> because a POST that legitimately redirects is a POST that worked.
>
> `redirect: "manual"` hands back an opaque response for a redirect
> instead of walking it to another origin and throwing. `opaqueredirect`
> is the whole of the signal and no header of it is readable, which is
> fine: that it redirects at all is what says the data is not there.
>
> Never allowed to throw. A diagnostic that can fail the thing it is
> diagnosing is worse than no diagnostic. (the redirect probe, `redirected`)
>
> The elapsed time and whether the browser thinks it has a network at
> all: the two facts that tell a refusal from a stall, and neither of
> them costs anything to collect. (the final `unreachable` detail)

## `hitTest`, [line 1471](../../../../../new-chrome-extension/src/page/page-code.js#L1471): Function

> Sight's other half: `viewport` tells the model where things are, and a
> model's answer is a point, which is only useful to a future run if it
> becomes a locator strong enough to skip sight next time. Descends into
> nested frames first (`elementFromPoint` never crosses a frame boundary on
> its own), moving the point into each frame's own coordinates. A frame
> whose document cannot be read (cross-origin) ends the descent with
> `unreachable: "cross_origin_frame"`, the frame's path and the point in its
> coordinates, so the caller can ask again inside that frame.
>
> Every answer carries `frame_path` (`framePathOf`, the recorder's own
> shape). The strongest identity that resolves to EXACTLY this element and
> nothing else, in the order teaching wants: a component query (itemId,
> then the last two links of the chain, then the whole chain) matching
> exactly this component; then role and name; then a unique test id; then
> an xpath -- and only an xpath that finds this element, else `null`, since
> a locator that finds nothing teaches a future run to fail.
>
> A reachable answer also carries a `pin`: the hit element is kept under it
> in that frame's own `__sroHits` map, so `holds` can later ask whether the
> step's RECORDED locator resolves to the element this point hit (X7 review,
> non-write sight ruling). ponytail: the map lives as long as the document
> and gains one entry per sight point; clear it per step if a page ever
> lives through enough sight steps for that to matter.

## `act`, [line 1436](../../../../../new-chrome-extension/src/page/page-code.js#L1436): Function

> Resolve, act through `actOn`, and pin what was touched: `pin` is a random
> token and `globalThis.__sroActed` holds the element under it, so `holds`
> can check that exact element without resolving again. `actOn` scrolls the
> element into view, which moves every box on the page, so a second
> resolution could pick a different duplicate. `repaired` says the control
> came from `repair`, which the caller must treat as unconfirmed. A throw
> from acting (typing into something that is not a field) becomes
> `not_actionable` rather than escaping the answer's shape.

## `settingOf`, [line 222](../../../../../new-chrome-extension/src/page/page-code.js#L222): Function

> The value half of an after-state, and structurally never free text
> (E5 ruling, 2026-09-25). Only a control whose value IS a state records one:
> a checkbox, radio or switch as `checked` / `unchecked`, read off its checked
> state and never its `value` attribute (which is `on` for every checkbox, so
> a later "is it ticked" check would always pass); a select as the visible
> label of what is chosen. Everything else -- every text-type input, a
> textarea, a contenteditable, a `role=textbox|searchbox|combobox` entry, a
> file input, a button, a custom element's host -- is `null`.
>
> Decided by what the control is and not by whether it looks secret, because
> "looks secret" is judged at the moment the state is read: a password field a
> "show" toggle has switched to `type=text`, and a password input inside a
> custom element's shadow root whose host exposes `.value`, both passed that
> check and leaked what was typed. A text control has no value here at all,
> so neither shape can. `isSecretField` still gates a select named like a
> credential -- in the recorder, which wraps this (`recorder.js`'s
> `stateOf`).
>
> Moved here from `recorder.js` (X4 review I8) so `stateOf` below -- and so
> `holds` -- read a checkbox as `checked`/`unchecked` and a select as its
> chosen label, exactly as the recorder stored it. Before, `holds` compared
> the raw `el.value` (`on`, the option's value) against the recorded word,
> so every checkbox, radio, switch or select step waited out its deadline
> and failed. `undefined` means "not a state control"; `null` means a select
> with nothing chosen.

## `stateOf`, [line 823](../../../../../new-chrome-extension/src/page/page-code.js#L823): Function

> The state `act` answers and `holds` compares. A state control reads through
> `settingOf`, in the recorder's words; any other control reads its live
> `value` (a password never), because the UI lane checks a typed field
> against the value THIS run typed, not against the recording, which keeps
> no free text. A removed element reads as the recorder reads one:
> `{value: null, visible: false, enabled: null}`, so a recorded "gone once
> done" holds and a recorded "still shown" does not.

## `holds`, [line 1453](../../../../../new-chrome-extension/src/page/page-code.js#L1453): Function

> Whether the element `act` pinned (`payload.pin`) matches
> `payload.expect`, read through `stateOf` -- the recorder's vocabulary, so an
> element that has gone reads as not visible rather than refusing outright.
> Answers `{repaired}` when it holds and `null` when it does not or the pin
> is unknown -- truthy exactly when it holds, so a `wait_for_function` on it
> waits for the right thing. Never re-resolves. A password field compares
> only `visible` and `enabled`: its value is never read back. A select also
> holds when the expected value is the chosen option's `value`: `act`
> accepts an option by value or by text, so a run's parameter may name
> either, while the recording names the label.
>
> A pin `hitTest` gave (sight) is stricter: the payload's recorded locator
> is resolved with `find`, never repaired (the sight lane sends no
> `write: false`), and holds only when it resolves to exactly the hit's
> nearest actionable element, `hit.closest(CANDIDATES)` -- so a click on a
> button's inner span confirms the button, while a container locator (a
> grid, a tab list) never confirms a click on one of its children, such as
> the wrong row (X7 re-review N1). The state is then read from that
> recorded control. So the right value typed
> into the wrong field, or a click on any element that is merely visible
> and enabled, never holds.

## `signals`, [line 1524](../../../../../new-chrome-extension/src/page/page-code.js#L1524): Function

> S6: what the page's own inputs say about it, never what was typed into
> them. Only inputs `shown` passes count -- the one visibility rule this file
> has (box, `visibility`, `display`), so a `visibility:hidden` anti-autofill
> decoy is not a signal (S6 fix round 1, I2). `autocomplete` is read as the
> HTML token list it is, split on whitespace and lower-cased
> (`section-login username webauthn` is three tokens; I3), and every shown
> input's tokens are returned de-duplicated; the domain decides which count.
> `password` is a shown password input that is not a `new-password` field: a
> "create user" or "change password" form's new-password box asks for no
> credential (I5). Structure only: no value is read off any control, matching
> the sign-in capture rule (E7 security ruling, spec §5.6) that a sign-in
> page's evidence never carries what was typed into it.

## `sroPage`, [line 1433](../../../../../new-chrome-extension/src/page/page-code.js#L1433): Function

Code: `const held = f.el && !isSecretField(f.el) && typeof f.el.value === "string" ? f.el.value : null;`

> Counts the controls a payload names without acting, and reads `held`: the
> DOM value the found control holds (an input's value, a select's chosen
> option's value), `null` for any credential field (`isSecretField`, the
> recorder's own rule) or a control with no string value. A
> composed field's save key must carry exactly that value (X10a review I1/I2).
> The answer is read in memory by the runtime and never stored.

## `readers`, [line 10](../../../../../new-chrome-extension/src/page/page-code.js#L10): Constant

> Its `SECRET_WORDS` line is GENERATED: `make gen-recorder` rewrites it from
> `sensitivity.SECRET_TOKENS` (`page_code_source`); never edit it by hand. There
> is one list, on the Python side; this used to be a second copy that drifted.
> `test_generated_scripts_are_current` fails when it is stale.
>
> Whole words, not substrings. Matched loosely this ate ordinary business data
> -- an address search box came back as «secret», so the demonstration could not
> say what was searched for, the model narrating it described a hole, and the
> value that would have become a parameter was gone. A redaction that eats
> business data is how people learn to switch it off.

## `readers.wordsOf`, [line 22](../../../../../new-chrome-extension/src/page/page-code.js#L22): Function

> `([A-Z]{2,})([A-Z][a-z])` and not `([A-Z]+)(...)`: the wider rule splits the
> lone N off `pickNPassAutoDropLocation` and leaves `Pass` bare, blanking a real
> warehouse field. Two-or-more needs three capitals in a row before it cuts, so
> `SAMLResponse` splits and `NPass` does not. Measured over 3,270 real field,
> header and query names: this rule changes none of them.

## `readers.isSecretField`, [line 82](../../../../../new-chrome-extension/src/page/page-code.js#L82): Function

> The one credential-field rule, shared by the recorder (through the readers
> splice) and the page code. A field matched here never has its value read: the
> recorder drops it before it leaves the page, `stateOf` answers `null`, `holds`
> does not compare it, and `resolve`'s `held` is `null` -- so a password, a card
> number, a card code or a one-time code never reaches the backend through a
> runtime answer either (X10a re-review N1). `type=password` and the
> autocomplete tokens are what the page itself says is a credential, the only
> signal here that is a decision rather than a guess; the name, id, aria-label
> and placeholder are judged by the secret words, and so are the Ext `data-ref`
> and the text of what `aria-labelledby` points at. A word counts alone, as two
> or three adjacent words read as one ("login code", "one time code"), or as the
> whole name -- never a bare "code", which is a job field ("Customer type code",
> "Postal code"). An input the page draws as dots (`-webkit-text-security`) is a
> secret whatever it is called. The credential words are generated from
> `sensitivity.SECRET_TOKENS`.

## `OUTLINE_OPTIONS`, [line 232](../../../../../new-chrome-extension/src/page/page-code.js#L232): Constant

> The screen outline (`outlineOf`) keeps a control's option labels only when
> it has at most this many. A short list is the control's vocabulary -- the
> departments, the carriers -- and is what a run needs to fill it by label. A
> list over the cap is data: customers, SKUs, locations, rows from the
> tenant's own tables. It is dropped whole (`options: null`), never cut to its
> first 25, so no part of a data list is kept. The server applies the same cap
> (`outline.py`, `K_OUTLINE_OPTIONS`).

## `OUTLINE_FIELDS`, [line 233](../../../../../new-chrome-extension/src/page/page-code.js#L233): Constant

> Caps on what one outline may carry: at most 80 fields, headings or buttons,
> 120 characters per string (`OUTLINE_TEXT`) and 10 messages
> (`OUTLINE_MESSAGES`). They bound each part; `OUTLINE_CHARS` bounds the
> whole. The server applies the same caps to whatever a client sends.

## `OUTLINE_CHARS`, [line 236](../../../../../new-chrome-extension/src/page/page-code.js#L236): Constant

> The most one outline may weigh, serialized: 16 KiB. An outline rides on its
> gesture record, and `observe.js` refuses any record over 128 KiB
> (`MAX_GESTURE_CHARS`) -- the whole gesture, not just the outline. At the
> per-part caps alone one outline measured about 100 KB (80 selects of 25
> long options), and a record carries up to `OUTLINES_PER_GESTURE` (3) of
> them, so the caps were never enough (E6 review, I2). Three outlines at
> 16 KiB leave well over half the limit for the gesture itself. `fitted`
> trims to it; the server applies the same cap (`K_OUTLINE_CHARS`).

## `NOT_VOCABULARY`, [line 238](../../../../../new-chrome-extension/src/page/page-code.js#L238): Constant

> A string holding a URL (`://`), a query-style pair (`name=value`), a run of
> 16 or more hex digits, or a run of 32 or more word characters is never
> outline vocabulary, and is how a token travels: an OAuth callback, an
> `access_token=` a page prints, a reset link's path ("Open /reset/9f8e...b1a0
> to continue", E6 review M4). No label, heading or option name is such a
> run. It is dropped whole in the page; the server drops it again, and also
> drops anything `redact_url` or `redact_shapes` would change.

## `labelOf`, [line 239](../../../../../new-chrome-extension/src/page/page-code.js#L239): Function

> What a field is called, from the page's words about it and never from the
> control itself: `aria-label`, `aria-labelledby`, the `<label>` bound to it,
> then `placeholder` or `title`. Unlike `nameOf` there is no `innerText`
> fallback. A contenteditable's `innerText` is exactly what the operator
> typed, and a field's own text is its value -- the first E6 stored the
> accessibility tree, whose names carried both (review 2026-09-25). The
> `<label>` is read through `labelled`, so a label that wraps its control
> never takes in the control's text.
>
> **Ceiling:** a label the page itself rewrites from a typed value (an
> `aria-labelledby` pointing at a mirror) is kept. There is no echo rule any
> more (see `outlineOf`); structure cannot tell such a label from any other.

## `requiredOf`, [line 245](../../../../../new-chrome-extension/src/page/page-code.js#L245): Function

> Whether the PAGE says this field must be filled: `aria-required`, the HTML5
> attribute, or a star at the end of its label; `null` where it says nothing.
> Moved here from recorder.js so the recorder's `describe` and the outline
> read it with one text. It reads `labelOf`, not the recorder's `label`, so a
> contenteditable's typed text is never searched for a star.

## `insideEditor`, [line 253](../../../../../new-chrome-extension/src/page/page-code.js#L253): Function

> An element inside an editing host (a rich-text editor) is typed content, not
> page structure: an `<h2>` the operator wrote in a notes editor is a heading
> of their text. The outline skips every such element.

## `fitted`, [line 255](../../../../../new-chrome-extension/src/page/page-code.js#L255): Function

> Trims an outline to `OUTLINE_CHARS`, deterministically and in this order:
> option lists from the last field back, then whole headings, landmarks,
> messages and buttons from the end, then fields last. Option lists go
> first because they are the bulk and the least of what a run needs: the
> field is found by its label, and its choices can be read off the live page.
> Fields go last, and headings first among the rest, because a field is what
> a run fills by label (X10): a field missing from the outline reads as a
> field that does not exist, while a dropped heading or landmark only costs
> orientation. The size is kept as a running total (each removal subtracts
> its own serialized length) rather than re-serializing the outline per
> step. An outline is never refused for size, so it never costs its gesture.

## `outlineOf`, [line 275](../../../../../new-chrome-extension/src/page/page-code.js#L275): Function

> A compact description of the screen: headings, named forms and dialogs,
> fields (role, label, required, small option lists), button names, and the
> ROLE of each message on screen (`alert`, `status`, and `invalid` for the
> element an `aria-invalid` field points at). Never a value, never free page
> text: a mirror `<div>` is not read at all, and every string passes
> `NOT_VOCABULARY`. Only what is laid out (`getClientRects`) is described.
>
> **Messages keep their role only** (E6 ruling, 2026-09-25). A message is the
> one part of a screen that pages build from what was typed: "Code 483920
> has expired" after the box is cleared, "Verifying 483920" from six
> one-digit boxes, a debounced "Checking 4839..", "You typed ..." from a
> password in a closed shadow root. The first outline compared message text
> with the controls' current values, and real Chrome showed all four
> reaching storage: by the time the message is read the value is gone,
> split, partial, or out of reach. So a message is recorded as "an alert
> appeared" and nothing it said. What an error MEANT comes from the server
> response the step received, which is stored, redacted, with the call. A
> message element with no text is not a message and is skipped.
>
> **No echo rule.** Headings, labels, landmarks, buttons and options are kept
> even when they equal something the operator typed. The rule that dropped
> them removed whole fields ("Pick Location" after "pick" was typed),
> headings, and the chosen option from its own list, and bought no privacy:
> a non-secret typed value is stored in its own `type` gesture anyway.
> **Ceiling:** a page that writes a secret into a heading, a button, a label
> or a dialog's name is not caught; structure cannot tell such a string from
> the page's own words.
>
> **Cost ceiling** (E6 review, M6): `outlineOf` took 19 ms on a page of about
> 6,000 elements. It runs synchronously in the capture phase of every
> gesture, and again whenever the text inside an `alert` or `status`
> changes, so a ticking status re-outlines the page on every tick (the
> result is deduplicated, the work is not). Upgrade path: debounce the
> observer's re-reads, or read only the changed subtree, if a real page
> shows the cost.
>
> It replaced tree capture (spec §4.6): the extension no longer attaches
> `chrome.debugger`, and Steel reads the same outline from the live page
> with `sroPage.outline()` -- one text, spliced into the recorder with the
> other readers.

## `outline`, [line 1536](../../../../../new-chrome-extension/src/page/page-code.js#L1536): Function

> `outlineOf(document)` for Steel (X10): the screen as the recorder would
> send it, read on demand from the live page.

## `fullNameOf`, [line 321](../../../../../new-chrome-extension/src/page/page-code.js#L321): Function

> The accessible name, read from the DOM alone: aria-labelledby, aria-label, a label element, title/placeholder/alt, and the element's own text only for roles the platform names from content. The full accessibility-tree computation needs the debugger permission this extension does not ask for. A credential field returns null.

## `siblingOf`, [line 339](../../../../../new-chrome-extension/src/page/page-code.js#L339): Function

> The position among siblings of the same tag and the same role, so a field's position does not move when a label or an unrelated control is added beside it.

## `choiceOf`, [line 347](../../../../../new-chrome-extension/src/page/page-code.js#L347): Function

> A combo's list is rendered floating by Ext, outside the field, so the choice is read from the clicked option row and its list, never from the field. Null when the click was not on an option, and null when the list belongs (aria-controls or aria-owns) to a credential field: a PIN's options are the PIN. Text passes the same vocabulary filter as the outline, and `index` is null when the row is past the 50 kept.

## `versionOf`, [line 360](../../../../../new-chrome-extension/src/page/page-code.js#L360): Function

> Which build the page is: Ext's own version, else a version meta tag, else the main script's file name.

## `placeOf`, [line 370](../../../../../new-chrome-extension/src/page/page-code.js#L370): Function

> Where the person was: route, title, the first visible headings, the active tabs, the grid's title, the labelled dialogs and forms, and the build. Read-only, capped, text only.

## `secretsIn`, [line 491](../../../../../new-chrome-extension/src/page/page-code.js#L491): Function

> What a secret field leaves in the page: the ids its aria-describedby/aria-errormessage point at, and its value. Fields are read from the top document and every same-origin frame below it. One bounded set per page (`known`, 256 values, a true LRU: a quote that matches refreshes its entry, and the least recently matched is evicted, cleared on pagehide, never sent, logged or stored) holds secret values that are gone: a field's last value joins it when replaced by something that is not a longer version of it, or cleared (a per-field last-value WeakMap, so keystroke prefixes never enter it). It is fed from the first moment (`rememberSecrets`, called by the recorder at load) and at every check; when a watcher starts, every secret field's value is promoted into it too (a click cannot land mid-keystroke, and the click may unmount the field), and current field values are also consulted live. Secret fields include contenteditable and `role=textbox` elements. Raw lowercased and whitespace-collapsed forms are both kept, as `say` emits the latter. A noticed element that is one of those ids, or holds a secret field, is dropped; any text quoting a known or current value is dropped, and so is any text with a run of 3+ `*` or `•` next to a letter or digit, or of 3+ `x` next to a digit (`xxxx1234`) (partial masks are never kept; a lone `*` as in `Required *`, and words such as `Size XXXL` or `Mexxxico`, are). When the top document is another origin's (`blind`), nothing said in this frame can be checked, so all its text and errors are dropped. Ceilings: memory is per window, so a secret typed and cleared in a same-origin CHILD frame (or a sibling, or a cross-origin one) is not known to this window's watcher; a full page load (a form POST) starts with empty memory, so text on the next page quoting the last page's password is not known; pagehide clears it and a bfcache restore does not bring it back; more than 256 distinct secrets with none quoted since lets the oldest be forgotten; a secret typed in a field that is removed before any gesture started a watcher is never seen; a secret set and cleared programmatically inside one task is unknowable; a mistyped last character after backspacing joins `known` as its own value (over-drops only).

## `watchEffect`, [line 545](../../../../../new-chrome-extension/src/page/page-code.js#L545): Function

> What changed on the page after one gesture. Ends on 500 ms of quiet, 3 s at most, or the next gesture (`finish("next")`), and always disconnects its MutationObserver and restores `console.error` (only if nobody wrapped it after us). Request timing comes from Resource Timing, so the app's network is never patched. Fields are read as states only (enabled, shown, invalid), never values; every text goes through `say`. Each reader is wrapped so a failure loses only its key. Shortcuts ride on the open watcher rather than becoming gestures. The observer callback does no page-wide scan: secrets are read only after a noticed element appeared, and the busy elements are re-queried only when a mutation touched one. An effect with nothing in it (no items, fields, errors, shortcuts, route change, request or mask time) is not sent. Ceiling: a shortcut pressed after the effect finished (more than 500 ms after the last change) has no open watcher and is lost.
