## 1. OpenSpec And FlowGuard Model

- [x] 1.1 Add OpenSpec requirements for PM-authored node context packages.
- [x] 1.2 Extend focused FlowGuard node-gate model/checks with context package
  presence, freshness, and downstream packet attachment.

## 2. Runtime Implementation

- [x] 2.1 Parse and validate PM node context packages from accepted node
  acceptance plan results.
- [x] 2.2 Store context package state on route nodes and invalidate it on repair
  or route mutation replacement.
- [x] 2.3 Attach current node context packages to pre-work FlowGuard, worker,
  post-result FlowGuard, and Reviewer packets.
- [x] 2.4 Block downstream packet issuance when the package is missing or stale.

## 3. Prompt Cards And Contracts

- [x] 3.1 Update PM role guidance so node acceptance plans must return the
  context package.
- [x] 3.2 Update FlowGuard operator and Reviewer guidance so the context package
  is the minimum starting point, not a boundary.

## 4. Tests, Validation, And Sync

- [x] 4.1 Add focused unit tests for missing context, stale context, and context
  attachment across the node packet chain.
- [x] 4.2 Run OpenSpec validation, focused FlowGuard checks, targeted unit tests,
  install checks, and topology rebuild/check.
- [x] 4.3 Sync the repo-owned FlowPilot skill into the local installed version
  and report final git state.
