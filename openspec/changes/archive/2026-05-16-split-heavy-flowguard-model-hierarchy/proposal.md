## Why

The FlowPilot `meta` and `capability` FlowGuard models have grown to roughly two million states each, making ordinary validation dependent on sharding, proof reuse, and long background runs. The repository already has many focused child models, so the next step is to make the heavy parent models consume child evidence through an explicit hierarchy instead of repeatedly expanding every concern inside one monolithic graph.

## What Changes

- Add a model hierarchy contract that classifies heavyweight parents, focused child models, shared kernels, evidence freshness, and parent partition coverage.
- Add executable FlowGuard checks that reject unsafe split plans, stale child evidence, hidden skipped checks, uncovered parent partitions, and sibling ownership overlap.
- Introduce a lightweight hierarchy runner that can be used in foreground validation while meta/capability full regressions run in the background.
- Update validation surfaces so install/smoke checks can distinguish hierarchy evidence from full heavyweight regression evidence.
- Preserve existing meta/capability runners as heavyweight regressions until their parent responsibilities are safely narrowed.
- Keep peer-agent work intact; final git submission must include compatible peer changes rather than reverting unrelated work.

## Capabilities

### New Capabilities

- `flowguard-model-hierarchy`: Defines how FlowPilot represents heavyweight FlowGuard models as parent/child model hierarchies with partition coverage, ownership, evidence tiers, stale-result rules, and background regression obligations.

### Modified Capabilities

- None.

## Impact

- Affected areas include `simulations/`, model check runners, FlowGuard coverage/install validation, OpenSpec change artifacts, and documentation for model hierarchy and background regression evidence.
- The change does not alter the FlowPilot runtime protocol directly unless validation integration reveals a narrow required hook.
- Heavy regressions remain required for release confidence, but day-to-day confidence moves toward targeted child checks plus parent hierarchy validation.
