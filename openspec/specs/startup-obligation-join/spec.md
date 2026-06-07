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

### Requirement: Startup runtime mechanical audit waits for startup prep ACK join

FlowPilot SHALL check startup prep pending card returns before Runtime/Router
writes startup mechanical audit and before PM receives startup intake release.

#### Scenario: Runtime startup audit waits for prep ACK join

- **WHEN** a startup prep card ACK remains pending
- **AND** Router would otherwise write startup mechanical audit or release PM startup intake
- **THEN** Router MUST return the ordinary pending-card-return wait/remediation
  for the missing prep ACK
- **AND** Router MUST NOT write startup mechanical audit or release PM startup
  intake until the prep ACK join is clean

#### Scenario: PM startup intake release waits for prep ACK join

- **WHEN** PM submits `pm_releases_startup_intake`
- **AND** at least one startup prep card ACK remains pending
- **THEN** Router MUST reject or defer the report through the existing
  pending-card-return blocker path
- **AND** Router MUST return the ordinary pending-card-return wait/remediation
  for the missing ACK
- **AND** `startup_intake_released` MUST remain false

### Requirement: PM startup intake release uses existing same-role ACK blocking

FlowPilot SHALL NOT add a separate all-startup ACK join before PM startup
intake release. PM startup intake release decisions SHALL use the ordinary
same-role card ACK dependency for `pm.startup_intake_release`.

#### Scenario: PM startup intake release waits for its own card ACK

- **WHEN** PM submits `pm_releases_startup_intake`
- **AND** the PM startup intake release card ACK remains pending
- **THEN** Router MUST block through the existing same-role pending-card-return
  path
- **AND** `startup_intake_released` MUST remain false

#### Scenario: Startup intake release opens after runtime audit and PM card ACK

- **WHEN** startup runtime mechanical audit is complete
- **AND** PM has ACKed `pm.startup_intake_release`
- **AND** PM submits a valid startup intake release approval
- **THEN** Router MAY set `startup_intake_released`
- **AND** route/material work MAY begin only after that release opens startup
