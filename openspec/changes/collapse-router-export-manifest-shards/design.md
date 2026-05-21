## Context

`flowpilot_router.py` is already a small compatibility facade, but its export
registry is still physically split across several Python shard files:
actions, controller subdomains, route, startup, and terminal/work. FlowGuard
Architecture Reduction classified this as the only ready contraction candidate
because it is registry data protected by the public facade, not control-flow
state reconciliation.

Current constraints:

- Keep `flowpilot_router.py` and `install_facade_exports(...)` behavior stable.
- Keep compatibility imports such as `owner_exports_actions()` available unless
  StructureMesh and downstream tests prove a removal is safe.
- Do not touch receipt reconciliation, lifecycle cleanup, event names, ledger
  shapes, or runtime control semantics in this change.
- Other AI agents may be active, so the write set must stay narrow.

## Goals / Non-Goals

**Goals:**
- Collapse the internal export registry data into one canonical owner module.
- Keep old manifest shard modules as thin compatibility wrappers over the
  canonical registry.
- Make tests verify that old wrapper functions and the aggregate
  `OWNER_EXPORTS` expose the same public names.
- Update model/test contract references so FlowGuard evidence matches the final
  structure.
- Synchronize the locally installed FlowPilot skill after validation.

**Non-Goals:**
- Do not remove public facade exports.
- Do not remove compatibility wrapper modules during this pass.
- Do not refactor Controller receipt, lifecycle, event-dispatch, or router
  state-writing logic.
- Do not publish, tag, push, or create a GitHub release.

## Decisions

### Decision: Single canonical registry with wrapper compatibility

Create one registry owner module that stores domain-keyed export specs. Existing
modules like `flowpilot_router_facade_export_manifest_actions.py` become thin
views over that registry.

Alternative considered: delete shard modules and update all imports. Rejected
because tests and downstream callers still import the shard helper functions.

### Decision: Preserve domain view functions

Functions such as `owner_exports_actions()`, `owner_exports_route()`, and
`owner_exports_controller()` remain the compatibility surface. They should
return data derived from the canonical registry rather than own separate rows.

Alternative considered: expose only `OWNER_EXPORTS`. Rejected because the
existing model-test alignment evidence names the view functions as code
contracts.

### Decision: Use focused validation before broad regressions

First run import/contract tests for the facade export registry, then run the
existing StructureMesh/model-test alignment checks. Heavy Meta, Capability, and
router regressions can run through the repository background artifact contract.

Alternative considered: run all heavy checks first. Rejected because focused
failures are cheaper to diagnose before launching long background validation.

## Risks / Trade-offs

- Public export drift -> Mitigate with tests comparing wrapper views,
  aggregate registry rows, and installed facade names.
- Model-test evidence drift -> Update source-contract/model-test references
  if code contract paths or symbols change.
- Micro-module churn -> Keep wrapper modules only for compatibility and avoid
  adding one-function data files.
- Peer-agent overlap -> Check `git status --short` before each write phase and
  only stage this change's paths.

## Migration Plan

1. Add OpenSpec and FlowGuard evidence for the narrowed contraction.
2. Introduce the canonical export-registry owner.
3. Convert existing shard modules to compatibility views over the registry.
4. Run focused import/contract tests and FlowGuard structure checks.
5. Run background router/Meta/Capability regressions and inspect final
   artifacts before claiming completion.
6. Sync the repo-owned FlowPilot install, audit freshness, and commit locally.

Rollback is local git rollback of this change's files; no remote publication is
in scope.

## Open Questions

No product or protocol decision is currently open. If validation shows a public
export contract depends on a shard module owning its own data, keep the wrapper
and stop at a narrower registry cleanup.
