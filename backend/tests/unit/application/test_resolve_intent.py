"""Which task was asked for — decided before any medium is chosen.

The expensive failure is not "could not find it". It is finding the wrong thing
confidently and performing it immediately.
"""

from __future__ import annotations

from sro.application.context import RequestContext
from sro.application.intent.plan_task import PlanTask
from sro.application.intent.resolve import ResolveIntent
from sro.application.knowledge.record_claim import Claim, RecordClaims
from sro.application.knowledge.retrieve import Retrieve
from sro.domain.knowledge.entry import EntryKind, EvidenceLevel
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.promotion import PromotionStage
from tests import factories as f
from tests.unit.fakes import FakeClock, FakeEmbedder, FakeIdFactory, FakeUnitOfWork

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)


async def _library(uow: FakeUnitOfWork) -> None:
    adjust = f.skill(
        id=SkillId("skill-adjust"),
        name="Inventory Adjust",
        objective_key=f.objective(objective_type="adjust", entity_type="inventory", facility="SG"),
        versions=0,
    )
    version = f.skill_version()
    version.describe(
        summary="Adjust inventory at SG on blue_yonder, writing PUT /wm/inventory/adjust.",
        when_to_use="Use after a physical stock check. Needs lpn, quantity.",
    )
    adjust.add_version(version)
    version.promote(PromotionStage.SHADOW, f.at(600), f.OPERATOR)
    await uow.skills.add(adjust)

    release = f.skill(
        id=SkillId("skill-wave"),
        name="Release Wave",
        objective_key=f.objective(objective_type="release", entity_type="wave", facility="SG"),
        versions=0,
    )
    wave_version = f.skill_version()
    wave_version.describe(summary="Release a wave at SG.", when_to_use="Use to start picking.")
    release.add_version(wave_version)
    wave_version.promote(PromotionStage.SHADOW, f.at(600), f.OPERATOR)
    await uow.skills.add(release)


def _resolver(uow: FakeUnitOfWork) -> ResolveIntent:
    return ResolveIntent(uow, PlanTask(Retrieve(uow, FakeEmbedder())))


async def test_a_sentence_finds_the_skill_that_was_taught_for_it() -> None:
    uow = FakeUnitOfWork()
    await _library(uow)

    resolution = await _resolver(uow).execute(CTX, utterance="adjust inventory at SG")

    assert resolution.matched is not None
    assert resolution.matched.skill.id == SkillId("skill-adjust")
    assert resolution.why, "every match records what matched, for the audit trail"


async def test_the_answer_names_what_it_still_needs() -> None:
    uow = FakeUnitOfWork()
    await _library(uow)

    resolution = await _resolver(uow).execute(CTX, utterance="adjust inventory at SG")

    assert resolution.missing_parameters == ("shipment_id",)
    assert resolution.question == "I need shipment_id."
    assert resolution.runnable


async def test_a_value_already_supplied_is_not_asked_for_again() -> None:
    uow = FakeUnitOfWork()
    await _library(uow)

    resolution = await _resolver(uow).execute(
        CTX, utterance="adjust inventory at SG", parameters={"shipment_id": "555"}
    )

    assert resolution.missing_parameters == ()
    assert resolution.question is None


async def test_wording_alone_never_matches_a_skill() -> None:
    """ "Release" is in the wave skill's summary. Nothing structural matches an
    utterance about carriers, so the answer is not the nearest skill."""
    uow = FakeUnitOfWork()
    await _library(uow)

    resolution = await _resolver(uow).execute(CTX, utterance="start picking")

    assert resolution.matched is None


async def test_a_skill_nobody_reviewed_is_found_and_refused() -> None:
    uow = FakeUnitOfWork()
    skill = f.skill(
        id=SkillId("skill-count"),
        name="Cycle Count",
        objective_key=f.objective(objective_type="count", entity_type="inventory"),
        versions=0,
    )
    version = f.skill_version()
    version.describe(summary="Count inventory.", when_to_use="Weekly.")
    skill.add_version(version)
    await uow.skills.add(skill)

    resolution = await _resolver(uow).execute(CTX, utterance="count inventory")

    assert resolution.matched is not None
    assert not resolution.runnable
    assert "has not been reviewed" in (resolution.question or "")


async def test_nothing_taught_falls_to_the_knowledge_base_not_to_the_ladder() -> None:
    """The tempting mistake is running the nearest skill in a browser and
    hoping vision sorts it out."""
    uow = FakeUnitOfWork()
    await _library(uow)
    await RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder()).execute(
        CTX,
        (
            Claim(
                system="blue_yonder",
                kind=EntryKind.SCREEN,
                key="#wm.config/wm.config.partners.carriers////",
                title="Configuration ▸ Partners ▸ Carriers",
                body={"label": "Carriers"},
                source="index/app-map.json",
                evidence=EvidenceLevel.OBSERVED,
            ),
        ),
    )

    resolution = await _resolver(uow).execute(CTX, utterance="add a carrier")

    assert resolution.matched is None
    assert resolution.proposal is not None
    assert "Carriers" in resolution.proposal.steps[0].what
    assert "index/app-map.json" in resolution.proposal.sources
    # Knowledge without a demonstration is now a pursuit rather than a refusal:
    # the screen is known, so it can be worked out on the screen. A write still
    # asks first.
    assert resolution.pursuit is not None
    assert resolution.pursuit.needs_confirmation


async def test_a_proposal_is_never_mistaken_for_a_skill() -> None:
    uow = FakeUnitOfWork()
    await RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder()).execute(
        CTX,
        (
            Claim(
                system="blue_yonder",
                kind=EntryKind.SCREEN,
                key="#carriers",
                title="Carriers",
                body={"label": "Carriers"},
                source="index/app-map.json",
                evidence=EvidenceLevel.OBSERVED,
            ),
        ),
    )

    resolution = await _resolver(uow).execute(CTX, utterance="carriers")

    assert resolution.proposal is not None
    assert not resolution.runnable
    assert "not from a demonstration" in resolution.proposal.caveat


async def test_nothing_taught_and_nothing_known_asks_to_be_taught() -> None:
    uow = FakeUnitOfWork()

    resolution = await _resolver(uow).execute(CTX, utterance="do the thing")

    assert resolution.matched is None and resolution.proposal is None
    # Nothing taught and nothing known: there is no screen to open, so the
    # honest answer is still to be shown once.
    assert resolution.pursuit is None
    assert "Show me" in (resolution.question or "") or "Teach me" in (resolution.question or "")


async def test_a_skill_that_cannot_explain_the_verb_is_offered_as_a_question() -> None:
    """The dangerous match is the partial one. "Count inventory in SG" hits an
    adjust skill's entity and facility and scores well, while the only word that
    says what to do matches nothing."""
    uow = FakeUnitOfWork()
    await _library(uow)

    resolution = await _resolver(uow).execute(CTX, utterance="count inventory in SG")

    assert resolution.matched is not None, "still offered — it is probably close"
    assert not resolution.confident
    assert resolution.matched.unexplained == ("count",)
    assert "Did you mean" in (resolution.question or "")
    assert "count" in (resolution.question or "")


async def test_a_sentence_the_skill_fully_accounts_for_is_confident() -> None:
    uow = FakeUnitOfWork()
    await _library(uow)

    resolution = await _resolver(uow).execute(
        CTX, utterance="adjust inventory at SG", parameters={"shipment_id": "1"}
    )

    assert resolution.confident
    assert resolution.question is None


async def test_two_skills_with_one_name_are_told_apart_by_their_key() -> None:
    uow = FakeUnitOfWork()
    for facility in ("DC03", "DC07"):
        skill = f.skill(
            id=SkillId(f"skill-wave-{facility}"),
            name="Release Wave",
            objective_key=f.objective(
                objective_type="release", entity_type="wave", facility=facility
            ),
            versions=0,
        )
        version = f.skill_version()
        version.describe(summary="Release a wave.", when_to_use="To start picking.")
        skill.add_version(version)
        version.promote(PromotionStage.SHADOW, f.at(600), f.OPERATOR)
        await uow.skills.add(skill)

    resolution = await _resolver(uow).execute(CTX, utterance="release wave")

    assert resolution.matched is None
    assert "DC03" in (resolution.question or "") and "DC07" in (resolution.question or "")


async def test_a_sentence_that_names_no_job_while_something_stands_is_about_what_stands() -> None:
    """F2. "check now", typed under a standing run, was planned into Check In
    and Check Out screens. The screen is known here too, so the planner WOULD
    propose it -- and with something standing it is never asked."""
    uow = FakeUnitOfWork()
    await RecordClaims(uow, FakeClock(), FakeIdFactory(), FakeEmbedder()).execute(
        CTX,
        (
            Claim(
                system="blue_yonder",
                kind=EntryKind.SCREEN,
                key="#check",
                title="Inbound ▸ Check In",
                body={"label": "Check In"},
                source="index/app-map.json",
                evidence=EvidenceLevel.OBSERVED,
            ),
        ),
    )

    nothing_standing = await _resolver(uow).execute(CTX, utterance="check now")
    standing = await _resolver(uow).execute(CTX, utterance="check now", standing=True)

    assert nothing_standing.pursuit is not None, "the fixture no longer reaches the explore"
    assert not nothing_standing.about_what_stands
    assert standing.about_what_stands
    assert standing.proposal is None and standing.pursuit is None
    assert standing.question is None


async def test_a_sentence_that_names_a_job_is_that_job_even_while_something_stands() -> None:
    uow = FakeUnitOfWork()
    await _library(uow)

    resolution = await _resolver(uow).execute(
        CTX, utterance="adjust inventory at SG", standing=True
    )

    assert resolution.matched is not None
    assert resolution.matched.skill.id == SkillId("skill-adjust")
    assert not resolution.about_what_stands
