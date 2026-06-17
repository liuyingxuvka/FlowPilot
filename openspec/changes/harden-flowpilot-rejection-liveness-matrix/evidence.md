# Evidence Trail

## Model Miss: Current Run Repeated Startup Intake

Observed source:

- `.flowpilot/current.json`
- `.flowpilot/runs/run-20260614-184920/ledger.json`
- `simulations/flowpilot_model_mesh_results.json`

Observed failure:

- Current run id: `run-20260614-184920`.
- Current next action: `open_startup_intake`.
- Lifecycle guard repeat threshold:
  `lifecycle_guard_config.max_repeated_action_without_event = 3`.
- Latest lifecycle guard history repeated the same action key and same
  observed event count 14 times.
- Event `event-0006` recorded `decision = control_plane_stuck`.
- Later `final_preflight` refreshes returned to `decision =
  process_next_action` for the same action key and observed event count.
- The model mesh result still projected the current run as
  `mesh_green_can_continue`.

Classification:

- Miss type: `evidence_overclaimed` plus `invariant_too_weak`.
- Root cause: stuck detection was represented, but stuck absorption and parent
  mesh live projection did not consume the repeated-action evidence as a
  blocker.
- Same-class case: any rejected or repeated packet/result/report continuation
  that returns with the same subject, same payload, or same action and no new
  current event can loop unless the rejection feedback names a repair target
  and the next attempt is checked for semantic delta.

Closure evidence required by this change:

- Focused FlowGuard model rejects stuck detection without absorption.
- Live projection reports repeated current-run action as blocked or
  repair-required.
- Model mesh rejects a repeated-action live projection as green.
- Runtime/lifecycle guard keeps repeated same-action state blocked until new
  progress evidence exists.
- Fake AI and synthetic coverage include no-delta retry plus corrected retry
  cells.

## Implementation Evidence

Artifacts:

- `simulations/flowpilot_rejection_liveness_matrix_model.py`
- `simulations/run_flowpilot_rejection_liveness_matrix_checks.py`
- `simulations/flowpilot_rejection_liveness_matrix_results.json`
- `simulations/flowpilot_synthetic_agent_coverage_matrix_results.json`
- `simulations/flowpilot_model_mesh_results.json`
- `simulations/flowpilot_model_test_alignment_results.json`
- `simulations/flowpilot_process_liveness_results.json`
- `docs/flowguard_project_topology.json`

Passing checks:

- `python simulations/run_flowpilot_rejection_liveness_matrix_checks.py --json-out simulations/flowpilot_rejection_liveness_matrix_results.json`
  - Result: passed; 143 required cells; 11 hazards rejected; FlowGuard explorer
    ok.
- `python simulations/flowpilot_synthetic_agent_coverage_matrix.py --json-out simulations/flowpilot_synthetic_agent_coverage_matrix_results.json`
  - Result: passed; 279 required cells; 326 rows; zero findings.
- `python -m unittest tests.test_flowpilot_synthetic_agent_coverage_matrix tests.test_flowpilot_synthetic_agent_trace_replay.FlowPilotSyntheticAgentTraceReplayTests.test_rejection_liveness_fake_ai_matrix_covers_no_delta_and_corrected_retry`
  - Result: 8 tests passed.
- `python -m unittest tests.test_flowpilot_lifecycle_guard`
  - Result: 24 tests passed.
- `python -m unittest tests.test_flowpilot_full_model_test_gap_closure`
  - Result: 15 tests passed.
- `python -m unittest tests.test_flowpilot_model_test_alignment`
  - Result: 19 tests passed.
- `python simulations/run_flowpilot_model_mesh_checks.py --json-out simulations/flowpilot_model_mesh_results.json`
  - Result: model ok true; live projection classifies the active run as
    `blocked_by_live_evidence`, not `mesh_green_can_continue`.
- `python simulations/run_flowpilot_model_test_alignment_checks.py --json-out simulations/flowpilot_model_test_alignment_results.json`
  - Result: `alignment_ok: true`; 13 families; zero findings.
- `openspec validate harden-flowpilot-rejection-liveness-matrix --strict`
  - Result: valid.
- `python -m flowguard project-audit --root .`
  - Result: pass with FlowGuard 0.47.2 and schema 1.0.
- `python scripts/flowguard_project_topology.py build`
  - Result: pass; 145 models, 1050 code surfaces, 13 alignment families.
- `python scripts/flowguard_project_topology.py check`
  - Result: pass; zero findings.
- `python scripts/install_flowpilot.py --sync-repo-owned --skip-self-check --json`
  - Result: pass; installed `flowpilot` changed from stale digest to
    `source_fresh: true`.
- `python scripts/audit_local_install_sync.py --json`
  - Result: pass.
- `python scripts/install_flowpilot.py --check --json`
  - Result: pass.
- `python -m compileall <touched simulation/runtime/test files>`
  - Result: pass.

Expected live-run failure:

- `python simulations/run_flowpilot_process_liveness_checks.py --json`
  - Result: repository model graph checks passed, but top-level result is false
    because the active run `run-20260614-184920` has
    `repeated_lifecycle_action_not_absorbed`.
  - Current projection evidence:
    - action type: `open_startup_intake`
    - next action class: `user_required`
    - repeated count: 14
    - threshold: 3
    - prior stuck same action: true
  - This is the intended live projection boundary for this change. The active
    run was not advanced or repaired.
