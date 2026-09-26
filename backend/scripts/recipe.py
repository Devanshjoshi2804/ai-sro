from __future__ import annotations

import argparse
import asyncio
import json

from sro.application.skill.job_facts import job_facts
from sro.container import build_container
from sro.domain.shared.identifiers import TenantId


def as_yaml(value: object, depth: int = 0) -> list[str]:
    pad = "  " * depth
    if isinstance(value, dict) and value:
        lines: list[str] = []
        for key, one in value.items():
            if isinstance(one, dict | list) and one:
                lines += [f"{pad}{key}:", *as_yaml(one, depth + 1)]
            else:
                lines.append(f"{pad}{key}: {json.dumps(one, ensure_ascii=False)}")
        return lines
    if isinstance(value, list) and value:
        lines = []
        for one in value:
            inner = as_yaml(one, depth + 1) if isinstance(one, dict | list) and one else []
            lines += (
                [f"{pad}- {inner[0].strip()}", *inner[1:]]
                if inner
                else [f"{pad}- {json.dumps(one, ensure_ascii=False)}"]
            )
        return lines
    return [pad + json.dumps(value, ensure_ascii=False)]


async def main(tenant: str, job: str) -> int:
    container = build_container()
    async with container.unit_of_work() as uow:
        workflow = await uow.workflows.get(TenantId(tenant), job)
        (facts,) = await job_facts(uow, TenantId(tenant), [workflow])
    print("\n".join(as_yaml(facts.compiled.view)))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--job", required=True)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.tenant, args.job)))
