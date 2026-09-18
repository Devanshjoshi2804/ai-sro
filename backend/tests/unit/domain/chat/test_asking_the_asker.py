"""The mail a run writes to whoever asked, when only they can answer.

The panel's question works because somebody is standing in front of it. This
is for the case where nobody is: a request naming a description and no code,
a mailbox that does not say either, and an asker who is not the operator and
not watching anything.

What these pin is the wording, because the wording is the whole artifact -- it
leaves the company over the operator's name and cannot be unsent.
"""

from __future__ import annotations

from sro.domain.chat.asking import Pending
from sro.domain.chat.asking_the_asker import draft_for, worth_asking

JOB = "Create a Customer Type"


def _short(**over: object) -> Pending:
    fields: dict[str, object] = {
        "workflow_id": "wfl_1",
        "title": JOB,
        "values": {"Customer Type Description": "Leaning new SRO type 052"},
        "missing": ("Customer Type",),
    }
    fields.update(over)
    return Pending(**fields)  # type: ignore[arg-type]


def test_a_value_that_will_not_fit_is_asked_about_with_the_number() -> None:
    """A person told only "I need the Customer Type" sends back the one they
    already sent. The number is what makes one reply enough."""
    subject, body = draft_for(
        _short(
            values={"Customer Type": "NEWSROTEST", "Customer Type Description": "north dock"},
            limits={"Customer Type": 4},
        ),
        about="Customer type for the SRO pilot, round thirty",
    )

    assert subject == "Re: Customer type for the SRO pilot, round thirty"
    assert "needs to be 4 characters or fewer" in body
    assert "The request said NEWSROTEST, which is 10." in body
    # And what is already established, so they can see this is their request.
    assert "Customer Type Description: north dock" in body


def test_a_value_nobody_could_find_says_so_rather_than_quoting_a_limit() -> None:
    subject, body = draft_for(_short(), about="Customer type for the SRO pilot")

    assert "I still need Customer Type, and I could not find it in the thread." in body
    assert "characters" not in body
    assert subject.startswith("Re: ")


def test_one_question_a_mail_and_the_rest_named_after_it() -> None:
    """The same rule the panel keeps. A list of four is a mail somebody answers
    one line of."""
    _, body = draft_for(_short(missing=("Customer Type", "Department", "Region")))

    assert "I still need Customer Type" in body
    assert "(I will need Department, Region after that.)" in body


def test_it_never_suggests_the_value() -> None:
    """ "The code must be four characters" is a fact about the system. "Call it
    NSRO" is this system inventing a customer type, which is the guess the
    whole ladder refuses."""
    _, body = draft_for(
        _short(values={"Customer Type": "NEWSROTEST"}, limits={"Customer Type": 4}),
    )

    # It quotes back what they sent and says what is wrong with it. It offers
    # nothing in its place.
    assert "NEWSROTEST" in body
    assert "NSRO" not in body
    assert "suggest" not in body.lower()
    assert "why not" not in body.lower()


def test_a_request_with_no_name_gets_a_subject_that_is_not_invented() -> None:
    """A mail with a made-up subject is one nobody recognises."""
    subject, _ = draft_for(_short())

    assert subject == f"{JOB} — one thing missing"


def test_it_says_who_it_is_for_and_what_sent_it() -> None:
    """Somebody receiving "what should the Customer Type be?" from a system
    they have never heard of deletes it, and rightly."""
    _, body = draft_for(_short(), signed="devansh")

    assert "Sent for devansh by AI-SRO." in body
    # And says what to do with it, because a mail nobody knows how to answer is
    # a mail nobody answers.
    assert "Reply to this mail" in body


def test_a_title_keeps_its_case() -> None:
    """A mined title is a noun phrase, and folding its case makes it read as an
    instruction: "I am setting up create a customer type"."""
    _, body = draft_for(_short())

    assert f"I am working on {JOB} from your request" in body


def test_a_run_short_of_nothing_is_not_worth_a_mail() -> None:
    """A mail that says "I need nothing" is a mail that should not have been
    sent. This system is careful about what it puts in somebody's inbox."""
    assert worth_asking(_short()) is True
    assert worth_asking(_short(missing=())) is False
    assert worth_asking(_short(workflow_id="")) is False
