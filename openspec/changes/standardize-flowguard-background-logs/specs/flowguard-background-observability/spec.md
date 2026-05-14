## ADDED Requirements

### Requirement: FlowPilot declares a stable background log root
FlowPilot repository guidance SHALL declare `tmp/flowguard_background/` as the default evidence root for long-running FlowGuard project checks.

#### Scenario: Agent runs a long project check
- **WHEN** an agent runs a FlowPilot FlowGuard check in the background
- **THEN** the agent writes or reports artifacts under `tmp/flowguard_background/` unless a stricter task-specific path is explicitly declared

### Requirement: FlowPilot reports long-check evidence
FlowPilot repository guidance SHALL require final reports to cite stdout, stderr, combined output, exit status, metadata, timestamp, and proof-reuse status for long project checks.

#### Scenario: Agent summarizes verification
- **WHEN** an agent summarizes `run_meta_checks.py` or `run_capability_checks.py`
- **THEN** the summary includes the relevant log paths, exit code, last update time, and whether a valid proof was reused

### Requirement: Legacy project runners emit stderr progress
The `run_meta_checks.py` and `run_capability_checks.py` runners SHALL emit bounded progress to stderr while building reachable graphs, without changing stdout final reports.

#### Scenario: Full graph build runs
- **WHEN** a legacy runner builds its reachable graph
- **THEN** stderr contains start, progress, and complete messages while stdout retains the final report sections

### Requirement: Progress output is configurable
Legacy project runner progress SHALL be disabled when `FLOWGUARD_PROGRESS=0`.

#### Scenario: Strict environment disables progress
- **WHEN** `FLOWGUARD_PROGRESS=0` is set
- **THEN** the legacy runner suppresses progress messages while preserving check behavior
