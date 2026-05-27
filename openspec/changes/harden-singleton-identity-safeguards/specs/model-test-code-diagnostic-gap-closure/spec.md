## ADDED Requirements

### Requirement: Diagnostics Report Singleton Authority Coverage
FlowPilot model-test-code diagnostics SHALL report singleton authority coverage, stale singleton evidence, and unverified singleton code boundaries.

#### Scenario: Singleton surface has no test evidence
- **WHEN** a singleton authority row names a model obligation and code boundary but no current test or live audit evidence
- **THEN** diagnostics report the row as a coverage gap

#### Scenario: Singleton surface has current evidence
- **WHEN** a singleton authority row has current model, code-boundary, test, and live audit evidence for the bounded scope
- **THEN** diagnostics report the row as covered for that bounded singleton claim
