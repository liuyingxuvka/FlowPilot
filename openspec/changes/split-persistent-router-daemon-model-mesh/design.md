# Design

## Boundary

The monolithic `flowpilot_persistent_router_daemon` result remains runnable and
continues to cover the full abstract daemon contract. The parent hierarchy does
not consume it directly as a thin child. Instead, the parent consumes four
focused FlowGuard children whose contracts reattach to the `router_daemon_resume`
partition.

## Child Evidence

Each child model is an executable FlowGuard classification model. The state
space stays small because each child covers one contract family and known-bad
variants for that family, rather than replaying all daemon branches together.

The four child evidence ids are:

- `flowpilot_daemon_startup_lock`
- `flowpilot_daemon_controller_actions`
- `flowpilot_daemon_wait_liveness`
- `flowpilot_daemon_terminal_projection`

## Parent Reattachment

The `router_daemon_resume` partition consumes these child result ids alongside
`flowpilot_router_loop`, `flowpilot_daemon_reconciliation`, and
`flowpilot_route_replanning_policy`.

The large compatibility model is still executed by smoke for regression
awareness, but it is no longer parent thin-child evidence.
