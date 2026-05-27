## Why

`flowpilot_router.py` is no longer the original monolithic router, but it still
contains more than twelve thousand lines and hundreds of top-level functions.
The next maintenance pass should continue the StructureMesh split by moving
cohesive remaining facade bodies into owned child modules while keeping the
public router import and CLI contract stable.

## What Changes

- Add a new FlowGuard/OpenSpec maintenance pass for the next router-facade
  slimming stage.
- Extract cohesive remaining facade regions into focused owner modules:
  self-interrogation helpers, payload-contract builders, and system-card/action
  delivery helpers.
- Keep `flowpilot_router.py` as the compatibility facade with stable public
  function names.
- Update StructureMesh/TestMesh evidence for new owner modules and keep
  known-bad hazards failing.
- Run focused checks and hidden background regressions with final artifacts.
- Synchronize the local installed FlowPilot skill and commit locally without
  pushing or publishing a GitHub Release.

## Capabilities

### Modified Capabilities
- `structuremesh-router-slimming`: Extends the target split beyond the protocol
  catalog owner so router facade slimming continues toward a smaller public
  skeleton.

## Impact

- Affected code: `skills/flowpilot/assets/flowpilot_router.py`, new router owner
  modules, StructureMesh/TestMesh model evidence.
- Affected validation: focused compile/import checks, router card/system-card
  tests, StructureMesh/TestMesh checks, router background tier, release tier,
  Meta and Capability FlowGuard regressions as needed.
- Release behavior: local version/install/git sync only; no GitHub push, tag, or
  remote release publication.
