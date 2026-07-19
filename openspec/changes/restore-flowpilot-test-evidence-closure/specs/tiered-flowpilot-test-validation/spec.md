## ADDED Requirements

### Requirement: Formal AI-response execution is owned by explicit tiers
FlowPilot SHALL register focused formal-submit, adversarial/nightly, release,
and final-confidence commands that directly own the canonical fake-AI,
contract-exhaustion, current-contract, historical, fuzz, and public-pipeline
evidence required by their scope.

#### Scenario: PR validation runs
- **WHEN** the formal-submit fast tier is selected
- **THEN** it MUST run authority/cardinality, all single-fault validator, public
  pairwise, and affected fast shard evidence within the measured PR budget

#### Scenario: Release validation runs
- **WHEN** a publish or tag is requested
- **THEN** current nightly/adversarial, router, integration, Meta/Capability
  full, public release, and final-confidence evidence MUST all be consumed
- **AND** an `all` tier that omits release/final-confidence MUST not be treated
  as release completion

### Requirement: Background evidence requires final artifacts
Every background supervisor and child SHALL write stable stdout, stderr,
combined, exit, and metadata artifacts in an isolated run root.

#### Scenario: Background process is still running
- **WHEN** progress output exists but final exit/result evidence is absent
- **THEN** the child and parent MUST remain running or incomplete
- **AND** the progress MUST NOT satisfy a pass, release, or reuse ticket

#### Scenario: Background owner times out or is interrupted
- **WHEN** a supervisor times out, is cancelled, is interrupted, or reports a
  non-terminal cleanup state
- **THEN** its evidence MUST remain failed or `cleanup-unconfirmed` until the
  full descendant process tree count is proven zero
- **AND** a new execution owner MUST NOT start from the same mutable evidence
  boundary before cleanup is confirmed

### Requirement: Final validation follows one-fingerprint dependency order
FlowPilot SHALL freeze one covered-source fingerprint and SHALL execute final
validation in dependency order without mixing snapshots or rerunning receipt
consumers as execution owners.

#### Scenario: Final evidence snapshot is produced
- **WHEN** source, toolchain, test inventory, dependencies, and verification
  ownership are frozen
- **THEN** isolated `all`, `formal-submit-adversarial`, and `release` owners
  MUST finish with the same start/end fingerprint before the final acceptance
  manifest is compiled
- **AND** every selected child MUST have a terminal exit/result artifact bound
  to that fingerprint

#### Scenario: Evidence manifest consumers run
- **WHEN** the final same-fingerprint manifest is current
- **THEN** ContractExhaustion, current Cartesian, MTA, acceptance TestMesh, and
  ModelMesh MUST consume that exact manifest before `final-confidence`
- **AND** Meta and Capability parents, topology build/check, install
  sync/audit/self-check, public-boundary checks, and OpenSpec strict validation
  MUST follow their declared dependencies

#### Scenario: A governed input changes during final validation
- **WHEN** any covered input changes after a required owner or consumer passes
- **THEN** the affected owner and all dependent receipts MUST become stale
- **AND** validation MUST rerun the minimum mapped owners plus mandatory
  parents without using a newest-result or approximate-fingerprint fallback

### Requirement: Test budgets are measured and enforced without dropping coverage
The validation mesh SHALL benchmark and enforce PR, nightly, and release time
budgets through deterministic sharding, bounded workers, compact results, and
freshness-aware reruns.

#### Scenario: A tier exceeds its budget
- **WHEN** measured duration exceeds the tier's approved budget
- **THEN** TestMesh MUST repartition, batch, or optimize equivalent execution
- **AND** it MUST not silently remove required case, shard, or receipt coverage
