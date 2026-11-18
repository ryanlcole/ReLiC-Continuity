"""Local read-only tools for AI consumers of ReLiC Community evidence.

The owning human chooses one existing database and one project. No network,
writer, external ReLiC service, or canonical authority is introduced here.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from .ledger import Observer, ValidationError, _check_id


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

    def _guard(self) -> dict[str, Any] | None:
        # Do not distribute record references from an invalid chain.
        report = self._observer.verify()
        if not report.ok:
            return {
                "authority": "NON_CANONICAL",
                "project": self._project,
                "status": "INTEGRITY_FAILURE",
                "failure_sequence": report.failure_sequence,
                "records_disclosed": 0,
            }
        return None

    def context_pack(self, limit: int = 10) -> dict[str, Any]:
        """Read at most 50 recent, metadata-only runes for the configured project."""
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ValidationError("limit 1..50")
        failure = self._guard()
        if failure is not None:
            return failure
        return self._observer.context_pack(self._project, limit=limit)

    def find_events(self, kind: str, limit: int = 20) -> dict[str, Any]:
        """Search only a known event kind within the configured project."""
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ValidationError("limit 1..50")
        failure = self._guard()
        if failure is not None:
            return failure
        return self._observer.search(self._project, kind, limit=limit)
