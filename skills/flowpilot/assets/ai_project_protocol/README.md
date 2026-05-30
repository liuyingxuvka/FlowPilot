# AI Project Protocol Kernel

This directory contains the clean protocol kernel for long-running AI project
execution. It is intentionally separate from the existing FlowPilot runtime
state and compatibility routes.

The kernel answers one question:

How can a project be split into isolated AI work packets, routed through
host-supported role bindings, reviewed independently, checked with FlowGuard,
and closed only when fresh evidence connects the user goal to the delivered
result?

## Files

- `protocol_contract.md`: readable contract and operating model.
- `schema_examples.json`: minimal JSON examples for ledger, lease, packet,
  result, review, FlowGuard work order, and final closure records.
- `flowguard_route_scheduler.json`: route table for selecting the correct
  FlowGuard skill by risk type.
- `stress_testing.md`: deterministic fake-AI, multi-round, historical replay,
  seeded long-run, and TestMesh evidence contract.

## Legacy Boundary

The old FlowPilot source is backed up under
`backups/ai-project-protocol-legacy-snapshot-20260529/`. Old startup visuals,
icons, and known failure cases may be reused as references.

Old runtime state, old route compatibility logic, historical role topologies,
and old validation evidence are not source of truth for this protocol.
