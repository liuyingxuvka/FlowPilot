## ADDED Requirements

### Requirement: Layered Coverage Accounting Has Parent And Child Proof

FlowPilot SHALL provide a read-only FlowGuard layered boundary proof for the
full coverage inventory boundary.

#### Scenario: current coverage accounting is consumed by the parent

- **WHEN** the current coverage inventory and model-test alignment evidence are
  loaded
- **THEN** the layered proof SHALL assign parent responsibilities to child
  proof contracts
- **AND** each child SHALL have current evidence
- **AND** each child SHALL have a matching parent reattachment proof.

### Requirement: Inventory Gap Classes Have Leaf Matrix Cells

FlowPilot SHALL represent every known inventory gap class as a leaf boundary
matrix cell.

#### Scenario: a known gap class is present or absent

- **WHEN** the layered coverage proof is built
- **THEN** the leaf matrix SHALL contain a cell for that gap class
- **AND** the cell SHALL record the expected closure strategy and current
  presence state.

### Requirement: Unknown Or Overflowing Leaf Evidence Blocks The Proof

FlowPilot SHALL fail the layered accounting proof when evidence escapes the
declared boundary.

#### Scenario: a new gap class appears without strategy ownership

- **WHEN** the inventory reports an unknown gap class
- **THEN** the accounting proof SHALL not be green.

#### Scenario: a leaf cell emits an undeclared output

- **WHEN** a leaf matrix cell observes an output outside its expected outputs
- **THEN** the FlowGuard layered proof SHALL report a leaf overflow finding.

### Requirement: Full Leaf Cartesian Claim Is Stricter Than Accounting

FlowPilot SHALL not claim whole-system full leaf Cartesian proof while scoped
or deferred runtime evidence remains.

#### Scenario: scoped replay or deferred StructureMesh split remains

- **WHEN** scoped replay, skipped evidence, hard runner findings, deferred
  StructureMesh split, or `full_coverage_ok=false` remain
- **THEN** the stricter full leaf Cartesian readiness proof SHALL be blocked
- **AND** the accounting proof MAY remain green only as coverage-accounting
  evidence.
