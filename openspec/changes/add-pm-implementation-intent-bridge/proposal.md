## Why

FlowPilot currently models the product target and the route process, but the PM's judgment about how the target should be realized is spread across product architecture, route skeleton, and node acceptance prompts. This lets route drafting begin before a PM-authored realization path has been formalized and simulated by FlowGuard.

## What Changes

- Add a PM-owned implementation intent bridge after accepted product behavior modeling and before PM route skeleton drafting.
- Add a FlowGuard Operator target-realization modeling step that converts the PM implementation intent into formal states, transitions, hazards, counterexamples, evidence gates, and downstream obligations.
- Add PM and Reviewer acceptance gates for the target-realization model before route skeleton work may proceed.
- Project accepted realization obligations into route skeletons, route process checks, node acceptance plans, worker packets, and terminal closure ledgers.
- Add strict current-contract templates, output contracts, router transitions, and negative regression coverage for missing, downgraded, or unconsumed implementation intent.
- Do not introduce LogicGuard, SourceGuard, compatibility aliases, prose fallbacks, missing-field defaults, or a parallel ledger family.

## Capabilities

### New Capabilities

- `pm-implementation-intent-bridge`: PM-authored realization intent, FlowGuard target-realization modeling, PM/Reviewer acceptance, and downstream obligation propagation.

### Modified Capabilities

- `flowpilot-prompt-boundary-policy`: Require prompt cards to preserve the PM/FlowGuard/Reviewer role split for implementation intent.
- `formal-gate-review-standards`: Require Reviewer challenge of implementation intent alignment before route drafting.
- `flowguard-boundary-test-alignment`: Bind implementation-intent model obligations to route, node, worker, and closure tests.

## Impact

- Runtime cards under `skills/flowpilot/assets/runtime_kit/cards/`.
- Runtime kit manifest, output contract, control transaction, and router transition surfaces that govern legal next actions.
- Reusable templates under `templates/flowpilot/`.
- FlowGuard planning-quality, meta, capability, role-output, router-action, and card-coverage model/test evidence under `simulations/` and `tests/`.
- Local install synchronization and install audit surfaces.
