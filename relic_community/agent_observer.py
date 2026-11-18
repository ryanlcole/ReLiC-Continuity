"""Local read-only tools for AI consumers of ReLiC Community evidence.

The owning human chooses one existing database and one project. No network,
writer, external ReLiC service, or canonical authority is introduced here.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .ledger import Observer, ValidationError, _check_id, _verify_rows, _KINDS


class AgentObserver:
    """Bounded, integrity-gated evidence reading within one configured project."""

    __slots__ = ("_observer", "_project")

    def __init__(self, database: str | Path, project: str):
        self._project = _check_id(project, "project")
        path = Path(database).expanduser().resolve(strict=True)
        if not path.is_file():
            raise ValidationError("database must be an existing local file")
        self._observer = Observer(path)  # SQLite opens in mode=ro, query_only=ON.

    def verify_chain(self) -> dict[str, Any]:
        """Check local chain integrity, not factual truth or independent anchoring."""
        report = asdict(self._observer.verify())
        return {"authority": "NON_CANONICAL", "scope": "LOCAL_LEDGER_ONLY", **report}

    def _verified_rows(self, query: str, parameters: tuple) -> tuple[dict | None, list]:
        """Verify and select using the same SQLite read snapshot.

        BEGIN pins a snapshot on the first SELECT. Concurrent commits cannot
        change the selected data before this connection's transaction ends.
        """
        with self._observer._connect() as connection:
            connection.execute("BEGIN")
            try:
                report = _verify_rows(connection.execute(
                    "SELECT * FROM events ORDER BY sequence").fetchall())
                if not report.ok:
                    return ({
                        "authority": "NON_CANONICAL",
                        "project": self._project,
                        "status": "INTEGRITY_FAILURE",
                        "failure_sequence": report.failure_sequence,
                        "records_disclosed": 0,
                    }, [])
                rows = connection.execute(query, parameters).fetchall()
                return None, rows
            finally:
                connection.rollback()

    @staticmethod
    def _validate_limit(limit: int) -> None:
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ValidationError("limit 1..50")

    def context_pack(self, limit: int = 10) -> dict[str, Any]:
        """Read at most 50 recent, metadata-only runes for the configured project."""
        self._validate_limit(limit)
        failure, rows = self._verified_rows(
            "SELECT sequence,kind,state,source_ref,recorded_at,entry_hash "
            "FROM events WHERE project=? ORDER BY sequence DESC LIMIT ?",
            (self._project, limit))
        if failure is not None:
            return failure
        return {
            "schema": "relic.community.context.v1",
            "authority": "NON_CANONICAL",
            "project": self._project,
            "coverage": "BOUNDED_LOCAL_EVIDENCE_ONLY",
            "runes": [{
                "sequence": r["sequence"], "kind": r["kind"], "state": r["state"],
                "source_ref": r["source_ref"], "recorded_at": r["recorded_at"],
                "entry_hash": r["entry_hash"],
            } for r in rows],
            "independently_verified": False,
            "canon_authority": False,
        }

    def find_events(self, kind: str, limit: int = 20) -> dict[str, Any]:
        """Search only a known event kind within the configured project."""
        self._validate_limit(limit)
        if kind not in _KINDS:
            raise ValidationError("Unknown event kind")
        failure, rows = self._verified_rows(
            "SELECT sequence,entry_hash,state,source_ref FROM events "
            "WHERE project=? AND kind=? ORDER BY sequence DESC LIMIT ?",
            (self._project, kind, limit))
        if failure is not None:
            return failure
        return {
            "authority": "NON_CANONICAL",
            "project": self._project,
            "kind": kind,
            "matches": [dict(r) for r in rows],
        }
