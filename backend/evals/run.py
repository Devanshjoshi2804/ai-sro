from __future__ import annotations

import json
import shutil
from collections.abc import Awaitable, Callable
from dataclasses import asdict, replace
from pathlib import Path
from typing import Protocol

from evals.model import Case, Report, Scored, as_markdown, every_time, gate, report
from evals.redact import redacted
from evals.replay import Replayed
from evals.suites.chat import Chat
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
    floor: float

    def asker(self, container: Container) -> Asker | None: ...

    async def cases(self, uow: UnitOfWork, tenant_id: TenantId) -> list[Case]: ...

    async def run(self, case: Case, asker: Asker) -> Scored: ...


SUITES: dict[str, Suite] = {"mining": Mining(), "reader": Reader(), "chat": Chat()}


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


def _retire(root: Path, tenant: str, name: str) -> None:
    results = root / "results" / tenant
    base = results / f"baseline-{name}.json"
    old = results / name
    gone = [str(one) for one in (base, old) if one.exists()]
    base.unlink(missing_ok=True)
    shutil.rmtree(old, ignore_errors=True)
    if gone:
        print(f"a new case set: retired {', '.join(gone)}")  # noqa: T201


async def frozen(
    root: Path,
    tenant: str,
    name: str,
    build: Callable[[], Awaitable[list[Case]]],
    *,
    rebuild: bool = False,
) -> list[Case]:
    path = root / "cases" / tenant / f"{name}.json"
    found = None if rebuild else _thawed(path)
    if found is not None:
        return found
    cases = await build()
    _retire(root, tenant, name)
    return _freeze(path, cases)


async def run_suite(
    name: str,
    tenant: str,
    *,
    baseline: bool,
    limit: int | None = None,
    rebuild: bool = False,
    repeat: int = 1,
) -> int:
    suite, container = SUITES[name], build_container()
    asker = suite.asker(container)
    if asker is None:
        raise SystemExit("make eval needs gemini_api_key and interpretation_enabled")

    async def build() -> list[Case]:
        async with container.unit_of_work() as uow:
            return await suite.cases(uow, TenantId(tenant))

    cases = (await frozen(HERE, tenant, name, build, rebuild=rebuild))[:limit]
    results = HERE / "results" / tenant
    scored = []
    with about(tenant=tenant):
        for case in cases:
            runs = [await suite.run(case, asker) for _ in range(repeat)]
            one = every_time(runs)
            answers = list(runs[0].answers) or ([runs[0].answer] if runs[0].answer else [])
            replace(case, answer=one.answer, answers=answers or None).save(results / name)
            scored.append(one)
    now = report(name, suite.prompt, scored)
    base = results / f"baseline-{name}.json"
    failed = gate(Report.load(base) if base.is_file() else None, now, floor=suite.floor)
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
            if case.answer is not None and case.answers is None:
                bad.append(
                    f"{path.name}: only the first answer is recorded; a replay needs them all"
                )
                continue
            recorded = case.answers or []
            if any(not conforms(one, suite.prompt.output_schema) for one in recorded):
                bad.append(f"{path.name}: a recorded answer does not match {suite.prompt.name}")
                continue
            replay = Replayed(case.answers if case.answers is not None else case.answer)
            asker = suite.asker(container) if container else replay
            with about(tenant="eval"):
                one = await suite.run(case, asker or replay)
            if not one.passed:
                bad.append(f"{path.name}: expected to pass, did not")
    if not seen:
        bad.append(f"no committed cases under {folder}: the redacted set guards nothing")
    for line in bad:
        print(line)  # noqa: T201
    return 1 if bad else 0


async def write_candidates(name: str, tenant: str, *, root: Path = HERE) -> int:
    current = {one.id for one in _thawed(root / "cases" / tenant / f"{name}.json") or []}
    out = root / "candidates" / tenant / name
    for path in sorted((root / "results" / tenant / name).glob("*.json")):
        case = Case.load(path)
        if case.id in current:
            redacted(case, tenant=tenant).save(out)
    print(f"read every file in {out} before moving any to ci/")  # noqa: T201
    return 0
