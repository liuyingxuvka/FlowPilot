## 1. Specification

- [x] 1.1 Capture the intended behavior in OpenSpec proposal, design, and capability requirements.
- [x] 1.2 Validate the OpenSpec change before implementation.

## 2. FlowGuard

- [x] 2.1 Verify real FlowGuard is available in the active environment.
- [x] 2.2 Model core-load-owned boundary confirmation and redundant-row hazards.
- [x] 2.3 Run the focused FlowGuard checks for the updated startup/control-plane model.

## 3. Runtime

- [x] 3.1 Make `load_controller_core` write or reconcile canonical Controller boundary confirmation evidence.
- [x] 3.2 Stop fresh startup from scheduling a standalone `confirm_controller_core_boundary` row after core load evidence is present.
- [x] 3.3 Preserve compatibility for existing pending/completed standalone boundary rows.

## 4. Tests And Sync

- [x] 4.1 Add focused router runtime tests for fresh startup and legacy boundary-action compatibility.
- [x] 4.2 Run targeted tests; Meta/Capability heavyweight regressions skipped by user as too heavy for this pass.
- [x] 4.3 Sync and audit the installed local FlowPilot skill.
- [x] 4.4 Review peer-agent changes and prepare one compatible final git state.
