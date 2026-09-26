from __future__ import annotations

import hashlib
import time
from dataclasses import asdict

from evals.model import Case, Scored
from sro.application.chat.understand import understand
from sro.application.ports.model import Asker
from sro.application.ports.repositories import UnitOfWork
from sro.container import Container
from sro.domain.chat.asked_by import mails_behind, texts
from sro.domain.execution.compose import normal
from sro.domain.prompts.read_request import READ_REQUEST
from sro.domain.prompts.record import quoted_in
from sro.domain.shared.identifiers import TenantId
from sro.domain.skill.workflow import Step, Workflow


def _job(raw: dict[str, object]) -> Workflow:
    steps = [Step(**one) for one in raw.pop("steps", [])]  # type: ignore[attr-defined]
    raw.pop("repeat", None)
    raw.pop("same_as", None)
    return Workflow(**raw, steps=steps)  # type: ignore[arg-type]


class Reader:
    name = "reader"
    prompt = READ_REQUEST

    def asker(self, container: Container) -> Asker | None:
        return container.asker

    async def cases(self, uow: UnitOfWork, tenant_id: TenantId) -> list[Case]:
        workflows = list(await uow.workflows.known(tenant_id))
        cites = tuple(sorted({one for w in workflows for s in w.steps for one in s.cites}))
        by_id = {one.id: one for one in await uow.gestures.gestures_for(tenant_id, ids=cites)}
        asked_by = {w.id: texts(mails_behind(w, by_id)) for w in workflows}
        found = []
        for workflow in workflows:
            same = [w.id for w in workflows if normal(w.title) == normal(workflow.title)]
            for mail in asked_by[workflow.id]:
                values = {
                    str(p["name"]): value
                    for p in workflow.parameters
                    for value in p.get("seen_values", [])  # type: ignore[attr-defined]
                    if isinstance(value, str) and quoted_in(value, mail)
                }
                found.append(
                    Case(
                        id=f"{workflow.id}:{hashlib.sha256(mail.encode()).hexdigest()[:8]}",
                        suite=self.name,
                        input={
                            "said": mail,
                            "jobs": [asdict(w) | {"repeat": None} for w in workflows],
                            "asked_by": {
                                k: [m for m in v if m != mail] for k, v in asked_by.items()
                            },
                        },
                        expected={"jobs": same, "values": values},
                    )
                )
        return found

    async def run(self, case: Case, asker: Asker) -> Scored:
        jobs = [_job(dict(one)) for one in case.input["jobs"]]  # type: ignore[attr-defined]
        asked_by = case.input.get("asked_by")
        started = time.monotonic()
        got = await understand(
            str(case.input["said"]), jobs, asker, asked_by if isinstance(asked_by, dict) else {}
        )
        latency = time.monotonic() - started
        wanted = case.expected.get("values")
        right_job = got.workflow_id in (case.expected.get("jobs") or [])  # type: ignore[operator]
        right_values = all(
            got.values.get(name) == value
            for name, value in (wanted or {}).items()  # type: ignore[attr-defined]
        )
        return Scored(
            case.id,
            right_job and got.sure and right_values,
            got.sure,
            got.answer.cost_usd,
            latency,
            got.answer.data,
            got.answer.error,
        )
