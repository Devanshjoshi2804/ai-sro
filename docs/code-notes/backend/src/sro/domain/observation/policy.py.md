# Notes for `backend/src/sro/domain/observation/policy.py`

Comments and docstrings moved out of [`backend/src/sro/domain/observation/policy.py`](../../../../../../../backend/src/sro/domain/observation/policy.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/observation/policy.py#L1): Docstring

> What an extension may capture, decided per tenant.
>
> Off until somebody turns it on. Passive observation of every tab an operator
> opens is monitoring, and ADR 008 makes it a contract conversation rather than a
> default -- so the absent policy is the refusing one, not the permissive one.

## module, [line 9](../../../../../../../backend/src/sro/domain/observation/policy.py#L9): Note on the line above

Code: `DEFAULT_EXCLUSIONS: tuple[str, ...] = ()`

> Empty. §5.6 (2026-09-24): a sign-in page is no longer excluded, it is
> captured like any other page, under the same redaction every other page
> gets.
>
> **Why this used to be here.** A sign-in page is where somebody types a
> password, and the identity hosts (`accounts.google.com`,
> `login.microsoftonline.com`, `b2clogin.com` -- Azure AD B2C's own domain,
> always `<tenant>.b2clogin.com`) were excluded wholesale rather than trust
> redaction to catch a credential there. That trust was misplaced the other
> way: `domain_matches` is a host-or-subdomain test, so excluding
> `login.microsoftonline.com` protected the sign-in page and not a mailbox
> behind the same identity provider -- the same shape of cost webmail's own
> exclusion paid, below.
>
> **Why it is safe now.** Nothing about a sign-in page is special to this
> system's redaction, which runs on every page: `is_secret_field` (recorder
> side) drops a credential field's value at the point of capture, whatever
> page it is on; `_redact_query` (server side, `domain/recording/sensitivity`)
> takes an OAuth `code` out beside its `state` companion; and E7
> (2026-09-24) found and closed the one path that had never been asked the
> question -- `trees.js`'s accessibility-tree snapshot carried a text
> field's live value verbatim, with no field name to redact by, because
> CDP's `Accessibility.getFullAXTree` exposes an editable control's typed
> content twice (its own `value`, and again as a child `StaticText`/
> `InlineTextBox` node's `name`) and offers no HTML attribute to judge
> either occurrence by. `withoutTypedText` now drops both, for every
> editable control, on every page -- not only a sign-in one.
>
> **The migration.** A stored policy whose `exclude_hosts` was exactly this
> old default held the default, not a tenant's own choice, so it is healed
> to `[]`. Any other list -- narrower, wider, reordered -- is a choice and
> stays. A customer's own identity host (this deployment also excluded a
> Keycloak at `keycloak-…-wms-keycloak-prod.us.live.external.byp.ai`) was
> never in this list to begin with; that name belongs to one warehouse, not
> to a vendor, and guessing at those is the "coverage that provides none"
> this list existed to avoid even when it had entries.
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
> A tenant that switched observation on with the older defaults was recording
> message bodies, recipients and a screenshot of the open message every
> gesture, for thirty days. That is now the documented consequence of
> pressing Watch on a mailbox, not an accident of a list being wrong. A tenant
> that does not want it says so: `excluding(...)` puts any of these back for that
> tenant alone, and `only()` turns the policy into an allow-list, which is the
> form that survives a mail client this file has never heard of.

## `ObservationPolicy`, [line 14](../../../../../../../backend/src/sro/domain/observation/policy.py#L14): Note on the line above

Code: `version: int = 0`

> Bumped on every change. The extension holds it and asks for a new policy
> only when the number moves, so a heartbeat costs one integer.

## `ObservationPolicy`, [line 18](../../../../../../../backend/src/sro/domain/observation/policy.py#L18): Note on the line above

Code: `include_hosts: tuple[str, ...] = ()`

> Empty means everything not excluded. A non-empty list narrows capture to
> those hosts and their subdomains.

## `ObservationPolicy`, [line 23](../../../../../../../backend/src/sro/domain/observation/policy.py#L23): Note on the line above

Code: `capture_snapshots: bool = False`

> Accessibility trees while nobody is deliberately teaching.
>
> The tree is the one view that says what a control *is* rather than where it
> happens to sit today, and induction builds a locator from it. Without one, a
> skill has only what the DOM offers -- a css path of framework ids assigned
> in render order, different on the next page load. So every skill that
> arrived the way this product intends -- watch, notice the repetition, offer
> it back -- got the weaker ladder, and the good locators were reserved for
> the path an operator has to remember to press.
>
> Off by default, and this is the only capture setting that is, because it is
> the only one an operator can see. Trees come from `chrome.debugger` and
> Chrome shows "AI-SRO is debugging this browser" for as long as anything is
> attached. An extension force-installed by enterprise policy
> (`ExtensionInstallForcelist`) raises no banner at all, which is the
> deployment this is for; an unpacked development copy does, and no extension
> can suppress it from inside. Turning this on is therefore an administrator's
> decision about a browser they manage, which is why it is written here rather
> than defaulted on and discovered by somebody working.
>
> It also costs the tab's debugger, and Chrome allows one. An operator who
> opens DevTools takes it and keeps it until they close them; capture carries
> on without trees rather than fighting them for it.

## `ObservationPolicy`, [line 25](../../../../../../../backend/src/sro/domain/observation/policy.py#L25): Note on the line above

Code: `snapshot_max_per_minute: int = 20`

> Its own budget, not the screenshots'. A tree is a round trip and some
> JSON, a picture is a PNG, and one shared counter would have whichever
> happened first spend the other's allowance.

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

## `ObservationPolicy.reading_structure`, [line 73](../../../../../../../backend/src/sro/domain/observation/policy.py#L73): Docstring

> Accessibility trees while nobody is deliberately teaching.
>
> Its own method rather than a field somebody edits, because turning it on
> is a decision about a browser an administrator manages: on an install
> that is not force-installed by policy, Chrome puts a debugging banner on
> every watched tab for as long as this is on.

## `ObservationPolicy.allows`, [line 52](../../../../../../../backend/src/sro/domain/observation/policy.py#L52): Comment

Code: `if excluded_by_default and host not in granted:`

> Exactly the host, never a subdomain of it: a grant is what somebody
> pressed a button about while looking at one page, and reading it as
> a whole domain would let a click on one mailbox admit every host
> under it.
