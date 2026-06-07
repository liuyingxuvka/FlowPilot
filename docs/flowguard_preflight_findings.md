# FlowPilot Meta-Process Preflight Findings

Date: 2026-06-07

## Current Finding Set

The active FlowPilot continuation model is manual lifecycle resume plus
foreground duty from the new `flowpilot_new.py` runtime. Heartbeat automation
and fixed role-set restoration are not part of the current formal FlowPilot
surface. The unsupported external recovery layer is no longer part of the
supported controller, PM, reviewer, installation, or lifecycle surface.

Current source and runtime checks must preserve these boundaries:

- the project manager may ask for continuation capability evidence, but may not
  require a unsupported recovery layer before route work can continue;
- the controller wakes only into the packet control plane and must ask PM for a
  `PM_DECISION` before dispatching work;
- the controller may read packet/result envelopes only; packet/result bodies
  are physical files for the addressed role, reviewer, or PM. Missing packet
  files, controller handoff text containing body content, controller body
  access, body execution, wrong-role relabelling, hash mismatch acceptance, and
  stale body reuse are control-plane blockers;
- manual resume must be recorded through
  `flowpilot_new.py resume --reason manual_resume`, then the Controller must
  follow the returned lifecycle guard, foreground duty, packet/lease state, and
  status projection before deciding what can proceed. Role dispatch is
  on-demand: only the currently requested packet responsibility may be opened
  through `dispatch-current-role`; fixed role-set prewarming and stale role
  reports are not current authority;
- router direct-dispatch validation is mandatory before PM-authored work
  packets reach a worker. Existing or fresh worker results must return to the
  PM for a recorded package-result disposition before any PM-built formal
  gate package is released to the reviewer;
- startup display and status evidence are Runtime/Router mechanical evidence,
  not a Reviewer startup gate. If the user-facing acknowledgement is disabled
  or the host cannot open the current background or parallel role surface,
  Runtime records the structured stop or blocker instead of continuing on a
  foreground-only route;
- old recovery scripts, prompts, and templates must remain absent from the
  active tree. `scripts/check_install.py` and
  `scripts/audit_local_install_sync.py` both enforce that absence.

## Modeled Risk Boundary

This preflight models the project-control workflow for the `flowpilot` Codex
skill. The current model boundary covers:

- acceptance contract freeze and route creation;
- PM-owned material research packages before product or route decisions can use
  unresolved sources, experiments, mechanisms, or validation claims;
- packet control plane handoff among controller, PM, reviewer, FlowGuard operators, and
  workers;
- manual lifecycle resume, foreground duty, and on-demand role assignment
  behavior;
- display and status startup behavior for current chat route signs;
- Runtime/Router mechanical startup audit followed by PM startup intake release;
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

Commands run during the 2026-06-07 strict current-contract maintenance pass:

```powershell
python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"
python -c "import importlib.metadata as m; print(m.version('flowguard'))"
python -m flowguard project-audit --root .
python simulations\run_meta_checks.py --full --force
python simulations\run_capability_checks.py --full --force
python simulations\run_flowpilot_field_mesh_checks.py
python simulations\run_flowpilot_field_contract_checks.py
python simulations\run_flowpilot_model_test_alignment_checks.py
python simulations\run_flowpilot_router_facade_split_checks.py
python -m unittest -v tests.test_flowpilot_high_standard_control_flow
python -m unittest -v tests.test_flowpilot_role_output_runtime
python -m unittest -v tests.test_flowpilot_new_entrypoint
python scripts\flowguard_project_topology.py build
python scripts\flowguard_project_topology.py check
python scripts\install_flowpilot.py --sync-repo-owned --json
python scripts\audit_local_install_sync.py --json
python scripts\install_flowpilot.py --check --json
python scripts\check_install.py --json
```

Results:

- FlowGuard schema version: `1.0`;
- FlowGuard package version: `0.40.12`;
- install self-check: passed, including unsupported-path absence checks;
- local install sync audit: passed, including source-fresh installed skill
  checks;
- meta and capability full parent checks passed with current layered evidence;
- field mesh and field contract checks passed, including stale old-field
  disposal;
- model-test alignment passed with full source/test coverage for the registered
  current surfaces;
- router facade split checks passed after the current child-module split;
- strict role output, high-standard control-flow, and entrypoint regressions
  passed;
- topology build and check passed.

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
follow the current finding set above rather than reconstructing unsupported recovery
behavior from old logs.
