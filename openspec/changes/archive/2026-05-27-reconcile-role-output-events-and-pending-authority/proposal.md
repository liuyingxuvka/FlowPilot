## Why

Recent FlowPilot control-plane runs can reach a split-brain state: durable ledgers show that a role output satisfied an external-event wait, while `router_state.pending_action` still presents that wait as current work. This change prevents completed waits and role-output events from being lost between ledgers, Router state, daemon status, and reminders.

## What Changes

- Add generic durable reconciliation for direct role-output events that declare an authorized `event_name`, instead of only recovering selected special cases.
- Require resolved Controller action rows or Router scheduler rows to invalidate matching `pending_action` projections before daemon status, current-work selection, reminders, or next-action computation.
- Ensure material-sufficiency review events fold back into Router state, material review projection, and the PM repair/research branch.
- Extend focused FlowGuard coverage and runtime tests for role-output event drift, stale pending authority, and stale reminders.
- No breaking user-facing API change; this tightens existing control-plane semantics.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `daemon-projection-reconciliation`: daemon reconciliation must fold generic direct role-output events into Router state before selecting work.
- `router-external-wait-reconciliation`: resolved external-event wait rows must clear matching pending-action projections and suppress reminders.
- `current-work-owner`: daemon status/current-work projection must reject pending actions whose durable wait rows are already resolved.

## Impact

- Affected runtime code: FlowPilot Router role-output bridge, expected-wait reconciliation, lifecycle reconciliation barrier, pending-action provider, and current-work/status derivation.
- Affected validation: focused FlowGuard control-plane consistency model, daemon/scheduler small models, control-plane contract tests, and install sync checks.
- Heavyweight Meta and Capability simulations may run later or in background, but they are not required for the first focused implementation pass unless release confidence is claimed.
