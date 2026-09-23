# Notes for `backend/src/sro/domain/recording/element.py`

Comments and docstrings moved out of [`backend/src/sro/domain/recording/element.py`](../../../../../../../backend/src/sro/domain/recording/element.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/recording/element.py#L1): Docstring

> Accessibility node identity. See docs/06-glossary.md#element-fingerprint.

## `ComponentIdentity`, [line 19](../../../../../../../backend/src/sro/domain/recording/element.py#L19): Docstring

> What the application itself calls this control.
>
> Present only where the page is built out of components and the recorder
> could reach the framework. For ExtJS that is `xtype`, `itemId`, and a query
> in the framework's own selector language -- the three things that survive a
> re-render, which the DOM id and often the accessibility role do not.

## `ComponentIdentity`, [line 27](../../../../../../../backend/src/sro/domain/recording/element.py#L27): Note on the line above

Code: `required: bool | None = None`

> Ext's own `allowBlank: false`. None where the component said nothing.

## `ElementFingerprint`, [line 37](../../../../../../../backend/src/sro/domain/recording/element.py#L37): Docstring

> Every independent signal about one element at one moment.
>
> Redundant by design: a single selector breaks on redesign and leaves nothing
> to reason about, whereas a heal step can score candidates that still match on
> role, accessible name and ancestry after the DOM path moved.

## `ElementFingerprint`, [line 38](../../../../../../../backend/src/sro/domain/recording/element.py#L38): Note on the line above

Code: `node_id: str | None = None`

> AX tree node id. Identity within one snapshot only -- not stable across them.

## `ElementFingerprint`, [line 51](../../../../../../../backend/src/sro/domain/recording/element.py#L51): Note on the line above

Code: `required: bool | None = None`

> Whether the PAGE says this field must be filled -- `aria-required`, the
> HTML5 attribute, or a star on its label. None where nothing said.

## `ElementFingerprint`, [line 55](../../../../../../../backend/src/sro/domain/recording/element.py#L55): Note on the line above

Code: `states: frozenset[str] = frozenset()`

> AX states present: ``disabled``, ``checked``, ``expanded``, ``selected``,
> ``focused``, ``required``, ``invalid``, ``busy``.

## `ElementFingerprint`, [line 57](../../../../../../../backend/src/sro/domain/recording/element.py#L57): Note on the line above

Code: `component: ComponentIdentity | None = None`

> The framework's own handle on this control, when there is one.

## `ElementFingerprint.__post_init__`, [line 70](../../../../../../../backend/src/sro/domain/recording/element.py#L70): Comment

Code: `object.__setattr__(self, "attributes", MappingProxyType(dict(self.attributes)))`

> Without this the dataclass is frozen but its attributes dict is not.
