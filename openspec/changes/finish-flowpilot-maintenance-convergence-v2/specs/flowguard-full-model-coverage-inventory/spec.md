## MODIFIED Requirements

### Requirement: Report prioritized follow-up groups

The inventory SHALL produce a human-readable report that groups follow-up work
by practical next action and SHALL treat v2 residual groups as convergence
blockers until each has direct current evidence.

#### Scenario: Follow-up groups are available

- **WHEN** the inventory completes
- **THEN** the report MUST identify prioritized groups such as source-audited
  test gaps, weak ordinary-test references, missing result artifacts,
  skipped/release-only evidence, and structure-only findings.

#### Scenario: V2 residual group remains blocking

- **GIVEN** a runner appears under `runner_not_ok`, live runtime findings,
  source/code findings, or unclassified model tiers
- **WHEN** final maintenance convergence is evaluated
- **THEN** the inventory SHALL keep the group visible as blocking or scoped
- **AND** the final report SHALL NOT claim full convergence from a narrower
  focused check alone.
