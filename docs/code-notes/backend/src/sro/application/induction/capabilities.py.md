# Notes for `backend/src/sro/application/induction/capabilities.py`

Comments and docstrings moved out of [`backend/src/sro/application/induction/capabilities.py`](../../../../../../../backend/src/sro/application/induction/capabilities.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/induction/capabilities.py#L1): Docstring

> Everything a demonstration proved, not only the thing it was about.
>
> An operator teaching "create a transport mode" opens the screen, and the screen
> lists the existing ones before they touch anything. That list is a GET, it
> answered 200, and its response is in the recording -- so the system already has
> the evidence to answer "how many transport modes are there" and was making the
> operator teach it a second time to get it.
>
> The rule stays what it has always been: nothing is invented. A capability is
> claimed only where a real request was made and a real response came back. What
> changes is that the *incidental* calls stop being thrown away because they were
> not what the operator had in mind.
>
> Only reads are claimed this way, and deliberately. A write that happened without
> anybody meaning to teach it is the one thing that must never quietly become a
> skill somebody can run.

## `ReadCapability`, [line 16](../../../../../../../backend/src/sro/application/induction/capabilities.py#L16): Docstring

> A read this demonstration performed, that answers a question about an entity.

## `ReadCapability`, [line 18](../../../../../../../backend/src/sro/application/induction/capabilities.py#L18): Note on the line above

Code: `entity: str`

> The entity as the endpoint names it, normalised: ``warehouseTransportModes``
> and ``transport_mode`` are the same subject asked about two ways.

## `ReadCapability`, [line 20](../../../../../../../backend/src/sro/application/induction/capabilities.py#L20): Note on the line above

Code: `rows: int`

> How many records came back in the response the demonstration captured.
> A collection is what answers "how many"; a single record answers "what
> is". Both are useful, and telling them apart costs one length check.

## `ReadCapability`, [line 22](../../../../../../../backend/src/sro/application/induction/capabilities.py#L22): Note on the line above

Code: `counted: int | None = None`

> How many existed when this was demonstrated, where the response said so.
>
> ``None`` when it came back as one page of something longer -- and then
> nothing about that afternoon is worth repeating as a number, because the
> length of a page is a fact about the request.

## `normalise`, [line 25](../../../../../../../backend/src/sro/application/induction/capabilities.py#L25): Docstring

> A name reduced to what it is about.
>
> ``warehouseTransportModes``, ``transport_modes`` and ``transportMode`` all
> become ``transportmode``: Blue Yonder prefixes the site-scoped variant of a
> resource with `warehouse`, and pluralises collections, and neither is a
> different subject.

## `reads_about`, [line 33](../../../../../../../backend/src/sro/application/induction/capabilities.py#L33): Docstring

> Reads this demonstration made about the entity it was about.
>
> Scoped to the entity on purpose. A screen fetches its policies, its unit
> conversions and its user's preferences before it shows anything, and turning
> every one of those into something an operator can ask for would bury the two
> that mean something under a dozen that do not.

## `_records_of`, [line 58](../../../../../../../backend/src/sro/application/induction/capabilities.py#L58): Docstring

> Whether this response carries the entity's own records.
>
> Judged against what the demonstration wrote, because that payload is the
> entity as the system itself describes it: a supplier has a
> `supplierNumber`, an `addressName`, a `clientId`. A response sharing none of
> those field names is about something else, whatever its URL says.
>
> Where the demonstration wrote nothing there is nothing to compare against,
> and the read is taken at its word -- a reading recording is all reads, and
> refusing every one of them would leave nothing at all.

## `_written_shape`, [line 65](../../../../../../../backend/src/sro/application/induction/capabilities.py#L65): Docstring

> The field names the demonstration sent when it changed the entity.

## `_resource_of`, [line 98](../../../../../../../backend/src/sro/application/induction/capabilities.py#L98): Docstring

> The last path segment that names a thing rather than an instance.

## `wrote_to`, [line 106](../../../../../../../backend/src/sro/application/induction/capabilities.py#L106): Docstring

> The collection the demonstration changed, if it changed one.
>
> The counterpart of a create is a read of the same collection. Blue Yonder's
> screen creates in `transportModes` and then refreshes `warehouseTransportModes`
> -- the site's own view of it -- so a read claimed from what the screen
> happened to fetch answers a narrower question than the write acts on, and
> says nothing about the difference.

## `_collection_of`, [line 116](../../../../../../../backend/src/sro/application/induction/capabilities.py#L116): Docstring

> The collection a call acted on, never the record inside it.
>
> `PUT /wm/addresses/A000144886` acts on the addresses collection. Reading the
> last segment gave `A000144886`, and that id was then offered to an operator
> as one of two collections their question might mean, and written into a
> skill summary as "writes to A000144886, which is a wider collection".

## `_is_a_record`, [line 123](../../../../../../../backend/src/sro/application/induction/capabilities.py#L123): Docstring

> A record's id names the record, not the collection it lives in.

## `reads_about`, [line 40](../../../../../../../backend/src/sro/application/induction/capabilities.py#L40): Comment

Code: `continue`

> The name is not enough. `/rpux/filter/columns/WMSupplier`
> ends in the entity, answers 200, and returns five rows -- of
> column definitions. A skill built from it told an operator
> there were five suppliers, which is the confident wrong
> answer this system exists to not give.

## `reads_about`, [line 50](../../../../../../../backend/src/sro/application/induction/capabilities.py#L50): Comment

Code: `found.setdefault(`

> First one wins: a screen that fetches the same list twice taught
> one capability, not two.

## `reads_about`, [line 55](../../../../../../../backend/src/sro/application/induction/capabilities.py#L55): Comment

Code: `return tuple(sorted(found.values(), key=lambda read: (normalise(read.entity) != wanted,)))`

> The subject itself, ahead of everything merely named after it.
> `warehouseTransportModeUoms` contains `transportmode` and is a list of
> unit conversions -- it was empty, it sorted first, and the skill built
> from it announced that there were 0 transport modes while seventeen were
> on screen. Containment finds the candidates; only equality identifies the
> subject.
