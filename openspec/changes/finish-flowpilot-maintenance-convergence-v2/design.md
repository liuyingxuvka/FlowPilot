## Context

The latest maintenance pass removed a stale prompt-boundary source-audit gap by
updating the checker to read the router facade plus the child modules and
runtime prompt assets that now own the prompt text. The current coverage
inventory still reports `full_coverage_ok: false` and
`release_convergence_ok: false` with four not-green runner groups:

- `flowpilot_control_plane_friction`
- `flowpilot_final_confidence_gate`
- `flowpilot_terminal_state_monotonicity`
- `protocol_contract_conformance`

The inventory also reports live/runtime findings, one source/code finding, and
unclassified model tiers. The maintenance map shows large structure pressure in
runtime owners, scripts, tests, and parent models, but current split rules
require model-backed contracts before any broad contraction.

## FlowGuard Route

The convergence process is modeled as:

`MaintenanceInput x RepositoryState -> Set(MaintenanceOutput x RepositoryState)`

The route uses FlowGuard satellite skills in this order:

1. `flowguard-existing-model-preflight` to locate current model ownership and
   avoid duplicate boundaries.
2. `flowguard-development-process-flow` to govern stage order, stale evidence,
   peer writes, and finalization confidence.
3. `flowguard-model-test-alignment` for protocol/source conformance, terminal
   monotonicity, code-boundary observations, and obligation-to-test evidence.
4. `flowguard-model-mesh` for live packet-authority projection, parent/child
   reattachment, oversized parent model evidence, and affected sibling review.
5. `flowguard-test-mesh` for large, layered, stale, background, or release-only
   validation evidence.
6. `flowguard-architecture-reduction` for shrink candidates that may remove,
   merge, or collapse duplicate handlers, adapters, state phases, or branches.
7. `flowguard-code-structure-recommendation` and `flowguard-structure-mesh` for
   model-derived target modules, facade compatibility, dependency direction,
   and parity evidence.

## Work Batches

### Batch A: Scope, Evidence, And Coordination

- Preserve current dirty-worktree context and identify peer-agent changes.
- Generate a fresh maintenance map, coverage sweep, and full coverage
  inventory.
- Validate this OpenSpec change before behavior-bearing code edits.
- Record the baseline gap table and required evidence for each residual runner.

### Batch B: Protocol Contract Conformance

- Split failures by external protocol family: startup reviewer facts, control
  blockers, PM resume decisions, role-output loader path/hash pairs, material
  scan packet-body contracts, wait event producers, and process/result binding
  tables.
- For each family, identify the model obligation, source owner, public input
  gate, output mapper, state writer, side effects, and tests.
- Repair source or checker boundaries only when direct model/test alignment
  proves the current implementation contract.

### Batch C: Terminal And Live Runtime Closure

- Repair `flowpilot_terminal_state_monotonicity` so completion/blocked/stopped
  state cannot move backward through stale events, ACK-only outputs, or
  ambiguous cleanup claims.
- Repair or explicitly dispose live runtime findings, including packet-authority
  projection and durable host automation cleanup evidence.
- Keep historical runtime evidence; do not delete `.flowpilot` state as a
  shortcut.

### Batch D: Final Confidence And Model/Test Mesh

- Refresh model-test alignment, model maturation, model hierarchy, final
  confidence, and full coverage inventory after protocol and terminal repairs.
- Classify unclassified model tiers into supporting, coverage-strong,
  specialized local hazard, or required child model/TestMesh owners.
- Make stale, progress-only, skipped, or release-only evidence block or scope
  confidence instead of being consumed as pass evidence.

### Batch E: Structure And Test Compression

- Contract only proven structure hotspots. Preserve facades for public modules,
  scripts, and aggregate tests.
- Prioritize runtime owner modules with both size pressure and external contract
  evidence gaps before script or test refactors.
- Split tests by externally visible contract family before moving internal
  fixtures.
- Split parent models by child contracts and current evidence ids; parent green
  confidence must consume current child evidence, not stale declarations.

### Batch F: Regression, Install, And Git Finalization

- Launch heavyweight Meta, Capability, router, integration, and final
  confidence regressions under stable background artifact roots.
- Inspect stdout, stderr, combined, exit, and meta artifacts before using a
  background check as evidence.
- Run install sync, install audit, install check, OpenSpec validation, public
  boundary/privacy checks where applicable, and local git scope review.
- Commit intended files locally only after all required evidence is current.

## Background Regression Contract

Use background artifacts under `tmp/flowguard_background/` or a task-specific
subdirectory with these files per command base name:

- `<name>.out.txt`
- `<name>.err.txt`
- `<name>.combined.txt`
- `<name>.exit.txt`
- `<name>.meta.json`

Progress lines are liveness only. Completion evidence requires final status,
exit code, latest update timestamp, and proof-reuse metadata where available.

## Compatibility And Safety

- Keep `flowpilot_router.py`, script commands, aggregate test entrypoints, and
  model import paths compatible unless a scoped OpenSpec delta authorizes a
  behavior change.
- Do not use generated result churn as a substitute for source repair.
- Do not stage unrelated peer-agent work until it is explicitly integrated and
  verified as part of this convergence pass.
- Do not weaken hard invariants or downgrade failing evidence to pass.

## Validation

- `openspec validate finish-flowpilot-maintenance-convergence-v2 --strict`
- `openspec validate --strict`
- `python -c "import flowguard; print(flowguard.SCHEMA_VERSION); print(flowguard.__file__)"`
- Maintenance map, coverage sweep, and full coverage inventory.
- Focused runner checks for every touched residual group.
- Model-test alignment and model hierarchy/maturation checks.
- StructureMesh/TestMesh checks for moved modules, tests, or model partitions.
- Background Meta and Capability checks with inspected artifacts.
- Router/integration/final-confidence tiers as required by touched surfaces.
- Install sync, install audit, install check, `check_install.py`, public
  boundary/privacy checks where applicable, and local git commit scope review.
