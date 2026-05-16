## ADDED Requirements

### Requirement: Review Work Requires Current-Scope Reconciliation
Before reviewer work starts for startup or the active node, the system SHALL reconcile only the current scope's review-affecting obligations and SHALL NOT start reviewer work while any unresolved local obligation can still change the review package.

#### Scenario: Startup reviewer waits for startup-local reconciliation
- **WHEN** Router is about to deliver or accept startup fact review work and startup-local card returns, Controller actions, or PM prep obligations remain unresolved
- **THEN** Router blocks reviewer work with a current-scope reconciliation wait instead of asking Reviewer to judge an unstable startup package

#### Scenario: Current-node reviewer waits for node-local reconciliation
- **WHEN** Router is about to deliver or accept current-node review work and current-node worker result, PM disposition, ACK, or local blocker obligations remain unresolved
- **THEN** Router blocks reviewer work with a current-node reconciliation wait instead of starting result review

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
