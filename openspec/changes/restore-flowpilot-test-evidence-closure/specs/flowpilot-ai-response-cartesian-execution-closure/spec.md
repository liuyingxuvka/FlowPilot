## ADDED Requirements

### Requirement: AI response coverage declares a finite universe
FlowPilot SHALL define every broad AI-response coverage claim through a
FlowGuard `ContractCoverageUniverse` that names its finite dimensions,
interaction groups, exclusions, required receipts, and claim scope.

#### Scenario: Full coverage is reported
- **WHEN** a report uses `full` for AI-response or Cartesian coverage
- **THEN** it MUST identify the exact coverage universe and applicable cells
- **AND** it MUST report excluded, generated, selected, executed, passed,
  failed, stale, and proof-backed counts separately

#### Scenario: An excluded combination is counted
- **WHEN** a generated combination is outside the executable universe
- **THEN** it MUST have a structured exclusion reason, source reference, owner,
  and expiry condition
- **AND** it MUST NOT be counted as executed or passed

### Requirement: AI response cases have executable oracles and unique identity
Every required reject, block, repair, reissue, or allow case SHALL have a
globally unique source-path-preserving id and an executable oracle covering
status, error/feedback, state transition, side effects, and next action.

#### Scenario: Two sanitized source paths collide
- **WHEN** two source contract paths would produce the same shortened id
- **THEN** generation MUST fail until their full paths produce distinct ids
- **AND** neither case may reuse the other case's evidence

#### Scenario: Cases are canonically compressed
- **WHEN** multiple model cells share one expensive runtime representative
- **THEN** the compression MUST prove equal oracle signature, owner, feedback,
  transition, and side-effect contract
- **AND** the representative's receipt MUST list every covered source case id

### Requirement: Tiered execution closes distinct behavior rather than raw product size
FlowPilot SHALL enumerate all declared structural cells, execute all single
mechanical faults, execute a constraint-aware pairwise public-pipeline set,
execute named high-risk interaction groups, and always execute historical
misses and deterministic fuzz cases.

#### Scenario: Model enumeration completes
- **WHEN** every cell in the declared structural universe is classified
- **THEN** the report MAY mark structural enumeration complete
- **AND** it MUST NOT increment public-runtime executed or passed counts for
  cells that were not submitted

#### Scenario: Public pairwise execution is accepted
- **WHEN** the pairwise lane completes
- **THEN** its receipt MUST prove every required value pair is present
- **AND** every selected row MUST traverse dispatch, lease, ACK, open-packet,
  checklist-driven response, and public submit-result

#### Scenario: A historical miss is optimized out
- **WHEN** a covering-array optimization does not select a registered
  historical failure case
- **THEN** the historical case MUST still execute as a pinned regression

### Requirement: Parent confidence consumes proof-backed child receipts
Broad AI-response confidence SHALL require current child execution receipts,
MTA owner bindings, TestMesh evidence, and ModelMesh composite handoff
acceptance.

#### Scenario: Child matrix is locally green
- **WHEN** a child model enumerates all cells but has no current execution
  receipt
- **THEN** parent confidence MUST remain blocked or scoped

#### Scenario: Parent omits a required receipt
- **WHEN** the parent receipt does not consume every required child receipt and
  composite acceptance id
- **THEN** `done`, `release`, `publish`, and `full` claims MUST fail

### Requirement: Authority-convergence hazards remain pinned known-bad cases
The declared finite universe SHALL pin the current-authority, requested-role
resume, compact Reviewer, workstream-semantic, daemon-cleanup, and fingerprint
hazards introduced by this successor until each has an executable oracle and
current owner evidence.

#### Scenario: Resume restores all same-run roles
- **WHEN** a generated or observed resume target includes an idle role, fixed
  role set, prior-run binding, history-derived role, duplicate target, or
  omits a current obligation owner
- **THEN** the oracle MUST reject the target-set equality claim
- **AND** no role-count, liveness, or continuity evidence may convert it to a
  positive resume case

#### Scenario: Reviewer accepts a retired or shallow result
- **WHEN** a positive fixture requires `independent_challenge`, omits the
  existing workstream structure, treats its presence as semantic proof, skips
  required reads, or returns only generic optimization prose
- **THEN** the oracle MUST classify the result as deleted-field or semantic
  review failure as applicable
- **AND** the case MUST NOT support Reviewer or parent pass evidence

#### Scenario: Interrupted or mixed-fingerprint evidence is consumed
- **WHEN** a receipt has live or unconfirmed descendants, lacks terminal
  artifacts, or belongs to a different covered-source fingerprint
- **THEN** the oracle MUST mark the evidence non-current and non-reusable
- **AND** all dependent done, release, publish, and full claims MUST remain
  blocked
