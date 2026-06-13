## Why

Long FlowPilot runs can rewrite their route many times. The current progress
fraction can count superseded repair history alongside the active route, which
makes a nearly finished route look like dozens of unfinished nodes remain.

## What Changes

- Make the runtime-owned `progress_fraction` reflect only the current active
  route when that route has a materialized `node_order`.
- Treat repair replacements as replacements of the original route slot, not as
  extra historical work that increases the user-visible denominator.
- Keep the existing packet projection only for the early phase before the
  active route has materialized route nodes.
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
  projection behavior.
- OpenSpec and FlowGuard validation evidence.
- Local installed FlowPilot skill sync after repository changes.
