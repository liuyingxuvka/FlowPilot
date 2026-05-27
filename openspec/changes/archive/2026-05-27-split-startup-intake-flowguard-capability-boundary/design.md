## StructureMesh Decision

Selected candidate:

- `skills/flowpilot/assets/flowpilot_router_startup_intake_materialization.py`

Selected branches:

- FlowGuard capability snapshot path.
- Portable FlowGuard skill-root discovery.
- Finite FlowGuard route classification.
- FlowGuard package import snapshot.
- FlowGuard skill route discovery.
- FlowGuard capability snapshot writing.

Not selected:

- Startup intake file materialization, because it remains the startup intake
  record owner.
- User request reference and user-intake packet scaffold, because they are tied
  to startup materialization state.
- Deterministic bootstrap seed orchestration, because it composes startup
  answers, mailbox setup, user request records, user-intake scaffold, and the
  FlowGuard capability snapshot child boundary.

## Target Structure

- `flowpilot_router_startup_intake_materialization.py`
  - startup intake record materialization;
  - startup answers record;
  - mailbox foundation;
  - user request reference;
  - user-intake packet scaffold;
  - deterministic bootstrap seed orchestration and completed-seed projection.

- `flowpilot_router_startup_intake_flowguard_capability.py`
  - FlowGuard snapshot path;
  - portable skill route discovery;
  - route classification;
  - import snapshot;
  - snapshot writeback.

## Leaf Model Boundary

`runtime_owner.startup_intake_flowguard_capability_boundary` owns the finite
FlowGuard route classification output vocabulary and the portable capability
snapshot write contract. The deterministic seed parent consumes this boundary
and does not duplicate the route-classification table.

If future evidence makes route classification and snapshot writeback look like
two independent primary obligations, split this child again instead of merging
their tests under one broad label.

## Validation

- Compile parent, child module, focused tests, and source-audited model files.
- Run direct FlowGuard capability child tests.
- Run startup deterministic seed and capability snapshot runtime tests.
- Run model-test alignment and full coverage inventory checks.
- Confirm startup intake materialization no longer appears as a deferred
  StructureMesh surface.
