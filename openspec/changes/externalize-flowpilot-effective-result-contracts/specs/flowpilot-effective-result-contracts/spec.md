## ADDED Requirements

### Requirement: Packet Results Use An External Effective Contract

Every FlowPilot packet result SHALL be governed by an external effective
contract generated from the base packet family and explicit packet envelope
profile ids.

#### Scenario: packet has a conditional result requirement

- **GIVEN** runtime issues a packet whose current result requires fields beyond
  the base family shape
- **WHEN** the packet envelope, output contract, current handoff contract, or
  open-packet submission checklist is inspected
- **THEN** the extra required fields, allowed values, type requirements, and
  minimal valid shape are visible there
- **AND** the role does not need to infer mechanical result fields from packet
  body prose.

### Requirement: FlowGuard Semantic Recheck Is Externally Contracted

FlowGuard blocker-bound semantic recheck packets SHALL expose the
`semantic_recheck` result object through the external effective contract.

#### Scenario: blocker-bound FlowGuard packet is opened

- **GIVEN** a FlowGuard packet is bound to an active repair blocker and requires
  subject-bound semantic recheck
- **WHEN** the FlowGuard operator opens the packet
- **THEN** `submission_checklist.result_skeleton` contains a complete
  `semantic_recheck` object
- **AND** `allowed_value_options` constrains the boolean fields to `true`, the
  coverage boundary to `subject_bound_semantic`, and id lists to current
  authorized ids.

### Requirement: Reissue Packets Carry Complete Repair Guidance

Mechanical reissue packets SHALL carry the same effective contract plus
repair-specific guidance sufficient to fix the next submission without field
name guessing.

#### Scenario: semantic recheck is malformed

- **GIVEN** a FlowGuard result uses an unsupported field name or wrong type for a
  `semantic_recheck` field
- **WHEN** runtime rejects and reissues the packet
- **THEN** the fresh packet includes the canonical minimal valid shape,
  field type requirements, allowed values, and the actual invalid submitted
  fields when present
- **AND** unsupported field names remain invalid rather than being translated or
  pre-advertised as examples.

### Requirement: Role-Visible Contract Surfaces Omit Field Lifecycle History

FlowPilot role-visible packet surfaces SHALL expose the current contract only,
while keeping full field-lifecycle history internal to runtime checks, models,
and negative tests.

#### Scenario: FlowGuard or reviewer packet carries subject stage evidence

- **GIVEN** runtime issues a FlowGuard or reviewer packet for a current subject
- **WHEN** the role-visible `subject_stage_evidence_matrix` is inspected
- **THEN** it contains current required fields, allowed value options, allowed
  blocker classes, and repair routing
- **AND** lifecycle-history field lists are not present in the role-visible
  packet body or handoff contract.
