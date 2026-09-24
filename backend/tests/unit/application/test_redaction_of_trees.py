from __future__ import annotations

from sro.application.observation.redact import redact_events


def test_a_password_node_keeps_no_value() -> None:
    event = {
        "kind": "snapshot",
        "snapshot": {
            "nodes": [
                {"name": {"value": "Password"}, "value": {"value": "hunter2"}},
                {"name": {"value": "Client"}, "value": {"value": "ACME"}},
            ]
        },
    }

    (out,) = redact_events([event])

    nodes = out["snapshot"]["nodes"]
    assert "value" not in nodes[0]
    assert nodes[1]["value"] == {"value": "ACME"}
