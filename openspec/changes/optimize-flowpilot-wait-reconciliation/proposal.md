## Why

FlowPilot already has packet batches, direct ACKs, active-holder leases, and PM role-work requests, but live runs can still idle because returned packet results are not reconciled before the Controller chooses another wait action. This change reduces mechanical wait time while preserving sealed-packet boundaries, PM/reviewer gates, and FlowGuard-first safety.

## What Changes

- Add durable wait reconciliation before Router wait decisions so existing ACKs, result envelopes, and controller status packets are consumed before another stale wait is emitted.
- Add per-packet partial batch accounting for material scan, research, current-node, and PM role-work batches.
- Add dependency-aware continuation so the Router can execute non-dependent work while blocking packet results are still pending.
- Broaden active-holder fast-lane handling from current-node packets to material scan, research, and PM role-work packets when the Router knows the live holder.
- Tighten prompt cards so PMs and roles classify packet dependency as `blocking`, `advisory`, or `prep-only`, and use only Router-authorized return events.
- Update FlowGuard models before production logic changes so stale waits, unsafe partial advancement, event-authority drift, and advisory/blocking mistakes are caught first.
- Preserve sealed-body privacy: Controller-facing status remains metadata-only and cannot summarize sealed packet contents.

## Capabilities

### New Capabilities
- `wait-reconciliation`: Router reconciles durable packet/ACK/result/status evidence before waiting again.
- `partial-batch-accounting`: Parallel batches track each packet independently and expose missing roles without treating the whole batch as unknown.
- `dependency-aware-continuation`: Router may continue non-dependent work while pending blocking/advisory packets are unresolved, without crossing protected gates.

### Modified Capabilities
- None. No existing OpenSpec capabilities are present in this repository.

## Impact

- Affected runtime code:
  - `skills/flowpilot/assets/flowpilot_router.py`
  - `skills/flowpilot/assets/packet_runtime.py`
  - `skills/flowpilot/assets/role_output_runtime.py` if event-authority validation needs shared helpers
- Affected prompt/card assets:
  - PM phase cards for material scan, research package, current-node loop, and PM role-work request
  - worker/officer/reviewer role cards that receive packet or active-holder instructions
- Affected schemas/templates:
  - packet ledger, packet envelope, result envelope, controller status packet, execution frontier, and activity events
- Affected models/tests:
  - FlowGuard models under `simulations/`
  - router runtime tests under `tests/test_flowpilot_router_runtime.py`
  - packet runtime and card coverage tests
- No remote GitHub sync is part of this change. Final sync is local install, local repository files, and local git only.
