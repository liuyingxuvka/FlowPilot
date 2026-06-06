## ADDED Requirements

### Requirement: Current Deferred Split Batch Is Closed By Evidence

The FlowPilot structure-debt convergence pass SHALL treat the current HFF batch
as complete only when all four named deferred StructureMesh findings are split
below their diagnostic thresholds and covered by current validation evidence.

#### Scenario: Four current split findings are closed

- **WHEN** the model-test alignment diagnostics are regenerated after this pass
- **THEN** `simulations/run_flowpilot_core_runtime_checks.py` SHALL no longer
  appear as a `needs_structure_split` finding
- **AND** `simulations/run_flowpilot_information_flow_alignment_checks.py`
  SHALL no longer appear as a `needs_structure_split` finding
- **AND** `skills/flowpilot/assets/flowpilot_new.py` SHALL no longer appear as
  a `needs_structure_split` finding
- **AND** `scripts/flowguard_project_topology.py` SHALL no longer appear as a
  `needs_structure_split` finding.

#### Scenario: Public parents remain current-path entrypoints

- **WHEN** each parent file is split
- **THEN** the original command or module path SHALL remain available for the
  current supported invocation
- **AND** the parent SHALL NOT add legacy aliases, old JSON-field acceptance,
  old-router fallback, newest-run fallback, repo-root fallback, missing-field
  defaults, or prose/shape guessing.

### Requirement: Split Children Carry Focused Evidence

Each child module introduced for the HFF batch SHALL have focused evidence that
the parent command behavior and the moved child ownership still agree.

#### Scenario: Focused checks cover moved ownership

- **WHEN** a validation runner, runtime entrypoint, or topology script moves
  ownership into a child module
- **THEN** focused tests or executable runner checks SHALL cover the moved
  ownership
- **AND** broad inventory evidence SHALL not classify the child as an orphan
  internal-only surface.
