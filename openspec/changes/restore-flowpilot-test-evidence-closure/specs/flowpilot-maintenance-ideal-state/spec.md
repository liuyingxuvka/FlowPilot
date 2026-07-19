## ADDED Requirements

### Requirement: Candidate closure uses current source, model, test, and install evidence
FlowPilot maintenance SHALL not claim a verified local candidate until the
final source tree, OpenSpec change, FlowGuard project record/topology, required
test tiers, installed skill, and version metadata are mutually current and
consistent.  One exact task-owned local commit SHALL be part of the candidate.
For the current authorized publication, the task branch, origin default branch,
annotated version tag, repository version files, release notes, and source-only
GitHub Release SHALL all identify that same commit and version.

#### Scenario: Installed skill is present but stale
- **WHEN** the installed FlowPilot skill exists but its repository-owned digest
  differs from the final verified source
- **THEN** release MUST block until sync, install audit, install check, and
  installed runtime self-check pass serially

#### Scenario: Source changes after background regression
- **WHEN** a covered source, model, test, prompt, contract, tier, or release
  artifact changes after evidence was produced
- **THEN** dependent proof receipts and release checks MUST become stale
- **AND** the minimum owning revalidation MUST run before publication

#### Scenario: GitHub release is created
- **WHEN** the current authorized publication reaches release closure and all
  local evidence is current and passing
- **THEN** the annotated version tag, origin default branch, repository version
  files, release notes, and GitHub Release MUST identify the same commit and
  version

#### Scenario: Authorized remote publication is incomplete
- **WHEN** the exact task commit is locally verified but the task branch,
  origin default branch, annotated tag, or GitHub Release is missing or points
  to another commit
- **THEN** release closure MUST remain blocked
- **AND** maintenance MUST repair the single same-commit publication path or
  report the exact collision without force-pushing, retagging, or selecting an
  alternate success path

### Requirement: Incomplete predecessor coverage changes are explicitly superseded
Earlier Cartesian/fake-AI changes that lack formal verification contracts SHALL
remain historical requirement sources and SHALL not independently support the
new release claim.

#### Scenario: Successor verification passes
- **WHEN** this change has current passing verification and release evidence
- **THEN** predecessor execution-coverage changes MAY be marked superseded or
  archived as history
- **AND** their generated-cell, abstract-green, or test-name proof claims MUST
  not remain active release evidence

#### Scenario: Predecessor provides retained current behavior
- **WHEN** a predecessor owns a still-current requested-role, role-memory,
  compact-review, stage-review, ledger, or contract-surface requirement
- **THEN** the successor disposition MUST identify that requirement as
  `retain` or `merge` with its current owner
- **AND** the predecessor's narrower or stale closure evidence MUST remain
  distinct from successor proof

#### Scenario: Predecessor has no explicit disposition
- **WHEN** a completed or incomplete predecessor can still appear to authorize
  the same resume, review, coverage, or release intent
- **THEN** successor closure MUST block until the predecessor is classified as
  `retain`, `merge`, `supersede`, `archive-history`, or `block`
- **AND** checked tasks or a green generated report MUST NOT choose the
  disposition automatically

#### Scenario: Required predecessor disposition set is audited
- **WHEN** successor verification begins
- **THEN** the disposition inventory MUST include
  `harden-flowpilot-control-plane-ledger-hygiene`,
  `adopt-runtime-requested-role-bindings`,
  `harden-flowpilot-role-continuity-memory`,
  `strengthen-flowpilot-reviewer-pm-challenge-chain`,
  `reduce-flowpilot-contract-surface`,
  `harden-flowpilot-fake-ai-review-window-coverage`,
  `harden-review-window-completeness-matrix`, and the affected earlier
  Cartesian/contract-exhaustion/formal-artifact/AI-projection changes
- **AND** no listed predecessor may independently support the successor's
  broad evidence or release claim

### Requirement: Existing verification-contract ownership remains explicit
Planning updates SHALL record new verification obligations in the current
proposal, design, specifications, and tasks even when the existing
`verification-contract.yaml` is outside the provider-reported
`existingOutputPaths`.

#### Scenario: Verification contract is outside update-change edit scope
- **WHEN** OpenSpec status does not return `verification-contract.yaml` as an
  existing output path
- **THEN** update-change MUST leave that file unchanged
- **AND** a separate task owned by the verification-contract workflow MUST
  synchronize the new obligations before broad verification or archive

#### Scenario: OpenSpec provider validation runs
- **WHEN** the planning artifacts are ready for strict provider validation
- **THEN** the current command MUST be
  `openspec validate restore-flowpilot-test-evidence-closure --type change --strict --no-interactive`
- **AND** the removed `openspec verify` command MUST NOT be used as completion
  evidence
