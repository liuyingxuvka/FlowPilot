# Structure Split Deferral Watchlist

This watchlist records structure-compression candidates found during the
FlowPilot maintenance convergence pass that were not split in this batch.
They are deferred because their external contracts and focused tests are
current, peer agents may be editing nearby runtime surfaces, and each split
requires a dedicated StructureMesh claim with facade-parity evidence before
production code is moved.

The final-confidence gate may treat this set as release-converged only while
all non-deferred model/test/code gaps remain at zero.

| Surface | Path | Evidence Status | Required Next Action |
| --- | --- | --- | --- |
| `flowpilot_controller_break_glass` | `skills/flowpilot/assets/flowpilot_controller_break_glass.py` | external contracts current; 603 lines above owner threshold | claim a StructureMesh split and preserve break-glass incident/index parity tests |
| `flowpilot_router_controller_scheduler_standby` | `skills/flowpilot/assets/flowpilot_router_controller_scheduler_standby.py` | compatibility facade contracts current; 394 lines above facade threshold | split only with facade import/export parity evidence |
| `flowpilot_router_controller_wait_audit` | `skills/flowpilot/assets/flowpilot_router_controller_wait_audit.py` | source contract and focused wait-audit test current; 539 lines above owner threshold | split audit classification helpers under controller-wait parity tests |
| `flowpilot_router_daemon_runtime` | `skills/flowpilot/assets/flowpilot_router_daemon_runtime.py` | daemon lock/status contracts current; 488 lines above owner threshold | split lock/status/tick helpers with daemon lifecycle replay evidence |
| `role_output_runtime_envelopes` | `skills/flowpilot/assets/role_output_runtime_envelopes.py` | role-output envelope contract current; 464 lines above owner threshold | split envelope submit/progress helpers with role-output registry parity tests |

Validation snapshot:

- `python simulations/run_flowpilot_model_test_alignment_checks.py --json-out simulations/flowpilot_model_test_alignment_results.json`
- `python simulations/run_flowpilot_final_confidence_gate_checks.py --json-out simulations/flowpilot_final_confidence_gate_results.json`

Current gate result:

- decision: `release_convergence_with_deferred_structure_splits`
- blockers: none
- deferred structure split count: 5
- unresolved non-deferred model/test/code gap count: 0
