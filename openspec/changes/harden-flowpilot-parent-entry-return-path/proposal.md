## Why

FlowPilot's existing recursive route rules already say parent/module nodes are entered before descendants, but the runtime can still advance a later sibling parent by immediately descending to its first child before the parent has its own accepted `node_acceptance_plan` and `node_context_package`. That lets final review discover a control-plane hard-gate leak that should have been stopped by the normal node-entry flow.

## What Changes

- Strengthen the existing parent/module entry path so every selected effective node must pass its own current node-entry gate before any child descent.
- Add a standard `control_plane_hard_gate_escape:<gate_type>:<subject_id>` return path for final-dispatch preflight hard-gate leaks that sends execution back to the owning normal gate instead of backfilling at final review.
- Keep parent replay, PM disposition, and final dispatch as assertion points only; they must not become fallback repair paths or Reviewer-owned hard-gate checks.
- Keep final backward review focused on delivered-output, parent composition, and quality review after runtime proves hard-gate completeness.
- Extend FlowGuard model and TestMesh coverage with Cartesian parent-entry and final-dispatch hard-gate cells.

## Capabilities

### New Capabilities

### Modified Capabilities

- `recursive-route-parent-entry`: parent/module entry must require that node's own current accepted node plan and context before child execution.
- `control-plane-failure-canary`: final-dispatch hard-gate leaks must route to the owning normal gate through one current-runtime return path.
- `hard-gate-coverage-matrix`: the hard-gate matrix must enumerate parent-entry and final-dispatch return-path Cartesian cells with executable evidence.

## Impact

- Runtime traversal and final-preflight behavior in `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- Packet/stage evidence surfaces if current evidence fields need to expose owning gate ids for existing families.
- PM and Reviewer runtime cards under `skills/flowpilot/assets/runtime_kit/cards/`.
- FlowGuard simulations and model-test alignment for recursive parent entry, control-plane failure canaries, and hard-gate coverage.
- Focused runtime, fake AI, model, TestMesh, install-sync, and local-install audit checks.
