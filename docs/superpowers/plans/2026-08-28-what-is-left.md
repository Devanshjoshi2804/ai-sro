# What is left

Written after the first end-to-end run: a skill learned from watching an
operator, which then created a real record in a real warehouse. That run, and
the two before it that failed, changed what this list should say — so the list
is written from evidence rather than from the roadmap.

## Where the system actually is

An operator created three work areas by hand in Blue Yonder. Nobody pressed
"teach". Passive capture recorded them, the miner clustered them as one task by
the change they make, automatic learning induced a skill, and that skill then
created `SROTEST1` and `SROTEST2` for real — from two supplied values, through
the operator's own signed-in session, at the `assisted` rung with a named human
behind it.

Six parameters, two required, four optional. The optional ones are optional
because the operator's *first* work area filled only a name and a description
and the warehouse accepted it; each carries the absent form that doing actually
sent — `null` for the three numeric boxes, `""` for the voice code. The live
work-area list is the proof: `NEWTESTS` and `DOCK-TES` sit there with those four
columns blank.

So the loop from *watching* to *acting* is closed and demonstrated. What is not
built is the loop from *being asked* to acting — which is the thing the owner
described wanting, and it is stage 1 of 4.

## What is open, with the evidence

Each of these has a reproduction. None is speculative.

**A URL query slot substitutes raw.** `X&limit=9999` renders
`?name=X&limit=9999&limit=25`, and `a/b` adds a path segment. The same class as
the JSON injection that was closed this week, in a different syntax. It needs
its own change because the two URL site kinds store values differently:
`url_query_pairs` decodes through `parse_qsl`, so encoding at substitution is
correct there, while `url_path_segments` never unquotes, so the same rule yields
`ATTN%2520ALI`. One rule cannot serve both. Recorded in ADR 010.

**Loop bounds count raw frames; step indices count aligned steps.** Reproducible
on `main` before any of this week's work, with two non-evidential unmatched
frames and no conditional step:
`InvariantViolation: a loop covers steps 3-3, and this version has 2`. It fails
loudly rather than shipping a wrong skill, which is why it was walled off behind
a refusal rather than fixed under time pressure.

**Two shapes refuse rather than guess.** A form that nulls a whole nested block,
and a loop task whose optional field is filled by its own keystroke. Both are
deliberate and both are capabilities the operator does not have. The second is
the one that will be met first, because a loop over order lines with an optional
field per line is an ordinary warehouse task.

**Teaching reads every episode of a candidate.** Fifty sightings means fifty
blob reads and fifty stored recordings in one teach. Bounded in practice today,
unbounded in principle, and the cost arrived with reading optionality across the
whole history.

**A value from a model reaches a filter unescaped** — `intent/narrow.py`, where
`choices._searched` escapes and this path does not. Flagged during review, not
fixed, different code path from the one that was.

**The induction version bump is a human step**, guarded by a docstring. Forget
it and a candidate refused under old rules is never retried — the silent failure
the version stamp exists to end.

**A base64-encoded response body is inlined without redaction** (`capture.py`).
It cannot reach a rendered request body, which was checked rather than assumed,
but it is what a reviewer reads in a recording.

## Decisions that are not work

**The knowledge base.** Sixty distinct staff logins, a few phone numbers and
some street addresses were pseudonymised in place this week, shape preserved, and
nothing reads those values. The real ones remain in git history, which is on
Bitbucket. Only a rewrite removes them, and that means force-pushing a branch
other people have. Separately: 78 MB of a customer's captured operational data
lives in a *source* repository, and `test_catalogue.py` already skips when the
base is absent — so the repo is built for it to live in object storage, fetched
by `make ingest-kb`. That fixes the future; only the rewrite fixes the past.

## The order, and why

**1. The URL query slot.** It is the last member of a class this week closed
everywhere else, it has a reproduction, and every day it stays open is a day a
skill can send a parameter nobody demonstrated. Half a day.

**2. Stage 1 of the autonomy plan — the watch.** A trigger the operator's own
browser evaluates: they point at a mail that is an example, mark the parts that
matter, and what is stored is *how to find them* rather than the text. On a
match the panel offers; nothing runs unasked. This is the first stage where the
owner's example becomes visible, and it is designed already
(`docs/superpowers/specs/2026-08-25-cross-system-workflow-design.md` and the
mail plan). A week.

**3. The loop-and-optional refusal.** By the time a watch is firing on real
mail, the tasks it fires will include loops, and this refusal will be met. It is
also the honest place to fix the frame-space/step-space mismatch underneath it,
which is a defect in its own right. A few days, and it wants the index spaces
unified rather than patched.

**4. Stage 2 — the reply, taught by demonstration.** Attended: a person presses
send every time, forever, because a gesture step can never reach `CLEAN` and so
can never earn autonomy. This is where the owner's example works end to end with
a human in it. A week.

**5. The knowledge base out of git.** Not urgent, not hard, and it stops the
problem growing. The history question can wait for a moment when a force-push
costs nobody anything.

**6. Stage 3 — a mail step that is a call.** An MCP connector, because a tool
call is the only kind of step the ladder can promote. This is the change that
makes stage 4 reachable at all, which is why it is not optional.

**7. Stage 4 — unattended.** Only after 3, and only per trigger, authorised by a
named person for one task on one system.

The smaller items — teaching's unbounded reads, the model-value escaping, the
version bump, the base64 redaction — are each an hour and belong in whichever
week touches their file. They are listed so they are not lost, not so they are
scheduled.

## What this ordering assumes

That proving the thing that exists is worth more than adding to it. The three
runs this week produced three defects that no test suite had found, two of them
in code written the same day and reviewed three times. Every stage above should
end the same way: something runs against the real system, and what breaks gets
written down before the next stage starts.
