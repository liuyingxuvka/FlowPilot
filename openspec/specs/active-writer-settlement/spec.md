# active-writer-settlement Specification

## Purpose
TBD - created by archiving change defer-active-writer-settlement. Update Purpose after archive.
## Requirements
### Requirement: Active runtime writes defer daemon blockers
FlowPilot SHALL treat active runtime writes as settlement-in-progress evidence
instead of immediate control-blocker evidence.

#### Scenario: fresh ledger write lock during receipt folding
- **WHEN** daemon receipt reconciliation needs a runtime JSON ledger whose fresh
  write lock shows another writer is active
- **THEN** Router SHALL defer reconciliation to a later daemon tick
- **AND** Router SHALL NOT create a control blocker solely because that ledger
  was incomplete during the active write.

#### Scenario: stale or unsupported evidence still blocks
- **WHEN** the write lock is stale, the JSON is corrupt without active writer
  evidence, or the receipt type is unsupported
- **THEN** Router SHALL use the existing blocker/repair path rather than waiting
  indefinitely.

### Requirement: Controller action scans ignore transient files
FlowPilot SHALL ignore transient Controller action write artifacts when
rebuilding or reconciling the Controller action ledger.

#### Scenario: transient action file appears during daemon scan
- **WHEN** `runtime/controller_actions` contains `.tmp-*.json`
- **THEN** Router SHALL NOT read it as a Controller action
- **AND** Router SHALL NOT stop the daemon if the transient file disappears
  before read.

### Requirement: Startup role flags fold as a stable pair
FlowPilot SHALL fold startup role flags from the bootstrap record into Router
state only when the paired role-start and core-prompt flags are stable together.

#### Scenario: paired startup role flags are present
- **WHEN** bootstrap startup state records both `roles_started` and
  `role_core_prompts_injected`
- **THEN** the daemon SHALL set both Router state flags before computing the
  next action.

#### Scenario: partial startup role flags are visible
- **WHEN** only one of the paired startup role flags is visible
- **THEN** Router SHALL wait for settlement rather than marking startup complete
  or creating a PM blocker from the partial pair.

### Requirement: Dead-owner write locks are immediately recoverable
FlowPilot SHALL distinguish a live active writer from a fresh JSON write lock
whose recorded owner process is not alive.

#### Scenario: Fresh write lock owner is dead
- **WHEN** Router attempts to write a runtime JSON file and its `.write.lock`
  is fresh but the recorded owner process is confirmed dead
- **THEN** Router MUST replace the lock without waiting for the stale-lock age
  threshold
- **AND** Router MUST record dead-owner takeover evidence for the affected
  path.

#### Scenario: Fresh write lock owner is alive
- **WHEN** Router attempts to write a runtime JSON file and its `.write.lock`
  is fresh with a live recorded owner process
- **THEN** Router MUST treat the file as active writer settlement in progress
  and defer the competing write instead of taking over the lock.

### Requirement: Writer crash evidence remains visible
FlowPilot SHALL preserve diagnostic evidence when it recovers a JSON write lock
left by a dead writer.

#### Scenario: Dead-owner takeover occurs
- **WHEN** Router replaces a JSON write lock because the owner process is dead
- **THEN** the takeover evidence MUST include the lock path, target JSON path,
  previous owner pid when available, classification, and timestamp
- **AND** the evidence MUST NOT mark the recovered write as a clean live-writer
  settlement.
