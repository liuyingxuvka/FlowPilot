## ADDED Requirements

### Requirement: Singleton live evidence completeness is all-or-evidence-insufficient
FlowPilot SHALL treat the singleton live-authority audit as full only when every
required current-run live evidence file is present, parseable, current, and
owned by the active run. Missing or invalid evidence for any required surface
SHALL remain `evidence_insufficient` and SHALL NOT be promoted to `safe`.

#### Scenario: All live evidence files are complete
- **WHEN** the current run has valid `route_state_snapshot.json`,
  `runtime/router_daemon.lock`, `packet_ledger.json`,
  `execution_frontier.json`, and `router_state.json` evidence
- **THEN** the live singleton audit MAY report full closure if no duplicate
  authority risk is detected.

#### Scenario: Any live evidence file is missing
- **WHEN** one or more required singleton live evidence files are absent for the
  current run
- **THEN** the corresponding surfaces MUST be classified as
  `evidence_insufficient` and full closure MUST remain false.

#### Scenario: Invalid live evidence is not safe
- **WHEN** a required singleton live evidence file exists but is malformed,
  stale, points to another run, or omits the expected authority owner
- **THEN** the corresponding surface MUST be classified as
  `evidence_insufficient` or risk, never safe-by-existence.
