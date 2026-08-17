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
    HeaderSite,
    JsonBodySite,
    Site,
    TextBodySite,
    UrlPathSite,
    UrlQuerySite,
    describe,
    parse_json,
    url_path_segments,
    url_query_pairs,
)
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.network import CapturedRequest
from sro.domain.recording.sensitivity import classify_header, is_replayable
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


def _control(frame: ActionFrame) -> str:
    """What the gesture acted on, as steadily as the page allows.

    The accessible name first, because ExtJS renumbers its generated ids between
    page loads and ``button-1148`` is not the same control tomorrow. Role and
    kind on their own would pair two different text boxes, which is the one
    mistake worth being strict about.
    """
    target = frame.action.target
    if target is None:
        return f"{frame.action.kind}"
    identity = target.accessible_name or target.test_id or target.css_path or target.xpath or ""
    return f"{frame.action.kind}:{target.role or ''}:{identity}"


def _evidential(frame: ActionFrame) -> bool:
    """Whether dropping this step would lose something the skill needs.

    A gesture that changed the system, or carried a value into it, is evidence.
    A click that fetched nothing and typed nothing is the operator finding their
    way -- focusing a field, opening a panel to look, clicking a label twice.
    """
    if frame.action.value or frame.action.secret:
        return True
    return any(request.is_mutation for request in frame.requests)


def align(
    run_a: tuple[ActionFrame, ...], run_b: tuple[ActionFrame, ...]
) -> tuple[tuple[ActionFrame, ActionFrame], ...]:
    """Pair the steps the two runs share, and say why they cannot be paired.

    The first demonstration of anything contains looking around: a field clicked
    twice, a panel opened to check a code, a grid sorted before the row is found.
    Demanding identical step counts made the exploration part of the task and
    refused the pair -- for two runs whose writes were byte-identical.

    So the runs are aligned rather than counted, on the longest sequence of
    gestures they share. What only one run did is dropped, but only when
    dropping it loses nothing: a step that changed the system or carried a value
    is never silently discarded, because that is a genuine disagreement about
    what the task is and guessing there is what ADR 004 exists to prevent.
    """
    if not run_a or not run_b:
        raise InductionFailed("both recordings must contain at least one step")

    paired = _longest_common(run_a, run_b)
    for run, label in ((run_a, "the first run"), (run_b, "the second run")):
        matched = {id(frame) for pair in paired for frame in pair}
        orphan = next((f for f in run if id(f) not in matched and _evidential(f)), None)
        if orphan is not None:
            raise InductionFailed(
                f"{label} did something the other did not: "
                f"{describe_step(orphan)}. The runs are not two runs of one task",
                step_index=orphan.index,
            )
    if not paired:
        raise InductionFailed("the runs share no steps at all; they are different tasks")
    return paired


def describe_step(frame: ActionFrame) -> str:
    """A step named the way an operator would recognise it."""
    target = frame.action.target
    name = (target.accessible_name or target.text or target.css_path) if target else None
    request = frame.primary_request
    call = f" ({request.method} {request.url.split('?')[0]})" if request else ""
    return f"{frame.action.kind} on {name or 'the page'}{call}"


def _longest_common(
    run_a: tuple[ActionFrame, ...], run_b: tuple[ActionFrame, ...]
) -> tuple[tuple[ActionFrame, ActionFrame], ...]:
    """Classic LCS over control identity. Runs are a handful of steps, so the
    quadratic table is smaller than the code to avoid it."""
    keys_a = [_control(frame) for frame in run_a]
    keys_b = [_control(frame) for frame in run_b]
    table = [[0] * (len(keys_b) + 1) for _ in range(len(keys_a) + 1)]
    for i in range(len(keys_a) - 1, -1, -1):
        for j in range(len(keys_b) - 1, -1, -1):
            table[i][j] = (
                table[i + 1][j + 1] + 1
                if keys_a[i] == keys_b[j]
                else max(table[i + 1][j], table[i][j + 1])
            )

    pairs: list[tuple[ActionFrame, ActionFrame]] = []
    i = j = 0
    while i < len(keys_a) and j < len(keys_b):
        if keys_a[i] == keys_b[j]:
            pairs.append((run_a[i], run_b[j]))
            i, j = i + 1, j + 1
        elif table[i + 1][j] >= table[i][j + 1]:
            i += 1
        else:
            j += 1
    return tuple(pairs)


def differences(run_a: tuple[ActionFrame, ...], run_b: tuple[ActionFrame, ...]) -> list[Difference]:
    found: list[Difference] = []
    for index, (frame_a, frame_b) in enumerate(align(run_a, run_b)):
        found.extend(_diff_action(index, frame_a, frame_b))
        found.extend(_diff_request(index, frame_a, frame_b))
    return found


def parameterise(
    run_a: tuple[ActionFrame, ...], run_b: tuple[ActionFrame, ...]
) -> Parameterisation:
    """Diff, classify as input or derived, name, and address every substitution."""
    # Every index below -- a difference's step, a parameter's source -- counts
    # paired steps, not the steps of either recording. Handing the raw runs to
    # _find_source would look up "step 4" in a run whose step 4 is somebody's
    # second click on a label.
    pairs = align(run_a, run_b)
    paired_a = tuple(pair[0] for pair in pairs)
    paired_b = tuple(pair[1] for pair in pairs)

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
        source = _find_source(value_a, value_b, paired_a, paired_b, before=earliest_use)

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
            description=_where(sites),
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


def _where(sites: list[Difference]) -> str:
    """Name every place this value appears, not just how many.

    A parameter is one value, and one value can sit under several field names:
    Blue Yonder's adjust payload sends the detail number as both `lpn` and
    `detailNumber`, so the group is named after whichever site was seen first
    and the plan reads `"lpn": "${detail_number}"`. That is faithful, and it
    looks exactly like a mis-binding to anybody reviewing it -- it cost an
    afternoon of mine. Saying where the value appears is the difference between
    a reviewer trusting the plan and re-deriving it.
    """
    places = list(dict.fromkeys(describe(site.site) for site in sites))
    if len(places) == 1:
        return f"varies between runs at {places[0]}"
    return "one value, varying between runs, sent at " + ", ".join(places)


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
        *_diff_headers(index, request_a, request_b),
        *_diff_body(index, request_a, request_b),
    ]


def _diff_headers(index: int, a: CapturedRequest, b: CapturedRequest) -> list[Difference]:
    """Headers that carry meaning and varied between the runs.

    Restricted to replayable headers on purpose. Everything else varies for
    reasons that have nothing to do with the task: a trace id is new per call, a
    cookie per session, a Referer per page. Diffing those would produce
    parameters no operator could answer.

    A header present in one run and missing in the other is left alone rather
    than treated as a difference -- browsers add and drop `sec-*` headers on
    their own, and a missing header has no value to parameterise.
    """
    replayable_a = {
        name.lower(): value
        for name, value in a.request_headers.items()
        if is_replayable(classify_header(name))
    }
    replayable_b = {
        name.lower(): value
        for name, value in b.request_headers.items()
        if is_replayable(classify_header(name))
    }
    original_case = {name.lower(): name for name in a.request_headers}

    return [
        Difference(
            step_index=index,
            site=HeaderSite(original_case[name]),
            value_a=value,
            value_b=replayable_b[name],
            url=a.url,
        )
        for name, value in replayable_a.items()
        if name in replayable_b and value != replayable_b[name]
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
        if query_a[key] != query_b[key] and not _is_a_clock(query_a[key], query_b[key])
    )
    return found


def _is_a_clock(value_a: str, value_b: str) -> bool:
    """Whether these two values differ only because time passed.

    Ext JS appends ``_dc=<epoch millis>`` to every request to defeat caching,
    and jQuery's ``_`` does the same. Both runs of a task therefore disagree
    there, always -- and the diff dutifully reported a parameter, so a skill
    asked its operator for a number that means "now". Two parameters out of four
    on the first real task taught were this.

    Detected by what the values are rather than by the key's name, because the
    name differs per framework and the shape does not: milliseconds since the
    epoch, recently, and different in the two runs.
    """
    recent = range(1_600_000_000_000, 4_000_000_000_000)  # 2020 to 2096, in millis
    return (
        value_a.isdigit()
        and value_b.isdigit()
        and int(value_a) in recent
        and int(value_b) in recent
    )


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
