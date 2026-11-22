# ReLiC setup — bring your own connected storage

Status: **public onboarding contract and local MCP reference**. This document
does not claim that ChatGPT globally registers `@ReLiC`, that the historical
ReLiC MCP service is healthy, or that a mere Drive connection grants access.

## The idea

ReLiC is a **continuity observer for the projects you authorize**, not a new
canonical project database. A user can choose Google Drive, OneDrive, Dropbox,
a local folder, or another provider with equivalent read/write interfaces.
The person's existing project database/files remain authoritative. ReLiC
records are always `NON_CANONICAL` and live separately. No accounts or data
are shared between users.

One project → one explicitly selected source scope → one private ReLiC
evidence area. Store **metadata and opaque source references**, not copies of
sensitive documents, chats, full logs, passwords, tokens or private source.

## Initial setup (human user)

1. **Connect your storage** using the storage provider's legitimate OAuth or
   local OS permissions. Google Drive connected in ChatGPT is useful for
   ChatGPT's available Drive tools, but does not automatically give another
   plugin or generic MCP server Drive permissions. Connect the intended
   ReLiC-capable agent/host too, if it requires separate authorization.
2. **Choose a project** and explicitly select the project source files/folder.
   If there is a project database, keep that as the only authoritative source.
   ReLiC must not replace its records with a chat summary, embedding or
   compiled pointer.
3. **Choose a separate private evidence folder**, such as
   `ReLiC-Continuity/projects/<project>/evidence`. Restrict sharing and
   ownership appropriately. Do not place evidence files inside the canonical
   project database. If connected storage cannot create files, use read-only
   mode until an eligible writable folder is chosen.
4. **Start read-only.** Run `@ReLiC Setup google_drive` in a compatible local
   MCP client, or use `plan_setup(provider="google_drive", project="myproject")`
   in the reference library. For OneDrive, Dropbox or local storage,
   substitute `onedrive`, `dropbox` or `local_directory`.
5. **Verify actual tool permissions.** A host adapter must successfully read
   the exact selected folder and must verify the authenticated account/scope.
   The setup manifest contains only folder references; it is not a credential,
   OAuth grant, or proof of access. ReLiC must report UNKNOWN if its connector
   is missing or refuses access.
6. **Inspect a bounded context pack** and validate that pointers correspond to
   only the approved project. Record unverified claims as UNKNOWN/ERROR;
   no AI memory or recovered string becomes canon automatically.
7. **Optionally enable saving** after a separate direct human decision. The
   host must verify a private, separate evidence folder supports new object
   creation. A real append protocol, verification receipt and permission audit
   are required before declaring an observation persistent. A synthetic test
   receipt is not a ReLiC external-service receipt.
8. **Revocation**: withdraw the app's OAuth grant or folder access at the
   provider, stop future reads/writes, and explicitly decide whether the
   owner-controlled evidence folder should be kept. Never delete canonical
   source files as part of ReLiC uninstallation.

Do not type passwords, API keys, OAuth tokens or recovery codes into a ReLiC
command. Never use this documentation as justification for bypassing
provider/account policies or for accessing another person's data.

## The current implementation's real capabilities

On the review branch `agent-consumers/local-readonly-mcp-2026-11-18`,
`relic_community/storage_onboarding.py` provides:

- `plan_setup(provider, project)`: seven setup steps, labeled
  SETUP_REQUIRED; **not** an external connection.
- `create_binding(...)` / `validate_binding(...)`: strict per-project,
  per-provider, per-folder scope descriptors, with a maximum of 32 explicit
  canonical source references. No credentials or broad account permissions
  accepted.
- `verify_connection(binding, probe)`: checks actual folder identity,
  account scope and read permission *only when the host injects a trusted
  provider probe*. Without one it returns UNKNOWN. To prepare write mode, it
  additionally requires a separate private evidence folder with create
  permission; even then it reports a **future human approval/append gate**,
  not that any write is permitted or completed.
- `@ReLiC Setup [provider]` via `relic_command(message)`: returns the
  bounded onboarding instructions through the local read-only MCP tool.

The pre-existing local SQLite `ContinuityLedger` is a single-host reference
writer. **Do not put an active SQLite file in a Dropbox/Drive/OneDrive sync
folder** and assume concurrent writers or automatic conflict resolution:
file-level synchronization is not a transactional database. Use the
local-only fixture for development until a provider-specific append-only
adapter, replay/fork detection, owner isolation, concurrency handling and
authenticated write receipts are independently verified.

### Connected-agent adapter contract

For a new provider integration the agent host must implement a *trusted* read
probe with inputs `(provider, folder_ref, project)` and return the actual
`folder_ref`, `account_scoped`, and `can_read` fields after making an
authenticated connector call. For an evidence folder it must independently
confirm `private` and `can_create`. File names, project IDs, user messages
and returned document content do **not** count as authentication.

For Google Drive this requires an approved Google Drive connector and
folder metadata/listing operations; a Drive folder URL/id alone is not
enough. For Dropbox, OneDrive, local filesystem, and other providers the
host needs equivalent authorized operations. Every provider adapter must
observe the same per-project allowlist, least privilege, and no-canon-write
boundary.

The returned `READ_ONLY_READY` status certifies a successful **test probe of
the selected folder**, not a public plugin release, a complete record
ingestion, or a durable cloud history. No provider adapter has been bundled
with this public reference yet. Credentials remain entirely in provider
OAuth/host controls.

## Local demonstration (fully functional, no cloud)

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

The final command starts local MCP stdio; a connected client may use its
`relic_command` tool with `@ReLiC Help`, `@ReLiC Setup google_drive`,
`@ReLiC Status`, `@ReLiC Continue` and `@ReLiC Verify chain`. The
only working evidence store here is the explicitly initialized **local**
synthetic SQLite fixture. The demo does not import a Google Drive account.

## Publication and trust gates

- The source repository is already public under Apache-2.0. This onboarding
  feature is a **draft contribution** pending owner review and merge.
- The historical private `@ReLiC` MCP connector returned HTTP 429 at its
  upstream interface on November 21, 2026. That is a service/tool availability
  issue; a local parser does not repair the remote connection.
- A public ChatGPT plugin that orchestrates connected accounts must be
  separately packaged, listed/shared where supported, and authorized by
  each end user. Private personal plugins are not automatically publishable
  to everyone.
- Do not expose a public unauthenticated MCP writer or shared SQLite ledger.
  Authenticated tenant isolation, provider scopes, storage write transactions,
  privacy review, rate limiting and durable receipts must be tested first.

All continuity output remains evidence, never canon.
`ID != REP; REP != TRUTH; UNKNOWN != FACT; MEMORY != CANON.`
