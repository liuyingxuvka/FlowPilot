# StructureMesh HFF Split Plan

## Scope

This plan covers the four current deferred split findings reported by
`simulations/flowpilot_model_test_alignment_results.json` before this change:

- `simulations/run_flowpilot_core_runtime_checks.py`
- `simulations/run_flowpilot_information_flow_alignment_checks.py`
- `skills/flowpilot/assets/flowpilot_new.py`
- `scripts/flowguard_project_topology.py`

## Partitions

| Parent | Child owner | Responsibility | Public entrypoint evidence |
| --- | --- | --- | --- |
| `simulations/run_flowpilot_core_runtime_checks.py` | `simulations/flowpilot_core_runtime_scenarios.py` | Runtime scenario construction and scenario catalog | Parent keeps `run_checks`, `main`, `--json-out`, and result JSON writer |
| `simulations/run_flowpilot_information_flow_alignment_checks.py` | `simulations/flowpilot_information_flow_alignment_obligations.py` | Information-flow obligation ids and obligation records | Parent keeps `build_alignment_plan`, `build_report`, `main`, and result JSON writer |
| `simulations/run_flowpilot_information_flow_alignment_checks.py` | `simulations/flowpilot_information_flow_alignment_contracts.py` | Code-contract catalog | Parent report still consumes contracts through the same model id |
| `simulations/run_flowpilot_information_flow_alignment_checks.py` | `simulations/flowpilot_information_flow_alignment_evidence.py` | Test-evidence catalog | Parent report still emits same evidence count and result shape |
| `simulations/run_flowpilot_information_flow_alignment_checks.py` | `simulations/flowpilot_information_flow_alignment_markers.py` | Marker and code-symbol checks | Parent report still emits marker and symbol layers |
| `skills/flowpilot/assets/flowpilot_new.py` | `skills/flowpilot/assets/flowpilot_new_shared.py` | Startup UI, run bootstrap, runtime/status projection helpers | Parent keeps current public import and CLI path |
| `skills/flowpilot/assets/flowpilot_new.py` | `skills/flowpilot/assets/flowpilot_new_role_commands.py` | Role assignment, lease, ACK, handoff, sealed packet/result opens | Parent re-exports current role command functions |
| `skills/flowpilot/assets/flowpilot_new.py` | `skills/flowpilot/assets/flowpilot_new_run_commands.py` | Progress, liveness, stop/cancel, submit, status, patrol, resume, repair, run-until-wait | Parent re-exports current run command functions |
| `skills/flowpilot/assets/flowpilot_new.py` | `skills/flowpilot/assets/flowpilot_new_cli.py` | Current CLI parser and dispatcher | Parent `__main__` delegates to current CLI only |
| `scripts/flowguard_project_topology.py` | `scripts/flowguard_project_topology_lib/common.py` | Constants, path helpers, JSON/text helpers, runner key and evidence helpers | Parent keeps `build`, `check`, and imported public helpers |
| `scripts/flowguard_project_topology.py` | `scripts/flowguard_project_topology_lib/collectors.py` | Model, alignment, surface, tier, evidence, and area collection | Parent keeps `build_report` import surface |
| `scripts/flowguard_project_topology.py` | `scripts/flowguard_project_topology_lib/render.py` | Markdown rendering, topology check, and artifact writing | Parent keeps `render_markdown`, `check_topology`, and `write_topology` import surface |

## DevelopmentProcessFlow Revalidation Plan

1. Syntax/import checks for all parent and child modules.
2. Focused runner parity:
   - `python simulations/run_flowpilot_core_runtime_checks.py --json-out simulations/flowpilot_core_runtime_results.json`
   - `python simulations/run_flowpilot_information_flow_alignment_checks.py --json-out simulations/flowpilot_information_flow_alignment_results.json`
   - `python -m unittest tests.test_flowguard_project_topology`
   - focused `flowpilot_new.py` entrypoint tests.
3. Model-test alignment regeneration and full coverage inventory regeneration.
4. Strict old-path/fallback sweep across models, tests, prompts, cards, and entrypoints.
5. Topology build/check after changed model/test/source/result artifacts.
6. Background Meta and Capability checks with final artifact inspection.
7. Repository-owned install sync, then install check and freshness audit in order.

## Claim Boundary

This split preserves only current public entrypoints. It does not add or
approve legacy field aliases, obsolete command names, old packet/result shapes,
repo-root fallback, newest-run fallback, prose/shape guessing, or automatic
historical-artifact promotion.
