"""Local append-only continuity evidence ledger.

NOT the original ReLiC server or a canonical source of truth. Not a secured
network service. All API results are explicitly NON_CANONICAL. Persist metadata
and opaque references only; never user data, PII, prompts, secrets or credentials.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import re
import sqlite3
import os
from typing import Callable

_DOMAIN = b"RELIC-COMMUNITY-CHAIN-V1\0"
_GENESIS = "0" * 64
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_REF = re.compile(r"^(?:opaque|public):[A-Za-z0-9._/-]{1,120}$")
_HASH = re.compile(r"^[a-f0-9]{64}$")
_KINDS = frozenset({"OBSERVATION", "DECISION_RECORD", "IMPLEMENTATION_EVIDENCE",
    "TEST_RESULT", "HYPOTHESIS", "WARNING", "ERROR", "CONTRADICTION",
    "COMPLIANCE_CHECK", "DRIFT", "UNKNOWN"})
_STATES = frozenset({"PASS", "FAIL", "PARTIAL", "UNKNOWN", "OBSERVED", "PROPOSED", "UNAVAILABLE"})
# A deliberately restrictive local identifier, not a substitute for privacy review.
_SUMMARY = re.compile(r"^[A-Za-z0-9 _.,:;!?#()\-/]{1,180}$")

class ValidationError(ValueError):
    """Invalid event metadata (fails closed)."""

@dataclass(frozen=True)
class Receipt:
    sequence: int
    entry_hash: str
    previous_hash: str
    recorded_at: str
    authority: str = "NON_CANONICAL"
    provenance: str = "LOCAL_LEDGER"

@dataclass(frozen=True)
class ChainReport:
    ok: bool
    checked: int
    failure_sequence: int | None
    head_hash: str
    independently_anchored: bool = False


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(seq: int, prior: str, payload: str) -> str:
    return sha256(_DOMAIN + _canonical({"sequence": seq, "previous_hash": prior,
                                       "event": json.loads(payload)})).hexdigest()


def _check_id(s: str, field: str) -> str:
    if not isinstance(s, str) or not _ID.fullmatch(s):
        raise ValidationError(f"{field} must be a bounded opaque identifier")
    return s


def _check_ref(ref: str) -> str:
    if not isinstance(ref, str) or not _REF.fullmatch(ref):
        raise ValidationError("source_ref must be a bounded public:/opaque: reference")
    return ref


def _check_summary(s: str) -> str:
    if not isinstance(s, str) or not _SUMMARY.fullmatch(s):
        raise ValidationError("summary must be short non-sensitive metadata without URLs/emails")
    if any(v in s.lower() for v in ("password", "api_key", "secret", "access_token", "ssn")):
        raise ValidationError("Do not place secrets or PII in the ledger")
    return s


def _verify_rows(rows: list[sqlite3.Row]) -> ChainReport:
    previous = _GENESIS
    for expected,row in enumerate(rows,1):
        try:
            valid_link = (row['sequence'] == expected and
                          row['previous_hash'] == previous and
                          row['entry_hash'] == _digest(expected, previous, row['payload']))
        except (ValueError, TypeError, json.JSONDecodeError):
            valid_link = False
        if not valid_link:
            return ChainReport(False, expected-1, expected, previous)
        try:
            body = json.loads(row['payload'])
            if (body['authority'] != 'NON_CANONICAL' or body['schema'] != 'relic.community.event.v1'
                or body['project'] != row['project'] or body['state'] != row['state']
                or body['kind'] != row['kind'] or body['source_ref'] != row['source_ref']
                or body['recorded_at'] != row['recorded_at']):
                return ChainReport(False,expected-1,expected,previous)
        except (KeyError,TypeError,ValueError):
            return ChainReport(False,expected-1,expected,previous)
        previous = row['entry_hash']
    return ChainReport(True,len(rows),None,previous)


class ContinuityLedger:
    """Dedicated local writer. Put each security domain in a separate DB file.

    Caller must enforce authentication and OS filesystem permissions; this class
    deliberately exposes no public network route. DB triggers and hash chain are
    tamper-evident aids, *not* tamper-proof independent attestations.
    """
    def __init__(self, file: str | Path, *, clock: Callable[[], datetime] | None = None):
        self.path = Path(file)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._init()
        # Local SQLite storage defaults to private owner permissions on POSIX.
        # This is defense in depth, not a replacement for host access controls.
        if os.name == "posix":
            self.path.chmod(0o600)

    def _connect(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA busy_timeout=30000")
        c.execute("PRAGMA foreign_keys=ON")
        return c

    def _init(self) -> None:
        with self._connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS events(
              sequence INTEGER PRIMARY KEY AUTOINCREMENT,
              project TEXT NOT NULL,
              kind TEXT NOT NULL,
              state TEXT NOT NULL,
              source_ref TEXT NOT NULL,
              recorded_at TEXT NOT NULL,
              payload TEXT NOT NULL,
              previous_hash TEXT NOT NULL,
              entry_hash TEXT NOT NULL UNIQUE
            );
            CREATE TRIGGER IF NOT EXISTS no_event_update
              BEFORE UPDATE ON events BEGIN SELECT RAISE(ABORT,'append-only'); END;
            CREATE TRIGGER IF NOT EXISTS no_event_delete
              BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'append-only'); END;
            CREATE INDEX IF NOT EXISTS event_project ON events(project,sequence);
            """)

    def append(self, *, project: str, actor: str, kind: str, state: str,
               source_ref: str, summary: str, evidence_sha256: str | None = None) -> Receipt:
        """Append one observation and return a local receipt (never a canon write)."""
        project = _check_id(project, 'project')
        actor = _check_id(actor, 'actor')
        if kind not in _KINDS: raise ValidationError("Unknown event kind")
        if state not in _STATES: raise ValidationError("Unknown event state")
        source_ref = _check_ref(source_ref)
        summary = _check_summary(summary)
        if evidence_sha256 is not None and (not isinstance(evidence_sha256,str) or
                                           not _HASH.fullmatch(evidence_sha256)):
            raise ValidationError("Evidence hash must be lowercase SHA-256 or omitted")
        instant = self._clock()
        if instant.tzinfo is None: raise ValidationError("Clock must be timezone-aware")
        recorded_at = instant.astimezone(timezone.utc).isoformat(timespec='microseconds')
        payload = _canonical({"schema":"relic.community.event.v1", "project":project,
                              "actor":actor,"kind":kind,"state":state,
                              "source_ref":source_ref,"summary":summary,
                              "evidence_sha256":evidence_sha256,
                              "recorded_at":recorded_at,"authority":"NON_CANONICAL"}).decode('utf-8')
        # Hold SQLite's write lock while checking and appending: no race with
        # another dedicated writer on the same database file.
        with self._connect() as c:
            c.execute("BEGIN IMMEDIATE")
            existing = c.execute("SELECT * FROM events ORDER BY sequence").fetchall()
            if not _verify_rows(existing).ok:
                raise ValidationError("Existing continuity chain failed integrity checks")
            last = existing[-1] if existing else None
            seq = int(last['sequence']) + 1 if last is not None else 1
            prev = str(last['entry_hash']) if last is not None else _GENESIS
            h = _digest(seq,prev,payload)
            c.execute("INSERT INTO events(sequence,project,kind,state,source_ref,recorded_at,payload,previous_hash,entry_hash) VALUES (?,?,?,?,?,?,?,?,?)",
                      (seq,project,kind,state,source_ref,recorded_at,payload,prev,h))
        return Receipt(seq,h,prev,recorded_at)

    def observer(self) -> 'Observer':
        return Observer(self.path)


class Observer:
    """Read-only observer: no append method. No public network exposure."""
    def __init__(self, file: str | Path): self.path = Path(file)

    def _connect(self) -> sqlite3.Connection:
        # mode=ro enforces read-only at the database connection layer.
        c = sqlite3.connect(self.path.as_uri() + '?mode=ro',uri=True)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA query_only=ON")
        return c

    def verify(self) -> ChainReport:
        with self._connect() as c:
            rows = c.execute("SELECT * FROM events ORDER BY sequence").fetchall()
        return _verify_rows(rows)

    def get_event(self, sequence: int) -> dict | None:
        if type(sequence) is not int or sequence < 1: raise ValidationError('Invalid sequence')
        with self._connect() as c:
            row=c.execute('SELECT payload,entry_hash,previous_hash,sequence FROM events WHERE sequence=?',(sequence,)).fetchone()
        if row is None: return None
        return {'sequence':row['sequence'],'entry_hash':row['entry_hash'],
                'previous_hash':row['previous_hash'],'event':json.loads(row['payload']),
                'authority':'NON_CANONICAL'}

    def context_pack(self, project: str, *, limit: int=10) -> dict:
        _check_id(project,'project')
        if type(limit) is not int or not 1 <= limit <= 50: raise ValidationError('limit 1..50')
        with self._connect() as c:
            rows=c.execute('SELECT sequence,kind,state,source_ref,recorded_at,entry_hash FROM events WHERE project=? ORDER BY sequence DESC LIMIT ?', (project,limit)).fetchall()
        return {'schema':'relic.community.context.v1', 'authority':'NON_CANONICAL',
                'project':project, 'coverage':'BOUNDED_LOCAL_EVIDENCE_ONLY',
                'runes':[{'sequence':r['sequence'],'kind':r['kind'],'state':r['state'],
                          'source_ref':r['source_ref'],'recorded_at':r['recorded_at'],
                          'entry_hash':r['entry_hash']} for r in rows],
                'independently_verified':False, 'canon_authority':False}

    def search(self, project: str, kind: str, *, limit:int=20) -> dict:
        _check_id(project,'project')
        if kind not in _KINDS: raise ValidationError('Unknown event kind')
        if type(limit) is not int or not 1 <= limit <= 50: raise ValidationError('limit 1..50')
        with self._connect() as c:
            rows=c.execute('SELECT sequence,entry_hash,state,source_ref FROM events WHERE project=? AND kind=? ORDER BY sequence DESC LIMIT ?',(project,kind,limit)).fetchall()
        return {'authority':'NON_CANONICAL','project':project,'kind':kind,
                'matches':[dict(r) for r in rows]}
