## Why

FlowPilot already asks FlowGuard officers to report model obligations, ordinary
test evidence, and missing test kinds, but the control flow does not make one
role explicitly responsible for turning those gaps into test-maintenance work
before node closure. This lets a broad FlowGuard model pass while lower-level
bugs remain untested or treated as residual prose.

## What Changes

- Add a PM-owned test obligation matrix at node entry and node completion.
- Require FlowGuard officer reports and worker results to feed that matrix
  instead of leaving `missing_test_kinds` as advisory prose.
- Require PM to disposition every missing, stale, skipped, failed, or
  not-run test obligation before node completion, evidence-quality packaging,
  final ledger work, or terminal closure can pass.
- Route test-authoring or test-maintenance work to worker packets or bounded
  PM role-work requests; FlowGuard officers design obligations and gaps, but
  do not become the default maintainers of ordinary test code.
- Escalate broad, slow, layered, stale, or release-only validation through
  TestMesh, and direct obligation/test mismatches through Model-Test Alignment.
- Add FlowGuard model and ordinary regression tests for this authority chain.

## Capabilities

### New Capabilities

- `flowguard-test-obligation-ownership`: PM-owned conversion of FlowGuard
  model obligations and missing test kinds into explicit worker test
  maintenance, TestMesh, Model-Test Alignment, waiver, or blocker decisions.

### Modified Capabilities

- None.

## Impact

- Affects FlowPilot runtime cards for PM, workers, reviewers, and FlowGuard
  officer request/report handling.
- Affects the runtime output-contract registry for worker and PM role-work test
  obligation evidence.
- Adds a focused FlowGuard simulation and focused tests for the new process
  ownership rule.
- Requires local installed FlowPilot skill sync and freshness audit after
  repo-owned skill files change.
