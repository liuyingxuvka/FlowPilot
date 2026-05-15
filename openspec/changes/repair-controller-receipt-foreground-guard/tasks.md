## 1. Model And Contract

- [x] 1.1 Upgrade the persistent Router daemon FlowGuard model for the receipt/fact and foreground-exit misses.
- [x] 1.2 Record the OpenSpec change for the minimal repair boundary.

## 2. Runtime Implementation

- [x] 2.1 Route `sync_display_plan` Controller receipt reconciliation through a Router-owned display fact writer.
- [x] 2.2 Expose foreground exit policy in standby/status metadata.
- [x] 2.3 Update Controller runtime guidance so ready Controller actions block foreground ending.

## 3. Tests And Validation

- [x] 3.1 Add focused runtime tests for receipt-only display sync not repeating.
- [x] 3.2 Add focused runtime tests for foreground exit policy on pending Controller actions.
- [x] 3.3 Run focused FlowGuard, Router tests, OpenSpec validation, and install sync/audit.

## 4. Finalization

- [x] 4.1 Update FlowGuard adoption notes.
- [x] 4.2 Review and stage all required changes, including compatible peer-agent changes.
- [x] 4.3 Commit the synchronized local git version.
