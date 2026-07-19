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

### Requirement: Proof applicability follows canonical owner inputs
The final evidence mesh SHALL retain one canonical snapshot fingerprint for
provenance and mixed-snapshot protection, while owner covered-input identity
derived from the existing MTA/TestMesh ownership graph SHALL be the sole
authority for child evidence applicability.

#### Scenario: Controlled text differs only by line endings
- **WHEN** a controlled UTF-8 text input differs only by CRLF versus LF
- **THEN** canonical fingerprinting MUST classify the content as equivalent
- **AND** no child owner may become stale solely because of the transport
  representation

#### Scenario: An unrelated mapped input changes
- **WHEN** a governed input changes and the owner graph maps it away from a
  current child proof
- **THEN** that child proof MUST remain eligible for a current
  `TestResultReuseTicket`
- **AND** parent evaluation MUST consume the ticket without launching the
  heavyweight child owner

#### Scenario: A mapped owner input changes
- **WHEN** a source, test, command, dependency, toolchain, environment, or
  verification-plan input mapped to an owner changes
- **THEN** that exact owner and its declared dependent receipts MUST become
  stale
- **AND** unaffected sibling proof MUST remain eligible for qualified reuse

#### Scenario: A declared shared-global input changes
- **WHEN** the owner graph explicitly classifies an input as shared-global
- **THEN** the one declared full owner MUST execute
- **AND** the runtime MUST NOT infer additional full owners from a global
  fingerprint mismatch

#### Scenario: Shared execution-wrapper imports change
- **WHEN** test-tier, impact-planning, or artifact-classification code imported
  by a shared execution wrapper changes while a nested payload's own command,
  wrapper, model/test inputs, environment, obligations, and evidence subjects
  remain unchanged
- **THEN** the exact infrastructure owner MUST become stale
- **AND** Meta, Capability, and other nested payload owners MUST remain eligible
  for qualified reuse rather than inheriting the wrapper's import closure
- **AND** replacing a former over-broad payload identity MAY reuse its proof
  only when the current inputs are a proper exact subset and every removed
  input is an actual wrapper import transferred to the infrastructure owner
- **AND** no legacy identity reader, compatibility branch, or fallback
  applicability path may remain

#### Scenario: A logical MTA row needs a supplemental owner
- **WHEN** the existing owner graph cannot bind one logical evidence row to
  exactly one existing command
- **THEN** it MUST generate one owner from that same graph without a second
  manual owner registry
- **AND** exact function evidence MUST select one collected `test_` function,
  while module, class, or fixture evidence MUST execute its declared command
- **AND** the supplemental owner MUST run after ordinary upstream owners whose
  current result artifacts it may inspect

#### Scenario: An input has no unambiguous owner mapping
- **WHEN** impact resolution finds an unmapped or ambiguously mapped input
- **THEN** the plan MUST block with `impact_mapping_missing`
- **AND** it MUST NOT fall back to `run all`, select a newest receipt, or
  approximate equivalence from command text

#### Scenario: Current executed and reused proof is composed
- **WHEN** every required owner has either a terminal current execution or a
  valid current reuse ticket under the frozen impact plan
- **THEN** the manifest and parent gates MAY compose those owner proofs
- **AND** the canonical snapshot fingerprint MUST record that composition
  without becoming a second applicability authority
