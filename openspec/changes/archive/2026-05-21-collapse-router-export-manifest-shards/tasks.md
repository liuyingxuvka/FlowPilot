## 1. Model And Target Structure

- [x] 1.1 Run FlowGuard existing-model preflight and architecture-reduction review for the export-manifest contraction.
- [x] 1.2 Derive the canonical registry target and compatibility wrapper boundaries from the FlowGuard result.
- [x] 1.3 Validate the OpenSpec change strictly before implementation.

## 2. Implementation

- [x] 2.1 Add a canonical router facade export registry owner.
- [x] 2.2 Convert existing export manifest shard modules into compatibility views over the canonical registry.
- [x] 2.3 Update model/test source-contract references and diagnostics for the new registry shape.
- [x] 2.4 Update maintainer-facing docs or maps that describe the export manifest structure.

## 3. Validation

- [x] 3.1 Run focused import, facade export, and source-contract tests.
- [x] 3.2 Run FlowGuard router facade split, StructureMesh, and model-test alignment checks.
- [x] 3.3 Run router/Meta/Capability regressions through the background artifact contract and inspect final logs.

## 4. Sync And Git

- [x] 4.1 Sync the repo-owned FlowPilot skill into the local installed skill location.
- [x] 4.2 Audit installed-skill freshness and run install/smoke checks.
- [x] 4.3 Recheck peer-agent worktree changes and create a local git commit containing only this change.
