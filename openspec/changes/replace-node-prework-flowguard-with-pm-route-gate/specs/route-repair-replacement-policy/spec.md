# route-repair-replacement-policy Delta

## ADDED Requirements

### Requirement: Structural route replacement remains staged until PM absorbs FlowGuard
FlowPilot SHALL not commit structural PM repair or disposition route redesign until the staged decision passes FlowGuard, PM FlowGuard acceptance, Reviewer review, and system validation.

#### Scenario: PM repair redesign waits for absorption
- **WHEN** a PM repair decision chooses `redesign_route`
- **AND** FlowGuard passes the staged route plan
- **THEN** Router SHALL issue PM FlowGuard acceptance before Reviewer review
- **AND** the active route version SHALL remain unchanged until PM acceptance, Reviewer pass, and system validation all complete.

#### Scenario: PM disposition redesign waits for absorption
- **WHEN** a PM node disposition chooses `redesign_route`
- **AND** FlowGuard passes the staged route plan
- **THEN** Router SHALL issue PM FlowGuard acceptance before Reviewer review
- **AND** the old route nodes SHALL not be superseded until the full gate closes.
