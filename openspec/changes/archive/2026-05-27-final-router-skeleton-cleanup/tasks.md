## 1. Planning And Model Boundaries

- [x] 1.1 Record the final router-skeleton OpenSpec change and keep remote publication out of scope.
- [x] 1.2 Update FlowGuard StructureMesh target evidence from compatibility-facade ownership to skeleton-plus-owner-export ownership.
- [x] 1.3 Update tests/install checks to treat only the allowlisted router names as public API.

## 2. Router Skeleton Cleanup

- [x] 2.1 Back up the current `flowpilot_router.py` before structural edits.
- [x] 2.2 Replace hand-written compatibility wrappers with an explicit owner-export registry.
- [x] 2.3 Keep supported CLI/runtime public entrypoints stable.
- [x] 2.4 Move or isolate remaining large real facade bodies where practical without changing behavior.

## 3. Owner Module Split

- [x] 3.1 Split or prepare the largest startup/work-packet/event/route owner modules by cohesive behavior boundaries.
- [x] 3.2 Keep prompt/system-card text externalized through runtime kit assets and prompt manifests where touched.
- [x] 3.3 Preserve owner boundaries without one-function-per-file fragmentation.

## 4. Validation

- [x] 4.1 Run focused compile/import and public API allowlist checks.
- [x] 4.2 Run focused router boundary/runtime checks.
- [x] 4.3 Run FlowGuard StructureMesh/TestMesh/model-alignment checks.
- [x] 4.4 Run hidden/background router tier and inspect final artifacts.
- [x] 4.5 Run Meta and Capability FlowGuard regressions.

## 5. Local Sync

- [x] 5.1 Synchronize the installed local FlowPilot skill and verify freshness.
- [x] 5.2 Update version, maintenance notes, and local install evidence.
- [x] 5.3 Run clean local public-release boundary checks without remote publication.
- [x] 5.4 Commit locally on `main`; do not push, tag, or publish a GitHub Release.
