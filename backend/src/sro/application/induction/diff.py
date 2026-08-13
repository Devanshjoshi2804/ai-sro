"""Two-run diff: what varies becomes a parameter.

Rationale and the rejected alternatives: docs/07-adr/004-diff-parameterisation.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from sro.application.induction import jsonutil
from sro.application.induction.errors import InductionFailed
from sro.application.induction.naming import deduplicate, suggest_name
from sro.application.induction.sites import (
    ActionValueSite,
    JsonBodySite,
    Site,
    TextBodySite,
    UrlPathSite,
    UrlQuerySite,
    parse_json,
    url_path_segments,
    url_query_pairs,
)
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.network import CapturedRequest
from sro.domain.skill.parameter import Parameter, ParameterKind


@dataclass(frozen=True, slots=True)
class Difference:
    step_index: int
    site: Site
    value_a: str
    value_b: str
    url: str = ""
    field_label: str | None = None


@dataclass(frozen=True, slots=True)
class Substitution:
    site: Site
    parameter: str


@dataclass(frozen=True, slots=True)
class Parameterisation:
    parameters: tuple[Parameter, ...]
    substitutions: dict[int, tuple[Substitution, ...]]

    def for_step(self, index: int) -> dict[Site, str]:
        return {sub.site: f"${{{sub.parameter}}}" for sub in self.substitutions.get(index, ())}


def align(run_a: tuple[ActionFrame, ...], run_b: tuple[ActionFrame, ...]) -> None:
    """Verify the runs describe the same task, or say why they do not.

    Alignment is positional and refuses anything that does not match exactly. A
    fuzzy match here would be a guess at the point where guessing costs most.
    """
    if not run_a or not run_b:
        raise InductionFailed("both recordings must contain at least one step")

    if len(run_a) != len(run_b):
        raise InductionFailed(
            f"the runs have different numbers of steps ({len(run_a)} and {len(run_b)}); "
            "they are not two runs of the same task -- re-record, or trim the extra steps"
        )

    for index, (frame_a, frame_b) in enumerate(zip(run_a, run_b, strict=True)):
        if frame_a.action.kind is not frame_b.action.kind:
            raise InductionFailed(
                f"run A did {frame_a.action.kind} but run B did {frame_b.action.kind}",
                step_index=index,
            )


def differences(run_a: tuple[ActionFrame, ...], run_b: tuple[ActionFrame, ...]) -> list[Difference]:
    align(run_a, run_b)
    found: list[Difference] = []
    for index, (frame_a, frame_b) in enumerate(zip(run_a, run_b, strict=True)):
        found.extend(_diff_action(index, frame_a, frame_b))
        found.extend(_diff_request(index, frame_a, frame_b))
    return found


def parameterise(
    run_a: tuple[ActionFrame, ...], run_b: tuple[ActionFrame, ...]
) -> Parameterisation:
    """Diff, classify as input or derived, name, and address every substitution."""
    # Grouped by value pair: an order number in the URL, the body and a
    # confirmation field is one parameter with three sites, not three that agree.
    groups: dict[tuple[str, str], list[Difference]] = {}
    for difference in differences(run_a, run_b):
        groups.setdefault((difference.value_a, difference.value_b), []).append(difference)

    parameters: list[Parameter] = []
    substitutions: dict[int, list[Substitution]] = {}
    taken: set[str] = set()

    for (value_a, value_b), sites in groups.items():
        first = sites[0]
        earliest_use = min(site.step_index for site in sites)
        source = _find_source(value_a, value_b, run_a, run_b, before=earliest_use)

        name = deduplicate(
            suggest_name(first.site, url=first.url, field_label=first.field_label), taken
        )
        taken.add(name)
        parameters.append(_build_parameter(name, value_a, value_b, sites, source))

        for difference in sites:
            substitutions.setdefault(difference.step_index, []).append(
                Substitution(site=difference.site, parameter=name)
            )

    return Parameterisation(
        parameters=tuple(parameters),
        substitutions={index: tuple(subs) for index, subs in substitutions.items()},
    )


def _build_parameter(
    name: str,
    value_a: str,
    value_b: str,
    sites: list[Difference],
    source: tuple[int, str] | None,
) -> Parameter:
    if source is None:
        return Parameter(
            name=name,
            kind=ParameterKind.INPUT,
            description=f"varies between runs at {len(sites)} place(s)",
            observed_values=(value_a, value_b),
        )
    step_index, pointer = source
    return Parameter(
        name=name,
        kind=ParameterKind.DERIVED,
        description=f"produced by step {step_index} response at {pointer}",
        observed_values=(value_a, value_b),
        source_step_index=step_index,
        source_pointer=pointer,
    )


def _diff_action(index: int, frame_a: ActionFrame, frame_b: ActionFrame) -> list[Difference]:
    value_a, value_b = frame_a.action.value, frame_b.action.value
    if value_a is None or value_b is None or value_a == value_b:
        return []
    target = frame_a.action.target
    return [
        Difference(
            step_index=index,
            site=ActionValueSite(),
            value_a=value_a,
            value_b=value_b,
            field_label=target.accessible_name if target else None,
        )
    ]


def _diff_request(index: int, frame_a: ActionFrame, frame_b: ActionFrame) -> list[Difference]:
    request_a, request_b = frame_a.primary_request, frame_b.primary_request
    if request_a is None and request_b is None:
        return []
    if request_a is None or request_b is None:
        raise InductionFailed(
            "one run made a network call here and the other did not; the demonstrations "
            "diverged (a cached page, or a different branch of the flow)",
            step_index=index,
        )
    if request_a.method.upper() != request_b.method.upper():
        raise InductionFailed(
            f"different HTTP methods ({request_a.method} and {request_b.method})",
            step_index=index,
        )

    return [
        *_diff_url(index, request_a, request_b),
        *_diff_body(index, request_a, request_b),
    ]


def _diff_url(index: int, a: CapturedRequest, b: CapturedRequest) -> list[Difference]:
    segments_a, segments_b = url_path_segments(a.url), url_path_segments(b.url)
    if len(segments_a) != len(segments_b):
        raise InductionFailed(f"different endpoint shapes: {a.url} and {b.url}", step_index=index)

    found = [
        Difference(
            step_index=index,
            site=UrlPathSite(position),
            value_a=segment_a,
            value_b=segment_b,
            url=a.url,
        )
        for position, (segment_a, segment_b) in enumerate(zip(segments_a, segments_b, strict=True))
        if segment_a != segment_b
    ]

    query_a, query_b = dict(url_query_pairs(a.url)), dict(url_query_pairs(b.url))
    if query_a.keys() != query_b.keys():
        raise InductionFailed(
            f"different query parameters: {sorted(query_a)} and {sorted(query_b)}",
            step_index=index,
        )
    found.extend(
        Difference(
            step_index=index,
            site=UrlQuerySite(key),
            value_a=query_a[key],
            value_b=query_b[key],
            url=a.url,
        )
        for key in query_a
        if query_a[key] != query_b[key]
    )
    return found


def _diff_body(index: int, a: CapturedRequest, b: CapturedRequest) -> list[Difference]:
    body_a, body_b = a.request_text, b.request_text
    if body_a is None and body_b is None:
        return []
    if body_a is None or body_b is None:
        raise InductionFailed("one run sent a request body and the other did not", step_index=index)
    if body_a == body_b:
        return []

    document_a, document_b = parse_json(body_a), parse_json(body_b)
    if document_a is None or document_b is None:
        # Form-encoded or plain text: the whole body becomes one parameter.
        # Coarse, but better than a confident mis-parse of a format we do not model.
        return [Difference(step_index=index, site=TextBodySite(), value_a=body_a, value_b=body_b)]

    if jsonutil.structure(document_a) != jsonutil.structure(document_b):
        raise InductionFailed(
            "the two runs sent differently-shaped request bodies; the flows diverged",
            step_index=index,
        )

    leaves_b = dict(jsonutil.leaves(document_b))
    return [
        Difference(
            step_index=index,
            site=JsonBodySite(pointer),
            value_a=str(leaf_a),
            value_b=str(leaves_b[pointer]),
        )
        for pointer, leaf_a in jsonutil.leaves(document_a)
        if str(leaf_a) != str(leaves_b[pointer])
    ]


def _find_source(
    value_a: str,
    value_b: str,
    run_a: tuple[ActionFrame, ...],
    run_b: tuple[ActionFrame, ...],
    *,
    before: int,
) -> tuple[int, str] | None:
    """Find an earlier response producing this value in *both* runs.

    Requiring both is what separates a real data dependency from a coincidence.
    A coincidence promoted to DERIVED leaves a parameter nothing can populate.
    """
    for step_index in range(before):
        request_a = run_a[step_index].primary_request
        request_b = run_b[step_index].primary_request
        if request_a is None or request_b is None:
            continue
        document_a = parse_json(request_a.response_text)
        document_b = parse_json(request_b.response_text)
        if document_a is None or document_b is None:
            continue

        leaves_b = {pointer: str(leaf) for pointer, leaf in jsonutil.leaves(document_b)}
        for pointer, leaf in jsonutil.leaves(document_a):
            if str(leaf) == value_a and leaves_b.get(pointer) == value_b:
                return step_index, pointer
    return None
