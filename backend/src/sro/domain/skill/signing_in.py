"""Which job of this tenant's signs in at the page a run is stuck on.

A run meets a sign-in page for one reason -- the session it was relying on has
gone -- and stopping there is the wrong answer twice over: the operator has to
notice, and the request they made goes nowhere until they do. On a system
somebody works in all day, sessions expire mid-flow, and so do dialogs, consent
screens and error pages. A system that only reports those is a system somebody
has to sit next to.

**And the way back in is already mined.** Measured on the deployment
2026-09-19, tenant `greyorange`:

    Log in using Azure B2C SSO   1  Click the 'Local WMS users (bf56-001-eus2)
                                    (SSO)'          blueyonderalphaus.b2clogin.com
                                 2  Click the SSO button to proceed
    Log in to Keycloak           0  Enter username or email   keycloak-…byp.ai
                                 1  Type the password

The operator has signed in through that chooser many times with the recorder
on, so the clicks are evidence like any other. This is the lookup from "the
browser is sitting on `blueyonderalphaus.b2clogin.com`" to "the job whose
evidence is that page".

**By the host, never by the title.** `Log in using Azure B2C SSO` is a model's
sentence about a job; the host is a fact about where the gestures happened. A
name match would also pick `Log in to Google Account` for a warehouse that
bounced to Google, which is a run signing into the wrong system.

**Every cited gesture on that host, not merely one.** `Log in to Keycloak`
cites one b2clogin gesture -- the operator crossed from the chooser into
Keycloak in the middle of it -- so a job that merely touches the host is not
the job for it. The one that is entirely there is the one that does exactly
this page and nothing else.

**One job or none.** Two jobs entirely on one sign-in host is two ways in, and
picking between them is guessing with somebody's credentials.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from sro.domain.observation.gesture import Gesture
from sro.domain.shared.hosts import origin_of
from sro.domain.skill.workflow import Workflow


def signs_in_at(
    where: str, among: Sequence[Workflow], by_id: Mapping[str, Gesture], *, not_this: str = ""
) -> str | None:
    """The job that signs in at this page, or None where nothing does.

    `where` is where the browser actually is -- `Look.elsewhere` when a step
    found no tab on its own system, which is what an interruption looks like
    from the inside.

    `not_this` is the job being run, which can never be its own way back in.
    """
    origin = origin_of(where)
    if not origin:
        return None
    found = [job.id for job in among if job.id != not_this and _entirely_at(job, origin, by_id)]
    return found[0] if len(found) == 1 else None


def is_a_way_in(job: Workflow, by_id: Mapping[str, Gesture]) -> bool:
    """Whether this job does nothing but sign in somewhere.

    `signs_in_at` asks which job gets a run back into a named page. This asks
    the same thing of a job on its own: every gesture it cites happened on one
    origin, and that is what a sign-in is -- a chooser, a form, a button, all
    on the identity provider and nothing anywhere else. A job that touches a
    second system is doing work there, whatever it did first.

    Nothing about the title. `Log in using Azure B2C SSO` is a model's sentence
    about a job, and a job that signed in and then created a customer type
    would wear the same one.
    """
    cited = [by_id[one] for step in job.steps for one in step.cites if one in by_id]
    if not cited:
        return False
    where = {origin_of(one.url or one.system or "") for one in cited}
    return len(where) == 1 and bool(next(iter(where)))


def _entirely_at(job: Workflow, origin: str, by_id: Mapping[str, Gesture]) -> bool:
    """Whether every gesture this job cites happened on that origin."""
    cited = [by_id[one] for step in job.steps for one in step.cites if one in by_id]
    if not cited:
        return False
    return all(origin_of(one.url or one.system or "") == origin for one in cited)


__all__ = ["is_a_way_in", "signs_in_at"]
