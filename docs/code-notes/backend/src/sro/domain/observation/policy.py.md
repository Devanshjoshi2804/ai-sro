# Notes for `backend/src/sro/domain/observation/policy.py`

Comments and docstrings moved out of [`backend/src/sro/domain/observation/policy.py`](../../../../../../../backend/src/sro/domain/observation/policy.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/observation/policy.py#L1): Docstring

> What an extension may capture, decided per tenant.
>
> Off until somebody turns it on. Passive observation of every tab an operator
> opens is monitoring, and ADR 008 makes it a contract conversation rather than a
> default -- so the absent policy is the refusing one, not the permissive one.

## module, [line 9](../../../../../../../backend/src/sro/domain/observation/policy.py#L9): Note on the line above

Code: `DEFAULT_EXCLUSIONS: tuple[str, ...] = (`

> The identity providers. Sign-in pages, and nothing else.
>
> Deliberately short. Finance, health and HR are the categories that matter most
> and they are named differently at every customer, so they are supplied by the
> tenant when observation is switched on. A guessed list would read as coverage
> and provide none.
>
> **Webmail was here and is not any more, deliberately.** `mail.google.com`, the
> four Outlook hosts and `mail.yahoo.com` were excluded by default; the work that
> starts in a mailbox -- a mail arrives, somebody reads it, and what it says
> decides what they then do in the WMS -- could not be recorded without an
> operator granting the host by hand on every tab. That is a real workflow this
> product exists to learn, and a default that hides half of it teaches half a
> task. Mail is now observed like any other host: only in a tab somebody pressed
> Watch on, only while `capture_enabled`, and only until they close it.
>
> What that costs is written down rather than argued away, because it happened.
> `domain_matches` is a host-or-subdomain test, so excluding
> `login.microsoftonline.com` protected the sign-in page and not the mailbox
> behind it -- and a tenant that switched observation on with the older defaults
> was recording message bodies, recipients and a screenshot of the open message
> every gesture, for thirty days. That is now the documented consequence of
> pressing Watch on a mailbox, not an accident of a list being wrong. A tenant
> that does not want it says so: `excluding(...)` puts any of these back for that
> tenant alone, and `only()` turns the policy into an allow-list, which is the
> form that survives a mail client this file has never heard of.
>
> The identity hosts stay, and they are a different question from mail. A
> sign-in page is where somebody types a password; there is no task to learn
> there and nothing on it anybody wants in evidence. `b2clogin.com` is the same
> family as `login.microsoftonline.com`: Azure AD B2C, where the host is always
> `<tenant>.b2clogin.com`. It is here rather than in one customer's policy
> because it is Microsoft's host, not theirs -- this deployment captured a real
> sign-in on `blueyonderalphaus.b2clogin.com` and closed it by editing that
> tenant's stored list, which left the next tenant exactly where this one
> started. Nothing but sign-in is served from b2clogin.com, so excluding the
> domain costs no evidence anybody wanted.
>
> A customer's OWN identity host stays out. This deployment also excluded a
> Keycloak at `keycloak-…-wms-keycloak-prod.us.live.external.byp.ai`, and that
> name belongs to one warehouse rather than to a vendor -- guessing at those is
> the "coverage that provides none" this list exists to avoid.

## `ObservationPolicy`, [line 18](../../../../../../../backend/src/sro/domain/observation/policy.py#L18): Note on the line above

Code: `version: int = 0`

> Bumped on every change. The extension holds it and asks for a new policy
> only when the number moves, so a heartbeat costs one integer.

## `ObservationPolicy`, [line 22](../../../../../../../backend/src/sro/domain/observation/policy.py#L22): Note on the line above

Code: `include_hosts: tuple[str, ...] = ()`

> Empty means everything not excluded. A non-empty list narrows capture to
> those hosts and their subdomains.

## `ObservationPolicy.allows`, [line 45](../../../../../../../backend/src/sro/domain/observation/policy.py#L45): Docstring

> Whether a page at this URL may be observed.
>
> The extension enforces this by not registering a content script on an
> excluded host, so an excluded page is never touched. This is the second
> check: an extension that is wrong, old or lying does not get to write
> into the evidence plane anyway.
>
> ``granted`` are hosts the operator chose in their own panel, for a tab
> in front of them (`domain/observation/grant.py`). They widen the
> exclusion list and nothing else, which is where the three answers
> below differ:
>
> - ``capture_enabled`` is the tenant's agreement that any of this
>   happens. No operator's button overrides it.
> - ``exclude_hosts`` is what the tenant agreed to *by default*, and a
>   default is the kind of thing the person in front of the screen may
>   decide otherwise about for one page.
> - ``include_hosts`` is an administrator naming the only hosts that may
>   ever be observed. That is not a default, and an operator does not get
>   to widen it from a side panel.

## `ObservationPolicy.enabled`, [line 58](../../../../../../../backend/src/sro/domain/observation/policy.py#L58): Docstring

> Observation on for this tenant. A contract conversation happened;
> this is where it is recorded.

## `ObservationPolicy.excluding`, [line 64](../../../../../../../backend/src/sro/domain/observation/policy.py#L64): Docstring

> Replaces the list rather than adding to it: an exclusion somebody
> thought they had removed is worse than one they have to retype.

## `ObservationPolicy.allows`, [line 52](../../../../../../../backend/src/sro/domain/observation/policy.py#L52): Comment

Code: `if excluded_by_default and host not in granted:`

> Exactly the host, never a subdomain of it: a grant is what somebody
> pressed a button about while looking at one page, and reading it as
> a whole domain would let a click on one mailbox admit every host
> under it.
