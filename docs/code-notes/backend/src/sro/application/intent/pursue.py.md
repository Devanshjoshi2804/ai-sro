# Notes for `backend/src/sro/application/intent/pursue.py`

Comments and docstrings moved out of [`backend/src/sro/application/intent/pursue.py`](../../../../../../../backend/src/sro/application/intent/pursue.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/intent/pursue.py#L1): Docstring

> Do it anyway: pursue a goal nobody has demonstrated.
>
> The console's honest answer to an unknown task used to be "teach me this one",
> and for an operator with a job to finish that is a dead end wearing a polite
> face. A person put in front of an unfamiliar WMS screen does not refuse; they
> read what is on it, work out which control does the thing, and do it.
>
> So this composes what is known into a goal and drives the browser toward it:
> the screen the knowledge base says the entity lives on, the fields its form
> declares, the endpoint that would confirm it worked, the quirks somebody has
> already been caught by. The model chooses gestures; every one of them is
> executed by the same driver a taught skill uses, against the same guards.
>
> Two things make this safe enough to exist.
>
> **A goal is not permission.** A pursuit that would change the system stops and
> shows what it is about to do. The operator's confirmation is what an assisted
> run has always required, and nothing here weakens it.
>
> **A pursuit is a demonstration.** Every gesture and every call is captured
> exactly as a taught session is, so a task done this way once can be induced
> into a skill and done over the API the next time. That is the whole point: the
> slow rung exists to make itself unnecessary.

## `Goal`, [line 10](../../../../../../../backend/src/sro/application/intent/pursue.py#L10): Docstring

> What to accomplish, said the way a person would say it to a colleague.
>
> Composed rather than generated: every line of it comes from something
> observed -- a screen in the catalogue, a field in a form model, an endpoint
> somebody's run has answered. A goal made up of guesses would be a model
> inventing a warehouse task, which is the failure this whole system is
> arranged against.

## `Goal`, [line 11](../../../../../../../backend/src/sro/application/intent/pursue.py#L11): Note on the line above

Code: `intent: str`

> The operator's own sentence. Kept verbatim -- it is the only part that
> says what they actually wanted.

## `Goal`, [line 13](../../../../../../../backend/src/sro/application/intent/pursue.py#L13): Note on the line above

Code: `start_url: str | None`

> Where to begin, when the knowledge base knows the screen.

## `Goal`, [line 15](../../../../../../../backend/src/sro/application/intent/pursue.py#L15): Note on the line above

Code: `changes_the_system: bool`

> Whether achieving this would write. Decides whether a confirmation is
> required before anything is done, not whether it may be attempted.

## `Goal`, [line 17](../../../../../../../backend/src/sro/application/intent/pursue.py#L17): Note on the line above

Code: `facts: tuple[str, ...] = field(default_factory=tuple)`

> What is known about doing this here, each traceable to a source.

## `Goal`, [line 19](../../../../../../../backend/src/sro/application/intent/pursue.py#L19): Note on the line above

Code: `fields: tuple[str, ...] = field(default_factory=tuple)`

> What the screen's form declares it needs. Asked for before anything
> opens: a model told to work out a value on screen will invent one.

## `Goal`, [line 21](../../../../../../../backend/src/sro/application/intent/pursue.py#L21): Note on the line above

Code: `watch_out: tuple[str, ...] = field(default_factory=tuple)`

> Quirks already paid for by somebody. A duplicate transport mode is
> blocked client-side with no network call at all -- a model that does not
> know this will click Save and conclude it worked.

## `compose`, [line 38](../../../../../../../backend/src/sro/application/intent/pursue.py#L38): Docstring

> Turn what is known into something a browser can be pointed at.

## `_start_url`, [line 50](../../../../../../../backend/src/sro/application/intent/pursue.py#L50): Docstring

> The screen the catalogue says this lives on, if it named one.

## `_fields`, [line 57](../../../../../../../backend/src/sro/application/intent/pursue.py#L57): Docstring

> The inputs the catalogue says this screen asks for.

## `_cautions`, [line 65](../../../../../../../backend/src/sro/application/intent/pursue.py#L65): Docstring

> Quirks somebody has already been caught by.

## `_writes`, [line 76](../../../../../../../backend/src/sro/application/intent/pursue.py#L76): Docstring

> Whether pursuing this would change anything.
>
> Read off the proposal's own endpoints where there are any, because a method
> is a fact and a verb in a sentence is an opinion. Where there are none, the
> sentence is all there is -- and the tie is broken towards "this writes",
> since the cost of asking for a confirmation nobody needed is a click, and
> the cost of not asking is a warehouse changed without one.

## `Goal.brief`, [line 23](../../../../../../../backend/src/sro/application/intent/pursue.py#L23): Docstring

> The goal as the model receives it.

## `Pursuit.of`, [line 97](../../../../../../../backend/src/sro/application/intent/pursue.py#L97): Docstring

> A pursuit, and whether it may start without being asked twice.
