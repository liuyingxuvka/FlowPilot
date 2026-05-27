## Context

FlowPilot has two legal paths for many Router-owned effects:

- the direct `apply_action` path, where the Router invokes the action handler and can set the Router-owned flag immediately; and
- the async Controller ledger path, where Controller performs host-visible work and writes a `done` receipt that Router must reconcile back into state.

The material scan failure showed a gap between those paths. `_apply_relay_material_scan_packets` can relay packets, issue leases, mark the batch relayed, and set `material_scan_packets_relayed`. The async receipt reconciler did not have an equivalent fold for `relay_material_scan_packets`, so it returned `unsupported_stateful_controller_receipt` even though packet ledger, batch, relay history, packet-open, and active-holder evidence existed.

## Goals / Non-Goals

**Goals:**

- Add one shared evidence-fold mechanism for evidence-backed packet/result relay receipts.
- Keep sealed body boundaries intact: receipt folding may inspect envelopes, ledgers, batches, leases, relay history, and hashes, but not packet or result body contents.
- Cover the same-family relay actions for material scan, research, current-node, and PM role-work packet/result relays.
- Make folding idempotent so repeated daemon ticks reuse existing evidence without duplicating relay history, leases, or batch counters.
- Let downstream waits proceed when relay evidence proves workers already have the packets, even if the aggregate flag was stale before reconciliation.

**Non-Goals:**

- Do not redesign packet runtime, Controller action ledger storage, repair transactions, or sealed-body contracts.
- Do not make Controller receipts sufficient by themselves; Router-visible evidence remains required.
- Do not waive worker result requirements. A packet-open/ACK proves dispatch, not completion.
- Do not publish or release as part of this change.

## Decisions

1. **Use a registry, not per-action special cases.**

   Add a small Router-owned registry that maps each evidence-backed relay action to:
   - the postcondition flag it owns;
   - the packet family or packet-record source;
   - whether evidence proves packet dispatch or result relay;
   - which batch/index/ledger evidence must be present.

   This keeps the repair root-level without building a large framework.

2. **Fold from existing Router-visible evidence before retry/blocker.**

   The receipt path first attempts a registered fold. If the batch says relayed, packet envelopes have Controller relay history, leases exist for packet dispatch, or result envelopes have been relayed to the expected recipient for result relay, Router sets the corresponding flag and reconciles the row. Retry/blocker is only for missing or contradictory evidence.

3. **Respect in-progress worker work.**

   If packet relay evidence exists and workers have opened or ACKed packets, Router must wait for remaining results instead of reissuing the relay. ACK and packet-open remain read/work-start evidence only; they never satisfy worker completion.

4. **Use focused model and tests as the gate.**

   The new FlowGuard model catches the abstract failure class and a source-contract audit catches current direct-flag relay actions without registered folds. Runtime tests cover the material scan instance that failed in the latest run.

## Risks / Trade-offs

- **Risk: false positives from partial evidence** -> Mitigation: dispatch folds require packet relay evidence and, for packet dispatch, batch/lease or packet-open evidence; result relay folds require result-envelope relay evidence.
- **Risk: duplicate ledger writes during repeated ticks** -> Mitigation: folds reuse existing records and set flags idempotently without invoking the relay action handler.
- **Risk: overly broad source audit** -> Mitigation: the audit is limited to evidence-backed packet/result relay actions, not every direct handler that writes a flag.
- **Risk: active peer-agent edits** -> Mitigation: edits stay scoped to FlowPilot runtime receipt/packet helpers, focused tests, OpenSpec artifacts, FlowGuard model results, and install evidence.

## Migration Plan

1. Add the OpenSpec deltas for receipt evidence folding and related capabilities.
2. Keep the new FlowGuard model red against current code until runtime folding is implemented.
3. Implement the shared evidence-fold registry and hook it into Controller receipt reconciliation before missing-postcondition repair scheduling.
4. Add targeted runtime tests for material scan dispatch folding from packet/batch/lease/open evidence.
5. Run focused FlowGuard/model/test checks, then background meta/capability regressions.
6. Sync the installed FlowPilot skill and run install audits.
7. Commit only this scoped repair and generated evidence, preserving peer README/hero edits.
