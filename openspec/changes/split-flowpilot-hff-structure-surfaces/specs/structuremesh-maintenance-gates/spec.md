## ADDED Requirements

### Requirement: HFF Split Partitions Have StructureMesh Evidence

StructureMesh maintenance SHALL record parent partitions, child ownership,
entrypoint preservation, side-effect boundaries, and parity evidence for each
HFF split in this batch before broad completion is claimed.

#### Scenario: Batch split evidence is complete

- **WHEN** this HFF batch is validated
- **THEN** the evidence SHALL name the parent entrypoint for each split
- **AND** it SHALL name each child module and owned responsibility
- **AND** it SHALL identify the focused parity evidence for current command or
  import behavior
- **AND** any stale, skipped, or failed evidence SHALL remain visible rather
  than being counted as passed.

#### Scenario: Duplicate ownership blocks split confidence

- **WHEN** two child modules own the same state, side effect, result contract,
  or topology artifact writer without an explicit shared-kernel allowance
- **THEN** the StructureMesh review SHALL block split confidence until one
  owner is selected.
