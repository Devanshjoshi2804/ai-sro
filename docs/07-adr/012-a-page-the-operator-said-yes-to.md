# 012 — A page the operator said yes to

**Status:** accepted, 2026-08-30
**Extends:** [008 — passive observation](008-passive-observation.md)

## The problem

ADR 008 excludes webmail and sign-in pages from observation, and the reasoning
holds: systematic monitoring of employee mail *content* triggers a mandatory
DPIA under GDPR, and employee consent is not a valid legal basis for it, because
of the power imbalance between an employer and the person whose mailbox it is.
Continuous capture of an inbox is exactly the thing that rule exists to stop.

The cost of it arrived with the first task that spans mail and the WMS. A reply
drafted in whatever client the customer runs is a gesture, and a gesture can
only be learned by watching one. Press "teach" in a mailbox today and four
separate things refuse it — `applyPolicy` registers no content script,
`injectInto` returns false, `allowsHost` gates the tab watch, and the backend's
`admit` refuses every event — so the recording comes back empty and the task can
never be demonstrated at all.

We could have made teaching a blanket exception to the exclusion list. We did
not, because "the system was in teaching mode" is a claim about a flag, and the
flag is set by the same software that would be doing the recording.

## The decision

**A host the tenant excludes may be observed when the operator says so about
that host, in their own browser, for the tab in front of them.**

The consent is the operator's own pick in the side panel — the "Watch this tab"
control that already exists — and on an excluded host the panel says what is
being agreed to and names it. It is recorded as a `HostGrant` on that device:
who granted it, when, and when it runs out.

This is not the thing ADR 008 forbids, and the difference is not a technicality:

| Passive capture of an excluded host | A grant |
| --- | --- |
| Continuous | One tab, ended by closing it |
| Invisible after setup | Named in the panel the whole time |
| Whatever the operator happens to open | One host they chose while looking at it |
| Configured by an administrator | Chosen by the person being observed |

The last row is the one that matters. GDPR's objection to consent is that an
employer asking an employee for it is not a free choice. Nobody is asking here:
there is no prompt, no default, and no administrator who can turn it on for
somebody else. The operator either presses the button or the mail half of their
task stays undemonstrable, which is a cost to them and to nobody else.

## What it must refuse, and does

- **`capture_enabled: false` is absolute.** A tenant that has not agreed to
  observation gets none, grant or no grant. That switch is the contract
  conversation, and no button in a side panel is allowed to be it.
- **A grant widens `exclude_hosts`, never `include_hosts`.** An exclusion list
  is a default and a default is the kind of thing the person in front of the
  screen may decide otherwise about. An administrator naming the only hosts
  that may ever be observed is not a default, and an operator does not get to
  overrule it from a panel.
- **Exactly the host, never the domain under it.** `hostMatches` is right for a
  policy pattern somebody wrote and wrong for a grant: reading one mailbox as a
  whole domain would admit every host beneath it. Backend and extension compare
  the same way.
- **It expires.** At most 12 hours, whatever is asked for. The extension revokes
  on `chrome.tabs.onRemoved`, so in the ordinary case a grant ends when the tab
  closes; the cap is what happens when the ordinary case does not — a crash, a
  killed worker, a laptop that slept. A standing grant nobody remembers giving
  is the thing the exclusion list exists to prevent.
- **Only the operator whose device it is.** Behind the device's own secret, and
  refused if the device's principal is not the caller. A browser is not a
  person, and a grant somebody else could add for you is not consent.
- **Nothing is retroactive.** A grant admits what is captured while it is live.
  Mail from before it was pressed was never recorded and cannot be.

## Consequences

The mail half of a task becomes demonstrable, which is what stage 2 of the
autonomy plan needs. It stays *attended*: a step performed by clicking makes
every run of it degraded (`domain/execution/verdict.py`), a degraded run resets
the clean streak, so a skill with a gesture step can never accumulate the ten
consecutive clean runs autonomy requires. `why_not_autonomous` now says that in
so many words rather than reporting a count that will never move — a governance
gate that answers "no" without "because" is one people work around.

A tenant that wants mail never observed under any circumstances still has
`include_hosts`: name the systems that may be observed, and no grant widens it.

The knowledge that a mailbox was observed does not disappear when the grant
does. The grant is recorded on the device with the name of who gave it, and the
recording it produced is evidence like any other — reviewable, and subject to
the same retention window.
