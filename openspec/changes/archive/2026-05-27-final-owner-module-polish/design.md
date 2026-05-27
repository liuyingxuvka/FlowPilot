## Context

The runtime is now broadly modular, but a few owner modules are still large
enough to hide unrelated behavior:

- `packet_control_plane_model_transitions.py` has all packet model transitions
  in one file.
- `flowpilot_router_facade_export_manifest.py` has all facade export registry
  entries in one manifest.
- `flowpilot_router_action_factory.py` combines dispatch gates, card-return
  blockers, passive waits, user reporting policy, and action construction.
- `flowpilot_router_work_packets_pm_role.py` combines PM role-work gate
  mappings, request writes, result return/decision handling, request indexes,
  officer lifecycle records, and next-action selection.
- `flowpilot_router_terminal_ledger.py` combines terminal summary, final
  ledger traceability, backward replay, closure suite, terminal recovery, and
  legacy repair.
- `flowpilot_router_controller_scheduler_receipts.py` combines Controller action
  writes, receipt writes, postcondition application, startup receipt effects,
  pending-action reconciliation, and scheduler backfill.

The goal is not to maximize file count. The goal is to make each remaining
heavy owner answer a clear question: "which behavior family owns this bug?"

## Goals

- Reduce the largest remaining owners without creating one-function files.
- Preserve public imports, private compatibility exports, and CLI behavior.
- Keep state-writing boundaries explicit and FlowGuard-modeled.
- Keep prompt text in external PromptStore assets only where it is truly prompt
  text and can be hash-managed.
- Keep all heavy regressions hidden/background with final artifacts.
- Finish with local install sync and local git commit on `main`.

## Non-Goals

- No GitHub push, tag, or release publication.
- No behavior redesign unless a real bug is exposed by the split.
- No broad repo formatter or unrelated cleanup.
- No deletion of compatibility names unless tests and export evidence prove
  they are unused and the cleanup is within this change's owner boundary.

## Design

### Phase-oriented packet control-plane transitions

Keep `packet_control_plane_model_transitions.py` as the import-compatible facade.
Move transition classes into cohesive files:

- issue/resume transitions;
- packet write/controller relay transitions;
- dispatch/result relay transitions;
- reviewer/PM outcome transitions.

`packet_control_plane_model.py` continues to import from the facade, so existing
model runner behavior stays stable.

### Domain-oriented router export manifests

Keep `flowpilot_router_facade_export_manifest.py` as the aggregator that exposes
`OWNER_EXPORTS` and `PUBLIC_EXPORT_NAMES`. Move registry rows into domain
manifest shards that mirror real owner families. The facade installer remains
unchanged from the perspective of `flowpilot_router_facade_exports.py`.

### Behavior-family router owner splits

Each large owner keeps a small compatibility facade and moves implementation to
children with the same bound-router pattern already used in the repository:

- action factory: blocker/gate helpers vs final action construction;
- PM role work: gate mapping, request/result writes, request indexes, lifecycle
  records, next-action/reconciliation;
- terminal ledger: summary, final ledger, closure/replay, recovery/legacy
  repair;
- Controller scheduler receipts: action/receipt writes, receipt effects,
  pending reconciliation, scheduled reconciliation/backfill.

### Prompt externalization discipline

Only move prompt-like text when all three are true:

1. the text is stable instruction/system-card/prompt material;
2. runtime behavior can load it through existing PromptStore mechanics or a
   clearly equivalent manifest path;
3. validation can reject missing/stale prompt assets.

If text is ordinary error text, ledger summary text, schema labels, or compact
runtime metadata, leave it in Python.

### FlowGuard evidence

Before claiming completion, StructureMesh/TestMesh evidence must know the new
owner modules. The model must keep known-bad variants meaningful: missing owner,
removed facade, stale parity, hidden skipped tests, progress-only background,
and insufficient release evidence must remain blocked in the model.

The model-test alignment runner also carries a source-contract layer for
selected externally visible Python surfaces. That layer binds model obligations
to `CodeContract` rows and selected tests, then uses FlowGuard's conservative
AST audit to reject missing Python symbols, tests that only assert helper paths,
tests that call no external assertion, and undeclared side-effect-looking calls.
This layer is narrower than full semantic replay; it is evidence that the
declared model/test rows touch real code contracts, not a substitute for router,
Meta, or Capability regressions.

### Validation strategy

Run focused compile/import checks first, then focused tests for touched areas.
After that, run StructureMesh/TestMesh/model-test alignment. Finally run router
background tier plus Meta/Capability layered full regressions through hidden
background artifacts and inspect final exit/meta evidence.

## Risks

- Splitting bound-router helpers can accidentally lose facade globals. Mitigate
  by keeping facades and `_bind_router` propagation in each child.
- Manifest shards can drift from the aggregator. Mitigate with facade export
  checks and install checks.
- Model transitions can lose workflow ordering. Mitigate by keeping the workflow
  facade and direct packet control-plane model runner green.
- Prompt movement can produce false-green coverage if coverage only reads
  Python. Mitigate by extending coverage models whenever prompt assets move.
