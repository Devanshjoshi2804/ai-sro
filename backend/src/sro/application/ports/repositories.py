"""Persistence ports.

``tenant_id`` is the first parameter everywhere and never defaulted, so scoping
is checked by mypy rather than by review. Missing entities raise ``NotFound``
instead of returning ``None``.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Protocol

from sro.domain.chat.reading import ChatReading
from sro.domain.chat.thread import Thread, ThreadId
from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.execution.belts import RunProof
from sro.domain.execution.learned_step import LearnedStep, Taught
from sro.domain.execution.model_call import ModelCall
from sro.domain.execution.run import Run, RunId
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel, KnowledgeEntry
from sro.domain.observation.batch import ObservationBatch
from sro.domain.observation.candidate import CandidateStatus, TaskCandidate
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.gesture import Gesture, GestureBatch, Intent
from sro.domain.observation.identity import ShapeKey
from sro.domain.observation.mining import MiningPass
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
from sro.domain.shared.prices import DaySpend
from sro.domain.skill.offers import Offer, OfferRow
from sro.domain.skill.skill import Skill
from sro.domain.skill.workflow import Workflow
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

    async def in_flight(self, tenant_id: TenantId, device_id: DeviceId) -> str | None:
        """The skill run already driving this browser, if one is.

        The same question `WorkflowRunRepository.in_flight` answers for the rig,
        and the skill path had neither this nor the index behind it: two
        triggers firing at one device in the same minute both started, and
        their clicks interleaved in one window.

        The read names the run so a person can be told which one has the
        browser. `uq_runs_one_running_per_device` is what actually refuses the
        second claim -- there are awaits between this and the commit.
        """
        ...

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

    async def revoke(self, tenant_id: TenantId, device_id: DeviceId, *, at: str) -> bool:
        """Whether there was a live browser to revoke.

        The secret is left alone rather than blanked: a device with no secret
        cannot be told from one registered before secrets existed, and this has
        to say *when* the authority ended as well as that it did. ``False`` for
        a browser already revoked, so a second press does not move that instant;
        ``NotFound`` for one this tenant does not have, which is a different
        answer and a different status code.
        """
        ...

    async def restore(self, tenant_id: TenantId, device_id: DeviceId) -> bool:
        """Give a revoked browser its authority back. ``True`` when one had
        been taken away, ``False`` when it was never revoked.

        Exists because revocation started enforcing. While ``revoked_at``
        changed no answer, a wrong press was cosmetic; now `refuse_unless_itself`
        refuses the browser on every device-scoped path, and registration is
        deliberately idempotent and hands back the same secret -- so
        re-registering does NOT undo it, and without this the only way back is
        a hand-edited row. ``NotFound`` for a browser this tenant does not
        have, as `revoke` gives.

        The secret is untouched: the browser still holds a working one, which
        is the whole reason it needs no reinstall.
        """
        ...

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[AgentDevice, ...]:
        """Every browser registered or revoked at or after this ISO instant,
        newest registration first.

        The audit's only answer to "who could act, and from when to when":
        ``revoked_at`` is the fact the runs and the offers cannot carry, so a
        browser registered last month and revoked this morning belongs in this
        morning's audit as much as one registered in it.
        """
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

    async def received_before(
        self, tenant_id: TenantId, cutoff: datetime
    ) -> tuple[ObservationBatch, ...]:
        """Batches this deployment RECEIVED before an instant, oldest first.

        What retention is counted on, and the reason it is not `between`: the
        window a tenant declares is "how long we keep what you send us", and
        the only clock that can answer it is the one that took delivery.
        `started_at` is the browser's, and on this store it runs up to 23 hours
        from `received_at` -- an offline extension flushing a queue, or simply
        a machine whose clock is wrong. Counted on that, a batch that arrived
        this morning can be a day old on arrival and be swept the same day.
        """
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

    async def remember(
        self,
        tenant_id: TenantId,
        key: str,
        *,
        tool: str,
        at: datetime,
        stale_after: timedelta | None = None,
    ) -> bool:
        """Claim this key. ``False`` when somebody already claimed it.

        Written *before* the call, and kept whatever the call answers. A key
        released on failure would let a timeout -- the one case where the send
        may well have landed -- be retried into a second send, which is the
        exact thing this exists to prevent. So a retry is refused and somebody
        is told the call may already have happened, which is the truth.

        `stale_after` is for a key that is not unique to one attempt. A
        connector call is keyed by run and step and is claimed forever; a rig
        step's write is keyed by the JOB, the step and the values, so that two
        runs of one job started three minutes apart cannot both create the
        record -- and a key like that must expire, or a job could never be done
        twice with the same values for the rest of the tenant's life. A claim
        older than `stale_after` is taken over rather than refused.
        """
        ...

    async def forget(self, tenant_id: TenantId, key: str) -> None:
        """Give a claim back, for the one case where nothing was sent.

        The rule above is that a claim is KEPT whatever the call answers, and
        it names the reason: a timeout may well have landed, and releasing it
        would retry a write into a second one. That reasoning is about the
        wire. It does not cover a browser that never reached the wire -- a
        command the extension refused because no tab was open on the system,
        or because the run was aborted, never touched the warehouse, and
        holding its key for half an hour blocks a retry that is entirely safe.

        Found on the live deployment 2026-09-16: a run failed
        `no_tab_for_system` because the operator's Blue Yonder session had
        expired, and every later run of the same job with the same values was
        refused for half an hour on the grounds that the first `may have
        landed`. It could not have.

        Narrow on purpose, and the caller decides: only the kinds that mean the
        extension refused BEFORE acting, never `timeout` and never a failure
        the page itself answered. Idempotent -- a key nobody claimed is a
        no-op, not an error.
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

    async def tenants_since(self, since: datetime) -> tuple[TenantId, ...]:
        """Every tenant whose browsers uploaded in the window.

        Tenant-blind, like `ObservationRepository.tenants_since` and for the
        same reason: the scheduled miner has no request behind it and nobody to
        take a tenant from. Ids only, never a row.

        The rig's own, rather than reusing the observation table's. The two
        answer the same today because one upload writes both, and building the
        rig's autonomy on the table it migrated away from is a trap that only
        springs the day the legacy write stops.

        Measured against the server's clock and not the browser's: a device
        whose clock is wrong would otherwise take its tenant out of every sweep
        or put it in every one.
        """
        ...

    async def save_intent(self, intent: Intent) -> None:
        """Replaces any earlier reading of that gesture."""
        ...

    async def intents_for(self, tenant_id: TenantId) -> tuple[Intent, ...]: ...

    async def intents_since(self, tenant_id: TenantId, *, since: str) -> tuple[Intent, ...]:
        """Every reading stored at or after this ISO instant, newest first.

        ``intents_since`` rather than a bare ``since``: this port holds two
        kinds of record and names every read after the one it returns. The
        clock is the row's ``created_at``, which is when the reading was
        stored rather than when the gesture happened -- the same column the
        day's spend is summed over, because it is the reading that was billed.
        """
        ...

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

    Not every read here takes a tenant. ``approve`` and ``fail_orphans`` are
    deliberately tenant-blind and say why below; ``approvals`` does not, and
    nor do the five workflow-scoped methods on ``WorkflowRepository``
    (``mark_stale``, ``clear_stale``, ``stale_count``, ``record_effect``,
    ``forget_effects``). Those six are safe only because a run or workflow id
    is unguessable and the route has already checked who is asking -- plan 3
    scopes them by workflow ownership, which is where the reason will be
    written down.
    """

    async def save(self, run: WorkflowRun) -> None:
        """Whole run, every time: called after every step so the panel can
        poll, with steps replaced rather than appended."""
        ...

    async def get(self, tenant_id: TenantId, run_id: str) -> WorkflowRun | None:
        """``None``, not ``NotFound``: every caller answers 404 itself."""
        ...

    async def for_workflow(self, tenant_id: TenantId, workflow_id: str) -> tuple[WorkflowRun, ...]:
        """Every run of one job, oldest first -- which is NOT how the rig
        listed them.

        The rig's ``GET /v1/runs`` was ``ORDER BY started_at DESC LIMIT ?``:
        the most recent runs, newest first. That is a list for a person to
        pick from, and it is ``recent`` below.

        This is the evidence order. What reads it is ``proofs`` -- the store's
        own query orders ``(started_at, id)`` ascending and the fake reaches
        this method to get the same -- and a job's writes are read forward,
        because the question is how this job has settled over time and the
        answer to it runs in the direction time does. Unbounded for the same
        reason: proof is not a page.

        Total, and the id is what makes it so: two runs of one workflow
        routinely start in the same instant -- one form submits them -- and an
        order that is not total is an order that changes between reads.
        """
        ...

    async def recent(
        self,
        tenant_id: TenantId,
        *,
        limit: int,
        workflow_id: str | None = None,
        ids: frozenset[str] | None = None,
    ) -> tuple[WorkflowRun, ...]:
        """The most recent runs, newest first, capped: the rig's own list
        query (``api.py:1152``), filters and all.

        ``workflow_id`` narrows to one job and ``ids`` to a named set --
        which is how ``awaiting=true`` is served, because the parked runs are
        a set of ids that comes from ``awaiting`` below. An empty ``ids`` is
        not the same as ``None``: it means nothing can match, said here so no
        caller has to branch on it -- the rig had to, because ``id IN ()`` with
        no ids to interpolate was a syntax error where it ran.

        The cap is in the query and not in the caller. Filtering or slicing a
        tenant's whole run history in Python is the defect ``tallies`` exists
        to have removed once already: it is linear in rows nobody asked for,
        and it degrades exactly as a customer succeeds.

        It caps the ROWS, though, and not ``ids``. A caller passing a set
        interpolates all of it, and the honest bound on that set is whatever
        the caller's own read returns -- see ``ListWorkflowRuns``, which says
        what bounds its one.

        Total, reversed, and for ``for_workflow``'s reason -- ``(started_at,
        id)`` descending, so a page boundary falls in the same place twice.
        """
        ...

    async def failures(self, tenant_id: TenantId) -> Mapping[str, int]:
        """How many runs of each job ended in the job's OWN failure.

        `failed` and `refused` only. A run that stopped to ask a person did not
        fail -- it asked -- and one a person aborted is a person changing their
        mind. Counting either as a failure silenced every job this deployment
        has: twelve runs of the sign-in job, eleven of them stopped on a
        password it was waiting for, and the job vanished from the browser that
        was trying to finish it.
        """
        ...

    async def tallies(self, tenant_id: TenantId) -> Mapping[str, tuple[int, int]]:
        """``(runs, held)`` for every workflow of this tenant that has been
        run, in one ``GROUP BY``.

        What ``shapes_for`` gates on, and the only reason it is a batch: the
        gate needs two integers per workflow, and asking ``for_workflow`` per
        proven workflow loads every run ever recorded with all of its steps to
        compute them. Counted against real Postgres, three workflows of four
        runs: ``shapes_for`` issued 14 statements, 6 against the runs tables;
        with this it issues 9 and 1. The 6 were linear in total run rows, on
        the read every browser makes on every gesture cache miss. The rig read
        the same two numbers off the runs index and this is that, batched
        across the tenant instead of asked per workflow.

        A workflow with no runs is ABSENT, not a zero pair. That is the runs
        index answering about itself -- it has no row to count and does not
        know what workflows exist -- and the caller defaults it, which is what
        keeps a job that has never been run servable.
        """
        ...

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[WorkflowRun, ...]:
        """Every run started at or after this ISO instant, newest first, with
        its steps. The spine of the audit: the approvals on each are read
        beside it, through ``approvals``."""
        ...

    async def in_flight(self, tenant_id: TenantId, device_id: DeviceId) -> str | None:
        """The run this browser is already driving, if any.

        One browser, one hand: two runs driving the same window interleave
        their clicks into a form neither of them can then read back.
        """
        ...

    async def awaiting(self, tenant_id: TenantId) -> tuple[tuple[str, int, str], ...]:
        """(run id, step ord, what the step says) for every step waiting on a
        person, across browsers: anyone may answer a parked run.

        A stated divergence from the rig, not an accident: the rig reported the
        deepest parked step of each run and this returns every one of them,
        ``ord`` ascending. Plan 4b decided it that way and kept it -- anyone
        may answer a parked run, and a queue that hides all but the deepest
        step hides work from the person who could clear it. ``GET
        /v1/workflow-runs`` serves the same rule from the other end: it
        answers with whole rows, so every parked step is on the wire and no
        reader has to ask a second time which of them are waiting.
        """
        ...

    async def waiting_on(
        self, tenant_id: TenantId, *, server: str, thread: str
    ) -> WorkflowRun | None:
        """The run that ended waiting to hear back on this outside conversation.

        Newest first, because a thread somebody asks about twice has two runs
        against it and the live question is the last one asked. Whether the
        wait is still open is the caller's to decide -- `still_waiting` reads
        the deadline -- because "nobody is holding this open any more" is a
        different sentence from "nobody ever asked about this", and a caller
        told `None` for both cannot say either.
        """
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


class WorkflowRepository(Protocol):
    """What a mining pass found, and what running it has since earned.

    Four things behind one port because they are one lifecycle: a pass proposes
    a workflow, its steps cite the evidence, a run notices a step going weak,
    and a verified write is registered against the job it was a step of.
    """

    async def save(self, workflow: Workflow) -> None:
        """Whole workflow, steps replaced rather than appended.

        Identity resolution re-saves a workflow it merged evidence into, so a
        step the merge dropped has to leave the store with it.
        """
        ...

    async def known(self, tenant_id: TenantId) -> tuple[Workflow, ...]:
        """Oldest first, which is the order the miner resolves against."""
        ...

    async def get(self, tenant_id: TenantId, workflow_id: str) -> Workflow: ...

    async def rekey(self, tenant_id: TenantId, workflow_id: str, key: ShapeKey) -> None:
        """Replace the shape identity resolution compares proposals against.

        Run once at startup, when the rule that makes a key has changed: keys
        mined before the change no longer match keys mined after, and a job
        already held could be proposed again as a new one.
        """
        ...

    async def add_pass(self, mining_pass: MiningPass) -> None:
        """One row per reading of a tenant's day, found anything or not.

        A refused call is the case that matters: it is then the only record
        left of a call that cost money and returned nothing.

        Raises ``Conflict`` when that pass id is already stored. An id is
        minted per reading, so a second row under one id is one model call
        billed twice.
        """
        ...

    async def passes(self, tenant_id: TenantId) -> tuple[MiningPass, ...]:
        """Every pass this tenant has been billed for, oldest first."""
        ...

    async def mark_stale(
        self, workflow_id: str, ord_: int, *, matched_by: str | None, noticed_at: str
    ) -> None:
        """A step only the weakest rung of the locator ladder found.

        One row per step, so a job run every morning reports the same weak step
        once rather than daily. Not written onto the workflow itself: that is
        what a mining pass writes and this is what a run learned, and one
        rewriting the other would race a re-mine.
        """
        ...

    async def remember_locator(
        self, workflow_id: str, learned: LearnedStep, *, by_run: str = ""
    ) -> None:
        """What a run found when the job's own identity for a control did not.

        `mark_stale` above says a step is about to break; this says what the
        run FOUND, so the next one tries it first rather than climbing the same
        ladder and paying for the same model call. One row per step, the last
        answer winning.
        """
        ...

    async def learned_for(self, workflow_id: str) -> tuple[LearnedStep, ...]:
        """Every step of this job that a run has found a working locator for."""
        ...

    async def taught_itself(self, workflow_id: str, limit: int = 50) -> tuple[Taught, ...]:
        """What this job has changed its mind about, newest first.

        The reviewable half of learning. `remember_locator` and
        `remember_limit` store the CURRENT answer and overwrite what was there,
        which is right for the run asking what to try first and leaves a job
        rewriting its own behaviour with nothing behind it.

        Bounded, and small: a history nobody can read in one page is a log.
        """
        ...

    async def remember_limit(
        self, workflow_id: str, ord_: int, holds: int, *, by_run: str = ""
    ) -> None:
        """How many characters this step's box turned out to take.

        Learnt on a step whose locator matched perfectly well, which is why it
        is not part of `remember_locator`: writing the two together would have
        a truncation erase a locator, or a locator erase a limit."""
        ...

    async def clear_stale(self, workflow_id: str, ord_: int) -> None:
        """The step matched properly again. A warning that never clears is a
        warning nobody reads. Idempotent: clearing a step that was never weak
        is not an error."""
        ...

    async def stale_count(self, workflow_id: str) -> int:
        """How many of this job's steps are about to break."""
        ...

    async def record_effect(
        self, workflow_id: str, *, run_id: str, ord_: int, verified_by: str, at: str
    ) -> None:
        """Register a write the verifier saw hold by state.

        A verdict that is not a state belt is dropped rather than stored: a
        model reading a screenshot is not evidence anything was written. One
        write of one run is one row however many times it is verified.
        """
        ...

    async def forget_effects(self, workflow_id: str) -> int:
        """How many were forgotten. One failed write empties the register."""
        ...

    async def proofs(self, tenant_id: TenantId, workflow_id: str) -> tuple[RunProof, ...]:
        """One per live run of this workflow that held, for ``earned_from``.

        The steps that wrote come off each step's own ``wrote`` marker, which
        the runner set at send time: SQL cannot ask ``writes()``, and the
        evidence a later reader would have to ask it about may have been
        re-mined by then.
        """
        ...


class OfferRepository(Protocol):
    """What the extension offered, and what became of it.

    Three reads and one write, because the two windows are one query with one
    predicate between them and the tally is a different question entirely.
    """

    async def record(self, offer: Offer) -> None:
        """One offer, one row. The id is minted where the offer is made."""
        ...

    async def newest(
        self, tenant_id: TenantId, workflow_id: str, *, limit: int
    ) -> tuple[OfferRow, ...]:
        """Newest first, ``at`` then arrival -- the window ``counsel_over``
        reads. Nudges (``k = 0``) are excluded: an arrival is not evidence
        either way. Every browser's offers count, because recognition is a
        property of the job rather than of who was asked."""
        ...

    async def newest_for_device(
        self, tenant_id: TenantId, workflow_id: str, device_id: DeviceId, *, limit: int
    ) -> tuple[OfferRow, ...]:
        """The same window, one browser's. Resting is per browser: one
        operator's no is not the next operator's."""
        ...

    async def fates(self, tenant_id: TenantId, workflow_id: str) -> Mapping[str, int]:
        """How many of this job's offers ended each way, nudges included.

        The panel's tally rather than the counsel's window, so neither the
        ``k > 0`` filter nor the limit applies: an arrival nudge is still an
        offer that was made.
        """
        ...

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[Offer, ...]:
        """Every offer made at or after this ISO instant, newest first, whole.

        The audit's question, not the counsel's: no ``k > 0`` and no limit,
        because an arrival nudge is still something this tenant's browsers were
        shown. Ties on ``at`` break on arrival, as everywhere else here.
        """
        ...


class ChatRepository(Protocol):
    """What the chat door read, and what the reading cost.

    Never the sentence. There is no column for it and no method that would
    write one: the row exists for the cap and the spend line, and neither needs
    an operator's words about their own warehouse.
    """

    async def record(self, reading: ChatReading) -> None: ...

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[ChatReading, ...]:
        """Every reading at or after this ISO instant, newest first. The day's
        spend is the sum over it, which is why the index leads with the
        tenant."""
        ...


class SpendRepository(Protocol):
    """What today has cost, across every table that can bill it."""

    async def today(self, tenant_id: TenantId, *, now: datetime) -> DaySpend:
        """Everything this tenant has been billed for since midnight UTC.

        Four tables, one predicate each: a reading, a mining pass, a run and
        a chat are the only things that cost money, and a cap that reads
        three of them is a cap.

        ``now`` is passed rather than read here so the caller's clock is the
        one the day is measured from; midnight is UTC's either way, and a
        ``now`` with no zone is read as UTC rather than as the server's local
        time.
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
    workflows: WorkflowRepository
    offers: OfferRepository
    chats: ChatRepository
    spend: SpendRepository
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
