## 1. OpenSpec And Model Setup

- [x] 1.1 Create OpenSpec proposal, design, specification delta, and task list for current status projection hardening.
- [x] 1.2 Add a focused FlowGuard current-status-projection model with finite Cartesian coverage for authority/projection convergence.

## 2. Runtime Projection Repair

- [x] 2.1 Add current derived top-level run/closure/preflight fields to `render_console` and compact status without creating a second authority.
- [x] 2.2 Refresh ledger `status_projection` during run-shell saves before writing ledger and artifacts.
- [x] 2.3 Keep public current blocker rows and role-memory current blocker rows filtered through the current-effective blocker predicate.
- [x] 2.4 Update node-closure rows when PM disposition resolves the node.
- [x] 2.5 Ensure repair-dossier projection stops exposing cleared, retired, superseded, or noncurrent-route blockers as active.

## 3. Cartesian Tests And Negative Cases

- [x] 3.1 Add runtime tests for terminal-complete projection fields across current, console, closure, status projection, and foreground duty.
- [x] 3.2 Add negative tests for cleared/retired/superseded blockers leaking into public current blockers or role memory.
- [x] 3.3 Add node-closure convergence tests for accept, repair, block, stop, and route replacement paths.
- [x] 3.4 Add repair-dossier tests proving noncurrent blocker pointers are history-only.
- [x] 3.5 Add model/runner checks for the Cartesian projection matrix and its known-bad cells.

## 4. Validation And Sync

- [x] 4.1 Run focused unit tests and the new FlowGuard model runner.
- [x] 4.2 Run affected router/runtime tests for terminal, closure, controller/status, repair, and progress surfaces.
- [x] 4.3 Run OpenSpec validation for this change.
- [x] 4.4 Rebuild and check the FlowGuard project topology.
- [x] 4.5 Sync the local installed FlowPilot skill/version and run install/self-check validation.
- [x] 4.6 Inspect final diff for fallback, compatibility aliases, target-app-specific fields, or peer-agent rollback.

Validation note: the focused affected tests and FlowGuard model runner passed. A
broad `router` tier background run was attempted as extra coverage; 42 completed
shards passed, then the supervisor failed while serializing its large meta JSON
with `MemoryError`. That broad tier result is not counted as a full pass.
