# Notes for `backend/src/sro/infrastructure/steel/generate_extension_recorder.py`

Comments and docstrings moved out of [`backend/src/sro/infrastructure/steel/generate_extension_recorder.py`](../../../../../../../backend/src/sro/infrastructure/steel/generate_extension_recorder.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/infrastructure/steel/generate_extension_recorder.py#L1): Docstring

> Writes the extension's generated content scripts, secrets already baked in.
>
> MV3 content scripts are static files -- there is no injection-time hook the
> way Steel's Playwright adapter has (`add_init_script`, substituting
> `__SECRET_WORDS__` fresh on every page). This runs the exact same
> substitution once, from the exact same `_recorder_script()`, so
> `SECRET_TOKENS` stays the one list either side reads from -- never a second
> copy hand-kept under `new-chrome-extension/` that drifts from this one.
>
> Two files come out, because the extension needs the same knowledge in two
> different JavaScript realms:
>
> `recorder.generated.js` runs in the page's own realm, where the application's
> framework globals live -- an ExtJS control cannot be identified from an
> isolated world, because `window.Ext` there is the isolated world's window.
>
> `sensitivity.generated.js` runs in the isolated realm, where the network
> relay redacts bodies and headers before they reach the service worker. It
> carries the classification rules rather than the recorder, so the page never
> sees them and the isolated world never needs the recorder.
>
> `sensitivity.module.js` is that same knowledge a second time, as an ES module,
> because the service worker has to redact as well: a `webNavigation` URL never
> passes through a content script, so the isolated world's copy cannot see it. A
> content script registered through `chrome.scripting` cannot be a module, and a
> module service worker has no `window` to hang an IIFE's result on, so the one
> list has to come out in both shapes. Both are written from the same rules
> below, so neither can drift from the other or from Python.
>
> Run with `make gen-recorder`. `test_generated_scripts_are_current.py` fails
> the build when either file drifts from its source, so a forgotten regenerate
> cannot ship a stale credential list.

## `_shape_source`, [line 50](../../../../../../../backend/src/sro/infrastructure/steel/generate_extension_recorder.py#L50): Docstring

> One alternation, as a JSON string for `new RegExp`.
>
> A string rather than a `/.../` literal because two of these patterns
> contain a `/` inside a character class, and hand-escaping a slash is
> exactly how the two sides stop being the same expression. JavaScript spells
> a named group `(?<name>)` where Python spells it `(?P<name>)`; that one
> character is the whole difference, and `test_the_copied_secret_shapes...`
> on the rig side re-derives these from this file to prove it.

## `_rules`, [line 54](../../../../../../../backend/src/sro/infrastructure/steel/generate_extension_recorder.py#L54): Docstring

> The rules themselves, as plain declarations both realms can wrap.

## `sensitivity_source`, [line 224](../../../../../../../backend/src/sro/infrastructure/steel/generate_extension_recorder.py#L224): Docstring

> The isolated world's copy: an IIFE that publishes onto that world's window.
>
> Generated rather than hand-written for the same reason the recorder is:
> there is one list of credential words and one list of credential headers,
> on the Python side, and a copy kept by hand under `new-chrome-extension/`
> would drift the moment somebody added a word to only one of them.

## `sensitivity_module_source`, [line 241](../../../../../../../backend/src/sro/infrastructure/steel/generate_extension_recorder.py#L241): Docstring

> The service worker's copy: the same rules as an ES module.
>
> The worker sees URLs no content script ever does -- `webNavigation` fires
> with no page involved -- so it cannot borrow the isolated world's copy, and
> a hand-written second list is the drift this whole file exists to prevent.

## `shape_source`, [line 252](../../../../../../../backend/src/sro/infrastructure/steel/generate_extension_recorder.py#L252): Docstring

> The rig's `target_identity`, as an ES module.
>
> The rule is written once here as text; `new_agent_arch/src/rig/shape.py` is
> the reference and both are held to `new-chrome-extension/fixtures/
> shape-identity.json`. Emitted rather than imported for the reason the rest
> of this file is: the extension has no build step, and a hand-kept second
> copy of a matching rule drifts the moment either side is edited. Never edit
> the output; edit this.

## `page_code_source`, [line 307](../../../../../../../backend/src/sro/infrastructure/steel/generate_extension_recorder.py#L307): Docstring

> page-code.js is hand-written and injected raw by both the extension
> (`executeScript`) and Steel (`add_init_script`), so it cannot take a marker
> substituted at injection. Its one generated line is the credential word list
> inside `readers`: this rewrites exactly that line from `SECRET_TOKENS` and
> nothing else, fails loudly if the line is missing or doubled, and writes the
> same bytes on every run. `isSecretField` itself lives once, in those readers;
> the recorder gets it by the readers splice, so there is no second copy
> (X10a re-review N1).
