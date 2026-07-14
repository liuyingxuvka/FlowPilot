# shared-skill-maintenance-log Specification

## Purpose
TBD - created by archiving change add-shared-skill-maintenance-log. Update Purpose after archive.
## Requirements
### Requirement: PM records each formal run in the shared skill maintenance log

For each formal FlowPilot run, the project manager SHALL maintain one shared Spark-style skill maintenance log entry during current-run planning. The entry SHALL identify `skill: flowpilot`, the main work summary, workspace root, current `run_id`, and current run folder.

#### Scenario: Existing shared log is used

- **WHEN** PM finds an existing Spark-style shared skill maintenance log during current-run planning
- **THEN** PM appends one concise FlowPilot run entry to that existing log.

#### Scenario: Missing shared log is created in shared format

- **WHEN** PM does not find an existing Spark-style shared skill maintenance log during current-run planning
- **THEN** PM creates `.codex/skill_maintenance_log.jsonl` in the workspace root and appends one concise FlowPilot run entry.

### Requirement: PM reports the maintenance entry without creating a gate

The project manager SHALL cite the shared maintenance log path and entry identifier in the existing PM planning report or workstream contract self-check. The maintenance entry SHALL be bookkeeping only and MUST NOT create a new result field, reviewer gate, FlowGuard gate, route node, or project acceptance condition.

#### Scenario: PM planning reports the maintenance row

- **WHEN** PM records the current run in the shared maintenance log
- **THEN** the PM report MAY cite the log path and entry id through the existing semantic report surface
- **AND** Runtime SHALL NOT require a material-understanding memo or a dedicated maintenance-log packet.

#### Scenario: Bookkeeping does not block project acceptance

- **WHEN** the shared maintenance entry is recorded or reported
- **THEN** FlowPilot treats it as an index for future lookup, not as evidence required to close product, route, review, or terminal acceptance gates.

