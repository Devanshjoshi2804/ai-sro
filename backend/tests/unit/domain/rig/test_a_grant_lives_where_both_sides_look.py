"""The connector and the backend have to spell one vault key the same way.

`gmail-connector/server.py` runs on its own, outside the package, so it cannot
import `connector_key` and spells the key itself. A second spelling is not a
style problem: the grant is stored under one key and asked for under another,
and the operator's mailbox is invisible to the only thing that needs it.

That failure has already happened once in this session one segment to the right
-- `mcp_token` written, `mcp-token` asked for -- so this is pinned rather than
trusted. The connector's own function is imported and called; a copy of its
arithmetic here would agree with itself while the connector drifted.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from sro.domain.execution.secrets import connector_key

CONNECTOR = Path(__file__).resolve().parents[4] / "gmail-connector" / "server.py"


def _connector() -> ModuleType:
    """The connector as a module. Safe to import: everything it does at the top
    level is constants and definitions, and the serving is behind `__main__`."""
    spec = importlib.util.spec_from_file_location("gmail_connector_under_test", CONNECTOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_connector_and_the_backend_agree_on_where_a_grant_lives() -> None:
    theirs = _connector()._vault_key
    for tenant, operator in (
        ("acme", "devansh.j"),
        ("greyorange", "sam"),
        # The three `_as_key` would have collapsed into one key, which is why
        # the principal is hashed rather than spelled.
        ("acme", "devansh_j"),
        ("acme", "devansh j"),
    ):
        assert theirs(tenant, operator) == connector_key(tenant, "gmail", operator), (
            f"{operator} of {tenant} would store a grant where nothing looks for it"
        )


def test_two_operators_who_differ_only_in_punctuation_get_different_keys() -> None:
    """`_as_key` collapses every run of punctuation to one dash, and
    `PrincipalId` constrains nothing but blankness -- so these three are ids
    somebody can be issued, and they would have shared one mailbox."""
    keys = {connector_key("acme", "gmail", who) for who in ("devansh.j", "devansh_j", "devansh j")}

    assert len(keys) == 3, "two operators would read the same mail"
