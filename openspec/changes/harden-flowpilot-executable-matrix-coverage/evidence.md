## Evidence Log

### Preflight

- FlowGuard schema check: `python -c "import flowguard; print(flowguard.SCHEMA_VERSION)"` -> `1.0`.
- FlowGuard package check: `python -c "import importlib.metadata as m; print(m.version('flowguard'))"` -> `0.51.0`.
- Project audit: `python -m flowguard project-audit --root .` -> passed.
- OpenSpec validation: `openspec validate harden-flowpilot-executable-matrix-coverage --strict` -> passed.
- Worktree boundary: repository was already heavily dirty with peer-agent changes before this change. This work avoided reverting peer files and kept the executable-matrix bridge isolated where possible.
- Sibling dependency: `reduce-flowpilot-contract-surface` remains a sibling in-progress change; this change consumes its current stage/packet-contract surfaces without editing its OpenSpec artifacts.

### DevelopmentProcessFlow Record

- `plan_detailing`: OpenSpec proposal, design, specs, tasks, and this evidence log define the implementation boundary.
- `agent_workflow`: no subagent delegation was used because the repository already had active peer-agent work and the bridge touched narrow files.
- `execution_freshness`: affected model results, synthetic coverage, model-test alignment, information-flow alignment, coverage sweep, and coverage inventory were regenerated after code/test changes.
- Minimum revalidation scope:
  - bridge model/checker/tests;
  - contract-exhaustion GlassBreak threshold semantics;
  - current-contract Cartesian matrix;
  - fake project rehearsal;
  - core runtime, high-standard control flow, and control-plane contracts;
  - synthetic coverage matrix;
  - model-test alignment and information-flow alignment;
  - repository coverage sweep and full coverage inventory;
  - project topology and local install sync before final done claim.

### Completed Validation

- `python simulations/run_flowpilot_executable_matrix_coverage_checks.py --write-results` -> passed.
- `python -m unittest tests.test_flowpilot_executable_matrix_coverage` -> passed.
- `python -m unittest tests.test_flowpilot_contract_exhaustion_mesh` -> passed.
- `python simulations/run_flowpilot_contract_exhaustion_mesh_checks.py --write-results` -> passed.
- `python -m unittest tests.test_flowpilot_synthetic_agent_coverage_matrix` -> passed.
- `python simulations/flowpilot_synthetic_agent_coverage_matrix.py --json-out simulations/flowpilot_synthetic_agent_coverage_matrix_results.json` -> passed.
- `python simulations/run_flowpilot_current_contract_cartesian_matrix_checks.py --write-results` -> passed.
- `python -m unittest tests.test_flowpilot_current_contract_cartesian_matrix` -> passed.
- `python -m unittest tests.test_flowpilot_fake_project_rehearsal` -> passed.
- `python -m unittest tests.test_flowpilot_control_plane_contracts` -> passed.
- `python -m unittest tests.test_flowpilot_high_standard_control_flow` -> passed.
- `python -m unittest tests.test_flowpilot_core_runtime` -> passed.
- `python -m unittest tests.test_flowpilot_model_test_alignment` -> passed.
- `python simulations/run_flowpilot_model_test_alignment_checks.py --json-out simulations/flowpilot_model_test_alignment_results.json` -> passed.
- `python simulations/run_flowpilot_information_flow_alignment_checks.py --json-out simulations/flowpilot_information_flow_alignment_results.json` -> passed.
- `python scripts/run_flowguard_coverage_sweep.py --timeout-seconds 120 --json-out simulations/flowpilot_full_model_coverage_sweep_results.json` -> passed.
- `python simulations/run_flowpilot_full_model_coverage_inventory.py --json-out simulations/flowpilot_full_model_coverage_inventory_results.json --markdown-out docs/flowpilot_full_model_coverage_inventory.md` -> passed.
- `python -m unittest tests.test_flowpilot_full_model_coverage_inventory` -> passed.
- `python -m unittest tests.test_flowpilot_reviewer_active_challenge` -> passed after aligning install checks with the current compact reviewer contract.
- `python -m unittest tests.test_flowpilot_planning_quality` -> passed after restoring explicit PM node-plan projection markers.
- `python scripts/check_runtime_card_capability_reminders.py --json` -> passed.
- `python scripts/flowguard_project_topology.py build` -> passed; regenerated `docs/flowguard_project_topology.json` and `docs/flowguard_project_topology.md`.
- `python scripts/flowguard_project_topology.py check` -> passed.
- `python scripts/check_install.py --json` -> passed with 896 checks.
- `python scripts/install_flowpilot.py --sync-repo-owned --json` -> passed and ran a passing self-check.
- `python scripts/audit_local_install_sync.py --json` -> passed with `flowpilot_source_fresh=true`.
- KB postflight recorded observation `e2b6b52d-df0a-4936-b09a-7ee66124af88` for the reusable distinction between model-only matrix coverage and executable bridge evidence, plus the need to serialize install sync and install audit.

### Notes

- Current-contract Cartesian rows are now reported as `model_matrix`, not `ordinary_runtime`, so parent reports do not mistake model-only coverage for executable Runtime/CLI replay.
- GlassBreak semantics are split: known recoverable rows forbid GlassBreak, while the explicit fifth same-class no-progress row requires GlassBreak as a safety fuse.
- Information-flow alignment was updated away from obsolete `evidence_consistency` field expectations and toward current `contract_self_check`, packet-owned hard evidence artifact, and `subject_stage_evidence_matrix` contracts.
- Install self-check was corrected to reject old `independent_challenge` output fields while still requiring reviewer independent challenge behavior in cards and packet context.
