## 1. Grounding and Inventory

- [x] 1.1 Verify real FlowGuard import, OpenSpec change validity, clean git state, and current peer-agent coordination boundaries.
- [x] 1.2 Inventory current model-test alignment obligations, branch kinds, ordinary test evidence, synthetic trace packs, and background evidence contracts.
- [x] 1.3 Identify current full-coverage blockers and confirm whether they are structure split work, missing test ownership, stale evidence, or untestable external AI semantics.

## 2. Coverage Matrix Implementation

- [x] 2.1 Add a generated synthetic agent coverage matrix that consumes current FlowGuard model-test alignment plans and explicit synthetic trace branch rows.
- [x] 2.2 Add coverage gate tests for missing obligation owners, missing branch kinds, invalid evidence status, progress-only background evidence, and synthetic evidence overclaiming.
- [x] 2.3 Register the coverage matrix gate in the fast test tier so future changes cannot bypass it.

## 3. Synthetic Trace Expansion

- [x] 3.1 Add or extend trace rows and tests for route mutation and stale old evidence ownership.
- [x] 3.2 Add or extend trace rows and tests for resume/recovery boundaries and ambiguous worker state.
- [x] 3.3 Add or extend trace rows and tests for role-output authority, PM disposition, raw result rejection, and fixture/live evidence separation.
- [x] 3.4 Add or extend trace rows and tests for background model evidence final-artifact requirements.

## 4. Structure Split Blocker Closure

- [x] 4.1 Split `flowpilot_router_controller_scheduler_receipts_packet_folds.py` into compatibility-preserving helper modules and record split metadata.
- [x] 4.2 Split or slim `flowpilot_router_work_packets_current_node_relay.py` while preserving public imports and relay behavior.
- [x] 4.3 Split or slim `flowpilot_runtime_commands.py` while preserving public CLI/runtime behavior.
- [x] 4.4 Update FlowGuard split metadata so completed splits no longer count as deferred coverage blockers.

## 5. Validation and Evidence Refresh

- [x] 5.1 Run focused synthetic coverage and trace replay tests.
- [x] 5.2 Run focused packet/runtime/router/model-test-alignment tests affected by the trace matrix and split work.
- [x] 5.3 Run the fast test tier and refresh generated FlowGuard evidence JSON.
- [x] 5.4 Run heavyweight meta and capability model regressions in background and inspect final out/err/combined/exit/meta artifacts.
- [x] 5.5 Confirm the full diagnostic has no unresolved actionable findings or record a concrete blocker.

## 6. Sync and Finalization

- [x] 6.1 Recheck git state for peer-agent writes before install sync.
- [x] 6.2 Synchronize the installed local FlowPilot skill from the validated repository state.
- [x] 6.3 Run install audit and install checks serially after sync.
- [x] 6.4 Validate the OpenSpec change, update tasks to complete, and commit the final repository state.
- [x] 6.5 Run predictive-KB postflight and record any reusable lesson or route gap.
