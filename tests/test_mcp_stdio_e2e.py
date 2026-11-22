"""Actual MCP v2 client-to-server JSON-RPC exchange over local stdio.

Run only in the optional MCP SDK CI job with synthetic SQLite fixtures.
No HTTP listener, external ReLiC server, payment, or customer data.
"""
from __future__ import annotations

import asyncio
import sqlite3
import sys

import pytest

pytest.importorskip("mcp.server.mcpserver")
from mcp import Client, StdioServerParameters

from relic_community.ledger import ContinuityLedger


def _params(path, project="allowed"):
    return StdioServerParameters(
        command=sys.executable,
        args=[
            "-m", "relic_community.mcp_server", "--db", str(path),
            "--project", project,
        ],
    )


def _fixture(tmp_path):
    ledger = ContinuityLedger(tmp_path / "synthetic-stdio.sqlite3")
    ledger.append(
        project="allowed", actor="fixture", kind="OBSERVATION",
        state="OBSERVED", source_ref="opaque:allowed-one",
        summary="Synthetic allowed observation",
    )
    ledger.append(
        project="other", actor="fixture", kind="OBSERVATION",
        state="OBSERVED", source_ref="opaque:other-one",
        summary="Synthetic other observation",
    )
    return ledger


def test_actual_stdio_client_lists_and_invokes_tools(tmp_path):
    ledger = _fixture(tmp_path)

    async def exercise():
        async with Client(_params(ledger.path), read_timeout_seconds=10) as client:
            listed = await client.list_tools()
            assert {t.name for t in listed.tools} == {
                "verify_chain", "context_pack", "find_events", "relic_command"
            }
            assert all(t.input_schema.get("type") == "object" for t in listed.tools)

            checked = await client.call_tool("verify_chain", {})
            assert checked.is_error is False
            assert checked.structured_content["ok"] is True
            assert checked.structured_content["authority"] == "NON_CANONICAL"

            pack = await client.call_tool("context_pack", {"limit": 10})
            assert pack.is_error is False
            p = pack.structured_content
            assert p["project"] == "allowed"
            assert p["canon_authority"] is False
            assert len(p["runes"]) == 1
            assert p["runes"][0]["source_ref"] == "opaque:allowed-one"
            assert "other-one" not in str(p)

            command = await client.call_tool(
                "relic_command", {"message": "@ReLiC Status"}
            )
            assert command.is_error is False
            assert command.structured_content["status"] == "OK"
            assert command.structured_content["remote_service"] == "NOT_CHECKED"
            assert command.structured_content["local_chain"]["ok"] is True

            setup = await client.call_tool(
                "relic_command", {"message": "@ReLiC Setup google_drive"}
            )
            assert setup.is_error is False
            assert setup.structured_content["status"] == "SETUP_REQUIRED"
            assert setup.structured_content["setup"]["connection_verified"] is False
            assert setup.structured_content["setup"]["provider"] == "google_drive"
            assert setup.structured_content["setup"]["write_authority"] is False

            blocked = await client.call_tool(
                "relic_command", {"message": "@ReLiC Save"}
            )
            assert blocked.is_error is False
            assert blocked.structured_content["status"] == "UNAVAILABLE"
            assert blocked.structured_content["automated_write"] is False

            found = await client.call_tool(
                "find_events", {"kind": "OBSERVATION", "limit": 10}
            )
            assert found.is_error is False
            f = found.structured_content
            assert f["project"] == "allowed"
            assert len(f["matches"]) == 1
            assert f["matches"][0]["source_ref"] == "opaque:allowed-one"

    asyncio.run(asyncio.wait_for(exercise(), timeout=30))


def test_corrupt_chain_discloses_nothing_over_stdio(tmp_path):
    ledger = _fixture(tmp_path)
    with sqlite3.connect(ledger.path) as conn:
        conn.execute("DROP TRIGGER no_event_update")
        conn.execute("UPDATE events SET entry_hash=? WHERE sequence=1", ("b" * 64,))

    async def exercise():
        async with Client(_params(ledger.path), read_timeout_seconds=10) as client:
            checked = await client.call_tool("verify_chain", {})
            assert checked.is_error is False
            assert checked.structured_content["ok"] is False
            for name, args in (
                ("context_pack", {"limit": 10}),
                ("find_events", {"kind": "OBSERVATION"}),
            ):
                result = await client.call_tool(name, args)
                assert result.is_error is False
                body = result.structured_content
                assert body["status"] == "INTEGRITY_FAILURE"
                assert body["records_disclosed"] == 0
                assert "runes" not in body and "matches" not in body

    asyncio.run(asyncio.wait_for(exercise(), timeout=30))
