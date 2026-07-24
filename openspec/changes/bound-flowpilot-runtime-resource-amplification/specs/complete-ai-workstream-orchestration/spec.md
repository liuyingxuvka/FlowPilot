## ADDED Requirements

### Requirement: One obligation-level workstream plan is authoritative
Each substantive role SHALL maintain exactly one
`contract_self_check.workstream_plan_and_completion` table whose rows represent
acceptance obligations or meaningful phases.  Commands, file reads, polls, and
other microsteps SHALL NOT require separate persistent rows, and final
submission SHALL update the existing rows instead of copying a second plan.

#### Scenario: Role executes several commands for one obligation
- **WHEN** a role uses multiple reads, commands, or delegated checks to satisfy one acceptance obligation
- **THEN** the workstream table contains one obligation row with referenced evidence
- **AND** the result does not copy command output or create a second completion plan

#### Scenario: Reviewer evaluates the role plan
- **WHEN** Reviewer audits completion and evidence
- **THEN** Reviewer cites the submitted plan and reports differences, gaps, and judgment
- **AND** Reviewer does not reproduce the complete plan body as a new authority
