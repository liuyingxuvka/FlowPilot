## ADDED Requirements

### Requirement: Break-glass can consume repeated no-progress loop evidence
Controller break-glass eligibility SHALL include repeated current-run
control-plane no-progress loops only after normal reissue, repair, wait, or
stop lanes cannot produce a legal next action.

#### Scenario: Repeated control-plane loop can open break-glass
- **WHEN** current-run metadata proves the same nonterminal action repeated
  above the configured threshold with no new event and no legal normal repair
  lane can produce a changed action or corrected payload
- **THEN** Controller MAY open a break-glass incident with the repeated-action
  evidence and failed normal-lane checks
- **AND** the incident MUST remain forbidden from approving target-project work,
  route mutation, gate approval, publication, deployment, or secrets handling.

#### Scenario: Normal repair lane prevents break-glass
- **WHEN** the repeated no-progress loop has an available current-contract
  repair, reissue, user-required wait, or stop path
- **THEN** Controller MUST use that normal lane and MUST NOT open break-glass.
