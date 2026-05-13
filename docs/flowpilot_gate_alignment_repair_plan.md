# FlowPilot Gate Alignment Repair Plan

## Scope

This plan repairs the FlowPilot gate-alignment failure where a legacy/general
role output, PM repair follow-up, or PM role-work result can be recorded without
satisfying the current gate that Router is waiting on.

Runtime code must not treat "event recorded" as equivalent to "current gate
closed." A gate closes only when a concrete gate pass/block event or a mapped
PM role-work result satisfies the active gate contract.

## Optimization Order

| Step | Change | Concrete work | Done when |
| --- | --- | --- | --- |
| 1 | Declare gate contracts | Add machine-readable gate contract metadata for gate-bearing system cards and waits. | Delivered card envelopes and wait actions expose the active gate id, pass events, block events, required flag, and legacy non-completion events. |
| 2 | Separate legacy/general events from gate completion | Keep legacy events registered for old artifacts, but remove them from current expected gate waits and terminal gate completion checks. | `product_officer_model_report` can be recorded only as legacy metadata and cannot close `product_architecture_modelability`. |
| 3 | Enforce active gate satisfaction | Add a shared Router predicate that checks whether an event satisfies the active gate before it can be treated as a gate outcome. | Router continues only after the active gate flag is set by a concrete pass/block event or mapped result. |
| 4 | Bind PM role-work repairs to gates | Preserve PM role-work as a repair/follow-up channel, but require gate-targeted role-work absorption to map to a concrete gate event before the original gate is considered closed. | PM absorbing a role-work result can close the request, but not the original gate unless it declares and satisfies the mapped gate event. |
| 5 | Verify and sync locally | Run focused FlowGuard, router/runtime tests, install audit, then sync the local installed FlowPilot skill. | Model, targeted runtime tests, install check, and local sync checks pass; no remote GitHub push is performed. |

## Bug Risks To Catch Before Runtime Changes

| Risk | What could go wrong | FlowGuard scenario/check |
| --- | --- | --- |
| 1 | A gate card is delivered without a clear machine-readable completion contract. | `gate_card_without_completion_contract` |
| 2 | A legacy/general report is accepted as if it completed the gate. | `legacy_event_accepted_without_required_gate_flag` |
| 3 | A control blocker is marked resolved by a repair follow-up event that did not satisfy the original gate. | `pm_repair_resolves_blocker_without_gate_event` |
| 4 | A PM role-work result is absorbed but never mapped into the active gate pass/block event. | `pm_role_work_result_not_mapped_to_current_gate` |
| 5 | A role-output report guesses or reuses an event outside the live Router wait. | `role_guesses_unknown_event`, `registered_event_not_currently_allowed` |
| 6 | Mechanical role-output validation is mistaken for Router acceptance or gate completion. | `mechanical_green_used_as_router_acceptance` |
| 7 | A production change reintroduces no-legal-next-action after a legacy event. | dynamic return-path live projection historical/current findings |

## Minimum Runtime Fix Shape

1. Add a compact gate-contract registry in Router code for current gate-bearing
   pre-route waits.
2. Attach the relevant gate contract to card delivery metadata and the generated
   `await_role_decision` action.
3. Filter expected gate waits so legacy events remain registered but are not
   treated as current gate-completion choices.
4. Ensure terminal group completion ignores events with
   `terminal_gate_outcome=false`.
5. Make PM role-work result decisions gate-aware only when a request declares a
   target gate contract; otherwise role-work absorption remains ordinary PM
   evidence absorption.

## Validation Plan

| Stage | Commands |
| --- | --- |
| Model preflight | `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` |
| Model checks | `python simulations/run_flowpilot_dynamic_return_path_checks.py --project-root . --json-out simulations/flowpilot_dynamic_return_path_results.json` |
| Syntax | `python -m py_compile simulations/flowpilot_dynamic_return_path_model.py simulations/run_flowpilot_dynamic_return_path_checks.py skills/flowpilot/assets/flowpilot_router.py tests/test_flowpilot_router_runtime.py tests/test_flowpilot_role_output_runtime.py` |
| Focused runtime tests | Targeted `tests.test_flowpilot_router_runtime` and `tests.test_flowpilot_role_output_runtime` cases for product architecture gate and router-supplied role-output authority. |
| Install/sync | `python scripts/check_install.py`, `python scripts/install_flowpilot.py --sync-repo-owned --json`, `python scripts/audit_local_install_sync.py --json`, `python scripts/install_flowpilot.py --check --json` |
