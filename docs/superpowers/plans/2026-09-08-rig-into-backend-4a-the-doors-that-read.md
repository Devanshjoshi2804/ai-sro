# The Rig Into The Backend, Phase 4a: The Doors That Read

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Put the rig's read-only HTTP surface on the backend's routers and the
backend's auth, and wire plans 3a and 3b's use cases into the composition root
so that something other than a test finally calls them.

**Architecture:** The rig authenticated with one bearer that was either the
tenant's or a device's, and its `caller`/`tenant_only` dependencies sorted the
two. The backend already separates those into a tenant credential that opens
every door and a per-browser secret that proves *which* browser — a stronger
rule that phase 4 adopts rather than replaces. Each rig route becomes a router
under `interface/http/v1/routers/`, keeping the rig's paths so the extension's
`api.js` changes only its base; the bodies come from use cases the earlier
plans already built and reviewed.

**Tech Stack:** FastAPI, pydantic v2 schemas in `interface/http/schemas.py`,
SQLAlchemy async over Postgres, pytest (unit / contract / integration),
import-linter, mypy strict, ruff.

**Spec:** `docs/superpowers/specs/2026-09-07-the-rig-into-the-backend-design.md`

**Predecessors:** plans 1, 2, 3a and 3b are merged. This plan is the first half
of the spec's phase 4; the write path — starting a workflow run, `awaiting`,
`approve`, `abort`, the stop route, `from_step` persistence, `fail_orphans` at
startup, `mine` and `chat` — is **phase 4b** and is deliberately not here. Split
for the same reason phase 3 was split: one reviewable plan does not carry ~250
tests.

## Global Constraints

- **A port that changes behaviour is two changes.** The rig
  (`new_agent_arch/src/rig/api.py`) is the source of truth for every route's
  shape and status codes. Any divergence is written into the code beside the
  line that diverges, with its reason — not only into a report.
- **Layering is linted.** `sro.domain` imports nothing of ours and holds no
  `typing.Any`, no pydantic, no bare generics. `sro.interface` must not import
  `sro.infrastructure`; the composition root (`sro/container.py`) is the only
  module allowed to. `uv run lint-imports` reports **4 kept, 0 broken**.
- **Authorisation.** The tenant's credential opens every door. A browser's
  secret opens ingest, its own socket, shapes for itself, the runs it drives,
  approve for those, and offers. The money routes and every cross-device read
  are tenant-only.
- **Absent, wrong, and belonging to somebody else are one 404** on every
  device-scoped path. A refusal must never distinguish them.
- **A refusal never echoes the values it refused.** A message that quotes a
  request body is a body in the access log.
- **The four test rules this project has paid for:**
  1. **Guard the caller, not only the rule.** Twenty-nine findings across eight
     tasks so far. Mutate each argument at each call site and report every one.
  2. **Any mutation touching set or dict ordering is re-run under several
     `PYTHONHASHSEED` values.**
  3. **Never date a fixture "today."**
  4. **Where a comment records a measurement or a decision that cost
     something, a test must fail when that thing changes.**
- **The seven gates**, measured as a delta against the task's starting commit:
  `uv run pytest tests/unit -q` · `uv run pytest tests/contract -q` (one
  pre-existing failure in `test_observation_payloads.py::…[shape-identity]` —
  do not fix it) · `uv run pytest tests/integration -q
  --ignore=tests/integration/test_steel_capture.py` · `uv run mypy src tests`
  · `uv run mypy src tests/unit/fakes.py` (clean) · `uv run ruff format --check
  .` (**2** pre-existing: `src/sro/infrastructure/mcp/client.py` **and**
  `tests/unit/application/test_teaching_two_candidates_as_one.py` — two
  different files) · `uv run lint-imports` (4 kept).
- **Baselines at the plan's base commit `a3ac456`:** unit **2180**, contract
  104 + 1 pre-existing failure, integration **112**, mypy **312 errors in 68
  files**.
- **Process:** `git stash` is forbidden in any form. Revert each mutation
  immediately after reading its result, and never revert with `git checkout --`
  while holding uncommitted work — commit the fix first, then mutate around it.
  Never delete, move, rename or stage an untracked file; stage only files you
  edited, by name.

---

## File Structure

**Created:**

| File | Responsibility |
|---|---|
| `src/sro/interface/http/asking.py` | One dependency: which browser is asking, if any. The rig's `caller` on the backend's two-factor model. |
| `src/sro/interface/http/v1/routers/shapes.py` | `GET /v1/shapes` |
| `src/sro/interface/http/v1/routers/devices.py` | `GET /v1/devices`, `POST /v1/devices/{id}/revoke`, `POST /v1/devices/{id}/restore` |
| `src/sro/interface/http/v1/routers/audit.py` | `GET /v1/audit` |
| `src/sro/interface/http/v1/routers/spend.py` | `GET /v1/spend` |
| `src/sro/interface/http/v1/routers/workflows.py` | `GET /v1/workflows`, `GET /v1/workflows/{id}/evidence` |
| `src/sro/interface/http/v1/routers/offers.py` | `POST /v1/offers` |
| `scripts/dry_run.py` | The offer replay's backend half, for `make offer-replay`. |

**Modified:** `src/sro/container.py` (factories for the phase-3 use cases),
`src/sro/interface/http/app.py` (router registration),
`src/sro/interface/http/schemas.py` (response models),
`src/sro/application/observation/register.py` (retire `ReadDevices`),
`src/sro/application/ports/repositories.py` and the Postgres/fake device
repositories (`restore`), `Makefile` (`offer-replay`).

**Task order.** Task 1 (the asking dependency) and Task 2 (container wiring)
come first because every router consumes both. Tasks 3–8 are one router each
and are mutually independent — they touch disjoint files apart from `app.py`
and `schemas.py`, which each task appends to. Task 9 needs Tasks 3 and 8.
Task 10 is the accounting and is last.

---

## Task 1: Which browser is asking

**Files:**
- Create: `src/sro/interface/http/asking.py`
- Test: `tests/unit/interface/test_asking.py`

**Interfaces:**
- Consumes: `ContainerDep`, `ContextDep`, `DeviceSecretDep` from
  `sro.interface.http.deps`; `container.read_device()` →
  `ReadDevice.execute(ctx, *, device_id: DeviceId, secret: str) -> AgentDevice`.
- Produces: `async def asking_device(container, ctx, x_device_secret, device_id) -> DeviceId | None`
  and the alias `AskingDeviceDep = Annotated[DeviceId | None, Depends(asking_device)]`.

**Why this exists.** The rig's `caller` answered "the tenant (None) or a
registered device (its id)" off one bearer. The backend cannot ask that
question the same way: its credential says which *tenant* and can never say
which *browser*, and the browser proves itself with a second header. So the
port of `caller` is not a credential check — it is "if this request also
carried a device secret that checks out, name that device; otherwise it is the
tenant asking."

- [ ] **Step 1: Write the failing tests**

```python
# tests/unit/interface/test_asking.py
"""Which browser is asking, on a model the rig did not have.

The rig's `caller` read one bearer and answered "tenant or this device". The
backend's credential names a tenant and never a browser, so the same question
is answered by the second header -- and a route that got this wrong would
serve one browser's rest to another, or let a tenant credential impersonate a
browser by naming it in a query string.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from sro.application.context import RequestContext
from sro.domain.shared.identifiers import DeviceId, PrincipalId, TenantId
from sro.interface.http.asking import asking_device


class _Devices:
    """A `read_device()` that accepts exactly one (id, secret) pair."""

    def __init__(self, device_id: str = "dev_1", secret: str = "shh") -> None:
        self._id, self._secret = device_id, secret
        self.asked: list[tuple[str, str]] = []

    def read_device(self) -> _Devices:
        return self

    async def execute(self, ctx: RequestContext, *, device_id: DeviceId, secret: str):
        self.asked.append((device_id.value, secret))
        from sro.application.observation.register import NotFound

        if device_id.value != self._id or secret != self._secret:
            raise NotFound(f"device {device_id.value} was not found")
        return object()


CTX = RequestContext(tenant_id=TenantId("acme"), principal_id=PrincipalId("you"))


async def test_no_secret_and_no_device_is_the_tenant_asking() -> None:
    container = _Devices()
    assert await asking_device(container, CTX, "", None) is None
    assert container.asked == [], "a request with no device asked the repository anyway"


async def test_a_browser_that_proves_itself_is_named() -> None:
    assert await asking_device(_Devices(), CTX, "shh", "dev_1") == DeviceId("dev_1")


async def test_the_secret_is_checked_against_the_device_that_was_named() -> None:
    # The seam: both arguments go to one call, and swapping them, or dropping
    # either, is how a browser gets served another browser's rest.
    container = _Devices()
    await asking_device(container, CTX, "shh", "dev_1")
    assert container.asked == [("dev_1", "shh")]


async def test_a_secret_for_another_browser_is_refused_not_downgraded() -> None:
    # Never silently "the tenant, then": a wrong secret is a request that
    # believed it was a browser, and answering it as the tenant would serve
    # every device's data to a browser that failed to prove it was one.
    with pytest.raises(HTTPException) as refused:
        await asking_device(_Devices(), CTX, "wrong", "dev_1")
    assert refused.value.status_code == 404


async def test_a_named_device_with_no_secret_is_refused() -> None:
    # A tenant credential naming a browser in a query string is not that
    # browser. Without this, `?device_id=` is an impersonation parameter.
    with pytest.raises(HTTPException) as refused:
        await asking_device(_Devices(), CTX, "", "dev_1")
    assert refused.value.status_code == 404


async def test_a_secret_with_no_device_named_is_refused() -> None:
    with pytest.raises(HTTPException) as refused:
        await asking_device(_Devices(), CTX, "shh", None)
    assert refused.value.status_code == 404
```

- [ ] **Step 2: Run and watch it fail**

Run: `uv run pytest tests/unit/interface/test_asking.py -q`
Expected: FAIL, `ModuleNotFoundError: No module named 'sro.interface.http.asking'`

- [ ] **Step 3: Write the module**

```python
# src/sro/interface/http/asking.py
"""Which browser is asking, if a browser is asking at all.

The rig's `caller` read one bearer and answered "the tenant (None) or this
device (its id)", because a device there held a token of its own. The backend
does not work that way and is not being changed to: its credential says which
tenant and can never say which browser, and a browser proves it is itself with
`X-Device-Secret` on top. So the port of `caller` is not a second credential
check -- it is "this request also carried a secret that checks out, so name the
browser it belongs to."

Declared divergence from `new_agent_arch/src/rig/api.py:405-419`: there, a
device bearer WAS a credential and a request could arrive as a device without
the tenant's token. Here both are always required, which is strictly stronger
and is the rule the rest of this codebase already keeps. Nothing downstream
notices: every route that cared only wanted the device's id.

Half a pair is a refusal, never a downgrade. A secret with no device named, or
a device named with no secret, is somebody reaching for a browser they cannot
prove they are -- answering that as "the tenant, then" would turn
`?device_id=` into an impersonation parameter.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Query, status

from sro.application.context import RequestContext
from sro.application.observation.register import NotFound
from sro.domain.shared.identifiers import DeviceId
from sro.interface.http.deps import ContainerDep, ContextDep, DeviceSecretDep


async def asking_device(
    container: ContainerDep,
    ctx: ContextDep,
    x_device_secret: DeviceSecretDep = "",
    device_id: Annotated[str | None, Query()] = None,
) -> DeviceId | None:
    """The browser this request proves it is, or ``None`` for the tenant.

    The 404 is the same one every device-scoped path gives: absent, wrong, and
    belonging to somebody else must not be told apart by a caller probing for
    which browsers exist.
    """
    if not device_id and not x_device_secret:
        return None
    if not device_id or not x_device_secret:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"device {device_id or ''} was not found",
        )
    named = DeviceId(device_id)
    try:
        await container.read_device().execute(ctx, device_id=named, secret=x_device_secret)
    except NotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return named


AskingDeviceDep = Annotated[DeviceId | None, Depends(asking_device)]
```

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/interface/test_asking.py -q`
Expected: 6 passed.

- [ ] **Step 5: Mutate, and report every result**

Run each, read the result, **revert it immediately**:

| Mutation | Must die |
|---|---|
| `if not device_id and not x_device_secret` → `if not device_id or not x_device_secret` | the tenant case, and the half-pair refusals |
| swap the two arguments at the `execute` call | `…the_secret_is_checked_against_the_device_that_was_named` |
| `secret=x_device_secret` → `secret=""` | the same |
| `except NotFound: return None` instead of raising | `…refused_not_downgraded` |
| `return named` → `return None` | `…a_browser_that_proves_itself_is_named` |

- [ ] **Step 6: Verify the gates and commit**

```bash
uv run pytest tests/unit -q && uv run mypy src tests | tail -1 && uv run lint-imports | tail -1
uv run ruff format --check src/sro/interface/http/asking.py tests/unit/interface/test_asking.py
```

Commit `src/sro/interface/http/asking.py` and `tests/unit/interface/test_asking.py`.

---

## Task 2: The composition root learns the phase-3 use cases

**Files:**
- Modify: `src/sro/container.py`
- Test: `tests/unit/test_container_wiring.py`

**Interfaces:**
- Produces, on `Container`:
  - `def read_roster(self) -> ReadRoster`
  - `def revoke_device(self) -> RevokeDevice`
  - `def read_audit(self) -> ReadAudit`
  - `async def shapes(self, tenant_id: TenantId, device_id: DeviceId | None) -> list[Shape]`
  - `async def record_offer(self, *, tenant_id, workflow_id, device_id, k, fate, run_id, at) -> Offer`

**Why this exists.** Plan 3b's Task 8 reported that nothing it built was wired
into `container.py`, because there was no route to wire it for and the file is
a collision point. There is a route now. `shapes_for` and `record_offer` are
module functions rather than classes, so the container owns supplying their
`now` from the injected clock — a route must never read a clock.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_container_wiring.py
"""The composition root hands out what the routers ask for.

Thin by design: what is worth holding is that each factory exists, returns the
type its router annotates, and is given the container's own clock and unit of
work rather than making its own. A use case built with a different clock is one
a test cannot move, and a route that reads a clock is a route with a rule in
it.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sro.application.analytics.audit import ReadAudit
from sro.application.capture.devices import ReadRoster, RevokeDevice
from sro.domain.shared.identifiers import DeviceId, TenantId
from tests.unit.fakes import build_test_container  # existing helper


def test_the_container_builds_the_phase_three_use_cases() -> None:
    container = build_test_container()
    assert isinstance(container.read_roster(), ReadRoster)
    assert isinstance(container.revoke_device(), RevokeDevice)
    assert isinstance(container.read_audit(), ReadAudit)


async def test_shapes_are_asked_with_the_containers_clock_not_a_fresh_one() -> None:
    # Fixed, and never "today": a shape's rest window is arithmetic on `now`,
    # so a container that read the wall clock here would make every rest test
    # depend on the day it ran.
    frozen = datetime(2026, 3, 4, 9, 30, tzinfo=UTC)
    container = build_test_container(now=frozen)
    served = await container.shapes(TenantId("acme"), DeviceId("dev_1"))
    assert served == []


async def test_the_asking_browser_reaches_shapes_for() -> None:
    # The caller seam: `device_id` decides whose refusals earned the rest, so
    # dropping it serves one browser the rest another browser earned.
    container = build_test_container(record_shape_calls=True)
    await container.shapes(TenantId("acme"), DeviceId("dev_7"))
    assert container.shape_calls == [(TenantId("acme"), DeviceId("dev_7"))]
```

- [ ] **Step 2: Run and watch it fail**

Run: `uv run pytest tests/unit/test_container_wiring.py -q`
Expected: FAIL, `AttributeError: 'Container' object has no attribute 'read_roster'`.

If `build_test_container` does not exist under that name, find the helper the
existing container tests use (`grep -rn "build_container\|Container(" tests/unit
| head`) and use it, adding the `now` / `record_shape_calls` hooks it needs.
**Report which helper you used in your report.**

- [ ] **Step 3: Add the factories**

Place these beside the existing use-case factories in `src/sro/container.py`,
after `read_summary`:

```python
    def read_roster(self) -> ReadRoster:
        return ReadRoster(self.unit_of_work(), self.agents)

    def revoke_device(self) -> RevokeDevice:
        return RevokeDevice(self.unit_of_work(), self.agents, self.clock)

    def read_audit(self) -> ReadAudit:
        return ReadAudit(self.unit_of_work())

    async def shapes(
        self, tenant_id: TenantId, device_id: DeviceId | None
    ) -> list[Shape]:
        """The extension's list, with this container's clock.

        A function rather than a class use case, so the `now` a route must not
        read is supplied here -- the one place that already holds a clock a
        test can move.
        """
        return await shapes_for(
            self.unit_of_work(),
            tenant_id=tenant_id,
            device_id=device_id,
            now=self.clock.now(),
        )

    async def record_offer(
        self,
        *,
        tenant_id: TenantId,
        workflow_id: str,
        device_id: DeviceId,
        k: int,
        fate: str,
        run_id: str | None,
        at: str,
    ) -> Offer:
        """Same reason as `shapes`: `record_offer` clamps the browser's reading
        against ours, and ours is this clock's."""
        return await record_offer(
            self.unit_of_work(),
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            device_id=device_id,
            k=k,
            fate=fate,
            run_id=run_id,
            at=at,
            now=self.clock.now(),
        )
```

Add the imports beside the existing application imports (alphabetical within
their group):

```python
from sro.application.analytics.audit import ReadAudit
from sro.application.capture.devices import ReadRoster, RevokeDevice
from sro.application.skill.record_offer import record_offer
from sro.application.skill.serve_shapes import shapes_for
from sro.domain.skill.offer import Offer
from sro.domain.skill.shape import Shape
```

**Check the attribute name for `AgentDrivers` on the container before you
write `self.agents`** — `grep -n "AgentDrivers" src/sro/container.py`. Use
whatever it is actually called and say so in your report.

- [ ] **Step 4: Run the tests**

Run: `uv run pytest tests/unit/test_container_wiring.py -q`
Expected: 3 passed.

- [ ] **Step 5: Mutate**

| Mutation | Must die |
|---|---|
| `device_id=device_id` → `device_id=None` in `shapes` | `…the_asking_browser_reaches_shapes_for` |
| `now=self.clock.now()` → `now=datetime.now(UTC)` in `shapes` | `…the_containers_clock_not_a_fresh_one` |
| `RevokeDevice(self.unit_of_work(), self.agents, self.clock)` → drop the clock argument | a `TypeError` at build |

- [ ] **Step 6: Gates and commit**

---

## Task 3: `GET /v1/shapes`

**Files:**
- Create: `src/sro/interface/http/v1/routers/shapes.py`
- Modify: `src/sro/interface/http/schemas.py`, `src/sro/interface/http/app.py`
- Test: `tests/unit/interface/test_shapes_route.py`

**Interfaces:**
- Consumes: `AskingDeviceDep` (Task 1), `container.shapes(...)` (Task 2).
- Produces: `ShapesResponse` in `schemas.py`.

**The rig:** `new_agent_arch/src/rig/api.py:1533-1546`. Two things carry over
and must be tested: the response is `{"shapes": [...]}` (not a bare list), and
**a browser holding a secret is named by the secret, whatever the query says** —
a rest is not something one browser reads off another.

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/interface/test_shapes_route.py
"""The list the extension matches a live tail against.

No model is on this path: arithmetic out and arithmetic in. What is worth
holding here is who the rest belongs to -- a workflow a browser refused three
times comes back quiet for that browser and for nobody else, so the identity
this route passes down is the whole of its behaviour.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.contract.conftest import client_for  # the suite's app-building helper


def test_the_shapes_of_the_asking_browser_are_served(app_client: TestClient) -> None:
    answered = app_client.get(
        "/v1/shapes",
        params={"device_id": "dev_1"},
        headers={"Authorization": "Bearer acme-token", "X-Device-Secret": "shh"},
    )
    assert answered.status_code == 200
    assert answered.json() == {"shapes": []}


def test_the_tenant_may_ask_without_naming_a_browser(app_client: TestClient) -> None:
    answered = app_client.get("/v1/shapes", headers={"Authorization": "Bearer acme-token"})
    assert answered.status_code == 200
    assert "shapes" in answered.json()


def test_a_browser_cannot_read_another_browsers_rest(app_client: TestClient) -> None:
    # The rig's rule, kept: the token names the browser, the query does not.
    # Here the secret is dev_1's and the query says dev_2, and the answer is a
    # 404 rather than dev_2's list.
    answered = app_client.get(
        "/v1/shapes",
        params={"device_id": "dev_2"},
        headers={"Authorization": "Bearer acme-token", "X-Device-Secret": "shh"},
    )
    assert answered.status_code == 404


def test_no_credential_is_refused_before_anything_is_read(app_client: TestClient) -> None:
    assert app_client.get("/v1/shapes").status_code == 401
```

- [ ] **Step 2: Run and watch it fail** — 404 on the route itself.

- [ ] **Step 3: Write the router**

```python
# src/sro/interface/http/v1/routers/shapes.py
"""What the extension matches a live tail against.

Ported from `new_agent_arch/src/rig/api.py:1533`. Arithmetic on the way out
and arithmetic on the way in: no model is on this path, which is why it can be
asked on every page an operator opens.

The asking browser is named by its secret and never by the query string --
`asking_device` refuses a mismatch rather than resolving it -- because the rest
a workflow earns is per browser: a job somebody refused three times comes back
quiet for them and for nobody else, and a browser that could name another's id
could read that.
"""

from __future__ import annotations

from fastapi import APIRouter

from sro.interface.http.asking import AskingDeviceDep
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import ShapesResponse

router = APIRouter(tags=["shapes"])


@router.get("/shapes")
async def shapes(
    container: ContainerDep,
    ctx: ContextDep,
    asking: AskingDeviceDep,
) -> ShapesResponse:
    served = await container.shapes(ctx.tenant_id, asking)
    return ShapesResponse(shapes=[shape.as_json() for shape in served])
```

In `schemas.py`, beside the other response models:

```python
class ShapesResponse(BaseModel):
    shapes: list[dict[str, object]]
    """The rig answered `{"shapes": [...]}` and the extension reads that key.
    An object rather than a bare list so a later field -- a server clock, a
    next-poll hint -- does not have to break the extension to be added."""
```

In `app.py`, beside the other registrations:

```python
    app.include_router(shapes.router, prefix="/v1", responses=PROBLEMS)
```

and add `shapes` to the router import block.

- [ ] **Step 4: Run the tests** — 4 passed.

- [ ] **Step 5: Mutate**

| Mutation | Must die |
|---|---|
| `container.shapes(ctx.tenant_id, asking)` → `(..., None)` | a test asserting the browser reaches the use case; if none does, **write one** |
| `ctx.tenant_id` → a literal `TenantId("acme")` | a two-tenant test; **write one if the suite has no fixture for it** |
| return a bare list instead of `ShapesResponse` | `…the_shapes_of_the_asking_browser_are_served` |

- [ ] **Step 6: Gates and commit**

---

## Task 4: `GET /v1/devices`, revoke, and restore

**Files:**
- Create: `src/sro/interface/http/v1/routers/devices.py`
- Modify: `src/sro/application/ports/repositories.py`,
  `src/sro/infrastructure/db/repositories.py`, `tests/unit/fakes.py`,
  `src/sro/application/capture/devices.py`,
  `src/sro/application/observation/register.py`,
  `src/sro/interface/http/v1/routers/agents.py`, `schemas.py`, `app.py`
- Test: `tests/unit/interface/test_devices_route.py`,
  `tests/unit/application/rig/test_devices.py` (extend)

**This task carries three of the five seams plan 3b left.**

1. **There is no un-revoke.** Now that revocation actually enforces
   (`refuse_unless_itself` refuses a revoked browser on all seven device-scoped
   paths), an administrator who revokes the wrong browser has no way back short
   of editing a row. `DeviceRepository` gets `restore`, and a `POST
   /v1/devices/{id}/restore` uses it.
2. **`ReadDevices` gives way to `ReadRoster`.** `ReadRoster` is a strict
   superset over the identical repository call. Point the existing wired route
   (`routers/agents.py:294-298`) at `ReadRoster`, add `online` to its response
   model, and delete `ReadDevices` from `register.py` and the container.
3. The rig's own `POST /v1/devices/{device_id}/revoke`
   (`api.py:988`), tenant-only.

**Interfaces:**
- Produces: `DeviceRepository.restore(tenant_id, device_id) -> bool`;
  `RestoreDevice` in `application/capture/devices.py`;
  `container.restore_device() -> RestoreDevice`; `RosterResponse` and
  `DeviceLineModel` in `schemas.py`.

- [ ] **Step 1: Write the failing tests for `restore` at the use-case level**

```python
# tests/unit/application/rig/test_devices.py  (append)

async def test_a_restored_browser_may_act_again() -> None:
    """The gap the enforcement opened.

    Before revocation enforced anything, an accidental revoke was cosmetic.
    Now it cuts the browser off on all seven device-scoped paths, so an
    administrator who pressed it on the wrong row has no way back -- and the
    row cannot simply be re-registered, because registration is deliberately
    idempotent and hands back the SAME secret, which would leave the browser
    revoked and the operator convinced they had fixed it.
    """
    uow, drivers, clock = _wired()
    await _register(uow, "dev_1")
    await RevokeDevice(uow, drivers, clock).execute(CTX, device_id=DeviceId("dev_1"))

    restored = await RestoreDevice(uow).execute(CTX, device_id=DeviceId("dev_1"))

    assert restored is True
    device = await _device(uow, "dev_1")
    assert device.revoked_at is None
    assert not device.revoked


async def test_restoring_a_browser_that_was_never_revoked_moves_nothing() -> None:
    # False rather than an error: the press is idempotent, and an administrator
    # pressing twice has not made a mistake worth an error page.
    uow, drivers, clock = _wired()
    await _register(uow, "dev_1")
    assert await RestoreDevice(uow).execute(CTX, device_id=DeviceId("dev_1")) is False


async def test_a_restore_does_not_open_a_socket_by_itself() -> None:
    # Revoking drops the socket; restoring must NOT dial one. The browser
    # reconnects on its own next heartbeat, and a backend that opened a channel
    # to a laptop nobody is sitting at is a channel nobody asked for.
    uow, drivers, clock = _wired()
    await _register(uow, "dev_1")
    await RevokeDevice(uow, drivers, clock).execute(CTX, device_id=DeviceId("dev_1"))
    drivers.dropped.clear()

    await RestoreDevice(uow).execute(CTX, device_id=DeviceId("dev_1"))

    assert drivers.dialled == [], "a restore opened a channel"


async def test_a_restored_browser_keeps_the_secret_it_had() -> None:
    # Deliberate, and the reason there is no "restore under a fresh secret":
    # this port already chose idempotent registration, so the extension still
    # holds the working secret and needs no reinstall.
    uow, drivers, clock = _wired()
    await _register(uow, "dev_1")
    before = (await _device(uow, "dev_1")).secret
    await RevokeDevice(uow, drivers, clock).execute(CTX, device_id=DeviceId("dev_1"))
    await RestoreDevice(uow).execute(CTX, device_id=DeviceId("dev_1"))
    assert (await _device(uow, "dev_1")).secret == before
```

Reuse this file's existing helpers (`_wired`, `_register`, `_device`, `CTX`).
If `FakeAgentDrivers` has no `dialled` list, add one that stays empty — **and
say in your report that you added it**, because `fakes.py` is shared.

- [ ] **Step 2: Run and watch them fail** — `RestoreDevice` is not defined.

- [ ] **Step 3: The port, the two adapters, and the use case**

In `application/ports/repositories.py`, on `DeviceRepository`, beside `revoke`:

```python
    async def restore(self, tenant_id: TenantId, device_id: DeviceId) -> bool:
        """Give a revoked browser its authority back. ``True`` when one was
        taken away, ``False`` when it was never revoked.

        Exists because revocation started enforcing. While `revoked_at` changed
        no answer, a wrong press was cosmetic; now it refuses the browser on
        every device-scoped path, and registration is deliberately idempotent
        and hands back the same secret -- so re-registering does NOT undo it,
        and without this the only way back is a hand-edited row.

        The secret is untouched: the browser still holds a working one.
        """
        ...
```

In the SQL repository, beside `revoke`, the same shape with
`revoked_at=None` and a `RETURNING`-or-rowcount check so the boolean is the
row's, not a re-read's. In `tests/unit/fakes.py`'s `FakeDeviceRepository`,
the same rule.

In `application/capture/devices.py`:

```python
class RestoreDevice:
    """A revoked browser may act again.

    No socket is opened: the extension dials on its own next heartbeat, and a
    backend that dialled a laptop nobody is sitting at would be a channel
    nobody asked for. That is the asymmetry with `RevokeDevice`, which drops
    one -- cutting off is urgent, letting back in is not.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, ctx: RequestContext, *, device_id: DeviceId) -> bool:
        async with self._uow as uow:
            restored = await uow.devices.restore(ctx.tenant_id, device_id)
            await uow.commit()
        return restored
```

- [ ] **Step 4: Run the use-case tests** — 4 passed.

- [ ] **Step 5: Retire `ReadDevices`**

- Point `routers/agents.py`'s device listing at `container.read_roster()`.
- Add `online: bool` to its response model, sourced from `DeviceLine.online`.
- Delete `ReadDevices` from `application/observation/register.py` and its
  container factory.
- `grep -rn "ReadDevices" src/ tests/` must come back empty.

Write the reason into the router where the call now happens:

```python
    # `ReadRoster` rather than the `ReadDevices` that used to be here: a strict
    # superset over the identical repository call, and two use cases over one
    # `list_for_tenant` in two packages is how they drift apart. `online` is
    # the thing it adds, and it is the question this list is actually read to
    # answer.
```

- [ ] **Step 6: The router**

```python
# src/sro/interface/http/v1/routers/devices.py
"""Who may act in this tenant, and taking it away or giving it back.

Ported from `new_agent_arch/src/rig/api.py:976-1019`. Tenant-only, all three:
a browser's secret opens its own doors and never the other browsers'.

`restore` has no rig ancestor. It exists because this port made revocation
enforce -- the rig's `issue` un-revoked as a side effect of handing out a fresh
token, and backend registration is idempotent and returns the same secret, so
nothing here undid a revoke until this route did.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from sro.application.observation.register import NotFound
from sro.domain.shared.identifiers import DeviceId
from sro.interface.http.deps import ContainerDep, ContextDep
from sro.interface.http.schemas import RosterResponse, RevocationResponse

router = APIRouter(tags=["devices"])


@router.get("/devices")
async def roster(container: ContainerDep, ctx: ContextDep) -> RosterResponse:
    return RosterResponse.of(await container.read_roster().execute(ctx))


@router.post("/devices/{device_id}/revoke")
async def revoke(
    device_id: str, container: ContainerDep, ctx: ContextDep
) -> RevocationResponse:
    """`moved` is false for a browser that was already revoked.

    Not a 404 and not an error: the first revocation's instant is what an audit
    is read against, and a second press must not move it. The 404 is for a
    browser this tenant does not have, which is a different answer.
    """
    try:
        moved = await container.revoke_device().execute(ctx, device_id=DeviceId(device_id))
    except NotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RevocationResponse(device_id=device_id, moved=moved)


@router.post("/devices/{device_id}/restore")
async def restore(
    device_id: str, container: ContainerDep, ctx: ContextDep
) -> RevocationResponse:
    try:
        moved = await container.restore_device().execute(ctx, device_id=DeviceId(device_id))
    except NotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RevocationResponse(device_id=device_id, moved=moved)
```

- [ ] **Step 7: Route tests**

```python
# tests/unit/interface/test_devices_route.py

def test_a_browser_is_revoked_and_the_second_press_moves_nothing(app_client) -> None:
    first = app_client.post("/v1/devices/dev_1/revoke", headers=TENANT)
    second = app_client.post("/v1/devices/dev_1/revoke", headers=TENANT)
    assert first.json()["moved"] is True
    assert second.json()["moved"] is False


def test_revoking_a_browser_this_tenant_does_not_have_is_a_404(app_client) -> None:
    assert app_client.post("/v1/devices/nobody/revoke", headers=TENANT).status_code == 404


def test_a_browser_may_not_revoke_anything(app_client) -> None:
    # Tenant-only: the money and the other browsers are not a browser's to
    # touch. A device secret on this path is not a second way in.
    answered = app_client.post(
        "/v1/devices/dev_1/revoke", headers={**TENANT, "X-Device-Secret": "shh"}
    )
    assert answered.status_code == 403


def test_the_roster_says_which_browsers_are_connected(app_client) -> None:
    body = app_client.get("/v1/devices", headers=TENANT).json()
    assert [line["online"] for line in body["devices"]] == [False]


def test_a_revoked_browser_stays_on_the_roster_carrying_when_it_ended(app_client) -> None:
    # The list is read before cutting a browser off and after. A revocation
    # that erased its own subject would leave an administrator unable to
    # confirm the thing they just did.
    app_client.post("/v1/devices/dev_1/revoke", headers=TENANT)
    (line,) = app_client.get("/v1/devices", headers=TENANT).json()["devices"]
    assert line["device_id"] == "dev_1"
    assert line["revoked_at"] is not None
    assert line["online"] is False


def test_a_restored_browser_is_on_the_roster_with_no_revocation(app_client) -> None:
    app_client.post("/v1/devices/dev_1/revoke", headers=TENANT)
    app_client.post("/v1/devices/dev_1/restore", headers=TENANT)
    (line,) = app_client.get("/v1/devices", headers=TENANT).json()["devices"]
    assert line["revoked_at"] is None
```

**The tenant-only rule needs a dependency.** Add to `asking.py`:

```python
async def tenant_only(asking: AskingDeviceDep) -> None:
    """The tenant's own credential, not a browser proving itself.

    Ported from `new_agent_arch/src/rig/api.py:423`. Registering and revoking
    browsers, spending model money and reading every browser's day are the
    tenant's: a browser's secret opens its own doors and not the tenant's purse
    or the other browsers' evidence.
    """
    if asking is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="that is the tenant's to do, not a browser's",
        )


TenantOnly = Depends(tenant_only)
```

and put `dependencies=[TenantOnly]` on this router.
**Extend `tests/unit/interface/test_asking.py` with a test for it**, both
directions.

- [ ] **Step 8: Mutate**

| Mutation | Must die |
|---|---|
| drop `dependencies=[TenantOnly]` from the devices router | `…a_browser_may_not_revoke_anything` |
| `restore` returns `True` always | `…moves_nothing` for restore |
| `restore` also clears the secret | `…keeps_the_secret_it_had` |
| `RestoreDevice` opens a channel | `…does_not_open_a_socket_by_itself` |
| roster hides revoked browsers | `…stays_on_the_roster_carrying_when_it_ended` |
| `NotFound` swallowed and reported as `moved: False` | `…is_a_404` |

- [ ] **Step 9: Gates and commit** (commit the port + adapters, the use case,
  the `ReadDevices` retirement, and the router as separate readable commits)

---

## Task 5: `GET /v1/audit`

**Files:**
- Create: `src/sro/interface/http/v1/routers/audit.py`
- Modify: `schemas.py`, `app.py`
- Test: `tests/unit/interface/test_audit_route.py`

**The rig:** `api.py:1366`. Tenant-only. `since` is required here where the rig
defaulted it to `""` meaning everything — a declared divergence plan 3b already
made at the use-case level (`ReadAudit.execute` takes a `datetime` with no
default); this route keeps it and says why.

- [ ] **Step 1: Write the failing tests**

```python
def test_the_audit_answers_with_the_bound_it_actually_used(app_client) -> None:
    # A caller that passes a naive time is told, in UTC, what that was taken
    # to mean -- which is the whole reason `Audit.since` is handed back rather
    # than echoed from the query.
    body = app_client.get("/v1/audit", params={"since": "2026-03-04T09:10:00"}, headers=TENANT).json()
    assert body["since"] == "2026-03-04T09:10:00+00:00"


def test_the_audit_needs_a_bound(app_client) -> None:
    # The rig's "no since means everything" is not ported: an unbounded audit
    # over a real tenant is a query nobody meant to run, and the console always
    # has a window in hand.
    assert app_client.get("/v1/audit", headers=TENANT).status_code == 422


def test_a_browser_may_not_read_the_tenants_audit(app_client) -> None:
    answered = app_client.get(
        "/v1/audit",
        params={"since": "2026-03-04T09:10:00Z"},
        headers={**TENANT, "X-Device-Secret": "shh"},
    )
    assert answered.status_code == 403


def test_each_list_comes_back_newest_first(app_client) -> None:
    body = app_client.get("/v1/audit", params={"since": "2026-01-01T00:00:00Z"}, headers=TENANT).json()
    for key in ("runs", "offers", "devices", "chats"):
        stamps = [row.get("at") or row.get("started_at") for row in body[key]]
        assert stamps == sorted(stamps, reverse=True), f"{key} was not newest first"
```

- [ ] **Steps 2–4:** run, write the router, run again. The router is a
  `ContextDep` + `container.read_audit()` call with `dependencies=[TenantOnly]`
  and an `AuditResponse.of(...)` in `schemas.py` carrying `since`, `runs`,
  `offers`, `devices`, `chats`.

- [ ] **Step 5: Mutate** — drop `TenantOnly`; echo the query's `since` instead
  of the `Audit.since` the use case returned; reverse one list's order (**re-run
  at `PYTHONHASHSEED` 0, 1, 42, 12345**); pass `ctx.tenant_id` from a literal.

- [ ] **Step 6: Gates and commit**

---

## Task 6: `GET /v1/spend`

**Files:**
- Create: `src/sro/interface/http/v1/routers/spend.py`
- Modify: `schemas.py`, `app.py`, `src/sro/container.py`
- Test: `tests/unit/interface/test_spend_route.py`

**The rig:** `api.py:663`, tenant-only. Reads
`SqlSpendRepository.today(tenant_id, now=...)` → `DaySpend`. The cap is
`settings.daily_usd_cap`, added by plan 3b Task 1.

The one rule worth its own test: **`unpriced` is reported, not folded into the
total.** A day whose bill cannot be trusted must say so — that is what plan 3b's
`789d069` and `11782b4` exist for, and a route that returned only a number
would throw it away at the last step.

- [ ] **Step 1: Write the failing tests**

```python
def test_the_day_reports_what_it_could_not_price(app_client) -> None:
    body = app_client.get("/v1/spend", headers=TENANT).json()
    assert body["unpriced"] is True
    assert "cost_usd" in body


def test_the_cap_is_reported_beside_the_spend(app_client) -> None:
    # Without it the console has a number and no scale, and "am I about to be
    # cut off" is the only question this endpoint is opened to answer.
    body = app_client.get("/v1/spend", headers=TENANT).json()
    assert body["cap_usd"] == 25.0


def test_a_browser_may_not_read_the_tenants_purse(app_client) -> None:
    answered = app_client.get("/v1/spend", headers={**TENANT, "X-Device-Secret": "shh"})
    assert answered.status_code == 403
```

Set the cap fixture to a value that is **not** the production default, so the
test fails if the route hardcodes one.

- [ ] **Steps 2–6:** as Task 5. Mutations: drop `TenantOnly`; return
  `unpriced=False` always; read the cap from a literal rather than settings;
  `now` from a fresh clock rather than the container's.

---

## Task 7: `GET /v1/workflows` and `/v1/workflows/{id}/evidence`

**Files:**
- Create: `src/sro/interface/http/v1/routers/workflows.py`
- Modify: `schemas.py`, `app.py`, `src/sro/container.py`
- Test: `tests/unit/interface/test_workflows_route.py`

**The rig:** `api.py:812` (authorised — tenant or browser) and `api.py:904`
(**tenant-only**: evidence is every browser's gestures, and one browser must not
read another's day through a workflow it happens to share).

That asymmetry is the whole point of the task and must be tested in both
directions.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_browser_may_list_the_jobs_it_could_be_offered(app_client) -> None:
    answered = app_client.get(
        "/v1/workflows",
        params={"device_id": "dev_1"},
        headers={**TENANT, "X-Device-Secret": "shh"},
    )
    assert answered.status_code == 200


def test_a_browser_may_not_read_a_jobs_evidence(app_client) -> None:
    # The list is what a browser may be offered; the evidence under it is
    # every browser's gestures. One is a menu, the other is somebody's day.
    answered = app_client.get(
        "/v1/workflows/wfl_1/evidence",
        headers={**TENANT, "X-Device-Secret": "shh"},
    )
    assert answered.status_code == 403


def test_the_tenant_may_read_a_jobs_evidence(app_client) -> None:
    assert app_client.get("/v1/workflows/wfl_1/evidence", headers=TENANT).status_code == 200


def test_evidence_for_a_job_this_tenant_does_not_have_is_a_404(app_client) -> None:
    assert app_client.get("/v1/workflows/nope/evidence", headers=TENANT).status_code == 404
```

- [ ] **Steps 2–6:** as above. Add `container.read_workflows()` and
  `container.workflow_evidence()` factories in Task 2's style. Mutations: swap
  the two dependencies between the routes (**this is the finding the task
  exists for** — it must die); `ctx.tenant_id` from a literal; the 404 softened
  to an empty list.

---

## Task 8: `POST /v1/offers`

**Files:**
- Create: `src/sro/interface/http/v1/routers/offers.py`
- Modify: `schemas.py`, `app.py`
- Test: `tests/unit/interface/test_offers_route.py`

**The rig:** `api.py:1548`. Authorised (a browser records its own offers). Four
validations, each with its own status code, and **the body is validated before
anything is written**: an unknown workflow is 400, a fate outside `FATES` is
400, a negative or non-integer `k` is 400, and only then is the row recorded.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_browser_records_the_offer_it_showed(app_client) -> None:
    answered = app_client.post(
        "/v1/offers",
        json={"workflow_id": "wfl_1", "fate": "shown", "k": 2, "device_id": "dev_1"},
        headers={**TENANT, "X-Device-Secret": "shh"},
    )
    assert answered.status_code == 201
    assert answered.json()["offer_id"].startswith("off_")


def test_an_offer_against_a_job_this_tenant_does_not_have_is_refused(app_client) -> None:
    answered = app_client.post(
        "/v1/offers",
        json={"workflow_id": "nope", "fate": "shown", "k": 1},
        headers={**TENANT, "X-Device-Secret": "shh"},
    )
    assert answered.status_code == 400
    assert "nope" not in answered.text, "the refusal echoed the body into the log"


def test_a_fate_that_is_not_one_is_refused(app_client) -> None:
    answered = app_client.post(
        "/v1/offers",
        json={"workflow_id": "wfl_1", "fate": "maybe", "k": 1},
        headers={**TENANT, "X-Device-Secret": "shh"},
    )
    assert answered.status_code == 400


def test_a_negative_k_is_refused_and_true_is_not_an_integer(app_client) -> None:
    # `True` is an int in Python and would record k=1 because the language
    # says so, not because anybody asked. The rig hit this on `from_step`.
    for k in (-1, True):
        answered = app_client.post(
            "/v1/offers",
            json={"workflow_id": "wfl_1", "fate": "shown", "k": k},
            headers={**TENANT, "X-Device-Secret": "shh"},
        )
        assert answered.status_code in (400, 422), f"k={k!r} was accepted"


def test_nothing_is_written_when_the_body_is_refused(app_client) -> None:
    app_client.post(
        "/v1/offers",
        json={"workflow_id": "nope", "fate": "shown", "k": 1},
        headers={**TENANT, "X-Device-Secret": "shh"},
    )
    assert app_client.get("/v1/audit", params={"since": "2026-01-01T00:00:00Z"}, headers=TENANT).json()["offers"] == []
```

- [ ] **Steps 2–6:** as above. Mutations: accept an unknown workflow; accept
  any fate; drop the `bool` check on `k`; record before validating (**the last
  test is the only thing that catches it**).

---

## Task 9: The offer replay, through the backend

**Files:**
- Create: `scripts/dry_run.py`
- Modify: root `Makefile` (the `offer-replay` target)
- Test: `tests/integration/test_offer_replay.py`

**Why:** the spec makes this phase 4's acceptance test — *"the offer replay
through `backend/scripts/dry_run.py`; `make offer-replay` names 8 of 8"* — and
it is the only check in this plan that exercises shapes and recognition
together against real stored evidence rather than fixtures.

The existing target runs the rig's `new_agent_arch/scripts/dry_run.py` and pipes
its JSON into `new-chrome-extension/scripts/offer-replay.mjs`. The backend's
script must emit **the same JSON shape** so the extension's replay script is
unchanged — read the rig's script for the shape before writing.

- [ ] **Step 1:** read `new_agent_arch/scripts/dry_run.py` and
  `new-chrome-extension/scripts/offer-replay.mjs`; write down the exact
  contract between them in your report.
- [ ] **Step 2:** write `backend/scripts/dry_run.py` emitting that shape from
  `container.shapes(...)` over a real Postgres, `--replay <path>`.
- [ ] **Step 3:** an integration test that runs the script against the
  integration database and asserts the JSON parses to the contract's shape.
- [ ] **Step 4:** add the Makefile target beside the existing one, named
  `offer-replay-backend` so both can run until phase 7 deletes the rig's.
- [ ] **Step 5:** run it. **Record the number named, whatever it is.** If it is
  not 8 of 8, that is a finding for phase 4b, not a reason to change the
  script's output — say so in your report and do not tune it.

---

## Task 10: The count, and what is left

**Files:** Modify: this plan file. **Status: done at `63dc580`.** No code
changed in this task; everything below is the accounting, and every line
number was read off the file rather than copied from a brief.

### The count, made by hand

**26 routes**, all of them in `new_agent_arch/src/rig/api.py`, all registered
by an `@app.get` / `@app.post` / `@app.websocket` decorator inside
`create_app`. Checked for registration anywhere else and found none: no
`APIRouter`, no `include_router`, no `add_api_route`, no `.mount()` — in
`api.py` or anywhere else under `new_agent_arch/src/`. The rig has no static
mount either; its one page is a route (`api.py:1575`) that reads
`web/index.html` off disk.

**The table above listed 25 rows for those 26 routes**, because `/v1/bakeoff`
and `/v1/bakeoff/readings` shared a row. So its arithmetic was right. Its
**paths were not** — six rows name a `{id}` segment the rig does not use, and
one route this plan shipped is missing from it entirely:

| The table said | The rig actually spells it | At |
|---|---|---|
| `WS /v1/agents/{id}/commands` | `{device_id}` | `api.py:440` |
| `GET /v1/workflows/{id}/evidence` | `{workflow_id}` | `api.py:904` |
| `POST /v1/devices/{id}/revoke` | `{device_id}` | `api.py:988` |
| `GET /v1/runs/{id}` | `{run_id}` | `api.py:1217` |
| `POST /v1/runs/{id}/abort` | `{run_id}` | `api.py:1237` |
| `POST /v1/runs/{id}/approve` | `{run_id}` | `api.py:1270` |
| *(no row)* | `POST /v1/devices/{device}/restore` — **4a shipped it; the rig has no such route** | `devices.py:71` |

Also worth stating because the table's shape hides it: **most of the rig's
surface was already on the backend before this plan started.** Nine of the 26
were ported in earlier phases, eight are ported here, seven are 4b's, and two
are dropped.

### Every rig route, accounted for

| # | Rig route (`api.py`) | Verdict | Where it is now |
|---|---|---|---|
| 1 | `GET /v1/health` :436 | **Ported before 4a**, path changed | `routers/health.py:25` as **`GET /health`** — `health.router` is the one router `app.py:89` includes *without* the `/v1` prefix. 4a added `GET /ready` beside it (`health.py:33`, commit `a3ac456`); the rig has no counterpart. |
| 2 | `WS /v1/agents/{device_id}/commands` :440 | **Ported before 4a**, byte-identical | `routers/agent_channel.py:36` |
| 3 | `POST /v1/observations` :478 | **Ported before 4a**; the spec's *observations extension* is **4b** | `routers/observations.py:24`. Diverges in the 202 body — see `snapshots_ignored` below. |
| 4 | `POST /v1/observations/artifacts` :537 | **Ported before 4a** | `routers/observations.py:59` |
| 5 | `GET /v1/streams` :587 | **Not ported. Later phase.** | Nothing reads the per-stream gesture roll-up. Tenant-only and read-only, so it would have fitted 4a; it was never in this plan's scope and the plan never claimed it. |
| 6 | `GET /v1/gestures` :596 | **Not ported. Later phase.** | Nearest is 4a's `GET /v1/workflows/{id}/evidence`, which reaches gestures only through one workflow's citations — not the raw stream a debugging page reads. |
| 7 | `GET /v1/spend` :663 | **Ported in 4a** | `routers/spend.py:44`, tenant-only. **Narrowed on purpose**: the rig answered twenty-two fields, this answers three (day's dollars, day's unpriced calls, cap). Reason written into the module docstring. |
| 8 | `POST /v1/mine` :739 | **4b** | `application/observation/mining_pass.py:164` is the ported pass and **has no caller**. **`POST /v1/candidates/mine` (`routers/candidates.py:51`) is NOT this route** — it is the heuristic candidate miner and makes no model call. Do not mistake one for the other in 4b. |
| 9 | `GET /v1/pool` :794 | **Not ported. Cheap for 4b.** | Everything behind it exists: `domain/observation/pool.py`, and `PoolRepository.retired` at `application/ports/repositories.py:623`. Nothing over the wire can read `retired`, which is the exact blindness the rig's docstring says the route exists to remove. |
| 10 | `GET /v1/workflows` :812 | **Ported in 4a** | `routers/workflows.py:51`, `authorised` — matching the rig. |
| 11 | `GET /v1/workflows/{workflow_id}/evidence` :904 | **Ported in 4a** | `routers/workflows.py:66`, `TenantOnly` — matching the rig. |
| 12 | `POST /v1/devices/register` :976 | **Ported before 4a**, path and shape changed | `routers/agents.py:35` as **`POST /v1/agents/register`**. The rig minted a fresh token each call and un-revoked as a side effect; backend registration is **idempotent and hands back the same secret**, which is precisely why `restore` had to exist (see `RestoreDevice`, `application/capture/devices.py:67-96`). |
| 13 | `POST /v1/devices/{device_id}/revoke` :988 | **Ported in 4a**, segment renamed | `routers/devices.py:59` as `/v1/devices/{device}/revoke`. URL byte-identical; see carried item 8 for why the segment differs. |
| 14 | `GET /v1/devices` :997 | **Ported in 4a**, two declared divergences | `routers/devices.py:52`. A device token gets a **403** here where the rig gave it a reduced answer; the body is `{"devices": [rows carrying online]}` where the rig's `devices` key meant the online-id subset. Both reasons are in the module docstring. |
| 15 | `POST /v1/runs` :1021 | **4b** | Nothing starts a workflow run. `application/execution/run_workflow.py:267` has no production caller — grep finds only `tests/unit/application/rig/test_runner.py`. `POST /v1/skills/{skill_id}/runs` (`routers/runs.py:48`) and `POST /v1/threads/{id}/runs` (`routers/threads.py:65`) start **skill** runs, a different resource. |
| 16 | `GET /v1/runs` :1152 | **4b — and the path is already occupied** | `routers/runs.py:217` answers a *different resource*: skill runs, filtered by `skill_id`, with no `awaiting`. The rig's lists **workflow** runs by `workflow_id` and can narrow to the parked ones. 4b must decide between extending that route and giving workflow runs their own path; it cannot simply "port" this one. |
| 17 | `GET /v1/runs/{run_id}` :1217 | **4b**, same collision | `routers/runs.py:234` resolves a skill run. |
| 18 | `POST /v1/runs/{run_id}/abort` :1237 | **4b** | `POST /v1/runs/{run_id}/stop` (`routers/runs.py:130`) is the skill-run half only — see carried item 1. |
| 19 | `POST /v1/runs/{run_id}/approve` :1270 | **4b** | `POST /v1/confirmations/{id}/approve` (`routers/confirmations.py:38`) approves a *confirmation*, keyed on the confirmation and not the run. Not the same door. |
| 20 | `GET /v1/bakeoff` :1313 | **Dropped** | The word `bakeoff` appears **nowhere** under `backend/`. The sweep it reads is started from a terminal (`make bakeoff`, in `new_agent_arch`) and writes a rig-private table; a read route over a table nothing on this side writes is a 404 with extra steps. If model comparison is ever wanted here it is a plan of its own, starting with the writer. |
| 21 | `GET /v1/bakeoff/readings` :1340 | **Dropped**, same reason | — |
| 22 | `GET /v1/audit` :1366 | **Ported in 4a** | `routers/audit.py:40`, tenant-only. |
| 23 | `POST /v1/chat` :1495 | **4b** | `application/chat/understand.py:114` is ported and **has no caller** — it takes an `Asker` nothing supplies. `POST /v1/intent/resolve` (`routers/intent.py:13`) is a different resolver over skills, not the rig's workflow chat. |
| 24 | `GET /v1/shapes` :1533 | **Ported in 4a** | `routers/shapes.py:30` |
| 25 | `POST /v1/offers` :1548 | **Ported in 4a** | `routers/offers.py:46`. Keeps the rig's four validations in the rig's order with the rig's 400s. Body drops the rig's `device_id` — the browser proves itself with `X-Device-Secret` instead, so no body can spend another browser's rest. |
| 26 | `GET /` (the served page) :1575 | **Not ported. Spec Open item, still open.** | The spec (`…-design.md:288-294`) recommends serving `index.html` at **`/rig`** during phase 4 so nothing is lost while console pages are built in phase 6. 4a did not do it. Still a decision, not a bug. |

**Totals:** ported before 4a **9** · ported in 4a **8** (7 rig routes + `restore`,
which has no rig ancestor) · 4b **7** · not ported, later phase **3** ·
dropped **2**. 9 + 7 + 7 + 3 = 26.

### What 4a added, in one place

Six new routers (`app.py:94-112`), eight routes:
`GET /v1/audit` · `GET /v1/devices` · `POST /v1/devices/{device}/revoke` ·
`POST /v1/devices/{device}/restore` · `POST /v1/offers` · `GET /v1/shapes` ·
`GET /v1/spend` · `GET /v1/workflows` · `GET /v1/workflows/{id}/evidence`
— plus `GET /ready` on the pre-existing health router.

### Gates at head

**Not filled in, deliberately, and this is the honest note rather than a
number.** This task changed no code, so no gate could move on it; and at the
time it was written a reviewer was mutating `backend/src` and `backend/tests`
in a separate worktree, so any figure taken here would have measured that
worktree and not this branch. The gate numbers for this branch belong to the
whole-branch review of `63dc580`, whose verdict is **NEEDS FIXES** — see
*Open against this branch* below.

---

## What phase 4b inherits

`.superpowers/` is gitignored and does not travel. This section is the record.

### Phase 4b's scope has shrunk, and this is the important part

4b was scoped as *"wire the Asker, give the miner and the runner a caller,
then the doors that write."* **The wiring is done, on this branch.** What is
left is a caller for `run_workflow`, the write doors, and the items below.

Four things were established by running the thing against a real store rather
than by reading it, and they change what 4b is:

- **The rig's model-driven half could not be constructed at all.**
  `container.asker` did not exist, and `mining_pass.mine` and `run_workflow`
  both take an `Asker` — neither could be built. Fixed here (`e32e478`;
  `container.py:197`, `:832`, `:919`). **Nothing under `src/` reads
  `container.asker` yet** — its docstring says "its caller checks and refuses"
  and there is no caller. **Phase 4b owns that**, and it is now the whole of
  what "wire the Asker" means.
- **Ingest never reached the evidence plane.** `correlate` and `add_gestures`
  had no caller anywhere; an upload stopped at `observation_batches`. Fixed
  (`f8b218f`; `application/observation/ingest.py:241-257`). A backfill then
  replayed **266 real batches into 507 gestures, 0 failures**.
- **The miner works on real evidence.** A real pass over those 507 gestures
  mined **2 workflows**, and the offer replay named **2 of 2 as themselves**.
  The chain runs end to end for the first time.
- **Task 9's "0 of 0" is superseded.** The replay reported nothing because the
  store was empty, and its conclusion — that *no phase moves the corpus into
  Postgres* — was a misreading: nothing could mine a corpus, because ingest
  never reached the gesture tables. **There is no import task for 4b to
  find.** The original reading would have sent it hunting one.

### Two money findings, both measured, both with a latent sibling

- **`K_EFFORT` was `"high"` and truncated the Pro model.** 204,747 tokens in,
  65,522 out, the answer truncated after 2,610 tokens, **$2.00 spent and
  nothing kept**. At `"medium"`: 6,041 output tokens, $0.93, 2 of 3 jobs kept.
  Fixed (`527d8f2`; `domain/skill/umbrella.py:23`).
- **`K_WINDOW_TOKENS` did not guard the price boundary it exists for.**
  `tokens()` (`domain/observation/window.py:115`) counts 4 characters to a
  token; on this evidence the real ratio is **2.36** — a **1.697×
  under-count** — so a 150,000 window shipped past 200,000, where Gemini 3.1
  Pro's input price doubles. Now 100,000, shipping 164,028 measured. Fixed
  (`63dc580`; `window.py:23`).
- **The latent sibling, which is the part 4b must not forget.** The fix was
  made at the constant and not at `tokens()`, because **every other cap in
  `window.py` is tuned against the same estimator** — `K_MAX_GESTURE_TOKENS`,
  `K_MAX_CROSSING_TOKENS`, the `kb` subtraction — and changing the divisor
  silently re-tunes all of them (four cap tests failed when it was tried).
  Each of those is the same bug in waiting; only the price-boundary one has
  been corrected.

### The pool rotates and does not starve

Ten simulated passes over the real store: pass 1 shows 81% of the day, pass 2
reaches 96%, and thereafter the window genuinely rotates — 375 to 426 gestures
shown per pass, a different set each time. The 19 never shown are all
**claimed**: cited by a mined workflow and deliberately out of the pool. This
is evidence, not a worry; recorded so nobody re-derives it.

### Nine carried defects and decisions

1. **No route can reach a parked workflow run to stop it.** The loop's half is
   built and proved, but `StopRun.execute`
   (`application/execution/read_runs.py:68-79`) resolves only through
   `uow.runs` — skill runs. A workflow run parked on an approval cannot be
   stopped from outside the process.
2. **`run_workflow` has no production caller.** `application/execution/run_workflow.py:267`;
   grep finds only `tests/unit/application/rig/test_runner.py`. **This is now
   the last unwired link in the whole chain** — ingest, mining and the Asker
   were all closed on this branch.
3. **A resumed run does not remember where it got to.** `from_step` is a
   parameter of `run_workflow` (`run_workflow.py:284`) and is on no persisted
   field of `WorkflowRun`. A run re-entered from a claimed row would redo the
   operator's steps. A resume route cannot be written until the field exists.
4. **`RestoreDevice` erases the audit instant.** Documented in the code
   (`application/capture/devices.py:83-90`): a restore deletes the revocation
   outright, so `DeviceRepository.since` afterwards has no record the browser
   was ever cut off, and a day containing a revoke and a restore reads as a day
   containing neither. `ReadAudit` cannot reconstruct one. The real answer is a
   **device-event table this codebase does not have** — a plan of its own, not
   a 4b line item.
5. **`SqlDeviceRepository.since` has no id tiebreak.**
   `infrastructure/db/repositories.py:653` orders `registered_at.desc()` alone.
   `ReadAudit` reads four collections (`application/analytics/audit.py:75-86`)
   and the **other three all break their tie** — `workflow_runs.since` on
   `id.desc()` (`db/workflow_runs.py:226`), `offers.since` on `seq`
   (`db/offers.py:118`), `chats.since` on `id.desc()` (`db/offers.py:180`).
   Landed with plan 3b. **The fix is `.id.desc()`.** (Noted while checking:
   `list_for_tenant` in the same class, `repositories.py:632`, has no tiebreak
   either — but it is not one of the audit's four and is out of scope for this
   item.)
6. **One response carries two spellings of UTC.** `DeviceLineModel`
   (`interface/http/schemas.py:1596-1598`) has `registered_at: datetime` and
   `revoked_at: str | None`, because `AgentDevice` is inconsistent the same way
   (`domain/observation/device.py:29` and `:62`). **Judged acceptable and the
   reason is in the schema's docstring** — re-parsing the string here would
   invent a timezone the row never recorded. The root cause is a **domain**
   inconsistency and the fix belongs there, not in a response model.
7. **`container.read_spend`'s docstring is correct at head — item closed.**
   The check was whether Task 8's conversion of `record_offer` into a class had
   left the docstring citing something that no longer exists. It has not:
   `container.py:330-331` already reads *"`record_offer` next door **was** a
   bare function too, and became a class anyway"* — past tense, and accurate
   against `container.py:347-355`. Nothing to fix; recorded so nobody re-opens
   it.
8. **`{device}` is the one path segment not spelled `device_id`.** Not
   cosmetic and not a choice: `tenant_only` pulls in `asking_device`, which
   reads `?device_id=` to learn which browser is proving itself, and FastAPI
   **refuses to build the app** when one name is both a path parameter and a
   defaulted query parameter. Two different browsers can be named on one of
   these requests. The seven `/v1/agents/{device_id}/…` paths keep their
   spelling because none of them is tenant-only. **The URL an operator types is
   byte-identical.** Reason is in `routers/devices.py:25-32`.
9. **`spend.py`'s "nothing here catches a domain error" has no test behind
   it.** `routers/spend.py:30-31`, inherited word for word from
   `routers/audit.py:22`. The project's fourth test rule says a comment
   recording a decision needs a test that fails when the decision stops being
   true; this one has none in either file.

### Three more, found by running it, that 4b must decide

- **`add_orphan_request` and `add_orphan_page` have no caller in `src/`.**
  Declared at `application/ports/repositories.py:552` and `:563`, implemented
  at `infrastructure/db/evidence.py:281` and `:300`, called by nothing.
  This is **the same no-caller defect that `f8b218f` fixed for
  `add_gestures`, still standing**: `correlate` returns both lists and
  `ingest.py:241` discards them as `_calls` and `_marks`. The consequence is
  concrete — a click whose XHR lands in the *next* batch loses its call
  permanently. **Cross-batch correlation is dead in the backend and alive in
  the rig.** Either wire them or declare the divergence in the code; it should
  not stay a silent one.
- **`snapshots_ignored` is dropped on the floor.** The rig returns it in the
  202 body (`new_agent_arch/src/rig/api.py:534`); `ingest.py:241` unpacks it as
  `snapshots` and never uses it, and `Ingested` does not carry it. This is
  against `correlate`'s own docstring, which says the count exists because
  *silently dropping them is not the same as never having received them*.
- **`GET /v1/pool`, `GET /v1/streams`, `GET /v1/gestures`** — three read-only
  rig doors with nothing behind them on this side. `pool` is the cheap one:
  `PoolRepository.retired` already exists and nothing can read it.

---

## Open against this branch, pending a second reader

A whole-branch review of `63dc580` returned **NEEDS FIXES**, and a second
independent review of the same commit was still running when this was written.
**Nothing in this section is settled, agreed, or done.** It is here so that a
later phase reading this plan does not mistake silence for a clean bill.

Fixes are outstanding, or at least claimed, for:

- **`K_WINDOW_TOKENS` is unpinned.** No test asserts its value or an upper
  bound on it; every test that mentions it *derives* from it
  (`tests/unit/application/rig/test_mine.py:162`,
  `tests/unit/domain/rig/test_umbrella.py:184`), so raising it back to 150,000
  — the value that crossed the price boundary — fails nothing.
- **The redacted-events decision in ingest is untested.** `ingest.py` correlates
  from the **redacted** events rather than the accepted ones, with a reason
  written beside it; no test fails if that flips.
- **`tokens()`'s docstring claims a safety property that was measured false.**
  `window.py:115-118` still says it "never lies in the expensive direction",
  which the 1.697× under-count above directly contradicts.
- **A tally assertion was weakened by `527d8f2`.**

Each is named, not judged. Confirm against the reviews before acting.

---

## Self-Review

**Spec coverage.** The spec's Interface section names `observations`
(extended), `shapes`, `offers`, `runs` (extended), `devices`, `audit`, `spend`,
`mine`, `chat`, `workflows`. This plan covers `shapes`, `offers`, `devices`,
`audit`, `spend`, `workflows`. **Deliberately deferred to 4b:** `runs`
(extended), `mine`, `chat`, and the `observations` extension — every one of
them either spends money or starts a run, which is the write half the split was
drawn on. Task 10 records that.

**The auth mapping** the spec asks for ("the rig's `caller`/`tenant_only`
become dependencies on the backend's auth") is Task 1 plus the `tenant_only`
added in Task 4.

**Type consistency:** `AskingDeviceDep` is used by Tasks 3, 7 and 8 exactly as
Task 1 defines it; `TenantOnly` is defined in Task 4 and used by Tasks 5, 6 and
7 — **Task 4 must therefore land before 5, 6 and 7**, which the task order
already requires.

**Known thin spots, stated rather than hidden:** Tasks 5, 6 and 7 give step
outlines rather than full router bodies, because all three are the same shape
as Task 3's, which is written out in full and is the one to copy. Task 9 is
deliberately investigative — the contract between the two existing scripts has
to be read before it can be restated, and inventing it here would be a
placeholder wearing a code block.
