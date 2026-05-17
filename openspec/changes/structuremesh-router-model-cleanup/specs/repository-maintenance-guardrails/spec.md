## MODIFIED Requirements

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
