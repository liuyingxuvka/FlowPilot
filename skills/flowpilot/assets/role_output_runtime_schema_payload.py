"""Payload-shape helpers for role-output contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from role_output_runtime_schema_io import _project_relative
from role_output_runtime_schema_specs import PLACEHOLDER_PREFIXES


def _path_parts(field_path: str) -> list[str]:
    return [part for part in field_path.split(".") if part]


def _has_path(payload: dict[str, Any], field_path: str) -> bool:
    current: Any = payload
    for part in _path_parts(field_path):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    return True


def _get_path(payload: dict[str, Any], field_path: str, default: Any = None) -> Any:
    current: Any = payload
    for part in _path_parts(field_path):
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def _set_path(payload: dict[str, Any], field_path: str, value: Any) -> None:
    parts = _path_parts(field_path)
    current = payload
    for part in parts[:-1]:
        next_value = current.get(part)
        if not isinstance(next_value, dict):
            next_value = {}
            current[part] = next_value
        current = next_value
    if parts:
        current[parts[-1]] = value


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _is_placeholder(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(PLACEHOLDER_PREFIXES)


def _choose_placeholder(field_path: str, choices: list[Any]) -> str:
    return f"<choose:{field_path}:{'|'.join(str(item) for item in choices)}>"


def _required_placeholder(field_path: str) -> str:
    return f"<required:{field_path}>"


def _prior_path_context(project_root: Path, run_root: Path) -> dict[str, Any]:
    return {
        "reviewed": True,
        "source_paths": [
            _project_relative(project_root, run_root / "route_memory" / "pm_prior_path_context.json"),
            _project_relative(project_root, run_root / "route_memory" / "route_history_index.json"),
        ],
        "completed_nodes_considered": [],
        "superseded_nodes_considered": [],
        "stale_evidence_considered": [],
        "prior_blocks_or_experiments_considered": [],
        "impact_on_decision": _required_placeholder("prior_path_context_review.impact_on_decision"),
        "controller_summary_used_as_evidence": False,
    }


def _contract_self_check(explicit_arrays_required: bool) -> dict[str, Any]:
    return {
        "all_required_fields_present": False,
        "exact_field_names_used": True,
        "empty_required_arrays_explicit": not explicit_arrays_required,
        "runtime_mechanical_validation_passed": False,
        "semantic_sufficiency_reviewed_by_runtime": False,
    }
