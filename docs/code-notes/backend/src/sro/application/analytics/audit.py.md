# Notes for `backend/src/sro/application/analytics/audit.py`

Comments and docstrings moved out of [`backend/src/sro/application/analytics/audit.py`](../../../../../../../backend/src/sro/application/analytics/audit.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/analytics/audit.py#L1): Docstring

> Everything a person would want to see after the fact, since a time.
>
> The runs with each step's verdict and what was sent, when a person approved a
> write, every offer's fate, which browsers could act and until when, and what
> the chat door cost. Four reads plan 2 gave the repositories, one tenant, one
> bound, each list newest first.
>
> Nothing here computes. The summary beside it derives numbers; this hands back
> rows somebody can open, because an audit that summarised would be answering a
> question other than the one it was asked. The only work it does is turn one
> instant into the one string all four reads compare against -- which is the
> whole of what a "since" is, and the reason it is a use case rather than four
> calls a route makes in a row.
>
> Ported from the rig's ``GET /v1/audit``. Two of that route's rules are
> deliberately not here: its ``limit`` is a page size and belongs to whoever
> serves a page, and the repository reads plan 2 landed take no limit; and its
> device select had no tenant filter at all, so one tenant's audit listed every
> tenant's browsers -- a leak rather than a rule, already fixed in
> ``SqlDeviceRepository.since`` and not travelling here.
>
> Nor does its ``since: str = ""``, which meant "everything ever". ``since`` is a
> ``datetime`` and required: an audit of all time is a table scan nobody asked
> for, and a caller that wants one can say when the deployment started.

## module, [line 14](../../../../../../../backend/src/sro/application/analytics/audit.py#L14): Note on the line above

Code: `K_ATTEMPTS = 500`

> How many attempts one audit carries.
>
> Five hundred is a heavy day for one tenant and a page a person can scroll.
> The other four reads are bounded by what the system itself produced; this one
> is bounded by how much somebody pressed, which has no ceiling.

## `AuditedRun`, [line 20](../../../../../../../backend/src/sro/application/analytics/audit.py#L20): Note on the line above

Code: `approvals: tuple[tuple[int, str, str | None], ...]`

> (step ord, when, which browser) for each write a person let out.
>
> Beside the run rather than folded into its steps: a ``RunStep`` is what the
> runner writes and an approval is what a person did, and a record that
> carried both could be saved back with somebody's approval in it.

## `Audit`, [line 25](../../../../../../../backend/src/sro/application/analytics/audit.py#L25): Note on the line above

Code: `since: str`

> The bound the four reads actually used, normalised -- not the argument.
>
> Handed back because a reader has to be able to tell which instant they got:
> a caller that passed a naive time is told, in UTC, what that was taken to
> mean.

## `Audit`, [line 32](../../../../../../../backend/src/sro/application/analytics/audit.py#L32): Note on the line above

Code: `attempts: tuple[Attempt, ...] = ()`

> What somebody asked for, including the times nothing came of it.
>
> The other four are STATE: a run because a run was created, an offer
> because an offer was made. They are a good account of everything that
> worked, and they are silent about the press that started nothing -- which
> is the half a person opens an audit to find. See
> `sro.domain.observation.attempts`.
>
> Last, and defaulted, because it is the newest of the five and a reader
> written against the other four still reads.

## `_bound`, [line 61](../../../../../../../backend/src/sro/application/analytics/audit.py#L61): Docstring

> One instant, in UTC, as all four reads compare it.
>
> A naive ``since`` is read as UTC and never as the server's local time --
> ``sro.infrastructure.db.codec.when``'s rule on the other edge, and the
> rig's on this one. A bound quietly shifted by the host's offset does not
> fail; it returns an audit that starts hours from where it was asked to,
> and looks exactly like one that does not.

## `ReadAudit.execute`, [line 43](../../../../../../../backend/src/sro/application/analytics/audit.py#L43): Comment

Code: `audited = [`

> ``approvals`` is tenant-blind, and is only safe asked this way:
> every run id here came out of a tenant-scoped read a line above,
> so nothing crosses that boundary by asking with an id a caller
> supplied.

## `ReadAudit.execute`, [line 50](../../../../../../../backend/src/sro/application/analytics/audit.py#L50): Comment

Code: `attempts = await uow.attempts.since(ctx.tenant_id, since=since, limit=K_ATTEMPTS)`

> Capped where the others are not, because this one grows with
> what people DO rather than with what the system made: a busy day
> of somebody pressing things is thousands of rows, and an audit
> is read by a person.
