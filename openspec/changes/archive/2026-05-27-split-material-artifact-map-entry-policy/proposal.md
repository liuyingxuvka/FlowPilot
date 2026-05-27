## Why

The full FlowGuard coverage diagnostics still flag `flowpilot_material_artifact_map.py`
as a deferred StructureMesh split candidate. The file owns two different
responsibilities:

- the public material-map refresh/read/summary facade;
- the internal entry/reference/status policy used to construct safe map rows.

Keeping those responsibilities together makes the refresh path longer than
needed and makes future boundary changes easier to apply in the wrong layer.

## What Changes

- Extract material-map entry/reference/status construction into a focused child
  module.
- Keep `flowpilot_material_artifact_map.py` as the public compatibility facade
  for callers.
- Preserve the existing material-map JSON schema, sealed-body exclusion,
  source-ref hashing, review-source ids, and reviewable path behavior.
- Refresh the FlowGuard coverage diagnostics after the split.

## Impact

- Affected source:
  - `skills/flowpilot/assets/flowpilot_material_artifact_map.py`
  - new internal child module under `skills/flowpilot/assets/`
- Affected validation:
  - material artifact map FlowGuard model checks;
  - focused material-map runtime/boundary tests;
  - full coverage sweep/inventory and model-test alignment refresh;
  - local FlowPilot install sync/freshness audit.
