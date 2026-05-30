# FlowPilot Protocol Kernel

This directory contains the clean protocol kernel for long-running FlowPilot
execution. It is intentionally separate from non-authoritative runtime state
and rejected transition paths.

The kernel answers one question:

How can a project be split into isolated work packets, routed through
host-supported role bindings, reviewed independently, checked with FlowGuard,
and closed only when fresh evidence connects the user goal to the delivered
result?

## Files

- `protocol_contract.md`: readable contract and operating model.
- `schema_examples.json`: minimal JSON examples for ledger, lease, packet,
  result, review, FlowGuard work order, and final closure records.
- `flowguard_route_scheduler.json`: route table for selecting the correct
  FlowGuard skill by risk type.
- `stress_testing.md`: deterministic actor, multi-round, recorded replay,
  seeded long-run, and TestMesh evidence contract.

## Reference Boundary

The prior FlowPilot source is backed up under
`backups/flowpilot-protocol-reference-snapshot-20260529/`. Startup visuals,
icons, and known failure cases may be reused as references.

Prior runtime state, unsupported transition logic, fixed role topologies, and
prior validation evidence are not source of truth for this protocol.
