from __future__ import annotations

# Nango integration -> the MCP server (SRO_MCP_SERVERS name) that reads its mail.
MCP_SERVER = {"microsoft": "outlook"}


def not_set_up(integration: str) -> str:
    name = MCP_SERVER.get(integration, integration).capitalize()
    return f"{name} isn't set up on this server yet. An admin adds it in Nango first."
