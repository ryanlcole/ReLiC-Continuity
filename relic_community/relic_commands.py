"""Public, local-only @ReLiC command router for the ReLiC Community observer.

This is not the private ReLiC service. It never writes, makes a network call,
creates an authenticated identity, or promotes evidence into canonical truth.
"""
from __future__ import annotations

import re
from typing import Any
from .storage_onboarding import PROVIDERS, StorageSetupError, plan_setup

_COMMAND = re.compile(r"^@relic(?:\s+([a-z]+))?(?:\s+([^\r\n]+))?$", re.IGNORECASE)
_SUPPORTED_KINDS = frozenset({
    "OBSERVATION", "DECISION_RECORD", "IMPLEMENTATION_EVIDENCE",
    "TEST_RESULT", "HYPOTHESIS", "WARNING", "ERROR", "CONTRADICTION",
    "COMPLIANCE_CHECK", "DRIFT", "UNKNOWN",
})
_SUPPORTED = ("Help", "Setup [google_drive|onedrive|dropbox|local_directory|other]",
              "Status", "Checkup", "Continue", "Load",
              "Verify chain", "Trace <EVENT_KIND>")
_RECOGNIZED = frozenset({
    "help", "status", "checkup", "continue", "load", "relic", "verify", "trace",
    "save", "quit", "pause", "resume", "smile", "wink", "milestone", "drift",
    "guard", "test", "handoff", "next", "idea", "amend", "setup",
})


def dispatch_command(message: str, observer: Any) -> dict[str, Any]:
    """Route literal @ReLiC commands to *local* read-only evidence.

    No raw user text is returned, including on malformed or unsupported input.
    Public consumers must not mistake this adapter for hosted service health,
    evidence authenticity, independent truth, or complete project knowledge.
    """
    base: dict[str, Any] = {
        "schema": "relic.community.command.v1",
        "authority": "NON_CANONICAL",
        "scope": "LOCAL_READ_ONLY_REFERENCE",
        "remote_service": "NOT_CHECKED",
        "project_canon": "NOT_CHECKED",
        "automated_write": False,
    }

    def result(status: str, **extra: Any) -> dict[str, Any]:
        return {**base, "status": status, **extra}

    if type(message) is not str or len(message) > 240 or "\n" in message or "\r" in message:
        return result("INVALID_COMMAND")
    match = _COMMAND.fullmatch(message.strip())
    if not match:
        return result("INVALID_COMMAND")
    command = (match.group(1) or "help").lower()
    argument = (match.group(2) or "").strip()
    if command not in _RECOGNIZED:
        return result("UNKNOWN_COMMAND", supported=list(_SUPPORTED))
    if command == "help":
        if argument:
            return result("UNSUPPORTED_ARGUMENT")
        return result("OK", supported=list(_SUPPORTED),
                      other_commands="UNAVAILABLE_IN_LOCAL_REFERENCE")
    if command == "setup":
        provider = argument.lower() or "google_drive"
        if provider not in PROVIDERS:
            return result("UNSUPPORTED_PROVIDER", supported_providers=list(PROVIDERS))
        return result("SETUP_REQUIRED", setup=plan_setup(
            provider=provider, project=observer._project
        ))
    if command in ("relic", "continue", "load"):
        if argument:
            return result("UNSUPPORTED_ARGUMENT")
        context = observer.context_pack(limit=10)
        if context.get("status") == "INTEGRITY_FAILURE":
            return result("INTEGRITY_FAILURE", context=context, records_disclosed=0)
        return result("OK", command="Continue", context=context,
                      coverage="LOCAL_FIXTURE_ONLY; NOT_A_FULL_PROJECT_RECONCILIATION")
    if command in ("status", "checkup"):
        if argument:
            return result("UNSUPPORTED_ARGUMENT")
        verification = observer.verify_chain()
        ok = verification.get("ok") is True
        response = result("OK" if ok else "INTEGRITY_FAILURE",
                          command=command.capitalize(),
                          local_chain=verification,
                          external_connections="UNKNOWN",
                          deployment="NOT_CHECKED",
                          source_identity="LOCAL_SQLITE_REFERENCE")
        if ok:
            response["context"] = observer.context_pack(limit=1)
        else:
            response["records_disclosed"] = 0
        return response
    if command == "verify":
        if argument.lower() not in ("chain", "ledger", "local chain", "local hash chain"):
            return result("UNKNOWN", reason="EXTERNAL_CLAIM_NOT_VERIFIABLE_BY_LOCAL_ADAPTER")
        check = observer.verify_chain()
        return result("PASS" if check.get("ok") is True else "FAIL",
                      local_chain=check,
                      guarantee="LOCAL_HASH_CONSISTENCY_ONLY_NOT_FACTUAL_TRUTH")
    if command == "trace":
        kind = argument.upper()
        if kind not in _SUPPORTED_KINDS:
            return result("UNKNOWN", reason="TRACE_REQUIRES_A_KNOWN_LOCAL_EVENT_KIND")
        found = observer.find_events(kind, limit=10)
        if found.get("status") == "INTEGRITY_FAILURE":
            return result("INTEGRITY_FAILURE", result=found, records_disclosed=0)
        return result("OK", command="Trace", result=found,
                      guarantee="LOCAL_BOUNDED_METADATA_ONLY")
    if command == "save":
        return result("UNAVAILABLE", reason="PUBLIC_ADAPTER_HAS_NO_WRITER")
    if command in ("pause", "resume", "quit"):
        return result("UNAVAILABLE", reason="SESSION_CONTROL_MUST_BE_ENFORCED_BY_CLIENT")
    return result("UNAVAILABLE", reason="REQUIRES_AUTHORITATIVE_EXTERNAL_CONTEXT_OR_EXPLICIT_HUMAN_ACTION")
