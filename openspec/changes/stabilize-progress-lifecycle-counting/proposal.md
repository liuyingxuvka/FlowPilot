## Why

FlowPilot `progress_fraction` can collapse from a previously expanded route to `1/2` when a later route materialization overwrites active `node_order` with a short supplemental node list. Users need progress to follow formal node lifecycle and route-structure disposition, not incidental list replacement.

## What Changes

- Count progress from current-run expanded route nodes instead of treating active `node_order` as the sole denominator.
- Preserve previously expanded nodes in public progress until a formal route mutation, replacement, waiver, stop, block, or supersession disposition removes or ends them.
- Allow the denominator to shrink only when route/node disposition explicitly proves the removed nodes are no longer effective obligations.
- Keep the display-only initial planning node for the no-route-node case.
- Keep packet, lease, ACK, patrol, role, and sealed-body surfaces excluded from progress.

## Capabilities

### New Capabilities
- `flowpilot-progress-fraction`: Runtime-owned public expanded-node progress for current-run FlowPilot ledgers.

### Modified Capabilities

## Impact

- Affected runtime: `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- Affected tests: focused `progress_fraction` coverage in `tests/test_flowpilot_core_runtime.py`.
- Affected validation: OpenSpec validation, focused runtime unit tests, FlowGuard route-replanning/mutation checks, install sync audit, and install self-check.
