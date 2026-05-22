## StructureMesh Decision

Selected candidate:

- `skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_packet_folds.py`

Selected branches:

- Registered receipt evidence-fold action metadata.
- Packet/result lifecycle writeback policy and the two lifecycle write paths.

Not selected:

- Packet dispatch evidence validation, because packet relay/open/lease/batch
  proof remains one business branch.
- Result relay evidence validation, because result recipient proof is a
  separate business branch.
- Control-blocker delivery, because it is a dedicated non-packet lifecycle
  branch.
- The public `_apply_registered_controller_receipt_evidence_fold` entrypoint,
  because it remains the compatibility owner.

## Target Structure

- `flowpilot_router_controller_scheduler_receipts_packet_folds.py`
  - parent compatibility entrypoint;
  - record lookup;
  - packet evidence validation;
  - result evidence validation;
  - control-blocker delivery;
  - final fold summary assembly.

- `flowpilot_router_controller_scheduler_receipts_packet_fold_registry.py`
  - registry table;
  - sorted registered action exposure;
  - no Router facade binding or side effects.

- `flowpilot_router_controller_scheduler_receipts_packet_fold_lifecycle.py`
  - packet/result lifecycle target policy;
  - parallel batch lifecycle writeback;
  - PM role-work lifecycle writeback;
  - no packet/result body reads.

## Leaf Model Boundary

`runtime_owner.receipt_packet_fold_registry_boundary` owns only the finite
action metadata table and sorted action exposure.

`runtime_owner.receipt_packet_fold_lifecycle_boundary` owns packet/result
lifecycle target selection and the concrete batch/PM lifecycle writes. If future
evidence makes the policy and writeback paths both look like separate primary
evidence, split this leaf again rather than changing labels.

## Validation

- Compile parent, child modules, focused tests, and source-audited model files.
- Run direct registry and lifecycle child tests.
- Run focused receipt-fold runtime/model checks.
- Run model-test alignment and full coverage inventory checks.
- Confirm packet-fold no longer appears as a deferred StructureMesh surface.
