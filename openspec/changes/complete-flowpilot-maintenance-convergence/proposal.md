## Why

FlowPilot has converged through many completed OpenSpec and FlowGuard passes,
but the active change backlog, maintenance evidence reports, and remaining
runtime-owner hotspots still need one coordinated local convergence pass. The
repository should finish this without deleting evidence, breaking public
facades, or claiming completion before install sync and local git evidence are
fresh.

## What Changes

- Archive completed OpenSpec changes that have strict validation evidence while
  preserving their proposal, design, spec, and task files.
- Keep duplicate validation artifacts and `.flowpilot` runtime retention as
  report-first evidence; do not remove or rewrite them in this pass.
- Apply FlowGuard Architecture Reduction and StructureMesh only to proven
  runtime-owner hotspots where facade compatibility can be preserved.
- Refresh maintenance diagnostics, background model evidence, local installed
  FlowPilot skill contents, version notes, and local git state.

## Capabilities

### Modified Capabilities

- `repository-maintenance-guardrails`: Clarifies whole-repository convergence,
  archive safety, report-first cleanup, FlowGuard-backed hotspot contraction,
  install freshness, and local git finalization.

## Impact

- Affected OpenSpec files: completed active changes move under the tracked
  archive area and this maintenance change records the new work.
- Affected code: targeted `skills/flowpilot/assets/` runtime-owner modules with
  compatibility facades retained.
- Affected evidence: OpenSpec strict validation, FlowGuard maintenance
  diagnostics, focused router tests, background Meta/Capability checks, install
  sync/audit, changelog/version notes, and local git commit.
- Out of scope: remote push, release publication, destructive runtime cleanup,
  deletion of validation artifacts, and changes to the frozen public behavior
  contract.
