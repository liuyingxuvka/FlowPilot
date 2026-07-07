## ADDED Requirements

### Requirement: PM dispositions close actionable Reviewer suggestions
FlowPilot SHALL require PM to record a current disposition for every actionable
Reviewer suggestion that needs PM attention before the dependent gate or final
closure advances.

#### Scenario: PM accepts or rejects a concrete suggestion
- **WHEN** Reviewer returns a PM-actionable suggestion in
  `pm_suggestion_items`
- **THEN** PM SHALL either adopt it, repair or reissue current work, redesign
  through the current route-mutation path, reject with reason, waive with
  authority, stop for the user, record it for FlowPilot maintenance, or bind it
  to a named downstream node or gate.

#### Scenario: Vague deferral is not a disposition
- **WHEN** PM uses `defer_to_named_node`
- **THEN** PM SHALL name an already existing downstream node or gate and the
  evidence responsibility that will decide the suggestion
- **AND** PM SHALL NOT use deferral to mean "later maybe" or unresolved
  postponement.

### Requirement: PM preserves optimization authority
FlowPilot SHALL keep soft quality opportunities as PM decision-support unless
they expose a hard current-gate failure.

#### Scenario: Soft sub-target score remains advisory
- **WHEN** Reviewer reports a score below `9/10` while the minimum hard gate
  passed and no hard failure is named
- **THEN** PM SHALL treat the score as decision-support
- **AND** PM SHALL own whether to optimize, continue, reject the suggestion,
  waive with authority, stop, or ask the user.

#### Scenario: Hard failure remains repair-bound
- **WHEN** Reviewer names an unmet hard requirement, missing proof, semantic
  downgrade, unverifiable acceptance surface, role-boundary failure, protocol
  violation, or current quantitative gap
- **THEN** PM SHALL route repair, reissue, waiver, route mutation, or stop
  through the existing current-contract paths before the gate can advance.
