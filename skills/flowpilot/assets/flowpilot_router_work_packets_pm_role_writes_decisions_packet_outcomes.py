"""PM package disposition packet outcome helpers."""

from __future__ import annotations

from types import ModuleType
from typing import Any

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


def _pm_package_disposition_body_hash(router: ModuleType, payload: dict[str, Any]) -> str:
    _bind_router(router)
    envelope = payload.get('_role_output_envelope')
    if isinstance(envelope, dict):
        for key in ('body_hash', 'body_raw_sha256', 'body_semantic_sha256'):
            value = str(envelope.get(key) or '').strip()
            if value:
                return value
    return router._payload_body_hash(payload)


def _packet_outcome_counts(packet_outcomes: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for outcome in packet_outcomes:
        key = str(outcome.get('outcome') or '')
        counts[key] = counts.get(key, 0) + 1
    return counts


def _normalise_pm_package_packet_outcomes(
    router: ModuleType,
    records: list[dict[str, Any]],
    payload: dict[str, Any],
    *,
    decision: str,
    package_label: str,
) -> list[dict[str, Any]]:
    _bind_router(router)
    packet_ids = [str(record.get('packet_id') or '') for record in records]
    packet_roles = {str(record.get('packet_id') or ''): str(record.get('to_role') or record.get('holder_role') or '') for record in records}
    if any((not packet_id for packet_id in packet_ids)):
        raise RouterError(f'{package_label} result disposition requires packet ids for every member')
    raw_outcomes = payload.get('packet_outcomes')
    if raw_outcomes in (None, ''):
        derived = 'accepted' if decision == 'absorbed' else decision
        return [
            {
                'packet_id': packet_id,
                'role': packet_roles.get(packet_id) or None,
                'outcome': derived,
                'reason': f'derived from aggregate PM decision: {decision}',
                'derived_from_aggregate_decision': True,
            }
            for packet_id in packet_ids
        ]
    if not isinstance(raw_outcomes, list):
        raise RouterError(f'{package_label} result disposition packet_outcomes must be a list')
    expected = set(packet_ids)
    seen: set[str] = set()
    outcomes: list[dict[str, Any]] = []
    for item in raw_outcomes:
        if not isinstance(item, dict):
            raise RouterError(f'{package_label} result disposition packet_outcomes entries must be objects')
        packet_id = str(item.get('packet_id') or '').strip()
        if not packet_id:
            raise RouterError(f'{package_label} result disposition packet_outcomes entries require packet_id')
        if packet_id not in expected:
            raise RouterError(f'{package_label} result disposition packet_outcomes references unknown packet_id: {packet_id}')
        if packet_id in seen:
            raise RouterError(f'{package_label} result disposition packet_outcomes has duplicate packet_id: {packet_id}')
        raw_outcome = str(item.get('outcome') or '').strip()
        outcome = 'accepted' if raw_outcome == 'absorbed' else raw_outcome
        allowed_outcomes = set(getattr(router, 'PM_PACKAGE_RESULT_PACKET_OUTCOMES', ()))
        if outcome not in allowed_outcomes:
            allowed = ', '.join(sorted(allowed_outcomes))
            raise RouterError(f'{package_label} result disposition packet outcome must be one of: {allowed}')
        reason = str(item.get('reason') or item.get('decision_reason') or '').strip()
        if not reason:
            raise RouterError(f'{package_label} result disposition packet_outcomes entries require reason')
        normalised = {
            'packet_id': packet_id,
            'role': str(item.get('role') or packet_roles.get(packet_id) or '').strip() or None,
            'outcome': outcome,
            'reason': reason,
            'derived_from_aggregate_decision': False,
        }
        for optional_key in ('rework_scope', 'blocker_id', 'repair_target', 'next_action'):
            if item.get(optional_key) not in (None, ''):
                normalised[optional_key] = item.get(optional_key)
        outcomes.append(normalised)
        seen.add(packet_id)
    missing = sorted(expected - seen)
    if missing:
        raise RouterError(f"{package_label} result disposition packet_outcomes missing packet ids: {', '.join(missing)}")
    return outcomes


def _validate_pm_package_packet_outcomes_for_decision(
    packet_outcomes: list[dict[str, Any]],
    *,
    decision: str,
    package_label: str,
) -> None:
    if decision != 'absorbed':
        return
    nonaccepted = [item for item in packet_outcomes if item.get('outcome') != 'accepted']
    if nonaccepted:
        packet_ids = ', '.join(str(item.get('packet_id') or '') for item in nonaccepted)
        raise RouterError(
            f'{package_label} result disposition cannot be absorbed while packet outcomes require more work: {packet_ids}'
        )


def _check_existing_pm_package_disposition(
    router: ModuleType,
    batch: dict[str, Any],
    payload: dict[str, Any],
    *,
    package_label: str,
) -> str:
    _bind_router(router)
    incoming_hash = _pm_package_disposition_body_hash(router, payload)
    existing = batch.get('pm_result_disposition')
    if isinstance(existing, dict):
        existing_hash = str(existing.get('source_body_hash') or '').strip()
        if existing_hash and incoming_hash and existing_hash != incoming_hash:
            raise RouterError(
                f'{package_label} result disposition already recorded for this batch/generation; '
                'different body hash requires an authorized repair/reissue path'
            )
        raise RouterError(f'{package_label} result disposition already recorded for this batch/generation')
    return incoming_hash


__all__ = (
    '_check_existing_pm_package_disposition',
    '_normalise_pm_package_packet_outcomes',
    '_packet_outcome_counts',
    '_pm_package_disposition_body_hash',
    '_validate_pm_package_packet_outcomes_for_decision',
)

_LOCAL_NAMES = set(globals())
