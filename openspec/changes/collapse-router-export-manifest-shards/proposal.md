## Why

FlowGuard Architecture Reduction found one low-risk FlowPilot contraction target:
the router facade export manifest shards. They are compatibility registry data,
not runtime control-flow logic, and can be collapsed while preserving the public
`flowpilot_router.py` facade.

## What Changes

- Collapse the router facade export manifest shard layer into a single
  registry-backed owner module.
- Preserve all public facade exports, helper functions, and compatibility import
  paths used by existing tests and downstream callers.
- Update FlowGuard StructureMesh/model-test evidence so the new registry shape
  is explicitly covered.
- Run focused validation first, then background model/router regressions before
  local install sync and local git completion.

## Capabilities

### New Capabilities
- `router-facade-export-registry`: Covers the router facade export registry
  structure, compatibility wrappers, public export parity, and validation gates.

### Modified Capabilities
- `repository-maintenance-guardrails`: Extends the maintenance guardrails for
  this repo so this contraction remains OpenSpec/FlowGuard-traced, locally
  installed, and locally committed without remote publication.

## Impact

- Affected runtime code: `skills/flowpilot/assets/flowpilot_router_facade_export_manifest*.py`
  and any direct facade export manifest tests.
- Affected model/test evidence: router facade split checks, structure
  maintenance checks, model-test alignment source contracts, full diagnostic
  contracts, and install checks.
- Affected local sync: source-owned FlowPilot install sync and installed-skill
  freshness audit.
- No event names, JSON ledger shapes, runtime protocols, CLI commands, GitHub
  push, tag, or release publication are in scope.
