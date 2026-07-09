## Why

The DataBank live run showed that FlowPilot can still reach `complete` with a
dirty control-plane ledger: a `review_blocked` result remained attached through
`packet.accepted_result_id`, repair-chain packets lost `repair_blocker_id`,
open break-glass artifacts were not closed, and final Reviewer replay packets
were issued without authorized result bodies. This is a model miss after prior
control-plane hardening, so the repair must bind the observed failure class to
runtime invariants, FlowGuard models, and fake-AI Cartesian coverage.

## What Changes

- Harden the accepted-result lifecycle so PM FlowGuard absorption packages are
  not formally accepted before Reviewer and system validation gates, and every
  `accepted_result_id` must point to a mechanically clean accepted result.
- Make assignment-repair paths reject dirty accepted pointers instead of
  resurrecting packets whose target result was later review-blocked.
- Preserve `repair_blocker_id` through the existing blocker -> PM decision gate
  -> FlowGuard check -> PM FlowGuard acceptance -> review/recheck chain.
- Add terminal ledger hygiene checks that block closure and terminal return
  when stale active blockers, dirty accepted pointers, open break-glass
  incidents, or pending permanent-fix patches remain.
- Ensure final/backward replay Reviewer packets receive authorized evidence
  bundles through existing `authorized_result_reads`, rather than asking the
  Reviewer to infer or read sealed sibling bodies.
- Extend prompt/card text only where it describes existing role duties and
  existing runtime fields; no fallback, UI, compatibility aliases, or new
  persistent fields are introduced.
- Extend FlowGuard models, model-test alignment, and fake-AI/D-card Cartesian
  coverage for the observed control-plane miss family.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `flowpilot-control-plane-contract-kernel`: accepted-result pointers,
  assignment repair, and PM FlowGuard absorption must preserve current-contract
  ledger invariants.
- `flowpilot-packet-review-flow`: PM FlowGuard acceptance and review packets
  must use formal Reviewer/System gates before accepted packet state is
  committed.
- `blocker-repair-policy`: repair-chain derived packets must preserve existing
  repair blocker identity instead of rebinding or guessing.
- `controller-break-glass-repair`: open incidents and pending permanent-fix
  patches must block clean closure/terminal return until disposition is
  recorded.
- `terminal-ledger`: final closure and terminal preflight must consume whole
  ledger hygiene, not only the current target filter.
- `synthetic-agent-coverage-matrix`: fake-AI/D-card coverage must include the
  Cartesian control-plane miss axes for accepted pointers, repair identity,
  break-glass state, stale blockers, reviewer authorization, and closure phase.
- `end-to-end-synthetic-agent-chaos-replay`: synthetic replay must exercise the
  same current-runtime paths with observed bad packages and corrected retries.

## Impact

- Runtime: `skills/flowpilot/assets/flowpilot_core_runtime/runtime.py` and
  closely related contract/projection helpers as needed.
- Prompt/cards: runtime-generated packet instructions and existing Reviewer,
  FlowGuard, PM, and break-glass cards only where they reference existing
  duties and fields.
- Models: existing FlowGuard simulations for control surface contracts, blocker
  repair information flow, controller break-glass, runtime closure, recursive
  closure reconciliation, model-test alignment, and Cartesian control-plane
  exhaustion.
- Tests: focused runtime regressions, historical live-run replay fixtures,
  fake-AI runtime replay, synthetic agent trace replay, and coverage-matrix
  checks.
