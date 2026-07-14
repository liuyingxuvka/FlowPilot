"""FlowGuard runtime-path evidence helpers for FlowPilot alignment.

The helper builds a required runtime node for each FlowPilot model obligation.
Those nodes are diagnostic evidence: they make the compared model path visible
to tests and maintenance tools without replacing the ordinary behavioral tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from typing import Any

from flowguard import (
    CodeContract,
    ModelObligation,
    ModelTestAlignmentPlan,
    RuntimeNodeContract,
    RuntimePathRecorder,
    RuntimePathRun,
    TestEvidence,
)


RUNTIME_PATH_OUTPUT = "current_test_execution_passed"
RUNTIME_PATH_NOT_CURRENT_OUTPUT = "test_execution_not_current"
RUNTIME_PATH_NEXT_STATE = "current_proof_artifact_consumed"
RUNTIME_PATH_NOT_CURRENT_STATE = "execution_proof_missing_or_stale"
RUNTIME_PATH_STATE_WRITE = "proof_artifact_bound"
RUNTIME_PATH_SIDE_EFFECT = "result_artifact_consumed"


@dataclass(frozen=True)
class RuntimePathAuthority:
    """Canonical development-process authority for diagnostic runtime evidence."""

    business_intent: str
    business_intent_id: str
    behavior_commitment_id: str
    primary_path_id: str
    expected_terminal: str
    surface_id: str
    inventory_revision: str

    def __post_init__(self) -> None:
        missing = tuple(
            name
            for name in (
                "business_intent",
                "business_intent_id",
                "behavior_commitment_id",
                "primary_path_id",
                "expected_terminal",
                "surface_id",
                "inventory_revision",
            )
            if not str(getattr(self, name))
        )
        if missing:
            raise ValueError(
                "diagnostic runtime-path authority is incomplete: "
                + ", ".join(missing)
            )


def _slug(value: str) -> str:
    chars = [char.lower() if char.isalnum() else "_" for char in str(value)]
    return "_".join(part for part in "".join(chars).split("_") if part)


def runtime_node_id(model_id: str, obligation_id: str) -> str:
    """Return the stable runtime node id for one model obligation."""

    return f"{model_id}:{obligation_id}"


def _with_runtime_node_id(
    obligation: ModelObligation,
    *,
    model_id: str,
) -> ModelObligation:
    node_id = runtime_node_id(model_id, obligation.obligation_id)
    required = tuple(dict.fromkeys((*obligation.required_runtime_node_ids, node_id)))
    return replace(obligation, required_runtime_node_ids=required)


def _source_evidence_for_obligation(
    plan: ModelTestAlignmentPlan,
    obligation_id: str,
) -> Any:
    matching = [
        evidence
        for evidence in plan.test_evidence
        if obligation_id in evidence.covered_obligations
    ]
    for evidence in matching:
        proof = getattr(evidence, "proof_artifact", None)
        if evidence.has_current_pass() and proof is not None and proof.has_current_pass():
            return evidence
    if matching:
        return matching[0]
    return None


def _code_contract_id(prefix: str, obligation_id: str) -> str:
    return f"{prefix}.{_slug(obligation_id)}" if prefix else f"runtime_path.{_slug(obligation_id)}"


def _runtime_path_code_contract(
    obligation: ModelObligation,
    *,
    code_contract_id: str,
) -> CodeContract:
    return CodeContract(
        code_contract_id=code_contract_id,
        path="skills/flowpilot/assets/flowpilot_runtime_path_evidence.py",
        symbol="attach_runtime_path_evidence_to_plan",
        surface_type="diagnostic_runtime_path_binding",
        implements_obligations=(obligation.obligation_id,),
    )


def _with_code_contract_bindings(
    evidence: TestEvidence,
    *,
    contracts_by_obligation: dict[str, str],
) -> TestEvidence:
    contract_ids = list(evidence.covered_code_contracts)
    for obligation_id in evidence.covered_obligations:
        contract_id = contracts_by_obligation.get(obligation_id)
        if contract_id:
            contract_ids.append(contract_id)
    return replace(evidence, covered_code_contracts=tuple(dict.fromkeys(contract_ids)))


def attach_runtime_path_evidence_to_plan(
    plan: ModelTestAlignmentPlan,
    *,
    family: str,
    authority: RuntimePathAuthority,
    code_contract_prefix: str = "",
    model_path: str = "",
) -> ModelTestAlignmentPlan:
    """Return a copy of ``plan`` with required FlowGuard runtime-path evidence."""

    resolved_model_path = model_path or f"FlowPilot model-test alignment/{family}/{plan.model_id}"
    obligations = tuple(
        _with_runtime_node_id(obligation, model_id=plan.model_id)
        for obligation in plan.obligations
    )
    recorder = RuntimePathRecorder(
        f"{plan.model_id}:runtime-path-current",
        metadata={
            "family": family,
            "model_id": plan.model_id,
            "model_path": resolved_model_path,
        },
    )
    contracts: list[RuntimeNodeContract] = []
    code_contracts: list[CodeContract] = []
    contracts_by_obligation: dict[str, str] = {}
    existing_code_contract_ids = {contract.code_contract_id for contract in plan.code_contracts}

    for index, obligation in enumerate(obligations):
        node_id = runtime_node_id(plan.model_id, obligation.obligation_id)
        evidence = _source_evidence_for_obligation(plan, obligation.obligation_id)
        evidence_id = getattr(evidence, "evidence_id", "") if evidence is not None else ""
        evidence_path = getattr(evidence, "path", "") if evidence is not None else ""
        evidence_command = getattr(evidence, "command", "") if evidence is not None else ""
        contract_id = _code_contract_id(code_contract_prefix, obligation.obligation_id)
        observation_id = f"runtime_path.{_slug(plan.model_id)}.{index:02d}.{_slug(obligation.obligation_id)}"
        input_case = f"{plan.model_id}.external_contract_input"
        state_case = f"{plan.model_id}.current_model_state"
        next_state = f"{plan.model_id}.{RUNTIME_PATH_NEXT_STATE}"
        proof_artifact = getattr(evidence, "proof_artifact", None) if evidence is not None else None
        proof_passed = bool(
            evidence is not None
            and evidence.has_current_pass()
            and proof_artifact is not None
            and proof_artifact.has_current_pass()
        )
        observed_output = RUNTIME_PATH_OUTPUT if proof_passed else RUNTIME_PATH_NOT_CURRENT_OUTPUT
        observed_next_state = next_state if proof_passed else f"{plan.model_id}.{RUNTIME_PATH_NOT_CURRENT_STATE}"
        observed_state_writes = (RUNTIME_PATH_STATE_WRITE,) if proof_artifact is not None else ()
        observed_side_effects = (
            (RUNTIME_PATH_SIDE_EFFECT,)
            if proof_artifact is not None and proof_artifact.result_path
            else ()
        )
        observed_status = getattr(evidence, "result_status", "not_run") if evidence is not None else "not_run"
        contracts_by_obligation[obligation.obligation_id] = contract_id
        if contract_id not in existing_code_contract_ids:
            code_contracts.append(
                _runtime_path_code_contract(
                    obligation,
                    code_contract_id=contract_id,
                )
            )
        metadata = {
            "family": family,
            "source_test_evidence_id": evidence_id,
            "source_test_path": evidence_path,
            "source_test_command": evidence_command,
            "source_proof_artifact_id": getattr(proof_artifact, "artifact_id", ""),
            "source_proof_result_path": getattr(proof_artifact, "result_path", ""),
            "observation_source": "current_test_execution_proof_artifact" if proof_passed else "missing_or_nonpassing_execution_proof",
            "compared_flowguard_model": plan.model_id,
            "compared_flowguard_model_path": resolved_model_path,
            "compared_flowguard_obligation": obligation.obligation_id,
            "progress_contract": "flowguard.runtime_path lines name model, node, run, status, model_path, obligation, input_case, state_case, evidence, and progress",
        }
        contracts.append(
            RuntimeNodeContract(
                node_id=node_id,
                model_id=plan.model_id,
                model_path=resolved_model_path,
                child_model_id=plan.model_id,
                leaf_model_id=obligation.obligation_id,
                model_obligation_id=obligation.obligation_id,
                code_contract_id=contract_id,
                boundary_id=f"flowpilot.runtime_path.{plan.model_id}",
                input_case=input_case,
                state_case=state_case,
                business_path_id=authority.primary_path_id,
                business_intent=authority.business_intent,
                business_intent_id=authority.business_intent_id,
                behavior_commitment_id=authority.behavior_commitment_id,
                expected_terminal=authority.expected_terminal,
                primary_path_id=authority.primary_path_id,
                surface_id=authority.surface_id,
                surface_role="owner",
                require_no_fallback=True,
                sequence_index=index,
                allowed_outputs=(RUNTIME_PATH_OUTPUT,),
                allowed_next_states=(next_state,),
                allowed_state_writes=(RUNTIME_PATH_STATE_WRITE,),
                allowed_side_effects=(RUNTIME_PATH_SIDE_EFFECT,),
                required_observation_ids=(observation_id,),
                metadata=metadata,
            )
        )
        recorder.record(
            node_id,
            observation_id=observation_id,
            model_id=plan.model_id,
            model_path=resolved_model_path,
            child_model_id=plan.model_id,
            leaf_model_id=obligation.obligation_id,
            model_obligation_id=obligation.obligation_id,
            code_contract_id=contract_id,
            boundary_id=f"flowpilot.runtime_path.{plan.model_id}",
            input_case=input_case,
            state_case=state_case,
            business_path_id=authority.primary_path_id,
            business_intent=authority.business_intent,
            business_intent_id=authority.business_intent_id,
            behavior_commitment_id=authority.behavior_commitment_id,
            primary_path_id=authority.primary_path_id,
            surface_id=authority.surface_id,
            surface_role="owner",
            observed_output=observed_output,
            observed_next_state=observed_next_state,
            observed_terminal=(
                authority.expected_terminal if proof_passed else "alignment_blocked"
            ),
            observed_state_writes=observed_state_writes,
            observed_side_effects=observed_side_effects,
            result_status=observed_status,
            evidence_current=proof_passed,
            evidence_id=evidence_id,
            proof_artifact=proof_artifact,
            progress_message=(
                f"compares FlowPilot code/test evidence {evidence_id or '(none)'} "
                f"with FlowGuard model {plan.model_id} obligation {obligation.obligation_id}"
            ),
            metadata=metadata,
        )

    run = RuntimePathRun(
        run_id=recorder.run_id,
        observations=recorder.observations,
        source_evidence_id=f"runtime_path.{plan.model_id}",
        result_status="passed" if all(observation.has_current_pass() for observation in recorder.observations) else "not_run",
        current=all(observation.has_current_pass() for observation in recorder.observations),
        business_intent_id=authority.business_intent_id,
        behavior_commitment_id=authority.behavior_commitment_id,
        primary_path_id=authority.primary_path_id,
        inventory_revision=authority.inventory_revision,
        covered_surface_ids=(authority.surface_id,),
        metadata={
            **recorder.metadata,
            "progress_lines": recorder.format_progress_lines().splitlines(),
        },
    )
    return replace(
        plan,
        obligations=obligations,
        code_contracts=(*plan.code_contracts, *code_contracts),
        test_evidence=tuple(
            _with_code_contract_bindings(
                evidence,
                contracts_by_obligation=contracts_by_obligation,
            )
            for evidence in plan.test_evidence
        ),
        runtime_node_contracts=(*plan.runtime_node_contracts, *contracts),
        runtime_path_runs=(*plan.runtime_path_runs, run),
        require_proof_artifacts=True,
        require_runtime_path_evidence=True,
    )


def runtime_path_progress_lines(plan: ModelTestAlignmentPlan) -> tuple[str, ...]:
    """Return all parseable runtime-path progress lines for a plan."""

    lines: list[str] = []
    for run in plan.runtime_path_runs:
        lines.extend(run.format_progress_lines().splitlines())
    return tuple(lines)


def runtime_path_summary(plan: ModelTestAlignmentPlan) -> dict[str, Any]:
    """Return compact runtime-path evidence metadata for reports."""

    lines = runtime_path_progress_lines(plan)
    return {
        "required": plan.require_runtime_path_evidence,
        "runtime_node_contract_count": len(plan.runtime_node_contracts),
        "runtime_path_run_count": len(plan.runtime_path_runs),
        "runtime_observation_count": sum(len(run.observations) for run in plan.runtime_path_runs)
        + len(plan.runtime_node_observations),
        "progress_line_count": len(lines),
        "progress_lines": list(lines),
    }
