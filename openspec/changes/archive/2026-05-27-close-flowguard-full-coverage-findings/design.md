# Design

## Route

OpenSpec owns the scope and acceptance boundary. FlowGuard owns the evidence
route:

- Existing Model Preflight: reuse current FlowPilot runner/audit models.
- Model-Test Alignment: ensure source contracts and focused tests cover the
  changed audit/runtime obligations.
- TestMesh: classify scoped, skipped, and default-output evidence without
  overclaiming.
- Model-Miss Review: preserve live findings that contradict prior green model
  confidence.
- DevelopmentProcessFlow: keep evidence freshness and local install checks
  current after edits.

## Repair Ordering

1. Fix false-negative audit reads caused by prior StructureMesh splits.
2. Fix small production runtime writes that caused future live-state drift.
3. Re-run focused red runners and unit tests.
4. Refresh coverage sweep, model-test alignment, and inventory.
5. If remaining live findings require active run mutation, stop at an explicit
   authority blocker instead of editing `.flowpilot/runs/` opportunistically.
6. If remaining structure findings require broad module splits, leave them as
   StructureMesh-owned deferred tasks unless a focused split can be proven with
   parity tests inside this change.

## Evidence Boundary

This pass can claim repaired source/runtime/model-test issues and refreshed
inventory evidence. It cannot claim that a live FlowPilot run is safe to
continue unless the live authority model is green or the run state is repaired
through an authorized route.
