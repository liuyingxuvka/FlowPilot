## ADDED Requirements

### Requirement: Role recovery injects current-run memory before replay

After a background role is restored or replaced, Router SHALL require current-run role memory and allowed metadata context to be injected before any outstanding obligation for that role is settled or reissued.

#### Scenario: Recovered role has memory before replay

- **WHEN** `recover_role_agents` reports a recovered role with `role_recovery_roles_restored=true`
- **THEN** Router records that the role received current-run role memory and controller-visible run metadata before replaying waits for that role

#### Scenario: Missing memory blocks replay

- **WHEN** a role is recovered but current-run role memory cannot be loaded or injected
- **THEN** Router escalates recovery rather than issuing replacement ACK or work obligations

### Requirement: Router scans recovered-role obligations

Router SHALL scan current-run wait rows, card return waits, and packet ownership metadata for obligations whose target or waiting role is the recovered role.

#### Scenario: Multiple waits are discovered

- **WHEN** the recovered role has multiple unresolved wait rows in the scheduler or controller ledgers
- **THEN** Router builds a replay candidate list containing each unresolved obligation and its original order

#### Scenario: Unrelated waits are ignored

- **WHEN** wait rows target roles other than the recovered role
- **THEN** Router does not replay or supersede those rows as part of the recovered role replay

### Requirement: Existing valid evidence settles the original wait

Router SHALL settle an outstanding obligation without replay when a valid current-run ACK or output envelope already satisfies the original expected evidence.

#### Scenario: Existing ACK satisfies wait

- **WHEN** a card ACK envelope exists for the expected delivery, current run, role, card, return kind, and hash
- **THEN** Router marks the original ACK wait satisfied without issuing a replacement ACK task

#### Scenario: Existing output satisfies wait

- **WHEN** an output envelope exists for the expected current-run role, packet or report contract, return kind, and hash
- **THEN** Router marks the original output wait satisfied without issuing a replacement work task

### Requirement: Missing or invalid evidence creates replacement obligations

Router SHALL create a replacement obligation for missing, invalid, stale, or superseded evidence instead of asking PM to acknowledge successful mechanical recovery.

#### Scenario: Missing ACK creates replacement ACK task

- **WHEN** an outstanding card wait lacks a valid ACK envelope after role recovery
- **THEN** Router creates a replacement ACK task that references the original delivery and expected ACK path

#### Scenario: Missing formal output creates replacement work task

- **WHEN** an outstanding role-decision or packet wait lacks a valid output envelope after role recovery
- **THEN** Router creates a replacement work or resume task that references the original work authority and output contract

#### Scenario: Invalid old-agent output is quarantined

- **WHEN** an output exists but belongs to a superseded or mismatched agent identity
- **THEN** Router quarantines that output for audit and creates a replacement output obligation for the recovered role

### Requirement: Replacement obligations preserve original order

When several obligations require replay, Router SHALL issue replacement obligations in the original scheduler/controller order and stop issuing later replacements if an earlier replacement cannot be created.

#### Scenario: Ordered replay

- **WHEN** a recovered role has three missing obligations with original orders 2, 4, and 5
- **THEN** Router issues replacement rows in order 2, then 4, then 5

#### Scenario: Failed replacement stops later replay

- **WHEN** Router cannot durably create the replacement for the first missing obligation
- **THEN** Router leaves later obligations unreplayed and records the blocker instead of skipping ahead

### Requirement: Original rows are superseded only after replacement is durable

Router SHALL mark an original wait row `superseded` only after its replacement row exists in the controller action ledger and carries a reverse link to the original row.

#### Scenario: Replacement row links to original

- **WHEN** Router creates a replacement row for a missing obligation
- **THEN** the replacement row includes `replaces`, `replacement_reason`, and `original_order`

#### Scenario: Original row links to replacement

- **WHEN** the replacement row has been durably written
- **THEN** Router marks the original row `superseded` and records `superseded_by` pointing at the replacement row

### Requirement: PM escalation is reserved for semantic ambiguity

Router SHALL notify PM after role recovery only when mechanical replay cannot safely determine continuation.

#### Scenario: Mechanical replay avoids PM

- **WHEN** recovery succeeds and all waits are settled or replacement obligations are issued without conflict
- **THEN** Router does not deliver a PM freshness or recovery-decision card solely to announce that the role was restored

#### Scenario: Conflicting outputs require PM

- **WHEN** two valid-looking outputs conflict or packet ownership cannot be mechanically resolved
- **THEN** Router escalates to PM with controller-visible envelope metadata and does not let Controller choose the winning output

#### Scenario: Route semantics changed

- **WHEN** replay would require changing route scope, acceptance criteria, or task semantics
- **THEN** Router escalates to PM before issuing replacement work
