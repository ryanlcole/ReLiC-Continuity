"""Portable, provider-neutral setup contract for a single user's ReLiC project.

Planning and connection verification ONLY. This module cannot read a Drive
account, impersonate its owner, write continuity data, or make a host plugin
available. Hosts must supply authenticated connector probes for actual access.
"""
from __future__ import annotations

import re
from typing import Any, Callable

SCHEMA = "relic.community.storage.binding.v1"
PROVIDERS = ("google_drive", "onedrive", "dropbox", "local_directory", "other")
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}$")
_ALLOWED_KEYS = frozenset({"schema", "project", "provider", "folder_ref",
                           "canonical_source_refs", "evidence_folder_ref",
                           "mode", "authority"})
_MODES = ("read_only", "append_evidence")


class StorageSetupError(ValueError):
    pass


def _ident(value: Any, label: str) -> str:
    if type(value) is not str or not _ID.fullmatch(value):
        raise StorageSetupError(f"Invalid {label}")
    return value


def _reference(value: Any, label: str) -> str:
    # Opaque provider-owned ID/path, not a URL, password, OAuth token or filename.
    if (type(value) is not str or not _REF.fullmatch(value)
        or value.lower().startswith(("http:", "https:"))
        or any(part in ("", ".", "..") for part in value.split("/"))):
        raise StorageSetupError(f"Invalid {label}")
    return value


def plan_setup(provider: str = "google_drive", project: str = "demo") -> dict[str, Any]:
    """Human-facing setup steps, not a connection or a permission grant."""
    if type(provider) is not str or provider not in PROVIDERS:
        raise StorageSetupError("Unsupported storage provider")
    _ident(project, "project")
    return {
        "schema": SCHEMA,
        "authority": "NON_CANONICAL",
        "project": project,
        "provider": provider,
        "status": "SETUP_REQUIRED",
        "connection_verified": False,
        "write_authority": False,
        "instructions": [
            "Sign in to the selected storage provider using its approved OAuth or local filesystem controls.",
            "Select one private project folder. Do not grant access to the entire account by default.",
            "Select the existing project database or files that are authoritative. ReLiC observes them; it never rewrites them.",
            "Create or designate a separate ReLiC evidence folder, private to that account and project.",
            "Start in read_only mode. The host must check actual folder access through its connected tool.",
            "Only after an explicit direct-user decision, separately enable new evidence-file creation.",
            "Run integrity and privacy checks on a synthetic record before using real project references.",
        ],
        "limitations": (
            "Connection to Google Drive in ChatGPT does not automatically install "
            "this MCP server, authorize its tools, or establish write access. "
            "A host-specific adapter must invoke the connected storage tools."
        ),
    }


def create_binding(*, project: str, provider: str, folder_ref: str,
                   canonical_source_refs: tuple[str, ...] = (),
                   evidence_folder_ref: str | None = None,
                   mode: str = "read_only") -> dict[str, Any]:
    """Describe the human-selected scope; does not verify access or save it."""
    _ident(project, "project")
    if provider not in PROVIDERS:
        raise StorageSetupError("Unsupported storage provider")
    folder_ref = _reference(folder_ref, "folder reference")
    if type(canonical_source_refs) is not tuple or len(canonical_source_refs) > 32:
        raise StorageSetupError("Invalid source list")
    refs = tuple(_reference(ref, "source reference") for ref in canonical_source_refs)
    if len(refs) != len(set(refs)):
        raise StorageSetupError("Duplicate source reference")
    if mode not in _MODES:
        raise StorageSetupError("Unsupported binding mode")
    if evidence_folder_ref is not None:
        evidence_folder_ref = _reference(evidence_folder_ref, "evidence folder")
    if mode == "append_evidence" and (
        evidence_folder_ref is None or evidence_folder_ref == folder_ref
        or evidence_folder_ref in refs):
        raise StorageSetupError("A distinct evidence folder is required for writes")
    return {
        "schema": SCHEMA,
        "authority": "NON_CANONICAL",
        "project": project,
        "provider": provider,
        "folder_ref": folder_ref,
        "canonical_source_refs": list(refs),
        "evidence_folder_ref": evidence_folder_ref,
        "mode": mode,
    }


def validate_binding(value: Any) -> dict[str, Any]:
    """Strictly validate a stored scope descriptor; never treat it as OAuth."""
    if not isinstance(value, dict) or set(value) != _ALLOWED_KEYS:
        raise StorageSetupError("Invalid binding fields")
    if value.get("schema") != SCHEMA or value.get("authority") != "NON_CANONICAL":
        raise StorageSetupError("Unsupported or authoritative binding")
    sources = value.get("canonical_source_refs")
    if not isinstance(sources, list):
        raise StorageSetupError("Invalid source list")
    expected = create_binding(
        project=value["project"], provider=value["provider"],
        folder_ref=value["folder_ref"],
        canonical_source_refs=tuple(sources),
        evidence_folder_ref=value["evidence_folder_ref"], mode=value["mode"],
    )
    if expected != value:
        raise StorageSetupError("Invalid binding encoding")
    return expected


def verify_connection(binding: dict[str, Any],
                      probe: Callable[[str, str, str], dict[str, Any]] | None
                      ) -> dict[str, Any]:
    """An adapter probe must actually verify this scoped folder's capabilities.

    No probe => UNKNOWN, never a fabricated successful connection. A probe is
    host-trusted, not sourced from a user-controlled project file.
    """
    validated = validate_binding(binding)
    result = {
        "schema": SCHEMA, "authority": "NON_CANONICAL",
        "project": validated["project"], "provider": validated["provider"],
        "status": "UNKNOWN", "connection_verified": False, "write_authority": False,
        "canon_write_authority": False,
    }
    if probe is None:
        return result
    try:
        checked = probe(validated["provider"], validated["folder_ref"],
                        validated["project"])
    except Exception:
        return {**result, "status": "PROVIDER_UNAVAILABLE"}
    if not isinstance(checked, dict) or checked.get("folder_ref") != validated["folder_ref"] or (
        checked.get("account_scoped") is not True or checked.get("can_read") is not True):
        return {**result, "status": "ACCESS_DENIED"}
    # A project-folder probe never establishes authorization for unrelated
    # explicitly selected source file IDs. Verify every source independently.
    for source_ref in validated["canonical_source_refs"]:
        try:
            source = probe(validated["provider"], source_ref, validated["project"])
        except Exception:
            return {**result, "status": "SOURCE_ACCESS_UNAVAILABLE"}
        if (not isinstance(source, dict)
            or source.get("folder_ref") != source_ref
            or source.get("account_scoped") is not True
            or source.get("can_read") is not True):
            return {**result, "status": "SOURCE_ACCESS_DENIED"}

    if validated["mode"] == "append_evidence":
        # A separately authorized *evidence* folder must be checked too.
        try:
            target = probe(validated["provider"], validated["evidence_folder_ref"],
                           validated["project"])
        except Exception:
            return {**result, "status": "EVIDENCE_ACCESS_UNAVAILABLE",
                    "connection_verified": True}
        if (not isinstance(target, dict)
            or target.get("folder_ref") != validated["evidence_folder_ref"]
            or target.get("account_scoped") is not True
            or target.get("private") is not True
            or target.get("can_create") is not True):
            return {**result, "status": "EVIDENCE_WRITE_DENIED",
                    "connection_verified": True}
        return {**result, "status": "EVIDENCE_FOLDER_VERIFIED",
                "connection_verified": True, "write_authority": False,
                "next_gate": "DIRECT_HUMAN_APPROVAL_AND_APPEND_PROTOCOL"}
    return {**result, "status": "READ_ONLY_READY", "connection_verified": True}
