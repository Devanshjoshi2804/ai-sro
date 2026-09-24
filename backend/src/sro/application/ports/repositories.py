from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Protocol

from sro.domain.chat.reading import ChatReading
from sro.domain.chat.thread import Thread, ThreadId
from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.execution.account import Account, Lease, LeaseState
from sro.domain.execution.belts import RunProof
from sro.domain.execution.learned_step import LearnedStep, Taught
from sro.domain.execution.model_call import ModelCall
from sro.domain.execution.run import Run, RunId
from sro.domain.execution.verified_writes import VerifiedWrite
from sro.domain.execution.workflow_run import WorkflowRun
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel, KnowledgeEntry
from sro.domain.observation.attempts import Attempt
from sro.domain.observation.batch import ObservationBatch
from sro.domain.observation.candidate import CandidateStatus, TaskCandidate
from sro.domain.observation.device import AgentDevice
from sro.domain.observation.driving import Driving, Uploaded
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
from sro.domain.shared.prices import DaySpend, ModelSpend
from sro.domain.skill.offers import Offer, OfferRow
from sro.domain.skill.skill import Skill
from sro.domain.skill.workflow import Noticed, Workflow
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
    ) -> tuple[Recording, ...]: ...

    async def list_capturing(self) -> tuple[Recording, ...]: ...


class SkillRepository(Protocol):
    async def add(self, skill: Skill) -> None: ...

    async def get(self, tenant_id: TenantId, skill_id: SkillId) -> Skill: ...

    async def save(self, skill: Skill) -> None: ...

    async def find_by_objective(
        self, tenant_id: TenantId, objective_key: ObjectiveKey
    ) -> Skill | None: ...

    async def list_for_tenant(
        self, tenant_id: TenantId, *, limit: int = 50, offset: int = 0
    ) -> tuple[Skill, ...]: ...


class ConnectionRepository(Protocol):
    async def add(self, connection: Connection) -> None: ...

    async def get(self, tenant_id: TenantId, connection_id: ConnectionId) -> Connection: ...

    async def save(self, connection: Connection) -> None: ...

    async def find_by_system(
        self, tenant_id: TenantId, target_system: str
    ) -> Connection | None: ...

    async def list_for_tenant(self, tenant_id: TenantId) -> tuple[Connection, ...]: ...

    async def list_connected(self) -> tuple[Connection, ...]: ...


class RunRepository(Protocol):
    async def add(self, run: Run) -> None: ...

    async def get(self, tenant_id: TenantId, run_id: RunId) -> Run: ...

    async def in_flight(self, tenant_id: TenantId, device_id: DeviceId) -> str | None: ...

    async def save(self, run: Run) -> None: ...

    async def list_for_tenant(
        self,
        tenant_id: TenantId,
        *,
        skill_id: SkillId | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Run, ...]: ...

    async def finished_since(
        self, tenant_id: TenantId, *, target_system: str, since: datetime
    ) -> tuple[Run, ...]: ...

    async def since(self, tenant_id: TenantId, *, since: datetime) -> tuple[Run, ...]: ...


class KnowledgeRepository(Protocol):
    async def add(self, entry: KnowledgeEntry) -> None: ...

    async def current(
        self, tenant_id: TenantId, *, system: str, kind: EntryKind, key: str
    ) -> KnowledgeEntry | None: ...

    async def save(self, entry: KnowledgeEntry) -> None: ...

    async def history(
        self, tenant_id: TenantId, *, system: str, kind: EntryKind, key: str, limit: int = 10
    ) -> tuple[KnowledgeEntry, ...]: ...

    async def without_embedding(
        self, tenant_id: TenantId, *, limit: int = 200
    ) -> tuple[KnowledgeEntry, ...]: ...

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
    ) -> tuple[KnowledgeEntry, ...]: ...


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
    ) -> tuple[Thread, ...]: ...


class ModelCallRepository(Protocol):
    async def add(self, call: ModelCall) -> None: ...

    async def list_for_run(self, tenant_id: TenantId, run_id: RunId) -> tuple[ModelCall, ...]: ...


class BrowserSessionRepository(Protocol):
    async def claim(
        self,
        tenant_id: TenantId,
        session_id: BrowserSessionId,
        opened_by: PrincipalId,
        opened_at: datetime,
    ) -> None: ...

    async def held_by(self, tenant_id: TenantId) -> tuple[BrowserSessionId, ...]: ...

    async def all_held(self) -> tuple[tuple[BrowserSessionId, datetime], ...]: ...

    async def release(self, session_id: BrowserSessionId) -> None: ...

    async def lease(self, tenant_id: TenantId, lease: Lease) -> Lease: ...

    async def current_lease(self, tenant_id: TenantId, account: Account) -> Lease | None: ...

    async def get_lease(self, tenant_id: TenantId, lease_id: str) -> Lease | None: ...

    async def settle(self, tenant_id: TenantId, lease_id: str, *, state: LeaseState) -> None: ...

    async def beat(
        self,
        tenant_id: TenantId,
        lease_id: str,
        *,
        now: datetime,
        holder: str | None = None,
    ) -> None: ...

    async def expired(self, *, now: datetime) -> tuple[Lease, ...]: ...

    async def busy_containers(self, *, now: datetime) -> tuple[str, ...]: ...

    async def leased_sessions(self) -> frozenset[str]: ...


class DeviceRepository(Protocol):
    async def add(self, device: AgentDevice) -> None: ...

    async def get(self, tenant_id: TenantId, device_id: DeviceId) -> AgentDevice: ...

    async def save(self, device: AgentDevice) -> None: ...

    async def registered_as(
        self, tenant_id: TenantId, principal_id: PrincipalId, label: str
    ) -> AgentDevice | None: ...

    async def list_for_tenant(self, tenant_id: TenantId) -> tuple[AgentDevice, ...]: ...

    async def revoke(self, tenant_id: TenantId, device_id: DeviceId, *, at: str) -> bool: ...

    async def restore(self, tenant_id: TenantId, device_id: DeviceId) -> bool: ...

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[AgentDevice, ...]: ...


class ObservationRepository(Protocol):
    async def add(self, batch: ObservationBatch) -> None: ...

    async def get(self, tenant_id: TenantId, batch_id: BatchId) -> ObservationBatch | None: ...

    async def between(
        self,
        tenant_id: TenantId,
        *,
        since: datetime,
        until: datetime | None = None,
        principal_id: PrincipalId | None = None,
    ) -> tuple[ObservationBatch, ...]: ...

    async def received_before(
        self, tenant_id: TenantId, cutoff: datetime
    ) -> tuple[ObservationBatch, ...]: ...

    async def tenants_since(self, since: datetime) -> tuple[TenantId, ...]: ...

    async def forget(self, tenant_id: TenantId, ids: tuple[BatchId, ...]) -> None: ...


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
    ) -> tuple[TaskCandidate, ...]: ...


class ObservationPolicyRepository(Protocol):
    async def get(self, tenant_id: TenantId) -> ObservationPolicy | None: ...

    async def save(self, tenant_id: TenantId, policy: ObservationPolicy) -> None: ...


class TriggerRepository(Protocol):
    async def add(self, trigger: Trigger) -> None: ...

    async def get(self, tenant_id: TenantId, trigger_id: TriggerId) -> Trigger: ...

    async def save(self, trigger: Trigger) -> None: ...

    async def remove(self, tenant_id: TenantId, trigger_id: TriggerId) -> None: ...

    async def list_for_tenant(
        self, tenant_id: TenantId, *, skill_id: SkillId | None = None
    ) -> tuple[Trigger, ...]: ...

    async def find(self, trigger_id: TriggerId) -> Trigger | None: ...


class ConfirmationRepository(Protocol):
    async def add(self, confirmation: Confirmation) -> None: ...

    async def get(self, tenant_id: TenantId, confirmation_id: ConfirmationId) -> Confirmation: ...

    async def save(self, confirmation: Confirmation) -> None: ...

    async def waiting(self, tenant_id: TenantId) -> tuple[Confirmation, ...]: ...

    async def tenants_waiting(self) -> tuple[TenantId, ...]: ...


class ToolCallRepository(Protocol):
    async def remember(
        self,
        tenant_id: TenantId,
        key: str,
        *,
        tool: str,
        at: datetime,
        stale_after: timedelta | None = None,
    ) -> bool: ...

    async def forget(self, tenant_id: TenantId, key: str) -> None: ...


class GestureRepository(Protocol):
    async def add_batch(self, batch: GestureBatch) -> None: ...

    async def add_gestures(self, gestures: tuple[Gesture, ...]) -> None: ...

    async def gestures_for(
        self,
        tenant_id: TenantId,
        *,
        ids: tuple[str, ...] | None = None,
        after: float | None = None,
        before: float | None = None,
    ) -> tuple[Gesture, ...]: ...

    async def uploads_for(
        self, tenant_id: TenantId, batch_ids: tuple[str, ...]
    ) -> Mapping[str, Uploaded]: ...

    async def unread(self, tenant_id: TenantId, *, limit: int) -> tuple[Gesture, ...]: ...

    async def newest_arrival(self, tenant_id: TenantId) -> datetime | None: ...

    async def tenants_since(self, since: datetime) -> tuple[TenantId, ...]: ...

    async def save_intent(self, intent: Intent) -> None: ...

    async def intents_for(self, tenant_id: TenantId) -> tuple[Intent, ...]: ...

    async def intents_since(self, tenant_id: TenantId, *, since: str) -> tuple[Intent, ...]: ...

    async def add_orphan_request(
        self,
        tenant_id: TenantId,
        *,
        batch_id: str,
        request_id: str,
        payload: Mapping[str, object],
    ) -> None: ...

    async def add_orphan_page(
        self, tenant_id: TenantId, *, batch_id: str, at: str, payload: Mapping[str, object]
    ) -> None: ...

    async def batch_owner(self, batch_id: str) -> str | None: ...

    async def count(self, tenant_id: TenantId) -> int: ...

    async def streams(self, tenant_id: TenantId) -> tuple[tuple[str, float, int], ...]: ...


class PoolRepository(Protocol):
    async def add_unclaimed(
        self, tenant_id: TenantId, *, window_ids: tuple[str, ...], claimed: frozenset[str]
    ) -> int: ...

    async def age(self, tenant_id: TenantId, *, shown: tuple[str, ...] | None = None) -> int: ...

    async def waiting(self, tenant_id: TenantId) -> tuple[PoolEntry, ...]: ...

    async def ids(self, tenant_id: TenantId) -> tuple[str, ...]: ...

    async def retired(self, tenant_id: TenantId) -> tuple[PoolEntry, ...]: ...


class WorkflowRunRepository(Protocol):
    async def save(self, run: WorkflowRun) -> None: ...

    async def get(self, tenant_id: TenantId, run_id: str) -> WorkflowRun | None: ...

    async def for_workflow(
        self, tenant_id: TenantId, workflow_id: str
    ) -> tuple[WorkflowRun, ...]: ...

    async def recent(
        self,
        tenant_id: TenantId,
        *,
        limit: int,
        workflow_id: str | None = None,
        ids: frozenset[str] | None = None,
    ) -> tuple[WorkflowRun, ...]: ...

    async def taken_back_by(self, tenant_id: TenantId, run_id: str) -> str | None: ...

    async def failures(self, tenant_id: TenantId) -> Mapping[str, int]: ...

    async def tallies(self, tenant_id: TenantId) -> Mapping[str, tuple[int, int]]: ...

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[WorkflowRun, ...]: ...

    async def outcomes_since(
        self, tenant_id: TenantId, *, since: str
    ) -> tuple[tuple[str, bool, int], ...]: ...

    async def driving_windows(self, tenant_id: TenantId) -> tuple[Driving, ...]: ...

    async def in_flight(self, tenant_id: TenantId, device_id: DeviceId) -> str | None: ...

    async def awaiting(self, tenant_id: TenantId) -> tuple[tuple[str, int, str], ...]: ...

    async def waiting_on(
        self, tenant_id: TenantId, *, server: str, thread: str
    ) -> WorkflowRun | None: ...

    async def approve(self, run_id: str, ord_: int, *, at: str, device_id: str | None) -> bool: ...

    async def approvals(self, run_id: str) -> tuple[tuple[int, str, str | None], ...]: ...

    async def fail_orphans(self, reason: str) -> int: ...


class WorkflowRepository(Protocol):
    async def save(self, workflow: Workflow) -> None: ...

    async def known(self, tenant_id: TenantId) -> tuple[Workflow, ...]: ...

    async def noticed_since(
        self, tenant_id: TenantId, *, since: datetime
    ) -> tuple[Noticed, ...]: ...

    async def get(self, tenant_id: TenantId, workflow_id: str) -> Workflow: ...

    async def retire(self, tenant_id: TenantId, workflow_id: str, *, at: datetime) -> None: ...

    async def place(
        self, tenant_id: TenantId, workflow_id: str, gesture_ids: tuple[str, ...]
    ) -> None: ...

    async def placed(self, tenant_id: TenantId) -> frozenset[str]: ...

    async def rekey(self, tenant_id: TenantId, workflow_id: str, key: ShapeKey) -> None: ...

    async def add_pass(self, mining_pass: MiningPass) -> None: ...

    async def passes(self, tenant_id: TenantId) -> tuple[MiningPass, ...]: ...

    async def mark_stale(
        self, workflow_id: str, ord_: int, *, matched_by: str | None, noticed_at: str
    ) -> None: ...

    async def remember_locator(
        self, workflow_id: str, learned: LearnedStep, *, by_run: str = ""
    ) -> None: ...

    async def learned_for(self, workflow_id: str) -> tuple[LearnedStep, ...]: ...

    async def taught_itself(self, workflow_id: str, limit: int = 50) -> tuple[Taught, ...]: ...

    async def remember_limit(
        self, workflow_id: str, ord_: int, holds: int, *, by_run: str = ""
    ) -> None: ...

    async def clear_stale(self, workflow_id: str, ord_: int) -> None: ...

    async def stale_count(self, workflow_id: str) -> int: ...

    async def grew(self, workflow: Workflow, *, moved: Mapping[int, int]) -> None: ...

    async def remember_write(
        self,
        tenant_id: TenantId,
        *,
        method: str,
        path_pattern: str,
        origin: str,
        run_id: str,
        workflow_id: str,
        verified_by: str,
        at: str,
    ) -> None: ...

    async def learned_writes(self, tenant_id: TenantId) -> tuple[VerifiedWrite, ...]: ...

    async def record_effect(
        self, workflow_id: str, *, run_id: str, ord_: int, verified_by: str, at: str
    ) -> None: ...

    async def forget_effects(self, workflow_id: str) -> int: ...

    async def proofs(self, tenant_id: TenantId, workflow_id: str) -> tuple[RunProof, ...]: ...


class AttemptRepository(Protocol):
    async def record(self, attempt: Attempt) -> None: ...

    async def since(
        self, tenant_id: TenantId, *, since: datetime, limit: int
    ) -> tuple[Attempt, ...]: ...


class OfferRepository(Protocol):
    async def record(self, offer: Offer) -> None: ...

    async def newest(
        self, tenant_id: TenantId, workflow_id: str, *, limit: int
    ) -> tuple[OfferRow, ...]: ...

    async def newest_for_device(
        self, tenant_id: TenantId, workflow_id: str, device_id: DeviceId, *, limit: int
    ) -> tuple[OfferRow, ...]: ...

    async def fates(self, tenant_id: TenantId, workflow_id: str) -> Mapping[str, int]: ...

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[Offer, ...]: ...


class ChatRepository(Protocol):
    async def record(self, reading: ChatReading) -> None: ...

    async def since(self, tenant_id: TenantId, *, since: str) -> tuple[ChatReading, ...]: ...


class SpendRepository(Protocol):
    async def record(self, spent: ModelSpend) -> None: ...

    async def today(self, tenant_id: TenantId, *, now: datetime) -> DaySpend: ...


class UnitOfWork(Protocol):
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
    attempts: AttemptRepository
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
