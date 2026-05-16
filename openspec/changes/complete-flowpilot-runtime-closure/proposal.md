## Why

FlowPilot v0.9.3 is healthy, but the remaining clean-rebuild gaps still leave
important runtime closure behavior partially enforced by generic packet paths,
protocol prose, or future-work notes. This pass closes the highest-value gaps
before heavier dogfooding: officer model packets, old-state quarantine, final
user-facing completion output, and route display refresh.

## What Changes

- Add a dedicated officer request/report packet lifecycle so Process and Product
  FlowGuard officer work cannot rely on invented direct events or system-card
  wording alone.
- Add current-run quarantine checks for imported prior state, old agent IDs,
  old assets, and stale route/control files before continuation evidence can
  become authority.
- Add a final user report artifact after terminal closure so the delivered
  result has a durable user-facing summary separate from internal ledgers.
- Add route display refresh requirements for chat route signs and UI-readable
  snapshots when route/frontier state changes.
- Tighten Router runtime settlement so an already-reconciled Controller action
  backfills its matching Router scheduler row, and active runtime writers are
  waited on through the existing settlement path instead of becoming false
  blockers.
- Add focused FlowGuard coverage, runtime tests, install checks, documentation,
  installed-skill synchronization, and local git completion evidence.

## Capabilities

### New Capabilities

- `officer-packet-lifecycle`: Dedicated PM-to-officer request and officer
  report packet lifecycle, including router-authorized events and result
  contracts.
- `continuation-state-quarantine`: Current-run import/quarantine checks for
  old control state, old role agents, stale assets, and prior-run evidence.
- `closure-user-report`: Durable user-facing completion report after clean PM
  closure and terminal backward replay.
- `route-display-refresh`: Chat route-sign and UI snapshot refresh behavior tied
  to route/frontier changes.
- `router-runtime-settlement`: Existing Router-owned receipt/reconciliation
  logic backfills scheduler rows from reconciled Controller actions and keeps
  fresh/progressing runtime writers in the wait/retry path.

### Modified Capabilities

- `repository-maintenance-guardrails`: require this maintenance pass to finish
  with FlowGuard adoption evidence, local install freshness, OpenSpec
  validation, and a local git commit.

## Impact

- `skills/flowpilot/assets/flowpilot_router.py`
- FlowPilot runtime helper modules under `skills/flowpilot/assets/`
- Runtime cards and contracts under
  `skills/flowpilot/assets/runtime_kit/`
- Templates under `templates/flowpilot/`
- Focused FlowGuard models and result files under `simulations/`
- Runtime and install tests under `tests/` and `scripts/check_install.py`
- Handoff, equivalence, adoption, and validation documentation
- Local installed FlowPilot skill under the Codex skills directory after
  repository validation passes
