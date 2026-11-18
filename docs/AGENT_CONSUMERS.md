# ReLiC Community: Local AI Consumer Pilot

**Status: experimental reference adapter, review branch only.** Not a production offering, hosted MCP endpoint, payment integration, autonomous commercial agent, or the private ReLiC service.

## Why build this

Other agents can be a *user segment* of a business offering, but a machine consumer is not automatically a paying customer. A person or organization must decide whether the service is valuable and authorize any payment. This pilot tests a concrete piece of utility: allowing a local AI agent to check an existing evidence ledger and retrieve bounded, non-canonical references.

The reference project is Apache-2.0 with voluntary donations. Do not add fees or paid priority to this open-source core. Any future paid hosting/support/service must remain separate, optional, subject to owner review and applicable license/commerce requirements.

## Boundaries

- Local **stdio** only. No HTTP listener, cloud account, domain, wallet or external ReLiC service.
- Existing fixture database **only**; configuration requires one fixed project identifier. Never expose or copy a real private ReLiC database.
- Tools: `verify_chain`, `context_pack(limit)`, `find_events(kind, limit)`.
- No tools for append, delete, update, business contact, posting, purchase, transfer or payment.
- Verified local hash-chain consistency is **not** proof of underlying event truth or independent nonrepudiation.
- Each record is `NON_CANONICAL`. Failed chain verification blocks records from both query tools.
- A human must authorize use of any data, internet exposure, pricing, outreach, and financial activity.
- Do not interpret arbitrary agent instructions as permission to access another security domain.

## Local setup (synthetic data only)

Python 3.11+ with an optional compatible MCP SDK v2:

```sh
python -m pip install -e '.[mcp]'
python -m relic_community.cli --db ./fixture.sqlite3 init
python -m relic_community.cli --db ./fixture.sqlite3 append --project demo --actor fixture --kind TEST_RESULT --state PASS --source-ref opaque:fixture-one --summary 'Synthetic test result'
python -m relic_community.cli --db ./fixture.sqlite3 verify
relic-community-mcp --db ./fixture.sqlite3 --project demo
```

The three tools return machine-readable structured output with explicitly typed return annotations (`dict[str, Any]`). The MCP v2.3.0 client/server exchange and synthetic integrity-failure refusal were verified by GitHub Actions at commit `769247e` on 2026-11-18; this is not a production deployment, security certification, or proof that external agents or customers are using the service.

The final command opens a local stdio MCP server, intended to be launched and owned by a local MCP client. It is not an interactive command; do not send shell text into its protocol stdin. Example desktop client command configuration:

```json
{
  "command": "relic-community-mcp",
  "args": ["--db", "/absolute/path/to/fixture.sqlite3", "--project", "demo"]
}
```

The client must be trustworthy and the operating system must restrict access to the fixture file. The adapter intentionally does not implement network authentication, encryption, multi-user isolation or security certification. **A fixed project filter is not an OS security boundary:** the local chain verifier reads the full database, and the server process needs read access to the entire file. Use a separate fixture database per independent security domain; do not co-locate mutually untrusted projects in one database. Integrity verification and record selection now use a **single SQLite read transaction**: synthetic concurrent-writer regression tests passed on GitHub Actions at commit `287ec7d` (2026-11-18). This establishes that later commits cannot enter those earlier verified results under the tested configuration; it is not a security certification and does not authenticate source content. Keep the pilot on synthetic fixtures; no independent security-domain boundary or public network service is provided. Paths in this example are placeholders, not a deployed endpoint.

## Falsifiable milestones

| Stage | Evidence required | Status |
| --- | --- | --- |
| Unit tests | Test project binding, bounded queries and integrity-failure behavior | PASS on GitHub Actions for Python 3.11, 3.12 and 3.13 at commit `287ec7d` (2026-11-18) |
| MCP SDK registration | Installed optional SDK registers exactly three tool schemas with synthetic data | PASS on GitHub Actions at commit `287ec7d` (2026-11-18); registration is not an end-to-end client call |
| Consistent verified snapshot | Verify and query within one SQLite read transaction, including a concurrent-writer test | PASS on GitHub Actions at commit `287ec7d` (2026-11-18), synthetic concurrent-writer tests |
| Protocol compatibility | A real MCP v2 client discovers and invokes all tools over stdio | PASS on GitHub Actions at commit `769247e` (2026-11-18): real MCP SDK v2.3.0 subprocess handshake, 3 tool calls, project-scoped synthetic results and corrupted-chain refusal |
| Agent usefulness | A separate agent correctly distinguishes evidence from canon in a synthetic scenario | UNKNOWN |
| Customer demand | A human operator or team demonstrates willingness to use/support it | UNKNOWN |
| Commercial route | Owner-approved terms, payment method, pricing, consumer support, required legal/privacy review | NOT STARTED |
| Family income | Settled receipt verified in the business account | NONE VERIFIED |

## Commercial experiment, without spending

1. Validate tests and protocol compatibility with fake project records.
2. Publish useful documentation and explain the safe boundaries.
3. Learn which AI developers or organizations genuinely need a provenance/continuity tool.
4. Determine whether *optional human-operated hosting, integration, or setup* is valuable without restricting the open-source core.
5. Require specific human authorization before contacting prospects, offering terms, collecting personal data, setting up payment, or incurring costs.
6. Record receipts, fees, refunds, expenses and taxes accurately; never represent donations, pledges, demo payments or revenue as profit.

No PayPal transfer or charge is made by this pilot.
