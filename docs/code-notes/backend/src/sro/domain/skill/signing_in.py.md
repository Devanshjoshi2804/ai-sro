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

## module, [line 26](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L26): Note on the line above

Code: `_SIGN_IN_PATHS = ("/oauth2/", "/protocol/openid-connect/", "/login-actions/", "/saml2/")`

> Paths an identity provider serves its sign-in pages under: Azure B2C's
> chooser (`…/oauth2/v2.0/authorize`), Keycloak's form (`…/protocol/openid-connect/
> auth`, and `…/login-actions/authenticate` once it has been posted once), SAML.

## `signs_in_at`, [line 12](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L12): Docstring

> The job that signs in at this page, or None where nothing does.
>
> `where` is where the browser actually is -- `Look.elsewhere` when a step
> found no tab on its own system, which is what an interruption looks like
> from the inside.
>
> `not_this` is the job being run, which can never be its own way back in.

## `is_sign_in_page`, [line 29](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L29): Docstring

> Whether this page belongs to an identity provider's sign-in.
>
> A click there can sign somebody in and nothing else -- no warehouse record
> is on an identity provider. Measured on the deployment 2026-09-23,
> `run_0133f4ce`: the click on the Azure chooser recorded no traffic, so it
> was a possible write by the silent-click rule, and when the page had not
> moved yet the run ended "state unknown after a write; not retried" on a
> sign-in link.

## `_starts_at`, [line 34](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L34): Docstring

> The origin of the first gesture this job cites, in time; the job's own step
> order breaks a tie.

## `sign_in_chain`, [line 42](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L42): Function

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

## `RecordedLogin`, [line 64](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L64): Class

> What a recorded sign-in says about credentials: the origin the password was
> typed on, which names its vault key, and the username typed before it.

## `recorded_login`, [line 70](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L70): Docstring

> The job that starts on the system's own page, when there is one
> (`signs_in_at`); otherwise the only tagged sign-in job that carries a
> credential at all. On the deployed tenant the credential-carrying job starts
> on the identity provider's host, not the system's, so the second rule is the
> one that finds it. Two candidates with nothing to tell them apart is None:
> guessing whose account to sign in with is not a choice to make.
>
> The username is the last non-secret value typed at or before the
> credential -- the identifier box, by position, not by label.
