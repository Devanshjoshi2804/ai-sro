from __future__ import annotations

from collections.abc import Iterable, Mapping


def notes_on(sent: Mapping[str, str], known: Mapping[str, Mapping[str, object]]) -> tuple[str, ...]:
    said: list[str] = []
    for slot in sorted(sent):
        claim = known.get(slot)
        if not isinstance(claim, Mapping):
            continue
        limit = _limit(claim)
        if limit is None:
            continue
        value = sent[slot]
        if len(value) > limit:
            said.append(
                f"{_label(claim, slot)} holds {limit} characters and this run supplies {len(value)}"
                + (" (what the form itself says)" if _observed(claim) else "")
            )
    for slot in sorted(known):
        claim = known[slot]
        if not isinstance(claim, Mapping) or slot in sent:
            continue
        if claim.get("required") is True:
            said.append(
                f"{_label(claim, slot)} is required on this form and this run sends nothing"
            )
    return tuple(said)


def _limit(claim: Mapping[str, object]) -> int | None:
    limit = claim.get("max_length")
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        return None
    return limit


def _observed(claim: Mapping[str, object]) -> bool:
    return bool(claim.get("observed"))


def _label(claim: Mapping[str, object], slot: str) -> str:
    labels = claim.get("labels")
    if isinstance(labels, list):
        for label in labels:
            if isinstance(label, str) and label.strip():
                return label.strip()
    return slot


def limits_named(
    names: Iterable[str], *sources: Mapping[str, Mapping[str, object]]
) -> dict[str, int]:
    wanted = {_flat(name): name for name in names if _flat(name)}
    limits: dict[str, int] = {}
    for source in sources:
        seen: dict[str, int | None] = {}
        for slot, claim in source.items():
            limit = _limit(claim)
            for label in (*_labels(claim), slot):
                if (flat := _flat(label)) not in wanted:
                    continue
                seen[flat] = None if flat in seen and seen[flat] != limit else limit
        for flat, limit in seen.items():
            if limit is None:
                continue
            name = wanted[flat]
            limits[name] = min(limit, limits.get(name, limit))
    return limits


def keys_named(
    names: Iterable[str], *sources: Mapping[str, Mapping[str, object]]
) -> dict[str, str]:
    wanted = {_flat(name): name for name in names if _flat(name)}
    keys: dict[str, str] = {}
    for source in sources:
        seen: dict[str, str | None] = {}
        for slot, claim in source.items():
            for label in (*_labels(claim), slot):
                if (flat := _flat(label)) not in wanted:
                    continue
                seen[flat] = None if flat in seen and seen[flat] != slot else slot
        for flat, key in seen.items():
            if key is not None and wanted[flat] not in keys:
                keys[wanted[flat]] = key
    return keys


def _labels(claim: Mapping[str, object]) -> tuple[str, ...]:
    labels = claim.get("labels")
    if not isinstance(labels, list):
        return ()
    return tuple(one.strip() for one in labels if isinstance(one, str) and one.strip())


def _flat(name: str) -> str:
    return "".join(one for one in name.lower() if one.isalnum())
