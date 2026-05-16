## ADDED Requirements

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
