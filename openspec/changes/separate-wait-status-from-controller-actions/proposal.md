## Why

FlowPilot can currently project pure wait states, such as waiting for a role return or scope reconciliation, as Controller action rows. Those rows are not executable work, and when they occupy the current action slot they can hide Router-owned obligations that would otherwise clear the wait.

## What Changes

- Separate executable Controller actions from passive wait status.
- Keep wait information visible through router daemon status, current status summaries, scheduler metadata, and continuous standby, instead of ordinary Controller action rows.
- Treat Controller action rows as a work board containing only actions that the Controller can actually perform or receipt.
- Keep continuous standby as the foreground duty when the ordinary Controller work board is empty and FlowPilot is still waiting.
- When a wait target reminder or liveness probe becomes due, create a distinct generic executable Controller row for the current waiting role instead of relying on a reviewer-specific or chat-only instruction.
- Add FlowGuard coverage for pure wait rows entering the Controller queue, executable actions being accidentally hidden by waits, and standby losing the wait target.

## Capabilities

### New Capabilities
- `controller-action-queue`: Defines the boundary between executable Controller work rows and Router-owned wait/status projections.

### Modified Capabilities

## Impact

- Affected runtime: `skills/flowpilot/assets/flowpilot_router.py`.
- Affected tests: focused Controller/router runtime tests for wait projection, current-scope reconciliation, role waits, card return waits, and continuous standby.
- Affected models: focused FlowGuard daemon and two-table scheduler models that represent Controller queue versus wait status and generic wait-target reminders.
- Installation: repository-owned FlowPilot skill must be synced to the local installed skill after verification.
