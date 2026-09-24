"""The composition root hands out what the routers ask for.

Thin by design: what is worth holding is that each factory exists, returns the
type its router annotates, and is given the container's own clock, drivers and
unit of work rather than making its own. A use case built with a different
clock is one a test cannot move, and a route that reads a clock is a route with
a rule in it.

Every factory here is a call site nobody else checks. Python will build
``ReadRoster(drivers, uow)`` as happily as ``ReadRoster(uow, drivers)`` and
``shapes_for`` will serve a whole tenant's rest to a browser that earned none
of it if ``device_id`` is dropped on the way in -- so the arguments are
asserted one by one, not merely the types that come back.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import pytest

from sro.application.analytics.audit import ReadAudit
from sro.application.capture.devices import ReadRoster, RestoreDevice, RevokeDevice
from sro.application.context import RequestContext
from sro.application.skill.record_offer import RecordOffer
from sro.application.skill.retire_workflow import RetireWorkflow
from sro.application.skill.serve_shapes import ServeShapes
from sro.container import Container
from sro.domain.shared.identifiers import DeviceId, PrincipalId, TenantId
from sro.domain.skill.workflow import Workflow
from sro.infrastructure.agent.drivers import RemoteAgents
from tests.unit.fakes import FakeAsker, FakeClock, FakeUnitOfWork
from tests.unit.interface.test_http import _FakeContainer

FROZEN = datetime(2026, 3, 4, 9, 30, tzinfo=UTC)
"""Fixed, and deliberately not "today". Both module functions below turn `now`
into a rule -- a shape's rest window, an offer's clamped instant -- so a
fixture dated by the calendar is a suite that passes because of the day it ran.
The gap between this and the wall clock is also what makes the "container read
`datetime.now`" mutation die."""

RIVAL = RequestContext(tenant_id=TenantId("rival"), principal_id=PrincipalId("clerk"))
"""Deliberately not `acme`, which every other fixture in the suite uses: a
use case that read a tenant off a literal instead of off the context would
agree with `acme` by coincidence."""


@pytest.fixture
def uow() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def container(uow: FakeUnitOfWork) -> Container:
    """Production's own factories over in-memory adapters.

    `_FakeContainer` subclasses `Container` and overrides only `unit_of_work`,
    which is exactly what wiring wants tested: the factories under test are the
    ones a deployment runs.
    """
    built = _FakeContainer(uow)
    built.clock = FakeClock(FROZEN)
    return built


def _spy(seen: dict[str, Any], answer: object) -> Callable[..., Awaitable[Any]]:
    """Stands in for a module function and records every argument it was given.

    A spy rather than a real call because the point of these two is the
    argument list: what reaches `now` cannot be read back off a `Shape`, and an
    argument silently swapped with its neighbour is invisible in the answer.
    """

    async def recorder(unit: object, **kwargs: object) -> object:
        seen["uow"] = unit
        seen.update(kwargs)
        return answer

    return recorder


def test_the_container_builds_the_phase_three_use_cases(
    container: Container, uow: FakeUnitOfWork
) -> None:
    roster = container.read_roster()
    revoke = container.revoke_device()
    audit = container.read_audit()

    assert isinstance(roster, ReadRoster)
    assert isinstance(revoke, RevokeDevice)
    assert isinstance(audit, ReadAudit)

    # The caller seam. `uow` and `drivers` are adjacent positional parameters
    # of two of these, so a swap builds cleanly and only fails in production.
    assert roster._uow is uow
    assert revoke._uow is uow
    assert audit._uow is uow
    # The type is not the seam; the socket registry is. A container that built
    # `RemoteAgents(DeviceSockets())` -- a driver over a fresh, empty registry
    # nobody else ever writes to -- is a `RemoteAgents` and passes an isinstance
    # check, and it breaks exactly the two things these use cases exist to
    # promise: every browser on the roster reads `online=False`, and a revoked
    # browser KEEPS ITS COMMAND CHANNEL because `drop` is a silent no-op. Both
    # survived the whole 2193-test suite until this line.
    # The isinstance is the narrowing that lets the next line be typed, not the
    # assertion: `AgentDrivers` is a Protocol and has no registry on it.
    assert isinstance(roster._drivers, RemoteAgents)
    assert isinstance(revoke._drivers, RemoteAgents)
    assert roster._drivers._sockets is container.agent_sockets
    assert revoke._drivers._sockets is container.agent_sockets
    # Not merely "a clock": the container's own, or a revocation is stamped
    # with an instant no test can move.
    assert revoke._clock is container.clock

    # The un-revoke, which is built from the unit of work alone. A container
    # that handed it `self.agents()` too would be the first step towards a
    # restore that dialled a laptop nobody is sitting at.
    restore = container.restore_device()
    assert isinstance(restore, RestoreDevice)
    # Everything it holds, not "it holds no attribute spelled `_drivers`":
    # `self._agents = self.agents()` would satisfy a spelling check and dial a
    # laptop nobody is sitting at on every press.
    assert vars(restore) == {"_uow": uow}


def test_a_deployment_reads_each_gesture_against_nothing_by_default(
    container: Container,
) -> None:
    """The tail is off, and the setting is what turns it back on.

    Two halves, and the suite was green without either. `Settings` decides the
    number -- the tail was carried to decide `continues`, which nothing reads,
    and measured against hand-labelled ground truth it bought two body fields
    out of 111 for 15.6% of the bill and the serial order itself. And the
    container has to actually hand it over: defaulted away here, every
    deployment would quietly go on paying for eight.
    """
    assert container.settings.gemini_read_tail == 0
    assert container.read_gestures()._tail_size == 0

    container.settings.gemini_read_tail = 8
    assert container.read_gestures()._tail_size == 8


def test_a_deployment_reads_a_group_of_gestures_at_a_time(container: Container) -> None:
    """And the container has to hand the width over too.

    Same failure as the tail's: `read_new_gestures` defaults `at_once` to 1,
    so a composition root that forgets this argument is a deployment that
    reads one gesture at a time for ever, with nothing red anywhere and the
    setting sitting in `Settings` looking configured.
    """
    assert container.settings.gemini_read_at_once == 8
    assert container.read_gestures()._at_once == 8

    container.settings.gemini_read_at_once = 3
    assert container.read_gestures()._at_once == 3


def test_the_container_builds_serve_shapes_from_its_own_parts(
    container: Container, uow: FakeUnitOfWork
) -> None:
    served = container.serve_shapes()

    assert isinstance(served, ServeShapes)
    # The whole of what it was built from, not merely that the two it needs are
    # right. `restore_device` three factories above guards the same thing with
    # `not hasattr(..., "_drivers")`; this is that assertion in the form a
    # renamed parameter cannot walk past. `ServeShapes` is the every-page poll,
    # and a container that handed it `self.agents()` would put a socket
    # registry behind the one read a browser makes on every gesture cache miss.
    #
    # `_clock` by identity and not merely "a clock", which is also why this is a
    # factory rather than a `ServeShapes()` a route could build: a use case
    # holding a clock of its own rests every job by the wall calendar, and no
    # test can move that.
    assert vars(served) == {"_uow": uow, "_clock": container.clock}


async def test_serve_shapes_is_asked_with_the_asking_browser_and_the_containers_clock(
    container: Container, uow: FakeUnitOfWork, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, Any] = {}
    monkeypatch.setattr("sro.application.skill.serve_shapes.shapes_for", _spy(seen, []))

    assert await container.serve_shapes().execute(RIVAL, device_id=DeviceId("dev_7")) == []

    assert seen["uow"] is uow
    # Off the context and never a literal: this is the seam where serving the
    # wrong tenant is one substitution away, so the tenant asserted here is
    # deliberately not the one every other fixture in the suite uses.
    assert seen["tenant_id"] == TenantId("rival")
    # The one that matters most: `device_id` decides whose refusals earned the
    # rest, so dropping it serves one browser the rest another browser earned.
    assert seen["device_id"] == DeviceId("dev_7")
    assert seen["now"] == FROZEN


async def test_serve_shapes_reaches_the_real_function_and_commits_nothing(
    container: Container, uow: FakeUnitOfWork
) -> None:
    """No spy: the import is real and a tenant with nothing proven gets [].

    Also the shape of a request no browser proved itself for -- `device_id` is
    allowed to be `None` and the tenant is answered anyway.

    And the promise `shapes_for` makes in its own docstring and nothing has
    ever held it to: "nothing writes, so nothing commits -- the caller owns the
    session". This is the read every browser makes on every gesture cache miss,
    answered inside a request that may be holding writes nobody has finished, so
    a commit here flushes somebody else's half-done work.
    """
    assert await container.serve_shapes().execute(RIVAL, device_id=None) == []

    assert uow.commits == 0


def test_the_container_builds_record_offer_from_its_own_parts(
    container: Container, uow: FakeUnitOfWork
) -> None:
    """The write door of phase 4a, and a factory rather than the container
    method it replaces: that one took a bare `tenant_id`, so the route would
    have unpacked the caller itself at the one seam where passing the wrong
    tenant is the failure.

    `vars` and not two `is` checks, for `serve_shapes`' reason above: a
    renamed parameter walks past a spelling check, and a `RecordOffer` built
    over a unit of work nobody else writes to records offers into a session
    that is never read.
    """
    recording = container.record_offer()

    assert isinstance(recording, RecordOffer)
    # `_clock` by identity: `clamped` holds the browser's reading against this
    # one, and a use case that read a clock of its own is one no test can move.
    assert vars(recording) == {"_uow": uow, "_clock": container.clock}


async def test_record_offer_clamps_the_browsers_clock_against_the_containers(
    container: Container, uow: FakeUnitOfWork
) -> None:
    """No spy, and the rule the clock buys: a browser ten months fast would
    otherwise own the rest window until 2027. The row carries ours.

    Asked as `rival`, and the job is `rival`'s: the tenant the row is written
    under comes off the context, and a use case reading a literal `acme`
    refuses this as an unknown workflow instead.
    """
    await uow.workflows.save(
        Workflow(id="wf_1", tenant="rival", title="a job of theirs", narrative="")
    )

    stored = await container.record_offer().execute(
        RIVAL,
        workflow_id="wf_1",
        device_id=DeviceId("dev_7"),
        k=3,
        fate="dismissed",
        run_id=None,
        at="2027-01-01T00:00:00+00:00",
    )

    assert stored.at == FROZEN.isoformat()
    assert stored.tenant == "rival"
    # And it is the row the store kept, not only the object handed back: this
    # is the window `counsel` reads to decide a job has earned a rest.
    window = await uow.offers.newest(TenantId("rival"), "wf_1", limit=5)
    assert [row.at for row in window] == [FROZEN.isoformat()]


def test_a_deployment_with_a_key_gets_a_model_for_the_rigs_own_passes() -> None:
    """The miner and the runner ask a model, and until this existed nothing
    built one: the port and `GeminiAsker` were ported by plan 2 and the
    composition root was never told about either, so `mining_pass.mine` and
    `run_workflow` could not be constructed at all -- an `AttributeError` on
    `container.asker` before a single call was made. Found by running the real
    thing, not by this suite.
    """
    from sro.config import Settings
    from sro.container import _build_asker
    from sro.infrastructure.gemini.asker import GeminiAsker

    with_key = Settings(gemini_api_key="k", interpretation_enabled=True, _env_file=None)
    assert isinstance(_build_asker(with_key, _meter()), GeminiAsker)


def test_no_key_and_no_consent_each_mean_no_model() -> None:
    """The same two switches its neighbours keep, and `None` rather than a
    no-op: a miner with nothing to ask must refuse rather than quietly find
    nothing, which reads exactly like a day with no work in it."""
    from sro.config import Settings
    from sro.container import _build_asker

    assert (
        _build_asker(
            Settings(gemini_api_key="", interpretation_enabled=True, _env_file=None), _meter()
        )
        is None
    )
    assert (
        _build_asker(
            Settings(gemini_api_key="k", interpretation_enabled=False, _env_file=None), _meter()
        )
        is None
    )


def test_no_asker_refuses_rather_than_handing_back_none() -> None:
    """`container.asker` is `Asker | None` and three callers need an `Asker`.
    Returning None to them means the refusal happens somewhere downstream, in
    the middle of a pass, after the window has been packed."""
    from sro.application.ports.model import AskerUnavailable, asker_or_refuse

    # `match=` and not a bare raises: the sentence IS the refusal. An operator
    # who gets this 503 has two settings to go and set, and a message that
    # named neither would leave them with a working system and no next step.
    with pytest.raises(AskerUnavailable, match="gemini_api_key") as raised:
        asker_or_refuse(None)
    assert "interpretation_enabled" in str(raised.value)


def test_every_door_that_needs_a_model_refuses_through_the_one_guard() -> None:
    """The count `container.py` used to keep in prose, kept where it rots loudly.

    That docstring said two of 4b's three doors read `asker_or_refuse` and that
    the sentence "goes present-tense when task 5 lands and not before". Task 5
    landed; the sentence did not move. A comment naming a grep result is a
    trip-wire nobody trips -- so this is the grep, and it fails on the commit
    that adds a caller rather than on the commit that reads the comment.

    Asserted as an exact set and not a count: a caller that MOVES from one
    module to another leaves the number alone, and which door refuses is the
    fact worth pinning. A new door that asks a model belongs on this list; a
    new door that asks a model and is NOT on it is refusing somewhere else, or
    not refusing at all.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "src"
    callers = {
        module.relative_to(root).as_posix()
        for module in root.rglob("*.py")
        if "asker_or_refuse(" in module.read_text()
    }

    assert callers == {
        # Where the guard itself lives.
        "sro/application/ports/model.py",
        # The rig miner's pass.
        "sro/application/observation/mine_pass.py",
        # The rig miner's reading of each gesture.
        "sro/application/observation/read_gesture.py",
        # POST /v1/chat
        "sro/application/chat/read_chat.py",
        # POST /v1/chat/from-the-mail -- one reading per mail it looks at.
        "sro/application/chat/from_the_mail.py",
        # POST /v1/workflow-runs -- both the press and the rescue path.
        "sro/application/execution/workflow_runs.py",
        # Planning where to look for the answer to a question. No route yet:
        # the plan is built and read before anything executes it, and the seam
        # that runs one is the next slice.
        "sro/application/lookup/plan_lookups.py",
        # The tool lane's mail hand -- writing the mail a mailbox step sends.
        "sro/container.py",
    }


def test_an_asker_is_handed_back_as_that_exact_object() -> None:
    """Not 'an Asker' -- that one. A guard that built a second one would bill
    against a client the spend tests never see."""
    from sro.application.ports.model import asker_or_refuse

    asker = FakeAsker()

    assert asker_or_refuse(asker) is asker


async def test_a_container_with_no_model_still_builds_every_factory(
    container: Container,
) -> None:
    """The reason the guard is not on the container. A factory that raised
    would make `container.mine_pass()` unbuildable, and every test that
    constructs a container without a model would fail at construction rather
    than at use.

    The `container` fixture above is already a container with no model:
    `_FakeContainer` sets `asker = None`, which is what a deployment with no
    key gets.
    """
    assert container.asker is None
    assert container.mine_pass() is not None
    assert container.read_chat() is not None
    assert container.read_gestures() is not None


def test_the_mining_pass_is_given_its_own_patience() -> None:
    """`gemini_timeout_ms` is every call's, and the two ends of this system
    differ by four orders of magnitude: it was chosen against a ~11s reading of
    ONE gesture, and a mining pass sends 162,000 tokens and answers in minutes.

    Measured on the deployed store 2026-09-21: `gemini-3.1-pro-preview` took
    107s, 135s and 217s against that 120s limit, so two of five passes died on
    a coin flip -- and each was recorded as $0 and 0 tokens while very probably
    being billed, which is the worst shape a failure can have.

    Asserted on the CLIENT the pass is handed, because that is where a timeout
    lives and there is nothing else to look at: the port's `ask` says nothing
    about time.
    """
    from sro.config import Settings
    from sro.container import _patient_asker_for
    from sro.infrastructure.gemini.asker import GeminiAsker

    # The shipped default, not a number this test made up: what is being
    # asserted is what a deployment gets.
    settings = Settings(_env_file=None, gemini_api_key="k")
    assert settings.gemini_mine_timeout_ms >= 300_000, (
        "a mining pass is minutes long and this is the timeout it runs under"
    )
    ordinary = GeminiAsker(client=object())

    patient = _patient_asker_for(settings, ordinary, _meter())

    assert isinstance(patient, GeminiAsker)
    assert patient is not ordinary, "the mining pass shares the reader's two minutes"
    assert settings.gemini_mine_timeout_ms > settings.gemini_timeout_ms


def test_an_asker_that_is_not_the_sdk_is_handed_back_untouched() -> None:
    """A fake in a test, or an asker a future deployment injects. Only the one
    with a timeout to set is rebuilt, and `isinstance` in the composition root
    is the one place allowed to know a concrete adapter."""
    from sro.config import Settings
    from sro.container import _patient_asker_for

    fake = FakeAsker()

    assert _patient_asker_for(Settings(_env_file=None), fake, _meter()) is fake
    assert _patient_asker_for(Settings(_env_file=None), None, _meter()) is None


def test_retiring_a_job_is_handed_the_containers_store_and_clock(
    container: Container, uow: FakeUnitOfWork
) -> None:
    """A retirement stamped by a clock nobody can move, or written to a store
    of its own, is one no test can see."""
    retire = container.retire_workflow()

    assert isinstance(retire, RetireWorkflow)
    assert retire._uow is uow
    assert retire._clock is container.clock


def _meter() -> Any:
    from sro.infrastructure.gemini.metered import Meter

    return Meter(FakeUnitOfWork, clock=FakeClock(), cap_usd=-1.0)


def test_every_model_adapter_a_deployment_builds_is_metered() -> None:
    """The meter is the client, so an adapter built without it spends without
    a bill and past the cap. Every Gemini adapter the root builds is checked,
    not a sample of them."""
    from sro.config import Settings
    from sro.container import (
        _build_asker,
        _build_embedder,
        _build_intent_parser,
        _build_transcriber,
        _build_vision,
        _patient_asker_for,
    )
    from sro.infrastructure.gemini.metered import Metered

    settings = Settings(
        _env_file=None,
        gemini_api_key="k",
        interpretation_enabled=True,
        vision_enabled=True,
        transcription_enabled=True,
        knowledge_embeddings_enabled=True,
    )
    meter = _meter()
    asker = _build_asker(settings, meter)
    built = [
        asker,
        _patient_asker_for(settings, asker, meter),
        _build_vision(settings, meter),
        _build_embedder(settings, meter),
        _build_transcriber(settings, meter),
        _build_intent_parser(settings, meter),
    ]

    assert [type(getattr(one, "_client", None)).__name__ for one in built] == [
        Metered.__name__
    ] * len(built)


def test_the_meter_judges_the_day_on_the_containers_own_clock() -> None:
    """A second clock is a second "today": a pinned container clock would put
    the ledger's rows and the cap's midnight on different days."""
    from sro.config import Settings
    from sro.container import build_container

    built = build_container(Settings(_env_file=None))

    assert built.meter._clock is built.clock


def test_the_pool_is_built_per_tenant_from_steel_urls() -> None:
    from sro.config import Settings
    from sro.container import _build_pool

    settings = Settings(
        _env_file=None,
        steel_urls={"acme": (("http://acme-steel:3000", "http://acme-steel:9223"),)},
    )
    pool = _build_pool(settings)

    assert pool._containers("acme") == ("http://acme-steel:3000",)
    assert pool._containers("beta") == (settings.steel_base_url,)
    assert "http://acme-steel:3000" in pool._clients
    assert settings.steel_base_url in pool._clients
