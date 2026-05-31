"""PM role-work result decision writer."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import packet_runtime
from flowpilot_router_errors import RouterError


def _bind_router(router: ModuleType) -> None:
    current = globals()
    local_names = current.get('_LOCAL_NAMES', set())
    for name, value in vars(router).items():
        if name.startswith('__') and name.endswith('__'):
            continue
        if name in local_names:
            continue
        current[name] = value


def _write_pm_role_work_result_decision(router: ModuleType, project_root: Path, run_root: Path, run_state: dict[str, Any], payload: dict[str, Any]) -> str:
    _bind_router(router)
    decision_payload = _load_file_backed_role_payload_if_present(project_root, payload)
    request_id = str(decision_payload.get('request_id') or '').strip()
    batch_id = str(decision_payload.get('batch_id') or '').strip()
    if not request_id and (not batch_id):
        raise RouterError('PM role-work result decision requires request_id or batch_id')
    decided_by_role = str(decision_payload.get('decided_by_role') or decision_payload.get('recorded_by_role') or '').strip()
    if decided_by_role != 'project_manager':
        raise RouterError('PM role-work result decision requires decided_by_role=project_manager')
    decision = str(decision_payload.get('decision') or '').strip()
    if decision not in PM_ROLE_WORK_TERMINAL_DECISIONS:
        raise RouterError('PM role-work result decision must be absorbed, canceled, or superseded')
    index = router._load_pm_role_work_request_index(run_root, run_state)
    records: list[dict[str, Any]]
    if batch_id:
        records = [record for record in index.get('requests', []) if isinstance(record, dict) and str(record.get('batch_id') or index.get('active_batch_id') or '') == batch_id]
        if not records:
            active_ids = {str(item) for item in index.get('active_request_ids', []) if item}
            records = [record for record in index.get('requests', []) if isinstance(record, dict) and str(record.get('request_id')) in active_ids]
    else:
        record = router._pm_role_work_request_record(index, request_id)
        records = [record] if isinstance(record, dict) else []
    if not records:
        raise RouterError('PM role-work result decision references unknown request_id or batch_id')
    if decision == 'absorbed' and any((record.get('status') != 'result_relayed_to_pm' for record in records)):
        raise RouterError('PM may absorb role-work batch only after Controller relays every result to PM')
    if decision in {'canceled', 'superseded'} and any((record.get('status') not in PM_ROLE_WORK_OPEN_STATUSES for record in records)):
        raise RouterError('PM role-work result decision can cancel or supersede only unresolved requests')
    gate_mappings = router._pm_role_work_gate_mappings_for_decision(decision_payload, records, decision=decision)
    decision_record = {'schema_version': PM_ROLE_WORK_RESULT_DECISION_SCHEMA, 'request_id': request_id or records[0].get('request_id'), 'batch_id': batch_id or records[0].get('batch_id'), 'request_ids': [record.get('request_id') for record in records], 'decided_by_role': 'project_manager', 'decision': decision, 'decision_reason': decision_payload.get('decision_reason') or '', 'gate_mappings': gate_mappings, 'recorded_at': utc_now(), **_role_output_envelope_record(decision_payload)}
    decisions_dir = run_root / 'pm_work_requests' / 'decisions'
    decision_key = batch_id or request_id
    decision_path = decisions_dir / f'{router._safe_packet_id_component(decision_key)}.{decision}.json'
    write_json(decision_path, decision_record)
    for record in records:
        record['status'] = decision
        record['pm_result_decision'] = {'decision': decision, 'decision_path': project_relative(project_root, decision_path), 'decision_hash': packet_runtime.sha256_file(decision_path), 'recorded_at': decision_record['recorded_at']}
        for mapping in gate_mappings:
            if mapping.get('request_id') == record.get('request_id'):
                record['pm_result_decision']['gate_mapping'] = mapping
        router._record_flowguard_operator_lifecycle_pm_decision(project_root, run_root, run_state, record, decision_record)
    if request_id and index.get('active_request_id') == request_id:
        index['active_request_id'] = None
    if batch_id and index.get('active_batch_id') == batch_id:
        index['active_batch_id'] = None
        index['active_request_ids'] = []
    router._write_pm_role_work_request_index(run_root, index)
    if batch_id and decision == 'absorbed':
        router._mark_parallel_batch_reviewed(run_root, 'pm_role_work', passed=True, reviewed_packet_ids=[str(record.get('packet_id')) for record in records])
    router._apply_pm_role_work_gate_mappings(project_root, run_root, run_state, decision_path=decision_path, decision_record=decision_record, mappings=gate_mappings)
    return decision


def _validate_result_bodies_opened_by_pm(router: ModuleType, project_root: Path, run_state: dict[str, Any], records: list[dict[str, Any]]) -> None:
    _bind_router(router)
    for record in records:
        result_path = router._result_envelope_path_from_packet_record(project_root, run_state, record)
        result = packet_runtime.load_envelope(project_root, result_path)
        opened = result.get('result_body_opened_by_role')
        if not (isinstance(opened, dict) and opened.get('role') == 'project_manager' and (opened.get('controller_relay_verified') is True) and (opened.get('body_hash_verified') is True)):
            raise RouterError(f"PM result disposition requires project_manager to open result body after Controller relay: {result.get('packet_id')}")


__all__ = (
    '_write_pm_role_work_result_decision',
    '_validate_result_bodies_opened_by_pm',
)

_LOCAL_NAMES = set(globals())
