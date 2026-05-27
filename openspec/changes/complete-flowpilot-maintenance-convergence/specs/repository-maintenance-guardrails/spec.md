## ADDED Requirements

### Requirement: Maintenance convergence preserves validated OpenSpec history

Repository maintenance SHALL archive completed OpenSpec changes only after
strict validation confirms the active backlog is valid, and SHALL preserve each
archived change as tracked reviewable history.

#### Scenario: Valid completed changes are archived

- **GIVEN** OpenSpec strict validation passes for completed active changes
- **WHEN** maintenance archives the completed backlog
- **THEN** each archived change remains under `openspec/changes/archive/`
- **AND** its proposal, design, spec deltas, and task files remain reviewable.

#### Scenario: Archive validation fails

- **GIVEN** OpenSpec validation fails for a change
- **WHEN** maintenance evaluates archive candidates
- **THEN** that change remains active
- **AND** the maintenance report names the failed change and blocker.

### Requirement: FlowGuard hotspot contraction keeps compatibility facades

Repository maintenance SHALL reduce runtime-owner hotspot modules only through
FlowGuard-backed, facade-preserving splits that leave public imports and
observable contracts unchanged.

#### Scenario: Runtime-owner hotspot is split

- **GIVEN** a runtime-owner module is over its StructureMesh threshold
- **AND** focused tests and model-test alignment identify its public contract
- **WHEN** maintenance moves cohesive blocks into child modules
- **THEN** the original module remains importable as a compatibility facade
- **AND** public router exports, runtime data contracts, prompt text, CLI
  behavior, and event or ledger shapes remain unchanged.

#### Scenario: Evidence is insufficient

- **GIVEN** a candidate split lacks a current model/test/code contract
- **WHEN** maintenance evaluates the candidate
- **THEN** the split is deferred and reported as a watchlist item
- **AND** completion is not claimed for that contraction.

### Requirement: Maintenance finalization is local-only and evidence-gated

Repository maintenance SHALL not finalize after source changes until evidence,
local installed skill freshness, and local git state are all synchronized.

#### Scenario: Source changes are finalized locally

- **WHEN** focused checks and background model regressions pass
- **AND** the repo-owned installed FlowPilot skill is synchronized and audited
- **THEN** maintenance may stage and commit the intended local files
- **AND** the final report includes the local commit identifier.

#### Scenario: Public publication remains out of scope

- **WHEN** maintenance creates a local commit
- **THEN** it does not push, tag, deploy, publish a release, or mutate remote
  state unless a separate explicit user approval authorizes that action.
