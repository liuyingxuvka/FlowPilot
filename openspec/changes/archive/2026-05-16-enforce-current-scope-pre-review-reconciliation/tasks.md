## 1. Model And Contract

- [x] 1.1 Add a focused FlowGuard model and runner for current-scope pre-review reconciliation, including local-only, carry-forward, review-created obligation, and no-final-review transition hazards.
- [x] 1.2 Run the focused model check and preserve the result JSON.
- [x] 1.3 Validate the OpenSpec change with strict validation.

## 2. Router Implementation

- [x] 2.1 Add Router helpers that summarize unresolved current-scope obligations without touching future, sibling, or route-wide scopes.
- [x] 2.2 Enforce current-node pre-review reconciliation before `current_node_reviewer_passes_result`.
- [x] 2.3 Preserve existing startup pre-review ACK join behavior and align its metadata with the current-scope reconciliation rule.
- [x] 2.4 Ensure review-created obligations remain local and node completion still requires PM disposition, reviewer pass, and node completion ledger closure.

## 3. Runtime Tests

- [x] 3.1 Add focused Router tests for current-node review blocking on unresolved local obligations.
- [x] 3.2 Add focused Router tests proving future/sibling obligations are not cleared or treated as current-node blockers.
- [x] 3.3 Add focused Router tests for review-created closure obligations before node transition.

## 4. Validation And Sync

- [x] 4.1 Run focused model and runtime checks, excluding `python simulations/run_meta_checks.py` and `python simulations/run_capability_checks.py` by user request.
- [x] 4.2 Sync the local installed FlowPilot skill and verify source freshness.
- [x] 4.3 Record FlowGuard adoption and KB postflight notes.
