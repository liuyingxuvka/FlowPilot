## Why

A live ProjectRadar FlowPilot run exposed a long-chain control-plane miss after
the route correctly redesigned repeated missing-authorized-material failures
into a v28 handoff bridge. The new v28 worker result produced a PM-readable
authorized receipt handoff, and packet-local FlowGuard passed that result.
However, final return preflight still reported older repair-chain blockers as
current because several early `repair_packet_open` blockers pointed at repair
packets that had already become accepted and noncurrent.

The bug is not a need for a new material subsystem or a larger route-node
field mesh. FlowPilot already has `current_handoff_contract`,
`authorized_result_reads`, route mutation state, semantic blockers, and
recursive decomposition gates. The missing piece is lifecycle coverage across
the whole chain: old same-family repair blockers must collapse when route
replacement makes them noncurrent, and downstream material authorization must
use the existing runtime authorized-read path instead of summaries or
historical artifacts.

## What Changes

- Treat accepted or otherwise noncurrent repair packets as non-current
  blockers during final return preflight.
- Extend route mutation cleanup so same-family old repair blockers are
  superseded when a replacement route resolves the same missing-information
  family, even if the mutation only names the most recent affected packets.
- Strengthen existing FlowGuard blocker-repair and information-flow coverage
  for stale final-preflight blockers and downstream handoff consumption.
- Add focused runtime tests for final-preflight currentness and same-family
  route-mutation blocker collapse.
- Add focused model/test alignment evidence so packet-local FlowGuard passes
  cannot be mistaken for whole-lifecycle completion.
- Update existing PM, Reviewer, and FlowGuard Operator cards to make the
  lifecycle obligation explicit without adding a separate PM display plan or
  broad new per-node fields.

## Impact

- `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py`
- `simulations/flowpilot_blocker_repair_information_flow_model.py`
- `simulations/run_flowpilot_blocker_repair_information_flow_checks.py`
- `simulations/flowpilot_project_control_information_flow_model.py`
- FlowPilot model-test alignment sources and focused runtime tests
- Existing FlowPilot PM/Reviewer/FlowGuard Operator cards
- Topology, install-sync, and local install validation after implementation
