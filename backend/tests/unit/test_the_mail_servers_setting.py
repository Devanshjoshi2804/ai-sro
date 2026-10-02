import pytest
from pydantic import ValidationError

from sro.config import Settings

OUTLOOK = "outlook=http://outlook:9100/mcp"


def test_a_tenant_s_mail_server_is_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SRO_MAIL_SERVERS", '{"acme": "outlook"}')
    monkeypatch.setenv("SRO_MCP_SERVERS", OUTLOOK)

    assert Settings(_env_file=None).mail_servers == {"acme": "outlook"}


@pytest.mark.parametrize(
    "value",
    ['{"acme": ""}', '{"acme": "Out look"}', '{"": "outlook"}', '{"acme": "outlook/1"}'],
)
def test_a_bad_mail_server_stops_the_load_and_says_which(
    value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SRO_MAIL_SERVERS", value)
    monkeypatch.setenv("SRO_MCP_SERVERS", OUTLOOK)

    with pytest.raises(ValidationError) as refused:
        Settings(_env_file=None)

    assert "SRO_MAIL_SERVERS" in str(refused.value)


@pytest.mark.parametrize("mcp", ["", "gmail=http://gmail:9000/mcp", "outlook=, gmail=http://g/mcp"])
def test_a_mail_server_no_connector_line_names_stops_the_load_and_says_which(
    mcp: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Day-end 6: every send and every look of that tenant would otherwise fail at run time."""
    monkeypatch.setenv("SRO_MAIL_SERVERS", '{"acme": "outlook"}')
    monkeypatch.setenv("SRO_MCP_SERVERS", mcp)

    with pytest.raises(ValidationError) as refused:
        Settings(_env_file=None)

    assert "SRO_MAIL_SERVERS" in str(refused.value) and "outlook" in str(refused.value)
    assert "SRO_MCP_SERVERS" in str(refused.value)
