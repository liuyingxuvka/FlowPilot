## ADDED Requirements

### Requirement: Facade-preserving structure split
FlowPilot maintenance SHALL preserve existing public commands, importable
facade names, JSON report shapes, and externally visible contracts when an
oversized validation or runtime module is split.

#### Scenario: Validation runner remains callable
- **WHEN** a `simulations/run_*checks.py` entrypoint is split into helper modules
- **THEN** the original runner SHALL still provide the same CLI and public helper functions used by tests and tier commands

#### Scenario: Runtime table parent remains authoritative
- **WHEN** a declarative runtime table is split into child modules
- **THEN** the original parent module SHALL still expose the same public constants and lookup functions

### Requirement: Structure debt remains visible
FlowPilot diagnostics SHALL keep remaining StructureMesh debt visible after a
maintenance split, including any child modules or deferred surfaces that still
need later work.

#### Scenario: Completed split is recorded
- **WHEN** a previously oversized public entrypoint is reduced through a safe split
- **THEN** the diagnostic metadata SHALL classify that public entrypoint as split or below threshold without introducing missing model, code, test, or stale-evidence gaps

#### Scenario: Unsafe split is deferred
- **WHEN** a module is dirty, state-ordering-sensitive, or lacks a dedicated StructureMesh target
- **THEN** the diagnostic SHALL keep it as an explicit deferred StructureMesh item rather than silently treating it as complete

### Requirement: Final validation evidence
FlowPilot maintenance SHALL use final executable validation evidence before
claiming a structure-maintenance pass is complete.

#### Scenario: Background progress is not proof
- **WHEN** a background validation starts but does not produce final exit artifacts
- **THEN** the maintenance pass SHALL not count it as passing proof

#### Scenario: Local install is synchronized
- **WHEN** repository-owned FlowPilot skill files change
- **THEN** the installed local FlowPilot skill SHALL be synchronized and audited before the local commit is treated as complete

## MODIFIED Requirements

### Requirement: FlowPilot diagnostic convergence remains current
The full model-test-code diagnostic SHALL continue to report zero missing model,
missing code, missing test, extra code, internal-only-test, and stale-evidence
gaps for the covered diagnostic surface while allowing explicit deferred
StructureMesh debt to remain visible.

#### Scenario: Structure maintenance refresh
- **WHEN** structure-maintenance code is changed
- **THEN** `simulations/run_flowpilot_model_test_alignment_checks.py --json-out simulations/flowpilot_model_test_alignment_results.json` SHALL refresh the diagnostic result without introducing unresolved non-deferred gaps
