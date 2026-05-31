## ADDED Requirements

### Requirement: Formal FlowGuard Evidence Uses Run-Local Output Paths

FlowPilot SHALL require FlowGuard evidence produced for a formal runtime work packet to be written under the requesting run's evidence directory unless the task explicitly requests a repository baseline refresh.

#### Scenario: FlowGuard officer receives a formal packet
- **WHEN** the runtime issues a `flowguard_check` packet for a formal run
- **THEN** the packet body MUST identify a run-local evidence root under `.flowpilot/runs/<run-id>/evidence/flowguard/<packet-id>/`
- **AND** it MUST forbid writing formal-run evidence to tracked `simulations/*_results.json` baseline files unless a baseline update is explicitly requested.

#### Scenario: Meta or Capability check runs for formal evidence
- **WHEN** a FlowGuard officer runs `run_meta_checks.py` or `run_capability_checks.py` as formal packet evidence
- **THEN** the command SHOULD use `--json-out` with a run-local output path
- **AND** the runner MUST write its result and proof artifacts to that override path family instead of the tracked default result file.

#### Scenario: Developer intentionally refreshes baselines
- **WHEN** a repository maintainer intentionally runs a runner without `--json-out`
- **THEN** the canonical tracked baseline path MAY be updated as repository-maintenance evidence.
