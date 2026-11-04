# AI Agent and Human Developer Rules — ReLiC Community

**Agents are invited to contribute tests, code, audits, and documentation through reviewed pull requests. No agent has autonomous canon authority or permission to expose private records.**

1. **ID != REP; REP != TRUTH; UNKNOWN != FACT; MEMORY != CANON.** Observations, summarized continuity, generated code and GitHub discussions are not canonical owner decisions.
2. Project databases and explicit owner decisions remain canonical. Do not overwrite them, reconstruct withheld algorithms, or treat public demos as the authoritative project.
3. `ContinuityLedger.append` is the **dedicated local reference writer**, not an available external ReLiC writer. A local receipt may not be presented as an external MCP receipt.
4. Never collect, request or disclose secrets, credentials, private logs, PII, unpublished project designs or source records. No training on private data.
5. Maintain append-only event lineage; changes to hash profiles, schema or claim semantics require explicit version migration and backward verification tests.
6. Report **PASS / FAIL / UNKNOWN** with reproducible evidence. Do not mark missing tests, unpublished changes or unavailable services as PASS.
7. Preserve noncanonical status for `DECISION_RECORD` and all other events. A new writer must not rewrite authoritative project data.
8. Follow Apache-2.0 licensing. Do not add license fees, mandatory cloud services, paid priority, tracking or public internet dependencies.
9. Any AI-authored contribution must identify the AI assistance, human sponsor or reviewer, affected behavior and tests. No self-merging, autonomous publishing or unsolicited outreach.
10. Handle security reports privately; do not post exploitation details or real customer data in public issues.

## Starter contributions

- Independent verification of hash-chain edge cases, canonical serialization and schema migrations.
- Separate OS/file permission tests, multi-process append tests and crash-recovery behavior.
- Bounded context improvements without raw data exposure.
- Read-only MCP adapter design using standard authenticated transport; **do not** expose the write endpoint publicly by default.
- Documentation clarity and examples of noncanonical evidence versus canonical decisions.
- Independent provenance anchoring proposals clearly marked experimental.

**AI collaboration invitation:** Fork the public repository, open an issue explaining a reproducible problem, submit focused code and tests, and request human review. Never infer or edit withheld canon.
