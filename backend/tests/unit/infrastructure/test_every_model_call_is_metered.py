"""Every call to the model is billed to the tenant it was made for, in one place.

The adapters are handed a metered client, so none of them can reach the model
without passing the meter: the cap is asked before the call, and the tokens
the model reports are written to the day's ledger after it. What the adapter
does with the answer -- keep it, throw it away, fold it into a run -- no longer
decides whether the day's bill sees it.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from sro.application.ports.vision import Screen
from sro.application.shared.refusals import OverCap
from sro.domain.recording.events import ActionKind
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import ModelSpend, price
from sro.infrastructure.gemini.asker import GeminiAsker
from sro.infrastructure.gemini.computer_use import GeminiVisionDriver
from sro.infrastructure.gemini.intent import GeminiIntentParser
from sro.infrastructure.gemini.metered import Meter, Metered
from sro.infrastructure.knowledge.embedding import GeminiEmbedder
from sro.infrastructure.transcription.gemini import GeminiTranscriber
from sro.whose import about
from tests.unit.fakes import FakeClock, FakeUnitOfWork

NOW = datetime(2026, 9, 24, 10, 0, tzinfo=UTC)
MODEL = "gemini-3-flash"


def _usage(prompt: int | None = 100, out: int | None = 20, thoughts: int = 5) -> Any:
    return SimpleNamespace(
        prompt_token_count=prompt,
        candidates_token_count=out,
        thoughts_token_count=thoughts,
        tool_use_prompt_token_count=None,
    )


class _Models:
    def __init__(self, text: str = "{}", usage: Any = None) -> None:
        self._text = text
        self._usage = _usage() if usage is None else usage
        self.called = 0

    async def generate_content(self, **_: Any) -> Any:
        self.called += 1
        return SimpleNamespace(text=self._text, usage_metadata=self._usage, candidates=[])

    async def embed_content(self, *, contents: list[str], **_: Any) -> Any:
        self.called += 1
        return SimpleNamespace(
            embeddings=[SimpleNamespace(values=[0.5]) for _ in contents], metadata=None
        )


def _client(models: _Models) -> Any:
    return SimpleNamespace(aio=SimpleNamespace(models=models))


def _metered(
    models: _Models, *, cap_usd: float = -1.0, uow: FakeUnitOfWork | None = None
) -> tuple[Metered, FakeUnitOfWork]:
    held = uow or FakeUnitOfWork()
    meter = Meter(lambda: held, clock=FakeClock(NOW), cap_usd=cap_usd)
    return Metered(_client(models), meter), held


def _rows(uow: FakeUnitOfWork) -> list[ModelSpend]:
    return list(uow.spend.rows)


async def test_an_asked_question_is_billed_to_the_tenant_it_was_asked_for() -> None:
    client, uow = _metered(_Models('{"ok": true}'))
    asker = GeminiAsker(api_key="", client=client)

    with about(tenant="acme"):
        await asker.ask(model=MODEL, instructions="i", evidence="e", schema={"type": "object"})

    [row] = _rows(uow)
    assert (row.tenant, row.model, row.in_tokens, row.out_tokens, row.thought_tokens) == (
        "acme",
        MODEL,
        100,
        25,
        5,
    )
    assert row.cost_usd == pytest.approx(price(MODEL, 100, 25))
    assert not row.unpriced


async def test_the_intent_parser_is_billed() -> None:
    client, uow = _metered(_Models('{"wants": "ask", "verb": "list", "confidence": 1}'))
    parser = GeminiIntentParser("", MODEL, client=client)

    with about(tenant="acme"):
        await parser.read("show the waves")
        await parser.extract("adjust sku 1", parameters=("sku",))

    assert [row.in_tokens for row in _rows(uow)] == [100, 100]


async def test_the_vision_driver_is_billed() -> None:
    client, uow = _metered(_Models())
    driver = GeminiVisionDriver("", MODEL, client=client)

    with about(tenant="acme"):
        await driver.propose(
            goal="save",
            screen=Screen(image=b"png", mime_type="image/png", width=10, height=10),
            allowed=(ActionKind.CLICK,),
        )

    [row] = _rows(uow)
    assert row.out_tokens == 25


async def test_the_transcriber_is_billed() -> None:
    client, uow = _metered(_Models('{"segments": []}'))

    with about(tenant="acme"):
        await GeminiTranscriber("", MODEL, client=client).transcribe(
            b"ogg", content_type="audio/ogg"
        )

    [row] = _rows(uow)
    assert row.in_tokens == 100


async def test_an_embedding_is_billed_by_what_it_was_sent() -> None:
    """The embedding endpoint reports no tokens, so what was sent is counted:
    four characters to a token, rounded up, priced off the table."""
    client, uow = _metered(_Models())

    with about(tenant="acme"):
        await GeminiEmbedder("", "gemini-embedding-001", client=client).embed(("a" * 400, "b"))

    [row] = _rows(uow)
    assert row.in_tokens == 101
    assert row.cost_usd == pytest.approx(price("gemini-embedding-001", 101, 0))
    assert not row.unpriced


async def test_a_model_the_price_table_does_not_know_is_recorded_as_unpriced() -> None:
    client, uow = _metered(_Models("{}"))

    with about(tenant="acme"):
        await GeminiAsker(api_key="", client=client).ask(
            model="gemini-9-unheard-of", instructions="i", evidence="e", schema={}
        )

    [row] = _rows(uow)
    assert row.unpriced
    assert (await uow.spend.today(TenantId("acme"), now=NOW)).blind == 1


async def test_an_answer_with_no_usage_is_unpriced() -> None:
    client, uow = _metered(_Models("{}", usage=_usage(prompt=None)))

    with about(tenant="acme"):
        await GeminiAsker(api_key="", client=client).ask(
            model=MODEL, instructions="i", evidence="e", schema={}
        )

    [row] = _rows(uow)
    assert row.unpriced


async def test_the_days_spend_counts_what_the_meter_wrote() -> None:
    client, uow = _metered(_Models("{}"))

    with about(tenant="acme"):
        await GeminiAsker(api_key="", client=client).ask(
            model=MODEL, instructions="i", evidence="e", schema={}
        )

    day = await uow.spend.today(TenantId("acme"), now=NOW)
    assert day.cost_usd == pytest.approx(price(MODEL, 100, 25))
    assert (await uow.spend.today(TenantId("other"), now=NOW)).cost_usd == 0.0


async def test_an_over_cap_tenant_never_reaches_the_model() -> None:
    models = _Models("{}")
    uow = FakeUnitOfWork()
    await uow.spend.record(_spent("acme", 6.0))
    client, _ = _metered(models, cap_usd=5.0, uow=uow)

    with about(tenant="acme"):
        answer = await GeminiAsker(api_key="", client=client).ask(
            model=MODEL, instructions="i", evidence="e", schema={}
        )
        with pytest.raises(OverCap):
            await GeminiEmbedder("", "gemini-embedding-001", client=client).embed(("x",))

    assert models.called == 0
    assert answer.error is not None and "daily cap reached" in answer.error
    assert len(_rows(uow)) == 1


async def test_a_neighbour_over_the_cap_does_not_stop_this_tenant() -> None:
    models = _Models("{}")
    uow = FakeUnitOfWork()
    await uow.spend.record(_spent("other", 6.0))
    client, _ = _metered(models, cap_usd=5.0, uow=uow)

    with about(tenant="acme"):
        await GeminiAsker(api_key="", client=client).ask(
            model=MODEL, instructions="i", evidence="e", schema={}
        )

    assert models.called == 1


async def test_a_call_that_never_answered_is_not_billed() -> None:
    class _Down(_Models):
        async def generate_content(self, **_: Any) -> Any:
            raise RuntimeError("connection reset")

    client, uow = _metered(_Down())

    with about(tenant="acme"):
        answer = await GeminiAsker(api_key="", client=client).ask(
            model=MODEL, instructions="i", evidence="e", schema={}
        )

    assert answer.error
    assert _rows(uow) == []


def _spent(tenant: str, usd: float) -> ModelSpend:
    return ModelSpend(id=f"spd_{tenant}", tenant=tenant, model=MODEL, at=NOW, cost_usd=usd)


async def test_a_look_in_the_mail_and_its_gather_are_billed() -> None:
    """The look reads each mail with the model and gathers what the mail did
    not carry with it too; both used to return their spend and drop it."""
    from sro.application.chat.from_the_mail import FromTheMail
    from sro.application.context import RequestContext
    from sro.application.execution.gather import GatherContext
    from sro.domain.shared.identifiers import PrincipalId
    from tests.unit.application.rig.test_from_the_mail import (
        JOB,
        _found,
        _held,
        _mail,
        _Mailbox,
        _reading,
    )
    from tests.unit.fakes import FakeIdFactory

    class _ThenGathers(_Models):
        def __init__(self) -> None:
            super().__init__()
            self._said = [json.dumps(_reading(JOB, bare=True))]

        async def generate_content(self, **_: Any) -> Any:
            self.called += 1
            text = self._said.pop(0) if self._said else "{}"
            return SimpleNamespace(text=text, usage_metadata=_usage(), candidates=[])

    uow = await _held()
    client, _ = _metered(_ThenGathers(), uow=uow)
    asker = GeminiAsker(api_key="", client=client)
    mailbox = _Mailbox(search=_found("m-1"), **{"m-1": _mail("please add a customer type")})
    ctx = RequestContext(tenant_id=TenantId("acme"), principal_id=PrincipalId("devansh"))
    look = FromTheMail(
        uow,
        mailbox,
        asker,
        model=MODEL,
        gather=GatherContext(tools=mailbox, asker=asker, model=MODEL),
        clock=FakeClock(NOW),
        ids=FakeIdFactory(),
    )

    with about(tenant="acme"):
        await look.execute(ctx)

    rows = _rows(uow)
    assert len(rows) >= 2, "the reading and the gather were not both billed"
    assert {row.tenant for row in rows} == {"acme"}
