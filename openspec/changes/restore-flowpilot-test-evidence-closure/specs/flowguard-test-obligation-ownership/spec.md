## ADDED Requirements

### Requirement: TestMesh child evidence is execution-backed
TestMesh MUST register every required Cartesian, fake-AI, validator,
historical, fuzz, and public-pipeline shard as a child suite with a real
command, final result path, exit status, selected/executed counts, freshness
fingerprint, and proof artifact.

#### Scenario: Runner hard-codes passed or current
- **WHEN** a child suite has no completed current command/result evidence
- **THEN** TestMesh MUST report missing, running, stale, or failed evidence
- **AND** the runner MUST NOT synthesize `passed`, `current`, or `test_count`
  from owned model cells

#### Scenario: A prior result is reused
- **WHEN** a child suite reuses an earlier passing result
- **THEN** it MUST provide a current `TestResultReuseTicket` and
  `ProofArtifactRef` covering command, source, tests, runtime, environment,
  result, and coverage scope

### Requirement: Parent TestMesh consumes every required execution shard
Release and full-confidence parent gates SHALL consume current passing evidence
for every required execution shard and keep skipped/release-only gaps visible.

#### Scenario: A required shard is stale or progress-only
- **WHEN** a child shard changed or has only background progress output
- **THEN** routine/release parent confidence MUST be scoped or blocked according
  to the shard's required scope

### Requirement: Heavy execution receipts require descendant-zero cleanup
Every heavyweight execution owner SHALL bind its launcher and descendant
process tree identity to the receipt and SHALL prove zero live descendants
after timeout, cancellation, interruption, or supervisor failure before the
receipt can be reused or another owner can start the same check.

#### Scenario: Supervisor exits while a child remains
- **WHEN** the parent process has exited but one or more descendant processes
  are still alive or cannot be enumerated
- **THEN** TestMesh MUST classify the evidence as `cleanup-unconfirmed`
- **AND** the partial result MUST NOT support reuse, pass, release, or another
  execution owner for the same check

#### Scenario: Interrupted execution is cleaned up
- **WHEN** the explicit owner terminates or reconciles the complete descendant
  tree and records a terminal descendant count of zero
- **THEN** TestMesh MAY allow a fresh owner execution
- **AND** no progress, PID, parent-exit, Scheduled Task, unattended retry, or
  background resume record may substitute for the descendant-zero proof

### Requirement: Proof consumers share one frozen source fingerprint
The final evidence mesh SHALL require all background tier supervisors,
children, proof artifacts, compiled manifests, model consumers, final-
confidence checks, and parent checks to bind one frozen covered-source
fingerprint.

#### Scenario: Required tiers have different fingerprints
- **WHEN** `all`, `formal-submit-adversarial`, or `release` starts or finishes
  with a fingerprint different from another required tier or the current
  compiled manifest
- **THEN** the manifest MUST fail compilation or remain non-current
- **AND** no downstream consumer may mix the receipts or select a newer result

#### Scenario: Covered input changes after evidence
- **WHEN** a covered source, toolchain, test inventory, dependency, or
  verification-plan input changes after a child receipt is produced
- **THEN** mapped owners and every dependent receipt MUST become stale
- **AND** only current same-fingerprint revalidation may restore their claim
  scope
