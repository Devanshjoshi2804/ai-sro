"""Two-run diff: what varies becomes a parameter.

Rationale and the rejected alternatives: docs/07-adr/004-diff-parameterisation.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Literal
from urllib.parse import urlsplit

from sro.application.induction import jsonutil
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
from sro.domain.recording.background import is_background_traffic
from sro.domain.recording.events import ActionFrame
from sro.domain.recording.network import CapturedRequest
from sro.domain.recording.sensitivity import classify_header, is_replayable
from sro.domain.skill.parameter import Evidence, Parameter, ParameterKind

_UNREMARKABLE = frozenset({"", "true", "false", "null", "0", "1"})
"""Values too common to be evidence of anything, wherever they turn up."""


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
class Choice:
    """A value both demonstrations chose, that either of them could have chosen
    differently.

    The operator picked an address off a list and then picked the same one
    again. Nothing in two runs can say whether that address is policy or
    preference -- and both answers are ordinary. Replaying it writes every
    supplier to one address; parameterising it asks a question nobody wanted.
    So it is neither: it is asked.
    """

    step_index: int
    sites: tuple[Site, ...]
    """Everywhere this call sends the value. One answer settles all of them: the
    address is in the path and in two body fields, and prompting for it three
    times would be three questions about one thing."""

    value: str
    field: str
    """What the parameter would be called, if it became one."""

    seen_at: int
    """The step whose response listed it. The evidence that it was chosen from
    what the screen offered rather than typed out of somebody's head."""


@dataclass(frozen=True, slots=True)
class Parameterisation:
    parameters: tuple[Parameter, ...]
    substitutions: dict[int, tuple[Substitution, ...]]
    choices: tuple[Choice, ...] = ()
    """Constants that were chosen rather than given. Nothing here changes what
    runs -- they are questions for an operator, not parameters."""

    def for_step(self, index: int) -> dict[Site, str]:
        return {sub.site: f"${{{sub.parameter}}}" for sub in self.substitutions.get(index, ())}


def _mutations(frame: ActionFrame) -> list[CapturedRequest]:
    """The calls this gesture made that changed something, in the order sent."""
    return [
        request
        for request in frame.requests
        if request.is_mutation and request.succeeded and not is_background_traffic(request.url)
    ]


def unfold(frames: tuple[ActionFrame, ...]) -> tuple[ActionFrame, ...]:
    """The same split as :func:`explode`, for a run with nothing to pair against.

    One demonstration has no second run to line calls up with, so each gesture's
    calls are taken in the order the application sent them.
    """
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
    """One step per call, where a single gesture made several.

    Clicking Save on the supplier screen sends a POST that creates the supplier
    and a PUT that sets its address. The frame kept both and everything
    downstream read only the "primary" one, so the skill replayed the address
    and never created the supplier -- a task that looks right in review and does
    half the work.

    Split after pairing rather than before it, because the pairing is a fact
    about gestures: two runs of the same task click the same Save, and what that
    Save sent is what has to line up underneath it. Splitting first would ask
    the aligner to pair calls whose paths carry the parameter that makes the two
    runs different.
    """
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
"""ExtJS numbers its generated ids per page load: the same Save button is
``button-1347-btnIconEl`` in one demonstration and ``button-1494-btnIconEl`` in
the next. Compared verbatim, every unnamed control in this application is a
different control every session."""


def _control(frame: ActionFrame) -> str:
    """What the gesture acted on, as steadily as the page allows.

    The accessible name first, because ExtJS renumbers its generated ids between
    page loads and ``button-1148`` is not the same control tomorrow. Role and
    kind on their own would pair two different text boxes, which is the one
    mistake worth being strict about.

    An unnamed control has its generated numbers taken out, which is the same
    point made one level down: ``button-1347-btnIconEl`` and
    ``button-1494-btnIconEl`` are one Save button seen in two sessions.
    """
    target = frame.action.target
    if target is None:
        return str(frame.action.kind)
    identity = target.accessible_name or target.test_id or target.css_path or target.xpath or ""
    if not target.accessible_name:
        identity = _GENERATED.sub("#", identity)
    return f"{frame.action.kind}:{target.role or ''}:{identity}"


def _same(frame_a: ActionFrame, frame_b: ActionFrame) -> bool:
    """Whether these two steps are the same step of the same task.

    Either signal will do, because each fails on its own. The page renames its
    own controls -- one demonstration reported an accessible name of "Save" and
    the next, of the same button, reported none at all -- so identity alone
    refuses pairs that are plainly the same gesture. And what a step sent is
    absent from every step that only typed into a field, so calls alone would
    pair nothing in a form.

    What the step sent is the stronger of the two when both are present: the
    page describes the control, the application describes the call.
    """
    if _control(frame_a) == _control(frame_b):
        return True
    sent_a, sent_b = frame_a.primary_request, frame_b.primary_request
    if sent_a is None or sent_b is None:
        return False
    return sent_a.method.upper() == sent_b.method.upper() and _shape(sent_a.url) == _shape(
        sent_b.url
    )


def _shape(url: str) -> str:
    """A path with its identifiers taken out, so two runs of one task agree.

    ``/addresses/A00022791`` and ``/addresses/A00022812`` are the same step of
    the same task. Which record it was is what the diff exists to find; here it
    would only stop the two steps being recognised as each other.
    """
    return "/".join("*" if any(c.isdigit() for c in seg) else seg for seg in url_path_segments(url))


def _evidential(frame: ActionFrame) -> bool:
    """Whether dropping this step would lose something the skill needs.

    A gesture that changed the system, or carried a value into it, is evidence.
    A click that fetched nothing and typed nothing is the operator finding their
    way -- focusing a field, opening a panel to look, clicking a label twice.
    """
    if frame.action.value or frame.action.secret:
        return True
    # Background traffic is not what a step did. A keep-alive fires on a timer
    # and lands on whichever gesture happens to be open, so counting it made
    # clicking a paragraph of help text "evidence" -- and one operator reading
    # the screen for a moment longer than the other refused the whole pair.
    return any(
        request.is_mutation and not is_background_traffic(request.url) for request in frame.requests
    )


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
    return explode(paired)


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


def differences(run_a: tuple[ActionFrame, ...], run_b: tuple[ActionFrame, ...]) -> list[Difference]:
    found: list[Difference] = []
    for index, (frame_a, frame_b) in enumerate(align(run_a, run_b)):
        found.extend(_diff_action(index, frame_a, frame_b))
        found.extend(_diff_request(index, frame_a, frame_b))
    return found


def parameterise(
    run_a: tuple[ActionFrame, ...],
    run_b: tuple[ActionFrame, ...],
    *,
    ask_for: frozenset[str] = frozenset(),
    also: tuple[Choice, ...] = (),
) -> Parameterisation:
    """Diff, classify as input or derived, name, and address every substitution.

    ``ask_for`` names the fields an operator has since said they want to choose
    per run -- values both demonstrations happened to agree on. Their answer,
    not our inference: without it these stay exactly as they were demonstrated.

    ``also`` adds candidates the diff cannot find on its own. A single
    demonstration has nothing to disagree with, so the values a person typed are
    offered from there -- still gated by ``ask_for``, still never invented.
    """
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
        earliest_use = min(site.step_index for site in sites)
        source = _find_source(value_a, value_b, paired_a, paired_b, before=earliest_use)

        named_by = _names_it(sites)
        name = deduplicate(
            suggest_name(named_by.site, url=named_by.url, field_label=named_by.field_label), taken
        )
        taken.add(name)
        parameters.append(_build_parameter(name, value_a, value_b, sites, source))

        for difference in sites:
            substitutions.setdefault(difference.step_index, []).append(
                Substitution(site=difference.site, parameter=name)
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


def typed_values(run: tuple[ActionFrame, ...]) -> tuple[Choice, ...]:
    """Values a person typed, and where the calls afterwards carried them.

    Only for a demonstration with no partner. Two runs settle this by
    disagreeing: what changed is a parameter, what held is literal. One run
    cannot disagree with anything, so every value it sent looked equally fixed --
    including the supplier number an operator had just typed into a box labelled
    "What is the supplier number?". Replaying that creates the same supplier
    again.

    Typing is not an inference: the frame records that a human entered this
    value, and the control records what it was called. Everything else the call
    carried stays exactly as demonstrated, because nothing says it varies.
    """
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
            name = deduplicate(suggest_name(site, url=request.url, field_label=label), set())
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
    """The record a write addressed, where the operator picked it off a screen.

    Narrow on purpose. A create copies twenty fields off the record it was
    given -- the address line, the city, the postcode -- and every one of them
    was "chosen" in the sense that it came from a list. Asking about all twenty
    is worse than asking about none: fifteen questions arrived for one task and
    nobody would answer any of them.

    What actually matters is which *record* the call acts on, and that is in the
    URL path: `PUT /wm/addresses/A000144886`. Answer that one and the fields
    that carry the same value are settled with it, because they are not separate
    decisions -- they are the same address written down three times.
    """
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
            # Either run showing it on screen is enough. The second operator
            # may have had the panel open already, or reached it by a route
            # whose response the first one never fetched -- and a question that
            # changes nothing until it is answered is cheap to ask and
            # expensive to skip.
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
    """Every path the demonstration called, so a record can be told from a route.

    `/data/WM/wm/addresses/A000144886` and `/data/WM/wm/suppliers` both end in a
    segment that is constant across the runs, and only one of them is a record
    somebody picked: the demonstration also called `/data/WM/wm/addresses`, and
    never called `/data/WM/wm`. A path whose parent was fetched as a collection
    is addressing one of its members.
    """
    return frozenset(
        urlsplit(request.url).path.rstrip("/")
        for frame in run
        for request in frame.requests
        if not is_background_traffic(request.url)
    )


def _inside_a_collection(url: str, site: UrlPathSite, collections: frozenset[str]) -> bool:
    segments = url_path_segments(url)
    if site.index != len(segments) - 1:
        # Routes have segments after them; a record is the end of the address.
        return False
    return "/" + "/".join(segments[: site.index]) in collections


def _name_for(sites: tuple[Site, ...], url: str) -> str:
    """The call's own name for this value, preferring the payload's.

    `/wm/addresses/A000144886` names it `addresse_id` by position; the body
    calls it `addressId`. The body is the system's own vocabulary and does not
    depend on how the path happens to be pluralised.
    """
    bodies = [site for site in sites if isinstance(site, JsonBodySite)]
    # Among several, the one named after the collection: an address record
    # carries both `resourceId` and `addressId`, and only one of those means
    # anything to somebody being asked which address to use.
    segments = url_path_segments(url)
    collection = singular(segments[-2]) if len(segments) > 1 else ""
    named = [site for site in bodies if collection and collection in site.pointer.lower()]
    ranked: list[Site] = [*named, *bodies, *sites]
    return suggest_name(ranked[0], url=url, field_label=None)


def _listed_before(run: tuple[ActionFrame, ...], value: str, before: int) -> int | Literal[False]:
    """The step whose read offered this value, or False if none did.

    Matched against the values a response carried, never its text: `data` and
    `suppliers` appear in the body of every JSON payload ever sent, and matching
    text asked the operator whether the word "data" in the endpoint's own path
    was a choice they had made.
    """
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
    """Values an earlier call in this same task minted, bound to where they came from.

    The diff only sees what varies, so a record id the server assigned during
    the demonstration is invisible to it: both runs sent whatever that run's
    server said, and the value that reached the next call was different in each
    -- but only because the runs are different runs, not because an operator
    chose anything. Left alone it becomes a literal, and every replay writes to
    the record the demonstration happened to create.

    So a value is bound to the response that produced it when three things hold:
    both runs' responses carried it at the same pointer, the step that used it
    came later, and nobody in either run had that value in their hands before
    that response arrived. The last one is what separates a server-minted id
    from a facility code the operator picked on the first screen: a value that
    was already being sent was not produced by anything.
    """
    # One value is one parameter, however many places the call sends it: an id
    # in the path and the same id in the body is one thing the system produced.
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
    """The earlier response that produced this value, if one demonstrably did.

    Stricter than the diff's own source-finding, because there is no variation
    here to corroborate anything: an unvarying value matches by luck all the
    time. A list of forty addresses contains "CAN" and "SUP" and a dozen true
    flags, and binding a supplier's country to row 44 of a lookup would be a
    confident wrong answer of exactly the kind ADR 004 exists to prevent.

    So the value has to be unique in the response -- one pointer, not one of
    forty rows -- at the same pointer in both runs, and where the place it is
    later sent has a name, the response has to use that same name for it. The
    system's own vocabulary is the evidence; agreement on it is not luck.
    """
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
            # Row 44 of a lookup list. Position in a collection is not stable
            # between one run and the next, so a value read from one was never
            # a dependency -- it is the same value happening to sit in a list
            # somebody scrolled past.
            continue
        return step_index, pointer
    return None


def _key_of(site: Site) -> str | None:
    """What the call calls this value, where it calls it anything."""
    if isinstance(site, JsonBodySite):
        return site.pointer.rsplit("/", 1)[-1]
    if isinstance(site, UrlQuerySite):
        return site.key
    return None


def _constant_sites(a: CapturedRequest, b: CapturedRequest) -> list[tuple[Site, str]]:
    """Every addressable value this call sent that both runs sent identically."""
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
    """Whether anybody in this run had the value before that step answered.

    Typed, or sent in a URL or a body. The step that produced it is included:
    a call that sends an id in its own path did not learn that id from its own
    response, whatever the response repeats back.
    """
    for frame in run[: until + 1]:
        if frame.action.value == value:
            return True
        for request in frame.requests:
            if value in request.url or (request.request_text and value in request.request_text):
                return True
    return False


def _names_it(sites: list[Difference]) -> Difference:
    """Which of the places this value appears should name it.

    The call's own field name, wherever there is one. A screen labels the field
    "Supplier*\nWhat is the supplier number?" and the payload calls the same
    value `supplierNumber` -- and naming it after the label produced
    `supplier_what_is_the_supplier_number`, which is not only ugly: the model
    asked to fill it in refused to bind "ACMETEST9" to it, so the skill could
    not be run from a sentence at all. The system's own vocabulary is shorter,
    stabler, and already what every other part of this reads.
    """
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
        # One run fetched something the other did not. Whether that matters
        # depends entirely on what it was.
        lonely = request_a or request_b
        if lonely is not None and not lonely.is_mutation:
            # A read. The second demonstration of a task does not refetch what
            # the browser still has, and refusing the pair over a cache made
            # the operator record the whole task again to no purpose -- the
            # writes were identical both times. The step is kept; there is
            # simply nothing to diff at it.
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
        # Every call the gesture made, not its "primary" one: a Save that
        # created a record and then addressed it answers twice, and the id the
        # next step needs is in whichever of those the frame did not rank first.
        leaves_b = {pointer: str(leaf) for pointer, leaf in _response_leaves(run_b[step_index])}
        for pointer, leaf in _response_leaves(run_a[step_index]):
            if str(leaf) == value_a and leaves_b.get(pointer) == value_b:
                return step_index, pointer
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
