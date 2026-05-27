## Context

`flowpilot_router_role_output_bridge.py` owns several distinct responsibilities:
role-output envelope helpers, mutable-artifact envelope hash repair, prompt
delivery context repair, local status sync, and role-output event
reconciliation. The event-reconciliation branch has its own model boundary in
the branch-pruning model: role-output events must not be recorded unless they
have durable Router authority.

This is a StructureMesh split, not a behavior change.

## Target Structure

- `flowpilot_router_role_output_bridge.py`
  - compatibility helper names exported through the router facade;
  - envelope record helpers;
  - mutable-artifact envelope hash repair;
  - prompt delivery context repair;
  - current/index status sync;
  - delegation to the event-reconciliation child module.

- `flowpilot_router_role_output_bridge_events.py`
  - role-output ledger output iteration;
  - startup fact role-output ledger reconciliation;
  - body payload recovery from role-output records;
  - durable Router authority checks for role-output events;
  - material-review projection from role-output payloads;
  - direct role-output event ledger reconciliation.

Dependency direction is one-way: the bridge facade imports the child module.
The child module receives the router facade explicitly and must not import the
bridge facade or become a second router state authority.

## Compatibility Boundary

The following names remain available from
`flowpilot_router_role_output_bridge.py`:

- `_try_reconcile_startup_fact_role_output_ledger`
- `_role_output_body_payload_from_record`
- `_role_output_event_has_durable_authority`
- `_sync_material_review_from_role_output_payload`
- `_try_reconcile_direct_role_output_event_ledger`
- `_role_output_ledger_outputs`
- `_startup_fact_canonical_report_is_valid`

## Validation Boundary

The split is green only if:

- focused child tests directly exercise the child module;
- existing role-output bridge/router runtime evidence still passes through the
  facade names;
- source-audited model-test evidence covers the child module;
- full coverage diagnostics no longer report `flowpilot_router_role_output_bridge`
  as a StructureMesh split finding;
- local installed FlowPilot is synced and fresh.
