# startup-obligation-join Specification

## Purpose
TBD - created by archiving change async-startup-obligation-join. Update Purpose after archive.
## Requirements
### Requirement: Startup uses the common interaction ledgers

FlowPilot SHALL represent startup deliveries, Controller receipts, and role ACKs
through the same Controller action ledger and system-card pending-return ledgers
used by the rest of runtime.

#### Scenario: Startup does not create a separate wait table

- **WHEN** Router issues startup card delivery or startup mechanical work
- **THEN** the Controller-visible action MUST be represented in
  `runtime/controller_action_ledger.json`
- **AND** Controller completion MUST be recorded as an ordinary Controller
  receipt for that action row
- **AND** role card ACK obligations MUST be represented as ordinary pending card
  returns
- **AND** Router MUST NOT require a separate startup-only wait table to decide
  the next startup action

### Requirement: Independent startup work may continue while startup ACKs are pending

FlowPilot SHALL allow Router to issue independent startup actions before all
startup-scope card ACKs have returned.

#### Scenario: Startup card ACK does not block independent startup delivery

- **WHEN** a startup-scope card ACK is still pending
- **AND** Router has an independent startup card delivery or startup mechanical
  action that does not depend on that ACK
- **THEN** Router MAY return that independent action before returning the
  pending-card-return wait
- **AND** the pending ACK obligation MUST remain recorded until its ordinary
  ACK clears it

#### Scenario: Non-startup ACKs keep existing blocking behavior

- **WHEN** a non-startup card ACK is pending
- **THEN** Router MUST keep the existing pending-card-return blocking behavior
  before issuing unrelated formal work that could cross the ACK boundary

### Requirement: Reviewer startup review waits for startup prep ACK join

FlowPilot SHALL check startup prep pending card returns before Reviewer begins
live startup fact review.

#### Scenario: Reviewer startup fact card waits for prep ACK join

- **WHEN** a startup prep card ACK remains pending
- **AND** Router would otherwise deliver `reviewer.startup_fact_check`
- **THEN** Router MUST return the ordinary pending-card-return wait/remediation
  for the missing prep ACK
- **AND** Router MUST NOT deliver `reviewer.startup_fact_check` until the prep
  ACK join is clean

#### Scenario: Reviewer startup report waits for prep ACK join

- **WHEN** Reviewer submits `reviewer_reports_startup_facts`
- **AND** at least one startup prep card ACK remains pending
- **THEN** Router MUST reject or defer the report through the existing
  pending-card-return blocker path
- **AND** Router MUST return the ordinary pending-card-return wait/remediation
  for the missing ACK
- **AND** `startup_fact_reported` MUST remain false

### Requirement: PM startup activation uses existing same-role ACK blocking

FlowPilot SHALL NOT add a separate all-startup ACK join before PM startup
activation. PM activation decisions SHALL use the ordinary same-role card ACK
dependency for `pm.startup_activation`.

#### Scenario: PM activation waits for its own card ACK

- **WHEN** PM submits `pm_approves_startup_activation`
- **AND** the PM startup activation card ACK remains pending
- **THEN** Router MUST block through the existing same-role pending-card-return
  path
- **AND** `startup_activation_approved` MUST remain false

#### Scenario: Startup activation opens after reviewer report and PM card ACK

- **WHEN** reviewer startup facts are complete
- **AND** PM has ACKed `pm.startup_activation`
- **AND** PM submits a valid startup activation approval
- **THEN** Router MAY set `startup_activation_approved`
- **AND** route/material work MAY begin only after that activation opens startup
