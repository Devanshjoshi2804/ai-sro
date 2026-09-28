from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Literal

from evals.model import Case, Scored
from evals.replay import Replayed
from sro.application.context import RequestContext
from sro.application.ports.model import Asker
from sro.application.ports.page import PageDriver
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.vision import VisionDriver
from sro.application.runtime.broker import SessionBroker
from sro.application.runtime.sight_lane import ALLOWED, sight_goal
from sro.application.runtime.step import Held
from sro.application.runtime.ui_lane import ui_payload
from sro.container import Container
from sro.domain.execution.evidence import primary_gesture, writes
from sro.domain.prompts.sight import SIGHT
from sro.domain.shared.identifiers import PrincipalId, TenantId

Break = Literal["restructured", "relabelled", "repair"]
_SELECTORS = ("css_path", "xpath", "test_id")
_UNREACHABLE = -1.0


def broken(payload: Mapping[str, object], how: Break) -> dict[str, object]:
    """The recorded target as the page no longer matches it.

    restructured: the build changed, so every selector is stale; the label stays.
    relabelled: the label changed; the structure stays.
    repair: only what repair scores by and no locator can use -- the chain
    (a locator only when longer than one), bounds and placeholder."""
    target = dict(payload.get("target") or {})  # type: ignore[call-overload]
    attributes = dict(target.get("attributes") or {})
    if how == "relabelled":
        target.pop("text", None)
        target["name"] = f"{target.get('name') or ''} (renamed)".strip()
        return {**payload, "target": target, "learned": None}
    for key in _SELECTORS:
        target.pop(key, None)
    attributes.pop("id", None)
    if how == "restructured":
        target.pop("component", None)
    else:
        for key in ("name", "text"):
            target.pop(key, None)
        for key in ("name", "autocomplete"):
            attributes.pop(key, None)
        chain = (target.get("component") or {}).get("chain") or ()
        target["component"] = {"chain": list(chain)}
    target["attributes"] = attributes
    return {**payload, "target": target, "learned": None}


def _recorded(payload: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in payload.items() if key != "write"}


class Repair:
    prompt = SIGHT

    def __init__(
        self,
        lane: Literal["sight", "ui"],
        vision: VisionDriver | None,
        broker: SessionBroker,
        driver: PageDriver,
        how: Break = "repair",
    ) -> None:
        self.name = f"repair-{lane}" if how == "repair" else f"resolve-{how}"
        self._lane, self._vision, self._broker, self._driver = lane, vision, broker, driver
        self._how = how

    def asker(self, container: Container) -> Asker | None:
        return Replayed(None)

    async def cases(self, uow: UnitOfWork, tenant_id: TenantId) -> list[Case]:
        found = []
        for workflow in await uow.workflows.known(tenant_id):
            if not await uow.workflows.proofs(tenant_id, workflow.id):
                continue
            ids = tuple(one for step in workflow.steps for one in step.cites)
            by_id = {g.id: g for g in await uow.gestures.gestures_for(tenant_id, ids=ids)}
            for step in workflow.steps:
                primary = primary_gesture(step, by_id)
                target = primary.action.target if primary else None
                if primary is None or target is None or not target.xpath or not primary.page_url:
                    continue
                if self._lane == "ui" and writes(step, by_id):
                    continue
                found.append(
                    Case(
                        id=f"{workflow.id}:{step.order}",
                        suite=self.name,
                        input={
                            "tenant": tenant_id.value,
                            "page": primary.page_url,
                            "goal": sight_goal(step, {}, primary),
                            "write": writes(step, by_id),
                            "payload": ui_payload(step, primary, None, None, by_id),
                        },
                        expected={},
                    )
                )
        return found

    async def run(self, case: Case, asker: Asker | None) -> Scored:
        ctx = RequestContext(TenantId(str(case.input["tenant"])), PrincipalId("eval"))
        page = str(case.input["page"])
        account = await self._broker.account_for(ctx, page)
        held = await self._broker.acquire(ctx, account, page, holder=f"eval:{case.id}")
        try:
            return await self._scored(case, held)
        finally:
            await self._broker.release(ctx, held)

    async def _scored(self, case: Case, held: Held) -> Scored:
        payload = dict(case.input["payload"])  # type: ignore[call-overload]
        held_by = await self._driver.resolve(held.session, held.target_id, _recorded(payload))
        if not held_by.ok or held_by.candidates != 1 or not held_by.xpath:
            return Scored(case.id, False, False, 0.0, _UNREACHABLE)
        started = time.monotonic()
        if self._lane == "ui":
            got = await self._driver.resolve(
                held.session, held.target_id, broken(payload, self._how)
            )
            named = got.ok and got.candidates == 1
            if self._how == "repair" and named and got.matched_by != "repair":
                return Scored(case.id, False, False, 0.0, _UNREACHABLE)
            passed = named and got.xpath == held_by.xpath
            return Scored(
                case.id,
                passed,
                named,
                0.0,
                time.monotonic() - started,
                answer={"matched_by": got.matched_by},
            )
        if self._vision is None:
            raise SystemExit("the repair-sight suite needs vision_enabled and gemini_api_key")
        screen = await self._driver.screenshot(held.session, held.target_id)
        proposed = await self._vision.propose(
            goal=str(case.input["goal"]), screen=screen, allowed=ALLOWED, history=()
        )
        if proposed.x is None or proposed.y is None:
            return Scored(case.id, False, False, 0.0, time.monotonic() - started)
        hit = await self._driver.hit_test(held.session, held.target_id, proposed.x, proposed.y)
        if not hit or not hit.get("strategy"):
            return Scored(case.id, False, True, 0.0, time.monotonic() - started)
        again = await self._driver.resolve(
            held.session,
            held.target_id,
            {
                **_recorded(payload),
                "target": {},
                "learned": {"strategy": hit["strategy"], "query": hit["query"]},
                "frame_path": hit.get("frame_path"),
            },
        )
        passed = again.ok and again.candidates == 1 and again.xpath == held_by.xpath
        return Scored(case.id, passed, True, 0.0, time.monotonic() - started)
