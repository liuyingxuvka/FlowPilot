## Why

Recent FlowPilot runtime evidence showed that a Controller boundary
confirmation can be fully present in durable files and ledgers while Router
state flags still say the boundary is unfinished. The daemon then risks
re-exposing the same completed Controller action or sleeping before it has
drained immediately available Router work.

## What Changes

- Add a narrow daemon projection reconciliation gate for Controller boundary
  confirmation evidence before Router chooses or returns the next action.
- Treat the durable boundary artifact, Controller receipt/action ledger,
  Router scheduler row, and Router flags as four projections of one fact that
  must converge before progress decisions.
- Extend the focused daemon reconciliation FlowGuard model with explicit
  fast-loop and sleep/continue hazards so the model catches stale projection
  reuse, action exposure without a pending row, and unnecessary sleep when the
  queue stopped only because the per-tick budget was reached.
- Keep the existing broad wait-reconciliation, two-table scheduler, and packet
  continuation changes intact; this change is a hardening slice over the
  projection gap, not a second scheduler rewrite.
- Skip heavyweight Meta and Capability model suites for this pass by user
  direction, and record the residual boundary in the adoption note.

## Capabilities

### New Capabilities

- `daemon-projection-reconciliation`: Router daemon reconciles durable
  Controller-boundary projections and only sleeps when no immediate Router work
  remains after the current queue pass.

### Modified Capabilities

- None. Existing OpenSpec capabilities are represented as pending change-local
  artifacts rather than archived baseline specs in this repository.

## Impact

- Router runtime:
  - `skills/flowpilot/assets/flowpilot_router.py`
- Focused FlowGuard model and runner:
  - `simulations/flowpilot_daemon_reconciliation_model.py`
  - `simulations/run_flowpilot_daemon_reconciliation_checks.py`
  - `simulations/flowpilot_daemon_reconciliation_results.json`
- Runtime tests:
  - `tests/test_flowpilot_router_runtime.py`
- Documentation and adoption evidence:
  - `docs/flowpilot_daemon_projection_reconciliation_plan.md`
  - `docs/flowguard_adoption_log.md`
- Local sync:
  - `scripts/install_flowpilot.py --sync-repo-owned --json`
  - install/audit checks for the local installed FlowPilot skill
