"""Optional Google Drive v3 evidence adapter for public ReLiC Community.

Requires a caller-supplied, already OAuth-authorized Google Drive API client;
never obtains or stores credentials. Writes only new metadata files under the
explicit private evidence folder, and only with append_evidence binding.
A Google Drive file is not an immutable ledger or historical ReLiC MCP receipt.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from uuid import uuid4
import json
import re
from typing import Any, Callable
from .storage_onboarding import validate_binding, StorageSetupError

SCHEMA = "relic.community.drive.evidence.v1"
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_HASH = re.compile(r"^[a-f0-9]{64}$")
_REF = re.compile(r"^(opaque|public):[A-Za-z0-9._/-]{1,120}$")
_KINDS = frozenset(("OBSERVATION", "IMPLEMENTATION_EVIDENCE", "TEST_RESULT",
    "HYPOTHESIS", "WARNING", "ERROR", "CONTRADICTION", "COMPLIANCE_CHECK",
    "DRIFT", "UNKNOWN"))
_STATES = frozenset(("PASS", "FAIL", "PARTIAL", "UNKNOWN", "OBSERVED",
                     "PROPOSED", "UNAVAILABLE"))


class EvidenceError(RuntimeError):
    pass


class UnverifiedWrite(EvidenceError):
    """Create may have succeeded; caller must reconcile before retry."""


@dataclass(frozen=True)
class DriveReceipt:
    file_id: str
    event_id: str
    digest: str
    project: str
    authority: str = "NON_CANONICAL"
    verification: str = "PROVIDER_READBACK_NOT_IMMUTABLE_LEDGER"


def _json(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "kind", "state", "source_ref", "evidence_sha256"
    }:
        raise EvidenceError("Only bounded metadata fields are allowed")
    if (value["kind"] not in _KINDS or value["state"] not in _STATES
        or type(value["source_ref"]) is not str
        or not _REF.fullmatch(value["source_ref"])
        or (value["evidence_sha256"] is not None and (
            type(value["evidence_sha256"]) is not str
            or not _HASH.fullmatch(value["evidence_sha256"])))):
        raise EvidenceError("Invalid evidence metadata")
    return dict(value)


class DriveEvidenceStore:
    def __init__(self, service: Any, binding: dict[str, Any],
                 media_factory: Callable[[bytes], Any] | None = None):
        self.binding = validate_binding(binding)
        if self.binding["provider"] != "google_drive":
            raise StorageSetupError("Google Drive provider required")
        if not self.binding["evidence_folder_ref"]:
            raise StorageSetupError("A distinct evidence folder is required")
        self._service = service
        self._media_factory = media_factory or self._media

    @staticmethod
    def _media(raw: bytes) -> Any:
        from googleapiclient.http import MediaIoBaseUpload
        return MediaIoBaseUpload(BytesIO(raw), mimetype="application/json",
                                resumable=False)

    @property
    def folder(self) -> str:
        return self.binding["evidence_folder_ref"]

    @property
    def project(self) -> str:
        return self.binding["project"]

    def _verify_folder(self, writing: bool = False) -> None:
        try:
            obj = self._service.files().get(
                fileId=self.folder, fields="id,mimeType,trashed,capabilities(canAddChildren)"
            ).execute()
        except Exception as exc:
            raise EvidenceError("Evidence folder unavailable") from exc
        if (not isinstance(obj, dict) or obj.get("id") != self.folder
            or obj.get("mimeType") != "application/vnd.google-apps.folder"
            or obj.get("trashed") is True):
            raise EvidenceError("Invalid evidence folder")
        if writing and obj.get("capabilities", {}).get("canAddChildren") is not True:
            raise EvidenceError("Evidence folder does not grant creation")

    def _items(self) -> list[dict[str, Any]]:
        self._verify_folder()
        items, page = [], None
        for _ in range(20):
            args = {"q": f"'{self.folder}' in parents and trashed = false",
                    "fields": "nextPageToken,files(id,name,mimeType,parents,appProperties,trashed)",
                    "pageSize": 100}
            if page is not None:
                args["pageToken"] = page
            try:
                data = self._service.files().list(**args).execute()
            except Exception as exc:
                raise EvidenceError("Evidence listing failed") from exc
            if not isinstance(data, dict) or not isinstance(data.get("files"), list):
                raise EvidenceError("Unexpected evidence listing")
            for obj in data["files"]:
                if not isinstance(obj, dict):
                    raise EvidenceError("Unexpected listing entry")
                tags = obj.get("appProperties") or {}
                if tags.get("relic_schema") == SCHEMA and tags.get("project") == self.project:
                    if self.folder not in (obj.get("parents") or []) or obj.get("trashed"):
                        raise EvidenceError("Evidence outside selected folder")
                    items.append(obj)
            page = data.get("nextPageToken")
            if not page:
                return items
        raise EvidenceError("Evidence list exceeds bound")

    def _read(self, meta: dict[str, Any]) -> dict[str, Any]:
        if meta.get("mimeType") != "application/json":
            raise EvidenceError("Unexpected evidence MIME")
        try:
            raw = self._service.files().get_media(fileId=meta["id"]).execute()
        except Exception as exc:
            raise EvidenceError("Evidence read failed") from exc
        if type(raw) is not bytes or len(raw) > 4096:
            raise EvidenceError("Evidence body invalid or oversized")
        try:
            data = json.loads(raw)
            if (not isinstance(data, dict) or set(data) != {
                "schema", "project", "event_id", "authority", "metadata", "sha256"
            } or data["schema"] != SCHEMA or data["project"] != self.project
                or data["authority"] != "NON_CANONICAL"
                or type(data["event_id"]) is not str or not _ID.fullmatch(data["event_id"])
                or type(data["sha256"]) is not str or not _HASH.fullmatch(data["sha256"])
                or _metadata(data["metadata"]) != data["metadata"]):
                raise EvidenceError("Evidence schema mismatch")
            unsigned = {k: v for k, v in data.items() if k != "sha256"}
            if sha256(_json(unsigned)).hexdigest() != data["sha256"]:
                raise EvidenceError("Evidence checksum mismatch")
            if meta.get("name") != f"relic-{data['event_id']}.json":
                raise EvidenceError("Evidence file name mismatch")
        except (ValueError, TypeError, KeyError, UnicodeDecodeError) as exc:
            raise EvidenceError("Invalid evidence JSON") from exc
        return data

    def observe(self, maximum: int = 100) -> dict[str, Any]:
        if type(maximum) is not int or not 1 <= maximum <= 100:
            raise EvidenceError("Invalid record bound")
        items = self._items()
        if len(items) > maximum:
            raise EvidenceError("Evidence exceeds selected bound")
        records = [self._read(item) for item in items]
        names = [x["event_id"] for x in records]
        if len(names) != len(set(names)):
            raise EvidenceError("Duplicate evidence event IDs")
        records.sort(key=lambda x: x["event_id"])
        return {"schema": SCHEMA, "project": self.project,
                "authority": "NON_CANONICAL", "status": "PROVIDER_READBACK",
                "immutable": False, "canon_authority": False, "records": records}

    def append(self, metadata: dict[str, Any], *, event_id: str | None = None) -> DriveReceipt:
        if self.binding["mode"] != "append_evidence":
            raise PermissionError("Owner-approved evidence binding required")
        self._verify_folder(writing=True)
        clean = _metadata(metadata)
        key = event_id or uuid4().hex
        if type(key) is not str or not _ID.fullmatch(key):
            raise EvidenceError("Invalid event ID")
        if any(item.get("name") == f"relic-{key}.json" for item in self._items()):
            raise EvidenceError("Existing event ID; reconcile before retry")
        unsigned = {"schema": SCHEMA, "project": self.project, "event_id": key,
                    "authority": "NON_CANONICAL", "metadata": clean}
        record = {**unsigned, "sha256": sha256(_json(unsigned)).hexdigest()}
        body = {"name": f"relic-{key}.json", "parents": [self.folder],
                "mimeType": "application/json",
                "appProperties": {"relic_schema": SCHEMA, "project": self.project}}
        try:
            out = self._service.files().create(
                body=body, media_body=self._media_factory(_json(record)),
                fields="id,name,mimeType,parents,appProperties,trashed"
            ).execute()
        except Exception as exc:
            raise UnverifiedWrite("Creation failed or outcome unknown") from exc
        if not isinstance(out, dict) or not isinstance(out.get("id"), str):
            raise UnverifiedWrite("Provider returned no file identifier")
        try:
            confirmed = self._service.files().get(
                fileId=out["id"], fields="id,name,mimeType,parents,appProperties,trashed"
            ).execute()
            if (confirmed.get("id") != out["id"] or
                self.folder not in (confirmed.get("parents") or []) or
                confirmed.get("appProperties", {}).get("project") != self.project
                or self._read(confirmed) != record):
                raise EvidenceError("Readback content or scope did not match")
        except Exception as exc:
            raise UnverifiedWrite("May have created file, readback unverified") from exc
        return DriveReceipt(out["id"], key, record["sha256"], self.project)
