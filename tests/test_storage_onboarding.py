"""Synthetic-only setup-contract tests; no external accounts or writes."""
from copy import deepcopy
import pytest

from relic_community.storage_onboarding import (
    SCHEMA, StorageSetupError, create_binding, plan_setup,
    validate_binding, verify_connection,
)


def sample(mode="read_only"):
    return create_binding(
        project="demo", provider="google_drive",
        folder_ref="project-folder-id",
        canonical_source_refs=("document-one", "document-two"),
        evidence_folder_ref="relic-evidence-only",
        mode=mode,
    )


def fake_probe(provider, folder_ref, project):
    assert provider == "google_drive"
    assert project == "demo"
    return {
        "folder_ref": folder_ref, "account_scoped": True,
        "can_read": True, "can_create": folder_ref == "relic-evidence-only",
        "private": folder_ref == "relic-evidence-only",
    }


@pytest.mark.parametrize("provider", ["google_drive", "dropbox", "onedrive",
                                      "local_directory", "other"])
def test_setup_plans_are_noncanonical_and_require_real_connector(provider):
    plan = plan_setup(provider=provider, project="demo")
    assert plan["schema"] == SCHEMA
    assert plan["status"] == "SETUP_REQUIRED"
    assert plan["connection_verified"] is False
    assert plan["write_authority"] is False
    assert any("authoritative" in x for x in plan["instructions"])
    assert "host-specific adapter" in plan["limitations"]


def test_binding_is_exact_scoped_metadata_not_authentication():
    binding = sample()
    assert validate_binding(binding) == binding
    assert binding["authority"] == "NON_CANONICAL"
    assert binding["mode"] == "read_only"
    assert "password" not in str(binding).lower()
    assert verify_connection(binding, None)["status"] == "UNKNOWN"


def test_real_adapter_probe_is_required_for_read_only_readiness():
    binding = sample()
    ready = verify_connection(binding, fake_probe)
    assert ready["status"] == "READ_ONLY_READY"
    assert ready["connection_verified"] is True
    assert ready["write_authority"] is False
    assert ready["canon_write_authority"] is False


def test_incorrect_scopes_and_provider_fail_closed():
    binding = sample()
    denied = verify_connection(binding, lambda p, f, j: {
        "folder_ref": "another-user-folder", "can_read": True,
        "account_scoped": True,
    })
    assert denied["status"] == "ACCESS_DENIED"
    denied = verify_connection(binding, lambda p, f, j: {
        "folder_ref": f, "can_read": False, "account_scoped": True,
    })
    assert denied["status"] == "ACCESS_DENIED"
    assert verify_connection(binding, lambda *args: 1 / 0)["status"] == "PROVIDER_UNAVAILABLE"


def test_write_mode_requires_separate_private_folder_and_still_cannot_write():
    binding = sample(mode="append_evidence")
    result = verify_connection(binding, fake_probe)
    assert result["status"] == "EVIDENCE_FOLDER_VERIFIED"
    assert result["write_authority"] is False
    assert result["next_gate"] == "DIRECT_HUMAN_APPROVAL_AND_APPEND_PROTOCOL"
    denied = verify_connection(binding, lambda p, f, j: {
        "folder_ref": f, "account_scoped": True,
        "can_read": True, "can_create": True, "private": False,
    })
    assert denied["status"] == "EVIDENCE_WRITE_DENIED"
    assert denied["write_authority"] is False


def test_no_canonical_overwrite_or_folder_reuse():
    with pytest.raises(StorageSetupError):
        create_binding(project="demo", provider="google_drive", folder_ref="x",
                       mode="append_evidence")
    with pytest.raises(StorageSetupError):
        create_binding(project="demo", provider="google_drive", folder_ref="x",
                       evidence_folder_ref="x", mode="append_evidence")
    with pytest.raises(StorageSetupError):
        create_binding(project="demo", provider="google_drive", folder_ref="x",
                       canonical_source_refs=("doc",),
                       evidence_folder_ref="doc", mode="append_evidence")


@pytest.mark.parametrize("bad", [
    {"project": "../private"}, {"provider": "not-connected"},
    {"folder_ref": "https://example.invalid/?token=secret"},
    {"canonical_source_refs": ("ok", "ok")},
    {"canonical_source_refs": ("ok", "<PRIVATE>")},
    {"mode": "overwrite_canon"},
])
def test_reject_untrusted_binding_fields(bad):
    kwargs = dict(project="demo", provider="google_drive", folder_ref="x",
                  canonical_source_refs=(), evidence_folder_ref=None,
                  mode="read_only")
    kwargs.update(bad)
    with pytest.raises(StorageSetupError):
        create_binding(**kwargs)


def test_reject_manifest_additions_and_canon_claims():
    b = sample()
    for bad in (
        {**b, "password": "leak"},
        {**b, "authority": "CANONICAL"},
        {**b, "schema": "unknown"},
        {**b, "project": "other"},
    ):
        if bad.get("project") == "other":
            # Different project binding would be valid but isolated;
            # verification must still check the actual project's folder.
            assert validate_binding(bad)["project"] == "other"
            continue
        with pytest.raises(StorageSetupError):
            validate_binding(bad)


def test_each_canonical_source_requires_its_own_proven_read_access():
    binding = sample()
    called = []

    def restricted(provider, folder_ref, project):
        called.append(folder_ref)
        return {
            "folder_ref": folder_ref, "account_scoped": True,
            "can_read": folder_ref != "document-two",
        }

    denied = verify_connection(binding, restricted)
    assert denied["status"] == "SOURCE_ACCESS_DENIED"
    assert denied["write_authority"] is False
    assert called == ["project-folder-id", "document-one", "document-two"]


@pytest.mark.parametrize("ref", [
    "foo/../secrets", "foo/./doc", "foo//doc", "https://drive.google.com/file",
])
def test_unsafe_provider_references_are_never_accepted(ref):
    with pytest.raises(StorageSetupError):
        create_binding(project="demo", provider="other", folder_ref=ref)


def test_no_storage_mutation_is_exposed_by_setup_contract():
    import relic_community.storage_onboarding as module
    assert not hasattr(module, "append_event")
    assert not hasattr(module, "write_project")
    assert not hasattr(module, "delete_project")
    assert not hasattr(module, "create_oauth_token")
