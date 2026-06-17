"""PM package result disposition writer."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import flowpilot_material_artifact_map as material_artifact_map
import packet_runtime
from flowpilot_router_errors import RouterError
from flowpilot_router_work_packets_pm_role_writes_decisions_formal_gate import _write_pm_formal_gate_package
from flowpilot_router_work_packets_pm_role_writes_decisions_packet_outcomes import (
    _check_existing_pm_package_disposition,
    _normalise_pm_package_packet_outcomes,
    _packet_outcome_counts,
    _validate_pm_package_packet_outcomes_for_decision,
)


_BOUND_ROUTER: ModuleType | None = None
def _bind_router(router: ModuleType) -> None:
    global _BOUND_ROUTER
    if _BOUND_ROUTER is router:
        return
    _BOUND_ROUTER = router
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value


def _material_generation_context_for_pm_disposition(router: ModuleType, project_root: Path, run_root: Path, batch: dict[str, Any], records: list[dict[str, Any]], *, package_label: str) -> dict[str, Any]:
    _bind_router(router)
    material_index_path = router._material_scan_index_path(run_root)
    material_index = read_json_if_exists(material_index_path)
    if not material_index:
        raise RouterError(f'{package_label} result disposition requires current material scan packet index')
    index_records = [record for record in material_index.get('packets') or [] if isinstance(record, dict)]
    if not index_records:
        raise RouterError(f'{package_label} result disposition requires current material scan packet records')
    batch_packet_ids = [str(record.get('packet_id') or '') for record in records]
    index_packet_ids = [str(record.get('packet_id') or '') for record in index_records]
    if batch_packet_ids != index_packet_ids:
        raise RouterError(f'{package_label} result disposition references a non-current material packet generation')
    index_batch_id = str(material_index.get('batch_id') or '')
    batch_id = str(batch.get('batch_id') or '')
    if index_batch_id and batch_id and index_batch_id != batch_id:
        raise RouterError(f'{package_label} result disposition batch does not match current material generation')
    current_generation_id = str(material_index.get('current_generation_id') or '')
    if current_generation_id:
        batch_generation_ids = {str(record.get('packet_generation_id') or '') for record in records}
        if batch_generation_ids != {current_generation_id}:
            raise RouterError(f'{package_label} result disposition batch is not the current material generation')
        index_generation_ids = {str(record.get('packet_generation_id') or '') for record in index_records}
        if index_generation_ids != {current_generation_id}:
            raise RouterError(f'{package_label} result disposition material index has inconsistent generation records')
    return {
        'schema_version': 'flowpilot.material_generation_context.v1',
        'current_generation_id': current_generation_id or None,
        'batch_id': batch_id or None,
        'material_index_path': project_relative(project_root, material_index_path),
        'parallel_batch_path': project_relative(project_root, router._parallel_packet_batch_path(run_root, batch_id)) if batch_id else None,
        'packet_ids': batch_packet_ids,
    }


def _write_pm_package_result_disposition(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any], *, batch_kind: str, package_label: str, gate_kind: str, output_path: Path, router_event: str | None = None) -> None:
    _bind_router(router)
    payload = _load_file_backed_role_payload_if_present(project_root, payload)
    role_output_envelope = payload.get('_role_output_envelope') if isinstance(payload.get('_role_output_envelope'), dict) else {}
    if role_output_envelope.get('role_output_runtime_validated') is not True:
        raise RouterError(f'{package_label} result disposition requires a role-output runtime envelope')
    if role_output_envelope.get('output_type') != PM_PACKAGE_RESULT_DISPOSITION_OUTPUT_TYPE:
        raise RouterError(f'{package_label} result disposition requires output_type={PM_PACKAGE_RESULT_DISPOSITION_OUTPUT_TYPE}')
    if role_output_envelope.get('output_contract_id') != PM_PACKAGE_RESULT_DISPOSITION_CONTRACT_ID:
        raise RouterError(f'{package_label} result disposition requires output_contract_id={PM_PACKAGE_RESULT_DISPOSITION_CONTRACT_ID}')
    if payload.get('decided_by_role') != 'project_manager':
        raise RouterError(f'{package_label} result disposition requires decided_by_role=project_manager')
    decision = str(payload.get('decision') or '').strip()
    if decision not in PM_PACKAGE_RESULT_DECISIONS:
        raise RouterError(f'{package_label} result disposition has unsupported decision')
    if "decision_reason" not in payload and "reason" in payload:
        raise RouterError(f'{package_label} result disposition requires decision_reason; reason is not a current alias')
    decision_reason = str(payload.get('decision_reason') or '').strip()
    if not decision_reason:
        raise RouterError(f'{package_label} result disposition requires non-empty decision_reason')
    batch = router._active_parallel_packet_batch(run_root, batch_kind)
    if not batch:
        raise RouterError(f'{package_label} result disposition requires results_relayed_to_pm')
    source_body_hash = _check_existing_pm_package_disposition(router, batch, payload, package_label=package_label)
    if batch.get('status') != 'results_relayed_to_pm':
        raise RouterError(f'{package_label} result disposition requires results_relayed_to_pm')
    records = [record for record in batch.get('packets') or [] if isinstance(record, dict)]
    if not records:
        raise RouterError(f'{package_label} result disposition requires packet records')
    material_generation_context = {}
    if batch_kind == 'material_scan':
        material_generation_context = _material_generation_context_for_pm_disposition(router, project_root, run_root, batch, records, package_label=package_label)
    router._validate_result_bodies_opened_by_pm(project_root, run_state, records)
    resolved_router_event = router_event or {
        'material_scan': 'pm_records_material_scan_result_disposition',
        'research': 'pm_records_research_result_disposition',
        'current_node': 'pm_records_current_node_result_disposition',
    }.get(batch_kind, '')
    if not resolved_router_event:
        raise RouterError(f'{package_label} result disposition requires a registered router event')
    packet_outcomes = _normalise_pm_package_packet_outcomes(router, records, payload, decision=decision, package_label=package_label)
    _validate_pm_package_packet_outcomes_for_decision(packet_outcomes, decision=decision, package_label=package_label)
    control_transaction = router._validate_control_transaction_requirements(
        run_root,
        transaction_type='result_absorption',
        producer_role='project_manager',
        output_contract_id=PM_PACKAGE_RESULT_DISPOSITION_CONTRACT_ID,
        router_events=(resolved_router_event,),
        required_event_usages=('recorded_event', 'wait'),
        required_commit_targets=(
            'packet_ledger',
            'pm_package_disposition',
            'run_state',
            'status_summary',
            'wait_closure',
        ),
        require_packet_authority=True,
        require_repair_transaction=False,
        outcome_policy='single_event',
    )
    formal_package = {}
    if decision == 'absorbed':
        formal_package = _write_pm_formal_gate_package(router, project_root, output_path, run_state=run_state, batch=batch, records=records, batch_kind=batch_kind, package_label=package_label, gate_kind=gate_kind, decision=decision, payload=payload)
    release_satisfied = bool(
        decision == 'absorbed'
        and formal_package.get('formal_gate_package_path')
        and formal_package.get('formal_gate_package_hash')
    )
    packet_outcome_summary = _packet_outcome_counts(packet_outcomes)
    disposition = {'schema_version': 'flowpilot.pm_package_result_disposition.v1', 'run_id': run_state['run_id'], 'batch_id': batch.get('batch_id'), 'batch_kind': batch_kind, 'package_label': package_label, 'gate_kind': gate_kind, 'decided_by_role': 'project_manager', 'decision': decision, 'decision_reason': decision_reason, 'packet_ids': [str(record.get('packet_id')) for record in records], 'packet_outcomes': packet_outcomes, 'packet_outcome_summary': packet_outcome_summary, 'packet_generation_id': material_generation_context.get('current_generation_id') if material_generation_context else None, 'material_generation': material_generation_context or None, 'result_envelope_paths': [str(record.get('result_envelope_path')) for record in records], 'source_body_hash': source_body_hash, 'formal_gate_package_released': release_satisfied, 'control_transaction': control_transaction, 'pm_reviewer_release_evidence': {'schema_version': 'flowpilot.pm_reviewer_release_evidence.v1', 'release_kind': 'absorbed_pm_package_result_disposition' if release_satisfied else 'none', 'release_satisfied': release_satisfied, 'formal_gate_package_required': decision == 'absorbed', 'formal_gate_package_path': formal_package.get('formal_gate_package_path'), 'formal_gate_package_hash': formal_package.get('formal_gate_package_hash'), 'reviewer_receives_raw_worker_result': False, 'reviewer_review_scope': 'pm_formal_gate_package_only' if release_satisfied else 'none'}, 'reviewer_receives_raw_worker_result': False, 'reviewer_review_scope': 'pm_formal_gate_package_only' if release_satisfied else 'none', 'residual_risks': payload.get('residual_risks') if isinstance(payload.get('residual_risks'), list) else [], 'recorded_at': utc_now(), **formal_package, **_role_output_envelope_record(payload)}
    write_json(output_path, disposition)
    material_artifact_map.refresh_material_artifact_map(project_root, run_root, run_state)
    outcomes_by_packet_id = {str(item.get('packet_id') or ''): item for item in packet_outcomes}
    for record in records:
        outcome = outcomes_by_packet_id.get(str(record.get('packet_id') or ''))
        if outcome:
            record['pm_result_outcome'] = outcome
    batch['pm_result_disposition'] = {'decision': decision, 'decision_path': project_relative(project_root, output_path), 'decision_hash': packet_runtime.sha256_file(output_path), 'source_body_hash': source_body_hash, 'recorded_at': disposition['recorded_at'], 'packet_outcomes': packet_outcomes, 'packet_outcome_summary': packet_outcome_summary, 'control_transaction': control_transaction, 'material_generation': material_generation_context or None}
    if decision == 'absorbed':
        batch['status'] = 'pm_absorbed'
        if batch_kind == 'material_scan':
            run_state['flags']['material_scan_results_absorbed_by_pm'] = True
        elif batch_kind == 'research':
            run_state['flags']['research_result_absorbed_for_review_by_pm'] = True
        elif batch_kind == 'current_node':
            run_state['flags']['current_node_result_absorbed_by_pm'] = True
    else:
        batch['status'] = decision
    router._write_parallel_packet_batch_state(run_root, batch)


__all__ = (
    '_material_generation_context_for_pm_disposition',
    '_write_pm_package_result_disposition',
)

_LOCAL_NAMES = set(globals())
