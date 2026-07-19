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

#### Scenario: A child publishes terminal artifacts
- **WHEN** a background child reaches a terminal result
- **THEN** it MUST atomically publish final metadata before atomically
  publishing the exit artifact
- **AND** the supervisor MUST treat exit as the last terminal marker so it
  cannot observe exit with stale running metadata

#### Scenario: Background owner times out or is interrupted
- **WHEN** a supervisor times out, is cancelled, is interrupted, or reports a
  non-terminal cleanup state
- **THEN** its evidence MUST remain failed or `cleanup-unconfirmed` until the
  full descendant process tree count is proven zero
- **AND** a new execution owner MUST NOT start from the same mutable evidence
  boundary before cleanup is confirmed

### Requirement: Final validation follows one canonical impact plan
FlowPilot SHALL canonicalize controlled text, freeze one source snapshot and
one MTA/TestMesh-derived impact plan, and SHALL validate in dependency order
without mixing unqualified evidence or rerunning receipt consumers as
execution owners.

#### Scenario: Final evidence plan is produced
- **WHEN** source, toolchain, test inventory, dependencies, environment, and
  verification ownership are frozen
- **THEN** every required owner MUST receive exactly one `reuse`, `execute`, or
  `blocked` decision
- **AND** `reuse` MUST require a current terminal proof plus a current
  `TestResultReuseTicket`
- **AND** `blocked` MUST stop invalid descendants instead of expanding to
  `run all`

#### Scenario: Selected and reused evidence is composed
- **WHEN** all `execute` owners have terminal current artifacts and all `reuse`
  owners have valid current tickets
- **THEN** the final manifest MUST bind every owner proof and the canonical
  snapshot identity
- **AND** ContractExhaustion, current Cartesian, MTA, acceptance TestMesh,
  ModelMesh, `final-confidence`, Meta, Capability, topology, installation,
  public-boundary, and OpenSpec checks MUST follow only their declared
  dependencies

#### Scenario: A governed input changes during final validation
- **WHEN** any covered input changes after the impact plan is frozen
- **THEN** the plan and every affected owner or dependent receipt MUST become
  stale
- **AND** validation MUST resolve a new plan and execute only newly affected
  owners while retaining qualified unaffected proof

#### Scenario: A parent release gate is mandatory
- **WHEN** child owner evidence changes but the parent gate's own implementation
  and environment remain current
- **THEN** the parent MUST be re-evaluated as a receipt consumer
- **AND** it MUST NOT relaunch Meta, Capability, `all`, adversarial, release, or
  another heavyweight child unless the frozen impact plan explicitly selects
  that owner

### Requirement: Test budgets are measured and enforced without dropping coverage
The validation mesh SHALL benchmark and enforce PR, nightly, and release time
budgets through deterministic sharding, bounded workers, compact results, and
freshness-aware reruns.

#### Scenario: A tier exceeds its budget
- **WHEN** measured duration exceeds the tier's approved budget
- **THEN** TestMesh MUST repartition, batch, or optimize equivalent execution
- **AND** it MUST not silently remove required case, shard, or receipt coverage
