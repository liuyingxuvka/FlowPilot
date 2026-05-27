# flowpilot-packet-review-flow Specification

## Purpose
TBD - created by archiving change simplify-flowpilot-packet-review-flow. Update Purpose after archive.
## Requirements
### Requirement: PM-issued packet results return to PM before Reviewer gates
FlowPilot SHALL route results from PM-issued material, research, current-node, and PM role-work packets to the project manager for package-result disposition before any Reviewer gate may inspect or pass the work.

#### Scenario: Worker result returns to PM for disposition
- **WHEN** a Worker or Officer returns a result for a PM-issued packet whose expected recipient is `project_manager`
- **THEN** Router SHALL expose a Controller-visible result relay to PM disposition
- **AND** Router SHALL NOT expose a Reviewer gate for that result before PM records a package-result disposition.

#### Scenario: Raw worker result cannot satisfy Reviewer gate
- **WHEN** a raw Worker result exists without an absorbed PM package-result disposition
- **THEN** Reviewer gate evidence SHALL reject the result as premature
- **AND** PM SHALL NOT complete the node, material gate, or research gate from that raw result alone.

### Requirement: Absorbed PM disposition releases a formal Reviewer package
FlowPilot SHALL treat an absorbed PM package-result disposition as Reviewer release evidence only when it writes a reviewer-readable formal gate package with a path, hash, review scope, and raw-result boundary.

#### Scenario: Absorbed disposition releases package
- **WHEN** PM records package-result disposition `absorbed`
- **AND** the disposition includes `formal_gate_package_released: true`, `formal_gate_package_path`, `formal_gate_package_hash`, and `reviewer_review_scope`
- **THEN** Router and Reviewer gates SHALL treat that disposition as the PM release for Reviewer review.

#### Scenario: Absorbed disposition without package is insufficient
- **WHEN** PM records package-result disposition `absorbed` without a formal gate package path and hash
- **THEN** Reviewer review SHALL remain blocked
- **AND** PM SHALL NOT use the disposition as node, material, or research acceptance evidence.

### Requirement: Reviewer reviews formal packages, not dispatch requests
FlowPilot SHALL keep Reviewer review on PM-built formal gate packages and independent quality/source/fact checks, not pre-dispatch approval of PM-authored worker packets.

#### Scenario: New packet flow skips Reviewer dispatch approval
- **WHEN** PM issues a valid work packet for a Worker or Officer
- **AND** Router direct-dispatch validation and packet-ledger checks pass
- **THEN** Controller may relay the packet envelope to the assigned role without a Reviewer dispatch approval event.

#### Scenario: Reviewer quality gate remains required
- **WHEN** PM has released a formal gate package after absorbed disposition
- **THEN** Reviewer SHALL inspect the formal package and required direct evidence before pass or block
- **AND** PM SHALL NOT advance solely from Router mechanical proof.

### Requirement: Legacy reviewer-dispatch flags cannot satisfy new flow gates
FlowPilot SHALL treat old reviewer-dispatch cards, events, or flags as legacy compatibility evidence only. They MUST NOT satisfy new PM disposition, formal package release, or Reviewer package-review requirements.

#### Scenario: Legacy flag is ignored for current acceptance
- **WHEN** a run contains `reviewer_dispatch_allowed`, `reviewer_dispatch_card_delivered`, or an equivalent legacy reviewer-dispatch flag
- **THEN** Router and PM package gates SHALL NOT count that flag as PM package-result disposition
- **AND** Reviewer gates SHALL still require a formal PM gate package for new-flow acceptance.
