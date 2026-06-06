"""PM formal gate package writer."""

from __future__ import annotations

from pathlib import Path
from types import ModuleType
from typing import Any

import flowpilot_material_artifact_map as material_artifact_map
import packet_runtime
from flowpilot_router_errors import RouterError


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


def _result_contract_self_check_summary(result_envelope: dict[str, Any], packet_id: str) -> dict[str, Any]:
    check = result_envelope.get('contract_self_check')
    if not isinstance(check, dict):
        return {
            'packet_id': packet_id,
            'ok': False,
            'reason': 'contract_self_check_missing',
        }
    required = bool(check.get('required'))
    completed = bool(check.get('completed'))
    passed = bool(check.get('passed'))
    contract_matches = check.get('source_output_contract_id_matches') is not False
    decision = check.get('decision')
    ok = (not required) or (completed and passed and contract_matches and bool(decision))
    reason = 'passed' if ok else 'contract_self_check_unparseable_or_failed'
    if completed and not passed:
        reason = 'contract_self_check_failed'
    if not completed:
        reason = 'contract_self_check_missing_or_unparseable'
    if not contract_matches:
        reason = 'contract_self_check_contract_mismatch'
    return {
        'packet_id': packet_id,
        'ok': ok,
        'required': required,
        'completed': completed,
        'passed': passed,
        'decision': decision,
        'source_output_contract_id': check.get('source_output_contract_id'),
        'declared_source_output_contract_id': check.get('declared_source_output_contract_id'),
        'source_output_contract_id_matches': contract_matches,
        'reason': reason,
    }


def _write_pm_formal_gate_package(
    router: ModuleType,
    project_root: Path,
    output_path: Path,
    *,
    run_state: dict[str, Any],
    batch: dict[str, Any],
    records: list[dict[str, Any]],
    batch_kind: str,
    package_label: str,
    gate_kind: str,
    decision: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _bind_router(router)
    run_root = project_root / str(run_state['run_root'])
    map_doc = material_artifact_map.refresh_material_artifact_map(project_root, run_root, run_state)
    map_ref = material_artifact_map.material_artifact_map_source_ref(project_root, run_root)
    review_entry_ids = material_artifact_map.review_source_entry_ids(map_doc, batch_kind=batch_kind)
    review_paths = material_artifact_map.reviewable_source_paths(map_doc, entry_ids=review_entry_ids)
    package_path = output_path.with_name(f"pm_{router._safe_packet_id_component(package_label)}_formal_gate_package.json")
    result_envelopes: list[dict[str, Any]] = []
    source_contract_self_checks: list[dict[str, Any]] = []
    for record in records:
        result_rel = str(record.get('result_envelope_path') or '')
        result_hash = None
        result_envelope: dict[str, Any] = {}
        if result_rel:
            result_path = resolve_project_path(project_root, result_rel)
            if result_path.exists():
                result_hash = packet_runtime.sha256_file(result_path)
                result_envelope = packet_runtime.load_envelope(project_root, result_rel)
        packet_rel = str(record.get('packet_envelope_path') or result_envelope.get('source_packet_envelope_path') or '')
        packet_hash = None
        packet_envelope: dict[str, Any] = {}
        if packet_rel:
            packet_path = resolve_project_path(project_root, packet_rel)
            if packet_path.exists():
                packet_hash = packet_runtime.sha256_file(packet_path)
                packet_envelope = packet_runtime.load_envelope(project_root, packet_rel)
        source_output_contract_id = str(
            result_envelope.get('source_output_contract_id')
            or result_envelope.get('output_contract_id')
            or packet_envelope.get('output_contract_id')
            or packet_runtime.output_contract_id(
                packet_envelope.get('output_contract') if isinstance(packet_envelope.get('output_contract'), dict) else None
            )
            or ''
        )
        result_entry = {
            'packet_id': str(record.get('packet_id') or ''),
            'result_envelope_path': result_rel,
            'result_envelope_hash': result_hash,
        }
        if packet_rel:
            result_entry['packet_envelope_path'] = packet_rel
            result_entry['packet_envelope_hash'] = packet_hash
        if source_output_contract_id:
            result_entry['source_output_contract_id'] = source_output_contract_id
        if result_envelope:
            check_summary = _result_contract_self_check_summary(result_envelope, str(record.get('packet_id') or ''))
        else:
            check_summary = {
                'packet_id': str(record.get('packet_id') or ''),
                'ok': False,
                'reason': 'result_envelope_missing',
            }
        result_entry['contract_self_check'] = check_summary
        source_contract_self_checks.append(check_summary)
        result_envelopes.append(result_entry)
    failed_checks = [item for item in source_contract_self_checks if not item.get('ok')]
    if failed_checks:
        raise RouterError(
            f"{package_label} formal gate package requires passed source result contract self-checks: "
            f"{failed_checks}"
        )
    package = {
        'schema_version': 'flowpilot.pm_formal_gate_package.v1',
        'run_id': run_state['run_id'],
        'batch_id': batch.get('batch_id'),
        'batch_kind': batch_kind,
        'package_label': package_label,
        'gate_kind': gate_kind,
        'decision': decision,
        'reviewer_readable': True,
        'reviewer_review_scope': 'pm_formal_gate_package_only',
        'reviewer_receives_raw_worker_result': False,
        'raw_worker_result_bodies_included': False,
        'material_artifact_map_path': map_ref.get('path') if isinstance(map_ref, dict) else None,
        'material_artifact_map_hash': map_ref.get('hash') if isinstance(map_ref, dict) else None,
        'review_source_entry_ids': review_entry_ids,
        'reviewable_source_paths': review_paths,
        'packet_ids': [str(record.get('packet_id')) for record in records],
        'result_envelopes': result_envelopes,
        'source_result_contract_self_checks': source_contract_self_checks,
        'all_source_result_contract_self_checks_passed': True,
        'source_pm_disposition_path': project_relative(project_root, output_path),
        'content_boundary': {
            'includes_pm_disposition_summary': True,
            'includes_result_envelope_paths_and_hashes': True,
            'includes_material_artifact_map_refs': True,
            'includes_reviewable_source_paths': True,
            'excludes_worker_result_bodies': True,
            'sealed_body_boundary_preserved': True,
        },
        'decision_reason': payload.get('decision_reason') or payload.get('reason') or '',
        'residual_risks': payload.get('residual_risks') if isinstance(payload.get('residual_risks'), list) else [],
        'created_at': utc_now(),
    }
    write_json(package_path, package)
    return {
        'formal_gate_package_schema_version': package['schema_version'],
        'formal_gate_package_path': project_relative(project_root, package_path),
        'formal_gate_package_hash': packet_runtime.sha256_file(package_path),
        'formal_gate_package_reviewer_readable': True,
        'formal_gate_package_content_boundary': package['content_boundary'],
    }


__all__ = (
    '_result_contract_self_check_summary',
    '_write_pm_formal_gate_package',
)

_LOCAL_NAMES = set(globals())
