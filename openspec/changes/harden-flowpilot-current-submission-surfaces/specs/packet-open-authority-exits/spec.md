## MODIFIED Requirements

### Requirement: Open packet exposes role submission checklist
FlowPilot SHALL include a role-facing submission checklist in successful
`open-packet` output when the opened packet body or current handoff contract
declares result contract fields, branch shapes, material obligations, or a
minimal valid shape.

#### Scenario: Open packet returns checklist with skeleton
- **WHEN** the addressed role successfully opens a current packet through
  `flowpilot_new.py open-packet`
- **AND** the sealed packet body or current handoff contract includes required
  result fields, conditional fields, forbidden fields, branch-valid shapes, or
  a minimal valid shape
- **THEN** the open output MUST include a Controller-hidden
  `submission_checklist` derived from those current packet contract fields
- **AND** the checklist MUST include the current `result_skeleton` and
  `branch_valid_shapes` when the packet contract exposes them.

#### Scenario: Open packet checklist includes required reads
- **WHEN** the current handoff contract declares authorized input materials or
  required authorized result reads
- **THEN** the `submission_checklist` MUST name the required input/result read
  obligations before submit
- **AND** the checklist MUST state whether all required authorized result
  bodies must be opened before submit.

#### Scenario: Open packet keeps authorization boundary
- **WHEN** `open-packet` returns the submission checklist and authorized input
  materials
- **THEN** Controller MUST remain unable to read sealed packet bodies or sealed
  authorized input bodies
- **AND** the checklist MUST NOT authorize sibling packets, old-run packets, or
  sealed bodies outside the current role and packet boundary.

