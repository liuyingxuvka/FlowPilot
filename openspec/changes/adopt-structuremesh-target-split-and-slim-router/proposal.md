## Why

FlowGuard's upgraded StructureMesh now requires a model-derived target structure before it will trust a large script split. FlowPilot's router split evidence still describes current ownership but does not yet encode that target structure, so the new checks correctly block further maintenance and release.

## What Changes

- Add model-derived StructureMesh target recommendations for the FlowPilot router facade split and the broader structure-maintenance gate.
- Add model-derived TestMesh target split derivations so parent test gates cannot overclaim child-suite coverage.
- Continue router slimming by extracting the largest low-risk declarative protocol/catalog band into an owned child module while retaining `flowpilot_router.py` as the public import and CLI facade.
- Run focused and background FlowGuard regressions with final artifact evidence before local release readiness.
- Synchronize the installed local FlowPilot skill from the repository, commit locally, and defer GitHub push/release publication.

## Capabilities

### New Capabilities
- `structuremesh-router-slimming`: Covers FlowGuard StructureMesh target derivation, router facade compatibility, background regression evidence, install synchronization, and release-ready publication for large router splits.

### Modified Capabilities
- None.

## Impact

- Affected code: `skills/flowpilot/assets/flowpilot_router.py`, new or existing router owner modules, StructureMesh/TestMesh simulation models and result artifacts.
- Affected validation: StructureMesh, TestMesh, model-test alignment, router tier, release tier, Meta and Capability FlowGuard regressions.
- Affected release materials: `VERSION`, `CHANGELOG.md`, local installed skill copy, and local Git commit. GitHub push/release publication is explicitly deferred.
