# ReLiC Community Continuity Reference v0.1

**Open-source, offline-first, observer-first reference implementation. Apache-2.0. Donations voluntary.**

This is **new public reference code implementing a bounded subset of ReLiC principles**. It is **not** the former private ReLiC MCP service, a reconstruction of private algorithms, a replacement for project databases, or a deployment of the user's old infrastructure.

## Purpose

Preserve an append-only, tamper-evident **local evidence history** while separating evidence from truth or canon. A ReLiC event records what was *observed or claimed*, the evidence reference, a local timestamp and hash. The authoritative project database determines canon independently.

**ID != REP · REP != TRUTH · UNKNOWN != FACT · MEMORY != CANON.**

## What works

- Local SQLite append-only event table with `UPDATE`/`DELETE` rejection triggers.
- Dedicated `ContinuityLedger.append` entry point returns a local receipt, and `Observer` exposes read-only access.
- Deterministic SHA-256 chain with a canonical JSON profile and integrity checker. Hashes are **not signatures, proof of truth, independent timestamps or external anchors**.
- Bounded, project-filtered context packs (`runes`) and exact-kind search. Context packs never promote records to authority.
- Explicit `NON_CANONICAL` labeling of every record, decision and result.
- Identifier and metadata validation; non-sensitive public/opaque evidence references; no raw project records, chats, source rows or credential fields.
- No mandatory network, no cloud services, no paid functionality, no telemetry.

## Quick start

```sh
python -m pip install -e . pytest
python -m pytest -q
python -m relic_community.cli --db ./relic.sqlite3 init
python -m relic_community.cli --db ./relic.sqlite3 append \
  --project demo --actor dev_agent --kind TEST_RESULT --state PASS \
  --source-ref opaque:fixture-one --summary 'Fixture tests passed'
python -m relic_community.cli --db ./relic.sqlite3 verify
python -m relic_community.cli --db ./relic.sqlite3 context --project demo
```

The database is created on your local machine. Keep it private, set appropriate filesystem permissions, and use **synthetic data** while testing.

## Public/private boundaries

This repository contains **only generic continuity concepts and independently written code**. It does not release private project state, credentials, historic event logs, the private AI composition solver, or unpublished ReLiC implementation files. Do not infer missing source code from memory or context summaries.

The `Observer` has no writer. The `ContinuityLedger` is the **only writer exposed by this reference library**. This does not authorize writing to an external ReLiC MCP server. Owner-authorized canonical decisions remain in separately managed project records; a `DECISION_RECORD` is only evidence that a decision was reported.

The library has no multi-user authentication, remote MCP transport, trusted clock, security certification, external immutability anchor, replication, or operational disaster recovery. It **must not** be attached directly to a public network or used with real sensitive records.

See [AGENTS.md](AGENTS.md), [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), and [docs/CANON_AND_PROVENANCE.md](docs/CANON_AND_PROVENANCE.md).

## Relationship to Grimoire

Grimoire's `relic_observer.py` is a **read-only workflow observer**. This repository provides an independent local continuity reference implementation. They are separately licensed open-source projects; do not automatically ingest Grimoire observations into the continuity database or claim ReLiC receipts until a dedicated, authorized writer actually succeeds.

## Publication status

Prepared for an independently created public GitHub repository. This source archive is not itself proof of GitHub publication. Contributions are welcome through reviewed PRs once its actual repository URL is known.

## AI and human contributor invitation

See [`docs/AI_INVITATION.md`](docs/AI_INVITATION.md) and machine-readable [`CONTRIBUTION_TASKS.json`](CONTRIBUTION_TASKS.json). These are discoverable instructions for would-be contributors, **not evidence that messages have been sent or that any agent is participating**.
