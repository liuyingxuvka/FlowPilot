## Why

FlowPilot keeps seeing same-class stalls because different ledgers and role
surfaces still decide "is this obligation closed?" with local status lists. A
Controller row can be closed while a current-scope scan still treats it as
pending, and the same drift can recur for Worker, PM, Reviewer, packet, ACK, or
terminal records.

This change introduces one small closure classification kernel so blocking
scans ask the same question everywhere: whether a record still blocks progress.

## What Changes

- Add a shared FlowPilot closure kernel that normalizes role-specific lifecycle
  records into `open`, `closed_success`, `closed_terminal`, `repair_required`,
  `invalid_or_incomplete`, or `unknown_needs_recheck`.
- Route high-risk blocking scans through the shared kernel instead of local
  hand-written closed-status sets.
- Cover Controller action rows, router scheduler waits, role deliveries, ACK
  returns, packet/result lifecycle records, PM/reviewer gate package records,
  and terminal lifecycle records at the classification boundary.
- Preserve domain-specific contracts: semantic review, worker self-checks,
  reviewer package sufficiency, and signed-artifact immutability remain separate
  hard gates.
- Add FlowGuard model coverage for same-class closure drift outside Controller,
  including worker/PM/reviewer/packet-style records.

## Capabilities

### New Capabilities

- `flowpilot-closure-kernel`: Defines the cross-surface closure classification
  contract used by runtime blockers, waits, dispatch gates, and terminal scans.

### Modified Capabilities

- `current-scope-pre-review-reconciliation`: Current-scope blockers must use
  canonical closure classification rather than local status lists.
- `router-controller-ledger-reconciliation`: Controller-visible and
  Router-executable records must share the same blocking/nonblocking closure
  decision.
- `wait-reconciliation`: Passive and active waits must settle from the same
  closure classification used by their source obligations.
- `system-card-ack-clearance`: ACK wait settlement must use the closure kernel
  while keeping ACK settlement separate from output-work completion.

## Impact

- Affected runtime code under `skills/flowpilot/assets/`, especially current
  scope blocker scans, controller/scheduler receipt projections, expected wait
  reconciliation, system-card/card-return reconciliation, and terminal closure
  summaries.
- Affected FlowGuard simulations for control-plane ledger consolidation and
  current-scope pre-review reconciliation; additional focused closure-kernel
  scenarios will be added.
- Affected tests for status vocabulary drift, resolved/reconciled row handling,
  and non-Controller same-class closure hazards.
- Local installed FlowPilot skill sync, install audit, and local git version
  update are required after validation.
