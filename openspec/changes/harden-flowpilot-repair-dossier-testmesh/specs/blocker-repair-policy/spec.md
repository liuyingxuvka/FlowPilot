## MODIFIED Requirements

### Requirement: Fixed blocker next actions are enforced
FlowPilot SHALL mechanically enforce the fixed next action for each blocker
class before opening PM repair work or ordinary route repair work.

#### Scenario: Missing required information is reissued with material
- **GIVEN** a blocker class is `missing_required_information`
- **AND** Runtime can authorize the missing information for the same packet
- **WHEN** Runtime handles the blocker
- **THEN** Runtime MUST reissue or repair the same packet with the required
  authorized material
- **AND** Runtime MUST NOT open an ordinary route-repair node for that blocker.

#### Scenario: Missing required information stops when material cannot be authorized
- **GIVEN** a blocker class is `missing_required_information`
- **AND** Runtime cannot authorize the missing information
- **WHEN** Runtime handles the blocker
- **THEN** Runtime MUST open a control-plane blocker or PM stop path
- **AND** Runtime MUST NOT ask PM to write another ordinary repair plan.

#### Scenario: Missing matching FlowGuard report issues matching FlowGuard
- **GIVEN** a blocker class is `missing_matching_flowguard_report`
- **WHEN** Runtime handles the blocker
- **THEN** Runtime MUST issue the matching FlowGuard packet for the current
  subject or block if that subject cannot be identified
- **AND** Runtime MUST NOT treat a PM node-context plan as the missing report.

#### Scenario: Evidence gap requires current evidence subject
- **GIVEN** a blocker class is `evidence_gap`
- **WHEN** Runtime opens repair work
- **THEN** the repair must produce current evidence for the blocked subject
- **AND** PM plan text alone MUST remain insufficient.
