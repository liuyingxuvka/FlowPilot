## Context

The repaired material flow already writes `current_generation_id`, active material batch metadata, and generation-scoped PM disposition evidence. The remaining failure is that some runtime decisions can still read old run-wide material flags first.

That makes a stale state look complete even when the active batch says the current repair generation is still registered, unrelayed, and missing worker results.

## Goals

- Keep the existing material repair transaction and batch files.
- Add one material progress projection at the Router decision boundary.
- Treat run-wide material flags as cache/display state for material repair generations, not as the authority.
- Avoid a broad rewrite of packet, PM disposition, or Controller action flows.

## Non-Goals

- Do not introduce a new repair subsystem or transaction registry.
- Do not rewrite the packet ledger format.
- Do not migrate historical `.flowpilot` runs as part of this source-code fix.
- Do not weaken existing generation-scoped PM disposition or packet result authority checks.

## Design

### Active Batch Projection

Add a small helper near material packet next-action selection that reads:

- `material/material_scan_packets.json`
- `packet_batches/active_material_scan.json`
- the active batch file referenced by that index

The helper derives:

- current packet count
- relayed count
- returned result count
- all-results-returned status
- current generation id
- current repair transaction id
- whether PM disposition exists for this active batch

`_next_material_packet_action` uses this projection before consulting run-wide flags. If the projection exists and points at a current repair generation, the active batch values decide relay, wait, result relay, and PM disposition wait.

### Stale Save Policy

Keep the existing stale-save merge for ordinary monotonic flags, but add a material-generation exception. If the loaded/current state cleared material progress flags for a newer active generation, an older foreground save must not restore `material_scan_packets_relayed`, `worker_packets_delivered`, `worker_scan_results_returned`, `material_scan_results_relayed_to_pm`, or `material_scan_result_disposition_recorded`.

### Role-Output Reconciliation

For generation-scoped material events, scoped identity must be checked before the run-wide event flag shortcut. A stale PM disposition role-output entry from an older batch can close a wait only if its scoped identity matches the current active batch/generation and body hash.

### Dispatch Block Metadata

Material dispatch block records already can carry `repair_transaction_id`. Ensure protocol-blocker records written from material dispatch checks include the current active repair transaction when one is present, so stale dispatch blockers are visibly superseded.

## Validation

- Focused unit/runtime tests for active repair batch state overriding stale material flags.
- Focused stale-save merge test for material progress flags.
- Focused role-output bridge test for stale PM disposition not short-circuiting current generation.
- FlowGuard control-plane friction checks with the new material generation hazards.
- Sequential local install sync and install freshness checks.
