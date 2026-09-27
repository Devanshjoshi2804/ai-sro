from __future__ import annotations

import hashlib
import time
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from evals.model import Case, Scored
from sro.application.chat.candidates import candidate_of, rank_jobs
from sro.application.chat.understand import held_runs, shown, understand
from sro.application.ports.model import Asker
from sro.application.ports.repositories import UnitOfWork
from sro.application.skill.job_facts import job_facts
from sro.container import Container
from sro.domain.chat.asked_by import mails_behind, texts
from sro.domain.chat.request import Candidate
from sro.domain.execution.compose import normal
from sro.domain.execution.field_classes import FieldClass, FieldLimits
from sro.domain.prompts.read_request import READ_REQUEST
from sro.domain.prompts.record import quoted_in
from sro.domain.shared.identifiers import TenantId


def _case_form(candidate: Candidate) -> dict[str, object]:
    kinds = {one.name: one for one in candidate.fields}
    form = shown(candidate)
    form["fields"] = [
        {
            **one,
            "kind": kinds[str(one["name"])].kind,
            "limits": asdict(kinds[str(one["name"])].limits),
        }
        for one in form["fields"]  # type: ignore[attr-defined]
    ]
    return form


def _candidate(raw: dict[str, Any]) -> Candidate:
    fields = raw["fields"]
    return Candidate(
        id=str(raw["id"]),
        title=str(raw["title"]),
        fields=tuple(
            FieldClass(
                one["name"],
                one["kind"],
                tuple(one["labels"]),
                FieldLimits(
                    one["limits"]["max_length"],
                    None if one["limits"]["options"] is None else tuple(one["limits"]["options"]),
                    one["limits"]["required_on_screen"],
                ),
            )
            for one in fields
        ),
        aliases={alias: one["name"] for one in fields for alias in one["aliases"]},
        seen={one["name"]: tuple(one["seen"]) for one in fields},
        asked_by=tuple(raw.get("asked_by", ())),
    )


class Reader:
    name = "reader"
    prompt = READ_REQUEST

    def asker(self, container: Container) -> Asker | None:
        return container.asker

    async def cases(self, uow: UnitOfWork, tenant_id: TenantId) -> list[Case]:
        workflows = list(await uow.workflows.known(tenant_id))
        facts = await job_facts(uow, tenant_id, workflows, now=datetime.now(tz=UTC))
        held = await held_runs(uow, tenant_id)
        found = []
        for one in facts:
            workflow = one.workflow
            same = [w.id for w in workflows if normal(w.title) == normal(workflow.title)]
            for mail in texts(mails_behind(workflow, one.by_id)):
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
                            "thread": mail,
                            "candidates": [
                                _case_form(candidate_of(ranked, leave_out=mail))
                                for ranked in rank_jobs(mail, facts, held=held)
                            ],
                        },
                        expected={"jobs": same, "values": values},
                    )
                )
        return found

    async def run(self, case: Case, asker: Asker) -> Scored:
        candidates = [_candidate(dict(one)) for one in case.input["candidates"]]  # type: ignore[attr-defined]
        started = time.monotonic()
        got = await understand(str(case.input["thread"]), candidates, asker)
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
