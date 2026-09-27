from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Iterable

from evals.model import K_COVERS, K_OWN, Case, Scored
from sro.application.observation.mining_pass import propose
from sro.application.ports.model import Asker
from sro.application.ports.repositories import UnitOfWork
from sro.container import Container
from sro.domain.execution.compose import normal
from sro.domain.observation.trim import is_secret
from sro.domain.observation.values import frequencies_over, shared_values
from sro.domain.observation.window import Packed, Window, as_evidence, evidence_tokens
from sro.domain.prompts.mine import MINE
from sro.domain.shared.identifiers import TenantId
from sro.domain.skill.workflow import Workflow, cited_ids, is_a_chore, ordered_cites

K_NOISE_S = 300.0


def request_values(typed: Iterable[str], seen: set[str]) -> list[str]:
    return sorted({value for value in typed if value in seen})


def _seen(workflow: Workflow) -> set[str]:
    return {
        str(value)
        for parameter in workflow.parameters
        for value in parameter.get("seen_values", [])  # type: ignore[attr-defined]
    }


class Mining:
    name = "mining"
    prompt = MINE

    def asker(self, container: Container) -> Asker | None:
        return container.mining_asker()

    async def cases(self, uow: UnitOfWork, tenant_id: TenantId) -> list[Case]:
        intents = {one.gesture_id: one for one in await uow.gestures.intents_for(tenant_id)}
        known = await uow.workflows.known(tenant_id)
        family: dict[str, set[str]] = defaultdict(set)
        for one in known:
            family[normal(one.title)] |= _seen(one)
        found = []
        for workflow in known:
            if is_a_chore(workflow):
                continue
            cites = ordered_cites(workflow)
            cited = await uow.gestures.gestures_for(tenant_id, ids=tuple(cites))
            if not cited:
                continue
            streams = {one.stream_id for one in cited}
            around = await uow.gestures.gestures_for(
                tenant_id,
                after=min(one.at for one in cited) - K_NOISE_S,
                before=max(one.at for one in cited) + K_NOISE_S,
            )
            day = [one for one in around if one.stream_id in streams]
            crossings = shared_values(day, intents, frequencies_over(day, intents))
            typed = [
                str(one.action.value).strip()
                for one in day
                if one.action.value and not is_secret(one)
            ]
            found.append(
                Case(
                    id=workflow.id,
                    suite=self.name,
                    input={
                        "day": [
                            {
                                "id": one.id,
                                "at": one.at,
                                "evidence": as_evidence(one, intents.get(one.id)),
                            }
                            for one in day
                        ],
                        "crossings": crossings,
                    },
                    expected={
                        "cites": list(dict.fromkeys(cites)),
                        "values": request_values(typed, family[normal(workflow.title)]),
                    },
                )
            )
        return found

    async def run(self, case: Case, asker: Asker) -> Scored:
        day = case.input.get("day")
        items = [
            Packed(
                gesture_id=str(one["id"]),
                at=float(one["at"]),
                evidence=dict(one["evidence"]),
                strength=0.0,
                tokens=evidence_tokens(dict(one["evidence"])),
            )
            for one in (day if isinstance(day, list) else [])
            if isinstance(one, dict)
        ]
        crossings = case.input.get("crossings")
        started = time.monotonic()
        proposed, answer = await propose(
            Window(items=items),
            crossings if isinstance(crossings, dict) else {},
            [],
            "",
            asker=asker,
            tenant="eval",
        )
        latency = time.monotonic() - started
        wanted = {str(one) for one in case.expected.get("cites", [])}  # type: ignore[attr-defined]
        values = {str(one) for one in case.expected.get("values", [])}  # type: ignore[attr-defined]
        passed = any(
            len(wanted & cited_ids(one)) >= K_COVERS * len(wanted)
            and len(wanted & cited_ids(one)) >= K_OWN * len(cited_ids(one))
            and values <= _seen(one)
            for one in proposed
        )
        return Scored(
            case.id, passed, bool(proposed), answer.cost_usd, latency, answer.data, answer.error
        )
