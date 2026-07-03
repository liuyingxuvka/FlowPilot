## Why

Long FlowPilot runs can rewrite their route many times. The current progress
fraction can count superseded repair history alongside the active route, which
makes a nearly finished route look like dozens of unfinished nodes remain.

## What Changes

- Make the runtime-owned `progress_fraction` reflect a stable initial planning
  node plus the current active route when that route has a materialized
  `node_order`.
- Treat repair replacements as replacements of the original route slot, not as
  extra historical work that increases the user-visible denominator.
- Replace the packet-count early fallback with one display-only initial
  planning node: before route nodes exist the fraction is `0/1`; after route
  nodes exist the initial node is counted as complete and real route nodes are
  added after it.
- Do not change execution authority, sealed packet visibility, or completion
  gates; this is a display/progress-accounting fix only.

## Capabilities

### New Capabilities

- `flowpilot-progress-fraction`: Runtime-owned progress-fraction display for
  the currently active FlowPilot route.

### Modified Capabilities

None.

## Impact

- FlowPilot runtime progress-fraction calculation.
- Focused runtime tests for active route, repair replacement, and packet
  non-projection behavior.
- OpenSpec and FlowGuard validation evidence.
- Local installed FlowPilot skill sync after repository changes.
