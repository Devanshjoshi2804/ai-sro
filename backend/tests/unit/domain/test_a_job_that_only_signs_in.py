"""Whether a job does nothing but sign in somewhere.

`signs_in_at` asks which job gets a run back into a named page. This asks the
same thing of a job on its own, and it is what lets a run tell "the page I sign
in at is gone because I signed in" from "I have failed".
"""

from __future__ import annotations

from sro.domain.observation.gesture import Action, Gesture
from sro.domain.skill.signing_in import is_a_way_in
from sro.domain.skill.workflow import Step, Workflow

KEYCLOAK = "https://keycloak-service-exec-wms-keycloak-prod.us.live.external.byp.ai"
WMS = "https://bf56-kms-wms-web-np2.jdadelivers.com"


def _at(gesture_id: str, url: str) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant="greyorange",
        stream_id="s",
        batch_id="b",
        at=1.0,
        url=f"{url}/page",
        system=url,
        tab_id=1,
        frame_url=None,
        action=Action(kind="click", at=1.0, url=f"{url}/page"),
    )


def _job(*cites: str) -> Workflow:
    return Workflow(
        id="wfl_1",
        tenant="greyorange",
        title="Log in to Keycloak",
        narrative="n",
        steps=[
            Step(order=n, says=f"step {n}", system=None, cites=[one]) for n, one in enumerate(cites)
        ],
    )


def test_a_job_entirely_on_one_identity_provider_is_a_way_in() -> None:
    store = {"a": _at("a", KEYCLOAK), "b": _at("b", KEYCLOAK)}

    assert is_a_way_in(_job("a", "b"), store) is True


def test_a_job_that_goes_on_to_do_something_is_not() -> None:
    """Whatever it did first. A job that signs in and then creates a customer
    type has work to finish, and its page going away is not the end of it."""
    store = {"a": _at("a", KEYCLOAK), "b": _at("b", WMS)}

    assert is_a_way_in(_job("a", "b"), store) is False


def test_the_title_says_nothing() -> None:
    """`Log in using Azure B2C SSO` is a model's sentence about a job, and a
    job that signed in and then did the work would wear the same one."""
    store = {"a": _at("a", WMS), "b": _at("b", WMS)}
    working = _job("a", "b")
    working.title = "Log in to Keycloak"

    # One origin, so it is a way in -- by its evidence, which is the only
    # thing that decides. And a two-system job keeps its title and is not.
    assert is_a_way_in(working, store) is True
    assert is_a_way_in(_job("a", "c"), {**store, "c": _at("c", KEYCLOAK)}) is False


def test_a_job_citing_nothing_anybody_kept_is_not_a_way_in() -> None:
    """Evidence that has aged out leaves a job nothing can be read off. A rule
    that answered True here would end a run on an absence."""
    assert is_a_way_in(_job("gone"), {}) is False
