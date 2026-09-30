from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path

from sro.domain.prompts.record import Prompt

K_COVERS = 0.8
K_OWN = 0.5
K_COST_TOLERANCE = 0.1


@dataclass(frozen=True, slots=True)
class Case:
    id: str
    suite: str
    input: dict[str, object]
    expected: dict[str, object]
    answer: dict[str, object] | None = None

    def save(self, folder: Path) -> Path:
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{self.id.replace(':', '_')}.json"
        path.write_text(json.dumps(asdict(self), indent=1, ensure_ascii=False), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> Case:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(raw["id"], raw["suite"], raw["input"], raw["expected"], raw.get("answer"))


@dataclass(frozen=True, slots=True)
class Scored:
    case_id: str
    passed: bool
    sure: bool
    cost_usd: float
    latency_s: float
    answer: dict[str, object] | None = None
    error: str | None = None
    fell_back: bool = False


@dataclass(frozen=True, slots=True)
class Report:
    suite: str
    prompt: str
    version: int
    model: str
    cases: int
    accuracy: float
    sure_but_wrong: float
    cost_per_case: float
    p50_s: float
    p95_s: float
    errors: int = 0
    fallbacks: int = 0
    case_ids: tuple[str, ...] = ()

    @classmethod
    def load(cls, path: Path) -> Report:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(**raw | {"case_ids": tuple(raw.get("case_ids", ()))})


def _at(ordered: list[float], q: float) -> float:
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))] if ordered else 0.0


def report(suite: str, prompt: Prompt, scored: Sequence[Scored]) -> Report:
    n = len(scored) or 1
    latencies = sorted(one.latency_s for one in scored)
    return Report(
        suite=suite,
        prompt=prompt.name,
        version=prompt.version,
        model=prompt.model,
        cases=len(scored),
        accuracy=sum(one.passed for one in scored) / n,
        sure_but_wrong=sum(one.sure and not one.passed for one in scored) / n,
        cost_per_case=sum(one.cost_usd for one in scored) / n,
        p50_s=_at(latencies, 0.5),
        p95_s=_at(latencies, 0.95),
        errors=sum(one.error is not None for one in scored),
        fallbacks=sum(one.fell_back for one in scored),
        case_ids=tuple(sorted(one.case_id for one in scored)),
    )


def gate(before: Report | None, after: Report, *, floor: float = 0.0) -> list[str]:
    failed = [f"{after.errors} case(s) errored"] if after.errors else []
    if after.accuracy < floor:
        failed.append(f"accuracy {after.accuracy:.1%} is below the {floor:.0%} floor")
    if before is None:
        return failed
    if after.case_ids != before.case_ids:
        failed.append("the case set differs from the baseline's")
        return failed
    if after.accuracy < before.accuracy:
        failed.append(f"accuracy fell: {before.accuracy:.1%} -> {after.accuracy:.1%}")
    if after.sure_but_wrong > before.sure_but_wrong:
        failed.append(
            f"sure-but-wrong rose: {before.sure_but_wrong:.1%} -> {after.sure_but_wrong:.1%}"
        )
    if after.cost_per_case > before.cost_per_case * (1 + K_COST_TOLERANCE):
        failed.append(
            f"cost per case rose: ${before.cost_per_case:.5f} -> ${after.cost_per_case:.5f}"
        )
    return failed


def as_markdown(report: Report, failed: Sequence[str]) -> str:
    rows = [
        f"### make eval — {report.suite}: {report.prompt} v{report.version} on {report.model}",
        "",
        "| cases | errors | fallbacks | accuracy | sure-but-wrong | cost/case | p50 | p95 |",
        "|---|---|---|---|---|---|---|---|",
        f"| {report.cases} | {report.errors} | {report.fallbacks} | {report.accuracy:.1%} | "
        f"{report.sure_but_wrong:.1%} | "
        f"${report.cost_per_case:.5f} | {report.p50_s:.2f} s | {report.p95_s:.2f} s |",
        "",
        "Gate: " + ("passed" if not failed else "FAILED — " + "; ".join(failed)),
    ]
    return "\n".join(rows)
