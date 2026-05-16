## Why

FlowPilot monitor status can show `waiting_for_role: null` even while a packet holder, passive reconciliation wait, or internal Router/Controller duty is still responsible for progress. Controller needs one clear monitor field that says who is currently advancing the work, not a narrow pending-action wait field that can go blank.

## What Changes

- Add a controller-facing "current work owner" projection to monitor/status payloads.
- Make the monitor's primary responsibility display answer: "who is currently working, and what are they doing?"
- Preserve existing `current_wait` and `waiting_for_role` fields for compatibility, but stop treating them as the only live ownership signal.
- Derive ownership from pending actions, passive waits, active packet holder state, and internal Router/Controller duties in a deterministic priority order.
- Add model and runtime coverage for `pending_action: null` cases that still have a real packet holder or passive reconciliation owner.

## Capabilities

### New Capabilities
- `current-work-owner`: Controller-facing monitor projection for the current responsible role/system actor and task label.

### Modified Capabilities

## Impact

- Affected code: `skills/flowpilot/assets/flowpilot_router.py`.
- Affected tests: focused router runtime tests for current status summaries, daemon status, packet-holder projection, and passive reconciliation waits.
- Affected models: focused FlowGuard coverage for monitor ownership projection; broad meta/capability regressions should still be run because monitor status is part of project-control flow.
- Affected install flow: local installed FlowPilot skill must be resynced after source changes.
