## Why

The FlowPilot StructureMesh diagnostics still flag
`role_output_runtime_envelopes.py` as an owner module above the target size.
The controller-boundary confirmation helpers are a distinct branch: they build
and submit the controller-only confirmation output while the rest of the file
owns generic role-output envelopes, receipts, ledger lookup, and runtime
receipt validation.

Keeping this branch inline makes future edits more likely to mix the
controller-core confirmation policy with ordinary role-output submission and
receipt lookup.

## What Changes

- Extract controller-boundary confirmation body/submission helpers into a
  focused child module.
- Keep `role_output_runtime_envelopes.py` and `role_output_runtime.py` as
  compatibility facades with the same public helper names.
- Preserve output body shape, envelope shape, default paths, receipt writes,
  ledger writes, and controller visibility restrictions.
- Refresh source-audited model-test evidence for the new child module.

## Impact

- Affected source:
  - `skills/flowpilot/assets/role_output_runtime_envelopes.py`
  - new internal child module under `skills/flowpilot/assets/`
- Affected validation:
  - focused role-output runtime tests;
  - source-audited model-test alignment;
  - full FlowPilot coverage sweep/inventory;
  - local FlowPilot install sync/freshness audit.
