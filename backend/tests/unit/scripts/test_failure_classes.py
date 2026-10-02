from itertools import pairwise
from types import SimpleNamespace
from typing import Any

import pytest
from scripts.measure import CLASSES, class_of, failure_classes


@pytest.mark.parametrize(
    ("verdict", "reason", "expected"),
    [
        (
            "unclear",
            "'Save' was sent and nothing confirms it; check it and answer",
            "unconfirmed_write",
        ),
        ("failed", "sign-in failed: TimeoutError", "sign_in"),
        ("failed", "no usable password is stored for U at host", "sign_in"),
        ("failed", "control_not_found", "not_found"),
        ("failed", "the recorded frame is no longer on the page", "not_found"),
        ("failed", "no recorded control to act on", "not_found"),
        ("failed", "the system rejected the write: already exists", "duplicate"),
        ("failed", "the page did not settle", "timing"),
        ("unclear", "sent by an earlier attempt, never settled", "wrong_resume"),
        ("failed", "the operator says it was not done; it is tried again", "wrong_resume"),
        ("failed", "something nobody classified", "other"),
    ],
)
def test_a_step_s_reason_names_its_failure_class(verdict: str, reason: str, expected: str) -> None:
    assert class_of(verdict, reason) == expected


@pytest.mark.parametrize(
    "verdict",
    ["held", "withheld", "skipped", "not_needed", "refused", "awaiting", "done_by_operator"],
)
def test_a_step_that_did_not_fail_has_no_failure_class(verdict: str) -> None:
    assert class_of(verdict, "the operator says it was not done") == ""


def test_every_class_the_spec_names_is_counted() -> None:
    assert set(CLASSES) >= {
        "unconfirmed_write",
        "sign_in",
        "not_found",
        "duplicate",
        "timing",
        "wrong_resume",
    }


@pytest.mark.parametrize(
    ("verdict", "reason", "by", "expected"),
    [
        ("failed", "dev_ID has no channel open", "none", "no_browser"),
        (
            "failed",
            "no_tab_for_system: no tab is open on https://host, which is the system",
            "none",
            "no_browser",
        ),
        ("failed", "not_actionable: the page did not answer", "none", "no_browser"),
        (
            "failed",
            "unreachable: TypeError: Failed to fetch, and the form was never filled",
            "none",
            "no_browser",
        ),
        ("failed", "the browser is on None, not https://host/portal", "read", "no_browser"),
        (
            "failed",
            "The browser is currently at null, so I must navigate to the step page first.",
            "none",
            "no_browser",
        ),
        (
            "failed",
            "the browser is on https://host/authresp, and this step was demonstrated on https://other",
            "none",
            "wrong_page",
        ),
        ("failed", "nobody approved the write within N minutes", "none", "no_approval"),
        ("failed", "stopped while waiting for approval", "none", "no_approval"),
        (
            "failed",
            "nobody gave a value for To recipients, and your mail does not say either",
            "none",
            "missing_value",
        ),
        (
            "failed",
            "the mail's recipients could not be read: it names nobody",
            "none",
            "missing_value",
        ),
        ("failed", "no usable password is stored for U at host", "none", "sign_in"),
        ("failed", "nobody signed in to https://host within N minutes", "none", "sign_in"),
        ("failed", "stopped while waiting for a signed-in browser", "none", "sign_in"),
        (
            "unclear",
            "a credential field is masked, so the screen cannot say it was typed",
            "screen",
            "sign_in",
        ),
        ("failed", "step N was given A, B and a click cannot carry a value", "none", "not_found"),
        (
            "failed",
            "another run of this job made this write with these values in the last half hour",
            "none",
            "duplicate",
        ),
        (
            "failed",
            "state unknown after a write; not retried: the screen said so",
            "screen",
            "unconfirmed_write",
        ),
        ("failed", "Q could not be done: sight has no page or no model", "sight", "no_model"),
        ("failed", "the mail could not be written: the model said nothing", "none", "no_model"),
        (
            "failed",
            "The Delete button remains disabled because the row was not selected.",
            "screen",
            "screen_disagrees",
        ),
        (
            "failed",
            "The browser is currently not on the step page, so it needs to navigate",
            "none",
            "wrong_page",
        ),
        (
            "failed",
            "the browser is currently not loaded on the required page, so navigate to it.",
            "none",
            "no_browser",
        ),
        ("failed", "the browser is not currently on any page, so navigate", "none", "no_browser"),
        ("failed", "the password for U at host was refused; stopped", "api", "sign_in"),
        ("failed", "step N types a password and nothing is stored under Q", "none", "sign_in"),
        (
            "failed",
            "the open email is for customer type A rather than the requested type B.",
            "screen",
            "screen_disagrees",
        ),
        (
            "failed",
            "the screen remains on the list table without opening the creation form",
            "screen",
            "screen_disagrees",
        ),
        (
            "failed",
            "the search filter is set to Q instead of filtering by type",
            "screen",
            "screen_disagrees",
        ),
        ("failed", "could not navigate: aborted: this run was aborted", "none", "other"),
        ("failed", "something nobody classified", "none", "other"),
    ],
)
def test_a_reason_shape_seen_on_qa_names_its_class(
    verdict: str, reason: str, by: str, expected: str
) -> None:
    assert class_of(verdict, reason, by) == expected


_PHRASE = {
    "unconfirmed_write": "Q was sent and nothing confirms it",
    "wrong_resume": "sent by an earlier attempt, never settled",
    "missing_value": "nobody gave a value for Password",
    "sign_in": "no usable password is stored for U",
    "duplicate": "the system refused it: Record already exists",
    "no_approval": "nobody approved the write within N minutes",
    "no_model": "the model did not answer",
    "no_browser": "not_actionable: the page did not answer",
    "not_found": "control_not_found",
    "timing": "the page did not settle",
    "wrong_page": "the browser is on https://host",
}
_ORDER = list(_PHRASE)


@pytest.mark.parametrize(("first", "later"), list(pairwise(_ORDER)))
def test_when_a_reason_names_two_causes_the_earlier_rule_wins(first: str, later: str) -> None:
    for reason in (f"{_PHRASE[first]}; {_PHRASE[later]}", f"{_PHRASE[later]}; {_PHRASE[first]}"):
        assert class_of("failed", reason) == first


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("nobody gave a value for Password", "missing_value"),
        ("the browser is on https://host; control_not_found", "not_found"),
        ("no recorded control; the browser is on https://host", "not_found"),
        ("the page did not settle ... nothing confirms it", "unconfirmed_write"),
        ("the model did not answer", "no_model"),
        ("the Save button is not loaded", "other"),
        ("the field is null", "other"),
        ("the Save button is on any page", "other"),
        ("it did not assign interface access", "other"),
        ("a design in progress", "other"),
    ],
)
def test_collision_probes(reason: str, expected: str) -> None:
    assert class_of("failed", reason) == expected


@pytest.mark.parametrize(
    ("verdict", "reason", "expected"),
    [
        ("failed", "The Save button remains disabled", "screen_disagrees"),
        ("failed", "something nobody classified", "other"),
        ("unclear", "The Save button remains disabled", "other"),
    ],
)
def test_screen_disagrees_is_a_failed_verdict_with_the_screens_words(
    verdict: str, reason: str, expected: str
) -> None:
    assert class_of(verdict, reason, "screen") == expected


async def test_failure_classes_counts_failing_steps_and_names_the_denominator() -> None:
    rows = [
        ("failed", "control_not_found", "none"),
        ("unclear", "Q was sent and nothing confirms it", "screen"),
        ("held", "fine", "status"),
        ("not_needed", None, None),
    ]

    class Db:
        async def execute(self, sql: Any, args: Any) -> Any:
            data = [("sight", 2)] if "known_broken" in str(sql) else rows
            return SimpleNamespace(all=lambda: data)

    section = await failure_classes(Db(), None)
    by_label = {line.label: line for line in section.lines}
    assert by_label["steps in class not_found"].value == 1
    assert by_label["steps in class unconfirmed_write"].value == 1
    assert by_label["steps in class not_found"].of == 2
    assert "of the failing steps" in section.why
    assert by_label["known_broken fingerprints on lane sight"].value == 2
