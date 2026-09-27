# Notes for `backend/src/sro/domain/skill/signing_in.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/signing_in.py`](../../../../../../../backend/src/sro/domain/skill/signing_in.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L1): Docstring

> Which job of this tenant's signs in at the page a run is stuck on.
>
> A run meets a sign-in page for one reason -- the session it was relying on has
> gone -- and stopping there is the wrong answer twice over: the operator has to
> notice, and the request they made goes nowhere until they do. On a system
> somebody works in all day, sessions expire mid-flow, and so do dialogs, consent
> screens and error pages. A system that only reports those is a system somebody
> has to sit next to.
>
> **And the way back in is already mined.** Measured on the deployment
> 2026-09-19, tenant `greyorange`:
>
>     Log in using Azure B2C SSO   1  Click the 'Local WMS users (bf56-001-eus2)
>                                     (SSO)'          blueyonderalphaus.b2clogin.com
>                                  2  Click the SSO button to proceed
>     Log in to Keycloak           0  Enter username or email   keycloak-…byp.ai
>                                  1  Type the password
>
> The operator has signed in through that chooser many times with the recorder
> on, so the clicks are evidence like any other. This is the lookup from "the
> browser is sitting on `blueyonderalphaus.b2clogin.com`" to "the job whose
> evidence is that page".
>
> **By the host, never by the title.** `Log in using Azure B2C SSO` is a model's
> sentence about a job; the host is a fact about where the gestures happened. A
> name match would also pick `Log in to Google Account` for a warehouse that
> bounced to Google, which is a run signing into the wrong system.
>
> **The host it starts on, not merely one it touches.** A job is the way
> through the page its first gesture (in time) was made on: replayed from
> there it does what the operator did from there. A job that only passes
> through the host in the middle would start half way through somebody
> else's page.
>
> This was "every cited gesture on that host" until 2026-09-23, and that
> rule rejected every real sign-in: the deployment's chain is the chooser on
> `b2clogin.com` and then the form on the Keycloak host, two origins, so no
> job was ever entirely on either and a run bounced to the chooser found no
> way back in.
>
> **One job or none.** Two jobs starting on one sign-in host is two ways in,
> and picking between them is guessing with somebody's credentials.
>
> **Only a job found to sign in.** The host a job starts on is also where
> every ordinary job on one host starts, so a run bounced to a page the
> tenant had worked on would have spliced that work in. The candidates are
> the jobs whose `Workflow.signs_in` the mining pass set -- `checks.signs_in`
> -- and the host then picks among them.

## `PageSignals`, [line 19](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L19): Docstring

> Pre-created for X4's UI-lane expired-session check, which needs
> `a_sign_in_page` to tell a genuinely missing control from a session that
> dropped the operator on a sign-in page mid-step. S6 owns this file's
> `signals()` picture of a page -- the shape here (`url`, `visited`,
> `password`, `autocomplete`) and `a_sign_in_page` itself are copied verbatim
> from S6's own brief, not designed here, so S6 lands the rest of it
> (`asks_for_a_code`, `PageDriver.signals`, the page code's `sroPage.signals`)
> on top of a type and a function already in their final shape.

## `a_sign_in_page`, [line 67](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L67): Docstring

> A page is a sign-in page when it shows a password field that is not a
> new-password field, or a `current-password` or `one-time-code` token, or
> when its tab is inside an OAuth/OIDC round trip. Structural signals only
> (S6, §5.6) -- never a host list or a login-looking path.
>
> S6 fix round 1 (I5): `username` alone and `new-password` alone never
> count. An in-app "create user" form carries both, and reading it as a
> sign-in page reported a failed act as an expired session. An
> identifier-first page (Azure B2C) is still caught: it sits inside the
> round trip its authorize request opened.
>
> A lost navigation log (`visited is None`, see `SteelDriver._arrived`) is
> read as possibly inside a round trip, never as outside one (M1): the cost
> is at most one needless re-sign-in, and §5.5 retries a step once.
>
> S6 re-review round 2 (N2): that "at most one" held only once
> `SteelDriver.navigated` was fixed to start the log on the tab's first
> main-frame navigation after adoption -- until then `visited` stayed
> `None` forever, so every later failed step in an adopted tab cost a
> re-sign-in, not just the first one.

## `a_navigation`, [line 44](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L44): Function

> A URL as the navigation log keeps it: scheme, host, path and the query's
> parameter names, never a value, and no fragment (S6 fix round 1, M2: the
> log held `?code=&state=` in the clear). The one value kept is an authorize
> request's `redirect_uri`, cut to its own scheme, host and path: it is the
> public page registered with the provider, and the round trip cannot be
> closed without it.
>
> S6 re-review round 2 (N4, partial): a bare query token with no `=`
> (`?<jwt>`) used to come back from `parse_qs` as a key of its own, so the
> whole token was kept as a "parameter name". Only names that actually
> appear as `name=value` in the raw query are kept now; a bare token is
> dropped. Ceiling: a path segment that is itself a secret (`/verify/<token>`)
> is still kept whole -- the log matches the recorded page by exact path,
> and folding it through `path_shape` would also fold the authorize
> request's `redirect_uri` path, which the round trip must match exactly.

## `_in_round_trip`, [line 56](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L56): Function

> S6 fix round 1 (C1): an authorize request opens the trip and names where
> it ends -- its own `redirect_uri`. The first main-frame navigation back to
> that origin and path closes it, whatever the return looks like: a query
> `code`, a fragment (keycloak-js; the log never sees fragments, the page
> path is enough), a `form_post` POST with no query (ASP.NET / Azure AD), or
> an error return. Matching on a `code` in the query left every other return
> open, so the tab read as a sign-in page for the rest of its life. It also
> no longer closes on an app URL that happens to carry `code` and `state`.
>
> S6 re-review round 2 (N3): a single `back` value let an inner federated
> hop (B2C to Azure AD, say) overwrite the outer trip's own `back`, so the
> outer trip's return went unmatched and a page still on the outer
> provider's host read as outside any round trip. `back` is now a stack of
> every open trip's return page; each navigation pops whichever entry it
> matches, wherever it sits in the stack, and the tab is inside a round
> trip while the stack is non-empty.

## `expired`, [line 80](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L80): Function

> Whether a step that could not act met an expired session: sign-in
> signals on a page whose shape (origin and `path_shape`, ids folded) is
> not the page the step was recorded on. A password form on the recorded
> page itself is the step's own work -- an in-app change-password screen --
> and never an expired session (S6 fix round 1). Ceiling: an application
> that routes its own login by fragment on the recorded path is not told
> apart; the step then fails honestly rather than re-signing in.

## `signs_in_at`, [line 86](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L86): Docstring

> The job that signs in at this page, or None where nothing does.
>
> `where` is where the browser actually is -- `Look.elsewhere` when a step
> found no tab on its own system, which is what an interruption looks like
> from the inside.
>
> `not_this` is the job being run, which can never be its own way back in.

## `_starts_at`, [line 100](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L100): Docstring

> The origin of the first gesture this job cites, in time; the job's own step
> order breaks a tie.

## `sign_in_chain`, [line 111](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L111): Function

> The steps a sign-back-in replays: every step, in step order, cut to the
> gestures made no later than the first act (in time) that left its host
> after the credential was typed; a step left with nothing is dropped
> (audit wave 1, task 10, 2026-09-24). Cutting by time rather than walking
> by step order (fix round): a step ordered early can cite a click made after
> the landing, and a credential step can be ordered after the submit's step.
> Cites whose gesture is missing are kept, so aged-out evidence still refuses
> the way back in.
>
> - The credential anchors the end, not the username: an identifier-first
>   sign-in leaves the username page's host for the password's, and that
>   Next is not the landing. With no credential cited, the first typed value
>   anchors it; with nothing typed, nothing says where the sign-in ends and
>   the whole job is the chain, as before.
> - A door before any typing (a credential chooser that crosses to the form's
>   host) is not a submit and never ends the chain.
> - Cut inside the step: the deployed Azure B2C job's last step cites both
>   the submit that left Keycloak and a click in the WMS nineteen seconds
>   later. Only cites up to the submit are kept; the job itself is not changed.
>   The step's `says` still describes both, so the planner sees text about the
>   portal with only the submit's evidence.
> - General: hosts via `passed_through`, never a host, page text or title.

>
> Fix round 2 (2026-09-24), reviewer rulings:
>
> - **Replay order.** Kept steps are replayed by the latest time among their
>   kept gestures, ties by step order, and the step holding the leaving
>   submit always last. In step order, a `Type the password` step filed
>   after the submit's step would submit an empty box and then type the
>   password on the landed page.
> - **Refused attempts are not replayed.** After the credential was first
>   typed, a submit on the leaving submit's host that stayed there
>   (`_submits`: an Enter/NumpadEnter/empty press, or a click that is not on
>   a field the job types into -- `_same_field`) is dropped only when it was
>   refused: a field typed before it is typed again after it and before the
>   leaving submit (fix round 3). Staying alone is not refusal -- an accepted
>   password is followed on the same host by "Stay signed in? Yes", a
>   one-time-code or update-password page, or a consent screen, and dropping
>   that `Sign in` would click Yes on a password page never submitted.
>   Typing and focusing always stay.
> - **An Enter that is the leaving submit.** §4.4 (2026-09-24): a click the
>   browser synthesises from Enter carries `detail == 0` on a real
>   `MouseEvent` (a person's own click is `detail >= 1`), so the recorder's
>   own `e.detail` says which submit this was, structurally, rather than the
>   two gestures merely landing close together in time. Where the leaving
>   submit carries a `detail` (evidence recorded after this change), the
>   press immediately before it in citation order -- `before_cut`, not
>   merely the nearest in time -- is the same submit exactly when
>   `detail == 0`; a press elsewhere in the chain, or a leaving click a
>   person actually made (`detail >= 1`), is never folded in this way.
>   `K_ONE_SUBMIT_S` (50 ms) is consulted only where the cut carries no
>   `detail` at all: evidence recorded before this change, or a cut that is
>   itself a key press (a press has no `detail`). The deployed job measured
>   for the timing window: press at .074, the leaving Sign In at .075.
> - **A gesture cited twice replays once.** The deployed job cites its first
>   password typing in two steps; the later-replayed step loses it, and a
>   step left with nothing is dropped. The deployed job's
>   step 2 holds the operator's first Sign In (stayed on Keycloak) and an
>   Enter in the password box; replayed, they submitted early. On the QA
>   export the chain now types the username and password and submits once,
>   with the Keycloak Sign In that left last. A Next before the password
>   (identifier first) is before the credential and is kept.
>
> Fix round 4 (2026-09-24): the order is taken after duplicates are removed.
> When two steps cite the leaving submit, only the last of them (by step
> order) keeps it, and the submit is moved to the end of that step's cites.
> The others keep the rest of their gestures and are then ordered by what
> they still hold. Before, the order was fixed first, so a step that lost the
> submit to dedupe still sorted last and replayed its other gestures (a focus
> on the password box) on the landed page.
## `RecordedLogin`, [line 199](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L199): Class

> What a recorded sign-in says about credentials: the origin the password was
> typed on, which names its vault key, and the username typed before it --
> with the name of the box it was typed in (`label`), which the reader uses to
> tell "username X" in a mail from a job's value.

## `Logins`, [line 207](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L207): Class

> The tenant's recorded sign-in usernames and the boxes they were typed in,
> both through `normal`; each box paired with the system its sign-in lands
> on, since a box name means a login only on that system. Never logged and never put in an eval case.

## `recorded_login`, [line 213](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L213): Docstring

> The tagged sign-in job that lands on the connection's own system: the
> `worked` half of `checks.signs_in_to`, the same key the mining pass folds
> sign-ins by. A system no job lands on has no recorded login, and its own
> connection keys (or the operator) answer instead.
>
> Until the final review of audit wave 1 (2026-09-24, C-1) a lone
> credential-carrying job was lent to every connection. It starts on the
> identity provider's host, so the start-host match almost never held and
> the lone job won by default: system A's password was typed into system
> B's form, and B's refusal latched A's key. The landing is where the
> credential is good for; nothing else picks the job.
>
> Two jobs landing on one system with nothing to tell them apart is None:
> guessing whose account to sign in with is not a choice to make.
>
> The username is the last non-secret value typed at or before the
> credential -- the identifier box, by position, not by label.

## `recorded_logins`, [line 237](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L237): Design

> Every tagged sign-in job that lands somewhere, read by the same
> `_typed_login` as `recorded_login`: the username typed before its
> credential. A job value is never a login (R1 review, I9): the reader's own
> scan of every job's evidence made "GT7", typed before a session-expiry
> password re-entry in a work job, a login for the whole tenant. Collecting
> is not choosing (R1 re-review 1, item 1): two sign-in copies on one system
> lend no credential, but both their names are logins -- the QA store has
> such copies, and "exactly one" turned the rule off there.
> ponytail: the operator's vault login is not consulted (listing accounts
> needs a new port, GC13); add it when a sign-in was never recorded.
