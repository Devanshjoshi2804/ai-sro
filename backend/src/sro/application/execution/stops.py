from __future__ import annotations


class Stops:
    def __init__(self) -> None:
        self._asked: set[str] = set()

    def ask(self, run_id: str) -> None:
        self._asked.add(run_id)

    def asked(self, run_id: str) -> bool:
        return run_id in self._asked

    def forget(self, run_id: str) -> None:
        self._asked.discard(run_id)
