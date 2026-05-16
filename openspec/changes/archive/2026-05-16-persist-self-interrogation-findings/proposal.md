## Why

FlowPilot already asks PMs, reviewers, officers, and workers to challenge their
own plans and outputs, but those self-interrogation results can remain trapped
in prose or role-local reasoning. This change makes meaningful findings become
run-scoped evidence that PM must disposition before downstream gates can
advance.

## What Changes

- Add a first-class self-interrogation record contract for startup/product
  architecture, node entry, repair, and completion scopes.
- Require PM-owned self-interrogation findings to be dispositioned into a
  downstream artifact, named future node/gate, PM suggestion ledger entry, or
  rejected/waived reason before protected gates proceed.
- Require reviewers, workers, and FlowGuard officers to surface hard blockers
  and useful nonblocking findings as structured PM suggestion candidates rather
  than leaving them only in report prose.
- Add Router mechanical checks for unresolved self-interrogation findings at
  root-contract freeze, current-node dispatch, final ledger, and terminal
  closure boundaries.
- Extend FlowGuard models and tests so known-bad routes where findings are
  created but ignored fail before implementation can claim completion.

## Capabilities

### New Capabilities

- `self-interrogation-disposition`: Persistent self-interrogation records and
  PM disposition gates for FlowPilot formal runs.

### Modified Capabilities

- None. There are no archived OpenSpec specs in this repository yet.

## Impact

- Runtime templates under `templates/flowpilot/`.
- FlowPilot runtime cards under `skills/flowpilot/assets/runtime_kit/cards/`.
- Router validation/writer logic in `skills/flowpilot/assets/flowpilot_router.py`.
- FlowGuard process and capability models in `simulations/meta_model.py` and
  `simulations/capability_model.py`.
- Model runners and tests that assert self-interrogation, output contracts,
  prompt coverage, and final ledger behavior.
- Local installed `flowpilot` skill copy after implementation sync.
