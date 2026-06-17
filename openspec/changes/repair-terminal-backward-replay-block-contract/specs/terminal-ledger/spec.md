## ADDED Requirements

### Requirement: Terminal replay blockers do not become closure evidence
FlowPilot terminal ledger state SHALL distinguish accepted terminal replay
closure evidence from blocking terminal replay findings. A blocking terminal
replay result MUST leave final closure blocked until the affected repair or
replay route has been completed and a later passing replay is accepted.

#### Scenario: Blocking replay records blocker only
- **WHEN** a mechanically valid terminal replay result has `passed=false`
- **THEN** runtime MUST record the terminal replay blocker and failing segment
  context in the current blocker flow
- **AND** runtime MUST keep `closure_confirmed_by_backward_replay` unset or
  false
- **AND** runtime MUST keep final closure decision blocked.

#### Scenario: Later passing replay can close
- **WHEN** PM completes the required repair or replay path after a terminal
  replay blocker
- **AND** Reviewer submits a later mechanically valid terminal replay result
  with `passed=true` covering all runtime-issued current targets
- **THEN** runtime MAY record accepted terminal replay closure evidence
- **AND** final closure MAY continue if every other closure blocker is clean.
