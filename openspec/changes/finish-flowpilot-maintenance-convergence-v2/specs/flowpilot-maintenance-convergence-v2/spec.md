## ADDED Requirements

### Requirement: V2 convergence closes current FlowGuard residual groups

The maintenance pass SHALL close or explicitly scope every current residual
FlowGuard runner group before claiming final convergence.

#### Scenario: Residual groups are classified before repair

- **GIVEN** a fresh coverage sweep and full coverage inventory exist
- **WHEN** maintenance starts implementation
- **THEN** each residual group SHALL be assigned to protocol/source,
  terminal/closure, live runtime, final confidence, model mesh, test mesh, or
  structure mesh ownership
- **AND** the report SHALL name the exact runner, current evidence status, and
  required repair evidence.

#### Scenario: Final convergence requires green inventory

- **GIVEN** all planned repair batches are complete
- **WHEN** final evidence is generated
- **THEN** the full coverage inventory SHALL report `full_coverage_ok: true`
- **AND** release convergence SHALL be green or explicitly blocked by a named
  out-of-scope release-only gate that is not claimed complete.

### Requirement: Protocol and terminal repairs use direct code-boundary evidence

Protocol conformance and terminal monotonicity repairs SHALL be proved with
current model obligations, source owners, and focused code-boundary or ordinary
test evidence.

#### Scenario: Protocol source contract repair is accepted

- **GIVEN** a protocol conformance failure names a source gap
- **WHEN** the source or checker is repaired
- **THEN** the corresponding FlowGuard model check SHALL pass
- **AND** focused tests SHALL observe the externally visible input, output,
  state write, side effect, or error path that the obligation covers.

#### Scenario: Terminal monotonicity repair is accepted

- **GIVEN** terminal state may be reopened, downgraded, or overclaimed by stale
  evidence
- **WHEN** terminal closure is repaired
- **THEN** terminal monotonicity checks SHALL prove completion, blocked, stop,
  ACK, output, cleanup, and historical evidence branches cannot contradict the
  current terminal state.

### Requirement: Live runtime findings are disposed without destructive cleanup

Live runtime findings SHALL be repaired or disposed with explicit current-state
evidence and SHALL NOT be hidden by deleting runtime artifacts.

#### Scenario: Live packet authority is repaired or disposed

- **GIVEN** a live model projection reports unchecked packet authority
- **WHEN** maintenance handles the finding
- **THEN** the current packet authority state SHALL either become valid
- **OR** the run SHALL be explicitly classified as historical/out-of-scope with
  recorded evidence and no final live confidence claim.

#### Scenario: Host automation cleanup is proved

- **GIVEN** terminal continuation cleanup depends on host automation state
- **WHEN** maintenance claims cleanup is complete
- **THEN** durable host automation evidence SHALL be present or the residual
  risk SHALL remain an explicit blocker.

### Requirement: Structure and test compression are behavior-preserving

Code, model, and test compression SHALL be performed only where FlowGuard
evidence proves the target boundary and compatibility facades remain intact.

#### Scenario: Structure hotspot split preserves facade compatibility

- **GIVEN** a module, script, model, or test file is split
- **WHEN** the split is complete
- **THEN** the original public import, command, aggregate suite, or result path
  SHALL remain compatible
- **AND** StructureMesh or TestMesh evidence SHALL identify dependency
  direction, child ownership, parity evidence, and stale evidence gaps.

#### Scenario: Compression is deferred when proof is weak

- **GIVEN** a candidate split lacks a model block, public facade, or external
  contract test
- **WHEN** maintenance evaluates it
- **THEN** that candidate SHALL be deferred with a watchlist entry
- **AND** it SHALL NOT be counted as completed cleanup.

### Requirement: Finalization synchronizes install and local git only after evidence

Finalization SHALL synchronize installed FlowPilot, repository evidence, and
local git only after required validation is current.

#### Scenario: Installed FlowPilot is synchronized

- **GIVEN** source changes affect the repo-owned FlowPilot skill or support
  scripts
- **WHEN** validation passes
- **THEN** `install_flowpilot.py --sync-repo-owned`, install audit,
  install check, and `check_install.py` SHALL pass in sequence.

#### Scenario: Local git finalization is scoped

- **GIVEN** final validation and install sync pass
- **WHEN** the local commit is created
- **THEN** only intended files for the convergence pass SHALL be staged
- **AND** the final report SHALL include the local commit id
- **AND** no push, tag, release, deployment, or remote mutation SHALL occur
  without separate explicit user approval.
