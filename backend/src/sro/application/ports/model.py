"""The structured-output port every mined-workflow model call goes through.

The backend's ``IntentParser`` stays for utterances. This is the seam the
reading loop, the mining pass, the planner, the verifier and the chat door
all ask through, and the one place a fake goes in for every test that would
otherwise cost money.
"""

from __future__ import annotations

from typing import Protocol

from sro.domain.shared.prices import Answer, Effort


class Asker(Protocol):
    async def ask(
        self,
        *,
        model: str,
        instructions: str,
        evidence: str,
        schema: dict[str, object],
        image: bytes | None = None,
        images: tuple[bytes, ...] = (),
        effort: Effort | None = None,
    ) -> Answer: ...


class AskerUnavailable(Exception):
    """No model is configured. Not a ``DomainError``: the request was fine.

    Raised rather than handing a caller ``None`` or a no-op double, for the
    reason written on ``Container.asker``: a miner with nothing to ask must not
    run and quietly find nothing, because that reads exactly like a day with no
    work in it. Same shape and same reasoning as ``VaultUnavailable`` and
    ``SchedulerUnavailable`` -- a dependency that is absent, answered 503.
    """


def asker_or_refuse(asker: Asker | None) -> Asker:
    """The general model, or a 503 saying there is not one.

    A function and not a ``Container`` method, and the reason is the defect it
    avoids: the three callers each take ``Asker | None`` and refuse inside
    ``execute``, so that a deployment with no model can still build every
    factory. A container method would therefore have had no caller at all --
    one file away from ``container.asker``, whose docstring records having had
    no reader for a day.

    Refusing at the top of ``execute`` means the failure lands before a window
    is packed and before a run row is claimed, rather than somewhere in the
    middle of either.
    """
    if asker is None:
        raise AskerUnavailable(
            "no model is configured: set gemini_api_key and interpretation_enabled"
        )
    return asker
