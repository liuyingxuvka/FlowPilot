## 1. Hierarchy Contract

- [x] 1.1 Add `simulations/flowpilot_model_hierarchy_model.py` with parent, child, shared-kernel, partition, overlap, stale-evidence, and full-regression obligation states.
- [x] 1.2 Add `simulations/run_flowpilot_model_hierarchy_checks.py` with graph, hazard, partition coverage, and model-inventory reporting.
- [x] 1.3 Persist `simulations/flowpilot_model_hierarchy_results.json` from the runner.

## 2. Validation Integration

- [x] 2.1 Include the hierarchy model and runner in `scripts/check_install.py` required-file and result-file surfaces.
- [x] 2.2 Include the hierarchy runner in `scripts/smoke_autopilot.py` as a lightweight foreground check.
- [x] 2.3 Include the hierarchy runner in `scripts/run_flowguard_coverage_sweep.py` coverage tiering.

## 3. Background Regression Flow

- [x] 3.1 Launch heavyweight meta and capability regressions through `tmp/flowguard_background/` with the standard stdout, stderr, combined, exit, and meta artifacts, or record valid proof reuse.
- [x] 3.2 Inspect background artifacts before claiming completion and report incomplete runs separately from passes.

## 4. Verification and Sync

- [x] 4.1 Run focused hierarchy, mesh, smoke-fast, and install checks; fix failures.
- [x] 4.2 Sync the installed FlowPilot skill from the repository and verify source freshness.
- [x] 4.3 Preserve compatible peer-agent changes in final git staging/commit instead of reverting unrelated work.
