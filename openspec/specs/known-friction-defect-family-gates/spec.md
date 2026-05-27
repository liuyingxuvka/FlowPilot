# known-friction-defect-family-gates Specification

## Purpose
TBD - created by archiving change promote-known-friction-defect-family-gates. Update Purpose after archive.
## Requirements
### Requirement: Known friction rows promote to defect-family gates
FlowPilot SHALL promote each accepted recurring or high-risk known-friction row
into a FlowGuard defect-family gate before using the row for a full confidence
claim.

#### Scenario: Accepted friction row has a defect-family gate
- **WHEN** a known-friction row is accepted for the parent gate
- **THEN** the row SHALL have a defect-family id, recurrence or high-risk
  metadata, an authority boundary, `defect_family_gate_required=true`, and
  `defect_family_promoted=true`

#### Scenario: Missing family promotion is blocked
- **WHEN** a recurring known-friction row lacks a required defect-family gate
  marker, explicit promotion marker, or recurrence/high-risk metadata
- **THEN** FlowPilot SHALL report a defect-family finding and SHALL NOT treat
  the row as supporting full confidence

### Requirement: Defect-family gates use FlowGuard recurring model-miss evidence
FlowPilot SHALL use FlowGuard's recurring model-miss helper to check known
friction defect-family gates rather than reimplementing the gate locally.

#### Scenario: Promoted dirty family has complete proof
- **WHEN** a known-friction family names a model obligation, authority boundary,
  observed historical failure, same-class generalized case, historical holdout,
  and current external passing proof
- **THEN** `review_defect_family_gates(...)` SHALL return full confidence for
  the bounded family

#### Scenario: Progress-only or stale proof blocks
- **WHEN** the known-friction family proof is progress-only, not passing, or
  stale
- **THEN** FlowPilot SHALL keep the defect-family gate blocked

#### Scenario: Internal-only proof blocks
- **WHEN** the known-friction family proof is passing but only exercises an
  internal path
- **THEN** FlowPilot SHALL reject it for the external authority boundary

### Requirement: Final confidence consumes defect-family gates
FlowPilot SHALL feed known-friction defect-family gate decisions into the Risk
Evidence Ledger before reporting full confidence.

#### Scenario: Family gate is current and external
- **WHEN** every accepted known-friction family gate is current and backed by
  external proof
- **THEN** the Risk Evidence Ledger SHALL allow full confidence for the named
  bounded family claims

#### Scenario: Family gate is blocked or scoped
- **WHEN** any known-friction family gate is blocked or scoped
- **THEN** the Risk Evidence Ledger SHALL block or downgrade the final claim
  instead of silently accepting the row
