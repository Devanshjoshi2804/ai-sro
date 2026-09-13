"""What a step's own post-conditions catch, one kind at a time.

`check`, `check_text` and `check_on_screen` are the authored skill's half of
verification -- assertions somebody wrote down, checked against one answer --
and they were reached only through `execute_skill`, where one status assertion
stood in for all four kinds. A mutation sweep on 2026-09-13 inverted
`RESPONSE_FIELD_PRESENT` in both readers and the suite stayed green: a skill
whose post-condition is "the answer carries an id" would have passed on an
answer carrying none, and a run that failed would have read as clean and
counted towards the version's promotion.

Verification is what stands between a model and a warehouse. Each kind gets a
test that holds and a test that does not.
"""

from __future__ import annotations

from types import MappingProxyType

from sro.application.execution.verify import check, check_on_screen, check_text, extract
from sro.application.ports.http import HttpResponse
from sro.domain.skill.assertion import Assertion, AssertionKind
from sro.domain.skill.template import Template

VALUES = {"shipment_id": "SH-4471"}


def _answered(text: str = '{"id": "ORD-1", "status": "open"}', status: int = 200) -> HttpResponse:
    return HttpResponse(status_code=status, headers=MappingProxyType({}), text=text)


def _asserting(kind: AssertionKind, *, expected: str = "", pointer: str | None = None) -> Assertion:
    return Assertion(kind=kind, expected=Template(expected), pointer=pointer)


def test_a_status_that_matches_is_no_failure_and_one_that_does_not_says_both() -> None:
    asserted = (_asserting(AssertionKind.HTTP_STATUS, expected="200"),)

    assert check(asserted, _answered(), values=VALUES) == ()
    # The sentence carries what was wanted AND what came back: "assertion 2
    # failed" tells the person reading the run afterwards nothing.
    (failure,) = check(asserted, _answered(status=500), values=VALUES)
    assert "200" in failure and "500" in failure


def test_a_field_the_answer_does_not_carry_is_a_failure_and_names_itself() -> None:
    asserted = (_asserting(AssertionKind.RESPONSE_FIELD_PRESENT, pointer="/id"),)

    assert check(asserted, _answered(), values=VALUES) == ()

    (failure,) = check(asserted, _answered(text='{"status": "open"}'), values=VALUES)
    assert "/id" in failure


def test_a_field_that_holds_the_wrong_value_is_not_a_field_that_is_missing() -> None:
    """Two different sentences on purpose: one says the system answered
    something else, the other says it answered nothing there at all, and the
    person reading the run does different things about them."""
    asserted = (
        _asserting(AssertionKind.RESPONSE_FIELD_EQUALS, expected="open", pointer="/status"),
    )

    assert check(asserted, _answered(), values=VALUES) == ()

    (wrong,) = check(asserted, _answered(text='{"status": "cancelled"}'), values=VALUES)
    assert "cancelled" in wrong and "open" in wrong

    (absent,) = check(asserted, _answered(text='{"id": "ORD-1"}'), values=VALUES)
    assert "has no /status" in absent


def test_a_screen_assertion_is_never_passed_by_a_network_replay() -> None:
    """Reported as a failure rather than skipped. A UI assertion silently
    counted as satisfied is how a replay convinces itself it produced a result
    nobody saw."""
    asserted = (_asserting(AssertionKind.UI_TEXT_VISIBLE, expected="Saved"),)

    (failure,) = check(asserted, _answered(), values=VALUES)
    assert "Saved" in failure and "replay" in failure


def test_a_value_the_run_supplied_is_what_the_assertion_is_rendered_with() -> None:
    # The template is the point: an assertion written once has to check the
    # value THIS run was asked for, not the one the demonstration carried.
    # `$name`, not a brace: recorded payloads are JSON, and one missed escape
    # in a brace syntax turns a literal into a phantom parameter.
    asserted = (
        _asserting(
            AssertionKind.RESPONSE_FIELD_EQUALS, expected="$shipment_id", pointer="/shipment"
        ),
    )

    assert check(asserted, _answered(text='{"shipment": "SH-4471"}'), values=VALUES) == ()
    (failure,) = check(asserted, _answered(text='{"shipment": "SH-9999"}'), values=VALUES)
    assert "SH-4471" in failure


def test_a_tool_answer_is_checked_for_its_fields_and_says_so_about_the_rest() -> None:
    """A connector answers a document, not an HTTP exchange. The two kinds that
    read a document are checked; the two that read something else are reported
    as unmet rather than skipped, because a status assertion on a tool step is
    a mistake in the mapping and a mistake nothing mentions is a step that
    verified less than whoever wrote it believed."""
    present = (_asserting(AssertionKind.RESPONSE_FIELD_PRESENT, pointer="/id"),)

    assert check_text(present, '{"id": "ORD-1"}', values=VALUES) == ()
    (missing,) = check_text(present, '{"status": "open"}', values=VALUES)
    assert "/id" in missing

    (unmet,) = check_text(
        (_asserting(AssertionKind.HTTP_STATUS, expected="200"),), '{"id": "x"}', values=VALUES
    )
    assert "no status code" in unmet


def test_a_tool_answer_that_is_not_a_document_at_all_fails_rather_than_passes() -> None:
    # `_parse` of something unparseable must not leave every field assertion
    # trivially satisfied.
    (failure,) = check_text(
        (_asserting(AssertionKind.RESPONSE_FIELD_PRESENT, pointer="/id"),),
        "an outage page",
        values=VALUES,
    )
    assert "/id" in failure


def test_the_screen_rung_checks_what_it_can_see_and_names_what_it_cannot() -> None:
    """A gesture landing is not a task being done: the driver answers
    "performed" when it found a control and clicked it. What is checkable here
    is the text the demonstration showed afterwards."""
    asserted = (
        _asserting(AssertionKind.UI_TEXT_VISIBLE, expected="Saved"),
        _asserting(AssertionKind.RESPONSE_FIELD_PRESENT, pointer="/id"),
    )

    failures, unchecked = check_on_screen(asserted, "Work area saved", values=VALUES)

    # Case-insensitive: the screen said "saved" inside a longer sentence.
    assert failures == ()
    assert unchecked == ("response_field_present",)

    failures, _ = check_on_screen(asserted, "Server error", values=VALUES)
    assert failures and "Saved" in failures[0]


def test_a_derived_value_comes_back_only_when_the_answer_really_carries_it() -> None:
    assert extract(_answered(), "/id") == "ORD-1"
    assert extract(_answered(text='{"status": "open"}'), "/id") is None
