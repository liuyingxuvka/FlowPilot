## 1. Model Contract

- [x] 1.1 Update focused FlowGuard dispatch-gate model so ACK-only stale waits can clear on ACK but output-bearing work remains busy until output evidence.
- [x] 1.2 Update focused scheduler/card-envelope model coverage for ACK-only versus output-bearing wait settlement.

## 2. Runtime Implementation

- [x] 2.1 Extend existing Router return settlement/reconciliation helpers to close stale ACK passive waits and scheduler rows.
- [x] 2.2 Ensure output-bearing card ACK settlement does not clear work busy unless the matching output event is recorded.
- [x] 2.3 Reuse existing write-lock wait/retry behavior and avoid treating active writes as corruption.

## 3. Runtime Tests And Prompts

- [x] 3.1 Add tests for ACK-only card ACK clearing stale waits.
- [x] 3.2 Add tests proving output-bearing card ACK does not clear busy until the output event returns.
- [x] 3.3 Add the smallest prompt/card wording update needed to preserve ACK-is-receipt-only semantics.

## 4. Verification And Sync

- [x] 4.1 Run focused FlowGuard checks and targeted runtime tests; skip Meta/Capability by user direction.
- [x] 4.2 Validate the OpenSpec change.
- [x] 4.3 Sync the installed local FlowPilot skill from the repository and verify install freshness.
