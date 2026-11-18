"""Synthetic-only tests for a local, non-canonical AI consumption surface."""
from __future__ import annotations

import sqlite3
import pytest

from relic_community.agent_observer import AgentObserver
from relic_community.ledger import ContinuityLedger, ValidationError


def fixture(tmp_path):
    ledger = ContinuityLedger(tmp_path / "events.sqlite3")
    ledger.append(project="allowed", actor="fixture", kind="OBSERVATION",
                  state="OBSERVED", source_ref="opaque:item-one",
                  summary="No sensitive data")
    ledger.append(project="other", actor="fixture", kind="OBSERVATION",
                  state="OBSERVED", source_ref="opaque:private-project",
                  summary="Outside scope")
    return ledger


def test_bound_to_configured_project(tmp_path):
    ledger = fixture(tmp_path)
    agent = AgentObserver(ledger.path, "allowed")
    pack = agent.context_pack()
    assert pack["authority"] == "NON_CANONICAL"
    assert pack["project"] == "allowed"
    assert len(pack["runes"]) == 1
    assert pack["runes"][0]["source_ref"] == "opaque:item-one"
    assert "private-project" not in str(pack)
    found = agent.find_events("OBSERVATION")
    assert len(found["matches"]) == 1
    assert agent.verify_chain()["ok"] is True


def test_no_local_writer_available(tmp_path):
    agent = AgentObserver(fixture(tmp_path).path, "allowed")
    assert not hasattr(agent, "append")
    assert not hasattr(agent, "write")


@pytest.mark.parametrize("limit", [-1, 0, 51, True, 1.25])
def test_bounds_fail_closed(tmp_path, limit):
    agent = AgentObserver(fixture(tmp_path).path, "allowed")
    with pytest.raises(ValidationError):
        agent.context_pack(limit)
    with pytest.raises(ValidationError):
        agent.find_events("OBSERVATION", limit)


def test_unknown_kind_rejected(tmp_path):
    agent = AgentObserver(fixture(tmp_path).path, "allowed")
    with pytest.raises(ValidationError):
        agent.find_events("CUSTOM_SENSITIVE_DATA")


def test_corrupted_chain_returns_no_records(tmp_path):
    ledger = fixture(tmp_path)
    with sqlite3.connect(ledger.path) as conn:
        conn.execute("DROP TRIGGER no_event_update")
        conn.execute("UPDATE events SET entry_hash = ? WHERE sequence = 1",
                     ("f" * 64,))
    agent = AgentObserver(ledger.path, "allowed")
    assert agent.verify_chain()["ok"] is False
    for result in (agent.context_pack(), agent.find_events("OBSERVATION")):
        assert result["status"] == "INTEGRITY_FAILURE"
        assert result["records_disclosed"] == 0
        assert "runes" not in result and "matches" not in result


def test_only_existing_database_accepted(tmp_path):
    missing = tmp_path / "no-file.sqlite3"
    with pytest.raises(FileNotFoundError):
        AgentObserver(missing, "allowed")
    assert not missing.exists()


def test_invalid_project_rejected(tmp_path):
    with pytest.raises(ValidationError):
        AgentObserver(fixture(tmp_path).path, "../other")


def test_mcp_adapter_import_remains_optional():
    # Optional mcp package is not needed merely to import the module.
    from relic_community.mcp_server import create_server
    assert callable(create_server)
