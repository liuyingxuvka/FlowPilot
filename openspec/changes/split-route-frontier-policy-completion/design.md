# Design

## StructureMesh Route

This is a facade-preserving StructureMesh maintenance split. The current module
already separates into three behavior blocks:

- route authority snapshot, rejection payload, and blocker writing;
- legal next-action context, parent child-entry, and route-action legality;
- node completion ledger, packet completion marking, and frontier node commit.

The split uses the repository's existing owner-module pattern:

- the original module imports each child module and re-exports the same public
  names through `__all__`;
- the original `_bind_router` copies router globals into the facade and forwards
  binding to each child module;
- each child module owns one behavior block and keeps its own `_bind_router`.

## Boundaries

- Runtime/router remains the mechanical owner for legal action validation,
  rejection payloads, frontier writes, and node-completion ledgers.
- FlowGuard/MTA owns the maintenance proof that the split removes the
  StructureMesh gap without creating missing-model or internal-only-test gaps.
- Tests assert identity between the facade exports and the child owner exports
  so callers continue to receive the same function objects from the original
  public module.

## Validation

Minimum validation:

- syntax/import checks for the touched modules;
- focused asset surface and full diagnostic contract tests;
- model-test alignment and synthetic-agent matrix regeneration;
- StructureMesh/TestMesh maintenance runner;
- project topology rebuild/check and local install sync before closure.
