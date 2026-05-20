## ADDED Requirements

### Requirement: Controller-Router Reconciliation Shares Closure Decisions
Router-controller reconciliation SHALL use the shared closure kernel when
projecting Controller-visible action rows and Router-executable obligations into
blocking or nonblocking workflow state.

#### Scenario: Controller-visible closure matches Router obligation closure
- **WHEN** a Controller action row and Router obligation row refer to the same
  obligation identity and the closure kernel classifies the obligation as
  nonblocking
- **THEN** Router reconciliation MUST NOT re-open the same obligation through a
  stale pending action, scheduler row, or passive wait projection

#### Scenario: Identity mismatch cannot close another obligation
- **WHEN** a Controller row has a closed status but its identity does not match
  the Router obligation being reconciled
- **THEN** the closure kernel classification for that Router obligation remains
  blocking or repair-required
