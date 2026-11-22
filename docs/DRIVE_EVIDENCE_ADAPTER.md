# ReLiC Community: Google Drive evidence adapter

Status: REVIEW ONLY. This adapter supports small, project-scoped evidence files through an already authorized Google Drive v3 client. It is NOT the private ReLiC service, the user's canonical project database, or an automatically installed ChatGPT plugin.

## Setup
1. User authenticates to Google Drive through the application host's approved OAuth workflow; never expose access or refresh tokens to ChatGPT, source files, or logs.
2. User chooses one existing private project folder, its authoritative source files, and a SEPARATE private evidence folder.
3. Use the provider-neutral create_binding function from relic_community.storage_onboarding with provider="google_drive" and mode="read_only"; never mistake that descriptor for actual OAuth approval.
4. The host constructs a Google Drive API v3 client from its already authorized credentials and passes that service to DriveEvidenceStore (relic_community.google_drive_evidence).
5. Read-only mode: call store.observe() to list and validate bounded, noncanonical metadata files in the evidence folder, never the canonical folder.
6. To write: obtain direct human approval and a distinct evidence folder whose Google Drive metadata confirms canAddChildren. Create a new binding with mode="append_evidence", and call store.append() with metadata-only fields: kind, state, source_ref, evidence_sha256. A receipt is issued ONLY after creating and reading back the exact Google Drive file.
7. Reopen using an authorized, new session and call observe() again. Keep the project database as the sole authority.

Host-side Python usage (host_oauth_credentials must be provided by a separately authorized OAuth implementation):

    from googleapiclient.discovery import build
    from relic_community.storage_onboarding import create_binding
    from relic_community.google_drive_evidence import DriveEvidenceStore
    drive = build("drive", "v3", credentials=host_oauth_credentials)
    binding = create_binding(
        project="demo", provider="google_drive",
        folder_ref="SELECTED_PROJECT_FOLDER_ID",
        canonical_source_refs=(),
        evidence_folder_ref="SEPARATE_PRIVATE_EVIDENCE_FOLDER_ID",
        mode="read_only",
    )
    print(DriveEvidenceStore(drive, binding).observe())

When authorized separately for evidence writing, replace mode with "append_evidence" and use:

    receipt = DriveEvidenceStore(drive, approved_binding).append(
        {"kind": "TEST_RESULT", "state": "PASS",
         "source_ref": "opaque:synthetic-test", "evidence_sha256": None},
        event_id="synthetic-demo-1",
    )

Install Google SDK only for an actual Google API client; the ReLiC reference core does not require it. This adapter uses Drive files.create multipart upload, files.list, files.get, and files.get_media through the authorized service.

## Safety, error and release gates

- Google Drive filenames are NOT unique. A host must ensure single-writer operation; readback and duplicate detection are not an atomic transaction across concurrent accounts.
- A Drive admin can modify or delete files. Provider readback and SHA-256 checks are NOT an immutable externally anchored ReLiC history receipt or factual proof.
- On ambiguous post-create failure, UnverifiedWrite is raised. Do not automatically retry: the file may exist.
- Privacy: records are bounded kind/state, opaque/public evidence pointer and optional SHA digest only. No sensitive source contents, chats, secret tokens, raw private files or canon writes.
- Connecting Drive to ChatGPT does not automatically authorize another MCP process. The local historical ReLiC connector may still fail with HTTP 429.
- No broad account read, public anonymous writer, multi-tenant hosting, private database publishing, or user impersonation.
- Provider-specific login/onboarding, independent security review and real account tests remain release gates for public installation.

Verify the synthetic adapter: python -m pytest -q tests/test_google_drive_evidence.py

Official reference: https://developers.google.com/workspace/drive/api/guides/manage-uploads

ID != REP; REP != TRUTH; UNKNOWN != FACT; MEMORY != CANON.
