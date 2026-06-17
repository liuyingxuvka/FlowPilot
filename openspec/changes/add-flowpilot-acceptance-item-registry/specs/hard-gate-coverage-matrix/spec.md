## ADDED Requirements

### Requirement: Hard-Gate Matrix Covers Acceptance Item Registry Gaps
The hard-gate coverage matrix SHALL include executable negative coverage for
missing acceptance item registry, orphan acceptance item, missing node
projection, low-quality item closure, route-mutation item loss, and terminal
replay item omission.

#### Scenario: Missing item projection lacks test coverage
- **WHEN** the hard-gate matrix is generated after this change
- **AND** no executable test covers a node acceptance plan missing active item
  projection being rejected
- **THEN** the matrix MUST report missing hard-gate coverage.

#### Scenario: Low-quality item closure lacks test coverage
- **WHEN** the hard-gate matrix is generated after this change
- **AND** no executable test covers existence-only evidence failing to close an
  active acceptance item
- **THEN** the matrix MUST report missing hard-gate coverage.
