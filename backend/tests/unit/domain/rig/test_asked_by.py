"""What counts as a mail a job was asked for by.

The corpus behind meaning-matching, and every rule in it is a place where a
prompt could be taught noise or, worse, handed somebody's old request as an
answer to copy.
"""

from __future__ import annotations

from sro.domain.chat.asked_by import K_EXAMPLES, K_LEAST, K_TEXT, mails_behind, texts
from sro.domain.observation.gesture import Action, Gesture, Target
from sro.domain.skill.workflow import Step, Workflow

MAILBOX = "https://mail.google.com"
WMS = "https://bf56-kms-wms-web-np2.jdadelivers.com"


def _gesture(gesture_id: str, *, said: str, at: float, where: str = MAILBOX) -> Gesture:
    return Gesture(
        id=gesture_id,
        tenant="greyorange",
        stream_id="str-1",
        batch_id="bat-1",
        at=at,
        url=f"{where}/mail/u/0/#inbox/abc",
        system=where,
        tab_id=7,
        frame_url=None,
        action=Action(kind="click", at=at, url=where, target=Target(name=said)),
    )


def _job(*cites: list[str]) -> Workflow:
    return Workflow(
        id="wfl_1",
        tenant="greyorange",
        title="Create a Customer Type",
        narrative="open the mail, open the screen, type the code, save",
        steps=[
            Step(order=order, says=f"step {order}", system=None, cites=list(named))
            for order, named in enumerate(cites)
        ],
    )


def test_the_mails_the_job_was_asked_for_by_are_read_off_what_it_cites() -> None:
    """Measured on the deployment 2026-09-16: `Create a Customer Type` cites
    five gestures on the operator's mailbox, each carrying the mail's own
    words. Nobody marked them and nobody typed a rule."""
    job = _job(["m-1", "m-2"], ["wms-1"])
    by_id = {
        "m-1": _gesture("m-1", said="a customer type :- GGD description :- new SRO type 01", at=10),
        "m-2": _gesture(
            "m-2", said="a customer type :- GKB description :- new SRO type 002", at=20
        ),
        "wms-1": _gesture("wms-1", said="Save the customer type record", at=30, where=WMS),
    }

    said = texts(mails_behind(job, by_id))

    assert said == [
        "a customer type :- GKB description :- new SRO type 002",
        "a customer type :- GGD description :- new SRO type 01",
    ], "newest first, and the warehouse click is not a request"


def test_a_job_demonstrated_from_a_page_has_no_examples_and_gets_none_invented() -> None:
    """`Delete a Customer Type` cites no mailbox gesture at all. The honest
    half: it is matched on its title and narrative exactly as before."""
    job = _job(["wms-1"])

    assert mails_behind(job, {"wms-1": _gesture("wms-1", said="Delete", at=1, where=WMS)}) == ()


def test_one_request_read_five_times_is_one_example() -> None:
    """A demonstration records the same row click several times -- five cited
    gestures on this deployment's own job are three distinct requests -- and
    five copies of one mail would be one example wearing the weight of five."""
    same = "a customer type :- GKB description :- leaning new SRO type 002"
    job = _job(["m-1", "m-2", "m-3"])
    by_id = {
        "m-1": _gesture("m-1", said=same, at=10),
        "m-2": _gesture("m-2", said=same, at=20),
        "m-3": _gesture("m-3", said=same, at=30),
    }

    (only,) = mails_behind(job, by_id)

    assert only.text == same
    assert only.at == 30, "the same request read twice is dated when it was last read"


def test_furniture_is_not_a_request() -> None:
    """The cited gesture on a mailbox is sometimes a toolbar: "Inbox",
    "Archive", "More". Those match everything and mean nothing."""
    job = _job(["m-1", "m-2"])
    by_id = {
        "m-1": _gesture("m-1", said="Archive", at=10),
        "m-2": _gesture("m-2", said="x" * K_LEAST, at=20),
    }

    assert texts(mails_behind(job, by_id)) == ["x" * K_LEAST]


def test_a_mail_reaches_a_prompt_as_an_example_and_never_as_correspondence() -> None:
    """Five of these go into every reading of every sentence. A subject and the
    line under it is an example set; a whole thread is somebody's mail in a
    prompt that grows with the tenant's history."""
    job = _job([f"m-{n}" for n in range(K_EXAMPLES + 3)])
    by_id = {
        f"m-{n}": _gesture(f"m-{n}", said=f"customer type request {n} " + "y" * K_TEXT, at=n)
        for n in range(K_EXAMPLES + 3)
    }

    said = mails_behind(job, by_id)

    assert len(said) == K_EXAMPLES
    assert all(len(one.text) <= K_TEXT + 1 for one in said)
    assert said[0].text.startswith(f"customer type request {K_EXAMPLES + 2}"), "newest first"
