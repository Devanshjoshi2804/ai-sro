"""Every call to the model is billed to the tenant it was made for, in one place.

The adapters are handed a metered client, so none of them can reach the model
without passing the meter: the cap is asked before the call, and the tokens
the model reports are written to the day's ledger after it. What the adapter
does with the answer -- keep it, throw it away, fold it into a run -- no longer
decides whether the day's bill sees it.
"""

from __future__ import annotations

import asyncio
import gc
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from sro.application.connection.check_session import CheckSession
from sro.application.connection.connect_system import RefreshSession
from sro.application.connection.keep_open import KeepSessionsOpen
from sro.application.connection.session_life import SessionLife
from sro.application.connection.sign_in import EnsureSignedIn, SignIn
from sro.application.knowledge.record_claim import RecordClaims
from sro.application.ports.vision import Screen
from sro.application.runtime.answer_run import AnswerRun
from sro.application.shared.refusals import OverCap
from sro.domain.connection.connection import Connection, ConnectionId
from sro.domain.prompts.sight import SIGHT
from sro.domain.recording.events import ActionKind
from sro.domain.shared.identifiers import TenantId
from sro.domain.shared.prices import ModelSpend, price
from sro.infrastructure.gemini.asker import GeminiAsker
from sro.infrastructure.gemini.computer_use import GeminiVisionDriver
from sro.infrastructure.gemini.intent import GeminiIntentParser
from sro.infrastructure.gemini.interpreter import GeminiInterpreter
from sro.infrastructure.gemini.metered import Meter, Metered, Unattributed, metered_client
from sro.infrastructure.knowledge.embedding import GeminiEmbedder
from sro.infrastructure.transcription.gemini import GeminiTranscriber
from sro.whose import about
from tests.unit.fakes import (
    FakeBrowserProvider,
    FakeClock,
    FakeCredentialVault,
    FakeDurableExecution,
    FakeHttpCaller,
    FakeIdFactory,
    FakeSignInDriver,
    FakeUnitOfWork,
)

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
    asker = GeminiAsker(client=client)

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
    parser = GeminiIntentParser(client=client)

    with about(tenant="acme"):
        await parser.read("show the waves")
        await parser.extract("adjust sku 1", parameters=("sku",))

    assert [row.in_tokens for row in _rows(uow)] == [100, 100]


async def test_the_interpreter_is_capped_and_billed() -> None:
    """A pursue reaches it (pursue_goal -> understand_recording), on a pro model."""
    models = _Models('{"steps": []}')
    client, uow = _metered(models)
    interpreter = GeminiInterpreter(client=client)

    with about(tenant="acme"):
        await interpreter.read("evidence")
        await interpreter.name_task("evidence")

    assert [(row.tenant, row.in_tokens) for row in _rows(uow)] == [("acme", 100)] * 2

    capped = FakeUnitOfWork()
    await capped.spend.record(_spent("acme", 6.0))
    over, _ = _metered(models, cap_usd=5.0, uow=capped)
    with about(tenant="acme"):
        await GeminiInterpreter(client=over).read("evidence")
    assert models.called == 2


async def test_the_vision_driver_is_billed() -> None:
    client, uow = _metered(_Models())
    driver = GeminiVisionDriver(SIGHT, client=client)

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
        await GeminiTranscriber(client=client).transcribe(b"ogg", content_type="audio/ogg")

    [row] = _rows(uow)
    assert row.in_tokens == 100


async def test_an_embedding_is_billed_by_what_it_was_sent() -> None:
    """The embedding endpoint reports no tokens, so what was sent is counted:
    four characters to a token, rounded up, priced off the table."""
    client, uow = _metered(_Models())

    with about(tenant="acme"):
        await GeminiEmbedder("gemini-embedding-001", client=client).embed(("a" * 400, "b"))

    [row] = _rows(uow)
    assert row.in_tokens == 101
    assert row.cost_usd == pytest.approx(price("gemini-embedding-001", 101, 0))
    assert not row.unpriced


async def test_a_model_the_price_table_does_not_know_is_recorded_as_unpriced() -> None:
    client, uow = _metered(_Models("{}"))

    with about(tenant="acme"):
        await GeminiAsker(client=client).ask(
            model="gemini-9-unheard-of", instructions="i", evidence="e", schema={}
        )

    [row] = _rows(uow)
    assert row.unpriced
    assert (await uow.spend.today(TenantId("acme"), now=NOW)).blind == 1


async def test_an_answer_with_no_usage_is_unpriced() -> None:
    client, uow = _metered(_Models("{}", usage=_usage(prompt=None)))

    with about(tenant="acme"):
        await GeminiAsker(client=client).ask(model=MODEL, instructions="i", evidence="e", schema={})

    [row] = _rows(uow)
    assert row.unpriced


async def test_the_days_spend_counts_what_the_meter_wrote() -> None:
    client, uow = _metered(_Models("{}"))

    with about(tenant="acme"):
        await GeminiAsker(client=client).ask(model=MODEL, instructions="i", evidence="e", schema={})

    day = await uow.spend.today(TenantId("acme"), now=NOW)
    assert day.cost_usd == pytest.approx(price(MODEL, 100, 25))
    assert (await uow.spend.today(TenantId("other"), now=NOW)).cost_usd == 0.0


async def test_an_over_cap_tenant_never_reaches_the_model() -> None:
    models = _Models("{}")
    uow = FakeUnitOfWork()
    await uow.spend.record(_spent("acme", 6.0))
    client, _ = _metered(models, cap_usd=5.0, uow=uow)

    with about(tenant="acme"):
        with pytest.raises(OverCap, match="daily cap reached"):
            await GeminiAsker(client=client).ask(
                model=MODEL, instructions="i", evidence="e", schema={}
            )
        with pytest.raises(OverCap):
            await GeminiEmbedder("gemini-embedding-001", client=client).embed(("x",))

    assert models.called == 0
    assert len(_rows(uow)) == 1


async def test_a_neighbour_over_the_cap_does_not_stop_this_tenant() -> None:
    models = _Models("{}")
    uow = FakeUnitOfWork()
    await uow.spend.record(_spent("other", 6.0))
    client, _ = _metered(models, cap_usd=5.0, uow=uow)

    with about(tenant="acme"):
        await GeminiAsker(client=client).ask(model=MODEL, instructions="i", evidence="e", schema={})

    assert models.called == 1


async def test_a_call_that_never_answered_is_not_billed() -> None:
    class _Down(_Models):
        async def generate_content(self, **_: Any) -> Any:
            raise RuntimeError("connection reset")

    client, uow = _metered(_Down())

    with about(tenant="acme"):
        answer = await GeminiAsker(client=client).ask(
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
    from sro.domain.prompts.gather import GATHER
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
            self.gathered = 0

        async def generate_content(self, **kw: Any) -> Any:
            contents = kw["contents"]
            self.called += 1
            self.gathered += GATHER.instructions in contents
            text = self._said.pop(0) if self._said else "{}"
            return SimpleNamespace(text=text, usage_metadata=_usage(), candidates=[])

    uow = await _held()
    models = _ThenGathers()
    client, _ = _metered(models, uow=uow)
    asker = GeminiAsker(client=client)
    mailbox = _Mailbox(search=_found("m-1"), **{"m-1": _mail("please add a customer type")})
    ctx = RequestContext(tenant_id=TenantId("acme"), principal_id=PrincipalId("devansh"))
    look = FromTheMail(
        uow,
        mailbox,
        asker,
        answer=AnswerRun(uow, FakeDurableExecution()),
        gather=GatherContext(tools=mailbox, asker=asker),
        clock=FakeClock(NOW),
        ids=FakeIdFactory(),
    )

    with about(tenant="acme"):
        await look.execute(ctx)

    rows = _rows(uow)
    assert models.gathered >= 1, "the look never gathered, so this proves nothing"
    assert len(rows) == models.called, "a call the model answered was not billed"
    assert {row.tenant for row in rows} == {"acme"}


async def test_a_response_with_no_output_count_is_priced_not_blind() -> None:
    """Proto3 drops a zero `candidatesTokenCount`, so the SDK hands back None
    for a response that wrote nothing. The prompt count is there, so the usage
    is known: zero out, priced -- not a blind row that stops the day."""
    client, uow = _metered(_Models("{}", usage=_usage(out=None, thoughts=0)))

    with about(tenant="acme"):
        await GeminiAsker(client=client).ask(model=MODEL, instructions="i", evidence="e", schema={})

    [row] = _rows(uow)
    assert (row.in_tokens, row.out_tokens, row.unpriced) == (100, 0, False)
    assert row.cost_usd == pytest.approx(price(MODEL, 100, 0))


async def test_a_call_nobody_is_named_for_is_refused_and_not_billed() -> None:
    """A model call with no tenant is a wiring bug: nobody's cap can be asked
    and nobody's bill can show it, so the meter refuses rather than spend."""
    models = _Models("{}")
    client, uow = _metered(models, cap_usd=5.0)

    with about():
        with pytest.raises(Unattributed):
            await GeminiEmbedder("gemini-embedding-001", client=client).embed(("x",))
        answer = await GeminiAsker(client=client).ask(
            model=MODEL, instructions="i", evidence="e", schema={}
        )

    assert models.called == 0
    assert answer.error is not None and "no tenant" in answer.error
    assert _rows(uow) == []


async def test_a_worker_activity_names_its_tenant_so_its_calls_are_capped_and_billed() -> None:
    """The Temporal worker is its own process with nobody attributed; every
    activity builds its context through `_context`, and that is where the
    tenant is named."""
    from sro.infrastructure.temporal.activities import _context

    models = _Models()
    uow = FakeUnitOfWork()
    client, _ = _metered(models, cap_usd=5.0, uow=uow)
    embedder = GeminiEmbedder("gemini-embedding-001", client=client)

    async def _activity(tenant: str) -> None:
        _context(tenant, "worker")
        await embedder.embed(("x",))

    with about():
        await _activity("acme")
    [row] = _rows(uow)
    assert row.tenant == "acme"

    await uow.spend.record(_spent("acme", 6.0))
    with about(), pytest.raises(OverCap):
        await _activity("acme")
    assert models.called == 1


async def test_a_refusal_names_the_model_and_who_asked(caplog: pytest.LogCaptureFixture) -> None:
    """A refused call in the log is only useful if it says which model and
    which part of the system wanted it."""
    uow = FakeUnitOfWork()
    await uow.spend.record(_spent("acme", 6.0))
    client, _ = _metered(_Models(), cap_usd=5.0, uow=uow)
    embedder = GeminiEmbedder("gemini-embedding-001", client=client)

    async def _wanting_a_vector() -> None:
        await embedder.embed(("x",))

    with about(tenant="acme"), pytest.raises(OverCap):
        await _wanting_a_vector()
    with about(), pytest.raises(Unattributed):
        await _wanting_a_vector()

    lines = [r.getMessage() for r in caplog.records if r.name.endswith("metered")]
    assert len(lines) == 2, lines
    for line in lines:
        assert "gemini-embedding-001" in line and "_wanting_a_vector" in line, line


async def test_a_keeper_sweep_embeds_its_session_claim_and_bills_the_connections_tenant() -> None:
    """The keeper runs outside any request: it names each connection's tenant
    itself, or every sweep's session-life claim is refused its embedding."""
    client, uow = _metered(_Models())
    vault, http, clock = FakeCredentialVault(), FakeHttpCaller(), FakeClock(NOW)
    http.answer(status_code=200, text="<main>waves</main>")
    connection = Connection(
        id=ConnectionId("con_1"),
        tenant_id=TenantId("acme"),
        name="WMS",
        target_system="wms",
        base_url="https://wms.example.com/portal",
        created_at=NOW,
    )
    connection.authenticated(NOW)
    async with uow:
        await uow.connections.add(connection)
        await uow.commit()
    await vault.store(connection.cookie_key, "SESSIONID=live")
    embedder = GeminiEmbedder("gemini-embedding-001", client=client)
    life = SessionLife(uow, RecordClaims(uow, clock, FakeIdFactory(), embedder))
    refresh = RefreshSession(uow, vault, clock)
    sign_in = SignIn(uow, vault, FakeBrowserProvider(), FakeSignInDriver(), refresh)
    check = CheckSession(uow, vault, http)

    await KeepSessionsOpen(uow, EnsureSignedIn(sign_in, check, uow, life, clock)).sweep()

    assert [row.tenant for row in _rows(uow)] == ["acme"]
    assert [bool(entry.embedding) for entry in uow.knowledge.rows.values()] == [True]


async def test_a_metered_client_built_inside_a_running_loop_stays_open() -> None:
    """The container is built inside the API's lifespan and inside
    `asyncio.run` for the scripts. Holding only `client.aio.models` let the
    genai client be collected at once, and its AsyncClient's finaliser scheduled
    `aclose()` on the running loop: every later call failed with "Cannot send a
    request, as the client has been closed", before the meter or the model."""
    metered = metered_client("not-a-key", Meter(FakeUnitOfWork, clock=FakeClock(), cap_usd=-1.0))
    gc.collect()
    await asyncio.gather(*(one for one in asyncio.all_tasks() if one is not asyncio.current_task()))

    assert not metered._models._api_client._async_httpx_client.is_closed


class _ByModel(_Models):
    """3.8-flash writes an empty draft, as it did on QA; 3.7-flash writes one."""

    async def generate_content(self, **asked: Any) -> Any:
        self.called += 1
        body = "" if asked["model"] == "gemini-3.8-flash" else "Done."
        text = json.dumps({"to": "", "subject": "s", "body": body, "cited": []})
        return SimpleNamespace(text=text, usage_metadata=self._usage, candidates=[])


async def test_a_fallback_is_billed_to_each_model_that_was_called() -> None:
    from sro.application.shared.asking import ask
    from sro.domain.prompts.write_mail import WRITE_MAIL

    client, uow = _metered(_ByModel())

    with about(tenant="acme"):
        got = await ask(
            GeminiAsker(client=client), WRITE_MAIL, trusted={}, untrusted={"conversation": "y"}
        )

    assert got.data is not None and got.data["body"] == "Done."
    assert [row.model for row in _rows(uow)] == ["gemini-3.8-flash", "gemini-3.7-flash"]
    assert not any(row.unpriced for row in _rows(uow))
    assert got.cost_usd == pytest.approx(sum(row.cost_usd for row in _rows(uow)))


async def test_a_call_on_the_older_flash_is_priced_and_counts_toward_the_cap() -> None:
    """Measured on QA: a 3.7-flash call of 925 in and 1029 + 997 out came back
    billed at $0.00 -- the price table had no row for it."""
    usage = _usage(prompt=925, out=1029, thoughts=997)
    client, uow = _metered(_Models("{}", usage), cap_usd=1.0)

    with about(tenant="acme"):
        await GeminiAsker(client=client).ask(
            model="gemini-3.7-flash", instructions="i", evidence="e", schema={}
        )

    [row] = _rows(uow)
    assert not row.unpriced and row.cost_usd == pytest.approx(price("gemini-3.7-flash", 925, 2026))
    assert row.cost_usd > 0
    day = await uow.spend.today(TenantId("acme"), now=NOW)
    assert day.cost_usd == pytest.approx(row.cost_usd) and day.blind == 0

    full, _ = _metered(_Models("{}", usage), cap_usd=row.cost_usd, uow=uow)
    with about(tenant="acme"), pytest.raises(OverCap, match="daily cap reached"):
        await GeminiAsker(client=full).ask(
            model="gemini-3.7-flash", instructions="i", evidence="e", schema={}
        )
