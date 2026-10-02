import pytest
from pydantic import ValidationError

from sro.config import Settings


def test_a_tenant_s_mail_server_is_read_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SRO_MAIL_SERVERS", '{"acme": "outlook"}')

    assert Settings(_env_file=None).mail_servers == {"acme": "outlook"}


@pytest.mark.parametrize(
    "value",
    ['{"acme": ""}', '{"acme": "Out look"}', '{"": "outlook"}', '{"acme": "outlook/1"}'],
)
def test_a_bad_mail_server_stops_the_load_and_says_which(
    value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SRO_MAIL_SERVERS", value)

    with pytest.raises(ValidationError) as refused:
        Settings(_env_file=None)

    assert "SRO_MAIL_SERVERS" in str(refused.value)
