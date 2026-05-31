## 1. OpenSpec And FlowGuard Model

- [x] 1.1 Add OpenSpec requirements for mandatory route-node pre-work FlowGuard gates.
- [x] 1.2 Add a focused FlowGuard model/check for node design, pre-work FlowGuard, PM repair, worker execution, post-result FlowGuard, and Reviewer independence.

## 2. Runtime Implementation

- [x] 2.1 Add current-generation node pre-work FlowGuard state to route nodes.
- [x] 2.2 Issue runtime-owned pre-work FlowGuard packets after PM node design/acceptance and before worker packets.
- [x] 2.3 Record pre-work FlowGuard reports as PM-visible work-order evidence.
- [x] 2.4 Route pre-work FlowGuard blocks back to PM repair and require a fresh pass after repair.
- [x] 2.5 Keep post-result FlowGuard and independent Reviewer gates unchanged.

## 3. Tests And Validation

- [x] 3.1 Add focused runtime tests for pass, block/repair/recheck, artifact visibility, and route-selection policy.
- [x] 3.2 Run OpenSpec validation, focused FlowGuard checks, targeted unit tests, and install checks.
- [x] 3.3 Rebuild/check project topology if changed runtime/model/test surfaces require it.

## 4. Repository Sync

- [x] 4.1 Sync the repo-owned FlowPilot skill into the local installed version.
- [x] 4.2 Review git status and preserve unrelated parallel worktree changes.
