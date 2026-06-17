## ADDED Requirements

### Requirement: Open packet exposes role submission checklist
FlowPilot SHALL include a role-facing submission checklist in successful
`open-packet` output when the opened packet body declares result contract
fields or a minimal valid shape.

#### Scenario: Open packet returns checklist with skeleton
- **WHEN** the addressed role successfully opens a current packet through
  `flowpilot_new.py open-packet`
- **AND** the sealed packet body includes `required_result_body_fields`,
  `conditional_required_fields`, or `minimal_valid_shape`
- **THEN** the open output MUST include a Controller-hidden
  `submission_checklist` derived from those packet-body fields
- **AND** the checklist MUST include the current `result_skeleton` when the
  packet body exposes `minimal_valid_shape`.

#### Scenario: Open packet keeps authorization boundary
- **WHEN** `open-packet` returns the submission checklist and authorized input
  materials
- **THEN** Controller MUST remain unable to read sealed packet bodies or sealed
  authorized input bodies
- **AND** the checklist MUST NOT authorize sibling packets, old-run packets, or
  sealed bodies outside the current role and packet boundary.

### Requirement: Role handoff points to open-packet checklist
FlowPilot SHALL tell the addressed role that the `open-packet`
`submission_checklist` is the mechanical submit checklist for the current
packet.

#### Scenario: Handoff directs role to checklist before submit
- **WHEN** Controller renders role handoff text for an assigned packet
- **THEN** the handoff text MUST tell the addressed role to open the packet and
  use the returned submission checklist or minimal valid shape before
  `submit-result`
- **AND** the handoff text MUST NOT tell Controller to open role-only sealed
  packet or result bodies.

