## Why

FlowPilot still has several Router maintenance paths where the code is hard to
reason about because many nested or sequential branches write the same
observable state in slightly different ways. The next simplification pass should
prune those logic trees first, then split files only where the reduced logic
needs clearer ownership.

## What Changes

- Add a FlowGuard-backed branch-pruning model for Router reconciliation logic.
- Classify complex reconciliation branches into a small result-case vocabulary:
  `noop`, `reconciled`, `superseded`, `replay_required`, `retry_pending`,
  `repair_pending`, and `blocked`.
- Require equivalence or conformance-replay evidence before collapsing
  behavior-bearing branches that write run state, controller action rows,
  controller receipts, history records, or control blockers.
- Treat file splitting as a secondary structure step that may follow branch
  pruning when it improves ownership, readability, and validation boundaries.
- Keep public Router, receipt, role-output, and runtime-state import surfaces
  compatible until StructureMesh proves a safe facade boundary.

## Capabilities

### New Capabilities

- `router-reconciliation-branch-pruning`: FlowGuard model and acceptance
  contract for reducing Router reconciliation logic branches while preserving
  observable behavior.

### Modified Capabilities

- `repository-maintenance-guardrails`: Clarify that structure optimization must
  prioritize logic contraction and bug-risk reduction over file splitting by
  itself.

## Impact

- Affected planning/model surfaces:
  - `simulations/flowpilot_router_facade_split_catalog.py`
  - `simulations/flowpilot_structure_maintenance_router_catalog.py`
  - `simulations/flowpilot_model_test_alignment_source_code_contracts.py`
  - future branch-pruning model/check artifacts
- Affected implementation candidates for later application:
  - `skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_scheduled.py`
  - `skills/flowpilot/assets/flowpilot_router_role_output_bridge.py`
  - `skills/flowpilot/assets/flowpilot_router_runtime_state.py`
  - `skills/flowpilot/assets/flowpilot_router_controller_scheduler_receipts_packet_folds.py`
- No runtime code is changed by this proposal step.
