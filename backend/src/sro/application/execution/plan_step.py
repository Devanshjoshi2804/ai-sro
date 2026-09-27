from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Mapping
from types import MappingProxyType
from typing import get_args

from sro.application.capture.rig_wire import headers_without_markers
from sro.application.ports.model import Asker
from sro.application.shared.asking import ask
from sro.domain.execution.cascade import writes_of
from sro.domain.execution.evidence import (
    Locator,
    control_names,
    locators_for,
    primary_gesture,
    recorded_call,
    writes,
)
from sro.domain.execution.learned_step import LearnedStep
from sro.domain.execution.planning import (
    LIVE_FETCHABLE_HEADERS,
    Look,
    Planned,
    unreplayable,
    value_for,
)
from sro.domain.execution.secrets import field_of, needs_a_secret, secret_key_of
from sro.domain.execution.verified_writes import VerifiedWrite, verified_write_for
from sro.domain.execution.write_plan import WritePlan, wanted_by, write_plan_for
from sro.domain.observation.gesture import Call, Gesture, Kind
from sro.domain.observation.trim import trim
from sro.domain.prompts.plan_step import PLAN_STEP
from sro.domain.prompts.record import Prompt
from sro.domain.prompts.see_step import SEE_STEP
from sro.domain.shared.hosts import REDACTED, origin_of
from sro.domain.shared.prices import Answer
from sro.domain.skill.workflow import Step

SecretFor = Callable[[str], Awaitable[str | None]]

ACTIONS: frozenset[str] = frozenset(get_args(Kind))

VALUED = ("type", "select", "upload", "press")


def _replay_of(
    step: Step,
    by_id: Mapping[str, Gesture],
    values: Mapping[str, str],
    verified_writes: tuple[VerifiedWrite, ...],
    seen: Mapping[str, frozenset[str]],
    keys: Mapping[str, str] = MappingProxyType({}),
) -> tuple[dict[str, object], WritePlan | None] | None:
    call = recorded_call(step, by_id)
    if call is None or unreplayable(call):
        return None
    verified = verified_write_for(call, verified_writes) is not None
    aimed = write_plan_for(step, by_id, values, verified_writes, seen, keys)
    if aimed is None and values and verified:
        return None
    wanted = wanted_by(step, by_id, seen)
    if verified and wanted and not any(values.get(name, "").strip() for name in wanted):
        return None
    recorded = call.request_body.text if call.request_body else None
    payload: dict[str, object] = {
        "method": call.method.upper(),
        "url": aimed.url if aimed is not None else call.url,
        "headers": headers_without_markers(call.request_headers),
        "body": aimed.body if aimed is not None else (recorded or None),
    }
    if verified:
        live = [
            name
            for name, value in call.request_headers.items()
            if REDACTED in value and name.lower() in LIVE_FETCHABLE_HEADERS
        ]
        if live:
            payload["live_headers"] = live
    return payload, aimed


def replay_without_asking(
    *,
    step: Step,
    cited: list[Gesture],
    values: Mapping[str, str],
    verified_writes: tuple[VerifiedWrite, ...],
    seen: Mapping[str, frozenset[str]] = MappingProxyType({}),
    keys: Mapping[str, str] = MappingProxyType({}),
    starts_on: str | None = None,
) -> Planned | None:
    by_id = {gesture.id: gesture for gesture in cited}
    call = recorded_call(step, by_id)
    if call is None or verified_write_for(call, verified_writes) is None:
        return None
    if _a_cascade(call, cited, verified_writes):
        return None
    sending = _replay_of(step, by_id, values, verified_writes, seen, keys)
    if sending is None:
        return None
    payload, aimed = sending
    if starts_on:
        payload["starts_on"] = starts_on
    return Planned(
        "http.send",
        payload,
        "the evidence records this call and the ledger has watched it succeed",
        Answer(),
        rewrote=aimed is not None,
        filled=dict(aimed.filled) if aimed is not None else {},
        confirm=dict(aimed.confirm) if aimed is not None else {},
        by="evidence",
    )


def _a_cascade(call: Call, cited: list[Gesture], ledger: tuple[VerifiedWrite, ...]) -> bool:
    doing = next((one for one in cited if call in one.requests), None)
    if doing is None:
        return False
    return len(writes_of(doing, ledger)) > 1


def _primary(step: Step, cited: list[Gesture], values: Mapping[str, str]) -> Gesture | None:
    holds = {name for name, value in values.items() if value.strip()}
    found = primary_gesture(step, {gesture.id: gesture for gesture in cited}, holds)
    return found or (cited[0] if cited else None)


def _ladder(primary: Gesture, learned: LearnedStep | None) -> list[Locator]:
    rungs = locators_for(primary)
    if learned is None or not learned.usable:
        return rungs
    first = Locator(learned.strategy, learned.query, visible_only=True)
    return [first, *[rung for rung in rungs if rung.as_payload() != first.as_payload()]]


def _clicking(
    ladder: list[Locator], origin: str | None, allow_focus: bool, starts_on: str | None
) -> dict[str, object]:
    payload: dict[str, object] = {
        "action": "click",
        "value": None,
        "locators": [rung.as_payload() for rung in ladder],
        "origin": origin,
    }
    if allow_focus:
        payload["allow_focus"] = True
    if starts_on:
        payload["starts_on"] = starts_on
    return payload


async def plan_step(
    *,
    step: Step,
    learned: LearnedStep | None = None,
    cited: list[Gesture],
    values: Mapping[str, str],
    look: Look,
    origin: str | None,
    starts_on: str | None,
    allow_focus: bool,
    asker: Asker,
    prompt: Prompt = PLAN_STEP,
    opened: bool = False,
    failure: str | None = None,
    failed_look: Look | None = None,
    verified_writes: tuple[VerifiedWrite, ...] = (),
    seen: Mapping[str, frozenset[str]] = MappingProxyType({}),
    keys: Mapping[str, str] = MappingProxyType({}),
    tenant_id: str = "",
    secret_for: SecretFor | None = None,
) -> Planned:
    primary = _primary(step, cited, values)
    evidence = json.dumps(
        {
            "step": {"order": step.order, "says": step.says, "parameters": step.parameters},
            "evidence": [trim(gesture) for gesture in cited],
            "values": dict(values),
            "browser": {"url": look.url, "screen_text": look.digest},
            "step_page": (primary.page_url or primary.url) if primary else None,
            "previous_attempt_failed": failure,
            "previous_attempt_left": None
            if failed_look is None
            else {
                "url": failed_look.url,
                "screen_text": failed_look.digest,
                "screenshot": None
                if not failed_look.screenshot
                else ("the second image" if look.screenshot else "the only image"),
            },
        },
        indent=2,
        ensure_ascii=False,
    )
    answer = await ask(
        asker,
        prompt,
        trusted={},
        untrusted={"evidence": evidence},
        image=look.screenshot,
        images=(failed_look.screenshot,) if failed_look and failed_look.screenshot else (),
    )
    if answer.data is None or primary is None:
        return Planned("none", {}, answer.error or "no evidence to act on", answer)

    data = answer.data
    kind = data.get("kind")
    why = str(data.get("why") or "")
    if kind == "navigate":
        url = data.get("url")
        if not isinstance(url, str) or not url:
            return Planned("none", {}, "navigate with no url", answer)
        return Planned(
            "navigate", {"url": url, "origin": origin, "allow_focus": allow_focus}, why, answer
        )

    if kind == "http.send":
        by_id = {gesture.id: gesture for gesture in cited}
        call = recorded_call(step, by_id)
        if call is None:
            return Planned(
                "none", {}, "http.send planned for a step whose evidence carries no call", answer
            )
        sending = _replay_of(step, by_id, values, verified_writes, seen, keys)
        if sending is not None:
            payload, aimed = sending
            if starts_on:
                payload["starts_on"] = starts_on
            return Planned(
                "http.send",
                payload,
                why,
                answer,
                rewrote=aimed is not None,
                filled=dict(aimed.filled) if aimed is not None else {},
                confirm=dict(aimed.confirm) if aimed is not None else {},
            )
        if unreplayable(call):
            why = f"recorded call is not replayable; {why}"
        elif values and verified_write_for(call, verified_writes) is not None:
            why = f"the recorded body cannot be re-aimed at this run's values; {why}"

    asked = data.get("action") if data.get("action") in ACTIONS else primary.action.kind
    action = primary.action.kind if needs_a_secret(primary) and asked not in VALUED else asked
    said = data.get("value")
    if action not in VALUED:
        asked = sorted(name for name in step.parameters if name in values)
        if asked and not writes(step, {gesture.id: gesture for gesture in cited}):
            if not opened:
                return Planned(
                    "ui.perform",
                    _clicking(locators_for(primary), origin, allow_focus, starts_on),
                    f"opening the list so {asked[0]} can be chosen by value",
                    answer,
                    opens=True,
                )
            wanted = values[asked[0]]
            return Planned(
                "ui.perform",
                _clicking([Locator("text", wanted)], origin, allow_focus, starts_on),
                f"choosing {wanted} from the open list",
                answer,
            )
        if asked:
            return Planned(
                "none",
                {},
                f"step {step.order} was given {', '.join(asked)} and a "
                f"{action} cannot carry a value: this step also writes, so the "
                "list cannot be opened first, and performing it would use the "
                "recorded choice instead of the one asked for",
                answer,
            )
    secret = None
    if action in VALUED and needs_a_secret(primary):
        if secret_for is None:
            return Planned(
                "none",
                {},
                f"step {step.order} types a password and this run has no vault to ask",
                answer,
            )
        here = look.url or (look.elsewhere if look.elsewhere_is_ours else "")
        recorded = origin_of(primary.url or "") or (primary.system or "")
        on = origin_of(here) or recorded
        wanted = secret_key_of(tenant_id or "", on, field_of(primary))
        secret = await secret_for(wanted)
        if not secret:
            return Planned(
                "none",
                {
                    "needs_secret": {
                        "system": on,
                        "field": field_of(primary),
                        "key": wanted,
                    }
                },
                f"step {step.order} types a password and nothing is stored under {wanted!r}",
                answer,
            )

    payload = {
        "action": action,
        "value": secret
        if secret is not None
        else value_for(step, primary, values, None if said is None else str(said))
        if action in VALUED
        else None,
        "locators": [rung.as_payload() for rung in _ladder(primary, learned)],
        "origin": origin,
    }
    if allow_focus:
        payload["allow_focus"] = True
    if starts_on:
        payload["starts_on"] = starts_on
    chosen = str(payload["value"]) if action in VALUED and payload.get("value") else ""
    if not chosen and opened:
        chosen = next(
            (
                values[name]
                for name in sorted(control_names(primary))
                if values.get(name, "").strip()
            ),
            "",
        )
    if chosen:
        option = _option_named(cited, chosen)
        if option:
            if not opened:
                return Planned(
                    "ui.perform", payload, f"{why}, and its list is open", answer, opens=True
                )
            return Planned(
                "ui.perform",
                _clicking(
                    [Locator("role_and_name", f"option|{option}")],
                    origin,
                    allow_focus,
                    starts_on,
                ),
                f"choosing {option!r} from the list the box opened",
                answer,
            )
    return Planned("ui.perform", payload, why, answer)


def _option_named(cited: list[Gesture], wanted: str) -> str:
    typed = next(
        (str(one.action.value) for one in cited if one.action.kind in VALUED and one.action.value),
        "",
    )
    if not typed:
        return ""
    for gesture in cited:
        target = gesture.action.target
        if gesture.action.kind != "click" or target is None or target.component is None:
            continue
        if not str(target.component.xtype).lower().endswith("boundlist"):
            continue
        said = target.name or target.text or ""
        if typed in said:
            return said.replace(typed, wanted)
    return ""


def _point_on(said: object, look: Look) -> tuple[int, int] | None:
    if not isinstance(said, dict):
        return None
    x, y = said.get("x"), said.get("y")
    if not (isinstance(x, int) and isinstance(y, int)):
        return None
    return (x, y) if 0 <= x < look.width and 0 <= y < look.height else None


async def plan_by_sight(
    *,
    step: Step,
    cited: list[Gesture],
    values: Mapping[str, str],
    look: Look,
    origin: str | None,
    asker: Asker,
    failure: str | None,
    opened: bool = False,
) -> Planned:
    primary = _primary(step, cited, values)
    if look.screenshot is None or not look.width or not look.height:
        why = f"no screen to look at: {look.refused}" if look.refused else "no screen to look at"
        return Planned("none", {}, why, Answer())
    if primary is None:
        return Planned("none", {}, "no evidence to act on", Answer())
    evidence = json.dumps(
        {
            "step": {"order": step.order, "says": step.says, "parameters": step.parameters},
            "demonstrated_on": trim(primary),
            "values": dict(values),
            "browser": {"url": look.url, "screen_text": look.digest},
            "viewport": {"width": look.width, "height": look.height},
            "previous_attempt_failed": failure,
        },
        indent=2,
        ensure_ascii=False,
    )
    answer = await ask(
        asker, SEE_STEP, trusted={}, untrusted={"evidence": evidence}, image=look.screenshot
    )
    data = answer.data
    if data is None:
        return Planned("none", {}, answer.error or "no answer", answer)
    why = str(data.get("why") or "")
    points_at = str(data.get("points_at") or "")
    if points_at != "the_control":
        clearing = points_at in ("what_reveals_it", "what_is_in_the_way")
        reveal = _point_on({"x": data.get("x"), "y": data.get("y")}, look) if clearing else None
        if reveal is not None:
            return Planned(
                "ui.perform_at",
                {"origin": origin, "x": reveal[0], "y": reveal[1], "action": "click"},
                (
                    f"clearing what is in the way: {why}"
                    if points_at == "what_is_in_the_way"
                    else f"opening what the control is under: {why}"
                )
                if why
                else "clearing the way to the control",
                answer,
                opens=True,
            )
        offered = {"x": data.get("x"), "y": data.get("y")} if clearing else None
        refusal = why or "the control is not on this screen"
        if offered is not None and reveal is None:
            refusal = (
                f"{refusal} (it named {offered!r} to open, which is not on the screen it was shown)"
            )
        return Planned("none", {}, refusal, answer)
    x, y = data.get("x"), data.get("y")
    if not (
        isinstance(x, int) and isinstance(y, int) and 0 <= x < look.width and 0 <= y < look.height
    ):
        return Planned("none", {}, f"the point ({x}, {y}) is not on the screen", answer)
    action = data.get("action")
    payload: dict[str, object] = {"origin": origin, "x": x, "y": y, "action": action}
    if action == "type":
        said = data.get("value")
        value = value_for(step, primary, values, str(said) if said is not None else None)
        if value is None:
            return Planned("none", {}, "nothing to type: no value for this control", answer)
        payload["value"] = value
    return Planned("ui.perform_at", payload, why, answer)
