## ADDED Requirements

### Requirement: Repairable final-closure combinations use normal repair before break-glass

FlowPilot SHALL treat missing final route-wide ledger, terminal replay, node
acceptance plan, node-context package, and requirement matrix evidence as
normal repairable closure blockers while any legal PM/runtime repair action can
be produced.

#### Scenario: Final closure has repairable missing evidence
- **WHEN** final closure detects one or more missing current closure evidence
  items
- **AND** runtime can issue a legal PM, reviewer, node-acceptance, node-context,
  or terminal-replay repair packet
- **THEN** Controller MUST continue through normal repair and MUST NOT open
  break-glass for that occurrence

#### Scenario: Normal repair cannot produce legal next action
- **WHEN** final closure blockers remain but Router cannot produce any legal
  current repair action
- **THEN** Controller MAY open break-glass after recording the failed normal
  repair lanes

### Requirement: Break-glass threshold remains explicitly tested

FlowPilot SHALL preserve dedicated tests showing that repeated same-root-cause
control-plane blockers open break-glass at the configured threshold.

#### Scenario: Same root cause reaches threshold
- **WHEN** the same current-contract blocker root cause repeats until the
  configured threshold is reached
- **THEN** Controller MUST open break-glass and record the repeated lineage

#### Scenario: Same root cause below threshold
- **WHEN** the same current-contract blocker root cause repeats below the
  configured threshold
- **THEN** Controller MUST keep using normal repair, reject, or reissue routing
