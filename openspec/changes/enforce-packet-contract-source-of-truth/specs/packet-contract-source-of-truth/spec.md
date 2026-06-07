## ADDED Requirements

### Requirement: Packet result contracts are the single runtime authority
FlowPilot SHALL maintain one current packet-result contract source of truth for
each supported packet family. Each row MUST name the packet family id, packet
kind, route scope, required top-level result fields, forbidden legacy fields,
runtime validator owner, fake-AI boundary, success unlock, and failure reissue
metadata.

#### Scenario: Runtime blocks undeclared shape drift
- **WHEN** a packet result omits a required field or uses a forbidden old field
- **THEN** runtime records the contract family id, missing required fields,
  forbidden fields seen, and minimal valid shape before reissuing the current
  packet

#### Scenario: Runtime cannot require hidden fields
- **WHEN** a runtime validator requires a result field for a packet family
- **THEN** that field MUST be present in the packet-result contract row and in
  the reissued packet body instructions

### Requirement: Fake AI success rows are contract-blind
FlowPilot fake AI success rows SHALL emit only fields declared by the current
packet-result contract for the packet under test. Hidden fields may appear only
in explicitly named negative overproduction scenarios.

#### Scenario: Fake AI cannot mask runtime mismatch
- **WHEN** a fake AI success body contains a field not declared by the packet
  contract
- **THEN** the fake AI parity check MUST fail before the rehearsal is accepted
  as green evidence

#### Scenario: Negative overproduction remains explicit
- **WHEN** a fake AI scenario intentionally emits undeclared hidden fields
- **THEN** the scenario MUST be labeled negative and runtime MUST reject the
  result without treating it as passing evidence

### Requirement: Packet reissue instructions carry the same contract metadata
FlowPilot SHALL include contract-family metadata in mechanical reissue packet
bodies so the responsible AI can correct the current output without relying on
old fields, hidden runtime knowledge, or prose fallback.

#### Scenario: Reissued packet names concrete repair fields
- **WHEN** runtime reissues a packet after a mechanical contract block
- **THEN** the reissued packet body MUST name required result body fields,
  forbidden fields seen, missing fields, blocked reason, and minimal valid
  shape for the same contract family id

### Requirement: Contract changes refresh model and test evidence
FlowPilot SHALL treat packet contract row changes as model, field lifecycle,
fake AI, runtime, and test evidence invalidations.

#### Scenario: Contract row changes stale parent confidence
- **WHEN** a packet contract row, runtime validator, or fake AI contract term is
  changed
- **THEN** FieldContract, FieldMesh, Model-Test Alignment, relevant fake AI
  tests, topology, and layered parent evidence MUST be refreshed before broad
  confidence is claimed
