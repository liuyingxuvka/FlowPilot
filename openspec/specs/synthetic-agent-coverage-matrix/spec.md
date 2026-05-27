# synthetic-agent-coverage-matrix Specification

## Purpose
TBD - created by archiving change complete-synthetic-agent-coverage-matrix. Update Purpose after archive.
## Requirements
### Requirement: Coverage matrix owns every current testable branch

FlowPilot SHALL maintain a repository-owned synthetic agent coverage matrix for
the currently modeled AI/action branch families. Each currently testable branch
SHALL declare its model family, obligation id, branch kind, primary evidence
owner, evidence command or test id, evidence status, and coverage boundary.

#### Scenario: Every modeled branch has coverage ownership

- **WHEN** the coverage matrix is generated for current FlowPilot model-test
  alignment plans
- **THEN** every current obligation branch that is finite and testable MUST have
  at least one primary evidence owner

#### Scenario: Missing owner fails the coverage gate

- **WHEN** a model obligation branch appears without a primary trace, test,
  model-alignment, or background-artifact evidence owner
- **THEN** the coverage matrix gate MUST fail and identify the missing branch

### Requirement: Synthetic traces remain non-live evidence

Synthetic trace packages SHALL be classified as control-flow or evidence-boundary
regression evidence only. They MUST NOT be classified as live AI semantic
quality, delivered product quality, human approval quality, or live project
completion evidence.

#### Scenario: Synthetic trace passes control-flow gate only

- **WHEN** a synthetic trace replays fake role actions through real FlowPilot
  packet, result, ledger, router, or role-output APIs
- **THEN** the coverage matrix MAY count the row as control-flow evidence and
  MUST keep the live completion boundary unresolved

#### Scenario: Fixture evidence cannot satisfy live completion

- **WHEN** a row is backed only by fixture or synthetic trace evidence
- **THEN** FlowPilot MUST disclose the row as non-live evidence and MUST NOT use
  it to close a live project completion or release claim

### Requirement: Branch families include positive and negative paths

The coverage matrix SHALL include happy, negative, failure, edge, replay, and
background-artifact branch kinds whenever those branches exist in the current
model-test alignment plans or synthetic trace contracts.

#### Scenario: Branch-kind gap is rejected

- **WHEN** an obligation requires multiple branch kinds and one required kind
  has no evidence row
- **THEN** the coverage matrix gate MUST fail with the missing branch kind

#### Scenario: Existing focused runtime test can own a branch

- **WHEN** an ordinary focused runtime test already proves a branch better than
  a synthetic trace
- **THEN** the matrix MUST allow that test to be the primary evidence owner and
  MUST NOT require a duplicate synthetic trace for the same branch

### Requirement: Background evidence requires final artifacts

Coverage rows backed by background checks SHALL require final artifact evidence,
including an exit status and metadata. Progress output alone SHALL NOT count as
passing coverage evidence.

#### Scenario: Progress-only background row fails

- **WHEN** a background check has progress output but no final exit artifact or
  no passing status
- **THEN** the coverage matrix MUST classify that row as incomplete,
  progress-only, running, or failed rather than passed

### Requirement: Full coverage depends on structure diagnostics

FlowPilot SHALL NOT claim full synthetic/model/test coverage while the full
model-test-code diagnostic reports unresolved actionable findings. Structure
split findings MUST be either fixed through compatibility-preserving extraction
or explicitly rejected as blockers.

#### Scenario: Deferred structure split blocks full coverage

- **WHEN** the full diagnostic reports `needs_structure_split` for a runtime
  surface that is not explicitly skipped by policy
- **THEN** the full coverage gate MUST remain failed until the split is
  completed and validated

#### Scenario: Completed split preserves public behavior

- **WHEN** a structure split extracts helper modules from a public runtime
  surface
- **THEN** the original import path MUST remain compatible and focused runtime,
  model-test alignment, and fast-tier validation MUST pass before the row can
  support a full coverage claim
