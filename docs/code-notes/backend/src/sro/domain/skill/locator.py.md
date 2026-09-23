# Notes for `backend/src/sro/domain/skill/locator.py`

Comments and docstrings moved out of [`backend/src/sro/domain/skill/locator.py`](../../../../../../../backend/src/sro/domain/skill/locator.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/domain/skill/locator.py#L1): Docstring

> How to find a control again, tomorrow, on a page that has been re-rendered.
>
> An element fingerprint records everything observed about a control at one
> moment. A locator is the other half: a statement about which of those signals is
> worth trusting later, ordered, so a driver tries the strongest first and can say
> which one it fell back to.
>
> The ordering is not cosmetic. Measured on this WMS: the accessibility tree
> carries no `button` role on three of four screens and never carries the field's
> payload key, while the DOM ids are assigned in render order -- `ext-gen4443` is
> a different control after a reload. The component model is the only view that is
> stable and the only one the application itself uses.

## `LocatorStrategy`, [line 11](../../../../../../../backend/src/sro/domain/skill/locator.py#L11): Note on the line above

Code: `COMPONENT = "component"`

> A query in the page's own component language, e.g. ExtJS
> ``rpFilterableViews rpFilterComboBox#filterComboBox``. Strongest where it
> exists: it is what the application's own code uses to find the control.

## `LocatorStrategy`, [line 14](../../../../../../../backend/src/sro/domain/skill/locator.py#L14): Note on the line above

Code: `ROLE_AND_NAME = "role_and_name"`

> The accessible way. Correct when the roles are there, and this WMS shows
> how often they are not.

## `LocatorStrategy`, [line 16](../../../../../../../backend/src/sro/domain/skill/locator.py#L16): Note on the line above

Code: `TEXT = "text"`

> Visible text. Fine for a menu item, dangerous for a grid cell whose text
> is the record being worked on -- so the text may be a template.

## `LocatorStrategy`, [line 18](../../../../../../../backend/src/sro/domain/skill/locator.py#L18): Note on the line above

Code: `CSS_PATH = "css_path"`

> Last resort, kept because it is occasionally the only thing left.

## `ControlLocator`, [line 24](../../../../../../../backend/src/sro/domain/skill/locator.py#L24): Note on the line above

Code: `query: Template`

> Strategy-specific: a component query, a test id, a role/name pair joined
> by ``|``, a text, a CSS path. A template because a locator may name the very
> record the run is about -- clicking the row for *this* LPN.

## `ControlLocator`, [line 26](../../../../../../../backend/src/sro/domain/skill/locator.py#L26): Note on the line above

Code: `within: str | None = None`

> Component query the match must sit inside. The same screen is often
> loaded several times over in this SPA and only one instance is visible.

## `ControlLocator`, [line 28](../../../../../../../backend/src/sro/domain/skill/locator.py#L28): Note on the line above

Code: `visible_only: bool = True`

> A driver acting on a hidden control has found the wrong one. The SPA
> keeps every screen it has ever shown, so the hidden matches outnumber the
> real one.
