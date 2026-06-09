## 1. OpenSpec And FlowGuard Boundary

- [x] 1.1 Validate the new OpenSpec artifacts before implementation.
- [x] 1.2 Inspect current route-depth, parent-entry, display, and packet-review owners for existing field coverage and overlap with parallel changes.
- [x] 1.3 Record the FlowGuard route decision and minimum revalidation plan for this conservative process-gate change.

## 2. Prompt And Card Updates

- [x] 2.1 Update PM route skeleton language to require one canonical executable route tree and remove PM-authored dual-plan wording.
- [x] 2.2 Update route display/card language so `display_plan` is described as a Router-derived projection/cache rather than route authority.
- [x] 2.3 Update FlowGuard operator route-process guidance to simulate ordered traversal, broad leaves, child-skill projection, parent replay, and final closure using existing hard verdict fields.
- [x] 2.4 Update Reviewer route and node-plan guidance to block broad leaves, parent worker dispatch, and worker-replanning leaves without requiring extra route-node fields.

## 3. Runtime Dispatch Gate

- [x] 3.1 Add a small runtime helper that identifies non-worker-dispatchable route nodes from existing `node_kind` and `child_node_ids`.
- [x] 3.2 Use that helper before worker task packet creation so parent/module or child-bearing nodes cannot receive worker packets.
- [x] 3.3 Keep accepted node acceptance plans as execution context only; do not let them override parent/module route shape.

## 4. Tests And FlowGuard Evidence

- [x] 4.1 Add focused unit tests for parent/module worker dispatch refusal.
- [x] 4.2 Add focused unit tests for child-bearing nodes declared as leaves.
- [x] 4.3 Update fake E2E or strict-route test fixtures so the happy path includes at least one parent/module and child leaf route.
- [x] 4.4 Add or update card coverage tests for single canonical route and derived display language.
- [x] 4.5 Run targeted tests and FlowGuard model checks for route, packet-review, planning-quality, and display surfaces.

## 5. Sync And Completion Evidence

- [x] 5.1 Rebuild and check FlowGuard project topology if changed surfaces require it.
- [x] 5.2 Run source install checks before local skill sync.
- [x] 5.3 Sync repository-owned FlowPilot skill files to the installed local skill.
- [x] 5.4 Run local install sync audit and installed skill check after sync.
- [x] 5.5 Review git status, preserve peer changes, and record FlowGuard/KB postflight evidence.
