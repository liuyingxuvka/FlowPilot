# flowguard-thin-parent-models Specification

## Purpose
TBD - created by archiving change thin-heavy-flowguard-parent-models. Update Purpose after archive.
## Requirements
### Requirement: Default parent checks use thin evidence aggregation
The system SHALL make routine Meta and Capability parent validation execute a
thin evidence aggregation path that reads child result/proof metadata,
partition ownership, skipped-check status, and parent-only obligations instead
of expanding the full legacy parent state graph.

#### Scenario: Routine Meta parent check runs
- **WHEN** the Meta parent runner is invoked without an explicit full-regression
  request
- **THEN** the runner MUST complete by checking thin parent evidence and MUST
  report that the result is not a full legacy graph regression

#### Scenario: Routine Capability parent check runs
- **WHEN** the Capability parent runner is invoked without an explicit
  full-regression request
- **THEN** the runner MUST complete by checking thin parent evidence and MUST
  report that the result is not a full legacy graph regression

### Requirement: Full legacy parent regressions remain available
The system SHALL preserve the full Meta and Capability graph exploration paths
behind explicit forced/full execution modes and background regression
workflows.

#### Scenario: Full Meta regression requested
- **WHEN** a caller explicitly requests full Meta regression
- **THEN** the system MUST run or schedule the legacy Meta graph exploration
  rather than treating thin evidence as a full regression pass

#### Scenario: Full Capability regression requested
- **WHEN** a caller explicitly requests full Capability regression
- **THEN** the system MUST run or schedule the legacy Capability graph
  exploration rather than treating thin evidence as a full regression pass

### Requirement: Parent responsibility ledger is machine-readable
The system SHALL maintain a machine-readable ledger that maps every effective
Meta and Capability parent partition and invariant family to a child model,
shared kernel, parent-only thin check, legacy-full-only obligation, or explicit
out-of-scope reason.

#### Scenario: Parent partition has no owner
- **WHEN** thin parent validation sees a partition or invariant family without
  an owner and without an out-of-scope reason
- **THEN** the thin parent check MUST fail with an uncovered-parent-partition
  finding

#### Scenario: Legacy-only family remains
- **WHEN** a parent invariant family cannot yet be represented by child or thin
  parent evidence
- **THEN** the ledger MUST mark that family as legacy-full-only and the thin
  parent result MUST preserve a full-regression obligation

### Requirement: Child evidence contracts are freshness checked
The system SHALL treat child model results as evidence contracts and MUST check
source freshness, result freshness, proof validity when available, skipped
required checks, and declared coverage before counting child evidence toward a
parent pass.

#### Scenario: Child evidence is stale
- **WHEN** a child result or proof fingerprint does not match its declared
  source inputs
- **THEN** the thin parent check MUST reject that child evidence and keep the
  parent from reporting green routine validation

#### Scenario: Child hides skipped required checks
- **WHEN** a child result hides skipped required checks or omits skipped-check
  visibility
- **THEN** the thin parent check MUST fail instead of counting that child as
  current evidence

### Requirement: Thin parent release confidence is bounded
The system SHALL distinguish routine thin-parent confidence from release-level
confidence that requires current full legacy regression evidence or an explicit
approved equivalence gate.

#### Scenario: Thin checks pass without full evidence
- **WHEN** thin Meta and Capability checks pass but full legacy parent
  regressions are missing, stale, incomplete, or only showing progress
- **THEN** the system MUST report routine confidence only and MUST preserve the
  full-regression obligation for release confidence

#### Scenario: Full evidence is current
- **WHEN** thin checks pass and current full legacy regression proof or
  completed background artifacts are available
- **THEN** the system MAY report release-level parent confidence with the full
  evidence paths cited

### Requirement: Thin parent splitting is recursive
The system SHALL treat thin parent aggregation as a recursive hierarchy rather
than a fixed two-layer structure, and SHALL require any child evidence model
that exceeds the heavyweight threshold to be split into a domain parent with
bounded child evidence before it is used for routine foreground validation.

#### Scenario: Child model grows too large
- **WHEN** a child or shared-kernel evidence model crosses the heavyweight
  state-count threshold
- **THEN** the hierarchy MUST keep routine foreground validation bounded by
  replacing that oversized child contract with a smaller domain-parent ledger
  and child evidence set, or by marking the area as full-regression-only until
  the split exists

### Requirement: Equivalence hazards guard the migration
The system SHALL include executable hazards that compare thin-parent decisions
against known legacy parent expectations for representative safe paths and
known-bad paths.

#### Scenario: Thin parent passes known bad evidence
- **WHEN** a known-bad case such as missing child evidence, stale proof, hidden
  skipped checks, sibling ownership overlap, or uncovered partition is injected
- **THEN** the thin parent hazard check MUST reject it

#### Scenario: Thin parent blocks known safe evidence
- **WHEN** all required child, shared-kernel, and parent-only evidence is
  current and no full-regression-only release claim is made
- **THEN** the thin parent hazard check MUST accept routine validation
