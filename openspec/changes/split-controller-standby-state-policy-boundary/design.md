## StructureMesh Decision

Selected candidate:

- `skills/flowpilot/assets/flowpilot_router_controller_scheduler_standby.py`

Selected branch:

- Foreground standby state and foreground-mode policy.

Not selected:

- The public `foreground_controller_standby` polling loop, because it owns
  runtime IO and foreground loop behavior.
- The `controller_patrol_timer` payload, because it remains tied to the public
  CLI-facing patrol result.
- Continuous standby row materialization, because it is a separate scheduler
  write boundary.

## Target Structure

- `flowpilot_router_controller_scheduler_standby.py`
  - public compatibility entrypoints;
  - daemon, ledger, current-wait, and snapshot assembly;
  - patrol timer result assembly;
  - import/export of the state-policy child helpers.

- `flowpilot_router_controller_scheduler_standby_policy.py`
  - standby-state classifier;
  - state-to-foreground-mode and permission mapping;
  - no router facade import, no file IO, and no scheduler write authority.

## Leaf Model Boundary

`runtime_owner.standby_state_policy_boundary` owns the matrix:

- terminal status;
- user-required status;
- daemon-liveness-check status;
- pending Controller action presence;
- wait-target condition family.

For every combination, the code may output only the declared standby states and
foreground modes. If future tests create multiple primary-looking evidence
rows for this leaf, split the leaf again instead of relabeling evidence.

## Validation

- Compile parent, child, focused test, and source-audited model files.
- Run the full Cartesian standby policy test.
- Run focused foreground Controller standby tests.
- Run model-test alignment and full coverage inventory checks.
- Confirm the standby parent no longer appears as a deferred StructureMesh
  surface.
