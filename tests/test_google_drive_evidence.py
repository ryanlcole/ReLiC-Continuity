"""Synthetic-only Google Drive API v3 adapter tests (no OAuth or internet)."""
import json
import pytest
from relic_community.google_drive_evidence import (
    DriveEvidenceStore, EvidenceError, UnverifiedWrite
)
from relic_community.storage_onboarding import create_binding


class Reply:
    def __init__(self, action):
        self.action = action
    def execute(self):
        return self.action()


class FakeDrive:
    def __init__(self):
        self.docs = {}
        self.raw = {}
        self.creates = 0
        self.writable = True
        self.bad_readback = False
    def files(self):
        return self
    def get(self, **kwargs):
        def callback():
            ident = kwargs["fileId"]
            if ident == "evidence-folder":
                return {"id": ident, "mimeType": "application/vnd.google-apps.folder",
                        "trashed": False, "capabilities": {
                            "canAddChildren": self.writable
                        }}
            return dict(self.docs[ident])
        return Reply(callback)
    def list(self, **kwargs):
        assert "'evidence-folder' in parents" in kwargs["q"]
        return Reply(lambda: {"files": list(self.docs.values())})
    def get_media(self, **kwargs):
        return Reply(lambda: self.raw[kwargs["fileId"]])
    def create(self, **kwargs):
        def callback():
            self.creates += 1
            ident = f"drive-file-{self.creates}"
            obj = {**kwargs["body"], "id": ident, "trashed": False}
            self.docs[ident] = obj
            self.raw[ident] = kwargs["media_body"]
            if self.bad_readback:
                self.raw[ident] = b'{"invalid": true}'
            return dict(obj)
        return Reply(callback)


def binding(mode="read_only"):
    return create_binding(project="demo", provider="google_drive",
                          folder_ref="canonical-folder", canonical_source_refs=("source",),
                          evidence_folder_ref="evidence-folder", mode=mode)


def evidence():
    return {"kind": "TEST_RESULT", "state": "PASS",
            "source_ref": "opaque:synthetic-test",
            "evidence_sha256": "a" * 64}


def test_read_only_starts_empty_and_has_no_mutating_capability():
    drive = FakeDrive()
    store = DriveEvidenceStore(drive, binding(), media_factory=lambda b: b)
    observed = store.observe()
    assert observed["records"] == []
    assert observed["immutable"] is False
    assert observed["canon_authority"] is False
    with pytest.raises(PermissionError):
        store.append(evidence())
    assert drive.creates == 0
    assert not hasattr(store, "delete")
    assert not hasattr(store, "update_canon")


def test_approved_evidence_create_and_cross_session_readback():
    drive = FakeDrive()
    writer = DriveEvidenceStore(drive, binding("append_evidence"),
                                media_factory=lambda b: b)
    receipt = writer.append(evidence(), event_id="first")
    assert receipt.file_id == "drive-file-1"
    assert receipt.event_id == "first"
    assert receipt.authority == "NON_CANONICAL"
    assert receipt.verification == "PROVIDER_READBACK_NOT_IMMUTABLE_LEDGER"
    assert drive.docs[receipt.file_id]["parents"] == ["evidence-folder"]
    assert drive.creates == 1

    new_session = DriveEvidenceStore(drive, binding(), media_factory=lambda b: b)
    records = new_session.observe()["records"]
    assert len(records) == 1
    assert records[0]["metadata"] == evidence()
    assert records[0]["sha256"] == receipt.digest
    assert records[0]["project"] == "demo"


def test_duplicate_event_id_fails_closed_not_silent_rewrite():
    drive = FakeDrive()
    store = DriveEvidenceStore(drive, binding("append_evidence"),
                               media_factory=lambda b: b)
    store.append(evidence(), event_id="same-event")
    with pytest.raises(EvidenceError, match="Existing event ID"):
        store.append(evidence(), event_id="same-event")
    assert drive.creates == 1


def test_tampered_bytes_fail_before_any_records_are_returned():
    drive = FakeDrive()
    store = DriveEvidenceStore(drive, binding("append_evidence"),
                               media_factory=lambda b: b)
    receipt = store.append(evidence(), event_id="tamper")
    changed = json.loads(drive.raw[receipt.file_id])
    changed["metadata"]["state"] = "FAIL"
    drive.raw[receipt.file_id] = json.dumps(changed).encode()
    with pytest.raises(EvidenceError, match="checksum"):
        store.observe()


def test_cross_project_records_never_appear_in_selected_project():
    drive = FakeDrive()
    store = DriveEvidenceStore(drive, binding("append_evidence"),
                               media_factory=lambda b: b)
    store.append(evidence(), event_id="approved")
    # Simulates another project in this same folder: filtered, not imported.
    drive.docs["other"] = {"id": "other", "name": "relic-private.json",
                            "mimeType": "application/json", "parents": ["evidence-folder"],
                            "appProperties": {"relic_schema": "relic.community.drive.evidence.v1",
                                              "project": "another"}}
    drive.raw["other"] = b"private"
    assert len(store.observe()["records"]) == 1


def test_write_permission_and_readback_gate():
    drive = FakeDrive()
    store = DriveEvidenceStore(drive, binding("append_evidence"),
                               media_factory=lambda b: b)
    drive.writable = False
    with pytest.raises(EvidenceError, match="does not grant"):
        store.append(evidence())
    assert drive.creates == 0
    drive.writable = True
    drive.bad_readback = True
    with pytest.raises(UnverifiedWrite, match="readback"):
        store.append(evidence(), event_id="ambiguous")
    assert drive.creates == 1  # Ambiguous: must NOT claim success or auto-retry.


@pytest.mark.parametrize("bad", [
    {"source_ref": "https://secret.invalid"}, {"kind": "DECISION_RECORD"},
    {"summary": "private text"}, {"evidence_sha256": "bad"},
])
def test_unbounded_or_sensitive_schema_rejected(bad):
    drive = FakeDrive()
    store = DriveEvidenceStore(drive, binding("append_evidence"),
                               media_factory=lambda b: b)
    metadata = evidence()
    metadata.update(bad)
    with pytest.raises(EvidenceError):
        store.append(metadata, event_id="invalid")
    assert drive.creates == 0


def test_bound_rejects_invalid_limit_and_duplicate_remote_name():
    drive = FakeDrive()
    store = DriveEvidenceStore(drive, binding("append_evidence"),
                               media_factory=lambda b: b)
    store.append(evidence(), event_id="bounded")
    with pytest.raises(EvidenceError):
        store.observe(0)
    with pytest.raises(EvidenceError):
        store.observe(True)
    # Drive names are not unique; duplicate event name causes an explicit error.
    original = drive.docs["drive-file-1"].copy()
    drive.docs["duplicate"] = {**original, "id": "duplicate"}
    drive.raw["duplicate"] = drive.raw["drive-file-1"]
    with pytest.raises(EvidenceError, match="Duplicate"):
        store.observe()


def test_no_host_permission_or_real_login_is_made_implicitly():
    drive = FakeDrive()
    store = DriveEvidenceStore(drive, binding(), media_factory=lambda b: b)
    assert not hasattr(store, "login")
    assert not hasattr(store, "grant_owner_authority")
    assert not hasattr(store, "promote_canon")
