"""Prepare, validate, and submit FlowPilot role-output envelopes.

This module remains the public compatibility facade. Implementation details are
split across focused role_output_runtime_* helpers while preserving imports, CLI
behavior, output keys, and JSON shape.
"""

from __future__ import annotations

import role_output_runtime_schema as _schema
import role_output_runtime_contracts as _contracts
import role_output_runtime_progress as _progress
import role_output_runtime_envelopes as _envelopes
import role_output_runtime_cli as _cli

for _module in (_schema, _contracts, _progress, _envelopes, _cli):
    for _name, _value in vars(_module).items():
        if _name.startswith("__") and _name.endswith("__"):
            continue
        globals()[_name] = _value


def update_output_progress(*args, **kwargs):
    """Compatibility wrapper for Controller-visible progress updates."""
    return _progress.update_output_progress(*args, **kwargs)


# Source-check compatibility markers:
# progress_written_by_runtime
# "submitted_to": "router"

__all__ = sorted(
    name
    for name in globals()
    if not (name.startswith("_") and name not in {
        "_read_json",
        "_write_json",
        "_sha256_file",
        "_project_relative",
        "_resolve_project_path",
        "_run_paths",
        "_spec_for",
        "_role_allowed",
        "_deep_merge",
        "_apply_runtime_fixed_values",
        "_finalize_contract_self_check",
        "_default_output_path",
        "_load_output_session",
        "_role_output_ledger_path",
        "_validate_progress_value",
        "_validate_progress_message",
        "_append_ledger",
        "_build_envelope",
    })
)

if __name__ == "__main__":
    raise SystemExit(main())
