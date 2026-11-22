"""Optional local-only MCP stdio server for the ReLiC Community reference.

No HTTP listener, payments, external connector, secrets, or mutation tools.
Use only an existing local database with intentionally non-sensitive fixtures.
Requires the separately installed optional MCP Python SDK v2.
"""
from __future__ import annotations

import argparse
from typing import Any
from .agent_observer import AgentObserver
from .relic_commands import dispatch_command


def create_server(database: str, project: str):
    # MCP SDK v2 renamed FastMCP to MCPServer; v1 import fails in v2.
    # Import only on explicit MCP use: the core ledger remains dependency-free.
    from mcp.server.mcpserver import MCPServer

    observer = AgentObserver(database, project)
    server = MCPServer("ReLiC Community Read-Only")

    @server.tool()
    def verify_chain() -> dict[str, Any]:
        """Verify the local append-only hash chain; no independent truth attestation."""
        return observer.verify_chain()

    @server.tool()
    def context_pack(limit: int = 10) -> dict[str, Any]:
        """Read bounded, non-canonical evidence references for one configured project."""
        return observer.context_pack(limit)

    @server.tool()
    def find_events(kind: str, limit: int = 20) -> dict[str, Any]:
        """Read one supported event kind from one configured project; no raw data."""
        return observer.find_events(kind, limit)

    @server.tool()
    def relic_command(message: str) -> dict[str, Any]:
        """Read-only local @ReLiC command parser; no canon, remote access, or writer."""
        return dispatch_command(message, observer)

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Local-only read-only ReLiC MCP stdio")
    parser.add_argument("--db", required=True, help="existing local fixture database")
    parser.add_argument("--project", required=True, help="single project identifier")
    args = parser.parse_args()
    server = create_server(args.db, args.project)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
