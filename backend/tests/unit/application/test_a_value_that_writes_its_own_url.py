"""A supplied value must not write the address it is sent to.

ADR 010 closed this for the JSON body -- a quantity of `2,"approved":true`
no longer adds a field -- and named the URL as the same defect in a different
syntax, left open. `X&limit=9999` in a search term added a query parameter the
demonstration never sent; `a/b` in a path slot added a segment.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, unquote, urlsplit

from sro.application.context import RequestContext
from sro.application.execution.execute_skill import ExecuteSkill, ExecutionRequest
from sro.domain.recording.sensitivity import Sensitivity
from sro.domain.shared.identifiers import SkillId
from sro.domain.skill.plan import HeaderPlan
from sro.domain.skill.promotion import PromotionStage
from sro.domain.skill.skill import SkillVersion
from sro.domain.skill.template import Template
from tests import factories as f
from tests.unit.fakes import (
    FakeClock,
    FakeCredentialVault,
    FakeHttpCaller,
    FakeIdFactory,
    FakeUnitOfWork,
)

CTX = RequestContext(tenant_id=f.TENANT, principal_id=f.OPERATOR)

_COOKIE_REF = "blue_yonder/SG/cookie"
_SCOPED = f"{f.TENANT}/{_COOKIE_REF}"


_TEMPLATE = "https://wms.test/data/WM/wm/areas/${area}?name=${name}&limit=25"


def _lookup_version() -> SkillVersion:
    """One GET carrying a value in each kind of URL slot: a path segment and a
    query parameter, with a second parameter beside the placeholder so a value
    that escapes has somewhere to land."""
    return f.skill_version(
        steps=(
            f.step(
                index=0,
                network_plan=f.network_plan(
                    method="GET",
                    url=Template(_TEMPLATE),
                    body=None,
                    headers=(
                        HeaderPlan(
                            name="cookie",
                            sensitivity=Sensitivity.SESSION,
                            credential_ref=_COOKIE_REF,
                        ),
                    ),
                ),
                ui_plan=None,
            ),
        ),
        parameters=(
            f.parameter(name="area", observed_values=("PACK-3", "PACK-4")),
            f.parameter(name="name", observed_values=("Smith", "Jones")),
        ),
    )


async def _sent(**parameters: str) -> str:
    uow, http, vault = FakeUnitOfWork(), FakeHttpCaller(), FakeCredentialVault()
    await vault.store(_SCOPED, "session=live")
    skill = f.skill(versions=0)
    skill.add_version(version := _lookup_version())
    stage = PromotionStage.RECORDED
    while stage is not PromotionStage.ASSISTED:
        stage = stage.next_stage()
        version.promote(stage, f.at(700), f.OPERATOR)
    await uow.skills.add(skill)

    await ExecuteSkill(uow, http, vault, FakeClock(), FakeIdFactory()).execute(
        CTX,
        ExecutionRequest(
            skill_id=SkillId("skill-1"),
            parameters={"area": "PACK-3", "name": "Smith", **parameters},
            authorized_by="supervisor",
        ),
    )
    assert len(http.sent) == 1, http.sent
    url = http.sent[0]["url"]
    assert isinstance(url, str)
    return url


async def test_a_search_term_does_not_add_a_query_parameter() -> None:
    url = await _sent(name="X&limit=9999")

    assert parse_qsl(urlsplit(url).query) == [("name", "X&limit=9999"), ("limit", "25")]


async def test_a_value_with_a_slash_does_not_add_a_path_segment() -> None:
    url = await _sent(area="a/b")

    path = urlsplit(url).path
    assert [unquote(s) for s in path.split("/") if s] == ["data", "WM", "wm", "areas", "a/b"]


async def test_a_value_carrying_every_delimiter_still_arrives_as_one_value() -> None:
    """The whole set at once, in both kinds of slot. A query parameter is read
    back with `parse_qsl` and a path segment with `unquote`, because arriving
    whole is the claim and a rendered string only looks like it."""
    awkward = "a&b=c?d#e/f"

    url = await _sent(area=awkward, name=awkward)

    assert dict(parse_qsl(urlsplit(url).query)) == {"name": awkward, "limit": "25"}
    assert [unquote(s) for s in urlsplit(url).path.split("/") if s][-1] == awkward


async def test_an_ordinary_value_renders_exactly_the_bytes_it_rendered_before() -> None:
    """The constraint that decides the shape of the encoding. Skills already
    exist, induced from real captures, and a value that works today has to go
    out unchanged tomorrow -- so this compares against the plain substitution
    this replaced rather than against a string written out by hand.

    `ATTN%20ALI` is the case that keeps the two slots apart: a path segment is
    stored the way the demonstration sent it, already encoded, and a uniform
    rule would send `ATTN%2520ALI`.
    """
    for area, name in [
        ("PACK-3", "Smith"),
        ("ATTN%20ALI", "Smith Jones"),
        ("caf\u00e9", "caf\u00e9"),
        ("a b", "a b"),
    ]:
        url = await _sent(area=area, name=name)
        assert url == Template(_TEMPLATE).render({"area": area, "name": name}), (
            f"{area!r} / {name!r} renders differently than it did before"
        )
