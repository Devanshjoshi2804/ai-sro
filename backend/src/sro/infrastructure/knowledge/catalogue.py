"""The recorded knowledge base on disk, read as claims.

`knowledge-base/blue-yonder-sce/` was produced by driving the real application
and storing every exchange. This turns it into entries the system can retrieve,
carrying each record's own evidence level rather than flattening everything to
"we know this" -- the flattening is exactly what its own audit caught.

Reading only. Nothing here writes to the knowledge base directory: it is
evidence, and evidence that a program edits is no longer evidence.
"""

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
    """Every claim the recorded base makes, in one pass.

    Flows (`http/flows/*.json`) are deliberately skipped: no key appears in all
    35 files, so there is nothing to read them by that would not be guesswork.
    They stay as human-readable evidence until something needs them.
    """
    claims: list[Claim] = []
    claims.extend(_screens(root, system))
    claims.extend(_endpoints(root, system))
    claims.extend(_fields(root, system))
    claims.extend(_forms(root, system))
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
    """A screen: its route, what it reads, and what it lets an operator do."""
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
            # A screen nobody could open is a claim, not an observation.
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
            # `hits` counts times the endpoint was actually seen on the wire.
            # Zero means it was catalogued from a screen's configuration and
            # nobody has watched it answer.
            evidence=(
                EvidenceLevel.OBSERVED
                if int(endpoint.get("hits") or 0) > 0
                else EvidenceLevel.ASSERTED
            ),
        )


def _fields(root: Path, system: str) -> Iterator[Claim]:
    """A payload key and what the vendor's help says it means.

    Always `asserted`: this is documentation joined to a key, not a request
    anybody watched. It is the vocabulary layer -- what `abcCountFlag` is called
    on screen -- which is what makes an operator's sentence resolvable.
    """
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
    """The fields a create form actually posts, captured from the real form."""
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


def _statuses(root: Path, system: str) -> Iterator[Claim]:
    """What a resource answered for each case of the probe battery.

    This is the verifier's raw material, and the reason the base distinguishes
    two 404s: `ROUTE-MISSING` means the endpoint never existed, `RECORD-MISSING`
    means it exists and the record is gone. Only the second proves a delete.
    """
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
                # The battery was re-run: a case seen more than once matched
                # what was stored the first time, which is what reproduced means.
                evidence=(
                    EvidenceLevel.REPRODUCED
                    if int(observation.get("observations") or 1) > 1
                    else EvidenceLevel.OBSERVED
                ),
            )


def _quirks(root: Path, system: str) -> Iterator[Claim]:
    """Claims the base makes about behaviour, including the falsified ones.

    A falsified claim is kept with its verdict. "We believed this and it was
    wrong" is the single most useful thing in the base, and deleting it is how
    the same wrong belief gets rediscovered next quarter.
    """
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
