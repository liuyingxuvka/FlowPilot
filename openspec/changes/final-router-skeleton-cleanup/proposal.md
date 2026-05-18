## Why

`flowpilot_router.py` has already been split into coarse owner modules, but the
file still contains hundreds of historical facade wrappers. Most of those names
exist only to preserve the old monolithic import surface, not because the new
runtime should treat them as public API.

The next maintenance pass should converge the router into a true skeleton:
keep the CLI and intentionally supported runtime entrypoints, move or broker
owner-owned implementation behind explicit StructureMesh ownership, and stop
treating every private helper from the old router as a permanent compatibility
contract.

## What Changes

- Convert the remaining broad router facade into a small skeleton plus an
  explicit owner-export registry for transitional internal owner lookups.
- Define a new public router API whitelist and remove the expectation that all
  old private helper names are public compatibility entries.
- Move remaining large real facade bodies into owner modules when practical.
- Continue splitting oversized owner modules by cohesive behavior, not by one
  function per file.
- Update FlowGuard StructureMesh/TestMesh evidence so the new target is a
  skeleton router with owned child modules rather than a compatibility facade.
- Synchronize the installed local FlowPilot skill, run local evidence, and
  commit locally without push, tag, or GitHub Release publication.

## Capabilities

### Modified Capabilities
- `structuremesh-router-skeleton`: finalizes router skeleton ownership and
  narrows the public API contract after prior facade-preserving splits.

## Impact

- Affected code: `skills/flowpilot/assets/flowpilot_router.py`, router owner
  modules, tests/install checks that import router internals, and FlowGuard
  StructureMesh/TestMesh model evidence.
- Affected validation: compile/import checks, focused router boundary tests,
  StructureMesh/TestMesh/model-alignment checks, router hidden background tier,
  install sync/audit, and Meta/Capability regressions.
- Release behavior: local version/install/git sync only; no remote publication.
