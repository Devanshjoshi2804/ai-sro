"""Persistence ports.

``tenant_id`` is the first parameter everywhere and never defaulted, so scoping
is checked by mypy rather than by review. Missing entities raise ``NotFound``
instead of returning ``None``.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol

from sro.domain.chat.thread import Thread, ThreadId
from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.execution.model_call import ModelCall
from sro.domain.execution.run import Run, RunId
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel, KnowledgeEntry
from sro.domain.observation.batch import ObservationBatch
from sro.domain.observation.candidate import CandidateStatus, TaskCandidate
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.gesture import Gesture, GestureBatch, Intent
from sro.domain.observation.policy import ObservationPolicy
from sro.domain.observation.pool import PoolEntry
from sro.domain.recording.recording import Recording
from sro.domain.shared.identifiers import (
    BatchId,
    BrowserSessionId,
    CandidateId,
    ConfirmationId,
    DeviceId,
    PrincipalId,
    RecordingId,
    SkillId,
    TenantId,
    TriggerId,
)
from sro.domain.shared.objective import ObjectiveKey
from sro.domain.skill.skill import Skill
from sro.domain.trigger.confirmation import Confirmation
from sro.domain.trigger.trigger import Trigger


class RecordingRepository(Protocol):
    async def add(self, recording: Recording) -> None: ...

    async def get(self, tenant_id: TenantId, recording_id: RecordingId) -> Recording: ...

    async def save(self, recording: Recording) -> None: ...

    async def list_for_tenant(
        self,
        tenant_id: TenantId,
        *,
        objective_key: ObjectiveKey | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Recording, ...]:
        """Newest first. Filtering by objective is how the UI offers run pairing."""
        ...

    async def list_capturing(self) -> tuple[Recording, ...]:
        """Recordings open right now, across tenants.

        Crosses the tenant boundary for one reason: the browser reaper has to
        know which sessions somebody is demonstrating in before it releases
        any, and nobody is making that request. It returns recordings, never
        their contents.
        """
        ...


class SkillRepository(Protocol):
    async def add(self, skill: Skill) -> None: ...

    async def get(self, tenant_id: TenantId, skill_id: SkillId) -> Skill: ...

    async def save(self, skill: Skill) -> None: ...

    async def find_by_objective(
        self, tenant_id: TenantId, objective_key: ObjectiveKey
    ) -> Skill | None:
        """``None`` is meaningful here: the caller creates the skill instead."""
        ...

    async def list_for_tenant(
        self, tenant_id: TenantId, *, limit: int = 50, offset: int = 0
    ) -> tuple[Skill, ...]: ...


class ConnectionRepository(Protocol):
    async def add(self, connection: Connection) -> None: ...

    async def get(self, tenant_id: TenantId, connection_id: ConnectionId) -> Connection: ...

    async def save(self, connection: Connection) -> None: ...

    async def find_by_system(self, tenant_id: TenantId, target_system: str) -> Connection | None:
        """``None`` is meaningful: the caller offers to connect one instead."""
        ...

    async def list_for_tenant(self, tenant_id: TenantId) -> tuple[Connection, ...]: ...

    async def list_connected(self) -> tuple[Connection, ...]:
        """Every connected system, across tenants.

        The one query in this codebase that deliberately crosses the tenant
        boundary, and the only caller is the keeper that signs sessions back in
        before they expire: nobody is making the request, so there is no tenant
        to scope it to. It returns connections, never anybody's data.
        """
        ...


class RunRepository(Protocol):
    async def add(self, run: Run) -> None: ...

    async def get(self, tenant_id: TenantId, run_id: RunId) -> Run: ...

    async def save(self, run: Run) -> None:
        """Overwrite the record of a run in progress.

        A run is append-only in the domain, so this only ever grows the step
        log; the repository rewrites the row because a run is one document.
        """
        ...

    async def list_for_tenant(
        self,
        tenant_id: TenantId,
        *,
        skill_id: SkillId | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Run, ...]:
        """Newest first."""
        ...

    async def finished_since(
        self, tenant_id: TenantId, *, target_system: str, since: datetime
    ) -> tuple[Run, ...]:
        """Runs against one system that have ended. What the breaker reads."""
        ...

    async def since(self, tenant_id: TenantId, *, since: datetime) -> tuple[Run, ...]:
        """Every run in a window, whatever it was for. What a summary counts.

        ponytail: whole rows, and the caller judges each one with the same
        function that judged it at finish -- so the numbers on a screen agree
        with the ladder rather than being a second opinion about it. Becomes a
        GROUP BY when a tenant does thousands of runs a day.
        """
        ...


class KnowledgeRepository(Protocol):
    async def add(self, entry: KnowledgeEntry) -> None: ...

    async def current(
        self, tenant_id: TenantId, *, system: str, kind: EntryKind, key: str
    ) -> KnowledgeEntry | None:
        """The claim believed right now for this key, if there is one."""
        ...

    async def save(self, entry: KnowledgeEntry) -> None: ...

    async def history(
        self, tenant_id: TenantId, *, system: str, kind: EntryKind, key: str, limit: int = 10
    ) -> tuple[KnowledgeEntry, ...]:
        """Every claim ever made about one key, newest first, superseded ones
        included.

        ``current`` is what the system believes; this is how it came to believe
        it. Nothing here is ever overwritten, so how many separate runs have
        said the same thing is already recorded and needs no counter of its own
        -- which is what a rule that must not act on a single observation reads.
        """
        ...

    async def without_embedding(
        self, tenant_id: TenantId, *, limit: int = 200
    ) -> tuple[KnowledgeEntry, ...]:
        """Current entries with no vector, for a deployment that turned
        embeddings on after it had already stored things."""
        ...

    async def search(
        self,
        tenant_id: TenantId,
        *,
        system: str | None = None,
        kinds: tuple[EntryKind, ...] = (),
        terms: str = "",
        embedding: tuple[float, ...] = (),
        min_evidence: EvidenceLevel | None = None,
        limit: int = 20,
    ) -> tuple[KnowledgeEntry, ...]:
        """Superseded entries are never returned: they are history, not belief.

        Structured filters narrow first and similarity only orders what is left
        -- ``docs/09-agentic-standards.md``, because a nearest neighbour across
        the whole store answers confidently with the wrong system's endpoint.
        """
        ...


class ThreadRepository(Protocol):
    async def add(self, thread: Thread) -> None: ...

    async def get(self, tenant_id: TenantId, thread_id: ThreadId) -> Thread: ...

    async def save(self, thread: Thread) -> None: ...

    async def list_for_tenant(
        self,
        tenant_id: TenantId,
        *,
        opened_by: PrincipalId | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Thread, ...]:
        """Most recently opened first.

        `opened_by` is one operator's own conversations, and it is a clause
        rather than a filter the caller applies afterwards: the console starts
        a thread on every first ask, so a page of the tenant's newest is a
        window somebody else's threads can push an operator's out of -- which
        would quietly begin them a second conversation.
        """
        ...


class ModelCallRepository(Protocol):
    async def add(self, call: ModelCall) -> None: ...

    async def list_for_run(self, tenant_id: TenantId, run_id: RunId) -> tuple[ModelCall, ...]:
        """Every call a run made, oldest first. The run's egress record."""
        ...


class BrowserSessionRepository(Protocol):
    """Who a browser belongs to.

    The only durable answer to that question. The API and the Temporal worker
    each open and close browsers in their own process, so an in-memory map is
    one process's opinion about a resource both of them touch.
    """

    async def claim(
        self,
        tenant_id: TenantId,
        session_id: BrowserSessionId,
        opened_by: PrincipalId,
        opened_at: datetime,
    ) -> None:
        """Record the owner.

        Raises ``Conflict`` when somebody already holds this id, which means the
        provider handed one browser to two callers. Serving it to the second is
        the bug this record exists to prevent, so it fails rather than transfers.
        """
        ...

    async def held_by(self, tenant_id: TenantId) -> tuple[BrowserSessionId, ...]:
        """Every session this tenant has claimed, live or not.

        Liveness belongs to the provider; the caller intersects the two.
        """
        ...

    async def all_held(self) -> tuple[tuple[BrowserSessionId, datetime], ...]:
        """Every claim in the deployment, and when it was made.

        Crosses the tenant boundary for the same reason ``list_capturing`` does:
        the browser sweep has to know which sessions are spoken for, and nobody
        is making that request. Ids and timestamps, never a tenant.
        """
        ...

    async def release(self, session_id: BrowserSessionId) -> None:
        """Forget the claim. Idempotent, and deliberately not tenant-scoped:
        crash recovery and the sweep are not anybody's request."""
        ...


class DeviceRepository(Protocol):
    async def add(self, device: AgentDevice) -> None: ...

    async def get(self, tenant_id: TenantId, device_id: DeviceId) -> AgentDevice: ...

    async def save(self, device: AgentDevice) -> None: ...

    async def registered_as(
        self, tenant_id: TenantId, principal_id: PrincipalId, label: str
    ) -> AgentDevice | None:
        """The device this operator already registered under this label.

        Registration is idempotent on it: an extension that lost its stored id
        -- a reinstall, a cleared profile -- must not accumulate a device per
        attempt, because the device list is how an administrator sees who is
        being observed.
        """
        ...

    async def list_for_tenant(self, tenant_id: TenantId) -> tuple[AgentDevice, ...]:
        """Most recently seen first."""
        ...


class ObservationRepository(Protocol):
    async def add(self, batch: ObservationBatch) -> None:
        """Raises ``Conflict`` when this batch id is already stored. The id is
        the extension's, so a retry of an upload that did land must be
        recognised rather than stored twice."""
        ...

    async def get(self, tenant_id: TenantId, batch_id: BatchId) -> ObservationBatch | None:
        """``None`` rather than ``NotFound``: the caller is asking whether a
        retry is a retry, and absence is the ordinary answer."""
        ...

    async def between(
        self,
        tenant_id: TenantId,
        *,
        since: datetime,
        until: datetime | None = None,
        principal_id: PrincipalId | None = None,
    ) -> tuple[ObservationBatch, ...]:
        """Batches overlapping a window, oldest first. What the miner reads, and
        what a purge counts."""
        ...

    async def for_recording(
        self, tenant_id: TenantId, recording_id: RecordingId
    ) -> tuple[ObservationBatch, ...]:
        """Every teaching batch of one demonstration, oldest first.

        Asked once, when the demonstration is sealed: the frames are assembled
        from all of it at once rather than per upload, because a click and the
        call it caused routinely land in different batches and a frame split
        across that seam is a step that lost its evidence.
        """
        ...

    async def tenants_since(self, since: datetime) -> tuple[TenantId, ...]:
        """Every tenant with evidence in the window.

        Tenant-blind, like the browser sweep and for the same reason: the
        scheduled miner has no request behind it and nobody to take a tenant
        from. Ids only, never a row.
        """
        ...

    async def forget(self, tenant_id: TenantId, ids: tuple[BatchId, ...]) -> None:
        """Delete the rows. The blobs they point at are the caller's to remove;
        a repository does not reach into object storage."""
        ...


class CandidateRepository(Protocol):
    async def add(self, candidate: TaskCandidate) -> None: ...

    async def get(self, tenant_id: TenantId, candidate_id: CandidateId) -> TaskCandidate: ...

    async def save(self, candidate: TaskCandidate) -> None: ...

    async def list_for_tenant(
        self,
        tenant_id: TenantId,
        *,
        status: CandidateStatus | None = None,
        principal_id: PrincipalId | None = None,
        seen_at_least: int = 0,
        host: str | None = None,
    ) -> tuple[TaskCandidate, ...]:
        """Most often seen first. The miner reads them all, including dismissed
        ones -- a task somebody said no to must not be offered again next week
        as if it were new.

        `host` is one system, which is what the extension's panel asks: "tasks
        you keep doing *here*" is a different question from "tasks you keep
        doing", and filtering after a limit would let twenty from elsewhere push
        the answer off the list.
        """
        ...


class ObservationPolicyRepository(Protocol):
    async def get(self, tenant_id: TenantId) -> ObservationPolicy | None:
        """``None`` when this tenant has never been given one. The caller
        supplies the refusing default -- absence must never read as consent."""
        ...

    async def save(self, tenant_id: TenantId, policy: ObservationPolicy) -> None: ...


class TriggerRepository(Protocol):
    async def add(self, trigger: Trigger) -> None: ...

    async def get(self, tenant_id: TenantId, trigger_id: TriggerId) -> Trigger: ...

    async def save(self, trigger: Trigger) -> None: ...

    async def remove(self, tenant_id: TenantId, trigger_id: TriggerId) -> None: ...

    async def list_for_tenant(
        self, tenant_id: TenantId, *, skill_id: SkillId | None = None
    ) -> tuple[Trigger, ...]:
        """Newest first."""
        ...

    async def find(self, trigger_id: TriggerId) -> Trigger | None:
        """Deliberately tenant-blind, and the only method here that is.

        A schedule fires with an id and nothing else -- there is no request and
        no caller to take a tenant from. What comes back carries its own, and
        everything after this point is scoped by that.
        """
        ...


class ConfirmationRepository(Protocol):
    async def add(self, confirmation: Confirmation) -> None: ...

    async def get(self, tenant_id: TenantId, confirmation_id: ConfirmationId) -> Confirmation: ...

    async def save(self, confirmation: Confirmation) -> None: ...

    async def waiting(self, tenant_id: TenantId) -> tuple[Confirmation, ...]:
        """Everything this tenant has not answered, oldest first.

        Including the ones that have run out: a card that vanished from a
        screen is not the same as one somebody can see was never answered, and
        the second is what tells a team its queue is not being read.
        """
        ...


class ToolCallRepository(Protocol):
    """What has already been sent through a connector, so it is not sent twice.

    A network step is protected within its run: an answered write is never
    retried, because a status code means the application saw it. Nothing
    protected a tool call *across* runs -- the same trigger firing twice, a
    durable workflow replayed after a crash, an operator pressing the button
    again because the first press seemed to hang. For a mail that is one
    message becoming two, and there is no taking it back.
    """

    async def remember(self, tenant_id: TenantId, key: str, *, tool: str, at: datetime) -> bool:
        """Claim this key. ``False`` when somebody already claimed it.

        Written *before* the call, and kept whatever the call answers. A key
        released on failure would let a timeout -- the one case where the send
        may well have landed -- be retried into a second send, which is the
        exact thing this exists to prevent. So a retry is refused and somebody
        is told the call may already have happened, which is the truth.
        """
        ...


class GestureRepository(Protocol):
    """The evidence plane: what a browser sent, what was read out of it."""

    async def add_batch(self, batch: GestureBatch) -> None:
        """Raises ``Conflict`` if that batch id was already written.

        An upload retried after its answer was lost must not be stored twice:
        the second copy would double every gesture in it and be mined as a
        second doing of the same job.
        """
        ...

    async def add_gestures(self, gestures: tuple[Gesture, ...]) -> None: ...

    async def gestures_for(
        self, tenant_id: TenantId, *, ids: tuple[str, ...] | None = None
    ) -> tuple[Gesture, ...]:
        """Ordered by ``at``. ``ids`` narrows to a citation set."""
        ...

    async def unread(self, tenant_id: TenantId, *, limit: int) -> tuple[Gesture, ...]:
        """Gestures with no intent row yet, oldest first."""
        ...

    async def save_intent(self, intent: Intent) -> None:
        """Replaces any earlier reading of that gesture."""
        ...

    async def intents_for(self, tenant_id: TenantId) -> tuple[Intent, ...]: ...

    async def add_orphan_request(
        self,
        tenant_id: TenantId,
        *,
        batch_id: str,
        request_id: str,
        payload: Mapping[str, object],
    ) -> None:
        """The same orphan twice is one row."""
        ...

    async def add_orphan_page(
        self, tenant_id: TenantId, *, batch_id: str, at: str, payload: Mapping[str, object]
    ) -> None: ...

    async def batch_owner(self, batch_id: str) -> str | None:
        """Which device uploaded that batch. ``None`` when nothing did.

        Tenant-blind on purpose, like ``TriggerRepository.find``: the question
        is asked of a device presenting its own token, before there is a tenant
        to scope by, so that one browser cannot mirror a screenshot onto
        another browser's batch.
        """
        ...

    async def count(self, tenant_id: TenantId) -> int: ...

    async def streams(self, tenant_id: TenantId) -> tuple[tuple[str, float, int], ...]:
        """(stream id, the last gesture's ``at``, how many), newest first."""
        ...


class PoolRepository(Protocol):
    """Evidence a pass did not place, waiting to be shown again.

    A retired entry is not a deleted one: it stops being offered ahead of fresh
    evidence and goes on being packed on its own merits. So the live entries
    and the retired ones are two reads, and an entry is retired exactly when it
    has a ``reason``.
    """

    async def add_unclaimed(
        self, tenant_id: TenantId, *, window_ids: tuple[str, ...], claimed: frozenset[str]
    ) -> int:
        """Anything the pass did not cite enters at age 0; anything it did leaves.

        ``claimed`` is cleared in full rather than only where it intersects the
        window: a pooled gesture is packed beside the fresh ones, so a pass can
        cite evidence that is only in the pool. Returns how many entered, and
        re-entering does not reset an entry's clock.
        """
        ...

    async def age(self, tenant_id: TenantId, *, shown: tuple[str, ...] | None = None) -> int:
        """One reading older, and only for evidence a reading actually saw.

        ``shown`` is what was in the window; ``None`` means every entry ages,
        which is what a caller with no window wants, and an empty tuple means a
        pass that packed nothing -- every entry waited one more. Returns how
        many retired, by either cap.
        """
        ...

    async def waiting(self, tenant_id: TenantId) -> tuple[PoolEntry, ...]:
        """Live entries, oldest first."""
        ...

    async def ids(self, tenant_id: TenantId) -> tuple[str, ...]:
        """Just the ids of the live entries, in the same order."""
        ...

    async def retired(self, tenant_id: TenantId) -> tuple[PoolEntry, ...]:
        """What the pool stopped offering, and why."""
        ...


class WorkflowRunRepository(Protocol):
    """What a run of a mined workflow left behind, and the approvals on it.

    The one port here whose reads are not all tenant-scoped. Approvals and the
    orphan sweep are deliberately tenant-blind, and each says why.
    """

    async def save(self, run: WorkflowRun) -> None:
        """Whole run, every time: called after every step so the panel can
        poll, with steps replaced rather than appended."""
        ...

    async def get(self, tenant_id: TenantId, run_id: str) -> WorkflowRun | None:
        """``None``, not ``NotFound``: every caller answers 404 itself."""
        ...

    async def for_workflow(self, tenant_id: TenantId, workflow_id: str) -> tuple[WorkflowRun, ...]:
        """Oldest first, as the rig listed them."""
        ...

    async def in_flight(self, tenant_id: TenantId, device_id: DeviceId) -> str | None:
        """The run this browser is already driving, if any.

        One browser, one hand: two runs driving the same window interleave
        their clicks into a form neither of them can then read back.
        """
        ...

    async def awaiting(self, tenant_id: TenantId) -> tuple[tuple[str, int, str], ...]:
        """(run id, step ord, what the step says) for every step waiting on a
        person, across browsers: anyone may answer a parked run."""
        ...

    async def approve(self, run_id: str, ord_: int, *, at: str, device_id: str | None) -> bool:
        """Whether this tap was the one that authorised the step.

        The first tap wins: a write rescued to the second rung parks at the
        same step and takes a second tap, and the first authorisation stands.
        Tenant-blind because the run id is the only thing the panel has, and
        the route has already checked the browser is driving this run.
        """
        ...

    async def approvals(self, run_id: str) -> tuple[tuple[int, str, str | None], ...]:
        """(step ord, when, which browser) for each write a person let out."""
        ...

    async def fail_orphans(self, reason: str) -> int:
        """Every run still ``running`` is marked failed, and how many there were.

        Called once at startup, across tenants -- nobody is making the request.
        One worker owns every run, so a row that says ``running`` when the
        process starts is a run nobody is driving. The reason lands on the
        last step, or on a new step when the run never reached one.
        """
        ...


class UnitOfWork(Protocol):
    """Transaction boundary. Leaving the block without ``commit`` rolls back."""

    recordings: RecordingRepository
    skills: SkillRepository
    connections: ConnectionRepository
    runs: RunRepository
    knowledge: KnowledgeRepository
    model_calls: ModelCallRepository
    threads: ThreadRepository
    browser_sessions: BrowserSessionRepository
    devices: DeviceRepository
    observations: ObservationRepository
    gestures: GestureRepository
    workflow_runs: WorkflowRunRepository
    pool: PoolRepository
    observation_policies: ObservationPolicyRepository
    candidates: CandidateRepository
    triggers: TriggerRepository
    tool_calls: ToolCallRepository
    confirmations: ConfirmationRepository

    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(self, *exc: object) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
