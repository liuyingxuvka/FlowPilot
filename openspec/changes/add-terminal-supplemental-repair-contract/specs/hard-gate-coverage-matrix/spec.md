## ADDED Requirements

### Requirement: Hard Gate Matrix Covers Supplemental Repair Obligations
FlowPilot hard-gate coverage SHALL include terminal supplemental repair contract
creation, repair item projection, FlowGuard process coverage, Reviewer repair
plan review, terminal replay coverage, and the three-round hard cap.

#### Scenario: Coverage matrix misses repair cap
- **WHEN** hard-gate coverage is generated for terminal closure
- **AND** it lacks a row proving the three-round supplemental repair cap
- **THEN** broad closure confidence MUST remain unsupported.

#### Scenario: Coverage matrix misses repair item projection
- **WHEN** a supplemental repair contract has active repair items
- **AND** hard-gate coverage lacks projection rows for those items
- **THEN** broad closure confidence MUST remain unsupported.
