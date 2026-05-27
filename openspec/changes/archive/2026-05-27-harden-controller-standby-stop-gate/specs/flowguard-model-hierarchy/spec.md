## ADDED Requirements

### Requirement: Full model confidence covers visible user branches

FlowGuard full-model confidence SHALL include every visible or
user-triggerable branch in the modeled branch inventory. This includes
buttons, displayed actions, status-return modes, wait-target duties, liveness
and recovery actions, and terminal/stop branches. A visible branch that is not
implemented and covered by current model evidence SHALL be hidden, disabled, or
explicitly marked out of scope; it MUST NOT appear as an enabled no-op.

#### Scenario: Visible branch is implemented and modeled

- **WHEN** FlowPilot exposes a visible control, status action, recovery action,
  or terminal/stop branch to the user or foreground Controller
- **THEN** the model hierarchy records the branch in the visible/user-triggered
  inventory
- **AND** current parent or child FlowGuard evidence covers the branch.

#### Scenario: Visible branch is not implemented

- **WHEN** a visible control or branch is not implemented or not covered by
  current model evidence
- **THEN** the branch is hidden, disabled, or explicitly unavailable with a
  recovery path
- **AND** full-model confidence is blocked until the implementation and model
  evidence exist.

#### Scenario: Visible branch evidence is stale

- **WHEN** the implementation, prompt surface, or runtime status branch changes
  after the last visible-branch model evidence was produced
- **THEN** full-model confidence is blocked until the relevant child or parent
  model is refreshed.
