## ADDED Requirements

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

### Requirement: Startup activation joins pending startup ACKs

FlowPilot SHALL check startup-scope pending card returns before accepting any PM
startup activation decision.

#### Scenario: PM activation waits for the startup ACK join

- **WHEN** PM submits `pm_approves_startup_activation`
- **AND** at least one startup-scope card ACK remains pending
- **THEN** Router MUST reject or defer the activation event through the existing
  pending-card-return blocker path
- **AND** Router MUST return the ordinary pending-card-return wait/remediation
  for the missing ACK
- **AND** `startup_activation_approved` MUST remain false

#### Scenario: Startup activation opens only after the common join is clean

- **WHEN** all startup-scope card ACKs required for activation have returned
- **AND** reviewer startup facts and PM startup prep are complete
- **AND** PM submits a valid startup activation approval
- **THEN** Router MAY set `startup_activation_approved`
- **AND** route/material work MAY begin only after that activation opens startup
