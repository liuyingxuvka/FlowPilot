## Why

FlowPilot has accumulated compatibility fields, event aliases, command aliases,
prompt language, migration helpers, historical equivalence gates, and public
facades from earlier control-plane designs. The product direction is now
FlowPilot-only: current runs must use the new FlowPilot workflow directly,
instead of accepting, migrating, or teaching old protocol paths.

## What Changes

- **BREAKING** Remove fresh-invocation compatibility aliases such as
  `next --new-invocation` and `run-until-wait --new-invocation`; fresh startup
  is entered through the current `start` path only.
- **BREAKING** Reject legacy startup payloads, legacy role/officer/reviewer
  event aliases, deprecated transaction kinds, output-type aliases, and
  compatibility report artifacts instead of canonicalizing them into current
  Router events.
- **BREAKING** Remove runtime migration/recovery helpers that import old
  FlowPilot layouts, old material packet contracts, or old terminal closure
  state into the new control plane.
- Remove active prompt/card instructions that describe old compatibility
  paths, old event names, direct chat-body returns, or deprecated repair flows
  as usable workflow options.
- Remove install and validation requirements that treat legacy-to-router,
  legacy-prompt, barrier-equivalence, or legacy-full checks as current
  release gates.
- Replace current safety quarantine fields that are named as `old_*` only where
  the value is not a legacy input contract; preserve the invariant that prior
  or superseded authority cannot regain current control.
- Stage public facade contraction through FlowGuard StructureMesh so owner
  modules remain the source of truth and remaining public entrypoints are
  current, not compatibility-preserving.
- Synchronize the local installed FlowPilot skill and commit the final local git
  result after validation.

## Capabilities

### New Capabilities

- `flowpilot-new-only-runtime`: FlowPilot accepts only current startup,
  event, transaction, prompt, and run-layout contracts; old compatibility
  surfaces are rejected or removed.

### Modified Capabilities

- `flowpilot-invocation-intent-isolation`: fresh invocation SHALL have only the
  current `start` entrypoint and no command alias for new invocation.
- `startup-intake-boundary`: startup intake SHALL reject legacy chat-body
  startup payloads rather than reconciling them.
- `flowpilot-prompt-boundary-policy`: active prompts and cards SHALL not
  instruct roles to use compatibility aliases or old workflow paths.
- `role-output-transaction-boundaries`: role outputs and transaction contracts
  SHALL remove legacy output aliases and deprecated transaction kind aliases.
- `executable-repair-transactions`: repair transactions SHALL use current
  transaction families only and reject deprecated `event_replay` or
  `legacy_reconcile` routes.
- `router-facade-export-registry`: public router exports SHALL distinguish
  current public API from compatibility facade exports and contract the latter.
- `tiered-flowpilot-test-validation`: validation SHALL stop requiring legacy
  equivalence and legacy-full checks as current release evidence.
- `final-structure-convergence`: completion SHALL include repository-owned
  install sync, install check, freshness audit, and local git commit.

## Impact

- Affected code includes `skills/flowpilot/`, runtime cards, runtime contract
  JSON, Router protocol/event modules, startup/layout helpers, terminal ledger
  recovery helpers, test tier registries, install checks, simulations, and
  FlowPilot/OpenSpec documentation.
- This intentionally changes local developer and runtime behavior for old
  FlowPilot inputs; callers must use the current FlowPilot startup, event, and
  transaction contracts.
- Historical documents may remain only as archived evidence when they are not
  install/runtime requirements and do not instruct active workflow behavior.
- No tag, push, release, deploy, or binary packaging is in scope.
