## ADDED Requirements

### Requirement: Foreground startup waits for active runtime writers
FlowPilot SHALL treat fresh runtime JSON write locks encountered by foreground
startup/status reads as settlement-in-progress evidence and retry after the
writer settles.

#### Scenario: foreground start sees fresh runtime writer
- **WHEN** a foreground startup command needs runtime JSON while a fresh
  runtime write lock is present
- **THEN** FlowPilot waits for the active writer to settle and retries the
  read
- **AND** FlowPilot MUST NOT return a fatal startup error solely because the
  fresh lock existed.

#### Scenario: stale runtime writer remains a failure
- **WHEN** a foreground startup command needs runtime JSON while the matching
  runtime write lock is stale
- **THEN** FlowPilot uses the existing stale-write failure path rather than
  waiting indefinitely.

### Requirement: Startup receipt application has a single final owner
FlowPilot SHALL reconcile startup daemon bootloader Controller receipts through
the existing startup receipt application path before marking startup action
rows or scheduler rows as Router-reconciled.

#### Scenario: daemon bootloader postcondition writes a done receipt
- **WHEN** a startup daemon bootloader action writes or observes a done
  Controller receipt
- **THEN** FlowPilot applies the startup postcondition through the existing
  startup receipt effect handler
- **AND** the resulting action-row and scheduler-row reconciliation source
  MUST be the startup Controller receipt owner, not a direct daemon
  postcondition owner.

#### Scenario: startup receipt replay is idempotent
- **WHEN** a startup daemon bootloader receipt has already been reconciled
- **THEN** a later daemon tick or foreground retry treats the receipt as
  already settled
- **AND** FlowPilot MUST NOT create a PM/control blocker from the replay.

#### Scenario: unsupported startup receipt still blocks
- **WHEN** the existing startup receipt effect handler cannot prove the
  startup postcondition from the receipt and run state
- **THEN** FlowPilot keeps the existing unsupported-receipt or blocker path
  instead of marking the row reconciled through a fallback owner.

### Requirement: Live projection accepts post-release startup packet states
FlowPilot's focused startup-settlement projection SHALL treat a Router-released
`user_intake` packet as released after the PM opens the packet body or after a
terminal lifecycle records that the previously released packet was stopped by
the user.

#### Scenario: released startup packet is opened by PM
- **WHEN** the packet ledger records Router startup release of `user_intake`
  to the project manager
- **AND** the packet status later becomes `packet-body-opened-by-recipient`
- **THEN** the live projection MUST treat startup `user_intake` as released
  rather than reporting an unreleased-packet finding.

#### Scenario: terminal lifecycle preserves prior release evidence
- **WHEN** the packet ledger records Router startup release of `user_intake`
  before a user stop or terminal lifecycle status
- **THEN** the live projection MUST preserve that release evidence
- **AND** it MUST NOT require the top-level active packet status to remain at
  the earlier `envelope-relayed` state.
