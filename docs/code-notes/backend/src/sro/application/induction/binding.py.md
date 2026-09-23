# Notes for `backend/src/sro/application/induction/binding.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/binding.py`](../../../../../../../backend/src/sro/application/induction/binding.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/binding.py#L1): Docstring

> Which field a keystroke filled.
>
> A step can only be made conditional on a parameter if something proves the step
> produces that parameter. The proof is already stored: what the operator typed
> turns up in the write their next few gestures sent, under one key.
>
> Normalised, because a form is allowed to tidy what it was given -- the work
> area name uppercases as you type, a code field trims, a number field sends 1
> for what was typed as "1". Nothing looser than that: a value that merely
> contains another is not a match, and a value that fits two keys fits neither.

## `_writes`, [line 12](../../../../../../../backend/src/sro/application/induction/binding.py#L12): Docstring

> Every succeeded, non-background mutating call on this frame.
>
> A write the system rejected is not the write whose fields a step's typed
> values ended up in -- a failed, retried mutation must not stand in for the
> one that actually happened.

## `write_document`, [line 20](../../../../../../../backend/src/sro/application/induction/binding.py#L20): Docstring

> The parsed body of this frame's write, for a caller that already knows
> there is exactly one -- true once `explode` has split a gesture into
> per-step frames, which is where every caller but `key_filled_by` gets its
> frames from. `key_filled_by` runs earlier, when that is not yet true, and
> searches every write itself rather than assuming this one.

## `key_filled_by`, [line 25](../../../../../../../backend/src/sro/application/induction/binding.py#L25): Docstring

> The pointer in `within`'s write that `frame`'s typed value filled.

## `_named`, [line 51](../../../../../../../backend/src/sro/application/induction/binding.py#L51): Docstring

> What the control calls itself, in the framework's terms and the DOM's.

## `tidied`, [line 64](../../../../../../../backend/src/sro/application/induction/binding.py#L64): Docstring

> One value as another part of the same page would have written it.
>
> Public because the diff groups by it too: the work area name uppercases as
> you type, so what the keystroke carried and what the write sent are the
> same value and have to end up as one parameter rather than two.

## `key_filled_by`, [line 28](../../../../../../../backend/src/sro/application/induction/binding.py#L28): Comment

Code: `return None`

> A keystroke that typed nothing but whitespace is not evidence that
> it filled anything -- without this, tidying would match it to every
> field a form happened to send back empty.

## `key_filled_by`, [line 34](../../../../../../../backend/src/sro/application/induction/binding.py#L34): Comment

Code: `documents = [`

> This runs on frames as recorded, before `explode` splits a gesture's
> several calls into separate steps -- a Save that creates a record and
> then sets its address is one frame with two mutating writes, and there
> is no principled "first" among them. So every write is searched, and
> the ambiguity rule already applied within one body applies across
> bodies too: a value that matches more than one write fits none of them.

## `key_filled_by`, [line 46](../../../../../../../backend/src/sro/application/induction/binding.py#L46): Comment

Code: `named = _named(frame)`

> Two keys holding "1" is not rare in a real form -- the work areas
> screen sends voiceCode "1" beside deltaPriority 1 -- and refusing
> both loses the one field the whole pair hangs on. The control says
> which is which: an ExtJS field is named for the key it posts under,
> so where exactly one of the tied keys is the field's own name, the
> tie is not a guess. Where none is, or several are, it still binds
> to neither.
