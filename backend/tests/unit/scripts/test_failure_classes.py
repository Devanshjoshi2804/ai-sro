import pytest
from scripts.measure import CLASSES, class_of


@pytest.mark.parametrize(
    ("verdict", "reason", "expected"),
    [
        (
            "unclear",
            "'Save' was sent and nothing confirms it; check it and answer",
            "unconfirmed_write",
        ),
        ("failed", "sign-in failed: TimeoutError", "sign_in"),
        ("failed", "the page asked for a password nobody gave", "sign_in"),
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
