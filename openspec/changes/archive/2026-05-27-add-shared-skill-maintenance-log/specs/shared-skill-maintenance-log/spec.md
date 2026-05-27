## ADDED Requirements

### Requirement: PM records each formal run in the shared skill maintenance log

For each formal FlowPilot run, the project manager SHALL maintain one shared Spark-style skill maintenance log entry during material understanding. The entry SHALL identify `skill: flowpilot`, the main work summary, workspace root, current `run_id`, and current run folder.

#### Scenario: Existing shared log is used

- **WHEN** PM finds an existing Spark-style shared skill maintenance log during material understanding
- **THEN** PM appends one concise FlowPilot run entry to that existing log

#### Scenario: Missing shared log is created in shared format

- **WHEN** PM does not find an existing Spark-style shared skill maintenance log during material understanding
- **THEN** PM creates `.codex/skill_maintenance_log.jsonl` in the workspace root and appends one concise FlowPilot run entry

### Requirement: PM reports the maintenance entry without creating a gate

The project manager SHALL include the shared maintenance log path and entry identifier in the material-understanding output. The maintenance entry SHALL be bookkeeping only and MUST NOT create a reviewer gate, FlowGuard gate, route node, or project acceptance condition.

#### Scenario: Material understanding preserves the maintenance report

- **WHEN** PM submits material understanding with `shared_skill_maintenance_record`
- **THEN** FlowPilot preserves that object in `.flowpilot/runs/<run-id>/pm_material_understanding.json`

#### Scenario: Bookkeeping does not block project acceptance

- **WHEN** the shared maintenance entry is recorded or reported
- **THEN** FlowPilot treats it as an index for future lookup, not as evidence required to close product, route, review, or terminal acceptance gates
