## ADDED Requirements

### Requirement: Inventory all FlowGuard check entrypoints

The repository SHALL provide a full inventory of FlowGuard check entrypoints
under `simulations/` and record each entrypoint's evidence status.

#### Scenario: All runners are listed

- **WHEN** the inventory is generated
- **THEN** every `simulations/run_*checks.py` entrypoint MUST appear in the
  machine-readable result with its script path, runner key, coverage tier, and
  result evidence status.

### Requirement: Separate evidence strength from coverage confidence

The inventory SHALL distinguish source-audited model-test evidence, ordinary
test references, abstract model-only evidence, skipped/release-only evidence,
  stale/progress-only evidence, and missing/unparsed evidence.

#### Scenario: Evidence is not overclaimed

- **WHEN** a model runner passes but has only abstract model evidence or no
  ordinary test reference
- **THEN** the inventory MUST classify that condition as a follow-up coverage
  gap rather than claiming every model boundary is fully tested.

### Requirement: Report prioritized follow-up groups

The inventory SHALL produce a human-readable report that groups follow-up work
by practical next action.

#### Scenario: Follow-up groups are available

- **WHEN** the inventory completes
- **THEN** the report MUST identify prioritized groups such as source-audited
  test gaps, weak ordinary-test references, missing result artifacts,
  skipped/release-only evidence, and structure-only findings.
