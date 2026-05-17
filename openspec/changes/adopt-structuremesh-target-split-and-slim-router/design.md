## Context

`flowpilot_router.py` has already been reduced by extracting coarse behavior owners, but it still contains a large declarative protocol/catalog band plus several cohesive behavior clusters. The upgraded FlowGuard StructureMesh blocks the current evidence because it now requires `target_structure`, and TestMesh similarly requires `target_split_derivation`.

## Goals / Non-Goals

**Goals:**
- Make StructureMesh and TestMesh consume explicit FlowGuard-derived target split recommendations.
- Keep the router public facade and CLI entrypoint stable.
- Extract one large, low-risk owner boundary first: protocol/catalog declarations and payload-contract helpers.
- Keep test and release evidence explicit, including background completion artifacts.
- Publish the completed maintenance work as a new release after validation.

**Non-Goals:**
- Do not split every top-level function into its own file.
- Do not remove the router facade or change the CLI path.
- Do not perform unrelated feature work, broad formatting, or technology-stack changes.
- Do not treat progress-only background output as pass evidence.

## Decisions

- **Use target-structure-first maintenance.** StructureMesh will describe the desired parent/child code layout through `CodeStructureRecommendation` and `TargetModuleRecommendation` before more code is moved. This makes the split plan reviewable and executable rather than ad hoc.
- **Extract a catalog owner before behavior-heavy owners.** The protocol/catalog band is mostly declarative tables, constants, schemas, and payload-contract builders. It offers the largest line-count reduction with the smallest behavior risk.
- **Retain facade wrappers.** Public imports and CLI behavior remain routed through `flowpilot_router.py`; extracted owners provide internal ownership, not a new public API.
- **Use TestMesh derivation for release claims.** Parent test claims must name child suites, partition coverage, and state/side-effect ownership fields rather than relying on a flat list of green tests.
- **Prepare the next version locally after the split.** Since the repository-visible version is already `0.9.7` and additional maintenance will be included, the local release-readiness target is `0.9.8` unless validation exposes a reason to stop. GitHub push and GitHub Release publication are deferred.

## Risks / Trade-offs

- **Risk: import-cycle or missing symbol during extraction.** Mitigation: move declarative data first, keep facade re-exports/wrappers, and run focused import/router tests immediately.
- **Risk: StructureMesh target recommendation drifts from real files.** Mitigation: update the model in the same change and make missing target structure a hard failing hazard.
- **Risk: release gates take a long time.** Mitigation: run heavy model regressions in hidden background jobs with final log artifacts.
- **Risk: parallel AI edits overlap.** Mitigation: check working-tree status before each edit stage and keep changes scoped to claimed files.

## Migration Plan

1. Add OpenSpec artifacts and use them as the execution checklist.
2. Update StructureMesh/TestMesh models for the upgraded FlowGuard API.
3. Extract protocol/catalog ownership into a child module while keeping facade compatibility.
4. Rerun focused structure and router gates.
5. Start and verify background Meta, Capability, router, and release checks.
6. Synchronize the installed skill copy, update release metadata, run local release-readiness checks, and commit locally without pushing or publishing a GitHub Release.
