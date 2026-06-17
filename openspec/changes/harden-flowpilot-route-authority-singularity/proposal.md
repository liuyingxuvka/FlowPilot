## Why

FlowPilot already rejects many malformed packets and has a legal next-action policy, but recent stuck-loop failures show that route authority is still tested in pieces rather than as one current-contract control path. A role can still drift toward a wrong route action, old alias, or unsupported fallback shape unless the router proves one owner, one current legal action set, and actionable repair feedback for every wrong-path rejection.

## What Changes

- Add a route-authority singularity contract: every foreground route/control state must expose one current owner, one current state family, legal next actions, forbidden actions, and a repair command when a submitted action is not legal.
- Extend FlowGuard coverage with a dedicated route-authority singularity model for owner missing/conflict, PM wrong-path choices, wrong-role submissions, stale legal snapshots, old aliases, prose/fallback wrappers, and missing repair feedback.
- Harden router/control-plane projections so `router_no_legal_next_action`, wrong-path rejections, and action-provider conflicts are visible to ModelMesh and model-test alignment.
- Extend synthetic fake-AI coverage and trace replay for wrong PM path, role overreach, old alias/fallback attempts, repeated wrong-path no-delta retries, and corrected retry return to the main route.
- Keep the new-only rule: unsupported old actions, aliases, wrappers, prose guesses, and compatibility fallbacks are rejected, not translated into valid current actions.

## Capabilities

### New Capabilities
- `flowpilot-route-authority-singularity`: FlowPilot route/control states expose exactly one current route authority, reject wrong-path role actions with current structured repair feedback, and prove no fallback or compatibility path can silently advance the route.

### Modified Capabilities
- `synthetic-agent-coverage-matrix`: Add fake-AI wrong-path and corrected-retry coverage for route authority failures.
- `synthetic-agent-trace-replay`: Add trace replay cases for role overreach, wrong-path no-delta retry, and repair-command-guided correction.
- `flowguard-boundary-test-alignment`: Bind the new route-authority model obligations to router runtime tests and synthetic replay evidence.

## Impact

- Affected runtime/control code: `skills/flowpilot/assets/flowpilot_router_action_providers_fresh.py`, `skills/flowpilot/assets/flowpilot_router_controller_runtime_next.py`, `skills/flowpilot/assets/flowpilot_router_action_factory_dispatch_blockers.py`, route action policy helpers, and related router facade exports.
- Affected registries/prompts: `skills/flowpilot/assets/runtime_kit/route_action_policy_registry.json`, system-card or packet payload contexts that expose legal/forbidden route actions.
- Affected models/tests: new route-authority singularity model and runner, `flowpilot_model_mesh_model.py`, `flowpilot_model_test_alignment_family_plans.py`, synthetic coverage matrix/replay tests, router runtime tests, generated result artifacts, and project topology.
- Affected process: FlowGuard project records already upgraded to installed FlowGuard `0.48.0`; final confidence requires OpenSpec validation, FlowGuard model checks, targeted unit tests, ModelMesh/MTA checks, topology rebuild/check, local install sync, and install audit.
