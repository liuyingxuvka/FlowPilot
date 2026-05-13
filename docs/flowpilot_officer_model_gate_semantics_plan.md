# FlowPilot Officer Model Gate Semantics Plan

## Scope

This plan covers the shared semantic repair for the Product and Process
FlowGuard Officer model gates.

The Product FlowGuard Officer gate is no longer merely a product architecture
modelability check. It is the canonical product behavior model submission that
PM must accept before reviewer challenge and route planning use it.

The Process FlowGuard Officer route gate is no longer merely a route process
check. It is the canonical process route model submission that PM must accept
before Product FlowGuard route fit review and Reviewer route challenge use it.

This plan intentionally preserves the broader gate-alignment repair in
`docs/flowpilot_gate_alignment_repair_plan.md`: every gate-bearing card or wait
still needs a machine-readable contract, and PM repair/role-work results may
close a gate only by mapping to the concrete active gate outcome.

## Optimization Order

| Step | Change | Concrete work | Done when |
| --- | --- | --- | --- |
| 1 | Preserve compatibility boundary | Keep old Product `product_architecture_modelability` names and old Process `route_process_check` names as aliases. | Old active runs, old events, old artifacts, and focused tests still work. |
| 2 | Introduce canonical Product model semantics | Add Product Officer submit/block events, flags, and canonical `flowguard/product_behavior_model.json`. | New Product path says "submit product behavior model"; old modelability pass/block only aliases it. |
| 3 | Introduce canonical Process model semantics | Add Process Officer submit/repair/block events, flags, and canonical `flowguard/process_route_model.json`. | New Process path says "submit process route model"; old route process check pass/repair/block only aliases it. |
| 4 | Keep PM as model acceptance owner | Require PM acceptance after Product model submission and after Process model submission before downstream roles may use either model. | Officer submission alone cannot advance reviewer/route challenge or activation paths. |
| 5 | Write canonical and compatibility artifacts | Write canonical artifacts first, then mirror old compatibility artifacts. Read helpers prefer canonical paths and fall back to old paths. | New code has a single canonical source while old source paths remain valid. |
| 6 | Align pass/block/repair flags | Recording either canonical or compatibility event updates both canonical and compatibility flags and clears contradictory stale flags. | Wait groups cannot be stuck or contradictory after alias use. |
| 7 | Update wording and targeted tests | Update card/event summaries and tests for both canonical paths and legacy alias paths. | FlowGuard model checks, router tests, and role-output authority tests pass. |

## Bug Risks To Catch Before Runtime Changes

| Risk | What could go wrong | FlowGuard scenario/check |
| --- | --- | --- |
| 1 | Product keeps treating "modelability pass" as the canonical model completion. | `product_behavior_model_gate_uses_modelability_as_canonical_completion` |
| 2 | Product canonical or compatibility event sets only one side of the flags. | `product_behavior_model_alias_does_not_set_compatibility_flags` |
| 3 | Product model submission skips PM acceptance and lets downstream flow continue. | `product_behavior_model_submission_skips_pm_acceptance` |
| 4 | Product writes only the old modelability artifact, not the canonical model artifact. | `product_behavior_model_missing_canonical_artifact` |
| 5 | Product block aliases leave pass/block flags contradictory. | `product_behavior_model_block_alias_flags_diverge` |
| 6 | Process keeps treating "route process check pass" as the canonical model completion. | `process_route_model_gate_uses_route_check_as_canonical_completion` |
| 7 | Process canonical or compatibility event sets only one side of the flags. | `process_route_model_alias_does_not_set_compatibility_flags` |
| 8 | Process model submission skips PM acceptance and lets Product/Reviewer route checks continue. | `process_route_model_submission_skips_pm_acceptance` |
| 9 | Process writes only the old route process check artifact, not the canonical process route model artifact. | `process_route_model_missing_canonical_artifact` |
| 10 | Process repair/block aliases leave pass/repair/block flags contradictory. | `process_route_model_block_alias_flags_diverge` |
| 11 | A legacy/general officer report or PM repair follow-up is recorded but does not satisfy the active gate. | Existing dynamic return-path gate-alignment scenarios |
| 12 | PM role-work result absorbs a model report without mapping it to the active gate event. | `pm_role_work_result_not_mapped_to_current_gate` |

## Minimal Runtime Fix Shape

1. Add canonical Product events:
   `product_officer_submits_product_behavior_model` and
   `product_officer_blocks_product_behavior_model`.
2. Keep Product compatibility events:
   `product_officer_passes_product_architecture_modelability` and
   `product_officer_blocks_product_architecture_modelability`.
3. Add canonical Process events:
   `process_officer_submits_process_route_model`,
   `process_officer_requests_process_route_model_repair`, and
   `process_officer_blocks_process_route_model`.
4. Keep Process compatibility events:
   `process_officer_passes_route_check`,
   `process_officer_requires_route_repair`, and
   `process_officer_blocks_route_check`.
5. Set both canonical and compatibility flags whenever either side is recorded.
6. Write canonical artifacts first:
   `flowguard/product_behavior_model.json` and
   `flowguard/process_route_model.json`.
7. Mirror compatibility artifacts:
   `flowguard/product_architecture_modelability.json` and
   `flowguard/route_process_check.json`.
8. Make downstream helpers prefer canonical paths with compatibility fallback.
9. Require PM product model acceptance before product architecture reviewer or
   route draft use, and PM process model acceptance before Product/Reviewer
   route challenge use.

## Validation Plan

| Stage | Commands |
| --- | --- |
| Model preflight | `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` |
| Dynamic return-path model | `python simulations/run_flowpilot_dynamic_return_path_checks.py --project-root . --json-out simulations/flowpilot_dynamic_return_path_results.json` |
| Recursive route model | `python simulations/run_flowpilot_model_driven_recursive_route_checks.py` |
| Syntax | `python -m py_compile simulations/flowpilot_dynamic_return_path_model.py simulations/run_flowpilot_dynamic_return_path_checks.py skills/flowpilot/assets/flowpilot_router.py tests/test_flowpilot_router_runtime.py tests/test_flowpilot_role_output_runtime.py` |
| Focused runtime tests | Product and Process model gate tests in `tests.test_flowpilot_router_runtime`, plus router-supplied role-output tests in `tests.test_flowpilot_role_output_runtime`. |
| Install/sync | `python scripts/check_install.py`, `python scripts/install_flowpilot.py --sync-repo-owned --json`, `python scripts/audit_local_install_sync.py --json`, `python scripts/install_flowpilot.py --check --json` |
