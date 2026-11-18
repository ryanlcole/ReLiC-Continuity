"""Run with the optional MCP SDK installed; no network or real data."""
from __future__ import annotations

import asyncio
import pytest

pytest.importorskip("mcp.server.mcpserver")

from relic_community.ledger import ContinuityLedger
from relic_community.mcp_server import create_server


def test_real_sdk_registers_only_three_read_only_tools(tmp_path):
    ledger = ContinuityLedger(tmp_path / "synthetic.sqlite3")
    ledger.append(
        project="fixture", actor="test", kind="TEST_RESULT",
        state="PASS", source_ref="opaque:synthetic",
        summary="Synthetic event only",
    )
    server = create_server(str(ledger.path), "fixture")
    tools = asyncio.run(server.list_tools())
    names = {tool.name for tool in tools}
    assert names == {"verify_chain", "context_pack", "find_events"}
    for tool in tools:
        assert tool.description
        assert tool.input_schema.get("type") == "object"
        assert tool.output_schema is not None
        assert tool.output_schema.get("type") == "object"
    assert not {"append", "write", "delete", "payment"} & names


def test_real_sdk_refuses_missing_database(tmp_path):
    with pytest.raises(FileNotFoundError):
        create_server(str(tmp_path / "missing.sqlite3"), "fixture")
