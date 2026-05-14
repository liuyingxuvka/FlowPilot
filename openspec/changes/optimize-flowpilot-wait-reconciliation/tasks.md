## 1. Paper Plan And Baseline Safety

- [x] 1.1 Keep `docs/flowpilot_wait_reconciliation_optimization_plan.md` as the ordered implementation and risk table for this change.
- [x] 1.2 Verify real FlowGuard import with `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"`.
- [x] 1.3 Inspect `git status --short --branch` before each implementation slice and avoid unrelated files.
- [x] 1.4 Start a FlowGuard adoption note for the model-first wait reconciliation change.

## 2. FlowGuard Model Coverage Before Runtime Edits

- [x] 2.1 Extend `simulations/flowpilot_control_plane_friction_model.py` with stale-wait, metadata-only status, and duplicate-reconciliation hazards.
- [x] 2.2 Extend `simulations/flowpilot_parallel_packet_batch_model.py` with member-level partial return, missing-role summary, protected-join, and non-dependent status/relay scenarios.
- [x] 2.3 Extend `simulations/flowpilot_decision_liveness_model.py` with blocking/advisory/prep-only continuation and terminal advisory-resolution scenarios.
- [x] 2.4 Extend `simulations/flowpilot_router_loop_model.py` with active-holder lease coverage for material, research, and PM role-work packets.
- [x] 2.5 Extend event-contract/capability models to cover dynamic `allowed_external_events` for partial batch and role-work returns.
- [x] 2.6 Run known-bad model checks and confirm the model can catch R1-R12 from the plan table.
- [x] 2.7 Run intended-design model checks and confirm the optimized plan passes before production edits.

## 3. Runtime Slice 1: Durable Wait Reconciliation

- [x] 3.1 Add Router helpers that scan durable packet ledger, ACK records, result envelopes, and controller status packets before wait selection.
- [x] 3.2 Make reconciliation idempotent by batch id, packet id, request id, role, and result target.
- [x] 3.3 Add router runtime tests for existing result evidence being consumed before stale wait.
- [x] 3.4 Run the targeted control-plane model and router tests for slice 1.

## 4. Runtime Slice 2: Partial Batch Accounting And Status

- [x] 4.1 Add member-level batch status fields and derived returned/missing counts.
- [x] 4.2 Update material, research, current-node, and PM role-work paths to refresh partial batch status.
- [x] 4.3 Update status summary generation to name returned and missing roles accurately while staying metadata-only.
- [x] 4.4 Add tests for A returned/B missing and stale expected-role summary repair.
- [x] 4.5 Run the targeted parallel-batch, control-plane, router, and packet tests for slice 2.

## 5. Runtime Slice 3: Active-Holder Fast Lane Expansion

- [x] 5.1 Generalize active-holder lease issuing beyond current-node packets.
- [x] 5.2 Add material scan, research, and PM role-work active-holder ACK/progress/result acceptance paths.
- [x] 5.3 Keep fallback Controller relay behavior when no live holder is known.
- [x] 5.4 Add wrong-holder, stale-run, wrong-packet, no-live-agent, and expanded-packet lease assertions.
- [x] 5.5 Run router-loop and packet-runtime tests for slice 3.

## 6. Runtime Slice 4: Dependency-Aware Continuation

- [x] 6.1 Add dependency-class and blocked-gate metadata to packet and role-work request handling.
- [x] 6.2 Add ready-action selection that allows non-dependent work while unresolved dependencies remain pending.
- [x] 6.3 Block protected PM/reviewer/material gates until all blocking dependencies are resolved.
- [x] 6.4 Block terminal closure until advisory work is absorbed, canceled, superseded, or explicitly carried forward.
- [x] 6.5 Add tests for advisory pending continuation, advisory closure block, blocking gate block, and prep-only continuation.
- [x] 6.6 Run decision-liveness, event-contract, event-capability, and router tests for slice 4.

## 7. Prompt, Template, And Documentation Updates

- [x] 7.1 Update PM cards for material scan, research package, current-node loop, and PM role-work request with dependency class, join policy, and allowed event instructions.
- [x] 7.2 Update worker/officer/reviewer-facing packet instructions with packet-type-agnostic active-holder instructions and Router-supplied event requirements.
- [x] 7.3 Update packet ledger, packet envelope, result envelope, controller status packet, and execution frontier templates.
- [x] 7.4 Update protocol/schema docs and refresh optimization plan docs.
- [x] 7.5 Run card instruction coverage, prompt isolation, event-contract, and install checks.

## 8. Final Local Verification And Sync

- [x] 8.1 Run the practical model/test suite for changed areas plus `scripts/check_install.py`.
- [x] 8.2 Sync repo-owned FlowPilot assets into the local installed skill with `scripts/install_flowpilot.py --sync-repo-owned --json`.
- [x] 8.3 Re-run `scripts/check_install.py` after local install sync.
- [x] 8.4 Update the FlowGuard adoption note with commands, results, findings, skipped checks, and next action.
- [x] 8.5 Stage and commit local git changes only; do not push to GitHub.
