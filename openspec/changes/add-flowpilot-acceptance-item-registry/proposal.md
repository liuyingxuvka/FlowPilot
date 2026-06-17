## Why

FlowPilot already has high-standard prompts and final gates, but the quality
floor is spread across PM prose, route nodes, node plans, Reviewer reports,
FlowGuard reports, and final ledgers. A run can therefore look heavily gated
while individual user requirements or PM-added high standards are not tracked
as the same closeable item from planning through terminal replay.

## What Changes

- Add a PM-owned acceptance item registry inside the existing
  `high_standard_contract` path. It compiles explicit user requirements,
  implicit user commitments, PM-added high standards, low-quality-success
  risks, target-realization obligations, child-skill standards, and FlowGuard
  obligations into atomic, testable acceptance items.
- Project acceptance item ids through existing route nodes,
  `node_acceptance_plan`, work packets, PM dispositions, Reviewer gates,
  FlowGuard route checks, final ledger, final requirement matrix, and terminal
  backward replay.
- Require Reviewer and FlowGuard operator cards to block orphan, generic,
  uncheckable, or low-quality item coverage while preserving the existing
  package, packet, result, and gate surfaces.
- Require final ledger and terminal replay to close every active acceptance
  item at high quality, with unresolved, waived, superseded, stale, or
  route-mutated items visible.
- Keep the current FlowPilot route and current-contract runtime. No new role
  family, packet kind, fallback lane, legacy migration path, or separate
  quality workflow is introduced.

## Capabilities

### New Capabilities

- `flowpilot-acceptance-item-registry`: PM compiles and maintains an atomic
  acceptance item registry that is projected through route, node, work,
  review, FlowGuard, final ledger, and terminal replay surfaces.

### Modified Capabilities

- `flowpilot-packet-review-flow`: Existing PM/reviewer package review must use
  acceptance item ids as trace keys when the current run declares a registry.
- `formal-gate-review-standards`: Reviewer still derives pass/fail standards
  from existing artifacts, but must also check the registry projection and
  high-quality closure for every applicable item.
- `terminal-ledger`: Terminal final ledger and backward replay must report
  active acceptance item closure, not only route node or requirement rows.
- `flowpilot-closure-kernel`: Closure remains blocked while any active
  acceptance item is missing, low-quality, stale, waived without authority, or
  unresolved after route mutation.
- `hard-gate-coverage-matrix`: Negative coverage must include missing registry,
  orphan item, missing node projection, low-quality item closure, and terminal
  item-replay gaps.

## Impact

- Runtime contracts and helpers under `skills/flowpilot/assets/`.
- Runtime cards under `skills/flowpilot/assets/runtime_kit/cards/`.
- FlowPilot templates under `templates/flowpilot/`.
- Focused runtime tests and planning-quality FlowGuard checks under `tests/`
  and `simulations/`.
- FlowGuard adoption evidence, topology artifacts, and installed-skill sync
  after validation.
