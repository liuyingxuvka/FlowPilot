## MODIFIED Requirements

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
