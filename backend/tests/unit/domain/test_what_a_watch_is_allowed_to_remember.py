"""What a watch stores, and what it only ever points at.

A watch is the first stage of a mail arriving and the work happening by itself:
the operator opens one mail that is an example of the thing, marks the parts
that matter, and from then on their own browser recognises the next one.

Everything here is about the difference between two things the plan for it says
in one breath. A *term* is the operator's rule -- "from this sender", "subject
containing this phrase" -- and its text is theirs, written by pointing, so it
may be stored. A *value* is the order number, different in every mail, so there
is nothing to compare and nothing to keep: only where to find it. Collapse the
two and you get either a matcher that cannot tell one mail from another, or
mail bodies in a database, and the second one is the kind of mistake that ends
a deployment.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from sro.domain.shared.errors import InvariantViolation
from sro.domain.shared.identifiers import DeviceId, SkillId
from sro.domain.skill.locator import ControlLocator, LocatorStrategy
from sro.domain.skill.template import Template
from sro.domain.trigger.trigger import Trigger, TriggerId, TriggerKind
from sro.domain.trigger.watch import MAX_TERM, Term, TermField, ValueAt, Watch
from tests import factories as f

GMAIL = "mail.google.com"
FROM_THE_CUSTOMER = Term(field=TermField.SENDER, contains="@northwind.example")
ASKING_FOR_STATUS = Term(field=TermField.SUBJECT, contains="order status")
ORDER_NUMBER = ValueAt(
    name="order_id",
    where=ControlLocator(
        strategy=LocatorStrategy.CSS_PATH, query=Template("div.mail-body span.order-ref")
    ),
)
SENDER_IS_HERE = ControlLocator(strategy=LocatorStrategy.CSS_PATH, query=Template("span.gD[email]"))
SUBJECT_IS_HERE = ControlLocator(strategy=LocatorStrategy.CSS_PATH, query=Template("h2.hP"))


def _watch(**over: object) -> Watch:
    defaults: dict[str, object] = {
        "host": GMAIL,
        "terms": (FROM_THE_CUSTOMER, ASKING_FOR_STATUS),
        "values": (ORDER_NUMBER,),
        "sender_at": SENDER_IS_HERE,
        "subject_at": SUBJECT_IS_HERE,
    }
    return Watch(**{**defaults, **over})  # type: ignore[arg-type]


def _trigger(**over: object) -> Trigger:
    defaults: dict[str, object] = {
        "id": TriggerId("trg-1"),
        "tenant_id": f.TENANT,
        "skill_id": SkillId("skl-1"),
        "kind": TriggerKind.WATCH,
        "created_by": f.OPERATOR,
        "created_at": datetime(2026, 8, 29, tzinfo=UTC),
        "parameters": {"facility": "DC01"},
        "watch": _watch(),
        "device_id": DeviceId("dev-lena-laptop"),
    }
    return Trigger(**{**defaults, **over})  # type: ignore[arg-type]


# --- a watch names a host and at least one thing to match on ----------------


def test_a_watch_with_nothing_to_match_on_is_refused() -> None:
    """The rule this exists for. A watch is a standing offer to act on a mail;
    one with no terms is that offer made about every mail that arrives, which
    is not a trigger, it is an interruption."""
    with pytest.raises(InvariantViolation, match="every mail"):
        _watch(terms=())


def test_a_watch_names_the_host_it_runs_on() -> None:
    """A browser has every site in it. A watch with no host is a rule the
    extension would have to try everywhere, including the ones ADR 008 says it
    must never touch."""
    with pytest.raises(InvariantViolation, match="host"):
        _watch(host="   ")


def test_a_term_with_nothing_in_it_is_the_same_as_no_term_at_all() -> None:
    """`"" in subject` is true for every subject there has ever been, so a
    blank term is the no-terms case wearing a disguise."""
    with pytest.raises(InvariantViolation, match="every mail"):
        Term(field=TermField.SUBJECT, contains="  ")


# --- a watch without a device is refused ------------------------------------


def test_a_watch_with_no_browser_watches_nothing() -> None:
    """There is no server-side evaluation of a watch, deliberately: the mail is
    never uploaded, so nothing but the operator's own browser is in a position
    to look at it. A watch with no device is not a trigger that fires rarely --
    it is one that cannot fire, and it would sit in the list looking armed."""
    with pytest.raises(InvariantViolation, match="no browser"):
        _trigger(device_id=None)


def test_a_watch_with_a_browser_is_fine() -> None:
    assert _trigger().device_id == DeviceId("dev-lena-laptop")


# --- only a watch carries one -----------------------------------------------


def test_a_watch_trigger_without_a_watch_is_refused() -> None:
    with pytest.raises(InvariantViolation, match="watch for"):
        _trigger(watch=None)


def test_a_trigger_that_is_not_a_watch_carries_no_matcher() -> None:
    """A cron expression and a matcher are two answers to "when", and a trigger
    that held both would fire on whichever one somebody remembered."""
    with pytest.raises(InvariantViolation, match="nothing to watch"):
        _trigger(kind=TriggerKind.MANUAL, device_id=None)


# --- a term may hold text; nothing here may hold a mail ----------------------


def test_there_is_no_field_a_body_could_be_matched_against() -> None:
    """The structural half of the guard. Sender and subject are short, and are
    what an operator points at. A `BODY` member is not a small addition -- it
    would put correspondence in the control plane, which is the line ADR 008
    draws -- so it does not exist and this test is what makes adding one a
    decision rather than an afternoon."""
    assert set(TermField) == {TermField.SENDER, TermField.SUBJECT}


def test_a_pasted_mail_is_not_a_phrase_somebody_pointed_at() -> None:
    """The other half. A subject phrase is a few words; a term of several
    thousand characters is a body that arrived through the field that was
    allowed to hold text."""
    with pytest.raises(InvariantViolation, match="capped"):
        Term(field=TermField.SUBJECT, contains="x" * (MAX_TERM + 1))


def test_a_term_needs_somewhere_to_read_the_header_it_compares() -> None:
    """The half a term cannot supply.

    An operator's text is one side of the comparison; the other is a header on
    a page, and there is no standard for where that is -- Gmail, Outlook Web
    and a corporate webmail each render a mail their own way. A watch without
    the mark would leave the browser guessing a selector, and a guess that is
    wrong reads as a mail that never arrived: the watch sits in the list
    looking armed and cannot fire. Refused here, where somebody finds out
    while they are making it.
    """
    with pytest.raises(InvariantViolation, match="nowhere to read the sender"):
        _watch(sender_at=None)


def test_the_marks_are_not_values_and_are_never_sent_anywhere() -> None:
    """Why these are locators on the watch rather than two more `ValueAt`s.

    A value is a skill parameter and is uploaded on a match. The sender and
    the subject are the two things this design is most careful never to send,
    so a mechanism that carried them would put them in the body of the one
    request a match makes.
    """
    assert _watch().reads == ("order_id",)


def test_a_watch_that_matches_only_on_the_subject_needs_only_that_mark() -> None:
    """The rule is per header, not both-or-nothing: an operator who matched on
    the subject alone never pointed at a sender and should not have to."""
    only_subject = _watch(terms=(ASKING_FOR_STATUS,), sender_at=None)

    assert only_subject.matches(GMAIL, sender="anyone@anywhere.test", subject="order status")


def test_a_value_is_a_location_and_has_nowhere_to_put_the_text() -> None:
    """The distinction, asserted rather than described. The order number is
    read at match time and passed as a parameter; there is no field on
    `ValueAt` it could be stored in, so it cannot be stored by accident."""
    assert set(ValueAt.__dataclass_fields__) == {"name", "where"}
    assert isinstance(ORDER_NUMBER.where, ControlLocator)


def test_a_value_names_the_parameter_it_fills() -> None:
    with pytest.raises(InvariantViolation, match="parameter"):
        ValueAt(name=" ", where=ORDER_NUMBER.where)


def test_two_places_to_read_one_parameter_is_one_too_many() -> None:
    """Silent otherwise: whichever came last wins, and which one that is
    depends on the order the operator happened to click in."""
    with pytest.raises(InvariantViolation, match="one too many"):
        _watch(values=(ORDER_NUMBER, ORDER_NUMBER))


# --- what the matcher actually decides --------------------------------------


def test_a_mail_that_matches_every_term_is_one_of_these() -> None:
    assert _watch().matches(
        GMAIL, sender="ops@northwind.example", subject="Order status for PO 4471?"
    )


def test_the_terms_are_all_of_them_not_any_of_them() -> None:
    """Narrowing is the safe direction to be wrong in: a miss costs a mail
    nobody was offered help with, and a false match costs a proposal about
    somebody's payroll. An "or" is two watches, which is also how an operator
    would say it."""
    assert not _watch().matches(
        GMAIL, sender="hr@acme.example", subject="Order status for PO 4471?"
    )


def test_nobody_writes_a_subject_the_way_they_typed_it_yesterday() -> None:
    assert _watch().matches(GMAIL, sender="OPS@Northwind.Example", subject="ORDER STATUS: 4471")


def test_a_lookalike_host_is_not_the_mailbox_this_was_made_for() -> None:
    """`domain_matches` rather than a suffix test, for the reason it exists:
    `notmail.google.com`.endswith(`mail.google.com`) is true."""
    assert not _watch().matches(
        "notmail.google.com", sender="ops@northwind.example", subject="order status"
    )


def test_a_subdomain_of_the_watched_host_still_counts() -> None:
    assert _watch(host="acme.example").matches(
        "mail.acme.example", sender="ops@northwind.example", subject="order status"
    )


# --- what a matching mail is allowed to supply ------------------------------


def test_the_mail_fills_the_values_the_operator_pointed_at() -> None:
    values = _trigger().values_from({"order_id": "4471"})

    assert values == {"facility": "DC01", "order_id": "4471"}


def test_a_mail_cannot_redirect_the_read_at_another_warehouse() -> None:
    """The same rule an inbound trigger has, reached by a different route: the
    names a watch may be told are exactly the ones it was pointed at, so a page
    that puts `facility` in its payload changes nothing."""
    values = _trigger().values_from({"order_id": "4471", "facility": "OTHER_DC"})

    assert values["facility"] == "DC01"


def test_the_names_come_from_where_they_are_read_and_nowhere_else() -> None:
    """One list, not two. A second list of names would be a second thing to
    keep in step, and the failure when it drifts is the mail's value being
    dropped for having the wrong name -- silently, every time it fires."""
    assert _trigger().from_message == ("order_id",)

    with pytest.raises(InvariantViolation, match="second list"):
        _trigger(from_message=("order_id",))


def test_a_watch_that_reads_nothing_still_fires() -> None:
    """A watch whose skill takes no values from the mail is a normal thing --
    "when the nightly exception report lands, run the reconciliation"."""
    trigger = _trigger(watch=_watch(values=()))

    assert trigger.from_message == ()
    assert trigger.values_from({"order_id": "4471"}) == {"facility": "DC01"}


# --- the rules a watch inherits ---------------------------------------------


def test_a_watch_that_writes_still_names_who_stands_behind_it() -> None:
    """Unchanged by any of this. A mail arriving is not a person deciding, so
    a watch that starts a write is exactly the case that rule was written for.
    """
    with pytest.raises(InvariantViolation, match="who authorised it"):
        _trigger(writes=True)


def test_a_watch_does_not_also_run_on_a_clock() -> None:
    with pytest.raises(InvariantViolation, match="does not run on a schedule"):
        _trigger(cron="0 6 * * 1-5")


def test_a_watch_is_not_reachable_by_a_token() -> None:
    """An inbound trigger has a secret because a relay presents one. Nothing
    presents anything to a watch -- the browser already holds it -- so a token
    on one is a credential that exists for no reason."""
    with pytest.raises(InvariantViolation, match="not reached by a token"):
        _trigger(inbound_token="a-secret")  # noqa: S106
