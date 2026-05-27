## 1. Planning And FlowGuard Boundaries

- [x] 1.1 Validate the OpenSpec change and keep GitHub push/tag/release out of scope.
- [x] 1.2 Update FlowGuard StructureMesh/TestMesh targets for the final owner-module polish.
- [x] 1.3 Record touched owner boundaries and focused validation commands.

## 2. Packet Control-Plane Transition Split

- [x] 2.1 Extract issue/resume transition classes into a focused owner module.
- [x] 2.2 Extract packet write/controller relay transition classes into a focused owner module.
- [x] 2.3 Extract dispatch/result relay transition classes into a focused owner module.
- [x] 2.4 Extract reviewer/PM outcome transition classes into a focused owner module.
- [x] 2.5 Keep `packet_control_plane_model_transitions.py` as a compatible facade.
- [x] 2.6 Run packet control-plane model checks.

## 3. Router Export Manifest Split

- [x] 3.1 Extract facade export registry rows into domain manifest shards.
- [x] 3.2 Keep `flowpilot_router_facade_export_manifest.py` as the compatible aggregator.
- [x] 3.3 Run facade export import/target checks.

## 4. Router Owner Module Polish

- [x] 4.1 Split action-factory helpers into focused gate/blocker/action owner modules.
- [x] 4.2 Split PM role-work helpers into gate, request/result, index/lifecycle, and next-action owner modules.
- [x] 4.3 Split terminal ledger helpers into summary, final-ledger, closure/replay, and recovery owner modules.
- [x] 4.4 Split Controller scheduler/receipt helpers into action/receipt write, receipt-effect, pending, and scheduled-reconciliation owner modules.
- [x] 4.5 Preserve all existing compatibility exports and bound-router behavior.

## 5. Prompt/Description Cleanup

- [x] 5.1 Identify remaining long prompt-like text in touched modules.
- [x] 5.2 Move only manifest-protectable prompt text to runtime-kit prompt assets.
- [x] 5.3 Update prompt manifest/tests/coverage when text moves, or document why no additional prompt move is safe.

## 6. Docs, Version, Install Checks

- [x] 6.1 Update install required-file checks for new owner modules/assets.
- [x] 6.2 Update maintainer documentation/module maps.
- [x] 6.3 Bump version and changelog.
- [x] 6.4 Synchronize installed local FlowPilot and verify freshness.

## 7. Validation And Local Completion

- [x] 7.1 Run focused compile/import checks for touched modules.
- [x] 7.2 Run focused unit/model tests for packet control-plane, router action/packet/card/terminal/controller boundaries.
- [x] 7.3 Run StructureMesh/TestMesh/model-test alignment checks.
- [x] 7.4 Run router background tier with hidden artifacts and inspect final status.
- [x] 7.5 Run Meta and Capability layered full regressions with hidden artifacts and inspect final status.
- [x] 7.6 Run local public-release boundary checks without push/tag/release.
- [x] 7.7 Commit locally on `main`.
