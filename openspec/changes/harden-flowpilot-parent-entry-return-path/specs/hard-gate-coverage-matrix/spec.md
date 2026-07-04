## ADDED Requirements

### Requirement: Parent-entry hard-gate coverage is Cartesian

FlowPilot SHALL maintain executable coverage that combines the finite parent-entry return-path boundary: hard-gate type, affected route topology, detection stage, and expected owner-gate outcome for parent/module entry and hard-gate escape return paths.

#### Scenario: Matrix enumerates valid parent-entry cells

- **WHEN** the hard-gate coverage matrix is generated for this change
- **THEN** it MUST include valid combinations for missing node entry, missing node context, missing parent replay, missing PM disposition, active packet unresolved, and stale current evidence across ancestor parent, descendant child, and mutation-created parent topologies and node-entry, parent-replay, PM-disposition, and final-preflight detection stages.

#### Scenario: Missing matrix cells are visible

- **WHEN** a combination is invalid, not implemented, or intentionally out of scope
- **THEN** the matrix MUST record an explicit scoped-out reason rather than hiding the gap.

### Requirement: Final-dispatch return-path coverage is executable

FlowPilot SHALL include focused runtime and fake-AI tests proving that final-dispatch hard-gate leaks do not reach Reviewer and instead return to the owning normal gate.

#### Scenario: Final dispatch blocks each hard-gate leak class

- **WHEN** a test ledger injects missing node-entry, parent-replay, PM-disposition, stale-evidence, or unresolved-packet evidence covered by the current hard-gate escape boundary
- **THEN** final-dispatch preflight MUST return the expected `control_plane_hard_gate_escape:<gate_type>:<subject_id>` or existing owner repair action
- **AND** no final Reviewer packet is issued.

#### Scenario: Final dispatch permits quality review after clean preflight

- **WHEN** a test ledger has complete current hard-gate evidence for the effective route
- **THEN** final-dispatch preflight MUST allow the existing final quality review path without adding an alternate route.
