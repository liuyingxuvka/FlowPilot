# Apply Layered Boundary Proof To FlowPilot Coverage

## Summary

Add a FlowGuard layered boundary proof check for FlowPilot coverage evidence.
The check separates current parent/child coverage accounting from the stricter
whole-system leaf Cartesian proof requirement.

## Motivation

FlowPilot already has broad FlowGuard coverage inventory and model-test
alignment checks, but the current reports can be misunderstood: scoped replay
gaps and deferred StructureMesh splits are visible, yet ordinary coverage
accounting can still be green. We need a machine-checked proof layer that keeps
those two claims separate.

## Scope

This change may add:

- a read-only simulation check that builds FlowGuard `LayeredBoundaryProofPlan`
  objects from current inventory/alignment evidence;
- ordinary unit tests for the proof boundary and known-bad cases;
- documentation/spec records for the new claim boundary.

This change must not:

- mutate `.flowpilot/runs/` state;
- edit production router behavior;
- treat scoped replay, skipped evidence, or deferred StructureMesh split as
  full leaf Cartesian proof;
- push, tag, publish, or release.

## Success Criteria

- Parent coverage accounting is green only when child coverage ownership,
  child reattachment, and inventory leaf matrix cells are current.
- Every inventory gap class has an explicit leaf matrix cell.
- The stricter full leaf Cartesian claim remains blocked while scoped replay,
  skipped evidence, hard runner findings, deferred StructureMesh split, or
  `full_coverage_ok=false` remain.
- Known-bad tests prove that unknown gap classes and unexpected leaf outputs
  block the proof.
