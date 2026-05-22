## Why

The full FlowGuard coverage diagnostics still flag
`flowpilot_router_controller_scheduler_current_work.py` as a deferred
StructureMesh split candidate. The file is a compatibility facade but still
keeps pending-action authority checks, scheduler-row lookup, durable wait
resolution, batch projection, and current-work projection in one decision
chain.

Keeping pending-action resolution inline makes it easier for future edits to
mix "what is the current work" display projection with "has this wait been
durably resolved" control authority.

## What Changes

- Extract pending-action resolution helpers into a focused child module.
- Keep `flowpilot_router_controller_scheduler_current_work.py` as the
  compatibility facade for existing router-owned helper names.
- Preserve current-work owner payloads, scheduler-row lookup behavior,
  durable wait clearing history, and batch-projection decisions.
- Refresh model-test alignment and full coverage diagnostics after the split.

## Impact

- Affected source:
  - `skills/flowpilot/assets/flowpilot_router_controller_scheduler_current_work.py`
  - new internal child module under `skills/flowpilot/assets/`
- Affected validation:
  - focused current-work and controller scheduler tests;
  - focused source-boundary test for the child module;
  - model-test alignment and full coverage sweep/inventory;
  - local FlowPilot install sync/freshness audit.
