## ADDED Requirements

### Requirement: Replayability failures are eligible control-plane break-glass triggers
FlowPilot SHALL treat package replayability failures as eligible
control-plane break-glass triggers when normal PM/control-blocker routing is
itself unable to produce a legal next action.

#### Scenario: Accepted evidence runner cannot be replayed
- **WHEN** a later review or recovery path proves an accepted evidence runner
  cannot execute because it hard-requires its original packet to be active
- **THEN** Controller may open break-glass under the existing playbook after
  recording the failed normal-lane checks.

#### Scenario: Ordinary quality defect remains outside break-glass
- **WHEN** the reviewed artifact content is poor but the control plane can
  route ordinary PM repair
- **THEN** Controller MUST NOT use break-glass solely to fix the quality defect.
