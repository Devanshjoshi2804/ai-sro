# Notes for `backend/src/sro/application/capture/identity.py`

Comments and docstrings moved out of [`backend/src/sro/application/capture/identity.py`](../../../../../../../backend/src/sro/application/capture/identity.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/capture/identity.py#L1): Docstring

> What a demonstration was about, read off what it did.
>
> The operator types a URL and nothing else, so the objective key comes from the
> evidence: the call the task ended on names the entity and the verb, and the query
> parameter every call carried names the facility. Same rule as parameter naming --
> the captured traffic already uses the vocabulary of the system being automated.

## module, [line 17](../../../../../../../backend/src/sro/application/capture/identity.py#L17): Note on the line above

Code: `_ROUTING_SEGMENTS = frozenset(`

> Segments that say how the server is wired, not what the task acted on.

## module, [line 28](../../../../../../../backend/src/sro/application/capture/identity.py#L28): Note on the line above

Code: `_UNKNOWN_FACILITY = "default"`

> Used when no call named one. A wrong guess would split one task into two
> objectives that never pair, so the honest answer is a single stated placeholder.

## module, [line 107](../../../../../../../backend/src/sro/application/capture/identity.py#L107): Note on the line above

Code: `_LABEL_LIMIT = 40`

> Longest text treated as a control's name. A button says "Clients"; the
> paragraph explaining what a client is says every warehouse noun there is, and
> letting that vote would name the task after whatever the operator read.

## `derive_objective_key`, [line 31](../../../../../../../backend/src/sro/application/capture/identity.py#L31): Docstring

> The key this demonstration earned, or ``None`` if it asked the server nothing.
>
> ``system`` comes from the connection the operator taught through; without one
> the host is used, which is at least stable per deployment.

## `system_named`, [line 66](../../../../../../../backend/src/sro/application/capture/identity.py#L66): Docstring

> What to call the system this URL belongs to.
>
> The connection's own label where somebody has connected it, and a label made
> from the host where nobody has. Both are what `target_system` holds, which
> is what matters: a system name and a hostname sitting side by side in the
> same field is how a circuit breaker ends up protecting a system that does
> not exist.

## `systems_touched`, [line 70](../../../../../../../backend/src/sro/application/capture/identity.py#L70): Docstring

> Every system these demonstrations touched, in the vocabulary the breaker
> speaks.
>
> Connection labels rather than hostnames, because `target_system` is a label
> and the breaker compares those strings -- a list of hosts beside a key of
> labels would refuse a run for a system nobody has ever heard of, or worse,
> fail to.
>
> A host nobody has connected still counts: it is a system this version
> touches whether or not this deployment holds a credential for it, which is
> exactly the case a run in somebody's own browser exists for.
>
> Two systems are never merged into one name. A derived name is the host's
> last meaningful label, so an unconnected `sap.acme.com` derives `acme` --
> which is also what somebody called their Blue Yonder connection. Merging
> them makes the version look like a single-system skill: no second breaker,
> no browser required, and every credential keyed to the first system
> resolved and sent to the second. Where that would happen the derived name
> keeps its host instead, which names nothing else and matches nothing else,
> and is the truth about a system nobody has connected.

## `system_of`, [line 91](../../../../../../../backend/src/sro/application/capture/identity.py#L91): Docstring

> The system name the operator gave when they connected this host.
>
> Preferred over anything read off the URL: `blue_yonder` is what the skill,
> the vault scope and the knowledge base all call it, and the hostname
> (`bf56-kms-wms-web-np2.jdadelivers.com`) is not.

## `host_of`, [line 103](../../../../../../../backend/src/sro/application/capture/identity.py#L103): Docstring

> The hostname of a URL, or "" when it has none.

## `_screen_words`, [line 110](../../../../../../../backend/src/sro/application/capture/identity.py#L110): Docstring

> What the operator's own gestures named, as entity words.
>
> Only labels: the accessible name a control reports, or its visible text.

## `_entity_of`, [line 123](../../../../../../../backend/src/sro/application/capture/identity.py#L123): Docstring

> The entity this call is about, by the same rule the key uses.

## `_calls`, [line 128](../../../../../../../backend/src/sro/application/capture/identity.py#L128): Docstring

> Every call the demonstration made, in order.
>
> Not one per step: a single Save can create a record and then address it, and
> reading only the step's "primary" call named the task after the second of
> those -- an update of an address, for a task that creates a supplier.

## `_is_record_id`, [line 145](../../../../../../../backend/src/sro/application/capture/identity.py#L145): Docstring

> A record's id names the record, never the task.

## `derive_objective_key`, [line 41](../../../../../../../backend/src/sro/application/capture/identity.py#L41): Comment

Code: `mutations = [call for call in calls if call.is_mutation]`

> The write is what the task is about; the reads around it are how the
> operator got there and how they checked afterwards. Where one gesture
> wrote twice -- Save creating a supplier and setting its address -- the
> creation names the task, because that is what the operator would call it
> and what nobody else can do by editing an existing record.

## `derive_objective_key`, [line 44](../../../../../../../backend/src/sro/application/capture/identity.py#L44): Comment

Code: `named = _screen_words(frames)`

> Where one Save wrote several records, the last one is not the task. A
> client creation posts an address, then the client, then its warehouse
> link, then a packing configuration -- and taking the last named that
> demonstration `create packing_configuration`, which is a child row of the
> thing the operator actually did. The screen says which: they were on
> Clients, and clicked a control that says so. That is evidence in the
> recording, not an inference about what they meant.

## `systems_touched`, [line 85](../../../../../../../backend/src/sro/application/capture/identity.py#L85): Comment

Code: `chosen = label or (host if derived in connected else derived)`

> Two hosts deriving one name is ordinary -- a portal and its API are
> one system -- and they merge. Colliding with a name somebody actually
> connected is not: those are two systems, and the derived one takes
> its host rather than the other's identity.
