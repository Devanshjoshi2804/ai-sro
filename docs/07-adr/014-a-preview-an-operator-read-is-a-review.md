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
them for when it starts. It is not a stronger review than a console one, or a
weaker one — it is a different review, sufficient for the rung it reaches.
ADR 013 makes the disciplined version of this move already: "a tool step is
not trusted more than a network step; it is trusted the same, and the
existing gate does the work." The same restraint applies here. A real reading
of `_check_runnable`'s rule is not a way around it.

**What the operator did not read.** A preview shows `SkillStep.intent`,
the resolved value of each parameter, and the tab the run starts in. It does
not show which system each step calls, whether that step writes or only
reads, or whether any step carries an assertion at all — the very thing
`verifiable` and `unchecked_writes` exist to check before a version may ever
reach the top of the ladder. A console reviewer looking at the same version
sees all of that, because the console renders the full `SkillVersionModel`;
the operator, mid-task, sees a shorter list built to be read in the seconds
before a press. This is a real gap, not a rounding error, and this decision
does not pretend otherwise.

It is not answered here. Nothing about the preview stops a step the
operator did not understand to be a write from writing, or to the system
they assumed. What is already built, and does the work `judge` already does
for every other run: "a run can be clean at every rung and still have made
the wrong record, and the person who was looking at it is the only one who
could ever know" — `run.wrong_because`, checked before anything else `judge`
reads, turns that person's own surprise into `FAILED` whatever the steps
did. A preview that undersold a write becomes a run the operator can call
wrong the moment they see what it made; that counts against the streak
exactly like any other failure, and `DEMOTE_AFTER_FAILURES = 3` pulls the
version back below `ASSISTED` on the third one. The gate does not stop the
first surprise. It stops a version that keeps surprising people from
staying at a rung a press can reach, which is the same shape of answer ADR
013 gives its own unmeasured claim: not solved here, solved by the rule
every other run already meets.

## What it deliberately does not reach, and why

A preview promotes to `ASSISTED` and never further, whatever the version's
track record says once it gets there, and whatever rung it started below.
`SkillVersion.promote` checks this immediately after `check_promotion` — the
existing rule for which rungs a promotion may move between at all — and
before any of its own other rules, so a preview is refused the same jump a
console promotion would be refused, plus this:

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

It would also not have bought the review `_check_runnable` cares about for
free. A shadow run's writes are withheld today and never shown to a person —
but that is this codebase's current choice about what `SHADOW` does with what
it builds, not a fact about rehearsal in general. A shadow run produces
exactly the request bodies that would make a preview stronger than the one
described above: which system, whether the step writes, what it would send.
The honest sentence is not "nothing could be added by rehearsing first" — it
is that *showing the operator what a rehearsal built is work this project is
not doing*, because it is still a second screen, on a second press, before
the thing they typed happens — the "teach me" problem in different clothes,
whatever ends up rendered on it. The preview the operator already reads
before pressing is the review this decision relies on; a rehearsal shown to
nobody, which is what `SHADOW` does today, would only be process standing
between the operator and the work they described.

## Consequences

The panel's first press on a version it just induced can now reach `ASSISTED`
instead of `NotRunnable`, for the versions this decision covers. It is not
every version induction produces. `promote` refuses a version that came from
one demonstration and writes — every value it sends is fixed as demonstrated
— unless the caller separately passes `acknowledging_fixed_values=True`, and
that is exactly the shape of the skill a freshly induced task most often is:
one demonstration, one write.

**Amended.** Resolved, by the task that turned this decision into a running
call (`RunFromPreview`): the preview promotion sets that flag on the
operator's behalf. This was left open above, and the reasoning first written
beside that call claimed the narrower trust the flag stands for was contained
in the larger one this ADR already grants — that a press trusted to move a
version from sending nothing to sending real writes has, by the same press,
already been trusted with the smaller claim that the particular fixed values
are the right ones. That claim does not hold, and it matters that it does
not: "What the operator did not read", above, is a closed list —
`SkillStep.intent`, the resolved value of each *parameter*, and the starting
tab — and a value `acknowledging_fixed_values` guards is definitionally not a
parameter. One demonstration means nothing was diffed, so nothing told a
value that varies apart from a value that happens to be constant; what the
flag exists to catch is precisely the constants that never became a parameter
and so were never a line in the preview at all. The two sets of values do not
overlap, and no reading of the press supplies the second set.

Setting the flag here is therefore not a proof already on file; it is an
accepted residual risk, taken on the same terms this ADR already accepts one
for. "What the operator did not read" above does not solve *that* gap either
— whether a step writes, to which system, checked by which assertion — and
says so plainly: what closes it is not the preview but the backstop every
other run already meets, `run.wrong_because` read before anything else
`judge` reads, and `DEMOTE_AFTER_FAILURES` pulling the version back down after
three. A write sent on a fixed value nobody actually read is exactly the kind
of surprise that backstop exists for: the operator who sees the wrong record
land calls it wrong, that counts against the version like any other failure,
and the version stops running assisted on the strength of a press once three
of them agree it was wrong. The flag is set because refusing it would dead-end
the commonest shape a freshly induced skill has on its very first press, not
because the press proved what it did not show.

`promoted_from` costs one field and one guard, both narrow: nothing about a
console promotion changes, and the guard composes with `check_promotion`
rather than duplicating what it already refuses — a one-rung jump past
`AUTONOMOUS`, a demotion disguised as a promotion, and a target already
reached are all still refused exactly as they were. `from_where` defaults to
`""`, so any caller unaware of it is unaffected; the two callers that were
already moving a version without a console press (`earn`'s clean-streak
promotion and `repair_drift`'s climb back to an inherited rung) were each
given an honest value of their own — `"earned"`, `"repair"` — rather than
left on that default. Blank has to mean exactly one thing, nobody has
promoted this version by any door, and leaving either of those two on `""`
would have made it mean that and "a person reviewed this" at once — the same
two-meanings-at-once failure `"console"` and `"preview"` exist to end.

What it does not buy: a way to reverse a preview-promotion that a console
promotion could not also be reversed by, and a shortcut to `AUTONOMOUS`. Both
gaps are deliberate, and both are the same gap the top of the ladder has
always had — evidence, not a click, moves a version past `ASSISTED`, whichever
door the click that got it to `ASSISTED` came through.

## Amended: three claims above were asserted, not enforced

A final review of the branch found that three of the load-bearing sentences in
this decision were true of the argument and false of the code. Each is now
enforced rather than asserted, and this section records what closed them
because the argument above reads differently once they hold.

**The version the operator read is the version that runs.** "What is on the
screen when the operator presses `Do it` is, line for line, what the run is
about to do" was not true. `ResolveIntent` matches on `skill.runnable or
skill.latest` and the panel previewed *that* version; the press carried no
version at all, so `RunFromPreview` took `skill.latest`. Any skill holding a
newer `RECORDED` version — re-teaching produces one, so do `repair_drift`,
`map_step_to_tool` and `add_assertion` — had the operator reading v1's steps
and values while v2 wrote, with v1's parameters, and had v2 promoted to
`ASSISTED` by a press that never showed a line of it. The panel now sends the
version number it drew the preview from, `RunFromPreview` runs exactly that
one, and a version that has moved between the preview and the press is
**refused** rather than run either way round — falling forward runs steps
nobody read, falling back runs a version somebody has since replaced. The
refusal is a sentence: what you read is no longer what this task would do, ask
again and read it through.

**The backstop this decision's residual-risk argument rests on now holds.**
That argument is made twice above and again beside `acknowledging_fixed_values`
— a surprise becomes `run.wrong_because`, that counts as a failure, and
`DEMOTE_AFTER_FAILURES = 3` pulls the version back below `ASSISTED`. It did not
hold. `promote` zeroes `consecutive_failures`, and a press promotes any version
below `ASSISTED`, so three wrong runs demoted a version and the operator's very
next press restored it with the counter at zero. A version that was wrong every
single time never stayed demoted, and the sentence above about a reviewer being
able to "wait, because three consecutive failures pull any `ASSISTED` version
back down" was untrue for exactly the versions this decision creates. It had a
second door as well, which a re-review of the first fix caught: three guards
now, not one.

- A preview promotion does not clear `consecutive_failures`. The clearing was
  written for the console — "cleared by the person who looked" — and the
  operator mid-task is not that person: they read one run's steps and values
  and nothing about the runs that failed before it. Without this a version at
  one or two failures is walked back to zero by every press and the third never
  arrives.
- A version carrying a `demotion_reason` is refused a preview promotion
  outright, in `promote` itself so every door is covered. A skill demoted for
  being wrong three times needs a person in the console with the evidence in
  front of them. That is what the ladder is for, and a press is not that. The
  refusal says so in an operator's words rather than naming a field.
- A verdict revised by the operator rewinds `consecutive_failures` to what it
  held before the verdict it replaces. The two guards above close the press's
  door and leave `FinishRun`'s wide open: `after(CLEAN)` zeroes the counter the
  instant a run ends, and the operator's answer only arrives afterwards, so the
  sequence this decision actually describes — a run finishes clean, the
  operator sees what it made and takes it back, repeat — oscillated between
  zero and one forever. Three was unreachable, and a version that made the
  wrong record *every single time* ran assisted indefinitely, which is the
  exact failure the first two guards were written to prevent arriving by a
  different route. `TrackRecord` now remembers what the count held before the
  most recently counted run, and `instead_of` puts it back before applying the
  replacement; restoring what the replaced verdict cleared is precisely that
  method's job.

None of the three narrows what this decision grants for a version that is
working. What they do is make the sentence "three in a row pulls it back down"
mean what it says — through the ordinary sequence, not only through three
outright crashes — which is the only thing standing behind the writes this
decision admits the operator never read.

**`promoted_from` is rendered.** "That visibility is the whole of what this
decision buys a reviewer" was false while the field was on
`SkillVersionModel` and drawn by no console component. It is now spelled out
where a reviewer reads a version's rung, in words rather than as a raw value,
so a promotion made from the panel is visibly a different thing from one made
here.

## The undo is a press this decision covers, and it shows less

`Undo that` routes through the same `/runs/from-preview` and promotes the
reversal skill under the same argument — but the reversal's steps and values
are rendered nowhere, so "the operator read it" was not true of that press at
all. One press is the design and stays one press; one press with no idea what
is about to be deleted is not something this decision ever argued for. The
reversal now carries the version it was validated against, pinned the same way,
and the delete step's own intent alongside the identifying values the run read
back — named on the card, before the button, so what the press removes is on
the screen when it is pressed. That is less than the closed list above: the
reversal skill's other steps, and which system each one calls, are still
unread. It is bounded by the same backstop as everything else here, and the
honest sentence is that this press shows what it deletes and not how.
