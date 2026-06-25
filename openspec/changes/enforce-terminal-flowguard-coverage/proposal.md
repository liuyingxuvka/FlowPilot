## Why

FlowPilot already has PM final ledgers, terminal backward replay, FlowGuard
operator reports, evidence quality packages, and supplemental repair contracts,
but terminal completion can still be argued from scattered node-level
FlowGuard evidence instead of one PM-accepted project-level coverage report.
This pass makes terminal FlowGuard coverage a first-class closure gate inside
the existing PM/Reviewer/repair flow rather than adding a parallel workflow.

## What Changes

- Add a terminal FlowGuard coverage Work Order and report boundary using the
  existing FlowGuard operator request/report lifecycle.
- Require PM final ledgers to cite a current, PM-accepted terminal FlowGuard
  coverage report before terminal reviewer replay or PM closure can pass.
- Require terminal Reviewer backward replay to include a
  `flowguard-coverage-governance` segment that checks the report, PM
  absorption, blocker disposition, freshness, and waivers.
- Route missing, stale, progress-only, unaccepted, or blocking terminal
  FlowGuard coverage through the existing supplemental repair contract loop.
- Add runtime contracts, quality-pack checks, FlowGuard model coverage, and
  fake-role/cartesian regression cases for the new terminal gate.
- Synchronize the repository-owned FlowPilot skill into the local Codex install
  and leave local git evidence after validation.

## Capabilities

### New Capabilities

- `terminal-flowguard-coverage`: project-level FlowGuard coverage report,
  PM absorption, reviewer terminal segment, and supplemental repair routing for
  terminal completion.

### Modified Capabilities

- `repository-maintenance-guardrails`: this maintenance pass finishes with
  OpenSpec validation, FlowGuard evidence, fake-role/cartesian regression
  coverage, local install freshness, and local git evidence. It does not push,
  tag, publish, or create a GitHub release.

## Impact

- Runtime cards under `skills/flowpilot/assets/runtime_kit/cards/`
- Runtime contracts under
  `skills/flowpilot/assets/runtime_kit/contracts/contract_index.json`
- Quality pack catalog under
  `skills/flowpilot/assets/runtime_kit/quality_pack_catalog.json`
- FlowPilot router/runtime helpers under `skills/flowpilot/assets/`
- Focused FlowGuard models and results under `simulations/`
- Runtime, output-contract, fake-role, and install tests under `tests/` and
  `scripts/`
- `HANDOFF.md`, `CHANGELOG.md`, `VERSION`, and local installed FlowPilot skill

