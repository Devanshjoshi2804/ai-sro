# 014 — A preview an operator read is a review

**Status:** accepted, 2026-08-31
**Relates to:** [012 — a page the operator said yes to](012-a-page-the-operator-said-yes-to.md), [013 — a tool call is a third medium](013-a-tool-call-is-a-third-medium.md)

## The problem

`_check_runnable` refuses to run a version at `RECORDED`, in its own words:

> a recorded skill has not been reviewed by anybody; promote it to shadow to
> run it against the system

That sentence is the whole of the rule. It does not say who has to review it or
where; it says nobody has, and until somebody does, the version does not run.
It has held since the ladder existed, and every version that ever reached
`SHADOW` reached it because a person in the console looked at the evidence and
pressed promote.

The panel this project is building offers to run a task the moment induction
finishes producing it. That version is `RECORDED` — it has never been anywhere
near a console, because there has not yet been time for a human to find it
there. Pressed at that moment, `Do it` reaches `_check_runnable` and is
refused, and the offer this whole project exists to make dead-ends on the
first task it was ever supposed to help with. Either the rule bends, or the
offer is a lie the panel tells before the operator has finished reading it.

## The decision

**A version may be promoted by an operator reading its own preview, and it
reaches `ASSISTED` and no further.**

The preview this promotes on is not a summary. Before the press, the panel
lists `SkillStep.intent` for every step the version has, the exact value each
one resolved to from the sentence the operator typed, and the tab it will act
in (`starts_on`). Nothing is elided and nothing is inferred silently — a
parameter `ResolveIntent` could not fill is asked for by name rather than
guessed, and a sentence it is not sure about is refused rather than matched to
the nearest skill. What is on the screen when the operator presses `Do it` is,
line for line, what the run is about to do.

That is why the press counts. `_check_runnable`'s rule is not "a person must
have clicked a button in a particular screen" — it is that nobody has looked.
Somebody has: the operator, on the exact steps and the exact values, at the
screen the run is about to act on, with a stop button already in front of
them for when it starts. That is a stronger review than most of what a
console promotion is, where the reviewer is reading an induced version's steps
in the abstract, on a system they may not be looking at right now. A real
reading of `_check_runnable`'s rule is not a way around it.

## What it deliberately does not reach, and why

A preview promotes to `ASSISTED` and never further, whatever the version's
track record says once it gets there, and whatever rung it started below.
`SkillVersion.promote` enforces this ahead of every other rule it checks:

```python
if from_where == "preview" and to.rung > PromotionStage.ASSISTED.rung:
    raise InvariantViolation(
        "a preview promotes no further than assisted; "
        f"{to} is earned by clean runs, not by a press"
    )
```

The whole argument above is that the operator read what *this* run would do.
`AUTONOMOUS` is not a claim about one run; it is a claim that ten consecutive
ones, unattended, will come out the same way the reviewed one did. Nobody
reading a preview read that — nobody could, because the ten runs it promises
have not happened yet, and a preview only ever shows the one in front of the
operator. The ladder's own rule for the top rung is a **streak**, counted by
`earn`, and a streak is evidence a press cannot manufacture no matter how
carefully it was read. `AUTONOMOUS` still needs the ten clean runs it needed
before this decision; a preview cannot pay that debt on its behalf, and does
not try to.

## How a reviewer tells the two apart, and disagrees

`promoted_from` is what makes this decision auditable rather than merely
policy. `"console"` is a version a person promoted after sitting down with the
evidence — the track record, the assertions, the steps — outside the moment
of any one run. `"preview"` is a version an operator moved up while reading
what one run would do. Both are real promotions to `ASSISTED`, made by a
named `promoted_by`, and neither is worth less to `_check_runnable` — a run
does not ask which door its version's promotion came through. But they are
different reviews, and a reviewer in the console reading a library of skills
needs to know which one happened, the same way ADR 012 needed a `HostGrant`
to say who gave it rather than let a flag mean two things.

What disagreeing looks like is bounded by what this ladder already lets
anyone do to a promotion, from either door. `demote` is deliberately not a
button: its own docstring says why — "this happens automatically, without a
human, which is exactly why it is a separate method with a reason attached."
Nobody can un-click a console promotion today either. A reviewer who reads
`promoted_from == "preview"` and disagrees is not left with nothing: they can
treat the streak with more scrutiny before authorising further runs, they can
teach the skill again from a clean demonstration — which lands a new version
at `RECORDED`, unreviewed, while the one in question keeps running until
somebody promotes the replacement — or they can wait, because three
consecutive failures pull any `ASSISTED` version back down regardless of who
put it there. `promoted_from` does not invent a weaker kind of promotion that
is easier to reverse; it makes visible, for the first time, which one is
already sitting on the version. That visibility is the whole of what this
decision buys a reviewer, and it is honest about not buying more.

## What was argued about: rehearse first, then ask

The alternative that was on the table before this: run the version once in
`SHADOW` — producing every request and sending none of them — and only offer
`Do it` once that rehearsal came back clean.

It reads safer, and it is not what the operator asked for. They typed
"create work operation NDPCK, north dock picking, priority 5" wanting a work
operation named NDPCK, not a demonstration that the system knows how to want
one. A rehearsal that withholds every write produces nothing they can point
to, so `Do it` after it would still be the first real attempt — the same
press, one screen later, having taught the operator that pressing a button
gets them a dry run rather than the thing they typed. That is the "teach me"
problem this whole project exists to leave behind, wearing a different coat:
it asks the operator to do something *for the system* — sit through a
rehearsal — before the system will do the thing *for them*.

It would also not have bought back the review `_check_runnable` cares about.
A shadow run's writes are withheld and never shown to a person; nothing about
running one adds a reader who was not there before. The preview the operator
already reads before pressing is the review. A rehearsal after it would be
process for its own sake — evidence nobody looks at, standing between the
operator and the work they described.

## Consequences

The panel's first press on a version it just induced now reaches `ASSISTED`
instead of `NotRunnable`, which is what makes the offer this project builds
usable on the task it was built for. `promoted_from` costs one field and one
guard, both narrow: nothing about a console promotion changes, every existing
caller of `promote` keeps its old behaviour by leaving the argument at its
default, and the guard composes with `check_promotion` rather than
duplicating what it already refuses — a one-rung jump past `AUTONOMOUS`, a
demotion disguised as a promotion, and a target already reached are all still
refused exactly as they were.

What it does not buy: a way to reverse a preview-promotion that a console
promotion could not also be reversed by, and a shortcut to `AUTONOMOUS`. Both
gaps are deliberate, and both are the same gap the top of the ladder has
always had — evidence, not a click, moves a version past `ASSISTED`, whichever
door the click that got it to `ASSISTED` came through.
