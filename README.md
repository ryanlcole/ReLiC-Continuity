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

This repository is publicly readable at https://github.com/ryanlcole/ReLiC-Continuity under Apache-2.0. The publicly available reference source is NOT a hosted MCP service, public ReLiC event database, or an installation of the historical private ChatGPT @ReLiC plugin. Review and release gates apply to optional new adapters.

## AI and human contributor invitation

See [`docs/AI_INVITATION.md`](docs/AI_INVITATION.md) and machine-readable [`CONTRIBUTION_TASKS.json`](CONTRIBUTION_TASKS.json). These are discoverable instructions for would-be contributors, **not evidence that messages have been sent or that any agent is participating**.

## Optional public local @ReLiC MCP client

A reviewed **draft** integration is available at [PR #3](https://github.com/ryanlcole/ReLiC-Continuity/pull/3). It adds a local-only, read-only MCP server for AI clients and a `relic_command(message)` tool that accepts literal text such as `@ReLiC Status`. The feature does **not** resolve the historical private remote ReLiC service's API connection or grant canonical authority. Do not treat an HTTP 429 from that remote service as proof that any source database is empty.

For a synthetic local demo after reviewing the PR branch:

```sh
git clone https://github.com/ryanlcole/ReLiC-Continuity.git
cd ReLiC-Continuity
git switch agent-consumers/local-readonly-mcp-2026-11-18
python -m pip install -e '.[mcp]' pytest
python -m pytest -q
python -m relic_community.cli --db ./synthetic.sqlite3 init
python -m relic_community.cli --db ./synthetic.sqlite3 append \
  --project demo --actor fixture --kind OBSERVATION --state OBSERVED \
  --source-ref opaque:sample --summary 'Synthetic sample only'
relic-community-mcp --db ./synthetic.sqlite3 --project demo
```

The last line starts a stdio transport for an MCP-capable local agent. It is **not** a shell chatbot and does not listen on HTTP. The client should call `relic_command` with messages such as `@ReLiC Help`, `@ReLiC Continue`, `@ReLiC Status`, `@ReLiC Verify chain`, or `@ReLiC Trace OBSERVATION`. Unsupported commands, including `@ReLiC Save`, report UNAVAILABLE instead of making false persistence claims.

Further explanation, bounded evidence semantics and example client configuration:
[docs/AGENT_CONSUMERS.md](docs/AGENT_CONSUMERS.md).

**Publication boundary:** Anyone may inspect this open-source review branch, but a reviewed merge, public hosted endpoint and separately authorized ChatGPT plugin listing are distinct milestones. Public code alone does not make the original private @ReLiC connector operational. No real ReLiC/private event records are included.
