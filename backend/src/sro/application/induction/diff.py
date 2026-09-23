from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal
from urllib.parse import urlsplit

from sro.application.induction import binding, jsonutil
from sro.application.induction.errors import InductionFailed
from sro.application.induction.naming import deduplicate, singular, suggest_name
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
from sro.application.induction.transform import discover
from sro.domain.recording.background import is_background_traffic
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.network import CapturedRequest
from sro.domain.recording.sensitivity import classify_header, is_replayable
from sro.domain.skill.parameter import Evidence, Parameter, ParameterKind, json_type_of
from sro.domain.skill.transform import Transform

_UNREMARKABLE = frozenset({"", "true", "false", "null", "0", "1"})


@dataclass(frozen=True, slots=True)
class Difference:
    step_index: int
    site: Site
    value_a: str
    value_b: str
    url: str = ""
    field_label: str | None = None
    absent_as: str | None = None

    filled_as: str | None = None


@dataclass(frozen=True, slots=True)
class Substitution:
    site: Site
    parameter: str

    unquoted: bool = False


@dataclass(frozen=True, slots=True)
class Choice:
    step_index: int
    sites: tuple[Site, ...]

    value: str
    field: str

    seen_at: int


@dataclass(frozen=True, slots=True)
class Parameterisation:
    parameters: tuple[Parameter, ...]
    substitutions: dict[int, tuple[Substitution, ...]]
    choices: tuple[Choice, ...] = ()

    def for_step(self, index: int) -> dict[Site, str]:
        return {sub.site: f"${{{sub.parameter}}}" for sub in self.substitutions.get(index, ())}

    def unquoted_sites(self, index: int) -> frozenset[Site]:
        return frozenset(sub.site for sub in self.substitutions.get(index, ()) if sub.unquoted)

    def conditional_on(self, index: int) -> str | None:
        return next(
            (
                sub.parameter
                for sub in self.substitutions.get(index, ())
                if isinstance(sub.site, ActionValueSite)
                and sub.parameter in {p.name for p in self.parameters if p.optional}
            ),
            None,
        )


def _mutations(frame: ActionFrame) -> list[CapturedRequest]:
    return [
        request
        for request in frame.requests
        if request.is_mutation and request.succeeded and not is_background_traffic(request.url)
    ]


def unfold(frames: tuple[ActionFrame, ...]) -> tuple[ActionFrame, ...]:
    grown: list[ActionFrame] = []
    for frame in frames:
        calls = _mutations(frame)
        if len(calls) < 2:
            grown.append(frame)
            continue
        grown.extend(replace(frame, requests=(call,)) for call in calls)
    return tuple(grown)


def explode(
    pairs: tuple[tuple[ActionFrame, ActionFrame], ...],
) -> tuple[tuple[ActionFrame, ActionFrame], ...]:
    grown: list[tuple[ActionFrame, ActionFrame]] = []
    for frame_a, frame_b in pairs:
        calls_a, calls_b = _mutations(frame_a), _mutations(frame_b)
        if len(calls_a) < 2 and len(calls_b) < 2:
            grown.append((frame_a, frame_b))
            continue
        if [call.method for call in calls_a] != [call.method for call in calls_b]:
            raise InductionFailed(
                f"{describe_step(frame_a)} sent "
                f"{', '.join(c.method for c in calls_a) or 'nothing'} in one run and "
                f"{', '.join(c.method for c in calls_b) or 'nothing'} in the other. "
                "The runs are not two runs of one task",
                step_index=frame_a.index,
            )
        for call_a, call_b in zip(calls_a, calls_b, strict=True):
            grown.append(
                (replace(frame_a, requests=(call_a,)), replace(frame_b, requests=(call_b,)))
            )
    return tuple(grown)


_GENERATED = re.compile(r"\d+")


def _control(frame: ActionFrame) -> str:
    target = frame.action.target
    if target is None:
        return str(frame.action.kind)
    identity = target.accessible_name or target.test_id or target.css_path or target.xpath or ""
    if not target.accessible_name:
        identity = _GENERATED.sub("#", identity)
    return f"{frame.action.kind}:{target.role or ''}:{identity}"


def _same(frame_a: ActionFrame, frame_b: ActionFrame) -> bool:
    if _control(frame_a) == _control(frame_b):
        return True
    sent_a, sent_b = frame_a.primary_request, frame_b.primary_request
    if sent_a is None or sent_b is None:
        return False
    return sent_a.method.upper() == sent_b.method.upper() and url_shape(sent_a.url) == url_shape(
        sent_b.url
    )


def url_shape(url: str) -> str:
    return "/".join("*" if any(c.isdigit() for c in seg) else seg for seg in url_path_segments(url))


def _evidential(frame: ActionFrame) -> bool:
    if frame.action.value or frame.action.secret:
        return True
    return any(
        request.is_mutation and not is_background_traffic(request.url) for request in frame.requests
    )


FILLS = frozenset({"type", "select", "upload"})


def settled(run: tuple[ActionFrame, ...]) -> tuple[ActionFrame, ...]:
    dropped: set[int] = set()
    latest: dict[str, int] = {}
    for position, frame in enumerate(run):
        if _wrote_something(frame):
            latest.clear()
            continue
        if frame.action.kind not in FILLS or frame.action.secret or not frame.action.value:
            continue
        control = _control(frame)
        if control in latest:
            dropped.add(latest[control])
        latest[control] = position
    return tuple(frame for position, frame in enumerate(run) if position not in dropped)


def _wrote_something(frame: ActionFrame) -> bool:
    return any(
        request.is_mutation and not is_background_traffic(request.url) for request in frame.requests
    )


def align(
    run_a: tuple[ActionFrame, ...], run_b: tuple[ActionFrame, ...]
) -> tuple[tuple[ActionFrame, ActionFrame], ...]:
    if not run_a or not run_b:
        raise InductionFailed("both recordings must contain at least one step")

    paired = _longest_common(run_a, run_b)
    matched = {id(frame) for pair in paired for frame in pair}
    excused = {id(fill.frame) for fill in optional_fills(run_a, run_b)}
    for run, label in ((run_a, "the first run"), (run_b, "the second run")):
        orphan = next(
            (
                frame
                for frame in run
                if id(frame) not in matched and id(frame) not in excused and _evidential(frame)
            ),
            None,
        )
        if orphan is not None:
            raise InductionFailed(
                f"{label} did something the other did not: "
                f"{describe_step(orphan)}. The runs are not two runs of one task",
                step_index=orphan.index,
            )
    if not paired:
        raise InductionFailed("the runs share no steps at all; they are different tasks")
    return explode(paired)


@dataclass(frozen=True, slots=True)
class Alignment:
    reference: tuple[ActionFrame, ...]
    seen: dict[int, int]

    doings: int


def align_all(runs: Sequence[tuple[ActionFrame, ...]]) -> Alignment:
    if not runs:
        raise InductionFailed("no doings were given to align; at least one is required")

    reference: list[ActionFrame] = list(_pick_reference(runs))
    seen: dict[int, int] = {id(frame): 0 for frame in reference}

    for run in runs:
        paired = _longest_common(tuple(reference), run)
        counterpart: dict[int, ActionFrame] = {
            id(run_frame): ref_frame for ref_frame, run_frame in paired
        }

        cursor = 0
        for frame in run:
            ref_frame = counterpart.get(id(frame))
            if ref_frame is not None:
                while reference[cursor] is not ref_frame:
                    cursor += 1
                seen[id(ref_frame)] += 1
                cursor += 1
            elif _evidential(frame):
                reference.insert(cursor, frame)
                seen[id(frame)] = 1
                cursor += 1

    return Alignment(
        reference=tuple(reference),
        seen={index: seen[id(frame)] for index, frame in enumerate(reference)},
        doings=len(runs),
    )


def _pick_reference(runs: Sequence[tuple[ActionFrame, ...]]) -> tuple[ActionFrame, ...]:

    def score(candidate: tuple[ActionFrame, ...]) -> tuple[int, int]:
        agreement = sum(
            len(_longest_common(candidate, other)) for other in runs if other is not candidate
        )
        return agreement, -len(candidate)

    return max(runs, key=score)


@dataclass(frozen=True, slots=True)
class OptionalFill:
    frame: ActionFrame
    pointer: str

    at: int


def optional_fills(
    run_a: tuple[ActionFrame, ...], run_b: tuple[ActionFrame, ...]
) -> tuple[OptionalFill, ...]:
    paired = _longest_common(run_a, run_b)
    steps = explode(paired)
    matched = {id(frame) for pair in paired for frame in pair}
    found = [
        OptionalFill(
            frame=frame,
            pointer=pointer,
            at=sum(1 for pair in steps if pair[side].index < frame.index),
        )
        for side, (run, other) in enumerate(((run_a, run_b), (run_b, run_a)))
        for frame in run
        if id(frame) not in matched
        and (pointer := _optional_pointer(frame, run, other)) is not None
    ]
    return tuple(sorted(found, key=lambda fill: fill.at))


def _optional_pointer(
    frame: ActionFrame, run: tuple[ActionFrame, ...], other: tuple[ActionFrame, ...]
) -> str | None:
    for write in run:
        pointer = binding.key_filled_by(frame, write)
        if pointer is None:
            continue
        for theirs in other:
            document = binding.write_document(theirs)
            if document is None:
                continue
            leaves = dict(jsonutil.leaves(document))
            if pointer in leaves:
                return pointer if jsonutil.is_empty(leaves[pointer]) else None
    return None


def describe_step(frame: ActionFrame) -> str:
    target = frame.action.target
    name = (target.accessible_name or target.text or target.css_path) if target else None
    request = frame.primary_request
    call = f" ({request.method} {request.url.split('?')[0]})" if request else ""
    return f"{frame.action.kind} on {name or 'the page'}{call}"


def _longest_common(
    run_a: tuple[ActionFrame, ...], run_b: tuple[ActionFrame, ...]
) -> tuple[tuple[ActionFrame, ActionFrame], ...]:
    matches = [[_same(frame_a, frame_b) for frame_b in run_b] for frame_a in run_a]
    table = [[0] * (len(run_b) + 1) for _ in range(len(run_a) + 1)]
    for i in range(len(run_a) - 1, -1, -1):
        for j in range(len(run_b) - 1, -1, -1):
            table[i][j] = (
                table[i + 1][j + 1] + 1 if matches[i][j] else max(table[i + 1][j], table[i][j + 1])
            )

    pairs: list[tuple[ActionFrame, ActionFrame]] = []
    i = j = 0
    while i < len(run_a) and j < len(run_b):
        if matches[i][j]:
            pairs.append((run_a[i], run_b[j]))
            i, j = i + 1, j + 1
        elif table[i + 1][j] >= table[i][j + 1]:
            i += 1
        else:
            j += 1
    return tuple(pairs)


def differences(
    run_a: tuple[ActionFrame, ...],
    run_b: tuple[ActionFrame, ...],
    others: tuple[tuple[ActionFrame, ...], ...] = (),
) -> list[Difference]:
    absences = _absences(others)
    found: list[Difference] = []
    for index, (frame_a, frame_b) in enumerate(align(run_a, run_b)):
        found.extend(_diff_action(index, frame_a, frame_b))
        found.extend(_diff_request(index, frame_a, frame_b, absences))
    return found


def _absences(runs: tuple[tuple[ActionFrame, ...], ...]) -> dict[tuple[str, str, str], set[str]]:
    found: dict[tuple[str, str, str], set[str]] = {}
    for run in runs:
        for frame in run:
            for request in _mutations(frame):
                document = parse_json(request.request_text)
                if document is None:
                    continue
                for pointer, leaf in jsonutil.leaves(document):
                    if not jsonutil.is_empty(leaf):
                        continue
                    key = (request.method.upper(), url_shape(request.url), pointer)
                    found.setdefault(key, set()).add(_absent_form(leaf))
    return found


def _absence_elsewhere(
    absences: dict[tuple[str, str, str], set[str]], request: CapturedRequest, pointer: str
) -> str | None:
    forms = absences.get((request.method.upper(), url_shape(request.url), pointer), set())
    return next(iter(forms)) if len(forms) == 1 else None


def parameterise(
    run_a: tuple[ActionFrame, ...],
    run_b: tuple[ActionFrame, ...],
    *,
    ask_for: frozenset[str] = frozenset(),
    also: tuple[Choice, ...] = (),
    others: tuple[tuple[ActionFrame, ...], ...] = (),
) -> Parameterisation:
    pairs = align(run_a, run_b)
    paired_a = tuple(pair[0] for pair in pairs)
    paired_b = tuple(pair[1] for pair in pairs)

    groups: dict[tuple[str, str, str | None, Site | None], list[Difference]] = {}
    for difference in differences(run_a, run_b, others):
        keystroke = isinstance(difference.site, ActionValueSite)
        key = (
            binding.tidied(difference.value_a) if keystroke else difference.value_a,
            binding.tidied(difference.value_b) if keystroke else difference.value_b,
            difference.absent_as,
            difference.site if keystroke or difference.absent_as is not None else None,
        )
        groups.setdefault(key, []).append(difference)

    for formless in [
        key for key in groups if key[2] is None and not isinstance(key[3], ActionValueSite)
    ]:
        named = {_key_of(difference.site) for difference in groups[formless]}
        formed = [
            key
            for key in groups
            if key[2] is not None
            and key[:2] == formless[:2]
            and named == {_key_of(groups[key][0].site)}
            and None not in named
        ]
        if len(formed) == 1:
            groups[formed[0]].extend(groups.pop(formless))

    for typed_key in [key for key in groups if isinstance(key[3], ActionValueSite)]:
        filled = [
            key
            for key in groups
            if not isinstance(key[3], ActionValueSite)
            and (binding.tidied(key[0]), binding.tidied(key[1])) == typed_key[:2]
        ]
        if len(filled) == 1:
            groups[filled[0]].extend(groups.pop(typed_key))

    parameters: list[Parameter] = []
    substitutions: dict[int, list[Substitution]] = {}
    taken: set[str] = set()

    for sites in groups.values():
        named_by = _names_it(sites)
        value_a, value_b = named_by.value_a, named_by.value_b
        earliest_use = min(site.step_index for site in sites)
        source = _find_source(value_a, value_b, paired_a, paired_b, before=earliest_use)

        name = deduplicate(
            suggest_name(named_by.site, url=named_by.url, field_label=named_by.field_label), taken
        )
        taken.add(name)
        parameters.append(_build_parameter(name, value_a, value_b, sites, source))

        for difference in sites:
            substitutions.setdefault(difference.step_index, []).append(
                Substitution(
                    site=difference.site,
                    parameter=name,
                    unquoted=renders_unquoted(difference),
                )
            )

    _link_produced_values(paired_a, paired_b, parameters, substitutions, taken)
    chosen = _chosen_constants(paired_a, paired_b, substitutions, taken)

    typed = {choice.field for choice in also}
    for choice in (*chosen, *also):
        if choice.field not in ask_for:
            continue
        parameters.append(
            Parameter(
                name=choice.field,
                kind=ParameterKind.INPUT,
                description=(
                    f"typed by the operator when this was demonstrated, into a control "
                    f"that asked for it. One demonstration cannot say whether "
                    f"{choice.value!r} varies, and a value somebody entered is the one "
                    f"most likely to"
                    if choice.field in typed
                    else f"chosen when this was demonstrated, twice. An operator asked to be "
                    f"prompted for it rather than always sending {choice.value!r}"
                ),
                observed_values=(choice.value,),
                evidence=Evidence.PROPOSED,
            )
        )
        substitutions.setdefault(choice.step_index, []).extend(
            Substitution(site=site, parameter=choice.field) for site in choice.sites
        )

    return Parameterisation(
        parameters=tuple(parameters),
        substitutions={index: tuple(subs) for index, subs in substitutions.items()},
        choices=chosen,
    )


def typed_values(run: tuple[ActionFrame, ...], taken: set[str] | None = None) -> tuple[Choice, ...]:
    already = set(taken or ())
    pairs = align(run, run)
    frames = tuple(pair[0] for pair in pairs)
    entered = {
        frame.action.value: frame for frame in run if frame.action.value and not frame.action.secret
    }
    if not entered:
        return ()

    found: dict[str, Choice] = {}
    for index, frame in enumerate(frames):
        request = frame.primary_request
        if request is None or not request.is_mutation:
            continue
        for site, value in _constant_sites(request, request):
            source = entered.get(value)
            if source is None or value.strip().lower() in _UNREMARKABLE:
                continue
            target = source.action.target
            label = (target.accessible_name or target.text) if target else None
            name = deduplicate(suggest_name(site, url=request.url, field_label=label), already)
            existing = found.get(name)
            sites = (*(existing.sites if existing else ()), site)
            found[name] = Choice(
                step_index=index if existing is None else existing.step_index,
                sites=sites,
                field=name,
                value=value,
                seen_at=source.index,
            )
    return tuple(found.values())


def _chosen_constants(
    run_a: tuple[ActionFrame, ...],
    run_b: tuple[ActionFrame, ...],
    substitutions: dict[int, list[Substitution]],
    taken: set[str],
) -> tuple[Choice, ...]:
    found: dict[str, Choice] = {}
    for index, (frame_a, frame_b) in enumerate(zip(run_a, run_b, strict=True)):
        request_a, request_b = frame_a.primary_request, frame_b.primary_request
        if request_a is None or request_b is None or not request_a.is_mutation:
            continue
        already = {sub.site for sub in substitutions.get(index, ())}
        constant = _constant_sites(request_a, request_b)
        collections = _collections_read(run_a) | _collections_read(run_b)
        addressed = {
            value
            for site, value in constant
            if isinstance(site, UrlPathSite)
            and site not in already
            and value.strip().lower() not in _UNREMARKABLE
            and _inside_a_collection(request_a.url, site, collections)
        }
        for value in addressed:
            listed = _listed_before(run_a, value, index)
            if listed is False:
                listed = _listed_before(run_b, value, index)
            if listed is False:
                continue
            sites = tuple(site for site, sent in constant if sent == value and site not in already)
            field = deduplicate(_name_for(sites, request_a.url), taken | set(found))
            found.setdefault(
                field,
                Choice(
                    step_index=index,
                    sites=sites,
                    value=value,
                    field=field,
                    seen_at=listed,
                ),
            )
    return tuple(found.values())


def _collections_read(run: tuple[ActionFrame, ...]) -> frozenset[str]:
    return frozenset(
        urlsplit(request.url).path.rstrip("/")
        for frame in run
        for request in frame.requests
        if not is_background_traffic(request.url)
    )


def _inside_a_collection(url: str, site: UrlPathSite, collections: frozenset[str]) -> bool:
    segments = url_path_segments(url)
    if site.index != len(segments) - 1:
        return False
    return "/" + "/".join(segments[: site.index]) in collections


def _name_for(sites: tuple[Site, ...], url: str) -> str:
    bodies = [site for site in sites if isinstance(site, JsonBodySite)]
    segments = url_path_segments(url)
    collection = singular(segments[-2]) if len(segments) > 1 else ""
    named = [site for site in bodies if collection and collection in site.pointer.lower()]
    ranked: list[Site] = [*named, *bodies, *sites]
    return suggest_name(ranked[0], url=url, field_label=None)


def _listed_before(run: tuple[ActionFrame, ...], value: str, before: int) -> int | Literal[False]:
    for step_index in range(before):
        frame = run[step_index]
        if any(request.is_mutation for request in frame.requests):
            continue
        if any(str(leaf) == value for _, leaf in _response_leaves(frame)):
            return step_index
    return False


def _link_produced_values(
    run_a: tuple[ActionFrame, ...],
    run_b: tuple[ActionFrame, ...],
    parameters: list[Parameter],
    substitutions: dict[int, list[Substitution]],
    taken: set[str],
) -> None:
    named: dict[tuple[str, int, str], str] = {}
    for index, (frame_a, frame_b) in enumerate(zip(run_a, run_b, strict=True)):
        request_a, request_b = frame_a.primary_request, frame_b.primary_request
        if request_a is None or request_b is None:
            continue
        already = {sub.site for sub in substitutions.get(index, ())}
        for site, value in _constant_sites(request_a, request_b):
            if site in already or not value:
                continue
            produced = _find_produced(value, run_a, run_b, before=index, key=_key_of(site))
            if produced is None:
                continue
            step_index, pointer = produced
            if any(_held_before(run, value, until=step_index) for run in (run_a, run_b)):
                continue
            name = named.get((value, step_index, pointer), "")
            if not name:
                name = deduplicate(suggest_name(site, url=request_a.url, field_label=None), taken)
                taken.add(name)
                named[(value, step_index, pointer)] = name
                parameters.append(
                    Parameter(
                        name=name,
                        kind=ParameterKind.DERIVED,
                        description=(
                            f"the value step {step_index} returned at {pointer}. The same in both "
                            "runs and sent by neither: the system produced it during the task"
                        ),
                        observed_values=(value,),
                        source_step_index=step_index,
                        source_pointer=pointer,
                    )
                )
            substitutions.setdefault(index, []).append(Substitution(site=site, parameter=name))
            already.add(site)


def _find_produced(
    value: str,
    run_a: tuple[ActionFrame, ...],
    run_b: tuple[ActionFrame, ...],
    *,
    before: int,
    key: str | None,
) -> tuple[int, str] | None:
    if value.strip().lower() in _UNREMARKABLE:
        return None
    for step_index in range(before):
        pointers_a = [p for p, leaf in _response_leaves(run_a[step_index]) if str(leaf) == value]
        pointers_b = [p for p, leaf in _response_leaves(run_b[step_index]) if str(leaf) == value]
        if len(pointers_a) != 1 or pointers_a != pointers_b:
            continue
        pointer = pointers_a[0]
        if key is not None and pointer.rsplit("/", 1)[-1] != key:
            continue
        if any(segment.isdigit() for segment in pointer.split("/")):
            continue
        return step_index, pointer
    return None


def _key_of(site: Site) -> str | None:
    if isinstance(site, JsonBodySite):
        return site.pointer.rsplit("/", 1)[-1]
    if isinstance(site, UrlQuerySite):
        return site.key
    return None


def _constant_sites(a: CapturedRequest, b: CapturedRequest) -> list[tuple[Site, str]]:
    segments_a, segments_b = url_path_segments(a.url), url_path_segments(b.url)
    found: list[tuple[Site, str]] = [
        (UrlPathSite(position), segment_a)
        for position, (segment_a, segment_b) in enumerate(zip(segments_a, segments_b, strict=False))
        if segment_a == segment_b
    ]

    query_b = dict(url_query_pairs(b.url))
    found.extend(
        (UrlQuerySite(key), value)
        for key, value in url_query_pairs(a.url)
        if query_b.get(key) == value
    )

    document_a, document_b = parse_json(a.request_text), parse_json(b.request_text)
    if document_a is not None and document_b is not None:
        leaves_b = {pointer: str(leaf) for pointer, leaf in jsonutil.leaves(document_b)}
        found.extend(
            (JsonBodySite(pointer), str(leaf))
            for pointer, leaf in jsonutil.leaves(document_a)
            if leaves_b.get(pointer) == str(leaf)
        )
    return found


def _held_before(run: tuple[ActionFrame, ...], value: str, *, until: int) -> bool:
    for frame in run[: until + 1]:
        if frame.action.value == value:
            return True
        for request in frame.requests:
            if value in request.url or (request.request_text and value in request.request_text):
                return True
    return False


def _names_it(sites: list[Difference]) -> Difference:
    ranked = (JsonBodySite, UrlQuerySite, UrlPathSite, HeaderSite)
    for kind in ranked:
        for site in sites:
            if isinstance(site.site, kind):
                return site
    return sites[0]


def _build_parameter(
    name: str,
    value_a: str,
    value_b: str,
    sites: list[Difference],
    source: tuple[int, str, Transform | None] | None,
) -> Parameter:
    is_the_body = any(isinstance(site.site, TextBodySite) for site in sites)
    if source is None:
        absent_as = next((site.absent_as for site in sites if site.absent_as is not None), None)
        if absent_as is not None:
            return Parameter(
                name=name,
                kind=ParameterKind.INPUT,
                description=(
                    f"{_where(sites)}; left empty in one of the doings watched, so it "
                    f"may be left out -- sent as {absent_as} when nobody supplies it"
                ),
                observed_values=tuple(value for value in (value_a, value_b) if value),
                absent_as=absent_as,
                unquoted_as=next(
                    (site.filled_as for site in sites if renders_unquoted(site)), None
                ),
                is_the_body=is_the_body,
            )
        return Parameter(
            name=name,
            kind=ParameterKind.INPUT,
            description=_where(sites),
            observed_values=(value_a, value_b),
            is_the_body=is_the_body,
        )
    step_index, pointer, rewrite = source
    described = f"produced by step {step_index} response at {pointer}"
    if rewrite is not None:
        described += f", {rewrite.said_plainly()}"
    return Parameter(
        name=name,
        kind=ParameterKind.DERIVED,
        description=described,
        observed_values=(value_a, value_b),
        source_step_index=step_index,
        source_pointer=pointer,
        transform=rewrite,
        is_the_body=is_the_body,
    )


def _where(sites: list[Difference]) -> str:
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


def _diff_request(
    index: int,
    frame_a: ActionFrame,
    frame_b: ActionFrame,
    absences: dict[tuple[str, str, str], set[str]] | None = None,
) -> list[Difference]:
    request_a, request_b = frame_a.primary_request, frame_b.primary_request
    if request_a is None and request_b is None:
        return []

    if request_a is None or request_b is None:
        lonely = request_a or request_b
        if lonely is not None and not lonely.is_mutation:
            return []
        raise InductionFailed(
            "one run changed the system here and the other did not; the demonstrations "
            "diverged (a different branch of the flow, or something already done)",
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
        *_diff_body(index, request_a, request_b, absences or {}),
    ]


def _diff_headers(index: int, a: CapturedRequest, b: CapturedRequest) -> list[Difference]:
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
    recent = range(1_600_000_000_000, 4_000_000_000_000)
    return (
        value_a.isdigit()
        and value_b.isdigit()
        and int(value_a) in recent
        and int(value_b) in recent
    )


def _diff_body(
    index: int,
    a: CapturedRequest,
    b: CapturedRequest,
    absences: dict[tuple[str, str, str], set[str]] | None = None,
) -> list[Difference]:
    body_a, body_b = a.request_text, b.request_text
    if body_a is None and body_b is None:
        return []
    if body_a is None or body_b is None:
        raise InductionFailed("one run sent a request body and the other did not", step_index=index)
    if body_a == body_b:
        return []

    document_a, document_b = parse_json(body_a), parse_json(body_b)
    if document_a is None or document_b is None:
        return [Difference(step_index=index, site=TextBodySite(), value_a=body_a, value_b=body_b)]

    if not jsonutil.same_shape(document_a, document_b):
        raise InductionFailed(
            "the two runs sent differently-shaped request bodies; the flows diverged",
            step_index=index,
        )

    leaves_b = dict(jsonutil.leaves(document_b))
    found: list[Difference] = []
    for pointer, leaf_a in jsonutil.leaves(document_a):
        if pointer not in leaves_b:
            raise InductionFailed(_group_left_empty(pointer), step_index=index)

        leaf_b = leaves_b[pointer]
        if str(leaf_a) == str(leaf_b):
            continue
        empty_a, empty_b = jsonutil.is_empty(leaf_a), jsonutil.is_empty(leaf_b)
        if empty_a and empty_b:
            continue
        found.append(
            Difference(
                step_index=index,
                site=JsonBodySite(pointer),
                value_a="" if empty_a else str(leaf_a),
                value_b="" if empty_b else str(leaf_b),
                absent_as=_absent_form(leaf_a if empty_a else leaf_b)
                if empty_a != empty_b
                else _absence_elsewhere(absences or {}, a, pointer),
                filled_as=json_type_of(leaf_b if empty_a else leaf_a),
            )
        )
    return found


def _group_left_empty(pointer: str) -> str:
    return (
        f"the two runs disagree at {pointer}: one sent a group there and the other "
        "left it empty. A whole group left empty is not a field left empty, and a "
        "skill cannot yet express one -- demonstrate the pair with that group "
        "filled in both runs"
    )


def renders_unquoted(difference: Difference) -> bool:
    return (
        isinstance(difference.site, JsonBodySite)
        and difference.absent_as is not None
        and not isinstance(json.loads(difference.absent_as), str)
    )


def _absent_form(leaf: object) -> str:
    return json.dumps(leaf)


def _find_source(
    value_a: str,
    value_b: str,
    run_a: tuple[ActionFrame, ...],
    run_b: tuple[ActionFrame, ...],
    *,
    before: int,
) -> tuple[int, str, Transform | None] | None:
    if not value_a or not value_b:
        return None
    for verbatim in (True, False):
        for step_index in range(before):
            leaves_b = {pointer: str(leaf) for pointer, leaf in _response_leaves(run_b[step_index])}
            for pointer, leaf in _response_leaves(run_a[step_index]):
                source_a, source_b = str(leaf), leaves_b.get(pointer)
                if source_b is None:
                    continue
                if verbatim:
                    if source_a == value_a and source_b == value_b:
                        return step_index, pointer, None
                    continue
                rewrite = discover(source_a, value_a)
                if rewrite is not None and rewrite.apply(source_b) == value_b:
                    return step_index, pointer, rewrite
    return None


def _response_leaves(frame: ActionFrame) -> list[tuple[str, object]]:
    found: list[tuple[str, object]] = []
    for request in frame.requests:
        if is_background_traffic(request.url):
            continue
        document = parse_json(request.response_text)
        if document is not None:
            found.extend(jsonutil.leaves(document))
    return found
