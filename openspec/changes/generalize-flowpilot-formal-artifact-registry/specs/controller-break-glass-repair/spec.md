## ADDED Requirements

### Requirement: Registered formal artifact loops use the existing threshold
FlowPilot SHALL route repeated same-family registered formal artifact
mechanical failures through the existing fifth-attempt Controller BreakGlass
threshold.

#### Scenario: Attempts one through four stay repairable
- **WHEN** a registered formal artifact mechanical failure repeats one through
  four times in the same current lineage
- **THEN** FlowPilot MUST keep issuing normal current-contract repair or
  reissue packets.

#### Scenario: Fifth same registered artifact failure reaches BreakGlass
- **WHEN** the same registered formal artifact mechanical failure repeats for
  the fifth time in the same current lineage
- **THEN** FlowPilot MUST route to the existing Controller BreakGlass diagnosis
  path.
