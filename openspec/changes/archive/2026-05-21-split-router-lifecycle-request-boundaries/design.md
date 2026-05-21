## Context

`flowpilot_router_lifecycle_requests.py` is the existing owner for terminal run
lifecycle requests and related private router exports. The router facade model
already lists this owner as responsible for run lifecycle requests, protocol
dead-end records, and exception blocker routing. The maintenance map flags the
file as over the StructureMesh line threshold, but current evidence treats the
behavior contract as green.

The safe path is therefore not to move lifecycle authority elsewhere. The safe
path is to keep `flowpilot_router_lifecycle_requests.py` as the facade and split
its internal FunctionBlocks into child modules with the same router binding
pattern used by other FlowPilot owner facades.

## Goals / Non-Goals

**Goals:**

- Keep every public and private router compatibility export available from
  `flowpilot_router`.
- Reduce the lifecycle request facade below the runtime owner StructureMesh
  threshold.
- Derive child modules from existing behavior blocks: terminal controller-work
  fencing, terminal authority reconciliation, lifecycle request records, and
  exception blocker fallback.
- Preserve artifact schemas and state transitions exactly.
- Refresh model/test/maintenance evidence for the new topology.

**Non-Goals:**

- No lifecycle behavior redesign.
- No schema migration for `run_lifecycle.json`, `terminal_fence.json`, or
  `terminal_reconciliation.json`.
- No changes to control-blocker semantics beyond preserving the existing
  terminal clearance call path.
- No remote push, tag, release, or publication.

## Decisions

1. Keep the parent module as a compatibility facade.

   The router facade registry points at `flowpilot_router_lifecycle_requests`.
   Retaining that module as the public owner avoids changing old imports or
   private router exports.

2. Split by state/side-effect ownership, not by arbitrary function size.

   The child modules should own coherent behavior:
   terminal controller-work fencing, terminal authority reconciliation,
   lifecycle request record writing, and exception blocker fallback. This keeps
   each module reviewable without creating one-function files.

3. Bind children through the parent facade.

   Child modules need access to router-bound helper names. The parent facade
   will call each child `_bind_router(router)` so legacy lookups and runtime
   exports keep the same behavior.

4. Update evidence before claiming completion.

   StructureMesh and model-test alignment must recognize the child modules, and
   the maintenance map should no longer list the parent lifecycle request module
   as an unresolved over-threshold runtime owner if the split succeeds.

## Risks / Trade-offs

- Compatibility wrapper drift -> keep facade exports and add focused identity or
  import assertions for the split functions.
- Hidden dependency on parent globals -> propagate router binding to child
  modules and run focused terminal/control-blocker tests.
- Oversplitting -> use four behavior children at most and avoid one-function
  modules unless a public contract requires it.
- Evidence overclaim -> run focused checks first, then background router, Meta,
  and Capability regressions with complete log artifacts.
