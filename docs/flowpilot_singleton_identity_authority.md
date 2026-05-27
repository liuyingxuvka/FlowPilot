# FlowPilot Singleton Identity Authority

FlowPilot has intentional plurality and scoped singleton authority at the same
time. Multiple runs, background Flow blocks, historical packets, and replayed
events can coexist. A duplicate becomes unsafe only when two authorities claim
the same declared singleton scope without replay, repair, reissue,
supersession, quarantine, or stale disposition.

The executable authority gate is:

```powershell
python simulations/run_flowpilot_singleton_identity_checks.py --json-out simulations/flowpilot_singleton_identity_results.json
```

The checker records:

- the singleton authority matrix;
- legal replay and illegal duplicate hazards;
- known-bad sanity checks for duplicate daemon writers, active holder
  conflicts, package body conflicts, replacement without old-object
  disposition, stale material generation flags, ACK-only output completion,
  final progress-only closure, and missing live ledgers;
- a read-only live `.flowpilot` audit for the current run.

## Authority Matrix

| Object family | Singleton scope | Canonical owner | Identity / generation | Duplicate rule |
| --- | --- | --- | --- | --- |
| Parallel FlowPilot runs | Per targeted run operation | Router/Controller target selection | `run_id` or `run_root`; current pointer is UI focus | Multiple runs are legal only when operations remain explicitly targeted. |
| Router daemon writer | One writer per run root | Router daemon lock | `run_id + run_root + owner pid`; lock status and tick | A second live writer is rejected or routed through stale-lock recovery. |
| Packet active holder | One holder per packet lease | Packet runtime active-holder lease | `packet_id + holder_role + holder_agent_id`; route/frontier version | Same holder replay is idempotent; wrong role, agent, or stale route is rejected. |
| PM package disposition | One semantic disposition per package identity | PM package disposition writer | `batch_id + packet_ids + packet_generation_id`; body hash is conflict evidence | Same body replay is idempotent; different body conflicts unless repair creates a new identity. |
| Route replacement | One current route/frontier authority after activation | Route mutation activation | `route_version + affected siblings + repair_transaction_id` | Old packets/evidence/nodes must be superseded, stale, quarantined, migrated, or blocking. |
| Material progress generation | One progress authority per material generation | Material work-packet lifecycle | `material_batch_id + packet_ids`; `current_generation_id` | Old run-wide progress flags cannot close current generation work. |
| ACK/output completion | Receipt wait and semantic output are separate surfaces | Wait reconciliation and role-output runtime | ACK id for receipt; result body hash for output | ACK replay settles receipt only; output needs durable evidence or disposition. |
| Final closure evidence | One closure claim boundary per final ledger | Terminal ledger and PM closure approval | Effective route nodes, gate ids, evidence ids; route/closure version | Progress-only, stale, or superseded evidence cannot close the final ledger. |

## Confidence Boundary

`flowpilot_singleton_identity_results.json` may report `full_closure_ok=true`
only when the model graph passes, known-bad hazards are detected, the matrix is
complete, and the live audit has no risky or evidence-insufficient singleton
surface. If the live audit finds an active-run issue, the checker reports
scoped confidence and does not repair the run.
