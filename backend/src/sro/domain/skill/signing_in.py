from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from urllib.parse import parse_qs, quote, urlsplit, urlunsplit

from sro.domain.execution.compose import normal
from sro.domain.observation.gesture import Action, Gesture, Target, passed_through
from sro.domain.observation.trim import is_secret, path_shape
from sro.domain.shared.hosts import origin_of, page_of
from sro.domain.skill.checks import signs_in_to
from sro.domain.skill.workflow import Step, Workflow, ordered_cites

_AUTHORIZE = frozenset({"response_type", "client_id", "redirect_uri", "state"})
_ASKS_FOR = frozenset({"current-password", "one-time-code"})


@dataclass(frozen=True, slots=True)
class PageSignals:
    url: str
    visited: tuple[str, ...] | None = ()
    password: bool = False
    autocomplete: frozenset[str] = frozenset()


def _asks(url: str) -> dict[str, list[str]]:
    return parse_qs(urlsplit(url).query, keep_blank_values=True)


def _where(url: str) -> tuple[str, str]:
    return origin_of(url), urlsplit(url).path


def an_authorize_request(url: str) -> bool:
    return _asks(url).keys() >= _AUTHORIZE


def _returns_to(url: str) -> str | None:
    if not an_authorize_request(url):
        return None
    return page_of(_asks(url)["redirect_uri"][0])


def a_navigation(url: str) -> str:
    parts = urlsplit(url)
    back = _returns_to(url)
    named = {segment.partition("=")[0] for segment in parts.query.split("&") if "=" in segment}
    names = [
        f"{name}={quote(back, safe='')}" if name == "redirect_uri" and back else name
        for name in _asks(url)
        if name in named
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "&".join(names), ""))


def _in_round_trip(urls: tuple[str, ...]) -> bool:
    stack: list[tuple[str, str]] = []
    for url in urls:
        where = _where(url)
        if where in stack:
            stack.remove(where)
        if (returns := _returns_to(url)) is not None:
            stack.append(_where(returns))
    return bool(stack)


def a_sign_in_page(page: PageSignals) -> bool:
    return (
        page.password
        or bool(page.autocomplete & _ASKS_FOR)
        or page.visited is None
        or _in_round_trip((*page.visited, page.url))
    )


def asks_for_a_code(page: PageSignals) -> bool:
    return "one-time-code" in page.autocomplete


def expired(page: PageSignals, recorded_page: str | None) -> bool:
    here, there = page.url, recorded_page or ""
    moved = (origin_of(here), path_shape(here)) != (origin_of(there), path_shape(there))
    return moved and a_sign_in_page(page)


def signs_in_at(
    where: str, among: Sequence[Workflow], by_id: Mapping[str, Gesture], *, not_this: str = ""
) -> str | None:
    origin = origin_of(where)
    if not origin:
        return None
    found = [
        job.id
        for job in among
        if job.signs_in and job.id != not_this and _starts_at(job, by_id) == origin
    ]
    return found[0] if len(found) == 1 else None


def _starts_at(job: Workflow, by_id: Mapping[str, Gesture]) -> str | None:
    cited = [by_id[one] for one in ordered_cites(job) if one in by_id]
    if not cited:
        return None
    first = min(range(len(cited)), key=lambda index: (cited[index].at, index))
    return origin_of(cited[first].url or cited[first].system or "")


K_ONE_SUBMIT_S = 0.05


def sign_in_chain(job: Workflow, by_id: Mapping[str, Gesture]) -> list[Step]:
    steps = sorted(job.steps, key=lambda one: one.order)
    cited = _in_order(job, by_id)
    typed = [one.at for one in cited if is_secret(one)] or [
        one.at for one in cited if one.action.kind == "type"
    ]
    landed = [
        one
        for one in cited
        if typed and one.at >= min(typed) and one.action.kind != "type" and passed_through(one)
    ]
    if not landed:
        return steps
    cut = landed[0]
    fields = [one for one in cited if one.action.kind == "type" and one.at <= cut.at]
    before_cut = max(
        (one for one in cited if one.at < cut.at), key=lambda one: one.at, default=None
    )

    def refused(gesture: Gesture) -> bool:
        if gesture.at < min(typed) or passed_through(gesture):
            return False
        if origin_of(gesture.system or "") != origin_of(cut.system or ""):
            return False
        if not _submits(gesture, fields):
            return False
        if gesture.action.kind == "press" and _same_submit(cut, gesture, before_cut):
            return True
        return any(
            before.at <= gesture.at
            and any(
                gesture.at < again.at and _same_field(before.action.target, again.action.target)
                for again in fields
            )
            for before in fields
        )

    def replayed(one: str) -> bool:
        gesture = by_id.get(one)
        if gesture is None or gesture is cut:
            return True
        return gesture.at <= cut.at and not refused(gesture)

    chain = [replace(step, cites=[one for one in step.cites if replayed(one)]) for step in steps]

    def late(step: Step) -> tuple[bool, float, int]:
        return (
            cut.id in step.cites,
            max((by_id[one].at for one in step.cites if one in by_id), default=float("-inf")),
            step.order,
        )

    holder = max((step for step in chain if cut.id in step.cites), key=lambda step: step.order)
    seen = {cut.id}
    once = []
    for step in sorted(chain, key=late):
        fresh = [one for one in step.cites if one not in seen]
        seen.update(fresh)
        if step is holder:
            fresh.append(cut.id)
        if fresh:
            once.append(replace(step, cites=fresh))
    return sorted(once, key=late)


def _submits(gesture: Gesture, typed: Sequence[Gesture]) -> bool:
    if gesture.action.kind == "press":
        return gesture.action.value in (None, "", "Enter", "NumpadEnter")
    return gesture.action.kind == "click" and not any(
        _same_field(gesture.action.target, field.action.target) for field in typed
    )


def _same_submit(cut: Gesture, press: Gesture, before_cut: Gesture | None) -> bool:
    if cut.action.detail is not None:
        return cut.action.detail == 0 and press is before_cut
    return cut.at - press.at <= K_ONE_SUBMIT_S


def _same_field(one: Target | None, other: Target | None) -> bool:
    if one is None or other is None:
        return False
    if one.css_path or other.css_path:
        return one.css_path == other.css_path
    return (one.tag, one.role, one.name) == (other.tag, other.role, other.name)


@dataclass(frozen=True, slots=True)
class RecordedLogin:
    job_id: str
    origin: str
    username: str | None
    label: str | None = None


@dataclass(frozen=True, slots=True)
class Logins:
    names: frozenset[str] = frozenset()
    # (system, box): a box name counts only on the system its sign-in lands on.
    labels: frozenset[tuple[str, str]] = frozenset()


def recorded_login(
    where: str, among: Sequence[Workflow], by_id: Mapping[str, Gesture]
) -> RecordedLogin | None:
    system = origin_of(where)
    landing = [
        job
        for job in among
        if job.signs_in and (lands := signs_in_to(job, by_id)) is not None and lands[1] == system
    ]
    typed = _typed_login(landing[0], by_id) if len(landing) == 1 else None
    if typed is None:
        return None
    credential, last = typed
    origin = origin_of(credential.url or credential.system or "")
    if not origin:
        return None
    return RecordedLogin(
        job_id=landing[0].id,
        origin=origin,
        username=last.value if last else None,
        label=last.target.name if last and last.target else None,
    )


def recorded_logins(among: Sequence[Workflow], by_id: Mapping[str, Gesture]) -> Logins:
    found = [
        (lands[1], last)
        for job in among
        if job.signs_in
        and (lands := signs_in_to(job, by_id)) is not None
        and (typed := _typed_login(job, by_id)) is not None
        and (last := typed[1]) is not None
    ]
    return Logins(
        names=frozenset(normal(last.value) for _, last in found if last.value),
        labels=frozenset(
            (system, normal(last.target.name))
            for system, last in found
            if last.target and last.target.name
        ),
    )


def _typed_login(
    job: Workflow, by_id: Mapping[str, Gesture]
) -> tuple[Gesture, Action | None] | None:
    """The job's credential, and the last thing it typed before it: the username."""
    credential = _credential(job, by_id)
    if credential is None:
        return None
    before = [
        gesture
        for gesture in _in_order(job, by_id)
        if gesture.at <= credential.at
        and gesture.action.kind == "type"
        and not is_secret(gesture)
        and gesture.action.value
    ]
    return credential, before[-1].action if before else None


def _credential(job: Workflow, by_id: Mapping[str, Gesture]) -> Gesture | None:
    return next((gesture for gesture in _in_order(job, by_id) if is_secret(gesture)), None)


def _in_order(job: Workflow, by_id: Mapping[str, Gesture]) -> list[Gesture]:
    cited = [by_id[one] for one in ordered_cites(job) if one in by_id]
    return sorted(cited, key=lambda gesture: gesture.at)


__all__ = [
    "Logins",
    "PageSignals",
    "RecordedLogin",
    "a_navigation",
    "a_sign_in_page",
    "an_authorize_request",
    "asks_for_a_code",
    "expired",
    "recorded_login",
    "recorded_logins",
    "sign_in_chain",
    "signs_in_at",
]
