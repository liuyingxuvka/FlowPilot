## Why

FlowPilot can currently mark a project route as materialized from parser-friendly prose, then silently fall back to a fixed bootstrap route when PM output is structured JSON the parser does not understand. That makes terminal closure vulnerable to accepting process evidence while the requested product artifacts were never created.

## What Changes

- **BREAKING** Require PM planning results to be a `flowpilot.route_plan.v1` JSON object with an explicit `nodes` array.
- **BREAKING** Reject prose-only, numbered-list, missing-schema, or `route_nodes` compatibility inputs instead of inferring nodes.
- **BREAKING** Remove active-route step fallback from route materialization.
- Carry node-level `required_outputs`, `deliverable_checks`, `validation_checks`, and schema metadata into executable route nodes.
- Add system-owned final deliverable checks to the final route-wide ledger and final requirement evidence matrix.
- Block terminal closure when route-declared deliverables are missing, unreadable, or failing their declared check kind.

## Capabilities

### New Capabilities

- `strict-route-plan-schema`: Defines the exact PM route-plan contract and the no-fallback materialization rule.

### Modified Capabilities

- `flowpilot-closure-kernel`: Adds system-owned deliverable verification as a terminal closure blocker.
- `terminal-ledger`: Adds route-declared deliverable check rows to final terminal evidence.

## Impact

- Runtime route materialization in `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`.
- Final route-wide ledger and final requirement evidence matrix construction.
- Focused runtime tests in `tests/test_flowpilot_recursive_route_execution_runtime.py` and `tests/test_flowpilot_high_standard_control_flow.py`.
- Core runtime model/regression runner and local installed FlowPilot sync checks.
