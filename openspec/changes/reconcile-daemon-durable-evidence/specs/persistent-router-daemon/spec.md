## MODIFIED Requirements

### Requirement: Router daemon reconciles durable evidence before deciding
The Router daemon SHALL reconcile durable Controller receipts, role-output
runtime submissions, canonical report artifacts, and existing mailbox evidence
before returning a pending action or computing a new action.

#### Scenario: Completed Controller action is not repeated
- **WHEN** a pending Controller action has a matching `done` receipt
- **THEN** Router MUST reconcile that receipt before returning work
- **AND** Router MUST NOT return the same completed pending action again

#### Scenario: Stateful Controller receipt is incomplete
- **WHEN** a stateful Controller action requires Router-owned postconditions
- **AND** its `done` receipt does not include enough payload to apply those postconditions
- **THEN** Router MUST clear the stale pending action
- **AND** Router MUST create a control blocker explaining the incomplete receipt
- **AND** Router MUST NOT silently mark the stateful postconditions complete

#### Scenario: Role output exists in durable ledger
- **WHEN** a valid role-output runtime ledger entry exists for a Router event
- **AND** the corresponding Router flag/event is not recorded
- **THEN** Router MUST reconcile the ledger entry into the Router event exactly once before computing unrelated work

#### Scenario: Canonical report artifact exists but flag is stale
- **WHEN** a canonical startup fact report artifact exists
- **AND** a validated runtime envelope for `reviewer_reports_startup_facts` exists in the role-output ledger
- **AND** `startup_fact_reported` is still false
- **THEN** Router MUST sync the flag and event from durable evidence
- **AND** Router MUST NOT require Controller to hand the same report back manually

#### Scenario: Stale daemon snapshot sees newer durable evidence
- **WHEN** a daemon tick loaded Router state before a role output or Controller receipt was written
- **AND** the durable file exists before next-action computation
- **THEN** Router MUST prefer durable evidence over the stale in-memory pending action
- **AND** Router MUST save only the reconciled state
