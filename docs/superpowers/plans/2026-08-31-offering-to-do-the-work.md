# Offering To Do The Work Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the panel's "teach it" offer with one that offers to do the operator's next piece of work, shows what it made, and lets them take it back.

**Architecture:** Almost all of this is wiring rather than building. `ResolveIntent`, `TeachCandidate`, `ExecuteSkill` bound to the operator's browser, the promotion ladder and the in-page band all exist. Three things are genuinely new: a run can be marked wrong by a person, a version records that it was promoted from a preview, and the panel gains a sentence box. Everything else reads machinery that is already there for a purpose it was not being read for.

**Tech Stack:** Python 3.14 / FastAPI / SQLAlchemy async / Alembic on the backend; plain ES modules in an MV3 Chrome extension for the panel; no framework and no build step on the extension side.

**Spec:** `docs/superpowers/specs/2026-08-31-offering-to-do-the-work-design.md`

## Global Constraints

- The word "teach" never appears in text an operator reads. Neither does a raw signature (`POST data/WM/wm/workOperations`), an endpoint path, or a candidate id.
- Nothing above `PromotionStage.ASSISTED` is reachable from a panel press. `REQUIRED_CLEAN_RUNS = 10` and `DEMOTE_AFTER_FAILURES = 3` are untouched.
- Undo is offered on three facts or not at all: the run's mutating call is a `POST` to a resource shape, a runnable skill in the tenant's library `DELETE`s that same shape, and the run derived the identifier that skill needs.
- The operator is never asked to demonstrate anything. Every path uses what was already watched.
- Only the principal a run was performed for may mark it wrong.
- Hexagonal import rules hold: `domain` imports nothing from `application`; `application` imports no `infrastructure`; `infrastructure` is reached only through `container.py`. `make lint` runs import-linter and it will fail the build.
- Every new test is proved by reverting the rule it defends before the task is committed. This is the repo's habit and reviewers check for it.
- Extension code must pass `make lint-extension` (`no-undef`) — `node --check` is not enough and has already shipped a `ReferenceError` this way.

---

### Task 1: A person can call a finished run wrong

**Files:**
- Modify: `backend/src/sro/domain/execution/run.py` (add a field to `Run`, near `failure` at :291)
- Modify: `backend/src/sro/domain/execution/verdict.py:30-43` (`judge`)
- Test: `backend/tests/unit/domain/test_a_run_the_operator_called_wrong.py` (create)

**Interfaces:**
- Produces: `Run.wrong_because: str | None = None`, and `judge(run) -> Verdict` returning `Verdict.FAILED` whenever `run.wrong_because` is set.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/domain/test_a_run_the_operator_called_wrong.py`:

```python
"""A run whose steps were perfect and whose result was wrong.

`judge` reads statuses, media and escalations. Every one of them can be clean
while the record the run created is not the one anybody wanted -- a work
operation with the priority off by a digit is a successful run and a wrong
answer. That is the one failure the ladder cannot see, and the only witness is
the person whose browser it ran in.
"""

from __future__ import annotations

from dataclasses import replace

from sro.domain.execution.verdict import judge
from sro.domain.skill.track_record import Verdict
from tests import factories


def _clean_run():
    """A run that `judge` calls CLEAN: succeeded, every step a network call."""
    run = factories.run(status=factories.RunStatus.SUCCEEDED)
    run.record(factories.step_outcome(index=0))
    return run


def test_a_run_the_operator_called_wrong_is_a_failure_however_clean_its_steps() -> None:
    run = _clean_run()
    assert judge(run) is Verdict.CLEAN

    run.called_wrong("undone by the operator")

    assert judge(run) is Verdict.FAILED


def test_a_run_nobody_touched_is_judged_exactly_as_before() -> None:
    """Silence is not a verdict. Nothing is asked after a run, so nothing goes
    unanswered, and a run the operator ignored must not drift downwards for it."""
    assert judge(_clean_run()) is Verdict.CLEAN


def test_the_reason_is_kept_because_undone_and_mistyped_are_different_things() -> None:
    run = _clean_run()
    run.called_wrong("wrong priority")
    assert run.wrong_because == "wrong priority"


def test_a_run_cannot_be_called_wrong_twice_with_a_different_story() -> None:
    """The first answer is the one the operator gave while they were looking at
    it. A second, later, is somebody rewriting the record."""
    from pytest import raises

    from sro.domain.shared.errors import InvariantViolation

    run = _clean_run()
    run.called_wrong("undone by the operator")
    with raises(InvariantViolation, match="already"):
        run.called_wrong("actually it was fine")
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd backend && uv run pytest tests/unit/domain/test_a_run_the_operator_called_wrong.py -v`
Expected: FAIL — `Run` has no attribute `called_wrong`.

If `factories.run`, `factories.step_outcome` or `factories.RunStatus` do not exist under those names, read `backend/tests/factories.py` and use what is there rather than adding new factories; the point of the test is `judge`, not the builders.

- [ ] **Step 3: Add the field and the method**

In `backend/src/sro/domain/execution/run.py`, beside `failure: str | None = None`:

```python
    wrong_because: str | None = None
    """Why the person this ran for said the result was wrong.

    `judge` reads statuses, media and escalations, and every one of them can be
    clean while the record the run created is not the one anybody wanted. That
    is the failure the ladder cannot see on its own, and the only witness is
    whoever was looking at the screen.

    Collected as an undo they wanted rather than as a question they answered:
    the press that takes the record back is the same press that says it was
    wrong, so being honest costs them nothing.
    """
```

And a method on `Run`:

```python
    def called_wrong(self, because: str) -> None:
        """The person this ran for says the result was wrong.

        Once. The first answer is the one they gave while looking at what it
        made; a second one later is somebody rewriting the record, and the
        track record has already been told.
        """
        if self.wrong_because is not None:
            raise InvariantViolation(
                f"this run was already called wrong: {self.wrong_because!r}"
            )
        if not because.strip():
            raise InvariantViolation("a run called wrong says why, even if only 'undone'")
        self.wrong_because = because
```

In `backend/src/sro/domain/execution/verdict.py`, as the first branch of `judge`:

```python
def judge(run: Run) -> Verdict:
    # Before anything the steps say. A run can be clean at every rung and still
    # have made the wrong record, and the person who was looking at it is the
    # only one who could ever know.
    if run.wrong_because is not None:
        return Verdict.FAILED
    if run.status is not RunStatus.SUCCEEDED:
```

- [ ] **Step 4: Run the tests**

Run: `cd backend && uv run pytest tests/unit/domain/test_a_run_the_operator_called_wrong.py -v`
Expected: PASS, 4 tests.

Then the whole unit suite, because `Run` is constructed in many places:
Run: `cd backend && uv run pytest tests/unit tests/contract -q`
Expected: PASS.

- [ ] **Step 5: Prove the test by reverting the rule**

Comment out the two-line `wrong_because` branch in `judge`, run the new test file, and confirm `test_a_run_the_operator_called_wrong_is_a_failure_however_clean_its_steps` fails. Put it back. This is the repo's habit and a reviewer will ask.

- [ ] **Step 6: Commit**

```bash
cd backend && uv run ruff format src tests && uv run ruff check src tests && uv run mypy src
git add backend/src/sro/domain/execution/run.py backend/src/sro/domain/execution/verdict.py backend/tests/unit/domain/test_a_run_the_operator_called_wrong.py
git commit -m "feat(execution): a person can call a finished run wrong

judge() reads statuses, media and escalations, and every one of them can be
clean while the record the run created is not the one anybody wanted. A work
operation saved with the priority off by a digit is a successful run and a
wrong answer, and the ladder cannot see it: the only witness is whoever was
looking at the screen.

Once, and with a reason. The first answer is the one they gave while looking at
what it made; a second later is somebody rewriting a record the track record has
already been told about."
```

---

### Task 2: The run row remembers it, and the endpoint sets it

**Files:**
- Modify: `backend/src/sro/infrastructure/db/models.py:182` (`RunRow`, beside `failure`)
- Modify: `backend/src/sro/infrastructure/db/mappers.py` (both directions for `RunRow`)
- Create: `backend/migrations/versions/20260831_0032_a_run_called_wrong.py`
- Create: `backend/src/sro/application/execution/call_run_wrong.py`
- Modify: `backend/src/sro/container.py` (a factory beside the other execution use cases)
- Modify: `backend/src/sro/interface/http/v1/routers/runs.py` (a new route after `stop_run` at :86)
- Modify: `backend/src/sro/interface/http/schemas.py` (`CalledWrongRequest`, and `wrong_because` on `RunModel`)
- Test: `backend/tests/unit/application/test_calling_a_run_wrong.py` (create)

**Interfaces:**
- Consumes: `Run.called_wrong(because: str) -> None` and `Run.wrong_because` from Task 1.
- Produces: `CallRunWrong.execute(ctx, *, run_id: RunId, because: str) -> Run`, and `POST /v1/runs/{run_id}/wrong` taking `{"because": str}`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/application/test_calling_a_run_wrong.py`:

```python
"""Who may say a run came out wrong, and what saying so does.

A run drives one operator's browser and they are the only person who saw what it
produced. Anybody else in the tenant is guessing, and a guess in a track record
is worse than a silence -- it demotes a skill on the strength of somebody's
impression of a screen they were not looking at.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.execution.call_run_wrong import CallRunWrong, NotYours
from sro.domain.execution.run import RunId
from sro.domain.skill.track_record import Verdict
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeUnitOfWork

OPERATOR = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


async def _a_finished_run(uow: FakeUnitOfWork):
    run = f.run(status=f.RunStatus.SUCCEEDED, requested_by=f.OPERATOR)
    run.record(f.step_outcome(index=0))
    async with uow as open_uow:
        await open_uow.runs.add(run)
        await open_uow.commit()
    return run


async def test_saying_it_was_wrong_counts_against_the_skill() -> None:
    uow, clock = FakeUnitOfWork(), FakeClock(f.at(900))
    run = await _a_finished_run(uow)
    skill = f.skill()
    async with uow as open_uow:
        await open_uow.skills.add(skill)
        await open_uow.commit()

    await CallRunWrong(uow, clock).execute(
        OPERATOR, run_id=run.id, because="undone by the operator"
    )

    async with uow as open_uow:
        again = await open_uow.runs.get(f.TENANT, run.id)
        assert again.wrong_because == "undone by the operator"


async def test_somebody_else_cannot_call_your_run_wrong() -> None:
    """They did not see it. A guess in the track record is worse than a silence."""
    uow, clock = FakeUnitOfWork(), FakeClock(f.at(900))
    run = await _a_finished_run(uow)
    somebody_else = RequestContext(tenant_id=f.TENANT, principal_id=f.PrincipalId("nobody"))

    with pytest.raises(NotYours):
        await CallRunWrong(uow, clock).execute(
            somebody_else, run_id=run.id, because="looked wrong to me"
        )


async def test_a_run_still_going_cannot_be_called_wrong_yet() -> None:
    """There is no result to judge. Stopping a run is a different button and it
    already exists."""
    uow, clock = FakeUnitOfWork(), FakeClock(f.at(900))
    running = f.run(requested_by=f.OPERATOR)
    async with uow as open_uow:
        await open_uow.runs.add(running)
        await open_uow.commit()

    with pytest.raises(NotYours, match="still going"):
        await CallRunWrong(uow, clock).execute(
            OPERATOR, run_id=running.id, because="undone by the operator"
        )
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd backend && uv run pytest tests/unit/application/test_calling_a_run_wrong.py -v`
Expected: FAIL — no module `sro.application.execution.call_run_wrong`.

Read `backend/tests/unit/fakes.py` for the real `FakeUnitOfWork` repository names before writing the use case; use the ones that are there.

- [ ] **Step 3: Write the use case**

Create `backend/src/sro/application/execution/call_run_wrong.py`:

```python
"""The person a run was performed for says its result was wrong.

Not a survey. This is reached by an operator pressing "undo that" or "it's
wrong, I'll fix it", both of which are things they wanted anyway -- which is why
the answer can be trusted. A question they answer to help us is a question they
stop answering.

The skill hears about it the same way it hears about a crash, because the
distinction it cares about is "did this still work", and a run that made the
wrong record did not.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.execution.run import Run, RunId, RunStatus
from sro.domain.execution.verdict import judge


class NotYours(Exception):
    """This is not a run this caller may pass judgement on."""


class CallRunWrong:
    def __init__(self, uow: UnitOfWork, clock: Clock) -> None:
        self._uow = uow
        self._clock = clock

    async def execute(self, ctx: RequestContext, *, run_id: RunId, because: str) -> Run:
        async with self._uow as uow:
            run = await uow.runs.get(ctx.tenant_id, run_id)
            if run.requested_by != ctx.principal_id:
                # A run drives one operator's browser and they are the only
                # person who saw what it produced.
                raise NotYours("only the person this ran for can say how it came out")
            if run.status is RunStatus.RUNNING:
                raise NotYours("this run is still going; stopping it is a different thing")

            run.called_wrong(because)
            await uow.runs.save(run)

            skill = await uow.skills.get(ctx.tenant_id, run.skill_id)
            skill.record(run.skill_version, judge(run), self._clock.now())
            await uow.skills.save(skill)
            await uow.commit()
        return run
```

If `Skill.record` has a different arity, read `backend/src/sro/domain/skill/skill.py:324` and call it the way `ExecuteSkill` does — that call site is the definition of how a verdict reaches a track record and there must not be a second opinion about it.

- [ ] **Step 4: Run the tests**

Run: `cd backend && uv run pytest tests/unit/application/test_calling_a_run_wrong.py -v`
Expected: PASS, 3 tests.

- [ ] **Step 5: Persist it**

In `backend/src/sro/infrastructure/db/models.py`, beside `failure`:

```python
    wrong_because: Mapped[str | None] = mapped_column(Text)
```

Add both directions in `backend/src/sro/infrastructure/db/mappers.py` wherever `failure` is carried.

Create `backend/migrations/versions/20260831_0032_a_run_called_wrong.py`:

```python
"""A run the person it ran for said was wrong

Revision ID: 0032
Revises: 0031
Create Date: 2026-08-31

`judge` reads statuses, media and escalations, and every one of them can be
clean while the record the run created is not the one anybody wanted. This is
where the only witness gets to say so.

Nullable, and null means nobody said anything -- which is the ordinary case and
is not a verdict. Nothing is asked after a run, so nothing goes unanswered.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("wrong_because", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("runs", "wrong_because")
```

Copy the exact `revision` / `down_revision` module-level names from `backend/migrations/versions/20260831_0031_confirmations.py` — match that file rather than this snippet if they differ.

Run: `cd backend && make -C .. migrate && uv run pytest tests/integration -q`
Expected: the migration applies and a run's `wrong_because` round-trips.

- [ ] **Step 6: Wire the endpoint**

In `backend/src/sro/interface/http/schemas.py`:

```python
class CalledWrongRequest(BaseModel):
    because: str = Field(min_length=1, max_length=500)
    """Why it was wrong. "undone by the operator" where they pressed undo, or
    what they typed. Kept because "I took it back" and "the priority was wrong"
    are different things to read a month later."""
```

Add `wrong_because: str | None = None` to `RunModel` and to its `of(...)`.

In `backend/src/sro/interface/http/v1/routers/runs.py`, after `stop_run`:

```python
@router.post("/runs/{run_id}/wrong", status_code=status.HTTP_202_ACCEPTED)
async def called_wrong(
    run_id: str, body: CalledWrongRequest, container: ContainerDep, ctx: ContextDep
) -> RunModel:
    """The person this ran for says the result was wrong.

    Reached by pressing "undo that" or "it's wrong, I'll fix it" -- things they
    wanted anyway, which is why the answer can be trusted. It counts against the
    skill exactly as a crash does, because the question the ladder is asking is
    "does this still work", and a run that made the wrong record did not.
    """
    run = await container.call_run_wrong().execute(
        ctx, run_id=RunId(run_id), because=body.because
    )
    return RunModel.of(run)
```

Map `NotYours` in `backend/src/sro/interface/http/errors.py` to 403, beside the other domain errors. Add `call_run_wrong()` to `container.py` next to the other execution use cases.

- [ ] **Step 7: Gate and commit**

```bash
cd backend && uv run ruff format src tests && uv run ruff check src tests && uv run mypy src && uv run lint-imports && uv run pytest tests/unit tests/contract -q
cd .. && make types
git add backend/src backend/tests backend/migrations frontend/openapi.json frontend/src/lib/api/generated.ts
git commit -m "feat(execution): an operator can say a run came out wrong

Only the person it ran for: a run drives one operator's browser and they are the
only one who saw what it produced. Anybody else is guessing, and a guess in a
track record is worse than a silence -- it demotes a skill on somebody's
impression of a screen they were not looking at.

Not asked as a question. This is reached by pressing undo, or by saying they
will fix it themselves, both of which they wanted anyway. A question answered to
help us is a question that stops being answered."
```

---

### Task 3: Whether an undo exists, and what it would remove

**Files:**
- Create: `backend/src/sro/application/execution/reversal.py`
- Modify: `backend/src/sro/interface/http/v1/routers/runs.py` (extend the existing `GET /runs/{run_id}`)
- Modify: `backend/src/sro/interface/http/schemas.py` (`ReversalModel`, `RunModel.reversal`)
- Test: `backend/tests/unit/application/test_taking_back_what_a_run_made.py` (create)

**Interfaces:**
- Consumes: `url_shape(url: str) -> str` from `sro.application.induction.diff`.
- Produces: `reversal_for(run: Run, skills: Sequence[Skill]) -> Reversal | None`, where `Reversal` is a frozen dataclass `(skill_id: SkillId, parameters: dict[str, str])`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/application/test_taking_back_what_a_run_made.py`:

```python
"""Whether the panel may offer to take back what a run just made.

A visible undo is the strongest trust mechanism an agentic surface has, because
trust is knowing you can recover. It is also the one place this design could
most easily start guessing, so it does not: three facts or no button.
"""

from __future__ import annotations

from sro.application.execution.reversal import reversal_for
from tests import factories as f


def _run_that_created(identifier: str | None):
    """A run whose write was POST /api/workOperations, having read back an id."""
    run = f.run(status=f.RunStatus.SUCCEEDED)
    run.record(
        f.step_outcome(
            index=0, method="POST", url="https://wms.test/api/workOperations"
        )
    )
    if identifier is not None:
        run.learn("operation_id", identifier)
    return run


def _deletes(path: str):
    """A runnable skill whose only step is a DELETE on that path."""
    return f.skill(
        versions=1,
        steps=(
            f.step(
                index=0,
                network_plan=f.NetworkPlan(
                    method="DELETE",
                    url=f.Template(path),
                    expected_status=204,
                ),
            ),
        ),
        parameters=(f.parameter(name="operation_id"),),
        stage=f.PromotionStage.ASSISTED,
    )


def test_an_undo_is_offered_when_all_three_facts_hold() -> None:
    found = reversal_for(
        _run_that_created("NDPCK"),
        [_deletes("https://wms.test/api/workOperations/$operation_id")],
    )

    assert found is not None
    assert found.parameters == {"operation_id": "NDPCK"}


def test_nothing_is_offered_when_the_run_never_learned_what_it_made() -> None:
    """A button that cannot name what it would remove is worse than no button."""
    assert (
        reversal_for(
            _run_that_created(None),
            [_deletes("https://wms.test/api/workOperations/$operation_id")],
        )
        is None
    )


def test_a_delete_on_another_resource_is_not_an_undo() -> None:
    """Shapes are compared, not words. `workAreas` is not `workOperations`, and
    a model's opinion that they look similar is exactly what this refuses."""
    assert (
        reversal_for(
            _run_that_created("NDPCK"),
            [_deletes("https://wms.test/api/workAreas/$operation_id")],
        )
        is None
    )


def test_a_skill_that_may_not_run_is_not_an_undo() -> None:
    """Offering it would put a button in front of somebody that the executor
    then refuses, which teaches them the panel lies."""
    recorded = _deletes("https://wms.test/api/workOperations/$operation_id")
    recorded.versions[-1].stage = f.PromotionStage.RECORDED

    assert reversal_for(_run_that_created("NDPCK"), [recorded]) is None


def test_a_run_that_only_read_has_nothing_to_take_back() -> None:
    run = f.run(status=f.RunStatus.SUCCEEDED)
    run.record(f.step_outcome(index=0, method="GET", url="https://wms.test/api/workOperations"))

    assert reversal_for(run, [_deletes("https://wms.test/api/workOperations/$operation_id")]) is None
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd backend && uv run pytest tests/unit/application/test_taking_back_what_a_run_made.py -v`
Expected: FAIL — no module `sro.application.execution.reversal`.

Read `backend/tests/factories.py` first; use the builders that exist rather than inventing `f.NetworkPlan`/`f.Template`/`f.PromotionStage` aliases if the file imports those directly instead.

- [ ] **Step 3: Write it**

Create `backend/src/sro/application/execution/reversal.py`:

```python
"""Whether what a run made can be taken back, and by which skill.

A visible undo is the strongest thing an agentic surface has, because trust is
knowing you can recover from a mistake. It is also where this design could most
easily begin guessing, so it does not: an undo is offered on three facts or not
at all.

  - the run's write was a POST to some resource shape, and
  - a runnable skill in this tenant's library DELETEs that same shape, and
  - the run read back the identifier that skill needs.

`url_shape` answers the middle one and is the same function induction uses to
decide two calls are the same call. Nothing here is proposed as a reverse
because it looked like one.

Most tasks will have no undo for a long time, because nobody demonstrates
deleting things. That is honest: the fallback is the operator fixing it while we
watch, which is what they were going to do anyway.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from sro.application.induction.diff import url_shape
from sro.domain.execution.run import Run
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.skill import Skill


@dataclass(frozen=True, slots=True)
class Reversal:
    skill_id: SkillId
    parameters: dict[str, str]


def reversal_for(run: Run, skills: Sequence[Skill]) -> Reversal | None:
    made = _what_it_made(run)
    if made is None:
        return None

    for skill in skills:
        version = skill.runnable
        if version is None:
            continue
        for step in version.steps:
            plan = step.network_plan
            if plan is None or plan.method.upper() != "DELETE":
                continue
            # The collection the delete acts on, which is the created resource's
            # shape with the identifier segment taken off the end.
            if _collection(url_shape(plan.url.raw)) != made:
                continue
            wanted = {p.name for p in version.inputs}
            if not wanted or not wanted <= run.derived.keys():
                # It needs something this run never read back. A button that
                # cannot name what it would remove is worse than no button.
                continue
            return Reversal(
                skill_id=skill.id,
                parameters={name: run.derived[name] for name in wanted},
            )
    return None


def _what_it_made(run: Run) -> str | None:
    """The shape of the one resource this run created, if it created one."""
    posts = [
        step
        for step in run.steps
        if step.method and step.method.upper() == "POST" and step.url
    ]
    if len(posts) != 1:
        # Nothing written, or several things. A run that made two records is not
        # one this can offer to unmake with a single press.
        return None
    return url_shape(posts[0].url or "")


def _collection(shape: str) -> str:
    """`api/workOperations/*` is a delete on `api/workOperations`."""
    return shape[: -len("/*")] if shape.endswith("/*") else shape
```

- [ ] **Step 4: Run the tests**

Run: `cd backend && uv run pytest tests/unit/application/test_taking_back_what_a_run_made.py -v`
Expected: PASS, 5 tests.

- [ ] **Step 5: Put it on the run's own read**

In `backend/src/sro/interface/http/schemas.py`:

```python
class ReversalModel(BaseModel):
    """What would take back what this run made, where anything would."""

    skill_id: str
    parameters: dict[str, str]
```

Add `reversal: ReversalModel | None = None` to `RunModel`. The router computes it where it reads a finished run, loading the tenant's skills through the existing repository.

- [ ] **Step 6: Prove the tests by reverting the rules**

Take out the `wanted <= run.derived.keys()` check and confirm `test_nothing_is_offered_when_the_run_never_learned_what_it_made` fails. Put it back. Take out the `version is None: continue` and confirm `test_a_skill_that_may_not_run_is_not_an_undo` fails. Put it back.

- [ ] **Step 7: Gate and commit**

```bash
cd backend && uv run ruff format src tests && uv run ruff check src tests && uv run mypy src && uv run lint-imports && uv run pytest tests/unit tests/contract -q
cd .. && make types
git add backend/src backend/tests frontend/openapi.json frontend/src/lib/api/generated.ts
git commit -m "feat(execution): whether what a run made can be taken back

A visible undo is the strongest thing an agentic surface has, because trust is
knowing you can recover. It is also where this could most easily start guessing,
so it does not: three facts or no button. The run POSTed to a resource shape, a
runnable skill DELETEs that same shape, and the run read back the identifier
that skill needs.

url_shape answers the middle one, and it is the same function induction uses to
decide two calls are the same call -- a second opinion here would offer an undo
that induction would refuse to align.

Most tasks will have no undo for a long time, because nobody demonstrates
deleting things. The fallback is the operator fixing it while we watch, which is
what they were going to do anyway."
```

---

### Task 4: A version records that a preview was its review

**Files:**
- Modify: `backend/src/sro/domain/skill/skill.py:361` (`SkillVersion.promote`)
- Modify: `backend/src/sro/application/skill/promote_skill.py`
- Modify: `backend/src/sro/interface/http/schemas.py` (`PromoteRequest`, `SkillVersionModel`)
- Create: `docs/07-adr/014-a-preview-an-operator-read-is-a-review.md`
- Test: `backend/tests/unit/domain/test_a_preview_is_a_review.py` (create)

**Interfaces:**
- Produces: `SkillVersion.promoted_from: str = ""` and `promote(..., from_where: str = "")`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/domain/test_a_preview_is_a_review.py`:

```python
"""Why a panel press may promote a version, and how far.

`_check_runnable` refuses a RECORDED version because "a recorded skill has not
been reviewed by anybody". After the preview it has been: by the operator, on
the exact steps and the exact values, at the screen it will act on, with a stop
button in front of them. That is a real reading of the rule and not a way around
it -- but a reviewer in the console has to be able to tell it apart from
somebody sitting down with the evidence, and disagree.
"""

from __future__ import annotations

import pytest

from sro.domain.shared.errors import InvariantViolation
from sro.domain.skill.promotion import PromotionStage
from tests import factories as f


def test_a_promotion_says_where_its_review_happened() -> None:
    version = f.skill_version(stage=PromotionStage.RECORDED)

    version.promote(PromotionStage.SHADOW, f.at(100), f.OPERATOR, from_where="preview")

    assert version.promoted_from == "preview"
    assert version.promoted_by == f.OPERATOR


def test_a_promotion_from_the_console_says_so_too() -> None:
    """Not a flag that only the new path sets. A blank would mean "old row" and
    "somebody reviewed this properly" at once, which is the kind of field nobody
    can read back."""
    version = f.skill_version(stage=PromotionStage.RECORDED)

    version.promote(PromotionStage.SHADOW, f.at(100), f.OPERATOR, from_where="console")

    assert version.promoted_from == "console"


def test_a_preview_cannot_reach_past_assisted() -> None:
    """The whole argument is that the operator read what it would do. Nobody
    reads what ten future unattended runs will do."""
    version = f.skill_version(stage=PromotionStage.ASSISTED)

    with pytest.raises(InvariantViolation, match="preview"):
        version.promote(
            PromotionStage.AUTONOMOUS, f.at(100), f.OPERATOR, from_where="preview"
        )
```

- [ ] **Step 2: Run it and watch it fail**

Run: `cd backend && uv run pytest tests/unit/domain/test_a_preview_is_a_review.py -v`
Expected: FAIL — `promote()` takes no `from_where`.

- [ ] **Step 3: Implement**

Add to `SkillVersion`, beside `promoted_by`:

```python
    promoted_from: str = ""
    """Where the review that promoted this version happened.

    `"console"` is somebody sitting down with the evidence. `"preview"` is an
    operator reading the steps and the values in the panel and pressing once,
    at the screen, with a stop button in front of them.

    Both are reviews and the second is a real reading of what the ladder asks
    for -- but they are not the same review, and somebody auditing a library has
    to be able to tell them apart and disagree with one of them.
    """
```

In `promote`, take `from_where: str = ""` as a keyword-only argument, and before anything else:

```python
        if from_where == "preview" and to.rung > PromotionStage.ASSISTED.rung:
            # The argument for a preview being a review is that the operator
            # read what this run would do. Nobody reads what ten future
            # unattended runs will do.
            raise InvariantViolation(
                "a preview promotes no further than assisted; "
                f"{to} is earned by clean runs, not by a press"
            )
```

then set `self.promoted_from = from_where` where `promoted_by` is set.

- [ ] **Step 4: Run the tests**

Run: `cd backend && uv run pytest tests/unit tests/contract -q`
Expected: PASS. Existing `promote` callers pass no `from_where` and keep working; update the console's use case to pass `from_where="console"`.

- [ ] **Step 5: Write the ADR**

Create `docs/07-adr/014-a-preview-an-operator-read-is-a-review.md` covering: the rule as it stood; what the preview shows and under what conditions; why the press is a review (the operator is at the screen, saw the steps and the values, and can stop it); what it deliberately does not reach and why; and how a reviewer tells the two apart. Follow the shape of `docs/07-adr/012-a-page-the-operator-said-yes-to.md`.

- [ ] **Step 6: Prove the test and commit**

Remove the `from_where == "preview"` guard, confirm `test_a_preview_cannot_reach_past_assisted` fails, put it back.

```bash
cd backend && uv run ruff format src tests && uv run ruff check src tests && uv run mypy src && uv run pytest tests/unit tests/contract -q
cd .. && make types
git add backend/src backend/tests docs/07-adr frontend/openapi.json frontend/src/lib/api/generated.ts
git commit -m "feat(skill): a version records where its review happened

_check_runnable refuses a RECORDED version because nobody has reviewed it. After
the panel's preview somebody has: the operator, on the exact steps and the exact
values, at the screen it will act on, with a stop button in front of them.

That is a real reading of the rule rather than a way around it, and it is
written down as one -- promoted_from tells a reviewer which kind of review
happened so they can disagree with either. A preview reaches assisted and no
further: the argument is that they read what this run would do, and nobody reads
what ten future unattended runs will do."
```

---

### Task 5: The press promotes and runs, in one call

**Files:**
- Create: `backend/src/sro/application/execution/run_from_preview.py`
- Modify: `backend/src/sro/container.py`
- Modify: `backend/src/sro/interface/http/v1/routers/runs.py`
- Test: `backend/tests/unit/application/test_running_what_the_operator_previewed.py` (create)

**Interfaces:**
- Consumes: `SkillVersion.promote(to, at, by, *, from_where: str = "")` from Task 4.
- Produces: `RunFromPreview.execute(ctx, *, skill_id, parameters, device_id, intent) -> Run`, and `POST /v1/skills/{skill_id}/runs/from-preview`.

Task 4 gave a version somewhere to record that a preview was its review. Nothing calls it. Without this task the panel's press reaches `_check_runnable`, which refuses a `RECORDED` version, and the whole offer dead-ends on the first press of every newly induced skill.

One call rather than promote-then-run from the panel: two calls race, and a version promoted by a press that then failed to start is a version sitting at assisted because somebody clicked once and walked away.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/unit/application/test_running_what_the_operator_previewed.py`:

```python
"""The press that runs a skill for the first time.

`_check_runnable` refuses a RECORDED version because nobody has reviewed it.
After the preview somebody has -- so this promotes and runs in one call, because
two calls race and a version promoted by a press that then failed to start is a
version at assisted because somebody clicked once and walked away.
"""

from __future__ import annotations

import pytest

from sro.application.context import RequestContext
from sro.application.execution.run_from_preview import RunFromPreview
from sro.domain.skill.promotion import PromotionStage
from tests import factories as f

OPERATOR = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


async def test_the_press_promotes_a_recorded_version_and_runs_it() -> None:
    uow = f.uow_with(skill=f.skill(stage=PromotionStage.RECORDED))
    ...
    assert version.stage is PromotionStage.ASSISTED
    assert version.promoted_from == "preview"
    assert version.promoted_by == f.OPERATOR


async def test_a_version_already_running_is_not_promoted_again() -> None:
    """A press on the fifth run is not a fifth promotion. Only a version that
    cannot run yet is moved, and only as far as it needs to go."""
    ...
    assert version.stage is PromotionStage.ASSISTED
    assert version.promoted_at == before


async def test_the_press_never_reaches_past_assisted() -> None:
    """Even pressed on an assisted version with ten clean runs behind it. The
    rungs above are earned by runs, not by presses."""
    ...
    assert version.stage is PromotionStage.ASSISTED


async def test_the_sentence_they_typed_is_on_the_run() -> None:
    """`Run.intent` is the audit answer to "why did this happen". A run started
    from a sentence records the sentence; there is no second store for it."""
    ...
    assert run.intent == "create work operation NDPCK, north dock picking"
```

Fill the `...` from the way `backend/tests/unit/application/test_execute_skill.py` (or whichever file exercises `ExecuteSkill`) builds a uow, a skill and a device. Do not invent factory helpers: use the ones that file uses, so a reviewer reads one setup and not two.

- [ ] **Step 2: Run it and watch it fail**

Run: `cd backend && uv run pytest tests/unit/application/test_running_what_the_operator_previewed.py -v`
Expected: FAIL — no module `sro.application.execution.run_from_preview`.

- [ ] **Step 3: Write it**

```python
"""Run a skill an operator has just read the preview of.

`_check_runnable` refuses a RECORDED version because "a recorded skill has not
been reviewed by anybody". After the preview it has been: by the operator, on
the exact steps and the exact values, at the screen it will act on, with a stop
button in front of them. ADR 014 makes that argument in full.

Promote and run in one call. Two calls race, and a version promoted by a press
that then failed to start is a version sitting at assisted because somebody
clicked once and walked away.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.ports.repositories import UnitOfWork
from sro.application.ports.system import Clock
from sro.domain.execution.run import Run
from sro.domain.shared.identifiers import DeviceId, SkillId
from sro.domain.skill.promotion import PromotionStage


class RunFromPreview:
    def __init__(self, uow: UnitOfWork, clock: Clock, execute_skill: object) -> None:
        self._uow = uow
        self._clock = clock
        self._execute = execute_skill

    async def execute(
        self,
        ctx: RequestContext,
        *,
        skill_id: SkillId,
        parameters: dict[str, str],
        device_id: DeviceId,
        intent: str,
    ) -> Run:
        async with self._uow as uow:
            skill = await uow.skills.get(ctx.tenant_id, skill_id)
            version = skill.versions[-1]
            # Only a version that cannot run yet, and only as far as it needs to
            # go. A press on the fifth run is not a fifth promotion, and the
            # rungs above assisted are earned by runs rather than by presses.
            if version.stage.rung < PromotionStage.ASSISTED.rung:
                version.promote(
                    PromotionStage.ASSISTED,
                    self._clock.now(),
                    ctx.principal_id,
                    from_where="preview",
                )
                await uow.skills.save(skill)
                await uow.commit()

        return await self._execute.execute(
            ctx,
            skill_id=skill_id,
            parameters=parameters,
            device_id=device_id,
            authorized_by=str(ctx.principal_id),
            intent=intent,
        )
```

Match `ExecuteSkill.execute`'s real keyword names by reading `backend/src/sro/application/execution/execute_skill.py`; the shape above is the intent, not the signature. Type `execute_skill` properly rather than as `object` — use whatever the container passes.

- [ ] **Step 4: Run the tests**

Run: `cd backend && uv run pytest tests/unit tests/contract -q`
Expected: PASS.

- [ ] **Step 5: Wire the endpoint and prove the rule**

Add `POST /v1/skills/{skill_id}/runs/from-preview` beside `run_skill`, and `run_from_preview()` to the container.

Prove: remove the `version.stage.rung < ASSISTED.rung` guard and confirm `test_a_version_already_running_is_not_promoted_again` fails. Restore.

- [ ] **Step 6: Commit**

```bash
cd backend && uv run ruff format src tests && uv run ruff check src tests && uv run mypy src && uv run lint-imports && uv run pytest tests/unit tests/contract -q
cd .. && make types
git add backend/src backend/tests frontend/openapi.json frontend/src/lib/api/generated.ts
git commit -m "feat(execution): the press an operator previewed promotes and runs

Task 4 gave a version somewhere to record that a preview was its review, and
nothing called it. Without this the panel's press reaches _check_runnable, which
refuses a RECORDED version, and the offer dead-ends on the first press of every
skill it ever induces.

One call, not promote-then-run from a panel: two calls race, and a version
promoted by a press that then failed to start is a version sitting at assisted
because somebody clicked once and walked away.

Only a version that cannot run yet, and only as far as it needs to go. A press
on the fifth run is not a fifth promotion, and the rungs above assisted are
earned by runs."
```

---

### Task 6: The panel offers to do the work

**Files:**
- Modify: `new-chrome-extension/src/panel/panel.js:681-720` (`row`)
- Modify: `new-chrome-extension/src/background/service-worker.js` (message kinds `resolve-intent`, `run-skill`, `run-wrong`)
- Modify: `new-chrome-extension/src/background/api.js` (the three calls)
- Test: `new-chrome-extension/src/panel/panel.test.mjs` (extend)

**Interfaces:**
- Consumes: `POST /v1/intent/resolve`, `POST /v1/candidates/{id}/teach`, `POST /v1/skills/{id}/runs`, `POST /v1/runs/{id}/wrong`, and `RunModel.reversal` from Task 3.
- Produces: `plainly(candidate) -> string`, exported from `panel.js` for its test.

- [ ] **Step 1: Write the failing test**

Append to `new-chrome-extension/src/panel/panel.test.mjs`, **above** the `for (const [name, fn] of tests)` loop — tests added below it are registered and never run, which has already happened once in this file:

```javascript
test("the offer is about their work, not about our system", async () => {
  // What it said before: "Create workOperations on bf56-kms-wms-web-np2
  // .jdadelivers.com / Seen 3 times / [Teach it] [Not worth it]". The title is
  // an API endpoint, the count is telemetry about the person reading it, and
  // both buttons ask them to work for us or to judge us. Nobody presses that.
  const { cards } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
    {
      candidates: [
        {
          id: "cnd-1",
          title: "Create workOperations on wms.example",
          signature: "POST data/WM/wm/workOperations",
          status: "new",
          times_seen: 3,
          median_duration_ms: 40000,
          minutes_so_far: 5,
          episodes: [],
          joins: [],
        },
      ],
    },
  );

  const said = cards.map(words).join(" ");
  assert.ok(/work operations/i.test(said), `no plain noun in: ${said.slice(0, 200)}`);
  assert.ok(/do the next one/i.test(said), "it never offers to do anything");
  assert.ok(!/teach/i.test(said), "the panel still asks to be taught");
  assert.ok(!/workOperations/.test(said), "an endpoint name reached the operator");
  assert.ok(!/seen 3 times/i.test(said), "telemetry about the operator is still shown");
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `node new-chrome-extension/src/panel/panel.test.mjs`
Expected: FAIL — "the panel still asks to be taught".

The harness must render candidates. If `panel(status, here, replies)` does not yet pass `replies.candidates` through the `candidates` message, extend the stub the same way the `deaf` tests extended it.

- [ ] **Step 3: Replace `row`**

In `panel.js`, add above `row`:

```javascript
/** The task, in the words somebody working would use.
 *
 * A model writes one where the deployment has one and the propose pass has run.
 * Where it has not, the noun comes off the signature's own path -- so this never
 * depends on a model being configured, and an operator is never shown
 * `POST data/WM/wm/workOperations`.
 */
export function plainly(candidate) {
  if (candidate.named_by_model && candidate.title) return candidate.title;
  const path = (candidate.signature || "").split(" ")[1] || "";
  const noun = path.split("/").filter(Boolean).pop() || "task";
  // `workOperations` is two words to everybody except a URL.
  const words = noun.replace(/([a-z0-9])([A-Z])/g, "$1 $2").toLowerCase();
  return words.endsWith("s") ? words : `${words}s`;
}
```

and rewrite `row` to render:

```javascript
  const said = document.createElement("p");
  said.className = "title";
  // A reason, not a statistic. "Seen 3 times" is telemetry about the person
  // reading it; "you've created 3 of these" is why we are asking.
  said.textContent =
    `You've created ${candidate.times_seen} ${plainly(candidate)} here — ` +
    `about ${Math.round(candidate.median_duration_ms / 1000)}s each.`;

  const offer = document.createElement("button");
  offer.type = "button";
  offer.textContent = "Do the next one";
  offer.addEventListener("click", () => beginOffer(candidate, item));

  const no = document.createElement("button");
  no.type = "button";
  no.className = "quiet";
  no.textContent = "No thanks";
```

`No thanks` keeps the existing dismiss call. `beginOffer` is Task 7; for this task it may be a stub that renders the input box and nothing else, so the test above passes on its own.

- [ ] **Step 4: Run the tests**

Run: `node new-chrome-extension/src/panel/panel.test.mjs`
Expected: PASS.
Run: `make test-extension && make lint-extension`
Expected: both clean.

- [ ] **Step 5: Prove the test**

Put `Teach it` back as the button label, confirm the test fails on "the panel still asks to be taught", then restore.

- [ ] **Step 6: Commit**

```bash
git add new-chrome-extension/src/panel/panel.js new-chrome-extension/src/panel/panel.test.mjs
git commit -m "feat(panel): offer to do the work, instead of asking to be taught

What it said: 'Create workOperations on bf56-kms-wms-web-np2.jdadelivers.com /
Seen 3 times / [Teach it] [Not worth it]'. The title is an API endpoint, the
count is telemetry about the person reading it, and both buttons ask them either
to work for us or to pass judgement on us. Nobody presses that.

What it says now is why we are asking and what we are offering. The noun comes
off the signature's own path where no model has named the task, so the offer
never depends on one being configured and a raw signature never reaches an
operator."
```

---

### Task 7: The sentence, the preview, and the press

**Files:**
- Modify: `new-chrome-extension/src/panel/panel.js` (`beginOffer`, `preview`, `runIt`)
- Modify: `new-chrome-extension/src/background/service-worker.js`, `api.js`
- Test: `new-chrome-extension/src/panel/panel.test.mjs` (extend)

**Interfaces:**
- Consumes: `plainly` from Task 6; `promoted_from` from Task 4.
- Produces: `previewOf(resolution, version) -> {steps: [{intent, value}], missing: [string]}`, exported for its test.

- [ ] **Step 1: Write the failing test**

Append above the runner loop in `panel.test.mjs`:

```javascript
test("the preview shrinks as the version earns it", async () => {
  // Requiring approval for every action an agent takes defeats the point of
  // automating it. The rungs already say when a version has earned the benefit
  // of the doubt; until now nothing read them for this.
  const { previewOf } = await import("./panel.js");
  const steps = [
    { intent: "Type the Operation code.", value: "NDPCK" },
    { intent: "Press Save.", value: null },
  ];

  const first = previewOf({ stage: "recorded", clean_streak: 0 }, steps);
  assert.equal(first.show, "every-step", "a first press hid what it would do");

  const trusted = previewOf({ stage: "assisted", clean_streak: 4 }, steps);
  assert.equal(trusted.show, "one-line", "a version with a streak still asked in full");

  const earned = previewOf({ stage: "autonomous", clean_streak: 10 }, steps);
  assert.equal(earned.show, "nothing", "an autonomous version still asked first");
});

test("what it could not work out, it asks for by the screen's own name", async () => {
  const { previewOf } = await import("./panel.js");

  const asked = previewOf({ stage: "recorded", clean_streak: 0 }, [
    { intent: "Type the Operation code.", value: "NDPCK" },
    { intent: "Enter the Voice Code.", value: null, missing: "voice_code", label: "Voice Code" },
  ]);

  assert.deepEqual(asked.missing, ["Voice Code"]);
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `node new-chrome-extension/src/panel/panel.test.mjs`
Expected: FAIL — `previewOf` is not exported.

- [ ] **Step 3: Implement**

```javascript
/** How much to show before running, and what still needs asking.
 *
 * Tied to the rung, not to the press. A preview on every press forever is the
 * thing that makes people stop reading previews -- and the ladder already says
 * when a version has earned the benefit of the doubt, on evidence rather than
 * on somebody's patience. This is not a preference: an operator cannot switch it
 * off, because it is the version that earned it and not them.
 */
export function previewOf(version, steps) {
  const missing = steps.filter((step) => step.missing).map((step) => step.label || step.missing);
  const show =
    version.stage === "autonomous"
      ? "nothing"
      : version.stage === "recorded" || !version.clean_streak
        ? "every-step"
        : "one-line";
  return { show, steps, missing };
}
```

Then `beginOffer(candidate, item)`:

1. `ask({kind: "teach-candidate", id: candidate.id})` — the operator never sees the word. On refusal render *"I've watched this 3 times but the doings differ too much for me to be sure — do one more and I'll try again."* and stop.
2. Render an input. On submit, `ask({kind: "resolve-intent", utterance, skillId})`.
3. Render by `previewOf(...).show`: every step and value; or one line and `Do it`; or run immediately.
4. `Do it` → `ask({kind: "run-skill", skillId, parameters, deviceId})`.

- [ ] **Step 4: The same box runs anything, not only what was offered**

Spec §6. A sentence that names no offered task still resolves, across the whole library, and the offer turns out to be a pre-filled message into the same input. This is mostly the absence of a restriction — `ResolveIntent` already ranks every skill and refuses when two are close — so what needs writing is the refusal's rendering, not a new path.

Add above the runner loop in `panel.test.mjs`:

```javascript
test("a sentence naming no offered task still runs the task it names", async () => {
  const { cards, sent } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
      asking: true,
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
    { "resolve-intent": { matched: { skill_id: "skl-9", name: "Create a work area" } } },
  );

  assert.ok(
    sent.some((m) => m.kind === "resolve-intent" && !m.skillId),
    "the box only ever asks about the offered skill",
  );
});

test("a sentence it is unsure about is not resolved by picking the top match", async () => {
  // ResolveIntent already refuses. What must not happen is the panel taking the
  // first of several and running it -- a warehouse write on a coin toss.
  const { cards } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
      asking: true,
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
    {
      "resolve-intent": {
        matched: null,
        between: [
          { skill_id: "skl-1", name: "Create a work area" },
          { skill_id: "skl-2", name: "Create a work operation" },
        ],
      },
    },
  );

  const said = cards.map(words).join(" ");
  assert.ok(/Create a work area/.test(said) && /Create a work operation/.test(said));
  assert.ok(/which/i.test(said), "it did not ask which one was meant");
});
```

Then send `resolve-intent` with no `skillId` so it ranks the whole library, and render `Resolution.between` as a list of buttons when nothing matched. Where `Resolution` names those fields differently, read `backend/src/sro/application/intent/resolve.py` and use the wire names `ResolutionModel` actually carries.

- [ ] **Step 5: Run the tests, prove them, commit**

Run: `node new-chrome-extension/src/panel/panel.test.mjs && make test-extension && make lint-extension`

Prove: make `show` always `"every-step"` and confirm the shrink test fails; restore. Then make the ambiguous branch pick `between[0]` and confirm the second new test fails; restore.

```bash
git add new-chrome-extension/src
git commit -m "feat(panel): a sentence, a preview that shrinks, and one press

Requiring approval for every action an agent takes defeats the point of
automating it, and the ladder already says when a version has earned the benefit
of the doubt -- on its track record rather than on somebody's patience. Until
now nothing read the rungs for this.

Every step and value on a first press, one line once the streak is going,
nothing at all at autonomous. Not a preference an operator can switch off: the
version earned it, not them."
```

---

### Task 8: What it made, and taking it back

**Files:**
- Modify: `new-chrome-extension/src/panel/panel.js` (a card for the last finished run)
- Test: `new-chrome-extension/src/panel/panel.test.mjs` (extend)

**Interfaces:**
- Consumes: `RunModel.reversal` and `RunModel.derived` from Task 3; `POST /v1/runs/{id}/wrong` from Task 2.

- [ ] **Step 1: Write the failing test**

```javascript
test("it shows what it made and offers to take it back", async () => {
  const { cards } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
      finished: {
        id: "run-1",
        status: "succeeded",
        derived: { operation: "NDPCK", description: "north dock picking" },
        reversal: { skill_id: "skl-2", parameters: { operation_id: "NDPCK" } },
      },
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
  );

  const said = cards.map(words).join(" ");
  assert.ok(/NDPCK/.test(said), "it did not show what it made");
  assert.ok(/Undo that/i.test(said), "no undo was offered when one exists");
  assert.ok(!/come out right/i.test(said), "it is still asking a survey question");
});

test("with no way to reverse it, it says so rather than offering a dead button", async () => {
  const { cards } = panel(
    {
      deviceId: "dev-1",
      capturing: true,
      watched: [{ tabId: 7, host: "wms.example", since: new Date().toISOString() }],
      finished: { id: "run-1", status: "succeeded", derived: { operation: "NDPCK" }, reversal: null },
    },
    { id: 7, host: "wms.example", url: "https://wms.example/portal" },
  );

  const said = cards.map(words).join(" ");
  assert.ok(!/Undo that/i.test(said), "an undo was offered with nothing behind it");
  assert.ok(/I'll fix it/i.test(said), "no way to say it was wrong at all");
});
```

- [ ] **Step 2: Run it and watch it fail**

Run: `node new-chrome-extension/src/panel/panel.test.mjs`
Expected: FAIL — nothing renders the finished run.

- [ ] **Step 3: Implement the card**

```javascript
/** What the last run made, and how to take it back.
 *
 * It asks nothing. "Did that come out right?" is a survey and surveys go
 * unanswered; an undo is a thing they wanted, so pressing it costs them nothing
 * to be honest about -- which is exactly what makes it the better signal.
 *
 * Silence means it was fine. A run nobody touched is judged as it is today.
 */
function finished(status) {
  const run = status.finished;
  const made = Object.entries(run.derived || {});
  const actions = [];
  if (run.reversal) {
    actions.push({ label: "Undo that", primary: true, act: (b) => undoRun(b, run) });
  }
  actions.push({ label: "It's wrong — I'll fix it", act: (b) => wasWrong(b, run) });
  return card({
    title: made.length
      ? `Created ${made.map(([, value]) => value).join(" — ")}.`
      : "Finished. I can't show you what it made — nothing was read back.",
    actions,
  });
}
```

`undoRun` sends `run-wrong` with `because: "undone by the operator"` **and** starts the reversal skill. `wasWrong` sends `run-wrong` with their note and renders *"Fix it the way you meant. I'm watching, and I'll learn from that."*

- [ ] **Step 4: Run, prove, commit**

Prove: render `reversal: null` and confirm the first test fails on the missing undo; restore.

```bash
git add new-chrome-extension/src
git commit -m "feat(panel): show what it made, and offer to take it back

'Did that come out right? Yes / No' is a survey, and surveys go unanswered. An
undo is a thing the operator wanted anyway, so pressing it costs them nothing to
be honest about -- which is what makes it the better signal, not just the kinder
button.

It asks nothing, so nothing goes unanswered: silence means it was fine and a run
nobody touched is judged exactly as it is today. Where no reverse exists the
panel says so rather than offering a button with nothing behind it."
```

---

### Task 9: End to end in a real Chrome

**Files:**
- Test: `backend/tests/browser/test_offering_to_do_the_work.py` (create)

- [ ] **Step 1: Write the test**

Follow `backend/tests/browser/test_the_extension_in_a_real_chrome.py` for the fixtures (`browser`, `stub`, `_sign_in`, `_watch`, `_flush`). Drive: the stub serves three doings of one task; mine; open the panel; assert the offer says "do the next one" and never says "teach"; type a sentence; assert the preview lists the steps; press once; assert the stub received the write; assert the panel shows what was made and offers the undo.

- [ ] **Step 2: Run it**

Run: `cd backend && uv run pytest tests/browser/test_offering_to_do_the_work.py -q`
Expected: PASS.

- [ ] **Step 3: Whole suite and commit**

```bash
make check
git add backend/tests/browser/test_offering_to_do_the_work.py
git commit -m "test(browser): the offer, the sentence, the press and the undo

The pieces are tested apart; this is the only thing that proves they are wired
to each other, in a real Chrome, against a real write."
```
