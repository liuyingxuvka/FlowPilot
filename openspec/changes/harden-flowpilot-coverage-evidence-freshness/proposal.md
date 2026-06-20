## Why

The live FlowPilot Cartesian and fake-AI coverage checks can now generate the
expanded formal-artifact and review-window matrices, but durable evidence can
still lag behind the current code. The observed stale state had live Cartesian
coverage at 71 mutation families while the persisted result JSON still recorded
65, and the full coverage sweep/inventory still recorded 150 runners while the
current repository had 152.

That gap makes a full-coverage claim unsafe: a focused check can pass while the
committed result artifacts, topology, and install self-check still consume old
evidence.

## What Changes

- Add regression tests that compare persisted Cartesian evidence with the live
  model-generated matrix summary.
- Add regression tests that require the persisted full coverage sweep and
  inventory to include every current `run_*_checks.py` runner, including the
  fake-AI runtime replay and real-issue backfeed runners.
- Refresh durable FlowGuard result artifacts, coverage sweep/inventory,
  topology, and install evidence so the local repository, installed skill, and
  git state agree.

## Impact

- `tests/test_flowpilot_full_model_coverage_inventory.py`
- `tests/test_flowpilot_cartesian_control_plane_exhaustion.py`
- `simulations/flowpilot_cartesian_control_plane_exhaustion_results.json`
- `simulations/flowpilot_full_model_coverage_sweep_results.json`
- `simulations/flowpilot_full_model_coverage_inventory_results.json`
- `docs/flowguard_project_topology.json`
- `docs/flowguard_project_topology.md`
- Focused FlowGuard/OpenSpec/topology/install checks.
