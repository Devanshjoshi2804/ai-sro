from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from sro.application.knowledge.record_claim import Claim
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel

logger = logging.getLogger(__name__)

_EVIDENCE_BY_NAME = {
    "asserted": EvidenceLevel.ASSERTED,
    "observed": EvidenceLevel.OBSERVED,
    "reproduced": EvidenceLevel.REPRODUCED,
    "round-trip": EvidenceLevel.ROUND_TRIP,
    "round_trip": EvidenceLevel.ROUND_TRIP,
}


def read_catalogue(root: Path, *, system: str) -> tuple[Claim, ...]:
    claims: list[Claim] = []
    claims.extend(_screens(root, system))
    claims.extend(_endpoints(root, system))
    claims.extend(_fields(root, system))
    claims.extend(_forms(root, system))
    claims.extend(_flows(root, system))
    claims.extend(_statuses(root, system))
    claims.extend(_quirks(root, system))
    return tuple(claims)


def _load(root: Path, relative: str) -> Any | None:
    path = root / relative
    if not path.is_file():
        logger.warning("knowledge base is missing %s", relative)
        return None
    return json.loads(path.read_text())


def _screens(root: Path, system: str) -> Iterator[Claim]:
    document = _load(root, "index/app-map.json")
    for screen in (document or {}).get("screens", []):
        route = screen.get("hash") or screen.get("label")
        if not route:
            continue
        yield Claim(
            system=system,
            kind=EntryKind.SCREEN,
            key=route,
            title=" ▸ ".join(screen.get("nav_path") or [screen.get("label", route)]),
            body={
                "label": screen.get("label"),
                "area": screen.get("area"),
                "tier": screen.get("tier"),
                "kind": screen.get("kind"),
                "reads": screen.get("reads", []),
                "actions": screen.get("actions", []),
                "columns": [
                    column for grid in screen.get("grids", []) for column in grid.get("columns", [])
                ],
                "can_create": screen.get("can_create"),
                "can_delete": screen.get("can_delete"),
                "resources": screen.get("resources", []),
            },
            source="index/app-map.json",
            evidence=(
                EvidenceLevel.ASSERTED
                if screen.get("unverified") or screen.get("route_dead")
                else EvidenceLevel.OBSERVED
            ),
        )


def _endpoints(root: Path, system: str) -> Iterator[Claim]:
    for endpoint in _load(root, "index/api-endpoints.json") or []:
        path = endpoint.get("path")
        if not path:
            continue
        yield Claim(
            system=system,
            kind=EntryKind.ENDPOINT,
            key=path,
            title=f"{endpoint.get('resource', path)} ({endpoint.get('kind', 'endpoint')})",
            body={
                "service": endpoint.get("service"),
                "resource": endpoint.get("resource"),
                "kind": endpoint.get("kind"),
                "params": endpoint.get("params", []),
                "seen_on_routes": endpoint.get("seen_on_routes", []),
                "hits": endpoint.get("hits", 0),
            },
            source="index/api-endpoints.json",
            evidence=(
                EvidenceLevel.OBSERVED
                if int(endpoint.get("hits") or 0) > 0
                else EvidenceLevel.ASSERTED
            ),
        )


def _fields(root: Path, system: str) -> Iterator[Claim]:
    document = _load(root, "index/field-dictionary.json")
    for entry in (document or {}).get("fields", []):
        key = entry.get("key")
        if not key:
            continue
        labels = entry.get("labels") or []
        yield Claim(
            system=system,
            kind=EntryKind.FIELD,
            key=key,
            title=f"{labels[0] if labels else key} ({key})",
            body={
                "labels": labels,
                "type": entry.get("type"),
                "description": entry.get("description"),
                "required_on": entry.get("required_on", []),
                "screens": entry.get("screens", []),
                "procedures": entry.get("procedures", []),
                "documented": entry.get("documented", False),
                "max_length": entry.get("maxLength"),
            },
            source="index/field-dictionary.json",
            evidence=EvidenceLevel.ASSERTED,
        )


def _forms(root: Path, system: str) -> Iterator[Claim]:
    document = _load(root, "index/form-models-all.json")
    for form in (document or {}).get("forms", []):
        route = form.get("hash")
        fields = form.get("fields")
        if not route or not fields:
            continue
        yield Claim(
            system=system,
            kind=EntryKind.FORM,
            key=route,
            title=f"{form.get('label', route)} — create form",
            body={
                "label": form.get("label"),
                "area": form.get("area"),
                "field_count": form.get("field_count"),
                "fields": fields,
                "required": form.get("required", []),
                "create_via": form.get("create_via"),
            },
            source="index/form-models-all.json",
            evidence=EvidenceLevel.OBSERVED,
        )


def _flows(root: Path, system: str) -> Iterator[Claim]:
    flows_dir = root / "http" / "flows"
    if not flows_dir.is_dir():
        return
    for path in sorted(flows_dir.glob("*.json")):
        document = json.loads(path.read_text())
        spec = document.get("spec") or path.stem
        resource = document.get("resource") or spec
        calls = document.get("calls") or []
        if not calls or not all(
            isinstance(call.get("request"), dict) and call["request"].get("url") for call in calls
        ):
            continue
        steps = [
            {
                "method": (call.get("request") or {}).get("method"),
                "endpoint": call.get("endpoint"),
                "status": (call.get("response") or {}).get("status"),
            }
            for call in calls
        ]
        writes = sum(1 for step in steps if step["method"] not in (None, "GET", "HEAD"))
        yield Claim(
            system=system,
            kind=EntryKind.FLOW,
            key=spec,
            title=f"{resource} — recorded cascade ({len(calls)} calls, {writes} writes)",
            body={
                "resource": resource,
                "spec": spec,
                "applied": document.get("applied") or {},
                "steps": steps,
                "evidence_file": f"http/flows/{path.name}",
            },
            source=f"http/flows/{path.name}",
            evidence=EvidenceLevel.OBSERVED,
        )


def _statuses(root: Path, system: str) -> Iterator[Claim]:
    document = _load(root, "http/status-matrix.json")
    for resource, detail in ((document or {}).get("resources") or {}).items():
        for case, observation in (detail.get("cases") or {}).items():
            yield Claim(
                system=system,
                kind=EntryKind.STATUS,
                key=f"{resource}:{case}",
                title=f"{resource} — {case} answers {observation.get('status')}",
                body={
                    "resource": resource,
                    "case": case,
                    "method": observation.get("method"),
                    "url": observation.get("url"),
                    "status": observation.get("status"),
                    "kind": observation.get("kind"),
                    "message": observation.get("userMessage") or observation.get("message"),
                    "evidence_file": detail.get("evidence"),
                },
                source="http/status-matrix.json",
                evidence=(
                    EvidenceLevel.REPRODUCED
                    if int(observation.get("observations") or 1) > 1
                    else EvidenceLevel.OBSERVED
                ),
            )


def _quirks(root: Path, system: str) -> Iterator[Claim]:
    document = _load(root, "http/claims.json")
    for claim in (document or {}).get("claims", []):
        identifier = claim.get("id")
        if not identifier:
            continue
        verdict = str(claim.get("verdict") or "")
        yield Claim(
            system=system,
            kind=EntryKind.QUIRK,
            key=identifier,
            title=claim.get("claim", identifier)[:200],
            body={
                "claim": claim.get("claim"),
                "verdict": verdict,
                "observed": claim.get("observed", []),
                "evidence_file": claim.get("evidence"),
                "origin": claim.get("source"),
                "falsified": "FALSIFIED" in verdict.upper(),
            },
            source="http/claims.json",
            evidence=_EVIDENCE_BY_NAME.get(
                str(claim.get("evidence_level", "")).lower(), EvidenceLevel.ASSERTED
            ),
        )
