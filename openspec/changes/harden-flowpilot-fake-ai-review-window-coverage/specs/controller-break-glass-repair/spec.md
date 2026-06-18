## ADDED Requirements

### Requirement: Break-glass threshold is tested through fake-AI repetition
Controller break-glass coverage SHALL include fake-AI generated repeated
same-family failures that prove normal reissue/repair is used before the
threshold and break-glass is triggered at the threshold.

#### Scenario: First four same-family errors stay ordinary
- **WHEN** the fake AI responder repeats the same current-contract failure one to four times
- **THEN** FlowPilot MUST keep the response on ordinary reissue, PM repair, or role repair paths
- **AND** Controller MUST NOT open break-glass solely because the error occurred before threshold.

#### Scenario: Fifth same-family error opens controlled recovery
- **WHEN** the same current-contract failure reaches the configured fifth same-family attempt
- **THEN** FlowPilot MUST open the configured break-glass or recovery escalation
- **AND** the incident MUST name the repeated failure family and the failed normal lanes.

### Requirement: Break-glass body reads are explicitly granted and recorded
Controller sealed-body reads SHALL remain forbidden in ordinary flow and SHALL
be allowed only through explicit break-glass or recovery-supervisor grants.

#### Scenario: Ordinary Controller cannot read sealed bodies
- **WHEN** Controller is outside break-glass or recovery supervisor authority
- **THEN** Controller-visible prompts and state MUST indicate sealed body reads are not allowed.

#### Scenario: Recovery grant records body access
- **WHEN** break-glass or recovery supervisor grants Controller access to relevant sealed bodies
- **THEN** the incident or transaction MUST record the reason, body refs, allowed scope, validation purpose, and exit condition
- **AND** those reads MUST NOT count as gate approval, reviewer approval, PM approval, or route completion evidence.
