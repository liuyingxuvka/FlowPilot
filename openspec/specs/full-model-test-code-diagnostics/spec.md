# full-model-test-code-diagnostics Specification

## Purpose
TBD - created by archiving change full-model-test-code-diagnostics. Update Purpose after archive.
## Requirements
### Requirement: Full diagnostic inventory covers repository maintenance surfaces

The system SHALL inventory FlowPilot owner modules, unsupported historical facades,
script entrypoints, and test tiers as first-class diagnostic surfaces.

#### Scenario: Owner modules and facades are inventoried
- **WHEN** the full model-test-code diagnostic runs
- **THEN** it reports owner-module and facade surfaces under
  `skills/flowpilot/assets`
- **AND** each surface includes its path, kind, owner family, and current
  coverage classification.

#### Scenario: Scripts and test tiers are inventoried
- **WHEN** the full model-test-code diagnostic runs
- **THEN** it reports script entrypoints and test-tier surfaces
- **AND** each surface includes its command or symbol boundary and current
  coverage classification.

### Requirement: Diagnostic findings classify model-code-test gaps explicitly

The system SHALL classify uncovered or suspect diagnostic surfaces with explicit
gap codes instead of silently omitting them from alignment evidence.

#### Scenario: Missing model, code, and test gaps are explicit
- **WHEN** a diagnostic surface lacks a required model obligation, code
  contract, or test evidence
- **THEN** the report includes `missing_model`, `missing_code`, or
  `missing_test` for that surface as applicable.

#### Scenario: Extra code and internal-only tests are explicit
- **WHEN** a code surface has no accepted model/test binding or a test only
  asserts internal paths without checking the external contract
- **THEN** the report includes `extra_code` or `internal_only_test` for that
  surface as applicable.

#### Scenario: Structure split candidates are explicit
- **WHEN** a module or script exceeds the accepted diagnostic threshold for a
  single owner surface or mixes unrelated owner families
- **THEN** the report includes `needs_structure_split` with the reason and
  path.

### Requirement: Known-bad diagnostics protect against false confidence

The system SHALL include known-bad sanity cases that fail if the diagnostic
accepts orphan code, wrapper-only evidence, progress-only background evidence,
or broad unsplit modules as fully covered.

#### Scenario: Known-bad hazards are rejected
- **WHEN** the diagnostic known-bad suite runs
- **THEN** it rejects each synthetic false-confidence hazard with the expected
  gap code.

#### Scenario: Progress-only background evidence is not accepted
- **WHEN** a background check has progress output but lacks final exit and meta
  artifacts
- **THEN** the diagnostic reports stale or incomplete evidence instead of
  marking the surface covered.

### Requirement: Diagnostic output is both machine-readable and reviewable

The system SHALL write a machine-readable diagnostic result and a reviewable
summary of current model-code-test gaps.

#### Scenario: JSON contains summary and surface details
- **WHEN** the diagnostic command completes
- **THEN** the JSON output includes overall status, finding counts, surface
  counts by kind, and per-surface gap details.

#### Scenario: Human report lists actionable gaps
- **WHEN** the diagnostic report is reviewed
- **THEN** it lists missing model, missing code, missing test, extra code,
  internal-only test, and structure-split candidates with concrete paths.
