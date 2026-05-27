## ADDED Requirements

### Requirement: Wait Reconciliation Uses Source Closure Classification
FlowPilot wait reconciliation SHALL settle passive waits, ACK waits, role-output
waits, and scheduler waits from the closure classification of their source
obligation.

#### Scenario: Passive wait settles after source obligation closes
- **WHEN** a passive wait points at an obligation that the closure kernel now
  classifies as `closed_success` or `closed_terminal`
- **THEN** Router settles or supersedes the wait instead of reissuing it

#### Scenario: Source obligation still open keeps wait active
- **WHEN** a wait points at an obligation that the closure kernel classifies as
  `open`, `repair_required`, `invalid_or_incomplete`, or
  `unknown_needs_recheck`
- **THEN** Router keeps the wait visible or routes a repair action according to
  the existing wait contract
