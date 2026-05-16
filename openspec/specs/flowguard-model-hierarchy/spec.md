# flowguard-model-hierarchy Specification

## Purpose
TBD - created by archiving change split-heavy-flowguard-model-hierarchy. Update Purpose after archive.
## Requirements
### Requirement: Heavy parent models are explicitly classified
The system SHALL classify FlowPilot FlowGuard models by role, observed size, evidence tier, and whether they require parent/child split review.

#### Scenario: Oversized parent detected
- **WHEN** a model result reports a state count above the configured heavyweight threshold
- **THEN** the hierarchy check MUST classify the model as a heavyweight parent that requires split review or current full-regression evidence

#### Scenario: Focused child retained
- **WHEN** a focused model is below the heavyweight threshold and owns a narrow risk boundary
- **THEN** the hierarchy check MUST classify it as child evidence rather than requiring further split for size alone

### Requirement: Parent partitions have explicit ownership
The system SHALL define a parent partition map for heavyweight FlowPilot parents, assigning each parent-space item to a child model, the parent, a read-only dependency, or a shared kernel.

#### Scenario: Coverage gap blocks hierarchy green
- **WHEN** a parent-space item has no owner and no explicit out-of-scope reason
- **THEN** the hierarchy check MUST reject a green hierarchy decision

#### Scenario: Unsafe sibling overlap blocks hierarchy green
- **WHEN** two sibling child models both own the same state write, side effect, or core functional area without a shared-kernel boundary
- **THEN** the hierarchy check MUST reject a green hierarchy decision

### Requirement: Child evidence freshness is visible
The system SHALL expose each child model's result path, freshness rule, evidence tier, skipped checks, and stale-result status before using child evidence for parent confidence.

#### Scenario: Stale child evidence is used
- **WHEN** a child model result is missing, stale, foreign to the current model source, or hides skipped required checks
- **THEN** the hierarchy check MUST report the child as insufficient evidence and avoid claiming parent coverage

#### Scenario: Current child evidence is usable
- **WHEN** a child model has current abstract, hazard, live, or conformance evidence matching its declared tier
- **THEN** the hierarchy check MAY count that child toward its assigned parent partition coverage

### Requirement: Heavy regressions remain distinct from hierarchy checks
The system SHALL distinguish lightweight hierarchy checks from full heavyweight `meta` and `capability` regressions.

#### Scenario: Hierarchy check passes but parent regression is not current
- **WHEN** the hierarchy check passes and a heavyweight parent does not have a current full-regression result or valid proof
- **THEN** the system MUST report that full heavyweight regression remains required for release-level confidence

#### Scenario: Background heavyweight run is incomplete
- **WHEN** a background meta or capability run has progress output but no final exit artifact and valid result/proof
- **THEN** the system MUST report the run as incomplete rather than passed

### Requirement: Validation surfaces include hierarchy evidence
The system SHALL include the model hierarchy runner in local validation surfaces without forcing foreground rebuild of the two heavyweight parent graphs.

#### Scenario: Install check validates hierarchy artifacts
- **WHEN** `scripts/check_install.py` validates repository readiness
- **THEN** it MUST verify the hierarchy model, runner, result artifact, and documentation or OpenSpec artifacts exist

#### Scenario: Smoke check uses fast hierarchy foreground evidence
- **WHEN** smoke validation runs with fast mode
- **THEN** it MUST run the lightweight hierarchy check in foreground and use proof reuse for slow parent checks when valid

### Requirement: Hierarchy reports thin parent result type
The system SHALL expose whether each Meta and Capability parent result came
from thin evidence aggregation, full legacy graph exploration, proof reuse, or
an incomplete background run.

#### Scenario: Thin parent result is current
- **WHEN** hierarchy inventory reads a current thin parent result
- **THEN** it MUST report the parent result type as thin and MUST NOT classify
  that result as a full legacy regression

#### Scenario: Full parent result is current
- **WHEN** hierarchy inventory reads a current full legacy parent result or
  valid full proof
- **THEN** it MUST report the full evidence path separately from the thin parent
  result

### Requirement: Hierarchy preserves full-regression obligations
The system SHALL preserve heavyweight parent full-regression obligations when
thin evidence is current but full Meta or Capability regression evidence is not
current.

#### Scenario: Thin evidence passes without full proof
- **WHEN** thin hierarchy evidence passes and full Meta or Capability proof is
  stale, missing, or incomplete
- **THEN** hierarchy inventory MUST report the parent as routine-current and
  release-confidence-incomplete

#### Scenario: Background run is still active
- **WHEN** a background Meta or Capability run has progress output but no final
  exit artifact and valid result or proof
- **THEN** hierarchy inventory MUST treat the background run as incomplete
  rather than release-current

### Requirement: Foreground validation uses hierarchy and thin parents
The system SHALL route fast install, smoke, and coverage-sweep validation
through hierarchy and thin parent checks while keeping full parent regressions
available as background or forced validation.

#### Scenario: Fast smoke validation runs
- **WHEN** smoke validation runs in fast mode
- **THEN** it MUST run thin parent and hierarchy checks in foreground and MUST
  only reuse or defer full parent regressions with visible proof or background
  obligations

#### Scenario: Install readiness is checked
- **WHEN** install readiness validation runs
- **THEN** it MUST verify thin parent artifacts, hierarchy artifacts, and any
  full-regression obligations without requiring foreground full Meta or
  Capability graph exploration
