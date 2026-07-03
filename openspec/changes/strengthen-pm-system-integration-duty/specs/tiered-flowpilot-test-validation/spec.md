## ADDED Requirements

### Requirement: Integration-duty validation has focused and broad tiers
FlowPilot SHALL validate the integration-duty change with focused tests before broad regressions.

#### Scenario: Focused tests cover changed prompt and template surfaces
- **WHEN** role cards, phase cards, reviewer cards, FlowGuard cards, or templates change
- **THEN** focused tests SHALL assert the required integration-duty phrases, template keys, and fixed `node_context_package` boundary.

#### Scenario: Focused tests cover model hazards
- **WHEN** planning-quality or coverage models change
- **THEN** focused tests SHALL assert that all declared hard integration hazards are detected and soft advisory hazards are not promoted to blockers.

#### Scenario: Broad regressions run after focused tests
- **WHEN** focused tests pass
- **THEN** meta, capability, install, topology, and relevant FlowPilot regression commands SHALL be run or recorded as background jobs with final artifacts before completion is claimed.

### Requirement: Background model regressions require final artifacts
FlowPilot SHALL not treat background progress output as completion evidence.

#### Scenario: Background command is still running
- **WHEN** a background model regression has stdout or progress but no exit artifact
- **THEN** the validation report SHALL treat it as liveness only, not pass evidence.

#### Scenario: Background command completed
- **WHEN** a background model regression is cited as validation evidence
- **THEN** the report SHALL include log root, stdout path, stderr path, combined path, exit path, metadata path, exit code, completion status, and proof-reuse status when available.
