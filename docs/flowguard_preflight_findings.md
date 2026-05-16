# FlowPilot Meta-Process Preflight Findings

Date: 2026-05-04

## Current Finding Set

The active FlowPilot continuation model is heartbeat-only continuation plus
explicit manual resume. The retired external recovery layer is no longer part of
the supported controller, PM, reviewer, heartbeat, installation, or lifecycle
surface.

Current source and runtime checks must preserve these boundaries:

- the project manager may ask for continuation capability evidence, but may not
  require a retired recovery layer before route work can continue;
- the controller wakes only into the packet control plane and must ask PM for a
  `PM_DECISION` before dispatching work;
- the controller may read packet/result envelopes only; packet/result bodies
  are physical files for the addressed role, reviewer, or PM. Missing packet
  files, controller handoff text containing body content, controller body
  access, body execution, wrong-role relabelling, hash mismatch acceptance, and
  stale body reuse are control-plane blockers;
- heartbeat/manual resume must load current-run state, execution frontier,
  packet ledger, and role memory before deciding what can proceed;
- router direct-dispatch validation is mandatory before PM-authored work
  packets reach a worker. Existing or fresh worker results must return to the
  PM for a recorded package-result disposition before any PM-built formal
  gate package is released to the reviewer;
- Cockpit UI unavailability is a startup display-surface fallback, not proof
  that route execution is blocked. If the user requested Cockpit and the UI
  cannot open, PM records the fallback and the reviewer independently verifies
  the display evidence before PM opens the start gate;
- old recovery scripts, prompts, and templates must remain absent from the
  active tree. `scripts/check_install.py` and
  `scripts/audit_local_install_sync.py` both enforce that absence.

## Modeled Risk Boundary

This preflight models the project-control workflow for the `flowpilot` Codex
skill. The current model boundary covers:

- acceptance contract freeze and route creation;
- PM-owned material research packages before product or route decisions can use
  unresolved sources, experiments, mechanisms, or validation claims;
- packet control plane handoff among controller, PM, reviewer, officers, and
  workers;
- route heartbeat/manual resume behavior;
- display-surface startup behavior for Cockpit or chat route signs;
- reviewer factual checks before PM start-gate release;
- child-skill fidelity gates and capability routing;
- planning-quality gates for PM planning profiles, child-skill standard
  contracts, route/node/work-packet projection, reviewer hard-blindspot
  blocking, and simple-task over-templating;
- reviewer active-challenge gates that require each human-like reviewer report
  to go beyond the PM checklist with scope restatement, explicit and implicit
  commitments, failure hypotheses, task-specific challenge actions, direct
  evidence or approved waiver, blocker triage, and PM reroute/repair request
  when hard issues are found;
- route mutation repair/replacement, including sibling branch replacement,
  stale sibling evidence, old current-node packet supersession before route
  recheck, replay-scope projection, and final-ledger blocking before same-scope
  replay;
- terminal closure, final route-wide gate ledgers, residual-risk review,
  defect-ledger/role-memory/quarantine reconciliation, and recursive
  parent/module route entry.

## Latest Validation

FlowGuard applicability decision: `use_flowguard`.

Commands run during the 2026-05-04 cleanup and synchronization pass:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python -m py_compile scripts\audit_local_install_sync.py scripts\check_install.py scripts\install_flowpilot.py
python scripts\check_install.py
python simulations\run_meta_checks.py
python simulations\run_capability_checks.py
python simulations\run_startup_pm_review_checks.py
python simulations\run_flowpilot_recursive_closure_reconciliation_checks.py
python scripts\install_flowpilot.py --sync-repo-owned --json
python scripts\audit_local_install_sync.py --json
python scripts\install_flowpilot.py --check --json
python scripts\smoke_autopilot.py
```

Results:

- FlowGuard schema version: `1.0`;
- install self-check: passed, including retired-path absence checks;
- local install sync audit: passed, including source-fresh installed skill
  checks;
- meta model: 564071 states, 584243 edges, zero invariant failures, zero stuck
  states, zero nonterminating components;
- capability model: 534893 states, 560353 edges, zero invariant failures, zero
  stuck states, zero nonterminating components;
- startup PM-review model: passed, including hazard detection and safe-graph
  checks;
- recursive closure reconciliation model: passed, including parent/module
  traversal and dirty terminal-closure hazard detection;
- smoke autopilot: passed.

## 2026-05-16 Small Pre-Release Maintenance Note

The route mutation activation/display model now also covers
`sibling_branch_replacement`, affected sibling declarations, replay-scope
declarations, old current-node packet supersession, stale sibling evidence, and
final-ledger blocking before same-scope replay. Focused validation passed:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python simulations\run_flowpilot_route_mutation_activation_checks.py --json-out simulations\flowpilot_route_mutation_activation_results.json
python -m unittest tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_route_mutation_requires_topology_and_resets_route_hard_gates tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_route_mutation_and_final_ledger_have_required_preconditions tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_route_mutation_new_repair_transaction_is_not_swallowed_by_old_flag tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_route_mutation_supersede_strategy_does_not_require_return_to_original tests.test_flowpilot_router_runtime.FlowPilotRouterRuntimeTests.test_route_mutation_sibling_branch_replacement_blocks_old_sibling_proof
python -m unittest tests.test_flowpilot_user_flow_diagram.FlowPilotUserFlowDiagramTests.test_sibling_branch_replacement_draws_replacement_and_replay_scope tests.test_flowpilot_user_flow_diagram.FlowPilotUserFlowDiagramTests.test_supersede_replacement_marks_old_node_without_forcing_return_edge
```

The heavyweight Meta and Capability model simulations were intentionally not
run in this pass by user request. They should be treated as skipped, not
passed, until a later release-level validation run.

## Historical Note

Earlier preflight notes explored a broader recovery architecture. Those notes
are superseded by this file and by the current executable checks. New work must
follow the current finding set above rather than reconstructing retired recovery
behavior from old logs.
