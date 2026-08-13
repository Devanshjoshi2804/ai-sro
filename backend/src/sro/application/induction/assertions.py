"""Post-conditions extracted from what the demonstration proved.

Fields identical across both runs are stable success markers; fields that
differed are parameters and asserting on them would pin the skill to one run.
"""

from __future__ import annotations

from dataclasses import dataclass

from sro.application.induction import jsonutil
from sro.application.induction.sites import parse_json
from sro.domain.recording.element import ElementFingerprint
from sro.domain.recording.events import ActionFrame
from sro.domain.skill.assertion import Assertion, AssertionKind
from sro.domain.skill.template import Template

MAX_FIELD_ASSERTIONS = 2
MAX_ASSERTED_VALUE_LENGTH = 64
_SUCCESS_WORDS = ("status", "state", "ok", "success", "result", "code", "message")


@dataclass(frozen=True, slots=True)
class StepEvidence:
    assertions: tuple[Assertion, ...]
    wait_for: ElementFingerprint | None


def extract(
    frame_a: ActionFrame,
    frame_b: ActionFrame,
    *,
    next_a: ActionFrame | None = None,
    next_b: ActionFrame | None = None,
) -> StepEvidence:
    """Derive assertions for one aligned step pair."""
    appeared = _element_that_appeared(frame_a, frame_b, next_a, next_b)

    request_a, request_b = frame_a.primary_request, frame_b.primary_request
    if request_a is None or request_b is None:
        return StepEvidence(assertions=_ui_assertions(appeared), wait_for=appeared)

    assertions: list[Assertion] = []
    if request_a.status is not None and request_a.status == request_b.status:
        assertions.append(
            Assertion(kind=AssertionKind.HTTP_STATUS, expected=Template(str(request_a.status)))
        )
    assertions.extend(_stable_response_fields(request_a.response_text, request_b.response_text))

    if not assertions:
        assertions.extend(_ui_assertions(appeared))

    return StepEvidence(assertions=tuple(assertions), wait_for=appeared)


def _stable_response_fields(body_a: str | None, body_b: str | None) -> list[Assertion]:
    document_a, document_b = parse_json(body_a), parse_json(body_b)
    if document_a is None or document_b is None:
        return []

    leaves_b = dict(jsonutil.leaves(document_b))
    stable = [
        (pointer, leaf)
        for pointer, leaf in jsonutil.leaves(document_a)
        if pointer in leaves_b
        and leaf == leaves_b[pointer]
        and leaf is not None
        and leaf != ""
        and len(jsonutil.as_text(leaf)) <= MAX_ASSERTED_VALUE_LENGTH
    ]
    # A stable `status` witnesses success better than a stable `pageSize`.
    stable.sort(key=lambda item: 0 if _looks_like_a_success_marker(item[0]) else 1)

    return [
        Assertion(
            kind=AssertionKind.RESPONSE_FIELD_EQUALS,
            pointer=pointer,
            expected=Template(jsonutil.as_text(leaf)),
        )
        for pointer, leaf in stable[:MAX_FIELD_ASSERTIONS]
    ]


def _looks_like_a_success_marker(pointer: str) -> bool:
    tail = pointer.rsplit("/", 1)[-1].lower()
    return any(word in tail for word in _SUCCESS_WORDS)


def _ui_assertions(appeared: ElementFingerprint | None) -> tuple[Assertion, ...]:
    if appeared is None or not appeared.accessible_name:
        return ()
    return (
        Assertion(kind=AssertionKind.UI_TEXT_VISIBLE, expected=Template(appeared.accessible_name)),
    )


def _element_that_appeared(
    frame_a: ActionFrame,
    frame_b: ActionFrame,
    next_a: ActionFrame | None,
    next_b: ActionFrame | None,
) -> ElementFingerprint | None:
    """First element that showed up after this step in *both* runs.

    Requiring both filters out incidentals -- a spinner, a tooltip, a timestamp.
    """
    if next_a is None or next_b is None:
        return None
    if frame_a.ax_graph is None or next_a.ax_graph is None:
        return None
    if frame_b.ax_graph is None or next_b.ax_graph is None:
        return None

    before_a = {node.accessible_name for node in frame_a.ax_graph.nodes}
    before_b = {node.accessible_name for node in frame_b.ax_graph.nodes}
    names_b = {node.accessible_name for node in next_b.ax_graph.nodes} - before_b

    for node in next_a.ax_graph.nodes:
        appeared_in_a = bool(node.accessible_name) and node.accessible_name not in before_a
        if appeared_in_a and node.accessible_name in names_b:
            return node
    return None
