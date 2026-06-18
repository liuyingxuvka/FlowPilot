# FlowPilot Fake-AI Review Window Validation Mesh

Date: 2026-06-18

## Scope

This mesh covers the `harden-flowpilot-fake-ai-review-window-coverage`
OpenSpec change. It upgrades existing FlowPilot validation surfaces without
adding a parallel fake runtime, reviewer lane, or legacy compatibility path.

## FlowGuard Route

- Existing model preflight: reuse current contract projection, contract
  exhaustion, current-contract Cartesian, reviewer, PM repair, and BreakGlass
  models.
- DevelopmentProcessFlow mode: `execution_freshness` for staged edits,
  validation evidence, install sync, and final claim boundaries.
- TestMesh mode: focused child tests plus model runners; background progress is
  liveness only until exit artifacts exist.

## Changed Surfaces

| Surface | Owner | Required Validation |
| --- | --- | --- |
| Contract-driven fake AI responder | `simulations/flowpilot_contract_driven_fake_ai.py` | Focused responder tests and contract-exhaustion fake-AI cells |
| AI-visible packet contracts | `packet_result_contracts.py`, `runtime.py` | AI contract projection tests, high-standard control-flow tests |
| Reviewer review windows | Runtime packet metadata and reviewer cards | Reviewer/gate focused tests and formal gate standard checks |
| PM repair loop for Reviewer blockers | Existing blocker repair policy | PM repair-loop tests and blocker repair information-flow model |
| BreakGlass threshold and body grants | Existing Controller BreakGlass recovery | BreakGlass unit tests and controller break-glass model |
| Matrix evidence | Existing FlowGuard runners | Contract exhaustion, current-contract Cartesian, planning quality, reviewer active challenge, model-test alignment |
| Install readiness | Repo-owned skill install scripts | install sync, local install audit, installed skill check |

## Minimum Revalidation Commands

Focused tests:

```powershell
python -m pytest tests/test_flowpilot_ai_contract_projection.py tests/test_flowpilot_high_standard_control_flow.py tests/test_flowpilot_contract_exhaustion_mesh.py tests/test_flowpilot_current_contract_cartesian_matrix.py tests/test_flowpilot_executable_matrix_coverage.py tests/test_flowpilot_core_runtime.py tests/test_flowpilot_card_instruction_coverage.py -q
```

FlowGuard/model checks:

```powershell
python simulations/run_flowpilot_contract_exhaustion_mesh_checks.py --write-results
python simulations/run_flowpilot_current_contract_cartesian_matrix_checks.py --write-results
python simulations/run_flowpilot_executable_matrix_coverage_checks.py --write-results
python simulations/run_flowpilot_planning_quality_checks.py --json-out simulations/flowpilot_planning_quality_results.json
python simulations/run_flowpilot_reviewer_active_challenge_checks.py --json-out simulations/flowpilot_reviewer_active_challenge_results.json
python simulations/run_flowpilot_blocker_repair_information_flow_checks.py --json-out simulations/flowpilot_blocker_repair_information_flow_results.json
python simulations/run_flowpilot_model_test_alignment_checks.py --json-out simulations/flowpilot_model_test_alignment_results.json
python simulations/run_flowpilot_reviewer_only_gate_checks.py --json-out simulations/flowpilot_reviewer_only_gate_results.json
python simulations/run_meta_checks.py
python simulations/run_capability_checks.py
```

Topology and install:

```powershell
python scripts/flowguard_project_topology.py build
python scripts/flowguard_project_topology.py check
python scripts/install_flowpilot.py --sync-repo-owned --json
python scripts/audit_local_install_sync.py --json
python scripts/install_flowpilot.py --check --json
python scripts/check_install.py --json
```

## Completion Boundary

This hardening is complete only when focused tests, affected model checks,
topology checks, install checks, and local install sync pass from current
artifacts. If broad tests fail due to concurrent peer-agent edits, preserve the
failure evidence and do not revert unrelated work.
