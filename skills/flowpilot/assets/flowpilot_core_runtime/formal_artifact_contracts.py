"""Current-contract registry for AI-submitted formal artifact files.

The rows here are intentionally narrow: they describe file-backed artifacts
that a role must submit with a result body and runtime must mechanically
validate. Runtime-owned persistence files and logical subject artifact ids do
not belong in this registry.
"""

from __future__ import annotations

from typing import Any, Mapping


FORMAL_ARTIFACT_FAULT_MODES = (
    "missing_formal_artifact",
    "wrong_formal_artifact_path",
    "invalid_formal_artifact_json",
    "missing_formal_artifact_decision",
    "wrong_formal_artifact_decision",
    "body_pass_artifact_blocks",
)

FLOWGUARD_FORMAL_ARTIFACT_CONTRACT: dict[str, Any] = {
    "contract_id": "flowguard.formal_evidence_artifact",
    "packet_result_family_id": "flowguard_check.post_result",
    "artifact_id": "flowguard_evidence.json",
    "artifact_type": "json",
    "artifact_owner": "flowguard_operator",
    "artifact_role": "formal_flowguard_evidence",
    "contract_exhaustion_family": "flowguard_check_result",
    "required_when": "body.evidence_output_policy.required_for_formal_run=true",
    "target_root_field": "evidence_output_policy.run_local_evidence_root",
    "required_field_paths": ("model_test_alignment_report.decision",),
    "decision_field_path": "model_test_alignment_report.decision",
    "allowed_value_options": {
        "model_test_alignment_report.decision": ("pass",),
    },
    "field_type_requirements": {
        "model_test_alignment_report.decision": "string:pass",
    },
    "body_only_insufficiency": "A result body alone cannot satisfy this formal evidence contract.",
    "fault_modes": FORMAL_ARTIFACT_FAULT_MODES,
}

FORMAL_ARTIFACT_CONTRACTS = (FLOWGUARD_FORMAL_ARTIFACT_CONTRACT,)

EXCLUDED_LOGICAL_ARTIFACT_PREFIXES = (
    "subject_packet:",
    "target_result:",
    "parent_repair_scope_contract:",
    "replacement_route_node:",
    "active_repair_child_node:",
    "inherited_child_node:",
    "inherited_accepted_result:",
    "node_acceptance_plan:",
    "parent_backward_replay:",
)

EXCLUDED_RUNTIME_FILE_FAMILIES = (
    "ledger.json",
    "events.jsonl",
    "packet_envelope",
    "packet_body",
    "result_envelope",
    "result_body",
    "route_snapshot",
    "generated_resource_ledger",
)


def all_contracts() -> tuple[Mapping[str, Any], ...]:
    return tuple(FORMAL_ARTIFACT_CONTRACTS)


def contract_ids() -> tuple[str, ...]:
    return tuple(str(contract["contract_id"]) for contract in FORMAL_ARTIFACT_CONTRACTS)


def artifact_ids() -> tuple[str, ...]:
    return tuple(str(contract["artifact_id"]) for contract in FORMAL_ARTIFACT_CONTRACTS)


def contract_for_artifact_id(artifact_id: str) -> Mapping[str, Any]:
    for contract in FORMAL_ARTIFACT_CONTRACTS:
        if contract.get("artifact_id") == artifact_id:
            return contract
    raise KeyError(artifact_id)


def contracts_for_packet_result_family(family_id: str) -> tuple[Mapping[str, Any], ...]:
    return tuple(
        contract
        for contract in FORMAL_ARTIFACT_CONTRACTS
        if contract.get("packet_result_family_id") == family_id
    )


def artifact_field_path(contract: Mapping[str, Any], field_path: str) -> str:
    artifact_id = str(contract.get("artifact_id") or "")
    if not artifact_id:
        raise ValueError("formal artifact contract missing artifact_id")
    return f"{artifact_id}.{field_path}" if field_path else artifact_id


def artifact_contract_path(contract: Mapping[str, Any], field_path: str = "") -> str:
    return f"artifact.{artifact_field_path(contract, field_path)}"


def required_field_paths(contract: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(str(field) for field in contract.get("required_field_paths") or ())


def fault_modes(contract: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(str(mode) for mode in contract.get("fault_modes") or FORMAL_ARTIFACT_FAULT_MODES)
