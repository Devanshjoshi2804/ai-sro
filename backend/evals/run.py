from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Protocol

from evals.model import Case, Report, Scored, as_markdown, gate, report
from evals.redact import redacted
from evals.replay import Replayed
from evals.suites.mining import Mining
from evals.suites.reader import Reader
from sro.application.ports.model import Asker
from sro.application.ports.repositories import UnitOfWork
from sro.container import build_container
from sro.domain.prompts.record import Prompt, conforms
from sro.domain.shared.identifiers import TenantId
from sro.whose import about

HERE = Path(__file__).parent


class Suite(Protocol):
    name: str
    prompt: Prompt

    async def cases(self, uow: UnitOfWork, tenant_id: TenantId) -> list[Case]: ...

    async def run(self, case: Case, asker: Asker) -> Scored: ...


SUITES: dict[str, Suite] = {"mining": Mining(), "reader": Reader()}


async def run_suite(name: str, tenant: str, *, baseline: bool, limit: int | None = None) -> int:
    suite, container = SUITES[name], build_container()
    if container.asker is None:
        raise SystemExit("make eval needs gemini_api_key and interpretation_enabled")
    async with container.unit_of_work() as uow:
        cases = (await suite.cases(uow, TenantId(tenant)))[:limit]
    scored = []
    with about(tenant=tenant):
        for case in cases:
            case.save(HERE / "cases" / name)
            one = await suite.run(case, container.asker)
            replace(case, answer=one.answer).save(HERE / "cases" / name)
            scored.append(one)
    now = report(name, suite.prompt, scored)
    base = HERE / "results" / f"baseline-{name}.json"
    failed = gate(Report(**json.loads(base.read_text())), now) if base.is_file() else []
    out = HERE / "results" / f"{name}-{suite.prompt.name}-v{suite.prompt.version}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(as_markdown(now, failed), encoding="utf-8")
    if baseline and not failed:
        base.write_text(json.dumps(asdict(now), indent=1), encoding="utf-8")
    print(out.read_text(encoding="utf-8"))  # noqa: T201
    return 1 if failed else 0


async def run_ci(*, live: bool) -> int:
    asker = build_container().asker if live else None
    bad = []
    for name, suite in SUITES.items():
        for path in sorted((HERE / "ci" / name).glob("*.json")):
            case = Case.load(path)
            if case.answer is not None and not conforms(case.answer, suite.prompt.output_schema):
                bad.append(f"{path.name}: the recorded answer does not match {suite.prompt.name}")
                continue
            with about(tenant="eval"):
                one = await suite.run(case, asker or Replayed(case.answer))
            if not one.passed:
                bad.append(f"{path.name}: expected to pass, did not")
    for line in bad:
        print(line)  # noqa: T201
    return 1 if bad else 0


async def write_candidates(name: str, tenant: str) -> int:
    folder = HERE / "cases" / name
    for path in sorted(folder.glob("*.json")):
        redacted(Case.load(path), tenant=tenant).save(HERE / "candidates" / name)
    print(f"read every file in {HERE / 'candidates' / name} before moving any to ci/{name}")  # noqa: T201
    return 0
