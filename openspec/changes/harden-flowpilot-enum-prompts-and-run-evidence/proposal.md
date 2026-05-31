## Why

The first real exercise of the new FlowPilot formal runtime exposed two avoidable operator traps: a role agent guessed an invalid `--host-kind` value, and FlowGuard evidence for the formal run dirtied a tracked simulation result file. Both problems are prompt/process contract gaps rather than old-compatibility requirements.

## What Changes

- Add explicit allowed-value menus wherever a FlowPilot prompt or command asks an AI to fill a fixed enum-like value, starting with `--host-kind`.
- Tell role agents to stop and report a value-menu mismatch instead of inventing values when none of the listed choices fits.
- Add run-local evidence output support for Meta and Capability FlowGuard check runners, so formal FlowPilot work packets can write current-run evidence under `.flowpilot/runs/<run-id>/evidence/...`.
- Make FlowGuard officer packets carry the run-local output policy and the concrete runner flags needed to avoid tracked baseline files.
- Add FlowGuard model coverage and ordinary regressions for enum-menu guidance and run-local evidence isolation.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `flowpilot-prompt-boundary-policy`: fixed-value prompt fields must enumerate allowed values and forbid invented alternatives.
- `flowguard-background-observability`: formal run FlowGuard evidence must support run-local output paths and avoid tracked baseline result files unless a baseline update is explicitly requested.

## Impact

- Affected runtime and skill guidance: `skills/flowpilot/SKILL.md`, `skills/flowpilot/assets/flowpilot_new.py`, and `skills/flowpilot/assets/ai_project_runtime/runtime.py`.
- Affected FlowGuard runners: `simulations/run_meta_checks.py`, `simulations/run_capability_checks.py`, and their implementation modules.
- Affected validation: new-entrypoint FlowGuard model/checks, focused unit tests, install checks, local installed skill sync, version/changelog, and FlowGuard adoption notes.
