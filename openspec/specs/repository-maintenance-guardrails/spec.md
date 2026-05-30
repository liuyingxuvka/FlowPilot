# repository-maintenance-guardrails Specification

## Purpose
TBD - created by archiving change maintain-flowpilot-repo-structure. Update Purpose after archive.
## Requirements
### Requirement: Completed OpenSpec work remains preserved when archived

Repository maintenance SHALL move completed OpenSpec changes only into an
archive location that remains tracked and reviewable.

#### Scenario: Completed changes leave the active list

- **GIVEN** OpenSpec reports a change as complete
- **WHEN** maintenance archives completed changes
- **THEN** the change directory is moved under `openspec/changes/archive/`
- **AND** its proposal, design, specs, and tasks files remain present.

#### Scenario: Incomplete task-count changes stay visible

- **GIVEN** OpenSpec reports a change as in-progress or its task checklist has
  unchecked items
- **WHEN** maintenance archives completed changes
- **THEN** that change remains under `openspec/changes/`
- **AND** the final report names it as intentionally left active.

### Requirement: Maintenance cleanup is report-first and non-destructive

Repository maintenance tools SHALL default to read-only reporting before any
cleanup of validation artifacts or runtime state.

#### Scenario: Validation artifact duplicates are reported

- **WHEN** the validation artifact audit runs
- **THEN** it reports duplicate result files, canonical candidates, sizes, and
  paths
- **AND** it does not delete, move, or rewrite artifacts.

#### Scenario: Runtime retention report protects current run pointers

- **WHEN** the runtime retention report runs
- **THEN** it reports `.flowpilot` size, run counts, current pointer status, and
  stale candidates
- **AND** it does not remove the current run, index, or runtime directory.

### Requirement: Local install freshness is verified after maintenance

After maintenance source changes, the local installed FlowPilot skill SHALL be
synchronized from the repository and audited for source freshness.

#### Scenario: Installed skill matches repo-owned source

- **WHEN** repository-owned install sync completes
- **THEN** the freshness audit passes
- **AND** the final maintenance report includes the install sync and audit
  commands' pass/fail status.

### Requirement: FlowGuard evidence remains executable and explicit

Maintenance SHALL run relevant focused checks, StructureMesh/TestMesh checks,
and background FlowGuard model regressions before claiming completion.

#### Scenario: Background model result has complete log artifacts

- **WHEN** a background FlowGuard regression is reported complete
- **THEN** stdout, stderr, combined, exit, and meta artifacts exist under the
  configured background log root
- **AND** the exit artifact shows a successful exit code.

#### Scenario: Skipped heavy checks remain visible

- **WHEN** a heavy check is not run
- **THEN** the final report names the skipped boundary, reason, and residual
  risk
- **AND** the skipped check is not described as passed.

#### Scenario: StructureMesh evidence gates large script splits

- **WHEN** maintenance moves functions, stateful helpers, side-effect writers,
  public entrypoints, or CLI surfaces out of a large script
- **THEN** the final report includes the relevant StructureMesh command,
  result status, routine/release decision, and any deferred obligations.

#### Scenario: TestMesh evidence gates split router suites

- **WHEN** maintenance relies on split router runtime suites for confidence
- **THEN** the final report includes the TestMesh command, child suite status,
  background artifact status, skipped count visibility, and stale evidence
  status.

#### Scenario: Model-Test Alignment evidence gates coverage claims

- **WHEN** maintenance claims that FlowGuard models and ordinary tests agree
- **THEN** the final report includes the Model-Test Alignment command, result
  status, missing evidence findings, orphan evidence findings, and overclaim
  findings
- **AND** skipped, stale, not-run, running, failed, timeout, and progress-only
  evidence is not described as passing coverage.

### Requirement: Architecture reduction changes are synchronized locally
Repository maintenance SHALL complete FlowGuard architecture-reduction source
changes with local install freshness evidence and local git evidence before
claiming done.

#### Scenario: Local installed FlowPilot skill is refreshed
- **WHEN** a FlowPilot architecture-reduction maintenance change modifies
  repo-owned skill source files
- **THEN** the repo-owned FlowPilot install sync command runs
- **AND** the installed-skill freshness audit passes before completion is
  claimed.

#### Scenario: Local git captures only the intended change
- **WHEN** validation and install sync pass for a FlowPilot architecture
  reduction
- **THEN** the local git commit contains only the OpenSpec artifacts, source,
  model/test evidence, docs, and sync outputs for that change
- **AND** remote push, tag, deploy, and GitHub release publication remain out
  of scope unless separately authorized.

### Requirement: Lifecycle request structure splits are locally synchronized

Repository maintenance SHALL finish FlowGuard-backed lifecycle request structure
splits with focused validation, background evidence, installed-skill freshness,
and local git evidence.

#### Scenario: Lifecycle request split completion is evidence backed

- **WHEN** a lifecycle request owner split modifies repo-owned FlowPilot skill
  source files
- **THEN** focused lifecycle, terminal, and control-blocker validation runs
- **AND** router, Meta, and Capability background regressions produce complete
  stdout, stderr, combined, exit, and meta artifacts before completion is
  claimed.

#### Scenario: Lifecycle request split is installed and committed locally

- **WHEN** lifecycle request split validation passes
- **THEN** the repo-owned FlowPilot skill is synced into the local installed
  skill location
- **AND** installed-skill freshness checks pass
- **AND** local git captures only the intended OpenSpec, source, model/test,
  docs, and evidence updates for the split.

### Requirement: Closure maintenance finishes with synchronized local evidence

Repository maintenance for FlowPilot runtime closure SHALL finish with
FlowGuard adoption evidence, local install freshness, OpenSpec validation, and
local git commit evidence before claiming the pass complete.

#### Scenario: Maintenance pass completes
- **WHEN** all implementation and validation tasks for this maintenance pass
  are complete
- **THEN** the final evidence includes FlowGuard adoption log updates, strict
  OpenSpec validation, install sync/check/audit pass status, and a local git
  commit containing the completed changes.

#### Scenario: Publication remains separate
- **WHEN** the maintenance pass commits locally
- **THEN** it does not push, tag, publish, or create a release unless the user
  explicitly authorizes that separate action.

### Requirement: Registry consolidation preserves parity evidence

Repository maintenance SHALL prove that registry-derived parity views match the previously exported tables before switching behavior-sensitive callers to the registry.

#### Scenario: Generated table parity is checked before caller migration

- **GIVEN** a canonical registry replaces a hand-written protocol table
- **WHEN** maintenance migrates runtime callers to the derived view
- **THEN** a focused parity test proves the derived table matches the previous exported names and values
- **AND** the final maintenance report names that parity evidence.

### Requirement: Local git completion excludes unrelated worktree changes

Repository maintenance SHALL keep local git completion scoped to the current change and avoid staging unrelated pre-existing edits.

#### Scenario: Dirty worktree has unrelated files

- **GIVEN** the worktree contains modified files outside the maintenance registry consolidation scope
- **WHEN** the change is staged or committed
- **THEN** only files intentionally changed for this OpenSpec change are staged
- **AND** unrelated files remain untouched and are named as pre-existing if relevant.

### Requirement: Full diagnostic evidence is distinguished from subset alignment

Repository maintenance evidence SHALL distinguish a selected model-test
alignment pass from a full model-test-code diagnostic pass.

#### Scenario: Subset alignment is not reported as full diagnostic coverage
- **WHEN** only selected model obligations have model-test-code source audit
  evidence
- **THEN** maintenance reports the covered subset and the remaining diagnostic
  scope
- **AND** it does not claim that every owner module, facade, script entrypoint,
  and test tier is fully covered.

#### Scenario: Full diagnostic report names residual gaps
- **WHEN** the full diagnostic pass completes with uncovered surfaces
- **THEN** maintenance reports the residual gap counts and representative paths
- **AND** uncovered surfaces are not described as passed checks.

### Requirement: Background evidence remains artifact-complete

Repository maintenance evidence SHALL reject background validation evidence
that only proves liveness or progress.

#### Scenario: Progress-only background artifact is rejected
- **WHEN** a background validation surface has stdout or progress lines but no
  successful exit and meta artifact
- **THEN** maintenance records the surface as incomplete or stale
- **AND** the result cannot be used as release-quality pass evidence.

### Requirement: Pre-release maintenance validates public boundary before remote sync
Repository maintenance SHALL run a public-boundary and privacy preflight before
pushing pre-release source changes to the remote FlowPilot repository.

#### Scenario: Privacy preflight blocks local-state leakage
- **WHEN** tracked files include private runtime state, local KB records, cache
  directories, local environment files, machine-specific paths, or secret-shaped
  content
- **THEN** remote source sync is blocked until the tracked public boundary is
  corrected or the finding is explicitly documented as a false positive.

#### Scenario: Remote sync is source-only
- **WHEN** pre-release maintenance pushes the branch to `origin`
- **THEN** it does not create tags, GitHub Releases, binary packages, deploys,
  or companion skill publication side effects.

### Requirement: Skipped release-heavy checks remain visible
Repository maintenance SHALL record user-skipped heavy checks as skipped, not
passed, when finalizing pre-release work.

#### Scenario: Meta and Capability regressions are excluded by user request
- **WHEN** the user asks to skip the heavyweight Meta and Capability model
  regressions
- **THEN** final validation evidence names both skipped model boundaries, the
  reason for skipping, and the residual confidence boundary.

### Requirement: Structure optimization prioritizes branch-risk reduction

Repository maintenance SHALL treat file splitting as a secondary technique
behind behavior-preserving logic contraction, duplicate-branch removal, and
bug-risk reduction.

#### Scenario: Line count alone does not justify a split

- **WHEN** a FlowPilot owner module exceeds a line-count threshold
- **THEN** the maintenance plan identifies the behavior-bearing branch risk,
  duplicate result paths, or ownership ambiguity being reduced
- **AND** it does not claim a maintenance improvement solely because code moved
  into more files.

#### Scenario: Branch pruning drives structure planning

- **WHEN** FlowGuard Architecture Reduction identifies repeated branches around
  the same observable state or side effects
- **THEN** Code Structure Recommendation derives target modules from the
  reduced FunctionBlocks, state ownership, side-effect ownership, and public
  unsupported historical boundary.

#### Scenario: Risky state owners remain explicit

- **WHEN** a candidate touches core runtime state, stale-save protection,
  dynamic Router event authority, or external event recording
- **THEN** the plan records the missing evidence or replay requirement
- **AND** the candidate remains blocked or model-only until that evidence is
  supplied.

### Requirement: Router IO structure splits are locally synchronized

Repository maintenance SHALL finish FlowGuard-backed Router IO structure splits
with focused validation, background evidence, installed-skill freshness, and
local git evidence.

#### Scenario: Router IO split completion is evidence backed

- **WHEN** a Router IO owner split modifies repo-owned FlowPilot skill source
  files
- **THEN** focused IO, daemon, terminal, and model-test validation runs
- **AND** router, Meta, and Capability background regressions produce complete
  stdout, stderr, combined, exit, and meta artifacts before completion is
  claimed.

#### Scenario: Router IO split is installed and committed locally

- **WHEN** Router IO split validation passes
- **THEN** the repo-owned FlowPilot skill is synced into the local installed
  skill location
- **AND** installed-skill freshness checks pass
- **AND** local git captures only the intended OpenSpec, source, model/test,
  docs, and evidence updates for the split.
