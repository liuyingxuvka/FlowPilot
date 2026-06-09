## Why

FlowPilot already has FieldLifecycleMesh, field-contract checks, and model-test
alignment slots, but the current field lifecycle coverage does not model
packet/result/frontier currentness as transition semantics. This allowed stale
or terminal packet state to be reactivated by late results and allowed derived
status projections to use local filters instead of the single Router currentness
predicate.

## What Changes

- Add current-contract lifecycle coverage for packet/result/frontier fields
  whose values decide whether work is current, terminal, pending, append-only,
  or derived.
- Bind derived projections such as compact active packets and closure active
  packet scans to the single runtime currentness predicate instead of parallel
  local filtering.
- Add FlowGuard model and model-test alignment evidence for the same failure
  family: late results after terminal packet disposition, stale route-node
  packets, pending route-mutation cleanup, and derived projection drift.
- Add focused ordinary tests and fake-host regression coverage that prove the
  repaired path is current-contract only and does not accept legacy aliases or
  fallback shapes.
- **BREAKING**: none for current-contract users. Unsupported old states remain
  unsupported and are not translated into current evidence.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `flowpilot-control-plane-contract-kernel`: packet/result/frontier lifecycle
  fields must preserve terminal currentness and route-scope authority.
- `flowpilot-derived-view-registries`: active-packet projections must derive
  from the single Router currentness predicate.
- `flowguard-boundary-test-alignment`: behavior-bearing field lifecycle rows
  must project into model obligations, owner code contracts, and ordinary
  regression evidence before broad confidence.
- `known-friction-regression-gates`: the observed currentness/projection miss
  must be represented as a same-family regression gate.

## Impact

- FlowGuard model files under `simulations/`, especially field contract/mesh
  and model-test alignment surfaces.
- FlowPilot runtime currentness and status projection code under
  `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- Focused runtime, lifecycle, and fake-agent regression tests under `tests/`.
- Generated FlowGuard result artifacts, local install sync artifacts, and
  repository topology if affected by model or runner changes.
