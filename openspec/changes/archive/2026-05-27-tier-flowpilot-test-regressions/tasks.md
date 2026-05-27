## 1. Spec And Model

- [x] 1.1 Create OpenSpec proposal, design, tasks, and requirements for
  tiered FlowPilot validation.
- [x] 1.2 Add a focused FlowGuard TestMesh-style model with valid scenarios
  and known-bad hazards.
- [x] 1.3 Add a runner that writes the model result JSON.

## 2. Test Tooling

- [x] 2.1 Add pytest configuration that scopes default discovery to `tests/`
  and excludes backup/temp/control directories.
- [x] 2.2 Add a tiered test runner with foreground, dry-run, JSON, and
  background artifact support.
- [x] 2.3 Add unit tests for tier command planning and background artifact
  naming.

## 3. Sync And Validation

- [x] 3.1 Register the new runner, tests, model, and result in install checks.
- [x] 3.2 Run focused TestMesh model checks and tier runner tests.
- [x] 3.3 Run install/local-sync validation.
- [x] 3.4 Launch long regressions in background when useful and inspect any
  completed artifacts before reporting completion.
