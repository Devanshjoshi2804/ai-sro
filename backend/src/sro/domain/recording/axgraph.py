"""The accessibility tree, kept as a graph. See docs/11-capture-completeness.md."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime

from sro.domain.recording.element import ElementFingerprint
from sro.domain.shared.errors import InvariantViolation


@dataclass(frozen=True)
class AxGraph:
    """Full AX tree at one instant, with parent/child edges preserved.

    A flat list answers "was this label on the page". A graph answers "what is
    this control inside", which is what disambiguates the third Save button and
    what a heal step needs to rank candidates.
    """

    taken_at: datetime
    url: str
    frame_url: str | None = None
    """Set when the snapshot is of a subframe rather than the top document."""

    nodes: tuple[ElementFingerprint, ...] = ()
    root_id: str | None = None

    _index: dict[str, ElementFingerprint] = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.taken_at.tzinfo is None:
            raise InvariantViolation("AxGraph.taken_at must be timezone-aware")
        index = {node.node_id: node for node in self.nodes if node.node_id is not None}
        object.__setattr__(self, "_index", index)

    def node(self, node_id: str) -> ElementFingerprint | None:
        return self._index.get(node_id)

    def children(self, node: ElementFingerprint) -> tuple[ElementFingerprint, ...]:
        return tuple(child for child_id in node.child_ids if (child := self._index.get(child_id)))

    def ancestors(self, node: ElementFingerprint) -> Iterator[ElementFingerprint]:
        """Walk to the root. Cycle-guarded: a malformed capture must not hang."""
        seen: set[str] = set()
        current = node
        while current.parent_id is not None and current.parent_id not in seen:
            seen.add(current.parent_id)
            parent = self._index.get(current.parent_id)
            if parent is None:
                return
            yield parent
            current = parent

    def path(self, node: ElementFingerprint) -> str:
        """Human-readable ancestry, e.g. ``dialog “Release” > form > button “Confirm”``.

        This is the disambiguation signal a bare accessible name cannot give.
        """
        chain = [ancestor.describe() for ancestor in self.ancestors(node)]
        chain.reverse()
        chain.append(node.describe())
        return " > ".join(chain)

    @property
    def interactive(self) -> tuple[ElementFingerprint, ...]:
        return tuple(node for node in self.nodes if node.is_interactive)

    @property
    def names(self) -> frozenset[str]:
        return frozenset(node.accessible_name for node in self.nodes if node.accessible_name)
