# Notes for `backend/src/sro/application/induction/frequency.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/frequency.py`](../../../../../../../backend/src/sro/application/induction/frequency.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/frequency.py#L1): Docstring

> What a step's frequency says about whether it is part of the task.
>
> Rationale and the rejected alternatives:
> docs/07-adr/015-a-step-is-decided-by-how-often-it-happens.md.

## module, [line 7](../../../../../../../backend/src/sro/application/induction/frequency.py#L7): Note on the line above

Code: `PART_OF_THE_TASK = 2 / 3`

> What share of the doings has to contain a step before it is the task itself
> rather than an exception to it.
>
> A share, never a count, so it means the same at four doings and at four
> thousand: a step three doings made is the task when there were four of them and
> a rounding error when there were four thousand, and a threshold counted in
> doings would quietly change its mind about a skill as the task got more popular.
>
> Two in three rather than a bare majority, because at the counts this actually
> sees a majority is one person's habit. Four doings is the real case -- somebody
> demonstrating a task they do -- and there the difference between half and a
> majority is a single operator filling a field they usually skip. A rule that
> flips on one doing is not a rule. Two in three is the smallest share that
> survives one dissenter at four, which is the smallest batch anyone is going to
> hand this.
>
> At the other end of the range the same number is aggressive rather than
> conservative, and that is the end this whole piece of work is about. At four
> thousand doings a step made thirteen hundred times is below two in three and is
> discarded -- unless it types a field some doing left empty, which is what
> actually carries a large batch. Thirteen hundred occurrences are not a
> mis-click by anybody's reading, and this number alone would call them one. The
> escape hatch is doing the work there, not the threshold; see ADR 015, which
> argues that trade rather than hiding it.
>
> It is not a precise number and does not pretend to be. It decides only what
> happens to a step nothing else explains: a rare step that types an optional
> field is kept whatever this says, because that is a branch and not a frequency
> question at all.

## `Standing`, [line 10](../../../../../../../backend/src/sro/application/induction/frequency.py#L10): Docstring

> What a step's place in the task is, once the doings have been counted.

## `Standing`, [line 11](../../../../../../../backend/src/sro/application/induction/frequency.py#L11): Note on the line above

Code: `ALWAYS = "always"`

> Part of the task. Runs every time.

## `Standing`, [line 13](../../../../../../../backend/src/sro/application/induction/frequency.py#L13): Note on the line above

Code: `CONDITIONAL = "conditional"`

> Part of the task, on a condition the doings named: it happens when
> somebody supplies a particular value and is skipped when nobody does. This
> is `SkillStep.when` -- the field already exists for exactly this and names
> the parameter whose presence decides whether the step happens at all.

## `Standing`, [line 15](../../../../../../../backend/src/sro/application/induction/frequency.py#L15): Note on the line above

Code: `NOISE = "noise"`

> Not part of the task. A mis-click, a field typed and corrected, a panel
> opened to look at -- the accidents union would have learned.

## `standing_of`, [line 18](../../../../../../../backend/src/sro/application/induction/frequency.py#L18): Docstring (debt)

> Decide each aligned step's place in the task, by reference-frame index.
>
> No model decides this, and ADR 004 is why: identity -- what a step *is*,
> what a value *means* -- is settled by evidence or not settled at all. So
> this reads two things and nothing else. How many of the doings contained
> the step out of how many doings there were, both of which
> :func:`align_all` counted and neither of which is estimated here; and
> which parameter, if any, the step's own keystroke fills, which the diff
> already worked out from what the demonstrations sent. Both are facts
> somebody could check by re-reading the recordings. A model asked "is this
> step really part of the task?" would produce a confident answer to a
> question the counts already answer, and would produce one just as
> confidently where they do not.
>
> Rarity on its own drops nothing. A step below the threshold that types a
> field some doing left empty is a branch, however rare: one in a hundred is
> the rate a real branch runs at, not evidence against it. Dropping it is how
> a skill silently stops handling the case somebody needed it for -- which is
> exactly what happened to the address lookup. A rare step with nothing
> explaining it is a fumble, and that is the only thing rarity decides.
>
> The keystroke, specifically, via
> :meth:`Parameterisation.conditional_on` -- not "this step mentions an
> optional parameter". The write that carries the field goes out either way,
> carrying the absent form the demonstration sent, so a rare write is a
> fumble however many nullable fields it happens to fill in.
>
> **What this actually checks, which is weaker than correlation.** The
> argument for keeping a rare step is that it happened *whenever* the value
> was supplied. This does not test that, and cannot: neither input carries
> per-doing supply counts. `Alignment.seen` says how many doings contained
> the step; nothing here says how many doings supplied the parameter, so the
> two counts are never compared. What is checked is the far weaker "this
> step's keystroke types some optional field at all". A step in one doing of
> a hundred whose parameter was supplied in sixty comes out `CONDITIONAL`
> exactly as one whose parameter was supplied in one -- perfect correlation
> and none are indistinguishable here.
>
> That is a real gap and it is left open rather than papered over, because
> the arithmetic to close it does not exist yet and inventing a supply count
> from what is on hand would be a confident number with nothing behind it.
> What it costs is bounded in the cheap direction: a step wrongly kept this
> way is skipped on every run where nobody supplies the parameter.
>
> ponytail: closing it needs a per-doing record of which parameters each
> doing supplied -- `align_all` already walks every run and could count, per
> reference index, how many of them filled each optional field. Then the test
> becomes "supplied in n doings, made in n of them" and the number means what
> the argument says. Worth building when a batch large enough for the
> difference to show up exists; at four doings the two tests agree anyway.
