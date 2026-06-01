## ADDED Requirements

### Requirement: Terminal Closure Checks Route Deliverables Directly

FlowPilot SHALL evaluate every effective route node's declared `deliverable_checks` during final route-wide closure and SHALL treat missing or failed deliverables as system-owned terminal blockers.

#### Scenario: Missing route deliverable blocks terminal closure

- **WHEN** an effective accepted route node declares a required `path_exists` deliverable check
- **AND** the referenced path does not exist under the target project root
- **THEN** final closure MUST be blocked with a deliverable-check blocker
- **AND** Reviewer, PM disposition, FlowGuard, and validation evidence MUST NOT override that blocker.

#### Scenario: Passing route deliverable is recorded as covered

- **WHEN** an effective accepted route node declares a required `path_exists` deliverable check
- **AND** the referenced path exists under the target project root
- **THEN** the final route-wide gate ledger MUST record that check as passed
- **AND** the check MUST NOT create a terminal blocker.
