"""FlowGuard runtime-path evidence helpers for FlowPilot alignment.

The helper builds a required runtime node for each FlowPilot model obligation.
Those nodes are diagnostic evidence: they make the compared model path visible
to tests and maintenance tools without replacing the ordinary behavioral tests.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from flowguard import (
    ModelObligation,
    ModelTestAlignmentPlan,
    RuntimeNodeContract,
    RuntimePathRecorder,
    RuntimePathRun,
)


RUNTIME_PATH_OUTPUT = "model_obligation_runtime_path_bound"
RUNTIME_PATH_NEXT_STATE = "runtime_path_evidence_bound"
RUNTIME_PATH_STATE_WRITE = "flowguard_runtime_path_evidence"
RUNTIME_PATH_SIDE_EFFECT = "progress_line_emitted"


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
    for evidence in plan.test_evidence:
        if obligation_id in evidence.covered_obligations and evidence.evidence_current:
            return evidence
    return plan.test_evidence[0] if plan.test_evidence else None


def _code_contract_id(prefix: str, obligation_id: str) -> str:
    return f"{prefix}.{_slug(obligation_id)}" if prefix else f"runtime_path.{_slug(obligation_id)}"


def attach_runtime_path_evidence_to_plan(
    plan: ModelTestAlignmentPlan,
    *,
    family: str,
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
        metadata = {
            "family": family,
            "source_test_evidence_id": evidence_id,
            "source_test_path": evidence_path,
            "source_test_command": evidence_command,
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
            observed_output=RUNTIME_PATH_OUTPUT,
            observed_next_state=next_state,
            observed_state_writes=(RUNTIME_PATH_STATE_WRITE,),
            observed_side_effects=(RUNTIME_PATH_SIDE_EFFECT,),
            evidence_id=evidence_id,
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
        metadata={
            **recorder.metadata,
            "progress_lines": recorder.format_progress_lines().splitlines(),
        },
    )
    return ModelTestAlignmentPlan(
        model_id=plan.model_id,
        obligations=obligations,
        code_contracts=plan.code_contracts,
        test_evidence=plan.test_evidence,
        obligation_families=plan.obligation_families,
        family_evidence=plan.family_evidence,
        boundary_contracts=plan.boundary_contracts,
        boundary_observations=plan.boundary_observations,
        runtime_node_contracts=(*plan.runtime_node_contracts, *contracts),
        runtime_node_observations=plan.runtime_node_observations,
        runtime_path_runs=(*plan.runtime_path_runs, run),
        require_code_contracts=plan.require_code_contracts,
        require_proof_artifacts=plan.require_proof_artifacts,
        require_runtime_path_evidence=True,
        allow_orphan_tests=plan.allow_orphan_tests,
        allow_orphan_code_contracts=plan.allow_orphan_code_contracts,
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
