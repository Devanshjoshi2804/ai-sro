# ADR 008 — Observation is passive and always on, in the operator's own browser

**Status:** accepted · v0 — supersedes the consent position in
[`docs/10-security-and-data.md`](../10-security-and-data.md)

## Context

ADR-era design settled on **deliberate demonstration**: an operator says "teach
the system this task", drives a server-side Steel browser through a live view,
and the session is sealed. `docs/10-security-and-data.md` states the reasoning —
clean on consent, on personal data, and on optics where union agreements apply.

Two things did not survive contact with use.

**The operator has to already know which tasks are worth automating.** They
don't. The tasks that cost a warehouse the most are the ones nobody notices,
because they are small and happen eleven times a week. A system that only ever
learns what somebody thought to teach it learns the tasks that were annoying
enough to remember, not the ones that are expensive.

**Teaching is a context switch.** Leave your browser, open the console, drive a
different Chrome that is signed in separately, remember to seal. Each of those is
a place a demonstration is abandoned, and every abandoned demonstration is a task
the system does not know.

The alternative is what Claude-in-Chrome does: an extension in the operator's own
browser that watches them work and proposes the automation itself.

## Decision

Passive, continuous observation across all tabs, in the operator's own Chrome, as
the default capture mode. Deliberate demonstration remains, as a higher-fidelity
tier for teaching a specific task.

**Rejected: allowlisted work apps only.** It sounds like the moderate option and
is worse than both. The allowlist has to be maintained by somebody who already
knows which systems matter — the same knowledge the deliberate-demonstration
model assumed and did not have — and the cross-application tasks (read the mail,
look it up in the WMS, reply) are exactly the ones it cuts in half. What it buys
is a smaller consent problem, which the controls below buy more cheaply.

**Rejected: keeping capture server-side and adding discovery later.** A
server-side browser only sees the sessions somebody deliberately opened in it. It
cannot observe work it was never invited to.

This decision is only defensible with its controls, so they ship with it, not
after:

- **Exclusion by non-injection.** Excluded hosts never have a content script
  registered on them. Not captured-then-filtered — untouched. The default
  exclusion list covers banking, health, HR and payroll, and webmail content.
- **A pause the operator controls**, and an administrator kill switch delivered
  on the heartbeat.
- **Truthful state, always visible** — the badge and the panel say whether
  capture is on, and an operator can open what was captured in the last hour and
  delete it.
- **Credential values still never reach storage**, by the mechanism that already
  exists: `recorder.js` drops the value of a credential field at the source, and
  credential-named body fields are replaced before a body is written. Matched by
  field name on whole words, never by inspecting values (ADR 004).
- **Per-tenant retention**, applied by an object-store lifecycle rule.
- **Per-tenant opt-in.** Passive observation is off until a tenant turns it on,
  and that is a contract conversation, not a config default.

## Consequences

The system can find work nobody thought to teach it, and the operator's own
signed-in session is the one being observed — no second sign-in, no delegated
credentials for capture.

The costs are real and are accepted:

- **This is monitoring, and it reads as monitoring.** Where union agreements or
  works councils apply, this needs written agreement before it is switched on.
  The per-tenant opt-in is the mechanism, and it must not become a default.
- **Personal data will be captured incidentally.** An operator checks something
  personal in a work browser. The exclusion list and the purge button reduce it;
  they do not eliminate it. Retention is the backstop.
- **Volume.** A day of always-on capture with per-gesture screenshots is far
  larger than a day of deliberate demonstrations. There is a per-device daily
  budget, and the extension drops screenshots first, response bodies second, and
  gestures never.
- **Passive evidence is thinner than a Steel recording** — no accessibility tree,
  no CDP initiator chain, response bodies only where the page could see them.
  Enough to recognise a repeated task; sometimes not enough to induce a skill
  from, which is why the teaching tier still exists.

## Amendment, 2026-08-31 — accessibility trees while nobody is teaching

Passive capture originally took screenshots and never accessibility trees. The
tree is the one view that says what a control *is* rather than where it happens
to sit today, and induction builds a locator from it. Without one a skill has
only what the DOM offers: a css path of framework ids assigned in render order,
`span#button-1350-btnIconEl`, which is a different element after a reload.

So every skill that arrived the way this document describes — watch the
operator, notice the repetition, offer it back — got the weaker ladder, and the
good locators were reserved for the one path an operator has to remember to
press a button for. That inverts the decision above: the deliberate tier was
meant to be higher-fidelity in what it *asks* of somebody, not the only tier
that produces a durable skill.

Trees are now taken passively, under `capture_snapshots`, with their own
per-minute cap.

**Off by default, and the only capture setting that is.** Trees come from
`chrome.debugger`, and Chrome shows "AI-SRO is debugging this browser" for as
long as anything is attached. That is a visible change to a screen somebody is
working on, so it is an administrator's decision taken where the cost is written
down, not a default an operator meets one morning.

**The banner is a deployment question, not a code one.** An extension
force-installed by enterprise policy (`ExtensionInstallForcelist`) does not
raise it at all — which is the deployment this is for: managed Chrome, operators
who installed nothing themselves. An unpacked development copy does raise it,
and no extension can suppress it from inside; `--silent-debugger-extension-api`
is a launch flag, so it is a developer's convenience and not an answer for a
fleet. A tenant running unmanaged browsers should leave this off.

**DevTools wins.** Chrome allows one debugger per tab. An operator who opens
DevTools takes it and keeps it; a refused attach is remembered and not retried,
and capture carries on without trees. Their tab, their tools.

**Teaching wins too.** A deliberate demonstration attaches its own debugger, so
passive trees let go first. The operator asked for that one and did not ask for
this one.

The controls above are unchanged and all still apply: excluded hosts are never
touched, the pause and the kill switch still stop it, and the panel still says
what is on.
