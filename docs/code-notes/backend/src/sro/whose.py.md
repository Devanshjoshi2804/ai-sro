# Notes for `backend/src/sro/whose.py`

Comments and docstrings moved out of [`backend/src/sro/whose.py`](../../../../../backend/src/sro/whose.py). Each note names the code it explains (function or class, then the line in the current file) and keeps the original text, which says what the code does and why.

## module, [line 1](../../../../../backend/src/sro/whose.py#L1): Docstring

> Whose work a log line is about.
>
> A line this system writes says what happened and not who it happened to:
>
>     INFO sro.application.observation.mining_pass
>          Delete a Customer Type: refused -- unknown gesture (ges_60e165c1)
>
> Which tenant? Which operator? Was anybody waiting on it? On one deployment
> with one tenant a person can work that out from the clock. On a deployment
> with twenty, that line is unattributable, and the question somebody actually
> asks -- *this* operator pressed *that* button and nothing happened, what went
> wrong -- cannot be answered by reading anything at all.
>
> So every line carries who it belongs to, and no call site has to remember.
> `about()` puts ids on the current task; `Attribution` copies them onto every
> record the logging module builds, whichever of this system's fifty-three
> loggers wrote it; `sro.observability` renders them.
>
> **At the top of `sro`, beside `observability`, rather than in
> `infrastructure`.** Everything writes log lines -- a domain rule, a use case,
> a router, an adapter -- so a module every layer must import cannot live in the
> one layer the other three are forbidden to touch. It was in
> `infrastructure.telemetry` and seven modules across `application` and
> `interface` imported it by name, which is the architecture check going red for
> a reason that was true: the rule is right and the address was wrong.
>
> Nothing in here is an adapter. It is `contextvars` and the stdlib's own
> logging types, which is what makes this address honest as well as convenient:
> importing it binds a caller to nothing.
>
> **Context variables rather than an argument.** The alternative is a `ctx` on
> every logging call in the codebase, which is fifty-three modules of churn that
> the fifty-fourth will forget. A `ContextVar` follows the task through every
> await without being passed, which is exactly the shape of the thing being
> tracked: one request, one run, one pass, from the door to the last line it
> writes.
>
> **Ids only.** The same rule the tracing module already holds itself to, and
> for the same reason: this plane is the one that gets shipped to a collector
> somebody else operates. A tenant id, a run id, a thread id and a step number
> say who and where; a customer's name, a password, the body of a request and
> the text of a mail say what, and none of them belong here. Nothing in this
> module takes a value.

## module, [line 10](../../../../../backend/src/sro/whose.py#L10): Note on the line above

Code: `_WHOSE: ContextVar[dict[str, str | int] | None] = ContextVar("sro_whose", default=None)`

> None rather than an empty dict: a mutable default on a ContextVar is one
> object shared by every task that never set one, and the day something reaches
> in and mutates it in place, every request in the process is attributed to
> whoever did.

## module, [line 12](../../../../../backend/src/sro/whose.py#L12): Note on the line above

Code: `KNOWN = (`

> What a line may be attributed to, and the order a reader wants them in.
>
> Fixed rather than open: an attribution that can hold anything ends up holding
> a value somebody put there in a hurry, and this is the plane that leaves the
> building. A name outside this list is refused by `about` rather than dropped
> quietly, so the refusal lands on whoever added it and not on whoever reads the
> logs six months later.
>
> `command` is the one that spans both halves of this system: the backend mints
> it, the browser answers with it, and both say it -- so a step that failed can
> be read from the side that sent it and the side that refused it without
> guessing which of the two `ui.perform`s in that second is which.

## `whose`, [line 26](../../../../../backend/src/sro/whose.py#L26): Docstring

> Who the work on this task belongs to, as far as anything has said.

## `about`, [line 31](../../../../../backend/src/sro/whose.py#L31): Docstring

> Attribute every line written inside this block.
>
> Nests: a run inside a request keeps the request's tenant and adds its own
> run id, and leaving the block puts back exactly what was there before.
> `None` is not an attribution and is dropped, so a caller may pass an
> optional id without a conditional around it.

## `attribute`, [line 44](../../../../../backend/src/sro/whose.py#L44): Docstring

> Attribute the rest of this task, with no block to put it in.
>
> `about()` is the safer shape and the one to reach for. This exists for the
> two places where the work to be attributed is the whole remainder of a
> function too long to indent -- a run, a mining pass -- and it is sound
> there for a reason worth writing down: `asyncio` copies the context when a
> task is created, so a `set` inside one is invisible to its parent and to
> its siblings. A run driven by its own task cannot attribute anybody else's
> lines to itself.
>
> In plain synchronous code, or in a coroutine awaited directly by the caller
> rather than run as its own task, this DOES outlive the call. Use `about()`
> there.

## `Louder`, [line 52](../../../../../backend/src/sro/whose.py#L52): Docstring

> Let one tenant's lines through below the level everything else is at.
>
> A deployment that wants to see what happened to ONE customer had two
> choices, and both are bad: turn the whole process to DEBUG -- every tenant,
> every sweep, every query, for as long as it takes to reproduce -- or see
> nothing. On a single-tenant deployment the first is merely expensive; on a
> shared one it is a bill and a haystack.
>
> So the level is raised for a named few. `SRO_LOUDER_FOR=greyorange,acme`
> puts those tenants at DEBUG while the rest stay where they were, and the
> attribution is what makes it possible at all: the record already knows
> whose it is by the time a filter sees it.
>
> A filter can only widen what a LOGGER already let through, so the logger
> sits at the lower level and this holds everything else back. That is the
> one awkward half of doing it this way, and it is written here because the
> alternative -- a handler per tenant -- is a handler set that changes as
> tenants arrive.

## `Attribution`, [line 65](../../../../../backend/src/sro/whose.py#L65): Docstring

> Copies the current attribution onto every record.
>
> A filter rather than a `LoggerAdapter`: an adapter has to be held by the
> code that logs, and the point of this is that the code that logs says
> nothing. Returns True always -- it filters nothing and is only here because
> a filter is the hook that runs on every record.

## `Plainly`, [line 71](../../../../../backend/src/sro/whose.py#L71): Docstring

> For a person reading a terminal: the line, then who it was for.
>
> The message first and the ids after it, because somebody scanning a log is
> looking for what happened; the attribution is what they read once they have
> found it.

## `AsJson`, [line 80](../../../../../backend/src/sro/whose.py#L80): Docstring

> For anything that will be queried rather than read.
>
> One object per line, attribution at the top level rather than nested, so a
> collector can index `tenant` without knowing anything about this system.
