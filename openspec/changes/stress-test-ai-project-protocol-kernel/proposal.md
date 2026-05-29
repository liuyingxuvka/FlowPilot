## Why

The first AI project protocol kernel proves the basic packet, lease, review,
FlowGuard, freshness, and backward-closure gates, but it is still mostly a
single-step model. The next risk is long-running project work: multiple AI
leases, route changes, stale returns, weak FlowGuard targeting, and background
checks can interact across rounds in ways a simple scenario table can miss.

## What Changes

- Add a dedicated stress-test capability for the clean AI project protocol
  kernel.
- Add a deterministic fake-AI wrapper that can simulate ACK-only workers,
  dead leases, late outputs, wrong-shaped results, weak reviewers,
  self-review, stale evidence, route mutation, wrong FlowGuard target
  selection, and final closure gaps.
- Add multi-round scripted scenarios that prove replacement workers can
  succeed while closed or stale workers cannot re-enter the authoritative
  ledger.
- Add seeded random long-run checks with stable outputs so regressions can be
  reproduced.
- Add a historical bad-case replay pack based on known FlowPilot failure
  families: ACK without output, route mutation with old packets, stale
  evidence reuse, progress-only background checks, and unsupported completion
  claims.
- Add a TestMesh-style evidence report that separates focused kernel tests,
  deterministic multi-round scripts, seeded long runs, historical replay,
  FlowGuard model exploration, background regressions, and install-surface
  verification.
- Update local install checks, version notes, and validation artifacts so the
  installed skill and repository copy agree after the new stress harness lands.

## Capabilities

### New Capabilities

- `ai-project-protocol-stress-testing`: Multi-round fake-agent stress testing,
  historical replay, seeded long-run validation, FlowGuard exploration, and
  TestMesh evidence for the clean AI project protocol kernel.

### Modified Capabilities

- `flowguard-background-observability`: Treat stress-test background and
  heavyweight model evidence as complete only when final artifacts, exit codes,
  and proof freshness metadata have been inspected.
- `repository-maintenance-guardrails`: Require install-surface sync and local
  source/install parity after adding protocol-kernel test assets.

## Impact

- Affected assets: new protocol stress-testing documentation under
  `skills/flowpilot/assets/ai_project_protocol/`.
- Affected simulations: new stress model/check runner and generated results
  under `simulations/`.
- Affected tests: focused tests for deterministic scenarios, seeded long-run
  checks, historical replay, and TestMesh evidence.
- Affected install/version surfaces: local install check inventory, version
  metadata, changelog/adoption notes, install sync, audit, and check commands.
- Out of scope: replacing the current FlowPilot router, changing old
  `.flowpilot/` runtime state, remote push, tag, release, deploy, or changing
  the frozen acceptance contract of existing archived changes.
