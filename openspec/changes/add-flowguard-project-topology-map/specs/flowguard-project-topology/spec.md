## ADDED Requirements

### Requirement: Generate project topology from current FlowGuard evidence
The repository SHALL provide a command that builds machine-readable and
human-readable FlowGuard project topology artifacts from current repository
models, tests, code surfaces, result artifacts, evidence tiers, and known-bad
signals.

#### Scenario: Topology build writes JSON and Markdown
- **WHEN** the topology build command runs
- **THEN** it MUST write `docs/flowguard_project_topology.json`
- **AND** it MUST write `docs/flowguard_project_topology.md`
- **AND** both artifacts MUST identify the generator version and source files
  consumed.

#### Scenario: Model layer is represented
- **WHEN** the topology JSON is generated
- **THEN** it MUST include every discovered `simulations/run_*checks.py`
  FlowGuard runner with runner key, runner path, model path when available,
  result path when available, coverage tier, area label, and evidence status.

#### Scenario: Test and code layers are represented
- **WHEN** the topology JSON is generated
- **THEN** it MUST include test-tier or ordinary-test evidence rows linked to
  model families when available
- **AND** it MUST include code owner or diagnostic surface rows linked to model
  families or area labels when available.

#### Scenario: Known-bad and evidence boundaries are visible
- **WHEN** result artifacts contain known-bad labels, rejected scenarios,
  hazard checks, stale evidence, skipped checks, progress-only evidence, or
  scoped confidence
- **THEN** the topology MUST expose those signals without marking them as pass
  evidence.

### Requirement: Check topology freshness and completeness
The repository SHALL provide a check command that fails when topology artifacts
are missing, malformed, stale relative to consumed sources, or missing required
model/test/code/evidence layers for a mature FlowGuard project.

#### Scenario: Missing topology fails
- **WHEN** topology check runs and either generated artifact is missing
- **THEN** the command MUST fail with a machine-readable finding naming the
  missing artifact.

#### Scenario: Stale topology fails
- **WHEN** a consumed model, runner, result, test registry, or diagnostic source
  is newer than the generated topology metadata
- **THEN** topology check MUST fail and report the stale source path.

#### Scenario: Required layer missing fails
- **WHEN** topology check runs in this mature FlowGuard project
- **THEN** it MUST fail if the topology lacks a model layer, test layer, code
  layer, evidence layer, or known-bad/risk layer.

### Requirement: Topology is orientation, not validation evidence
Project topology SHALL guide agent understanding and model/test/code discovery,
but SHALL NOT replace executable FlowGuard checks, ordinary tests, conformance
replay, install audit, or release validation.

#### Scenario: Topology cannot prove completion
- **WHEN** an agent claims task completion, install readiness, release
  confidence, or runtime conformance
- **THEN** topology evidence alone MUST be insufficient
- **AND** the claim MUST cite owning checks, tests, result artifacts, or scoped
  evidence according to the existing FlowGuard route.

#### Scenario: Topology can guide model selection
- **WHEN** an agent begins non-trivial work in a mature FlowGuard project
- **THEN** topology MAY guide which model families, tests, code surfaces, and
  known-bad signals to inspect before selecting downstream FlowGuard routes.

### Requirement: Topology maintenance has FlowGuard known-bad coverage
The repository SHALL include a focused FlowGuard model/check that rejects
topology-maintenance false confidence paths.

#### Scenario: Known-bad topology shortcuts are rejected
- **WHEN** the topology maintenance model checks synthetic bad cases
- **THEN** it MUST reject skipped topology intake, stale topology, missing
  model/test/code layers, missing known-bad signals, topology-as-validation
  overclaim, and role-authority misuse.

#### Scenario: Valid topology orientation passes
- **WHEN** the topology maintenance model checks a mature project that has
  current topology, model/test/code/evidence layers, visible known-bad signals,
  and separate validation evidence
- **THEN** it MUST accept the scenario.
