## ADDED Requirements

### Requirement: Current-run resolution is schema-compatible and explicit
FlowPilot SHALL resolve the current run through one shared resolver that accepts
new and legacy pointer field names while rejecting implicit project-root or
newest-run fallback.

#### Scenario: New current pointer schema is accepted
- **WHEN** `.flowpilot/current.json` contains `run_id` and `run_root`
- **THEN** runtime and audit code MUST resolve that exact run root
- **AND** MUST NOT require `current_run_id` or `current_run_root`.

#### Scenario: Missing pointer does not scan the project root
- **WHEN** the current pointer is missing, unreadable, or lacks a resolvable run
- **THEN** audit code MUST return a structured skipped/error finding
- **AND** MUST NOT scan the repository root or choose a run by directory sort.

### Requirement: Evidence reads are structured audit outcomes
FlowPilot audit helpers SHALL convert missing files, invalid JSON, and invalid
UTF-8 into structured read outcomes instead of uncaught exceptions.

#### Scenario: Invalid UTF-8 JSON is a finding
- **WHEN** an audit reads a `.json` file that is not valid UTF-8
- **THEN** the audit MUST record an unreadable-evidence finding
- **AND** the audit process MUST continue or fail cleanly without a traceback.

### Requirement: Role packets share one symmetric control-surface contract
FlowPilot SHALL validate packet and result authority through a role-neutral
contract that applies to PM, reviewer, FlowGuard operator, validator, closure,
and worker packets.

#### Scenario: PM-only contract coverage is insufficient
- **WHEN** PM packets carry full envelope/output authority but reviewer or
  FlowGuard packets lack equivalent fields
- **THEN** the control-surface contract MUST fail.

#### Scenario: ACK, result, and acceptance remain separate
- **WHEN** a role ACKs a packet but has not submitted a valid result
- **THEN** the packet MUST remain incomplete
- **AND** completion or accepted-result authority MUST NOT be inferred from ACK.

#### Scenario: Accepted packet is immutable without repair authority
- **WHEN** a packet already has `accepted_result_id`
- **THEN** the runtime MUST reject reassignment, ACK regression, or a new
  accepted result unless an explicit repair transaction restores authority.

#### Scenario: Old generation result is not current evidence
- **WHEN** a result generation is older than the current source generation
- **THEN** the result MUST be blocked or quarantined
- **AND** it MUST NOT count as current completion evidence.
