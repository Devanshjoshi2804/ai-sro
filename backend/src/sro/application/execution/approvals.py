from __future__ import annotations

import asyncio

K_APPROVAL_WAIT_S = 300.0


class Approvals:
    def __init__(self) -> None:
        self._waiting: dict[str, asyncio.Event] = {}

    def register(self, run_id: str) -> None:
        self._waiting.setdefault(run_id, asyncio.Event())

    async def wait_for(
        self,
        run_id: str,
        timeout: float = K_APPROVAL_WAIT_S,  # noqa: ASYNC109
    ) -> bool:
        self.register(run_id)
        event = self._waiting[run_id]
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            return True
        except TimeoutError:
            return False
        finally:
            self._waiting.pop(run_id, None)

    def approve(self, run_id: str) -> bool:
        event = self._waiting.get(run_id)
        if event is None:
            return False
        event.set()
        return True

    def waiting(self) -> frozenset[str]:
        return frozenset(self._waiting)

    def forget(self, run_id: str) -> None:
        self._waiting.pop(run_id, None)
