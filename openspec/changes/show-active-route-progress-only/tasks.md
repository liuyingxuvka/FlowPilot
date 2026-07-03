## 1. OpenSpec Contract

- [x] 1.1 Capture active-route-only progress semantics.
- [x] 1.2 Validate the OpenSpec change.

## 2. Runtime Implementation

- [x] 2.1 Update `current_progress_fraction` to use the display-only initial planning node plus active route `node_order`.
- [x] 2.2 Stop adding `repair_generation` history to visible progress counts.
- [x] 2.3 Remove packet projection as the early materialization fallback.

## 3. Verification And Sync

- [x] 3.1 Add focused tests for active-route filtering, repair replacement, and no packet fallback.
- [x] 3.2 Update existing progress-fraction tests for the initial-node route source.
- [x] 3.3 Run focused runtime tests and OpenSpec/FlowGuard checks.
- [x] 3.4 Sync the installed local FlowPilot skill copy.
- [x] 3.5 Commit the scoped repository changes without reverting peer work.
