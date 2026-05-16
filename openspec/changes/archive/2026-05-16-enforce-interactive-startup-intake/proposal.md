## Why

FlowPilot formal startup currently accepts a startup intake result that can be produced by the headless helper path, so an agent can bypass the native intake window while still advancing the run. This change makes the user-visible startup UI a hard runtime boundary instead of a prompt-only instruction.

## What Changes

- Require formal startup intake results to declare an interactive native launch source.
- Mark headless startup intake output as non-formal so it can be used for tests and diagnostics but not for real startup.
- Reject headless, scripted, or synthesized startup intake results before startup answers are recorded.
- Update FlowPilot prompt guidance so Controller stops on UI launch or provenance failure instead of filling the payload manually.
- Add FlowGuard and runtime regression coverage for the bypass class.

## Capabilities

### New Capabilities

- `interactive-startup-intake`: Formal FlowPilot startup accepts only user-confirmed interactive native intake results and rejects headless substitutes.

### Modified Capabilities

- None.

## Impact

- `skills/flowpilot/SKILL.md`
- `skills/flowpilot/assets/flowpilot_router.py`
- `skills/flowpilot/assets/ui/startup_intake/flowpilot_startup_intake.ps1`
- `simulations/flowpilot_startup_intake_ui_model.py`
- `tests/test_flowpilot_router_runtime.py`
- Local installed FlowPilot skill sync and install audit
