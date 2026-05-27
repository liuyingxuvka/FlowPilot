## Why

FlowPilot has many FlowGuard models and check runners, so closing two
model-test gaps must not be mistaken for full boundary coverage. The project
needs a full inventory that separates what is currently aligned, what is only
abstract/model-level evidence, what has stale or missing result evidence, and
what still needs ordinary boundary tests.

## What Changes

- Inventory all `simulations/run_*checks.py` FlowGuard check entrypoints.
- Cross-check the inventory against current model-test alignment evidence,
  ordinary test references, persisted result artifacts, skipped checks, and
  known coverage boundaries.
- Produce a machine-readable inventory result and a human-readable summary of
  remaining model/test coverage gaps.
- Do not automatically add large batches of tests in this change; the output is
  the prioritization map for follow-up focused test work.

## Capabilities

### New Capabilities

- `flowguard-full-model-coverage-inventory`: repository-wide FlowGuard
  model/check coverage inventory and gap classification.

### Modified Capabilities

- None.

## Impact

- Affects maintenance evidence under `simulations/`, `docs/`, and this
  OpenSpec change.
- May add or refine a read-only inventory helper if the existing sweep output
  is not specific enough.
- Does not alter production FlowPilot runtime behavior.
- Does not touch active `.flowpilot/runs/` state.
