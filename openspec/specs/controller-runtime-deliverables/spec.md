# controller-runtime-deliverables Specification

## Purpose
TBD - created by archiving change unify-controller-runtime-deliverables. Update Purpose after archive.
## Requirements
### Requirement: Controller formal deliverables use runtime contracts
Controller formal deliverables that create Router-visible durable facts SHALL
use a runtime output contract and runtime receipt instead of a
Controller-specific hand-written deliverable format.

#### Scenario: Controller boundary confirmation is delivered
- **WHEN** Controller completes the boundary-confirmation action
- **THEN** the submitted evidence includes a runtime output contract id,
  artifact path/hash metadata, and a runtime receipt that Router can validate

#### Scenario: Controller hand-writes a formal artifact
- **WHEN** Controller submits a receipt and a file without valid runtime
  contract evidence for a formal deliverable
- **THEN** Router treats the row as incomplete and schedules bounded repair
  rather than marking the postcondition complete

### Requirement: Controller lightweight actions remain receipt-only
Controller actions that do not create Router-visible durable facts SHALL remain
receipt-only and SHALL NOT require runtime output contracts.

#### Scenario: Controller performs a display sync
- **WHEN** Controller completes a lightweight display or standby action
- **THEN** Router reconciles the action through the existing lightweight receipt
  path without requiring a formal runtime output envelope

### Requirement: Controller runtime outputs preserve authority boundaries
Controller runtime output contracts SHALL be limited to mechanical
control-plane artifacts and MUST NOT allow Controller to read sealed bodies,
approve gates, mutate route state, implement worker work, or create arbitrary
project evidence.

#### Scenario: Controller output contract is selected
- **WHEN** Router issues a Controller formal deliverable row
- **THEN** the selected contract is a Controller-scoped control-plane contract
  with Controller sealed-body reads and route-approval authority disabled

### Requirement: Repair budget counts failed returned evidence
Controller deliverable repair accounting SHALL count a repair attempt as failed
only after the repair row returns with missing or invalid runtime evidence.

#### Scenario: Second repair row is issued
- **WHEN** Router schedules the second Controller repair row
- **THEN** Router does not create a budget-exhausted blocker until that second
  row returns invalid or missing runtime evidence
