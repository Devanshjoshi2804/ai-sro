"""Headers are diffed like any other value.

A header that carries meaning and varied between the runs is a parameter. A
header that varies for reasons of its own -- a trace id, a session cookie, a
Referer -- is not, and asking an operator to supply one would be nonsense.
"""

from __future__ import annotations

from sro.application.induction.diff import parameterise
from sro.application.induction.headers import build_header_plans
from sro.domain.recording.events import ActionFrame
from sro.domain.skill.parameter import ParameterKind
from tests import factories as f

Runs = tuple[tuple[ActionFrame, ...], tuple[ActionFrame, ...]]


def _runs(headers_a: dict[str, str], headers_b: dict[str, str]) -> Runs:
    """Two one-step runs of the same task, differing only in headers."""
    run_a = (f.frame(requests=(f.request(request_headers=headers_a),)),)
    run_b = (f.frame(requests=(f.request(request_headers=headers_b),)),)
    return run_a, run_b


class TestVaryingHeaders:
    def test_a_semantic_header_that_varies_becomes_a_parameter(self) -> None:
        run_a, run_b = _runs(
            {"X-Warehouse-Id": "WH-1", "Content-Type": "application/json"},
            {"X-Warehouse-Id": "WH-2", "Content-Type": "application/json"},
        )

        result = parameterise(run_a, run_b)
        names = {p.name for p in result.parameters}

        assert "warehouse_id" in names
        parameter = next(p for p in result.parameters if p.name == "warehouse_id")
        assert parameter.kind is ParameterKind.INPUT
        assert set(parameter.observed_values) == {"WH-1", "WH-2"}

    def test_a_header_that_stayed_the_same_is_left_literal(self) -> None:
        run_a, run_b = _runs(
            {"X-Warehouse-Id": "WH-1", "X-Facility": "DC01"},
            {"X-Warehouse-Id": "WH-2", "X-Facility": "DC01"},
        )

        result = parameterise(run_a, run_b)

        assert "facility" not in {p.name for p in result.parameters}


class TestHeadersThatVaryOnTheirOwn:
    def test_session_noise_never_becomes_a_parameter(self) -> None:
        # Every one of these differs between two runs of an identical task.
        run_a, run_b = _runs(
            {
                "Authorization": "Bearer token-one",
                "Cookie": "session=aaa",
                "X-CSRF-Token": "csrf-one",
                "traceparent": "00-trace-one-01",
                "X-Trace": "0.0598866813",
                "X-Idempotency-Key": "key-one",
                "Referer": "https://wms.test/waves?wave=W-1001",
                "Content-Length": "42",
            },
            {
                "Authorization": "Bearer token-two",
                "Cookie": "session=bbb",
                "X-CSRF-Token": "csrf-two",
                "traceparent": "00-trace-two-01",
                "X-Trace": "0.6707475306",
                "X-Idempotency-Key": "key-two",
                "Referer": "https://wms.test/waves?wave=W-2002",
                "Content-Length": "43",
            },
        )

        result = parameterise(run_a, run_b)

        assert result.parameters == ()

    def test_a_header_present_in_only_one_run_is_not_a_difference(self) -> None:
        # Browsers add and drop sec-* headers on their own, and a header that is
        # missing has no value to parameterise.
        run_a, run_b = _runs({"X-Warehouse-Id": "WH-1"}, {})

        result = parameterise(run_a, run_b)

        assert result.parameters == ()


class TestTheEmittedPlan:
    def test_the_header_carries_the_placeholder_not_the_first_run_s_value(self) -> None:
        run_a, run_b = _runs({"X-Warehouse-Id": "WH-1"}, {"X-Warehouse-Id": "WH-2"})
        result = parameterise(run_a, run_b)

        plans = build_header_plans(
            run_a[0].requests[0],
            target_system="blue_yonder",
            facility="DC01",
            replacements=result.for_step(0),
        )
        header = next(p for p in plans if p.name == "X-Warehouse-Id")

        assert str(header.value) == "${warehouse_id}"
        assert header.value is not None
        assert header.value.placeholders == frozenset({"warehouse_id"})

    def test_without_a_diff_the_observed_value_is_kept(self) -> None:
        plans = build_header_plans(
            f.request(request_headers={"X-Warehouse-Id": "WH-1"}),
            target_system="blue_yonder",
            facility="DC01",
        )

        assert str(next(p for p in plans if p.name == "X-Warehouse-Id").value) == "WH-1"


async def test_a_parameter_says_every_field_it_is_sent_as() -> None:
    """One value can sit under several field names. Blue Yonder's adjust payload
    sends the detail number as both `lpn` and `detailNumber`, so the group is
    named after whichever site came first and the plan reads
    `"lpn": "${detail_number}"` — faithful, and indistinguishable from a
    mis-binding unless the parameter says where it appears."""
    from sro.application.induction.diff import parameterise

    def run(detail: str, load: str) -> tuple:
        return (
            f.frame(
                0,
                requests=(
                    f.request(
                        method="PUT",
                        url="https://wms.test/data/WM/wm/inventory/adjust",
                        request_body=f.Body(
                            text=f'{{"loadNumber":"{load}","lpn":"{detail}","detailNumber":"{detail}"}}',
                            size_bytes=80,
                            mime_type="application/json",
                        ),
                    ),
                ),
            ),
        )

    result = parameterise(run("D0001", "LPN-1"), run("D0002", "LPN-2"))

    shared = next(p for p in result.parameters if "D0001" in p.observed_values)
    assert "/lpn" in shared.description and "/detailNumber" in shared.description
    assert "one value" in shared.description
