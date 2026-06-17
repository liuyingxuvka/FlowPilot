## ADDED Requirements

### Requirement: Stage-Aware Evidence Matrix

FlowPilot SHALL maintain one current-contract stage/evidence matrix for packet
result families that defines the lifecycle stage, current evidence kind,
future-only evidence, premature blockers, target-workspace artifact
requirements, and toolchain evidence owner.

#### Scenario: Preplanning Contract Defines Future Evidence Without Requiring It Now

- **GIVEN** PM submits a `task.high_standard_contract` result with
  `requirements` and `acceptance_item_registry.items`
- **AND** acceptance items include `required_evidence` text for future final
  closure
- **WHEN** Runtime issues the FlowGuard packet for that result
- **THEN** the packet SHALL include a matrix row whose `subject_stage` is
  `preplanning_contract_definition`
- **AND** the FlowGuard operator SHALL judge the requirements and acceptance
  registry as the current evidence
- **AND** missing Worker output, route-node proof, target-product proof, or
  final backward replay evidence SHALL NOT be valid blocker reasons for this
  stage unless the PM result claims that such evidence already exists.

#### Scenario: Node Acceptance Plan Projects Evidence Before Worker Dispatch

- **GIVEN** PM submits a node acceptance plan before Worker dispatch
- **WHEN** Reviewer or FlowGuard checks that plan-stage package
- **THEN** missing Worker result artifacts, post-result checks, and final
  closure proof SHALL be treated as future-stage evidence
- **AND** the plan SHALL still block if it fails to project owner nodes,
  acceptance items, direct-evidence expectations, or validation obligations.

#### Scenario: Result And Terminal Evidence Remain Strict

- **GIVEN** a Worker result, PM disposition, FlowGuard result, Reviewer result,
  or final backward replay package
- **WHEN** the matrix marks the subject as result-stage or terminal-stage
- **THEN** missing direct current evidence, stale evidence, skipped required
  checks, fake package success, or unapproved waiver SHALL remain blocking.

### Requirement: Portable FlowPilot Runtime Self-Check Receipt

Installed FlowPilot SHALL provide a portable runtime self-check receipt that
target projects can record at run startup without depending on the FlowPilot
development repository.

#### Scenario: Target Project Does Not Contain Dev Simulation Scripts

- **GIVEN** FlowPilot is installed as a Codex skill in an arbitrary target
  project
- **AND** the target project does not contain
  `simulations/run_flowpilot_model_test_alignment_checks.py`
- **WHEN** FlowPilot starts a current run
- **THEN** Runtime SHALL record an installed-skill self-check receipt under the
  current run root
- **AND** FlowGuard package examples SHALL refer to that receipt or run-local
  evidence root instead of requiring the target project to contain the dev
  simulation script.

### Requirement: Full Current-Contract Cartesian Matrix

FlowPilot SHALL maintain an executable generated matrix for the bounded
current-contract product of flow stage, packet/material family, action, object
state, AI return profile, timing, blocker/repair state, route shape, execution
source, and final-claim pressure.

#### Scenario: Every Materialized Cell Has A Current Reaction And Absorbing Next Action

- **GIVEN** the generated matrix materializes a current-contract Cartesian cell
- **WHEN** the matrix runner evaluates the cell
- **THEN** the cell SHALL name its expected reaction, evidence owner, coverage
  shard, and absorbing next action
- **AND** reject, block, reissue, stale-evidence, progress-only, route-mutation,
  overclaim, and terminal-gate outcomes SHALL all resolve to a normal next
  action rather than a stuck state.

#### Scenario: GlassBreak Is Not A Passing Current-Contract Path

- **GIVEN** any materialized current-contract Cartesian cell
- **WHEN** the cell is evaluated
- **THEN** the expected reaction SHALL NOT be GlassBreak
- **AND** repeated same-root blockers SHALL be absorbed by a structured repair
  delta requirement, current-packet reissue, PM disposition, or route redesign.

#### Scenario: Existing Test Reuse Requires Currentness Audit

- **GIVEN** a generated Cartesian cell overlaps an existing test
- **WHEN** the matrix runner counts the existing test as reused coverage
- **THEN** the runner SHALL verify that the existing test file, test name, and
  required current-contract markers are present
- **AND** the runner SHALL reject reused tests that still contain explicit
  legacy-positive markers such as legacy alias acceptance, fallback prose
  acceptance, old protocol acceptance, old-router fallback acceptance, or
  newest-run fallback acceptance.

#### Scenario: Non-Materialized Product Classes Are Explicit

- **GIVEN** the unrestricted symbolic product includes combinations no current
  owner can produce
- **WHEN** the matrix reports coverage
- **THEN** the matrix SHALL report explicit not-applicable classes instead of
  silently skipping those combinations.
