# hard-gate-coverage-matrix Specification

## Purpose
TBD - created by archiving change add-hard-gate-red-team-pack. Update Purpose after archive.
## Requirements
### Requirement: Hard-gate coverage matrix records boundary evidence
The system SHALL maintain a hard-gate coverage matrix that maps each red-team package to a runtime entrypoint, bad package class, expected outcome, protected state invariant, and executable test evidence.

#### Scenario: Matrix row is complete
- **WHEN** a hard-gate row is added
- **THEN** it MUST name `entrypoint`, `bad_package_class`, `expected_outcome`, `protected_state_invariant`, `recovery_route`, and `evidence_test`.

#### Scenario: Matrix rejects missing evidence
- **WHEN** a hard-gate row omits executable test evidence or protected-state invariant
- **THEN** the matrix validation MUST fail.

#### Scenario: Matrix distinguishes progress from proof
- **WHEN** a row concerns background model evidence
- **THEN** the expected outcome MUST require final artifact completion evidence and MUST NOT treat progress-only metadata as a pass.

### Requirement: Hard-gate coverage matrix exposes scoped confidence
The hard-gate coverage matrix SHALL report the covered entrypoints, remaining gaps, and known-bad cases so final confidence claims remain scoped to tested cells.

#### Scenario: Covered entrypoint summary
- **WHEN** the matrix is generated
- **THEN** it MUST report row count, covered entrypoints, bad package classes, and any missing or invalid rows.

#### Scenario: Known-bad cases fail
- **WHEN** known-bad rows omit state invariants, recovery routes, or evidence tests
- **THEN** matrix validation MUST report those failures.
