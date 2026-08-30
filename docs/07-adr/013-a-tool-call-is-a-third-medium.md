# 013 — A tool call is a third medium

**Status:** accepted, 2026-08-30
**Relates to:** [004 — diff parameterisation](004-diff-parameterisation.md), [012 — a page the operator said yes to](012-a-page-the-operator-said-yes-to.md)

## The problem

`Verdict.CLEAN` requires every step of a run to be at `Medium.NETWORK` with no
escalation. A gesture makes the run `DEGRADED`, `DEGRADED` resets the clean
streak, and `AUTONOMOUS` needs ten consecutive clean runs. So **a skill whose
mail half is browser gestures can never earn the right to run unattended** —
not as a policy anyone chose, but by construction.

ADR 012 made that half demonstrable. It did not make it promotable, and it
cannot: a click is a click. Something that is not a click has to exist, or the
ladder stops one rung short forever.

## The decision

**A step may be performed by calling a tool on a connector the tenant
configured, and that is its own medium.**

`Medium.TOOL`, beside `NETWORK`, `UI` and `VISION`. `judge` treats NETWORK and
TOOL alike, so a run made of calls can be clean.

**Why not just call it `NETWORK`.** It would have been one word and no
migration. But a run record is read back months later to answer what actually
happened, and one word meaning "the request the operator's own click made" in
some records and "whatever a third party's connector decided to send" in others
is a word that answers nothing. What they have in common — deterministic, and
checkable against a result — is why `judge` treats them alike. What they do not
is why a reader can tell them apart.

**Where a tool step comes from: a person.** Induction reads recordings, and a
recording holds gestures and the calls they made. Nobody demonstrates an MCP
call, so a `ToolPlan` is always somebody's decision — *this click on Send is
`send_message` on that server* — recorded as a decision with a name on it. That
is ADR 004's rule about identity, applied to the thing performing a step rather
than to the values it carries.

## What was argued about

The plan this came from justified clean-eligibility as "deterministic,
assertable and idempotency-keyed". Two of those hold. **Assertable is a claim
about the future, not evidence.** A network step's post-conditions come from two
demonstrations agreeing, and both runs' responses are there to check them
against; a tool step has none, because nobody ever watched `send_message` work.
Its assertions are whoever mapped it, writing down what they expect.

That could have been answered with a special rule for tool steps. It is answered
instead by the rule every other step already meets: a step that writes and
carries no assertion makes the version **unverifiable**, and an unverifiable
version never reaches the top of the ladder however clean its runs are. A tool
step is not trusted more than a network step; it is trusted the same, and the
existing gate does the work.

`ToolPlan.writes` is said by the person who mapped it. Nothing else can say:
MCP declares no such thing, and a tool named `send_message` is a name, not a
promise. A system that guessed would guess wrong in the direction of sending a
mail nobody approved.

## What it refuses

- **A second call with a key already claimed.** A network write is protected
  within its run — an answered POST is never retried, because a status code
  means the application saw it. Nothing protected a connector call *across*
  runs: the same trigger firing twice, a durable workflow replayed after a
  crash, an operator pressing the button again because the first press seemed
  to hang. For a mail that is one message becoming two. The key is claimed by
  inserting a row before the call and kept whatever the call answers — a key
  released on failure would let a timeout, the one case where the send may well
  have landed, be retried into a second send.
- **Falling back to clicking.** Every failure at the tool rung stops. The
  gesture this step replaced was mapped away on purpose, so falling back to it
  would perform by clicking a step somebody decided should be a call — and for
  a connector that refused, would do again what it just refused.
- **Discovering connectors.** Servers are named in configuration. A system that
  found one and used it would be making the tenant's integration decisions for
  them.
- **Trusting the provider's own deduplication.** A promise this system cannot
  check is not a control.

## Consequences

A mail half performed as tool calls can reach `CLEAN`, accumulate a streak, and
be promoted — which is what stage 4 needs and what nothing before this made
possible. It stays gated on everything else: a named authoriser, the breaker,
the blast radius, and the assertion rule above.

A deployment with no connectors configured is unchanged. Every skill runs the
way it did; what it cannot do is promote a mail step past assisted, and
`why_not_autonomous` says so rather than leaving somebody waiting on a streak
that cannot move.

The mapping itself — choosing a step, choosing a tool, saying whether it writes
— is not built here. Until it is, a `ToolPlan` can only be authored
programmatically, which is the honest state: the machinery is proved and the
surface that lets an operator use it is the next piece.
