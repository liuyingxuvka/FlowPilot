## Why

The FlowPilot StructureMesh diagnostics still flag
`flowpilot_router_role_output_bridge.py` as an owner module above the target
size. The file currently mixes role-output envelope helper behavior with
role-output event reconciliation policy: startup fact replay, direct
role-output event authority, material-review projection, and ledger iteration.

Keeping those event-reconciliation branches inline makes future edits more
likely to mix router authority decisions with envelope/hash repair helpers.

## What Changes

- Extract role-output event reconciliation helpers into a focused child module.
- Keep `flowpilot_router_role_output_bridge.py` as the compatibility facade
  for existing router-owned helper names.
- Preserve role-output ledger iteration, startup fact reconciliation, material
  review projection, direct event reconciliation, and authority checks.
- Refresh source-audited model-test evidence for the child module.

## Impact

- Affected source:
  - `skills/flowpilot/assets/flowpilot_router_role_output_bridge.py`
  - new internal child module under `skills/flowpilot/assets/`
- Affected validation:
  - focused role-output bridge child test;
  - role-output bridge/router runtime tests;
  - model-test alignment and full coverage sweep/inventory;
  - local FlowPilot install sync/freshness audit.
