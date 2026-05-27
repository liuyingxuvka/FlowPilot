# role-output-transaction-boundaries Specification

## Purpose
TBD - created by archiving change harden-role-output-transaction-boundaries. Update Purpose after archive.
## Requirements
### Requirement: PM package disposition uses registry-backed role output
FlowPilot SHALL define PM package result disposition as a registry-backed `role_output_runtime` output before Router accepts PM disposition events for material, research, or current-node packages.

#### Scenario: Router supplies PM package disposition output contract
- **WHEN** Router waits for a PM package result disposition
- **THEN** the wait state MUST name the expected output contract id, output type, allowed PM role, and Router event

#### Scenario: Manual PM disposition envelope is rejected
- **WHEN** PM submits a Controller-visible event envelope for package disposition with decision-body fields such as `decision`, `decided_by_role`, or package metadata at the envelope top level
- **THEN** Router MUST reject or quarantine the submission instead of treating it as valid continuation evidence

### Requirement: PM package disposition body remains separate from envelope
FlowPilot SHALL keep PM disposition body content in a file-backed body and expose only body references, hashes, receipt references, output type, and contract id in the Controller-visible role-output envelope.

#### Scenario: Standard PM disposition envelope is visible to Controller
- **WHEN** PM submits a package disposition through `role_output_runtime`
- **THEN** the Controller-visible envelope MUST contain `body_ref` and `runtime_receipt_ref`
- **AND** the envelope MUST NOT contain decision-body fields at top level

### Requirement: PM package absorption is a registered control transaction
FlowPilot SHALL validate PM package disposition through a registered result-absorption control transaction before it mutates package artifacts, batch status, wait flags, run state, status summaries, or reviewer-release evidence.

#### Scenario: PM absorption commits all required state surfaces
- **WHEN** a PM package disposition decision is accepted as absorbed
- **THEN** the transaction MUST commit the disposition record, any formal gate package, packet or batch ledger state, run-state flags, wait closure evidence, and status projection as one transaction outcome

#### Scenario: Interrupted PM absorption can be replayed safely
- **WHEN** PM package absorption finds existing disposition artifacts from an earlier interrupted attempt
- **THEN** Router MUST verify the transaction identity, expected hashes, and required commit targets before marking the disposition complete
- **AND** Router MUST quarantine or block mismatched half-written artifacts

### Requirement: Control-blocker actions carry blocker identity consistently
FlowPilot SHALL include existing blocker identity fields in deterministic action identity for every control-blocker-related action that carries blocker identity.

#### Scenario: Distinct blocker waits do not share action identity
- **WHEN** two PM waits or repairs have different `blocker_id` or `blocker_artifact_path`
- **THEN** Router MUST produce different Controller action ids and scheduler idempotency keys

#### Scenario: Same blocker wait remains idempotent
- **WHEN** Router repeats the same blocker-related wait with the same blocker identity
- **THEN** Router MUST reuse the same deterministic identity instead of creating duplicate Controller work
