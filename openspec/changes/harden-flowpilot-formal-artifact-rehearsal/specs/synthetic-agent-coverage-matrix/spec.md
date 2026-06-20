## ADDED Requirements

### Requirement: Synthetic matrix covers formal artifact lifecycle faults
FlowPilot SHALL treat every runtime-required formal artifact as a finite
synthetic-agent material axis whenever the packet family can require both a
result body and a packet-owned artifact.

#### Scenario: Missing formal artifact is a generated negative cell
- **WHEN** the synthetic coverage matrix is generated for a packet family with
  `evidence_output_policy.required_for_formal_run=true`
- **THEN** the matrix MUST include a fake-AI cell where the result body is valid
  and the formal artifact file is missing
- **AND** the oracle MUST expect a current-contract mechanical reissue that
  names the missing artifact.

#### Scenario: Formal artifact internal field faults are generated cells
- **WHEN** a runtime-required formal artifact has required internal decision or
  report fields
- **THEN** the matrix MUST include malformed JSON, missing child field, wrong
  enum value, wrong path/currentness, and body/artifact decision-conflict cells
- **AND** each cell MUST declare the expected runtime oracle reaction.

#### Scenario: Helper-written artifacts do not hide fake-AI faults
- **WHEN** fake-AI rehearsal executes a formal artifact packet family
- **THEN** the fake responder mode MUST determine whether the artifact is
  omitted, malformed, wrong-path, incomplete, conflicting, or correct
- **AND** helper code MUST NOT silently create a passing artifact unless the
  selected fake responder mode is the compliant artifact mode.

### Requirement: Synthetic matrix checks reissue feedback clarity
FlowPilot SHALL verify that reissue packets for formal artifact failures give
the role enough executable information to repair the artifact, not only the
result body.

#### Scenario: Missing artifact feedback is executable
- **WHEN** runtime rejects a result because a required formal artifact is
  missing
- **THEN** the reissue packet MUST identify the artifact filename, target
  packet-owned path or root, missing field list when known, and that submitting
  only a corrected result body is insufficient.

#### Scenario: Internal artifact field feedback is executable
- **WHEN** runtime rejects a result because the formal artifact exists but
  lacks a required internal field or allowed value
- **THEN** the reissue packet MUST identify the artifact field path, expected
  allowed values or type, and the current packet-owned artifact path.

### Requirement: Synthetic retry cells cover mechanical formal-artifact loops
FlowPilot SHALL include same-family retry cells for formal artifact mechanical
failures in the synthetic matrix.

#### Scenario: Attempts one through four remain normal reissue
- **WHEN** the same formal-artifact mechanical failure repeats for attempts one
  through four in the same current repair lineage
- **THEN** the synthetic oracle MUST expect normal current-contract reissue
- **AND** it MUST NOT expect break-glass before the threshold.

#### Scenario: Fifth same formal-artifact failure reaches break-glass
- **WHEN** the same formal-artifact mechanical failure repeats for the fifth
  attempt in the same current repair lineage
- **THEN** the synthetic oracle MUST expect Controller break-glass diagnosis
  through the existing break-glass lane.
