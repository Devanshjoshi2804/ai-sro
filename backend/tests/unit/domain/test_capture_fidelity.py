"""Total capture, selective propagation. See docs/11-capture-completeness.md."""

from __future__ import annotations

import pytest

from sro.application.induction.headers import build_header_plans
from sro.domain.recording.axgraph import AxGraph
from sro.domain.recording.element import ElementFingerprint
from sro.domain.recording.network import Body, Initiator, InitiatorKind
from sro.domain.recording.sensitivity import (
    Sensitivity,
    classify_header,
    is_replayable,
    is_secret,
)
from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.plan import HeaderPlan
from sro.domain.skill.template import Template
from tests import factories as f


class TestNothingIsDiscarded:
    def test_every_observed_header_reaches_the_plan(self) -> None:
        request = f.request()
        plans = build_header_plans(request, target_system="blue_yonder", facility="DC01")

        assert {p.name for p in plans} == set(request.request_headers)

    def test_a_payload_must_be_inline_or_point_at_a_blob(self) -> None:
        # The invariant behind "nothing is scrapped": a body large enough to be
        # offloaded must carry its URI, never silently become empty.
        with pytest.raises(InvariantViolation, match="never discards a payload"):
            Body(size_bytes=5_000_000)

        assert Body(blob_uri="s3://sro-artifacts/acme/rec-1/payload/req-9", size_bytes=5_000_000)


class TestSecretsAreReferencedNotCopied:
    def test_credentials_become_a_vault_reference(self) -> None:
        plans = build_header_plans(f.request(), target_system="blue_yonder", facility="DC01")
        auth = next(p for p in plans if p.name == "Authorization")

        assert auth.sensitivity is Sensitivity.AUTH
        assert auth.credential_ref == "blue_yonder/DC01/authorization"
        # The live token was captured in the evidence plane; it must not be a
        # literal in an artifact that gets versioned and shared between sites.
        assert auth.value is None

    def test_csrf_and_trace_headers_are_minted_not_replayed(self) -> None:
        plans = build_header_plans(f.request(), target_system="blue_yonder", facility="DC01")
        csrf = next(p for p in plans if p.name == "X-CSRF-Token")

        assert csrf.mint is True
        assert csrf.value is None

    def test_semantic_headers_are_replayed_verbatim(self) -> None:
        plans = build_header_plans(f.request(), target_system="blue_yonder", facility="DC01")
        facility = next(p for p in plans if p.name == "X-Facility")

        assert facility.sensitivity is Sensitivity.SEMANTIC
        assert str(facility.value) == "DC01"

    def test_client_managed_headers_never_carry_a_captured_value(self) -> None:
        # A Referer captured during a demonstration points at a page that no
        # longer exists, and a captured Content-Length describes a body that is
        # about to be re-rendered with different parameters.
        request = f.request(
            request_headers={
                "Referer": "https://wms.test/waves?wave=W-1001",
                "Content-Length": "42",
                "User-Agent": "Mozilla/5.0",
                "X-Facility": "DC01",
            }
        )
        plans = build_header_plans(request, target_system="blue_yonder", facility="DC01")
        by_name = {p.name: p for p in plans}

        for name in ("Referer", "Content-Length", "User-Agent"):
            assert by_name[name].managed is True
            assert by_name[name].value is None

        # The header that carries meaning is still replayed.
        assert str(by_name["X-Facility"].value) == "DC01"

    def test_a_managed_header_cannot_be_given_a_value(self) -> None:
        with pytest.raises(InvariantViolation, match="client-managed"):
            HeaderPlan(
                name="Referer",
                sensitivity=Sensitivity.TRANSPORT,
                managed=True,
                value=Template("https://wms.test/stale"),
            )

    def test_the_executor_is_told_which_credentials_it_needs(self) -> None:
        plans = build_header_plans(f.request(), target_system="blue_yonder", facility="DC01")
        plan = f.network_plan(headers=plans)

        assert plan.required_credentials == {"blue_yonder/DC01/authorization"}

    @pytest.mark.parametrize(
        ("header", "expected"),
        [
            ("Authorization", Sensitivity.AUTH),
            ("x-api-key", Sensitivity.AUTH),
            ("Cookie", Sensitivity.SESSION),
            ("X-CSRF-Token", Sensitivity.CSRF),
            ("traceparent", Sensitivity.TRACE),
            ("X-Trace", Sensitivity.TRACE),
            ("X-Nonce", Sensitivity.TRACE),
            ("X-Idempotency-Key", Sensitivity.TRACE),
            ("X-Request-Timestamp", Sensitivity.TRACE),
            ("User-Agent", Sensitivity.TRANSPORT),
            ("X-Warehouse-Id", Sensitivity.SEMANTIC),
        ],
    )
    def test_classification(self, header: str, expected: Sensitivity) -> None:
        assert classify_header(header) is expected

    def test_only_semantic_values_are_replayable(self) -> None:
        assert is_replayable(Sensitivity.SEMANTIC)
        for other in (Sensitivity.AUTH, Sensitivity.CSRF, Sensitivity.SESSION):
            assert not is_replayable(other)
            assert is_secret(other)


class TestCausality:
    def test_the_script_initiated_mutation_wins_over_other_traffic(self) -> None:
        # The initiator is the strongest evidence available that a call was
        # caused by the click, rather than merely coincident with it. A beacon
        # POST fired by the parser is not what the human did.
        beacon = f.request(
            request_id="a",
            method="POST",
            url="https://wms.test/telemetry",
            initiator=Initiator(kind=InitiatorKind.PARSER),
            started_at=f.at(11),
        )
        real = f.request(
            request_id="b",
            method="POST",
            initiator=Initiator(kind=InitiatorKind.SCRIPT),
            started_at=f.at(12),
        )
        frame = f.frame(requests=(beacon, real))

        assert frame.primary_request is real

    def test_console_errors_and_failed_calls_surface_as_why(self) -> None:
        failed = f.request(request_id="x", status=422, status_text="Unprocessable")
        frame = f.frame(requests=(failed,))

        assert any("422" in error for error in frame.errors)


class TestAxGraph:
    def test_ancestry_disambiguates_a_repeated_label(self) -> None:
        root = ElementFingerprint(
            node_id="1", role="dialog", accessible_name="Release", child_ids=("2",)
        )
        form = ElementFingerprint(node_id="2", role="form", parent_id="1", child_ids=("3",))
        button = ElementFingerprint(
            node_id="3", role="button", accessible_name="Save", parent_id="2"
        )
        graph = AxGraph(taken_at=f.at(0), url="https://wms.test", nodes=(root, form, button))

        assert graph.path(button) == "dialog “Release” > form > button “Save”"
        assert graph.children(root) == (form,)

    def test_a_cyclic_graph_does_not_hang(self) -> None:
        a = ElementFingerprint(node_id="1", role="group", parent_id="2")
        b = ElementFingerprint(node_id="2", role="group", parent_id="1")
        graph = AxGraph(taken_at=f.at(0), url="https://wms.test", nodes=(a, b))

        assert len(list(graph.ancestors(a))) <= 2

    def test_interactive_nodes_are_identifiable(self) -> None:
        graph = AxGraph(
            taken_at=f.at(0),
            url="https://wms.test",
            nodes=(
                f.fingerprint(node_id="1", role="button"),
                f.fingerprint(node_id="2", role="paragraph", accessible_name="hello"),
            ),
        )

        assert len(graph.interactive) == 1


def test_a_vendor_named_csrf_header_is_still_a_csrf_header() -> None:
    """Blue Yonder calls it `CSRF-ENCRYPT-TOKEN`; an exact list did not catch it,
    and the live token was written into a skill as a literal."""
    from sro.domain.recording.sensitivity import Sensitivity, classify_header

    assert classify_header("CSRF-ENCRYPT-TOKEN") is Sensitivity.CSRF
    assert classify_header("X-XSRF-HEADER") is Sensitivity.CSRF
