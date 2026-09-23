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
> **Every cited gesture on that host, not merely one.** `Log in to Keycloak`
> cites one b2clogin gesture -- the operator crossed from the chooser into
> Keycloak in the middle of it -- so a job that merely touches the host is not
> the job for it. The one that is entirely there is the one that does exactly
> this page and nothing else.
>
> **One job or none.** Two jobs entirely on one sign-in host is two ways in, and
> picking between them is guessing with somebody's credentials.
>
> **Only a job found to sign in.** "Entirely on that host" alone is also
> every ordinary job done on one host, so a run bounced to a page the tenant
> had worked on would have spliced that work in. The candidates are the jobs
> whose `Workflow.signs_in` the mining pass set -- a credential typed and
> nothing written back, `checks.signs_in` -- and the host then picks among
> them.

## module, [line 25](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L25): Note on the line above

Code: `_SIGN_IN_PATHS = ("/oauth2/", "/protocol/openid-connect/", "/login-actions/", "/saml2/")`

> Paths an identity provider serves its sign-in pages under: Azure B2C's
> chooser (`…/oauth2/v2.0/authorize`), Keycloak's form (`…/protocol/openid-connect/
> auth`, and `…/login-actions/authenticate` once it has been posted once), SAML.

## `signs_in_at`, [line 11](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L11): Docstring

> The job that signs in at this page, or None where nothing does.
>
> `where` is where the browser actually is -- `Look.elsewhere` when a step
> found no tab on its own system, which is what an interruption looks like
> from the inside.
>
> `not_this` is the job being run, which can never be its own way back in.

## `is_sign_in_page`, [line 28](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L28): Docstring

> Whether this page belongs to an identity provider's sign-in.
>
> A click there can sign somebody in and nothing else -- no warehouse record
> is on an identity provider. Measured on the deployment 2026-09-23,
> `run_0133f4ce`: the click on the Azure chooser recorded no traffic, so it
> was a possible write by the silent-click rule, and when the page had not
> moved yet the run ended "state unknown after a write; not retried" on a
> sign-in link.

## `_entirely_at`, [line 33](../../../../../../../backend/src/sro/domain/skill/signing_in.py#L33): Docstring

> Whether every gesture this job cites happened on that origin.
