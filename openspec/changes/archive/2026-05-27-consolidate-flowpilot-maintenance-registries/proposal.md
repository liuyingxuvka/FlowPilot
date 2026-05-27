## Why

FlowPilot now has strong runtime safety gates, but several maintenance facts are still repeated across Python tables, JSON registries, install checks, diagnostics, and tests. This change reduces that alignment burden by introducing single-source maintenance registries while preserving public compatibility names and hard control-plane boundaries.

## What Changes

- Add a registry-first maintenance path for FlowPilot code/table consolidation.
- Introduce canonical registries for maintenance surfaces, gate outcomes, external events, and contract/process bindings where the existing data is currently duplicated.
- Keep existing module names, exported constants, event names, schema values, CLI behavior, and public router facade imports compatible.
- Convert selected diagnostics and tests to consume generated or derived views instead of independently maintained lists.
- Preserve Controller foreground patrol, worker/PM/reviewer information isolation, runtime write-lock safety, terminal lifecycle authority ordering, and break-glass independence.
- Run relevant FlowGuard structure/model-test checks and background model regressions before claiming the maintenance pass complete.
- Synchronize the local installed FlowPilot skill and verify source freshness before any local git completion claim.

## Capabilities

### New Capabilities

- `maintenance-registry-consolidation`: Registry-first maintenance for FlowPilot surfaces, protocol tables, event catalogs, and generated compatibility exports.

### Modified Capabilities

- `repository-maintenance-guardrails`: Maintenance now requires single-source registries to preserve compatibility views and to prove background regression completion with real artifacts.

## Impact

- Affected code: FlowPilot protocol/catalog modules, model-test alignment diagnostics, install-check inventory, runtime kit contract binding readers, selected tests, and maintenance-map generation.
- Affected models/checks: FlowGuard StructureMesh, model-test alignment, router-focused tests, meta/capability regressions when release readiness is claimed.
- Compatibility: No breaking change is intended. Existing public imports, router facade exports, event names, schemas, and CLI commands remain stable.
- Operations: Local installed skill sync and freshness audit are required after source changes; git completion must not include unrelated pre-existing worktree changes.
