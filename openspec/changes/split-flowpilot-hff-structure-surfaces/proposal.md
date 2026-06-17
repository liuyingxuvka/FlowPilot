## Why

The current full model-test alignment inventory still reports four deferred
StructureMesh/HFF splits in high-confidence maintenance surfaces. They now
block strict local maintenance because the project standard requires current,
single-path structure with no fallback or compatibility branches hidden in
oversized entrypoints.

## What Changes

- Split the original four deferred StructureMesh surfaces while preserving only
  their current public command/module entrypoints:
  - `simulations/run_flowpilot_core_runtime_checks.py`
  - `simulations/run_flowpilot_information_flow_alignment_checks.py`
  - `skills/flowpilot/assets/flowpilot_new.py`
  - `scripts/flowguard_project_topology.py`
- Close the two final current runtime-contract StructureMesh diagnostics now
  reported by model-test alignment while preserving their current import
  surfaces:
  - `skills/flowpilot/assets/flowpilot_router_route_artifacts_architecture_product.py`
  - `skills/flowpilot/assets/flowpilot_router_work_packets_next_actions.py`
- Move cohesive helper ownership into child modules with one owner per
  partition, no old-shape aliases, no missing-field defaults, and no
  compatibility/fallback acceptance paths.
- Refresh the FlowGuard model-test alignment inventory, coverage sweep,
  topology map, and affected focused tests so the deferred split count drops
  only from executable evidence.
- Synchronize the repository-owned installed FlowPilot skill after validation,
  then audit local install freshness and local git state without release,
  deploy, tag, or remote publication.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `flowpilot-structure-debt-convergence`: close the four current deferred
  StructureMesh split findings with child-module evidence and focused tests.
- `structuremesh-maintenance-gates`: require partition/parity evidence for
  validation-runner, runtime-entrypoint, and topology-script splits in this
  pass.
- `flowguard-full-model-coverage-inventory`: regenerate the inventory so
  `needs_structure_split` findings are not treated as closed until the
  owning diagnostics no longer report them.
- `python-structure-simplification`: clarify that preserving public entrypoints
  means preserving the current supported entrypoint only, not accepting legacy
  fields, old JSON shapes, or fallback command paths.

## Impact

- Affected runtime entrypoint: `skills/flowpilot/assets/flowpilot_new.py`.
- Affected model/tooling entrypoints: the two FlowPilot validation runners and
  the FlowGuard project topology script listed above.
- Affected evidence: model-test alignment results, full coverage inventory,
  coverage sweep results, project topology artifacts, adoption logs, OpenSpec
  change artifacts, install-sync audit outputs, and focused test outputs.
- No public release, remote push, deployment, tag, secret handling, or
  destructive git operation is part of this change.
