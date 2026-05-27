## Why

FlowPilot's Controller packet relay fix closed the path-only relay hole, but the
same control-plane incident class still has broader root causes: action identity
can collapse distinct packet/request work into one closed row, failed host
delivery can be recorded as done, active-holder leases can trust stale agent IDs,
packet ledger writes can leave corrupt JSON behind, and material-gate evidence
can advertise reviewer-readable result bodies without a runtime-backed open path.

## What Changes

- Bind Controller action and scheduler identity to batch, request, packet, and
  target role fields so distinct control work cannot reuse a closed row.
- Reject `done` Controller receipts that themselves report failed host/message
  delivery.
- Harden packet ledger writes with per-write temporary files, a write lock,
  readback verification, and recoverable corrupt-ledger handling.
- Require active-holder leases to include current live role evidence from the
  run's crew ledger.
- Keep material artifact maps and PM formal gate packages honest about result
  body authority: reviewer-visible packages may cite envelopes and summaries,
  but raw result body access must be backed by runtime relay/open evidence, and
  source result self-checks must be parseable before PM releases a formal gate
  package.

## Impact

- Runtime helpers: `packet_runtime_schema.py`, `packet_runtime_ledger.py`,
  `packet_runtime_active_holder_lease.py`, `flowpilot_runtime_commands.py`.
- Router control plane: controller identity helpers, scheduler receipt writes,
  packet receipt evidence folds, material artifact map and formal package
  writers.
- Tests and models: focused unit/runtime tests plus the control-plane friction
  FlowGuard model and relevant router/packet regressions.
