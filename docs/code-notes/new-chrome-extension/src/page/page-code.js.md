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

## `perform`, [line 3](../../../../../new-chrome-extension/src/page/page-code.js#L3): Docstring

> Find a control by the first locator that resolves, act on it, and say which
> one worked.
>
> The strategies mirror `infrastructure/steel/ui_driver.py` deliberately: the
> same skill, replayed on the server or in the operator's own browser, has to
> find the same control or the two mediums are not interchangeable.

## `perform`, [line 3](../../../../../new-chrome-extension/src/page/page-code.js#L3): Comment

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

## `performAt`, [line 316](../../../../../new-chrome-extension/src/page/page-code.js#L316): Docstring

> Act at a point, because the gesture came from pixels rather than from a
> control the demonstration identified. Coordinates are CSS pixels in the
> viewport -- the same space `viewport` reports, so the picture the model
> was shown and the point it answers with measure the same thing.
>
> What the field would not take. See `landed` in `perform`: the same
> rule, and the same reason it can only be known here. (`shortAt`)

## `performAt`, [line 316](../../../../../new-chrome-extension/src/page/page-code.js#L316): Comment

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

## `screenSize`, [line 457](../../../../../new-chrome-extension/src/page/page-code.js#L457): Docstring

> How big the screen is and where it is, and nothing else.
>
> The cheap half of `viewport`, for when the whole of it cannot be had:
> three property reads, no layout, no selector. The picture is what the rung
> that looks actually needs -- the digest beside it is a help, and a help that
> costs the command its deadline is not one.

## `viewport`, [line 466](../../../../../new-chrome-extension/src/page/page-code.js#L466): Docstring

> The visible controls and where they are, plus the size of the space those
> coordinates are in.
>
> Normalised to 0-1000 because that is the space the vision model answers in,
> and measured in CSS pixels because that is the space `performAt` acts
> in. A picture measured in device pixels and a click measured in CSS pixels
> are out by the display's scale factor, which on any retina screen is a click
> halfway up the page.

## `viewport`, [line 466](../../../../../new-chrome-extension/src/page/page-code.js#L466): Comment

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

## `csrfToken`, [line 542](../../../../../new-chrome-extension/src/page/page-code.js#L542): Docstring

> The one header this extension knows how to read live: Blue Yonder keeps
> its write token in a page-level JS global, never in a cookie, so a
> recording can only ever capture a value the recorder correctly redacts.
> Runs in the MAIN world -- `Ext` is the page's own framework object, not
> reachable from the isolated world `send` runs in -- and answers
> `null`, never throws, when the page has no such global to read.

## `requestedWith`, [line 546](../../../../../new-chrome-extension/src/page/page-code.js#L546): Docstring

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

## `send`, [line 552](../../../../../new-chrome-extension/src/page/page-code.js#L552): Docstring

> Send a request from a tab that is already on that origin, so the operator's
> own session applies -- which is why a skill can be replayed against a system
> this deployment holds no credentials for at all.
>
> Runs in the isolated world. Same origin, same cookie jar, but the page's
> patched `fetch` is not the one called here: a replayed request must not
> arrive in the evidence plane looking like something the operator did.

## `send`, [line 552](../../../../../new-chrome-extension/src/page/page-code.js#L552): Comment

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
