## ADDED Requirements

### Requirement: Contract Projection Covers High-Standard Existing Fields
FlowPilot SHALL maintain fake-AI and contract-exhaustion coverage for every
current packet-result contract field family that is required for high-standard
planning, node context, review, and final acceptance, using existing field
definitions rather than hand-written fallback packages.

#### Scenario: Existing required fields generate Cartesian bad packages
- **WHEN** a packet-result contract declares required fields, non-empty array
  fields, child fields, allowed values, or forbidden aliases
- **THEN** fake-AI contract projection SHALL generate negative coverage for
  missing, empty, wrong-type, invalid-value, forbidden-alias, and representative
  valid package cases.

#### Scenario: Planning and node context fields are covered
- **WHEN** `task.high_standard_contract`, `task.discovery`,
  `task.skill_standard`, `task.planning`, or `task.node_acceptance_plan`
  declares current high-standard or node-context fields
- **THEN** coverage SHALL include those existing fields in focused tests and in
  the contract-exhaustion matrix.

#### Scenario: Semantic low-standard cases remain reviewer evidence
- **WHEN** a fake-AI package is structurally valid but local-only,
  source-intent diluted, or too low-standard for the user/PM contract
- **THEN** coverage SHALL classify runtime acceptance/rejection separately from
  Reviewer or FlowGuard semantic/process blocking evidence.
