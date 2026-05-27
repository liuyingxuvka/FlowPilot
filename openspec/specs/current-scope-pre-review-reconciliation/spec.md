# current-scope-pre-review-reconciliation Specification

## Purpose
TBD - created by archiving change enforce-current-scope-pre-review-reconciliation. Update Purpose after archive.
## Requirements
### Requirement: Review Work Requires Current-Scope Reconciliation
Before reviewer work starts for startup or the active node, the system SHALL reconcile only the current scope's review-affecting obligations and SHALL NOT start reviewer work while any unresolved local obligation can still change the review package.

#### Scenario: Drifted stateful postcondition is reconciled before review wait loops
- **WHEN** startup or current-node pre-review reconciliation sees a local Controller row whose receipt and durable evidence are valid but whose Router-owned postcondition flag is false
- **THEN** Router MUST first replay or reclaim that stateful postcondition into the authoritative state
- **AND** Router MUST re-evaluate the local reconciliation blockers from the updated state before returning another wait or Controller action

#### Scenario: Unrecoverable stateful drift blocks with evidence
- **WHEN** pre-review reconciliation sees a local stateful row that claims reconciliation but no valid durable evidence can be found
- **THEN** Router MUST record a repair/blocker reason naming the action, postcondition, and missing evidence
- **AND** Reviewer work MUST remain blocked until that repair/blocker is resolved

### Requirement: Reconciliation Is Local To The Active Scope
The system SHALL limit pre-review reconciliation to the active startup gate or active node scope and SHALL NOT clear, complete, or quarantine future-node, sibling-node, or route-wide obligations as part of local review preparation.

#### Scenario: Future-node obligation remains outside current-node reconciliation
- **WHEN** current-node review preparation runs while a future node has pending planned work
- **THEN** Router leaves the future-node work untouched and does not count it as a blocker for the current-node review

#### Scenario: Carry-forward is explicit
- **WHEN** a current-scope item is intentionally deferred beyond the current scope
- **THEN** Router records the item as carried forward with reason, target scope, owner, and join condition before local reconciliation can pass

### Requirement: Review-Created Obligations Close Before Scope Exit
After reviewer work starts, the system SHALL treat review-created ACKs, reports, pass/block receipts, PM dispositions, and completion ledgers as obligations in the same local scope and SHALL NOT complete or cross the scope until they are resolved or explicitly classified.

#### Scenario: Reviewer pass does not complete node without follow-up closure
- **WHEN** Reviewer passes a current-node result but PM disposition or node completion ledger work remains unresolved
- **THEN** Router keeps the current node open and exposes the next local closure action instead of crossing to the next node

#### Scenario: Reviewer card ACK remains local
- **WHEN** a reviewer card ACK required for the current scope is missing after review card delivery
- **THEN** Router keeps the current scope blocked until the ACK is returned or explicitly classified by the reconciliation rule

### Requirement: No-Final-Review Scopes Reconcile Before Transition
If an active scope has no final reviewer gate, the system SHALL run current-scope reconciliation before completing or crossing the scope boundary.

#### Scenario: No-review node waits before transition
- **WHEN** a node has no final reviewer gate and Router is about to complete or leave that node
- **THEN** Router reconciles current-node obligations first and blocks transition if unresolved local work remains

#### Scenario: Clean no-review node can transition
- **WHEN** a node has no final reviewer gate and all current-node obligations are resolved or explicitly classified
- **THEN** Router may complete or cross the node boundary without requiring an extra reviewer gate

### Requirement: Current-Scope Blockers Use Closure Kernel
Current-scope pre-review reconciliation SHALL decide whether local obligations
still block review by using the shared FlowPilot closure kernel rather than a
module-local list of closed statuses.

#### Scenario: Resolved reconciled Controller action does not block review
- **WHEN** a current-scope Controller action has `status=resolved` and its Router
  reconciliation evidence is complete for the same obligation
- **THEN** pre-review reconciliation treats the action as nonblocking and does
  not keep the current scope in a passive wait

#### Scenario: Closed Worker or PM lifecycle row does not block review
- **WHEN** a current-scope Worker or PM lifecycle record has role-specific
  closed evidence accepted by the closure kernel
- **THEN** pre-review reconciliation treats the record as nonblocking without
  requiring Controller-specific status vocabulary
