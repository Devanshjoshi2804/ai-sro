# Notes for `backend/src/sro/application/observation/mine_pass.py`

Comments and docstrings moved out of [`backend/src/sro/application/observation/mine_pass.py`](../../../../../../../backend/src/sro/application/observation/mine_pass.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../../../backend/src/sro/application/observation/mine_pass.py#L1): Docstring

> One mining pass, asked for from outside the process.
>
> `mining_pass.mine` had no caller in `src/` at all: every mining result this
> project has measured came from a script somebody ran by hand. This is the seam
> a route can reach it through.

## `MinePass`, [line 17](../../../../../../../backend/src/sro/application/observation/mine_pass.py#L17): Docstring

> Read this tenant's day, once, and bill it.
>
> A class where ``mine`` is a bare function, for the reason
> ``container.record_offer`` is one: ``mine`` takes a bare ``tenant_id``, and
> a route calling it would unpack the caller itself at the one seam where
> passing the wrong tenant is the failure. ``now`` is taken from the
> container's clock here for the same reason ``Container.read_spend`` takes
> it there -- which day is being billed is not a decision a route may make.
>
> Both refusals happen here rather than inside ``mine``. ``mine`` takes an
> ``Asker`` and cannot be given ``None``; and its own cap check
> (``mining_pass.py:296``) returns a ``MineResult`` carrying the reason,
> which is right for a pass that got as far as trying and wrong for a request
> that should never have been admitted -- a caller hammering the door would
> get 200s describing its own refusals. Raised here, the door answers 503 and
> 429, which is what those two facts are.

## `MinePass.execute`, [line 36](../../../../../../../backend/src/sro/application/observation/mine_pass.py#L36): Comment

Code: `asker = asker_or_refuse(self._asker)`

> Before the session is opened and long before a window is packed:
> neither refusal needs a database, and a 503 that first took a
> connection is a 503 that made the outage slightly worse.

## `MinePass.execute`, [line 38](../../../../../../../backend/src/sro/application/observation/mine_pass.py#L38): Comment

Code: `async with self._uow as uow:`

> One session, entered here. `mine`'s docstring: "`uow` is already
> open: the pass commits its own writes and never enters or leaves the
> block, so the caller owns the session." A second unit of work for
> the cap check would be a repository read off a `SqlUnitOfWork`
> nobody entered, which is `50864cf` -- green in every unit test and
> an AttributeError against real Postgres.
