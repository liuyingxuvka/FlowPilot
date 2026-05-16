## Why

FlowPilot's heaviest FlowGuard project checks can run long enough that foreground sessions time out or become hard to interpret. Current logs are spread across several task-local directories, and the legacy meta/capability runners do not emit live progress while building their large state graphs.

## What Changes

- Define `tmp/flowguard_background/` as the default FlowPilot long-check log directory.
- Require background FlowGuard runs to write stdout, stderr, combined output, exit status, and metadata files with stable command names.
- Require final reports to cite those paths, exit codes, timestamps, and proof-reuse status.
- Add stderr-only progress output to `simulations/run_meta_checks.py` and `simulations/run_capability_checks.py`.
- Preserve current model semantics, result JSON shape, proof reuse behavior, and stdout final-report content.

## Capabilities

### New Capabilities
- `flowguard-background-observability`: FlowPilot-specific logging and progress expectations for long-running FlowGuard project checks.

### Modified Capabilities
- None.

## Impact

- Updates FlowPilot repository operating rules in `AGENTS.md`.
- Updates the legacy meta and capability check runners.
- Adds focused tests for progress stream routing, opt-out behavior, and proof-reuse visibility.
- Does not change FlowPilot runtime routing behavior or acceptance contracts.
