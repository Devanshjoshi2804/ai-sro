from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
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
from sro.container import Container, build_container
from sro.domain.prompts.record import Prompt, conforms
from sro.domain.shared.identifiers import TenantId
from sro.whose import about

HERE = Path(__file__).parent


class Suite(Protocol):
    name: str
    prompt: Prompt

    def asker(self, container: Container) -> Asker | None: ...

    async def cases(self, uow: UnitOfWork, tenant_id: TenantId) -> list[Case]: ...

    async def run(self, case: Case, asker: Asker) -> Scored: ...


SUITES: dict[str, Suite] = {"mining": Mining(), "reader": Reader()}


def _thawed(path: Path) -> list[Case] | None:
    if not path.is_file():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Case(one["id"], one["suite"], one["input"], one["expected"]) for one in raw]


def _freeze(path: Path, cases: list[Case]) -> list[Case]:
    path.parent.mkdir(parents=True, exist_ok=True)
    kept = [asdict(one) for one in cases]
    path.write_text(json.dumps(kept, indent=1, ensure_ascii=False), encoding="utf-8")
    return _thawed(path) or []


async def frozen(path: Path, build: Callable[[], Awaitable[list[Case]]]) -> list[Case]:
    found = _thawed(path)
    return found if found is not None else _freeze(path, await build())


async def run_suite(name: str, tenant: str, *, baseline: bool, limit: int | None = None) -> int:
    suite, container = SUITES[name], build_container()
    asker = suite.asker(container)
    if asker is None:
        raise SystemExit("make eval needs gemini_api_key and interpretation_enabled")

    async def build() -> list[Case]:
        async with container.unit_of_work() as uow:
            return await suite.cases(uow, TenantId(tenant))

    cases = (await frozen(HERE / "cases" / tenant / f"{name}.json", build))[:limit]
    results = HERE / "results" / tenant
    scored = []
    with about(tenant=tenant):
        for case in cases:
            one = await suite.run(case, asker)
            replace(case, answer=one.answer).save(results / name)
            scored.append(one)
    now = report(name, suite.prompt, scored)
    base = results / f"baseline-{name}.json"
    failed = gate(Report.load(base) if base.is_file() else None, now)
    out = results / f"{name}-{suite.prompt.name}-v{suite.prompt.version}.md"
    out.write_text(as_markdown(now, failed), encoding="utf-8")
    if baseline and not failed:
        base.write_text(json.dumps(asdict(now), indent=1), encoding="utf-8")
    print(out.read_text(encoding="utf-8"))  # noqa: T201
    return 1 if failed else 0


async def run_ci(*, live: bool, folder: Path = HERE / "ci") -> int:
    container = build_container() if live else None
    bad, seen = [], 0
    for name, suite in SUITES.items():
        for path in sorted((folder / name).glob("*.json")):
            seen += 1
            case = Case.load(path)
            if case.answer is not None and not conforms(case.answer, suite.prompt.output_schema):
                bad.append(f"{path.name}: the recorded answer does not match {suite.prompt.name}")
                continue
            asker = suite.asker(container) if container else Replayed(case.answer)
            with about(tenant="eval"):
                one = await suite.run(case, asker or Replayed(case.answer))
            if not one.passed:
                bad.append(f"{path.name}: expected to pass, did not")
    if not seen:
        bad.append(f"no committed cases under {folder}: the redacted set guards nothing")
    for line in bad:
        print(line)  # noqa: T201
    return 1 if bad else 0


async def write_candidates(name: str, tenant: str) -> int:
    folder = HERE / "results" / tenant / name
    for path in sorted(folder.glob("*.json")):
        redacted(Case.load(path), tenant=tenant).save(HERE / "candidates" / tenant / name)
    print(f"read every file in {HERE / 'candidates' / tenant / name} before moving any to ci/")  # noqa: T201
    return 0
