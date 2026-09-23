# Notes for `backend/src/sro/domain/recording/axgraph.py`

Comments and docstrings moved out of [`backend/src/sro/domain/recording/axgraph.py`](../../../../../../../backend/src/sro/domain/recording/axgraph.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/recording/axgraph.py#L1): Docstring

> The accessibility tree, kept as a graph. See docs/11-capture-completeness.md.

## `AxGraph`, [line 12](../../../../../../../backend/src/sro/domain/recording/axgraph.py#L12): Docstring

> Full AX tree at one instant, with parent/child edges preserved.
>
> A flat list answers "was this label on the page". A graph answers "what is
> this control inside", which is what disambiguates the third Save button and
> what a heal step needs to rank candidates.

## `AxGraph`, [line 15](../../../../../../../backend/src/sro/domain/recording/axgraph.py#L15): Note on the line above

Code: `frame_url: str | None = None`

> Set when the snapshot is of a subframe rather than the top document.

## `AxGraph.ancestors`, [line 34](../../../../../../../backend/src/sro/domain/recording/axgraph.py#L34): Docstring

> Walk to the root. Cycle-guarded: a malformed capture must not hang.

## `AxGraph.path`, [line 45](../../../../../../../backend/src/sro/domain/recording/axgraph.py#L45): Docstring

> Human-readable ancestry, e.g. ``dialog “Release” > form > button “Confirm”``.
>
> This is the disambiguation signal a bare accessible name cannot give.
