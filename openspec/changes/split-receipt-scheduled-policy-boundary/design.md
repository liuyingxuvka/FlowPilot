## StructureMesh Decision

Selected candidate:

- `skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_scheduled.py`

Selected branches:

- Scheduler-row reconciliation lookup.
- Backfill from a reconciled Controller action into a Router scheduler row.
- Legacy startup daemon reconciliation canonicalization.
- Pending Controller action clearing.
- Controller action reconciliation commit.
- Scheduled receipt apply-result classification.

Not selected:

- The main scheduled receipt scan loop, because it remains the parent
  orchestration surface over action files, receipts, row reconciliation,
  blockers, and derived-view refresh.
- Receipt effect application, because that is already owned by the receipt
  effects boundary.
- Packet/result evidence folds, because they are owned by the packet-fold
  registry and lifecycle children.

## Target Structure

- `flowpilot_router_controller_scheduler_receipts_scheduled.py`
  - parent scan/orchestration loop;
  - compatibility import/export surface;
  - final ledger rebuild, route-memory refresh, display sync, and run-state
    save.

- `flowpilot_router_controller_scheduler_receipts_scheduled_policy.py`
  - finite scheduler-row reconciliation lookup;
  - finite scheduler-row backfill outcomes;
  - finite pending-action matching and clearing outcomes;
  - finite apply-result case classifier;
  - reconciliation commit helper used by the parent loop.

## Leaf Model Boundary

`runtime_owner.receipt_scheduled_policy_boundary` owns the finite policy rules
that map declared scheduler/action/receipt inputs to the only allowed policy
outputs. The parent scheduled receipt loop consumes this boundary; it does not
claim leaf-level Cartesian proof for the whole filesystem scan loop.

If future evidence shows two policy helpers both behave like independent
primary evidence for the same obligation, split this child again instead of
only changing evidence labels.

## Validation

- Compile parent, child module, focused tests, and source-audited model files.
- Run direct scheduled policy child tests.
- Run foreground/controller receipt runtime tests that exercise the scheduled
  parent loop.
- Run model-test alignment and full coverage inventory checks.
- Confirm scheduled receipts no longer appears as a deferred StructureMesh
  surface.
